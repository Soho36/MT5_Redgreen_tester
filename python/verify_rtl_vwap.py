"""Independent raw-minute and economic reconstruction of the RTL VWAP study.

No production feature/analyzer helpers are imported.  Minute PV contributions,
causal endpoint labels, as-of joins and all economic controls are rebuilt here.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_vwap_20261025'
PROTOCOL = ROOT / 'docs/baseline/rtl-vwap/PROTOCOL.md'
PROTOCOL_SHA = 'a75e57ab36fe49fb63f3664f847cb8ba52ac651a109a76c3cc220c0344eb0314'
MINUTES = Path(r'F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv')
M30 = ROOT / 'Reports/trend_rr_20261002/m30_reference.csv'
SOURCE = ROOT / 'Reports/rtl_market_regimes_20261023/trades.csv'
ERAS = {'2016-19': ('2016-01-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01')}
VARIANTS = ('full_hlc3', 'full_close', 'cash_hlc3')
POLICIES = ('skip_below', 'skip_far_above', 'skip_far_below', 'skip_churn', 'skip_churn4')
PARTITIONS = {'side': ('above', 'below', 'at', 'unknown'),
              'distance': ('far_below', 'below', 'at', 'above', 'far_above', 'unknown'),
              'event': ('reclaim', 'loss', 'same_side', 'unknown'),
              'churn': ('churn', 'orderly', 'unknown'), 'churn4': ('churn', 'orderly', 'unknown')}
END = pd.Timestamp('2026-10-01')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def numeric(actual, expected, label, atol=1e-8):
    np.testing.assert_allclose(np.asarray(actual, float), np.asarray(expected, float),
                               rtol=1e-10, atol=atol, equal_nan=True, err_msg=label)


def equal(actual, expected, label):
    a = pd.Series(actual).reset_index(drop=True).astype(object).fillna('<NA>').astype(str)
    b = pd.Series(expected).reset_index(drop=True).astype(object).fillna('<NA>').astype(str)
    assert a.equals(b), f'{label}: {pd.DataFrame({"actual": a, "expected": b}).loc[a != b].head()}'


def read(name):
    return pd.read_csv(OUT/name, float_precision='round_trip', low_memory=False)


def parse_dates(frame):
    for name in ('bar_time', 'available_at', 'submitted', 'entry_time', 'exit_time', 'session', 'week_start'):
        if name in frame:
            frame[name] = pd.to_datetime(frame[name], format='ISO8601')
    return frame


def raw_m30():
    """Rebuild every observed M30 OHLC and minute PV sum, validating raw input."""
    pieces, previous, n = [], None, 0
    columns = ['<DATE>', '<TIME>', '<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>', '<VOL>', '<TICKVOL>']
    for raw in pd.read_csv(MINUTES, sep='\t', usecols=columns, chunksize=500000):
        t = pd.to_datetime(raw['<DATE>']+' '+raw['<TIME>'], format='%Y.%m.%d %H:%M:%S')
        assert t.is_monotonic_increasing and t.is_unique
        if previous is not None:
            assert t.iloc[0] > previous
        previous = t.iloc[-1]
        assert (t.dt.hour >= 1).all()
        v = raw['<VOL>'].to_numpy()
        assert np.isfinite(v).all() and (v > 0).all() and np.array_equal(v, raw['<TICKVOL>'])
        prices = raw[['<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>']].to_numpy()
        assert np.isfinite(prices).all() and (prices > 0).all()
        o, h, l, c = prices.T
        assert np.all(h >= np.maximum.reduce([o, l, c])) and np.all(l <= np.minimum.reduce([o, h, c]))
        frame = pd.DataFrame(dict(bar_time=t.dt.floor('30min'), open=o, high=h, low=l, close=c,
                                  volume=v, hlc3_pv=((h+l+c)/3)*v, close_pv=c*v))
        pieces.append(frame.groupby('bar_time', sort=True).agg(open=('open', 'first'), high=('high', 'max'),
            low=('low', 'min'), close=('close', 'last'), volume=('volume', 'sum'),
            hlc3_pv=('hlc3_pv', 'sum'), close_pv=('close_pv', 'sum')))
        n += len(raw)
    # Chunk boundaries may split an M30 bar; recombine chronologically.
    result = pd.concat(pieces).groupby(level=0, sort=True).agg(open=('open', 'first'), high=('high', 'max'),
        low=('low', 'min'), close=('close', 'last'), volume=('volume', 'sum'),
        hlc3_pv=('hlc3_pv', 'sum'), close_pv=('close_pv', 'sum'))
    reference = pd.read_csv(M30, parse_dates=['bar_time'], index_col='bar_time')
    assert result.index.equals(reference.index)
    numeric(result[['open', 'high', 'low', 'close']], reference[['open', 'high', 'low', 'close']], 'raw M1 to M30 OHLC', atol=0)
    print(f'Independent raw source: {n:,} minute rows and {len(result):,} exact M30 OHLC matches.', flush=True)
    return result.loc[result.index+pd.Timedelta(minutes=30) < END].copy(), n


def literal_features(m30, variant):
    """Separate groupwise cumulative sums and explicit sliding-window labels."""
    f = m30.copy().reset_index()
    f['available_at'] = f.bar_time+pd.Timedelta(minutes=30)
    session = f.bar_time.dt.normalize()
    n = len(f)
    close, high, low = (f[c].to_numpy(float) for c in ('close', 'high', 'low'))
    previous = np.r_[np.nan, close[:-1]]
    tr = np.maximum.reduce([high-low, np.abs(high-previous), np.abs(low-previous)])
    a20 = np.full(n, np.nan)
    a20[19:] = np.lib.stride_tricks.sliding_window_view(tr, 20).sum(axis=1)/20
    f['a20'] = a20
    rolls = pd.read_csv(MINUTES.with_name('MT5_NQ_continuous_2010-2026_rolls.csv'), parse_dates=['date'])
    switch_days = set(rolls.loc[rolls.symbol.ne(rolls.symbol.shift()) & rolls.symbol.shift().notna(), 'date'])
    first = ~session.duplicated()
    switch = first & session.isin(switch_days)
    f['switch_bar'] = switch
    clean = np.zeros(n, bool)
    clean[20:] = ~np.lib.stride_tricks.sliding_window_view(switch.to_numpy(bool), 21).any(axis=1)
    f['roll_clean'] = clean & np.isfinite(a20) & (a20 > 0)
    vwap, cum, age = np.full(n, np.nan), np.full(n, np.nan), np.zeros(n, int)
    sessions = session.to_numpy()
    pv_column = 'close_pv' if variant == 'full_close' else 'hlc3_pv'
    starts = np.r_[0, np.flatnonzero(sessions[1:] != sessions[:-1])+1]
    stops = np.r_[starts[1:], n]
    minute_of_day = (f.bar_time.dt.hour*60+f.bar_time.dt.minute).to_numpy()
    for start, stop in zip(starts, stops):
        positions = np.arange(start, stop)
        if variant == 'cash_hlc3':
            positions = positions[minute_of_day[positions] >= 16*60+30]
        if not len(positions):
            continue
        cv = np.cumsum(f.volume.to_numpy()[positions], dtype=float)
        cp = np.cumsum(f[pv_column].to_numpy()[positions], dtype=float)
        cum[positions], vwap[positions], age[positions] = cv, cp/cv, np.arange(1, len(positions)+1)
    f['cum_volume'], f['vwap'], f['anchor_age'] = cum, vwap, age
    known = np.isfinite(vwap)
    f['vwap_available'] = known
    delta = close-vwap
    f['z'] = np.divide(delta, a20, out=np.full(n, np.nan), where=np.isfinite(a20) & (a20 > 0))
    f['side'] = np.where(~known, 'unknown', np.where(delta > 0, 'above', np.where(delta < 0, 'below', 'at')))
    z = f.z.to_numpy()
    f['distance'] = np.select([~np.isfinite(z), z < -1, z < 0, z == 0, z <= 1],
                             ['unknown', 'far_below', 'below', 'at', 'above'], default='far_above')
    events = np.full(n, 'unknown', dtype=object)
    has_previous = age > 1
    old_delta = np.r_[np.nan, delta[:-1]]
    events[has_previous] = 'same_side'
    events[has_previous & (old_delta <= 0) & (delta > 0)] = 'reclaim'
    events[has_previous & (old_delta >= 0) & (delta < 0)] = 'loss'
    f['event'] = events
    crossing = has_previous & (old_delta*delta < 0)
    for transitions, threshold in ((6, 3), (4, 2)):
        counts = np.full(n, np.nan)
        sums = np.lib.stride_tricks.sliding_window_view(crossing, transitions).sum(axis=1)
        counts[transitions-1:] = sums
        counts[age < transitions+1] = np.nan
        f[f'crossings{transitions}'] = counts
        f['churn' if transitions == 6 else 'churn4'] = np.where(~np.isfinite(counts), 'unknown',
            np.where(counts >= threshold, 'churn', 'orderly'))
    return f


def verify_feature_panel(actual, expected, label):
    assert len(actual) == len(expected), label
    for field in ('bar_time', 'available_at'):
        assert pd.to_datetime(actual[field]).reset_index(drop=True).equals(expected[field].reset_index(drop=True)), label+'/'+field
    for field in ('open', 'high', 'low', 'close', 'vwap', 'cum_volume', 'anchor_age', 'a20', 'z', 'crossings6', 'crossings4'):
        numeric(actual[field], expected[field], label+'/'+field)
    for field in ('side', 'distance', 'event', 'churn', 'churn4', 'roll_clean', 'switch_bar', 'vwap_available'):
        equal(actual[field], expected[field], label+'/'+field)


def verify_joins(features):
    base = parse_dates(pd.read_csv(SOURCE, float_precision='round_trip'))
    base = base.loc[base.primary].sort_values(['submitted', 'ticket'], kind='stable').reset_index(drop=True)
    assert len(base) == 16668 and base.ticket.is_unique
    actual = parse_dates(read('trades.csv'))
    assert len(actual) == 3*16668 and not actual.duplicated(['variant', 'ticket']).any()
    for variant in VARIANTS:
        saved = actual.loc[actual.variant.eq(variant)].sort_values(['submitted', 'ticket'], kind='stable').reset_index(drop=True)
        f = features[variant]
        indexes = np.searchsorted(f.available_at.to_numpy(), base.submitted.to_numpy(), side='right')-1
        assert (indexes >= 0).all()
        expected = f.iloc[indexes].reset_index(drop=True)
        assert expected.available_at.le(base.submitted).all()
        stale = expected.bar_time.dt.normalize().ne(base.session)
        reasons = np.where(stale, 'session_reset', np.where(~expected.vwap_available, 'before_anchor', ''))
        expected.loc[stale, ['vwap', 'cum_volume', 'z', 'crossings6', 'crossings4']] = np.nan
        expected.loc[stale, 'anchor_age'] = 0
        expected.loc[stale, ['vwap_available', 'roll_clean']] = False
        expected.loc[stale, ['side', 'distance', 'event', 'churn', 'churn4']] = 'unknown'
        equal(saved.unknown_reason.fillna(''), reasons, variant+'/unknown reason')
        assert (~saved.loc[stale, 'vwap_available']).all()
        verify_feature_panel(saved, expected, variant+'/joined features')
        for field in ('ticket', 'requested_price', 'original_sl', 'fill_price', 'exit_price', 'trade_profit',
                      'net_dollars', 'net_r', 'gross_r', 'initial_risk_dollars', 'fill_risk_dollars', 'holding_minutes',
                      'stress1_net_dollars', 'stress1_net_r', 'stress2_net_dollars', 'stress2_net_r', 'commission_r'):
            numeric(saved[field], base[field], variant+'/preserved '+field)
        for field in ('submitted', 'entry_time', 'exit_time', 'session', 'week_start', 'era'):
            equal(saved[field], base[field], variant+'/preserved '+field)
    for era, count, net in [('2016-19', 6167, 4416.65), ('2020-26', 10501, 38399.95)]:
        p = base.loc[base.era.eq(era)]
        assert len(p) == count
        numeric([p.net_dollars.sum()], [net], 'baseline '+era)
    numeric(base.net_dollars, base.trade_profit-1.05, 'net commission')
    numeric(base.net_r, base.net_dollars/base.initial_risk_dollars, 'net R denominator')
    return actual


def maxdd(values):
    equity = np.r_[0., np.cumsum(values)]
    return float(np.max(np.maximum.accumulate(equity)-equity))


def skip(frame, policy):
    if policy == 'skip_below':
        return frame.side.eq('below').to_numpy()
    if policy in ('skip_far_above', 'skip_far_below'):
        return frame.distance.eq(policy[5:]).to_numpy()
    return frame['churn4' if policy == 'skip_churn4' else 'churn'].eq('churn').to_numpy()


def metrics(trades, calendar):
    daily = trades.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.)
    weekly = daily.groupby(daily.index-pd.to_timedelta(daily.index.weekday, unit='D')).sum()
    ordered = trades.sort_values(['exit_time', 'entry_time', 'ticket'], kind='stable')
    balance, high, high_day, duration = 0., 0., calendar[0], 0
    for day, pnl in daily.items():
        balance += pnl
        if balance >= high-1e-9:
            high, high_day = max(high, balance), day
        else:
            duration = max(duration, (day-high_day).days)
    pos, loss = trades.net_dollars.clip(lower=0).sum(), -trades.net_dollars.clip(upper=0).sum()
    out = dict(trades=len(trades), active_sessions=trades.session.nunique(), active_weeks=trades.week_start.nunique(),
        eligible_sessions=len(calendar), eligible_weeks=len(weekly), gross_mean_r=trades.gross_r.mean(),
        net_mean_r=trades.net_r.mean(), gross_dollars=trades.trade_profit.sum(), net_dollars=trades.net_dollars.sum(),
        dollar_pf=pos/loss if loss else np.nan, risk_mean=trades.initial_risk_dollars.mean(),
        risk_median=trades.initial_risk_dollars.median(), commission_mean_r=trades.commission_r.mean(),
        holding_hours=trades.holding_minutes.sum()/60, mean_holding_minutes=trades.holding_minutes.mean(),
        worst_day=daily.min(), worst_week=weekly.min(), worst5pct_session_mean=daily.nsmallest(math.ceil(.05*len(calendar))).mean(),
        closed_trade_dd=maxdd(ordered.net_dollars.to_numpy()), daily_close_dd=maxdd(daily.to_numpy()),
        daily_dd_duration_days=duration, positive_net_dollars=pos, loss_dollars=loss,
        planned_risk_total=trades.initial_risk_dollars.sum(), net_r_total=trades.net_r.sum(), gross_r_total=trades.gross_r.sum(),
        winners=int(trades.net_dollars.gt(0).sum()), losers=int(trades.net_dollars.lt(0).sum()),
        adequate_coverage=len(trades) >= 200 and trades.week_start.nunique() >= 30)
    for stress in (1, 2):
        out[f'stress{stress}_net_dollars'] = trades[f'stress{stress}_net_dollars'].sum()
        out[f'stress{stress}_mean_r'] = trades[f'stress{stress}_net_r'].mean()
    equity = 0.
    peak, peak_time, longest = 0., calendar[0], 0.
    for row in ordered.itertuples():
        equity += row.net_dollars
        if equity >= peak-1e-9:
            peak, peak_time = max(equity, peak), row.exit_time
        else:
            longest = max(longest, (row.exit_time-peak_time).total_seconds()/86400)
    if equity < peak-1e-9:
        longest = max(longest, (calendar[-1]+pd.Timedelta(days=1)-peak_time).total_seconds()/86400)
    out['closed_trade_dd_duration_days'] = longest
    out['net_over_daily_dd'] = out['net_dollars']/out['daily_close_dd'] if out['daily_close_dd'] else np.nan
    return out


def metric_row(row, expected, label):
    for field, value in expected.items():
        assert field in row.index, label+'/'+field
        numeric([row[field]], [value], label+'/'+field, atol=1e-6)


def verify_economics(trades, calendar_all):
    tables = {name: read(name+'.csv') for name in ('summaries', 'yearly', 'roll_summary',
        'common_anchor_summary', 'availability', 'policies', 'roll_policies', 'policy_sessions')}
    tables['policy_sessions'] = parse_dates(tables['policy_sessions'])
    counts = {name: 0 for name in tables}
    for era, (start, stop) in ERAS.items():
        calendar = calendar_all[(calendar_all >= start) & (calendar_all < stop)]
        era_rows = trades.loc[trades.era.eq(era)]
        cash_ids = set(era_rows.loc[era_rows.variant.eq('cash_hlc3') & era_rows.vwap.notna(), 'ticket'])
        for variant in VARIANTS:
            part = era_rows.loc[era_rows.variant.eq(variant)]
            clean = part.loc[part.roll_clean]
            selection = [('summaries', part, calendar, None), ('roll_summary', clean, calendar, None)]
            if variant != 'full_close':
                selection.append(('common_anchor_summary', part.loc[part.ticket.isin(cash_ids)], calendar, None))
            for year in sorted(part.year.unique()):
                selection.append(('yearly', part.loc[part.year.eq(year)], calendar[calendar.year == year], year))
            for name, frame, cal, year in selection:
                saved = tables[name].loc[tables[name].era.eq(era) & tables[name].variant.eq(variant)]
                if year is not None:
                    saved = saved.loc[saved.year.eq(year)]
                    assert saved.partial.eq(year == 2026).all()
                groups = [('all', 'all', frame)]
                for dimension, cats in PARTITIONS.items():
                    assert frame[dimension].isin(cats).all()
                    groups.extend((dimension, cat, frame.loc[frame[dimension].eq(cat)]) for cat in cats)
                assert len(saved) == len(groups)
                for dimension, cat, group in groups:
                    rows = saved.loc[saved.dimension.eq(dimension) & saved.category.eq(cat)]
                    assert len(rows) == 1
                    metric_row(rows.iloc[0], metrics(group, cal), f'{name}/{era}/{variant}/{dimension}/{cat}')
                    counts[name] += 1
            availability = tables['availability'].query('era == @era and variant == @variant')
            assert len(availability) == 1
            metric_row(availability.iloc[0], dict(baseline_trades=len(part), vwap_available_trades=part.vwap.notna().sum(),
                vwap_available_fraction=part.vwap.notna().mean(), roll_clean_trades=len(clean),
                common_full_cash_available_trades=len(cash_ids), common_full_cash_available_fraction=len(cash_ids)/len(part)), 'availability')
            counts['availability'] += 1
            for name, frame in [('policies', part), ('roll_policies', clean)]:
                for policy in POLICIES:
                    omitted = frame.loc[skip(frame, policy)]
                    retained = frame.loc[~skip(frame, policy)]
                    fraction = retained.holding_minutes.sum()/frame.holding_minutes.sum()
                    fractions = dict(skipped_trades=len(omitted), skipped_active_weeks=omitted.week_start.nunique(),
                        skipped_net_dollars=omitted.net_dollars.sum(), skipped_net_mean_r=omitted.net_r.mean(),
                        losses_avoided=-omitted.net_dollars.clip(upper=0).sum(), profits_missed=omitted.net_dollars.clip(lower=0).sum(),
                        retained_trade_fraction=len(retained)/len(frame), retained_holding_fraction=fraction,
                        retained_planned_risk_fraction=retained.initial_risk_dollars.sum()/frame.initial_risk_dollars.sum())
                    scaled = frame.copy()
                    for column in ('net_dollars', 'trade_profit', 'initial_risk_dollars', 'fill_risk_dollars',
                                   'stress1_net_dollars', 'stress2_net_dollars', 'holding_minutes'):
                        scaled[column] *= fraction
                    if fraction == 0:
                        for column in ('gross_r', 'net_r', 'commission_r', 'stress1_net_r', 'stress2_net_r'):
                            scaled[column] = np.nan
                    for curve, group in [('baseline', frame), ('retained', retained), ('static_holding_scaled', scaled)]:
                        rows = tables[name].query('era == @era and variant == @variant and policy == @policy and curve == @curve')
                        assert len(rows) == 1
                        expected = dict(**metrics(group, calendar), **fractions,
                                        pnl_scale=fraction if curve == 'static_holding_scaled' else 1.)
                        metric_row(rows.iloc[0], expected, name+'/'+era+'/'+variant+'/'+policy+'/'+curve)
                        counts[name] += 1
                        if name == 'policies':
                            saved_curve = tables['policy_sessions'].query('era == @era and variant == @variant and policy == @policy and curve == @curve').sort_values('session')
                            actual_curve = group.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.)
                            equal(saved_curve.session, calendar, 'policy daily dates')
                            numeric(saved_curve.net_dollars, actual_curve, 'policy daily equity')
                            counts['policy_sessions'] += len(saved_curve)
    for name, count in counts.items():
        assert len(tables[name]) == count, (name, count, len(tables[name]))
    print('Verified all partitions, years, roll/common-anchor panels, omission economics and daily curves.', flush=True)
    return counts


def verify_bootstrap(trades, calendar_all):
    saved = read('bootstrap_draws.csv')
    summary = read('uncertainty.csv')
    rng = np.random.default_rng(20261025)
    count = 0
    for era, (start, stop) in ERAS.items():
        part = trades.loc[trades.era.eq(era) & trades.variant.eq('full_hlc3')]
        cal = calendar_all[(calendar_all >= start) & (calendar_all < stop)]
        weeks = pd.date_range(cal[0]-pd.Timedelta(days=cal[0].weekday()), cal[-1]-pd.Timedelta(days=cal[-1].weekday()), freq='7D')
        starts = rng.integers(0, len(weeks), size=(5000, math.ceil(len(weeks)/4)))
        sampled = np.column_stack([(starts+k) % len(weeks) for k in range(4)])
        # Interleave the four offsets of each block, rather than four offset blocks.
        sampled = sampled.reshape(5000, 4, -1).transpose(0, 2, 1).reshape(5000, -1)[:, :len(weeks)]
        for policy in POLICIES[:4]:
            mask = skip(part, policy)
            chosen, complement = part.loc[mask], part.loc[~mask]
            results = []
            for frame in (chosen, complement):
                weekly = frame.groupby('week_start').net_r.agg(['sum', 'count']).reindex(weeks, fill_value=0.)
                data = weekly.to_numpy()
                results.append(np.vstack([data[chunk].sum(axis=1) for chunk in np.array_split(sampled, 50)]))
            a, b = results
            means = np.divide(a[:, 0], a[:, 1], out=np.full(5000, np.nan), where=a[:, 1] > 0)
            other = np.divide(b[:, 0], b[:, 1], out=np.full(5000, np.nan), where=b[:, 1] > 0)
            diff = means-other
            rows = saved.query('era == @era and policy == @policy').sort_values('draw')
            assert len(rows) == 5000 and np.array_equal(rows.draw, np.arange(5000))
            for column, expected in [('selected_net_r', a[:, 0]), ('selected_trades', a[:, 1]),
                ('complement_net_r', b[:, 0]), ('complement_trades', b[:, 1]), ('mean_net_r', means), ('difference_net_r', diff)]:
                numeric(rows[column], expected, 'bootstrap '+era+'/'+policy+'/'+column)
            expected = dict(trades=len(chosen), active_weeks=chosen.week_start.nunique(), net_mean_r=chosen.net_r.mean(),
                complement_trades=len(complement), complement_net_mean_r=complement.net_r.mean(),
                difference_net_r=chosen.net_r.mean()-complement.net_r.mean(),
                valid_mean_draws=np.isfinite(means).sum(), valid_difference_draws=np.isfinite(diff).sum())
            for name, values in [('mean_net_r', means), ('difference_net_r', diff)]:
                finite = values[np.isfinite(values)]
                for suffix, alpha in [('95', .05), ('98_75', .0125)]:
                    bounds = np.quantile(finite, [alpha/2, 1-alpha/2]) if len(finite) else [np.nan, np.nan]
                    expected[name+'_ci'+suffix+'_low'], expected[name+'_ci'+suffix+'_high'] = bounds
            row = summary.query('era == @era and policy == @policy')
            assert len(row) == 1
            metric_row(row.iloc[0], expected, 'uncertainty')
            count += len(rows)
    assert count == len(saved) == 40000 and len(summary) == 8
    print('Reconstructed all 40,000 paired block-bootstrap group draws and intervals.', flush=True)
    return count


def verify_controls(trades, calendar_all):
    shifts, placement = read('placement_draws.csv'), read('placement_summary.csv')
    strata, confounds = read('confound_strata.csv'), read('confound_summary.csv')
    screen = read('screen.csv')
    rng = np.random.default_rng(20261026)
    shift_count, stratum_count, decisions = 0, 0, {}
    for era, (start, stop) in ERAS.items():
        frame = trades.loc[trades.era.eq(era) & trades.variant.eq('full_hlc3')].sort_values(['submitted', 'ticket'], kind='stable')
        cal = calendar_all[(calendar_all >= start) & (calendar_all < stop)]
        pnl, hours = frame.net_dollars.to_numpy(), frame.holding_minutes.to_numpy()/60
        day = cal.get_indexer(frame.session)
        assert np.all(day >= 0)
        base_dd = maxdd(np.bincount(day, weights=pnl, minlength=len(cal)))
        offsets = rng.integers(0, len(frame), size=1000)
        minutes = (frame.submitted.dt.hour*60+frame.submitted.dt.minute).to_numpy()
        blocks = np.select([minutes < 540, minutes < 990, minutes < 1200],
                           ['01:00-08:59', '09:00-16:29', '16:30-19:59'], default='20:00+')
        q1, q2 = np.quantile(frame.initial_risk_dollars, [1/3, 2/3])
        risk = np.where(frame.initial_risk_dollars <= q1, 'low', np.where(frame.initial_risk_dollars <= q2, 'middle', 'high'))
        for policy in POLICIES[:4]:
            mask = skip(frame, policy)
            def evaluate(keep):
                net, holding = pnl[keep].sum(), hours[keep].sum()
                dd = maxdd(np.bincount(day[keep], weights=pnl[keep], minlength=len(cal)))
                fraction = holding/hours.sum()
                return dict(retained_trades=keep.sum(), net_dollars=net, daily_close_dd=dd, holding_hours=holding,
                    holding_fraction=fraction, static_holding_net_dollars=pnl.sum()*fraction,
                    static_holding_daily_close_dd=base_dd*fraction, profit_advantage_vs_static=net-pnl.sum()*fraction,
                    dd_advantage_vs_static=base_dd*fraction-dd)
            values = pd.DataFrame([evaluate(~np.roll(mask, int(k))) for k in offsets])
            actual = evaluate(~mask)
            rows = shifts.query('era == @era and policy == @policy').sort_values('draw')
            assert len(rows) == 1000 and np.array_equal(rows.offset, offsets)
            for col in values:
                numeric(rows[col], values[col], 'placement '+era+'/'+policy+'/'+col, atol=1e-6)
            expected = dict(draws=1000, **{'actual_'+k: v for k, v in actual.items()})
            for col in ('profit_advantage_vs_static', 'dd_advantage_vs_static'):
                expected['fraction_shifts_beaten_'+col] = (values[col] < actual[col]).mean()
                expected['fraction_shifts_tied_'+col] = np.isclose(values[col], actual[col], rtol=0, atol=1e-8).mean()
            for col in ('net_dollars', 'daily_close_dd', 'profit_advantage_vs_static', 'dd_advantage_vs_static'):
                for q in (.025, .5, .975):
                    expected[col+'_q'+str(int(q*1000))] = np.quantile(values[col], q)
            ps = placement.query('era == @era and policy == @policy')
            assert len(ps) == 1
            metric_row(ps.iloc[0], expected, 'placement summary')
            shift_count += len(rows)
            # Independently enumerate the twelve predefined time/risk strata.
            weighted, support = 0., 0
            for block in ('01:00-08:59', '09:00-16:29', '16:30-19:59', '20:00+'):
                for tertile in ('low', 'middle', 'high'):
                    within = (blocks == block) & (risk == tertile)
                    if not within.any():
                        continue
                    a, b = frame.loc[within & mask], frame.loc[within & ~mask]
                    difference = a.net_r.mean()-b.net_r.mean()
                    supported = bool(len(a) and len(b))
                    if supported:
                        weighted += len(a)*difference
                        support += len(a)
                    expected = dict(selected_trades=len(a), complement_trades=len(b), selected_net_r_sum=a.net_r.sum(),
                        complement_net_r_sum=b.net_r.sum(), selected_net_mean_r=a.net_r.mean(), complement_net_mean_r=b.net_r.mean(),
                        difference_net_r=difference, common_support=supported)
                    s = strata.query('era == @era and policy == @policy and time_block == @block and risk_tertile == @tertile')
                    assert len(s) == 1
                    metric_row(s.iloc[0], expected, 'confound strata')
                    stratum_count += 1
            expected = dict(risk_tertile_q1=q1, risk_tertile_q2=q2, selected_trades=mask.sum(), supported_selected_trades=support,
                supported_selected_share=support/mask.sum() if mask.any() else np.nan,
                subset_count_weighted_difference_net_r=weighted/support if support else np.nan,
                unadjusted_difference_net_r=frame.loc[mask].net_r.mean()-frame.loc[~mask].net_r.mean())
            c = confounds.query('era == @era and policy == @policy')
            assert len(c) == 1
            metric_row(c.iloc[0], expected, 'confound summary')
            omitted = frame.loc[mask]
            core = bool(omitted.net_dollars.sum() < 0 and omitted.net_r.mean() < 0 and len(omitted) >= 200
                        and omitted.week_start.nunique() >= 30 and actual['daily_close_dd'] < base_dd)
            decisions.setdefault(policy, {})[era] = core
            s = screen.loc[screen.policy.eq(policy)]
            assert len(s) == 1
            metric_row(s.iloc[0], {era+'_negative_edge_core_passes': core, era+'_profit_delta': actual['net_dollars']-pnl.sum(),
                era+'_daily_dd_reduction': base_dd-actual['daily_close_dd'],
                era+'_profit_advantage_vs_static': actual['profit_advantage_vs_static'],
                era+'_daily_dd_advantage_vs_static': actual['dd_advantage_vs_static']}, 'screen')
    for policy, values in decisions.items():
        s = screen.loc[screen.policy.eq(policy)].iloc[0]
        assert s.negative_edge_core_both_eras == all(values.values())
        assert s.sensitivity_confound_interpretation_required and not s.adoption_authorized
    assert len(shifts) == shift_count == 8000 and len(strata) == stratum_count
    assert len(placement) == len(confounds) == 8 and len(screen) == 4
    print('Reconstructed all 8,000 placements, time/risk controls and screening decisions.', flush=True)
    return dict(placement_draws=shift_count, confound_strata=stratum_count)


def main():
    assert sha(PROTOCOL) == PROTOCOL_SHA
    checks, hashes = {}, {str(PROTOCOL): PROTOCOL_SHA}
    original = json.loads((ROOT/'Reports/rtl_price_structure_20261024/provenance.json').read_text())
    for path in (MINUTES, M30, SOURCE):
        assert sha(path) == original['inputs_sha256'][str(path)], 'Changed original source '+str(path)
    for filename in ('feature_provenance.json', 'economics_provenance.json'):
        provenance = json.loads((OUT/filename).read_text())
        assert provenance['protocol_sha256'] == PROTOCOL_SHA
        program = 'build_rtl_vwap_features.py' if filename.startswith('feature_') else 'analyze_rtl_vwap.py'
        assert sha(ROOT/'python'/program) == provenance['program_sha256'], 'Changed producer program'
        if 'prior_metrics_program_sha256' in provenance:
            assert sha(ROOT/'python/analyze_rtl_market_regimes.py') == provenance['prior_metrics_program_sha256']
        for name, expected in provenance['outputs_sha256'].items():
            assert sha(OUT/name) == expected, filename+'/'+name
        for name, expected in provenance['inputs_sha256'].items():
            path = Path(name) if Path(name).is_absolute() else OUT/name
            assert sha(path) == expected, filename+'/'+name
            hashes[str(path)] = expected
    checks['protocol_and_provenance'] = True
    raw, minute_count = raw_m30()
    checks['all_raw_minutes_and_exact_m30_ohlc'] = True
    features = {}
    for variant in VARIANTS:
        expected = literal_features(raw, variant)
        actual = read('features_'+variant+'.csv')
        verify_feature_panel(actual, expected, variant)
        numeric(actual.volume, expected.volume, variant+'/bar volume', atol=0)
        numeric(actual.pv_hlc3, expected.hlc3_pv, variant+'/minute HLC3 PV', atol=1e-5)
        numeric(actual.pv_close, expected.close_pv, variant+'/minute close PV', atol=1e-5)
        last = pd.to_datetime(actual.last_minute)
        first = pd.to_datetime(actual.first_minute)
        assert last.lt(pd.to_datetime(actual.available_at)).all()
        assert first.ge(pd.to_datetime(actual.bar_time)).all()
        assert pd.to_datetime(actual.feature_session).equals(expected.bar_time.dt.normalize())
        features[variant] = expected
        print(f'Independent {variant}: all {len(expected):,} VWAP values, labels, windows and boundaries match.', flush=True)
    checks['all_feature_math_and_availability'] = True
    trades = verify_joins(features)
    checks['all_submission_joins_and_preserved_economics'] = True
    calendar = pd.DatetimeIndex(raw.index.normalize().unique()).sort_values()
    table_counts = verify_economics(trades, calendar)
    checks['all_economic_partitions_and_policies'] = True
    draws = verify_bootstrap(trades, calendar)
    checks['all_bootstrap_draws_and_intervals'] = True
    control_counts = verify_controls(trades, calendar)
    checks['all_placements_confounds_and_decisions'] = True
    artifacts = [p for p in OUT.iterdir() if p.suffix in ('.csv', '.json') and p.name != 'independent_verification.json']
    result = dict(status='PASS', all_passed=True, checks=checks, minute_rows=minute_count,
        feature_rows_per_variant=len(raw), labelled_trade_rows=len(trades), economic_rows=table_counts,
        bootstrap_group_draws=draws, **control_counts, protocol_sha256=PROTOCOL_SHA,
        verifier_sha256=sha(Path(__file__)), inputs_sha256=hashes,
        artifact_sha256={p.name: sha(p) for p in artifacts})
    (OUT/'independent_verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if not k.endswith('sha256')}, indent=2))


if __name__ == '__main__':
    main()
