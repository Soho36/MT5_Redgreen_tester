"""Execute the frozen RTL daily/M30 price-structure exploratory study.

No strategy changes: completed-price labels and counterfactual ledger omission.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_rtl_market_regimes as prior

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / 'Reports/rtl_price_structure_20261024'
PROTOCOL = ROOT / 'docs/baseline/rtl-price-structure/PROTOCOL.md'
PROTOCOL_SHA256 = 'dcde54820c8f914b64f5e51d801c7b6a34e9d5ead3b0734d92d273cb829e2729'
SOURCE = prior.STUDY / 'trades.csv'
SOURCE_PROVENANCE = prior.STUDY / 'provenance.json'
GROUPS = ('low_eff_high_overlap', 'low_eff_other_overlap',
          'other_eff_high_overlap', 'other_eff_other_overlap')
NAMED = ('low_eff_high_overlap_high_wick', 'high_overlap_high_wick')
WINDOWS = (10, 20, 40)
TIMEFRAMES = ('d1', 'm30')
ERAS = prior.ERAS
SEED, BOOTSTRAP_DRAWS, SHIFT_DRAWS = 20261024, 10000, 2000


def build_features(ohlc, n, switches=(), timeframe='m30'):
    """Features end at each observed completed bar; no synthetic gap bars."""
    assert n >= 2 and timeframe in TIMEFRAMES
    bars = ohlc.sort_index().copy()
    assert bars.index.is_unique and bars.index.is_monotonic_increasing
    assert np.isfinite(bars[['open', 'high', 'low', 'close']]).all().all()
    assert (bars.high >= bars[['open', 'close', 'low']].max(axis=1)).all()
    assert (bars.low <= bars[['open', 'close', 'high']].min(axis=1)).all()
    out = bars.copy()
    out.index.name = 'bar_time'
    changes = bars.close.diff().abs()
    total = changes.rolling(n, min_periods=n).sum()
    out['efficiency'] = (bars.close-bars.close.shift(n)).abs().div(total).where(total != 0, 0)
    intersection = (np.minimum(bars.high, bars.high.shift())-np.maximum(bars.low, bars.low.shift())).clip(lower=0)
    union = np.maximum(bars.high, bars.high.shift())-np.minimum(bars.low, bars.low.shift())
    pair = intersection.div(union).where(union != 0, 1)
    out['overlap'] = pair.rolling(n-1, min_periods=n-1).mean()
    width = bars.high-bars.low
    wick = (1-(bars.close-bars.open).abs().div(width)).where(width != 0, 0)
    out['wick'] = wick.rolling(n, min_periods=n).mean()
    out['wick80_fraction'] = wick.ge(.8).rolling(n, min_periods=n).mean()
    out['history_start'] = bars.index.to_series().shift(n)
    out['last_bar_time'] = bars.index
    out['available_at'] = bars.index+(pd.Timedelta(days=1) if timeframe == 'd1' else pd.Timedelta(minutes=30))
    out['valid'] = out[['efficiency', 'overlap', 'wick', 'history_start']].notna().all(axis=1)
    roll = pd.Series(bars.index.isin(pd.DatetimeIndex(switches)), index=bars.index)
    out['switch_bar'] = roll
    out['roll_clean'] = roll.rolling(n+1, min_periods=n+1).sum().eq(0) & out.valid
    return out


def classify_features(features, cutoffs):
    out = features.copy()
    out['low_eff'] = out.efficiency.le(cutoffs['efficiency_low']) & out.valid
    out['high_overlap'] = out.overlap.ge(cutoffs['overlap_high']) & out.valid
    out['high_wick'] = out.wick.ge(cutoffs['wick_high']) & out.valid
    out['group'] = np.where(out.low_eff, 'low_eff_', 'other_eff_') + np.where(out.high_overlap, 'high_overlap', 'other_overlap')
    out.loc[~out.valid, 'group'] = 'warmup'
    return out


def label_trades(trades, features, timeframe, n):
    """As-of labels at submission, including a just-completed signal bar."""
    columns = ['available_at', 'last_bar_time', 'history_start', 'efficiency', 'overlap',
               'wick', 'wick80_fraction', 'valid', 'roll_clean', 'low_eff', 'high_overlap', 'high_wick', 'group']
    right = features[columns].sort_values('available_at').reset_index(drop=True)
    prefix = f'{timeframe}_{n}_'
    right = right.rename(columns={name: prefix+name for name in columns})
    ordering = ['submitted', 'ticket'] if 'ticket' in trades else ['submitted']
    result = pd.merge_asof(trades.sort_values(ordering, kind='stable'), right,
                           left_on='submitted', right_on=prefix+'available_at', direction='backward',
                           allow_exact_matches=True)
    assert (result[prefix+'available_at'] <= result.submitted).all()
    if timeframe == 'd1':
        assert (result[prefix+'last_bar_time'] < result.submitted.dt.normalize()).all()
    else:
        assert (result[prefix+'last_bar_time']+pd.Timedelta(minutes=30) <= result.submitted).all()
    return result


def selected_mask(trades, prefix, group):
    if group == 'all':
        return pd.Series(True, index=trades.index)
    if group == NAMED[0]:
        return trades[prefix+'group'].eq(GROUPS[0]) & trades[prefix+'high_wick']
    if group == NAMED[1]:
        return trades[prefix+'high_overlap'] & trades[prefix+'high_wick']
    return trades[prefix+'group'].eq(group)


def metrics(trades, calendar, prefix):
    result = prior.metrics(trades, calendar)
    result.update(planned_risk_total=float(trades.initial_risk_dollars.sum()),
                  positive_net_dollars=float(trades.net_dollars.clip(lower=0).sum()),
                  negative_net_dollars=float(trades.net_dollars.clip(upper=0).sum()))
    for field in ('efficiency', 'overlap', 'wick', 'wick80_fraction'):
        result['mean_'+field] = float(trades[prefix+field].mean())
    result['adequate_coverage'] = bool(result['trades'] >= 200 and result['active_weeks'] >= 30)
    return result


def daily_curve(trades, calendar):
    return trades.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.)


def bootstrap(trades, calendar, specifications, rng):
    """Shared week draws for all overlapping subsets and their complements."""
    first = calendar[0]-pd.Timedelta(days=calendar[0].dayofweek)
    last = calendar[-1]-pd.Timedelta(days=calendar[-1].dayofweek)
    weeks = pd.date_range(first, last, freq='7D')
    arrays = []
    labels = [('all', 20, 'all', pd.Series(True, index=trades.index))] + specifications
    for _, _, _, mask in labels:
        values = trades.loc[mask].groupby('week_start').net_r.agg(['sum', 'count']).reindex(weeks, fill_value=0)
        arrays.append(values.to_numpy())
    data = np.stack(arrays, axis=1)
    starts = rng.integers(0, len(weeks), size=(BOOTSTRAP_DRAWS, math.ceil(len(weeks)/4)))
    samples = ((starts[:, :, None]+np.arange(4)) % len(weeks)).reshape(BOOTSTRAP_DRAWS, -1)[:, :len(weeks)]
    sums = np.zeros((BOOTSTRAP_DRAWS, len(labels), 2))
    for start in range(0, BOOTSTRAP_DRAWS, 100):
        sums[start:start+100] = data[samples[start:start+100]].sum(axis=1)
    results = []
    for j, (timeframe, n, group, mask) in enumerate(labels[1:], start=1):
        denominator = sums[:, j, 1]
        complement_n = sums[:, 0, 1]-denominator
        means = np.divide(sums[:, j, 0], denominator, out=np.full(BOOTSTRAP_DRAWS, np.nan), where=denominator > 0)
        complement_mean = np.divide(sums[:, 0, 0]-sums[:, j, 0], complement_n,
                                    out=np.full(BOOTSTRAP_DRAWS, np.nan), where=complement_n > 0)
        differences = means-complement_mean
        selected, other = trades.loc[mask], trades.loc[~mask]
        row = dict(timeframe=timeframe, window=n, group=group, trades=len(selected),
                   active_weeks=int(selected.week_start.nunique()), net_mean_r=float(selected.net_r.mean()),
                   complement_trades=len(other), complement_net_mean_r=float(other.net_r.mean()),
                   difference_net_r=float(selected.net_r.mean()-other.net_r.mean()),
                   bootstrap_valid_mean_draws=int(np.isfinite(means).sum()),
                   bootstrap_valid_difference_draws=int(np.isfinite(differences).sum()))
        for name, values in (('mean_net_r', means), ('difference_net_r', differences)):
            finite = values[np.isfinite(values)]
            for suffix, alpha in (('95', .05), ('97_5', .025)):
                if suffix == '97_5' and group != GROUPS[0]:
                    continue
                low, high = np.quantile(finite, [alpha/2, 1-alpha/2], method='linear') if len(finite) else (np.nan, np.nan)
                row[f'{name}_ci{suffix}_low'] = float(low)
                row[f'{name}_ci{suffix}_high'] = float(high)
        results.append(row)
    metadata = dict(draws=BOOTSTRAP_DRAWS, block_weeks=4, circular=True, calendar_weeks=len(weeks),
                    blocks_per_draw=math.ceil(len(weeks)/4), trimmed_weeks=len(weeks),
                    paired_across_all_timeframes_and_subsets=True)
    return results, metadata


def max_dd(pnl):
    equity = np.r_[0., np.cumsum(pnl)]
    return float(np.max(np.maximum.accumulate(equity)-equity))


def omission_and_controls(trades, calendar, timeframe, group, rng):
    prefix = f'{timeframe}_20_'
    trades = trades.sort_values(['entry_time', 'ticket'], kind='stable')
    skip = selected_mask(trades, prefix, group).to_numpy(dtype=bool)
    retained = trades.loc[~skip]
    omitted = trades.loc[skip]
    holding_fraction = retained.holding_minutes.sum()/trades.holding_minutes.sum()
    fractions = dict(retained_holding_fraction=float(holding_fraction),
                     retained_trade_fraction=len(retained)/len(trades),
                     retained_planned_risk_fraction=float(retained.initial_risk_dollars.sum()/trades.initial_risk_dollars.sum()),
                     skip_trades=int(skip.sum()), skipped_loss_dollars_avoided=float(-omitted.net_dollars.clip(upper=0).sum()),
                     skipped_profit_dollars_missed=float(omitted.net_dollars.clip(lower=0).sum()),
                     skipped_net_dollars=float(omitted.net_dollars.sum()))
    fractions.update(retained_risk_fraction=fractions['retained_planned_risk_fraction'],
                     skipped_trades=fractions['skip_trades'],
                     losses_avoided=fractions['skipped_loss_dollars_avoided'],
                     profits_missed=fractions['skipped_profit_dollars_missed'])
    scaled = trades.copy()
    # Fractional whole-ledger scaling is a diagnostic portfolio, with risk and cost scaled too.
    for column in ('net_dollars', 'trade_profit', 'initial_risk_dollars', 'fill_risk_dollars',
                   'stress1_net_dollars', 'stress2_net_dollars', 'holding_minutes'):
        scaled[column] *= holding_fraction
    rows, sessions = [], []
    for name, frame in (('baseline', trades), ('omitted', retained), ('static_holding_scaled', scaled)):
        values = metrics(frame, calendar, prefix)
        values.update(fractions)
        values['pnl_scale'] = float(holding_fraction) if name == 'static_holding_scaled' else 1.
        rows.append(dict(timeframe=timeframe, window=20, group=group, subset=group, curve=name, **values))
        sessions.extend(dict(timeframe=timeframe, window=20, group=group, subset=group, curve=name,
                             session=str(date.date()), net_dollars=float(pnl))
                        for date, pnl in daily_curve(frame, calendar).items())
    pnl = trades.net_dollars.to_numpy()
    holding = trades.holding_minutes.to_numpy()/60
    day_ids = calendar.get_indexer(trades.session)
    assert (day_ids >= 0).all()
    target_holding = float(retained.holding_minutes.sum()/60)
    offsets = rng.integers(0, len(trades), size=SHIFT_DRAWS)
    draws = []
    for draw, offset in enumerate(offsets):
        keep = ~np.roll(skip, int(offset))
        kept_pnl = float(pnl[keep].sum())
        hours = float(holding[keep].sum())
        daily = np.bincount(day_ids[keep], weights=pnl[keep], minlength=len(calendar))
        dd = max_dd(daily)
        scale = target_holding/hours if hours else np.nan
        draws.append(dict(timeframe=timeframe, window=20, group=group, subset=group, draw=draw, offset=int(offset),
                          retained_trades=int(keep.sum()), net_dollars=kept_pnl, daily_close_dd=dd,
                          holding_hours=hours, exposure_scale=float(scale),
                          exposure_scaled_net_dollars=float(kept_pnl*scale),
                          exposure_scaled_daily_close_dd=float(dd*scale)))
    frame = pd.DataFrame(draws)
    actual_net = float(retained.net_dollars.sum())
    actual_dd = max_dd(daily_curve(retained, calendar).to_numpy())
    summary = dict(timeframe=timeframe, window=20, group=group, subset=group, draws=SHIFT_DRAWS,
                   distinct_offsets=int(frame.offset.nunique()), actual_net_dollars=actual_net,
                   actual_daily_close_dd=actual_dd, actual_holding_hours=target_holding, **fractions)
    for field in ('net_dollars', 'daily_close_dd', 'holding_hours', 'exposure_scaled_net_dollars', 'exposure_scaled_daily_close_dd'):
        for suffix, q in (('p025', .025), ('p50', .5), ('p975', .975)):
            summary[f'{field}_{suffix}'] = float(frame[field].quantile(q, interpolation='linear'))
    summary['raw_fraction_net_at_least_actual'] = float(frame.net_dollars.ge(actual_net-1e-9).mean())
    summary['raw_fraction_dd_at_most_actual'] = float(frame.daily_close_dd.le(actual_dd+1e-9).mean())
    summary['matched_fraction_net_at_least_actual'] = float(frame.exposure_scaled_net_dollars.ge(actual_net-1e-9).mean())
    summary['matched_fraction_dd_at_most_actual'] = float(frame.exposure_scaled_daily_close_dd.le(actual_dd+1e-9).mean())
    return rows, sessions, draws, summary


def write_csv(name, rows):
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    frame.to_csv(STUDY/name, index=False, float_format='%.15g')


def check_provenance():
    assert prior.digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol hash mismatch: no outcomes computed'
    source = json.loads(SOURCE_PROVENANCE.read_text(encoding='utf-8'))
    paths = (PROTOCOL, SOURCE, SOURCE_PROVENANCE, prior.RAW, prior.STATS, prior.HTML,
             prior.INI, prior.COMPLETION, prior.MANIFEST, prior.M30, prior.MINUTES, prior.ROLLS,
             Path(prior.__file__), Path(__file__))
    hashes = {str(path): prior.digest(path) for path in paths}
    assert hashes[str(SOURCE)] == source['outputs_sha256']['trades.csv']
    for path in (prior.RAW, prior.STATS, prior.HTML, prior.INI, prior.COMPLETION,
                 prior.MANIFEST, prior.M30, prior.MINUTES, prior.ROLLS, Path(prior.__file__)):
        assert hashes[str(path)] == source['inputs_sha256'][str(path)], f'Changed original source: {path}'
    return hashes


def load_trades():
    columns = ['submitted', 'requested_price', 'original_sl', 'ticket', 'entry_time', 'fill_price',
               'exit_time', 'exit_price', 'trade_profit', 'exit_comment', 'candle_range', 'red_run',
               'location', 'session', 'initial_risk_dollars', 'fill_risk_dollars', 'fill_minus_request_dollars',
               'gross_r', 'net_dollars', 'net_r', 'commission_r', 'holding_minutes',
               'stress1_net_dollars', 'stress1_net_r', 'stress2_net_dollars', 'stress2_net_r',
               'year', 'week_start', 'era', 'primary']
    frame = pd.read_csv(SOURCE, usecols=columns,
                        parse_dates=['submitted', 'entry_time', 'exit_time', 'session', 'week_start'])
    assert len(frame) == 25833 and frame.ticket.is_unique
    assert np.allclose(frame.net_dollars, frame.trade_profit-prior.COST, atol=1e-9)
    assert np.allclose(frame.net_r, frame.net_dollars/frame.initial_risk_dollars, atol=1e-12)
    assert np.allclose(frame.initial_risk_dollars, (frame.requested_price-frame.original_sl)*2, atol=1e-9)
    assert np.allclose(frame.holding_minutes, (frame.exit_time-frame.entry_time).dt.total_seconds()/60, atol=1e-9)
    assert frame.loc[frame.primary].groupby('era').size().to_dict() == {'2016-19': 6167, '2020-26': 10501}
    final = frame.loc[frame.era == 'partial_endpoint']
    assert len(final) == 1 and final.iloc[0].session == pd.Timestamp('2026-10-01')
    return frame


def main():
    inputs = check_provenance()
    print('Frozen protocol and original data hashes verified.', flush=True)
    STUDY.mkdir(parents=True, exist_ok=True)
    trades = load_trades()
    m30 = pd.read_csv(prior.M30, parse_dates=['bar_time']).set_index('bar_time')
    assert (m30.index.hour >= 1).all()
    daily = m30.groupby(m30.index.normalize()).agg(open=('open', 'first'), high=('high', 'max'),
                                                 low=('low', 'min'), close=('close', 'last'))
    rolls = pd.read_csv(prior.ROLLS, parse_dates=['date'])
    switch_dates = pd.DatetimeIndex(rolls.loc[rolls.symbol.ne(rolls.symbol.shift()) & rolls.symbol.shift().notna(), 'date'])
    first_bars = pd.Series(m30.index, index=m30.index.normalize()).groupby(level=0).first()
    assert switch_dates.isin(first_bars.index).all()
    switches = {'d1': switch_dates, 'm30': pd.DatetimeIndex(first_bars.loc[switch_dates])}
    feature_frames, threshold_rows, audit = {}, [], {'all_passed': True, 'source_trade_count': len(trades)}
    for timeframe, bars in (('d1', daily), ('m30', m30)):
        for n in WINDOWS:
            features = build_features(bars, n, switches[timeframe], timeframe)
            calibration = features.loc[features.valid & (features.available_at < '2016-01-01')]
            cutoffs = dict(efficiency_low=float(calibration.efficiency.quantile(1/3, interpolation='linear')),
                           overlap_high=float(calibration.overlap.quantile(2/3, interpolation='linear')),
                           wick_high=float(calibration.wick.quantile(2/3, interpolation='linear')))
            threshold_rows.append(dict(timeframe=timeframe, window=n, **cutoffs, calibration_windows=len(calibration),
                                       calibration_first_available=str(calibration.available_at.min()),
                                       calibration_last_available=str(calibration.available_at.max())))
            features = classify_features(features, cutoffs)
            feature_frames[(timeframe, n)] = features
            features.to_csv(STUDY/f'features_{timeframe}_{n}.csv', float_format='%.15g')
            trades = label_trades(trades, features, timeframe, n)
            assert trades.loc[trades.primary, f'{timeframe}_{n}_group'].isin(GROUPS).all()
    write_csv('thresholds.csv', threshold_rows)
    write_csv('trades.csv', trades)
    print('Six calibrated feature panels and causal labels saved; computing outcomes.', flush=True)
    summaries, yearly, wick_rows, named_rows, roll_rows, coverage_rows = [], [], [], [], [], []
    session_rows, uncertainty_rows, omission_rows, placement_rows, placement_summaries = [], [], [], [], []
    bootstrap_metadata = {}
    bootstrap_rng, placement_rng = np.random.default_rng(SEED), np.random.default_rng(SEED)
    for era, (start, stop) in ERAS.items():
        part = trades.loc[trades.era == era].copy()
        calendar = daily.index[(daily.index >= start) & (daily.index < stop)]
        assert part.session.isin(calendar).all()
        specifications = []
        for timeframe in TIMEFRAMES:
            for n in WINDOWS:
                prefix = f'{timeframe}_{n}_'
                groups = GROUPS+('all',)+(NAMED if timeframe == 'm30' else ())
                for group in groups:
                    chosen = part.loc[selected_mask(part, prefix, group)]
                    row = dict(timeframe=timeframe, window=n, era=era, group=group, **metrics(chosen, calendar, prefix))
                    if group in GROUPS+('all',):
                        summaries.append(row)
                    else:
                        named_rows.append(row)
                    clean = part.loc[part[prefix+'roll_clean']]
                    roll_chosen = clean.loc[selected_mask(clean, prefix, group)]
                    roll_rows.append(dict(timeframe=timeframe, window=n, era=era, group=group,
                                          **metrics(roll_chosen, calendar, prefix)))
                    if n == 20 and group != 'all':
                        specifications.append((timeframe, n, group, selected_mask(part, prefix, group)))
                    if n == 20 and group in GROUPS+('all',):
                        session_rows.extend(dict(timeframe=timeframe, window=n, era=era, group=group, subset=group,
                                                 curve='group_contribution', session=str(date.date()), net_dollars=float(pnl))
                                            for date, pnl in daily_curve(chosen, calendar).items())
                    for year in sorted(part.year.unique()):
                        annual_calendar = calendar[calendar.year == year]
                        annual = chosen.loc[chosen.year == year]
                        yearly.append(dict(timeframe=timeframe, window=n, era=era, year=int(year),
                                           partial=bool(year == 2026), group=group, **metrics(annual, annual_calendar, prefix)))
                clean = part.loc[part[prefix+'roll_clean']]
                coverage_rows.append(dict(timeframe=timeframe, window=n, era=era, full_trades=len(part),
                                           retained_trades=len(clean), retained_fraction=len(clean)/len(part),
                                           retained_holding_fraction=float(clean.holding_minutes.sum()/part.holding_minutes.sum())))
                if n == 20:
                    for group in GROUPS:
                        for high in (False, True):
                            chosen = part.loc[part[prefix+'group'].eq(group) & part[prefix+'high_wick'].eq(high)]
                            wick_rows.append(dict(timeframe=timeframe, window=n, era=era, group=group,
                                                  wick_state='high' if high else 'other', **metrics(chosen, calendar, prefix)))
        estimates, meta = bootstrap(part, calendar, specifications, bootstrap_rng)
        uncertainty_rows.extend(dict(era=era, **row) for row in estimates)
        bootstrap_metadata[era] = meta
        for timeframe, group in (('d1', GROUPS[0]), ('m30', GROUPS[0]), ('m30', NAMED[0]), ('m30', NAMED[1])):
            rows, sessions, draws, summary = omission_and_controls(part, calendar, timeframe, group, placement_rng)
            omission_rows.extend(dict(era=era, **row) for row in rows)
            session_rows.extend(dict(era=era, **row) for row in sessions)
            placement_rows.extend(dict(era=era, **row) for row in draws)
            placement_summaries.append(dict(era=era, **summary))
        print(f'{era}: summaries, paired uncertainty, and placement controls complete.', flush=True)
    summary_frame = pd.DataFrame(summaries)
    for _, frame in summary_frame.groupby(['timeframe', 'window', 'era']):
        whole = frame.loc[frame.group == 'all'].iloc[0]
        groups = frame.loc[frame.group != 'all']
        assert groups.trades.sum() == whole.trades
        assert np.isclose(groups.net_dollars.sum(), whole.net_dollars, atol=1e-8)
    for name, rows in [('summaries.csv', summary_frame), ('yearly.csv', yearly), ('wick_summary.csv', wick_rows),
                       ('named_wick_summary.csv', named_rows), ('roll_sensitivity.csv', roll_rows),
                       ('roll_coverage.csv', coverage_rows), ('uncertainty.csv', uncertainty_rows),
                       ('omission.csv', omission_rows), ('placement_draws.csv', placement_rows),
                       ('placement_summary.csv', placement_summaries), ('session_pnl.csv', session_rows)]:
        write_csv(name, rows)
    audit.update(protocol_hash_checked_before_outcomes=True, protocol_unchanged_at_end=prior.digest(PROTOCOL) == PROTOCOL_SHA256,
                 source_hashes_match_prior=True, exact_four_group_partitions=True,
                 complete_primary_trades=int(trades.primary.sum()),
                 era_trades=trades.loc[trades.primary].groupby('era').size().to_dict(),
                 calibration='all valid completed price windows with available_at strictly before 2016-01-01; linear quantiles',
                 feature_availability={'d1': 'source date + one calendar day midnight; strictly prior dates',
                                       'm30': 'bar open + thirty minutes; asof <= actual order submission'},
                 roll_exclusion='n+1 observed bar history includes first observed bar on switch date, including oldest close',
                 bootstrap=dict(seed=SEED, eras=bootstrap_metadata),
                 placement=dict(seed=SEED, draws=SHIFT_DRAWS, rng='separate numpy.default_rng PCG64; eras chronological; D1 main, M30 main, M30 two wick subsets',
                                shift='uniform integer offsets [0,n_trades), with replacement; zero offset allowed',
                                limitation='preserves circular trade-order run lengths, not calendar durations; descriptive control'),
                 common_calendar='all observed source sessions in era; zero-PnL dates retained for all comparisons',
                 drawdown='realized closed-trade/daily balances only, includes initial zero; no intratrade MTM',
                 static_control='baseline whole-ledger PnL, costs, planned risk and holding hours scaled by candidate retained holding fraction',
                 omission='counterfactual ledger omission, not full strategy replay',
                 raw_ohlc_independent_verification='separate verifier rebuilds every M30 OHLC column from minute source')
    assert audit['protocol_unchanged_at_end']
    prior.save_json(STUDY/'audit.json', audit)
    generated = [f'features_{tf}_{n}.csv' for tf in TIMEFRAMES for n in WINDOWS] + [
        'thresholds.csv', 'trades.csv', 'summaries.csv', 'yearly.csv', 'wick_summary.csv', 'named_wick_summary.csv',
        'roll_sensitivity.csv', 'roll_coverage.csv', 'uncertainty.csv', 'omission.csv', 'placement_draws.csv',
        'placement_summary.csv', 'session_pnl.csv', 'audit.json']
    prior.save_json(STUDY/'provenance.json', dict(study='RTL completed-price structure', protocol_sha256=PROTOCOL_SHA256,
                    inputs_sha256=inputs, outputs_sha256={name: prior.digest(STUDY/name) for name in generated},
                    primary_eras=ERAS, software=dict(numpy=np.__version__, pandas=pd.__version__),
                    strategy_changed=False, baseline_mutated=False, exploratory_only=True))
    print(summary_frame.loc[(summary_frame.window == 20) & summary_frame.group.isin([GROUPS[0], 'all']),
                            ['timeframe', 'era', 'group', 'trades', 'net_dollars', 'net_mean_r']].to_string(index=False), flush=True)
    print('Study output and immutable-source provenance saved.', flush=True)


if __name__ == '__main__':
    main()
