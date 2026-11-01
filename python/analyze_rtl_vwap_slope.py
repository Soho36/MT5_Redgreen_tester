"""Descriptive RTL rising-VWAP filter; fixed design in SLOPE_PROTOCOL.md."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CROSS = ROOT / 'Reports/rtl_vwap_cross_20261027'
OUT = ROOT / 'Reports/rtl_vwap_slope_20261101'
DOC = ROOT / 'docs/baseline/rtl-vwap'
PERIODS = {'2016-19': ('2016-01-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01'),
           '2016-26': ('2016-01-01', '2026-10-01'), '2010-15': ('2010-01-01', '2016-01-01')}
FROZEN = {'features_NQ.csv': 'd88bbd10f82df2b6bb428b418b5cbbdb3c13f8baea3fa2d6ae491656d3bc92d6',
          'trades_NQ.csv': '1c8537e0eca9de7a0470e9e6a9668687d3a09c0387c664b182c6d0f6f7ddaf3e',
          'calendars.csv': '64be3ff61751cc8237c82f5c4adad9e70e73f698d59715195c5e8586b0866141'}
MAIN = ('baseline', 'orange', 'rising', 'orange_rising')


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def slope_features(f):
    """Causal one-bar slope, no A20 requirement; expects chronological features."""
    assert f.bar_time.is_unique and f.bar_time.is_monotonic_increasing
    prev = f.shift(1)
    same = f.feature_session.eq(prev.feature_session)
    contiguous = f.bar_time.sub(prev.bar_time).eq(pd.Timedelta(minutes=30))
    finite = np.isfinite(f.vwap) & np.isfinite(prev.vwap)
    available = f.vwap_available.eq(True) & prev.vwap_available.eq(True)
    positive = f.cum_volume.gt(prev.cum_volume) & prev.cum_volume.gt(0)
    reason = np.select([~same, ~contiguous, ~(finite & available), ~positive],
                       ['session_start', 'time_gap', 'unavailable_vwap', 'no_added_volume'], default='')
    delta = f.vwap.sub(prev.vwap).where(reason == '')
    state = np.select([delta.gt(0), delta.lt(0), delta.eq(0)], ['up', 'down', 'flat'], default='unknown')
    return pd.DataFrame(dict(slope_delta=delta, slope_state=state, slope_reason=reason,
                             slope_per_a20=(delta / f.a20).where(f.a20.gt(0))))


def metrics(t, calendar, scale=1.):
    pnl = t.net_dollars * scale
    daily = pnl.groupby(t.session).sum().reindex(calendar, fill_value=0.)
    equity = np.r_[0., daily.cumsum().to_numpy()]
    dd = float((np.maximum.accumulate(equity) - equity).max())
    loss = -pnl[pnl < 0].sum()
    return dict(trades=len(t), net_dollars=float(pnl.sum()), gross_mean_r=float(t.gross_r.mean()),
                net_mean_r=float(t.net_r.mean()), win_rate=float(pnl.gt(0).mean()),
                profit_factor=float(pnl[pnl > 0].sum() / loss) if loss else np.nan,
                daily_close_dd=dd, net_over_dd=float(pnl.sum() / dd) if dd else np.nan,
                planned_risk=float(t.initial_risk_dollars.sum()) * scale, scale=scale)


def masks(t):
    known, up, orange = t.slope_state.ne('unknown'), t.slope_state.eq('up'), t.orange_keep
    return dict(baseline=np.ones(len(t), bool), orange=orange, rising=up, orange_rising=orange & up,
                known_baseline=known, known_orange=known & orange)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, digest in FROZEN.items():
        assert sha(CROSS / name) == digest, name
    assert json.loads((CROSS / 'independent_verification.json').read_text())['all_passed']
    inputs = [CROSS / name for name in (*FROZEN, 'summaries.csv', 'source_audit.json', 'independent_verification.json')]
    inputs += [DOC / 'SLOPE_PROTOCOL.md', Path(__file__).resolve()]
    save('input_manifest.json', {str(p.relative_to(ROOT)): sha(p) for p in inputs})
    f = pd.read_csv(CROSS / 'features_NQ.csv', float_precision='round_trip')
    t = pd.read_csv(CROSS / 'trades_NQ.csv', float_precision='round_trip', low_memory=False)
    for frame in (f, t):
        for col in ('bar_time', 'available_at', 'feature_session', 'session', 'submitted'):
            if col in frame:
                frame[col] = pd.to_datetime(frame[col])
    f = f.sort_values('bar_time').reset_index(drop=True)
    features = pd.concat([f, slope_features(f)], axis=1)
    t = t.loc[t.session < '2026-10-01'].copy()
    assert t.ticket.is_unique and t.close.lt(t.open).all()
    assert np.allclose(t.high, t.requested_price, rtol=0, atol=1e-9)
    assert np.allclose(t.low, t.original_sl, rtol=0, atol=1e-9)
    joined = pd.merge_asof(t[['ticket', 'submitted']].sort_values(['submitted', 'ticket']),
                           features, left_on='submitted', right_on='available_at', direction='backward')
    original = t.set_index('ticket').loc[joined.ticket].reset_index()
    assert (joined.available_at <= joined.submitted).all()
    assert original.bar_time.equals(joined.bar_time)
    for col in ('open', 'high', 'low', 'close'):
        np.testing.assert_allclose(original[col], joined[col], rtol=0, atol=1e-9)
    stale = joined.feature_session.ne(joined.submitted.dt.normalize())
    joined.loc[stale, ['slope_delta', 'slope_per_a20']] = np.nan
    joined.loc[stale, 'slope_state'] = 'unknown'
    joined.loc[stale, 'slope_reason'] = 'submission_session_reset'
    t = original
    for col in ('slope_delta', 'slope_state', 'slope_reason', 'slope_per_a20'):
        t[col] = joined[col]
    orange_known = t.vwap_available & t.a20.gt(0) & t.feature_session.eq(t.session) & t.vwap.notna()
    skip = orange_known & t.close.lt(t.vwap - t.a20)
    assert np.array_equal(skip, t.distance.eq('far_below'))
    t['orange_keep'] = ~skip
    t.to_csv(OUT / 'trades.csv', index=False, float_format='%.17g')
    cal = pd.read_csv(CROSS / 'calendars.csv', parse_dates=['session'])
    cal = pd.DatetimeIndex(cal.loc[cal.instrument.eq('NQ'), 'session']).sort_values()
    old = pd.read_csv(CROSS / 'summaries.csv')
    scopes = [(n, s, e, False) for n, (s, e) in PERIODS.items()]
    scopes += [(str(y), f'{y}-01-01', min(f'{y+1}-01-01', '2026-10-01'), True) for y in range(2010, 2027)]
    summaries, annual, groups, unknown, daily, slopes = [], [], [], [], [], []
    for period, start, end, yearly in scopes:
        part = t.loc[t.session.ge(start) & t.session.lt(end)]
        days = cal[(cal >= start) & (cal < end)]
        assert part.session.isin(days).all()
        selected = masks(part)
        rows = []
        total_risk = part.initial_risk_dollars.sum()
        for policy, keep in selected.items():
            kept = part.loc[keep]
            rows.append(dict(period=period, policy=policy, **metrics(kept, days),
                             risk_fraction=kept.initial_risk_dollars.sum() / total_risk))
            if not yearly and policy in MAIN:
                d = kept.groupby('session').net_dollars.sum().reindex(days, fill_value=0.)
                daily.append(pd.DataFrame(dict(period=period, policy=policy, session=days, net_dollars=d.values)))
            if not yearly and policy in ('baseline', 'orange'):
                ref = old.loc[old.instrument.eq('NQ') & old.period.eq('pooled' if period == '2016-26' else period)
                              & old.curve.eq('baseline' if policy == 'baseline' else 'retained')].iloc[0]
                for col in ('trades', 'net_dollars', 'net_mean_r', 'daily_close_dd'):
                    assert np.isclose(rows[-1][col], ref[col], rtol=0, atol=1e-6), (period, policy, col)
        for name, target, comparator in [('rising_risk_scaled_baseline', 'rising', 'baseline'),
                                         ('combined_risk_scaled_orange', 'orange_rising', 'orange')]:
            target_risk = part.loc[selected[target], 'initial_risk_dollars'].sum()
            base = part.loc[selected[comparator]]
            scale = target_risk / base.initial_risk_dollars.sum()
            rows.append(dict(period=period, policy=name, **metrics(base, days, scale), risk_fraction=target_risk / total_risk))
        (annual if yearly else summaries).extend(rows)
        if yearly:
            continue
        for scope in ('all', 'orange_kept', 'orange_skipped'):
            p = part if scope == 'all' else part.loc[part.orange_keep if scope == 'orange_kept' else ~part.orange_keep]
            for state in ('up', 'down', 'flat', 'unknown'):
                groups.append(dict(period=period, scope=scope, state=state,
                                   **metrics(p.loc[p.slope_state.eq(state)], days)))
        for reason, p in part.loc[part.slope_state.eq('unknown')].groupby('slope_reason'):
            unknown.append(dict(period=period, reason=reason, **metrics(p, days)))
        for col in ('slope_delta', 'slope_per_a20'):
            x = part[col].dropna()
            slopes.append(dict(period=period, measure=col, count=len(x), minimum=x.min(), median=x.median(),
                               maximum=x.max(), near_zero_nonflat=int((x.abs().le(1e-9) & x.ne(0)).sum())))
        all_groups = [r for r in groups if r['period'] == period and r['scope'] == 'all']
        assert sum(r['trades'] for r in all_groups) == len(part)
        assert np.isclose(sum(r['net_dollars'] for r in all_groups), part.net_dollars.sum(), rtol=0, atol=1e-7)
    for name, data in [('summaries', summaries), ('annual', annual), ('groups', groups),
                       ('unknown_reasons', unknown), ('slope_distribution', slopes)]:
        pd.DataFrame(data).to_csv(OUT / f'{name}.csv', index=False, float_format='%.17g')
    pd.concat(daily).to_csv(OUT / 'daily.csv', index=False, float_format='%.17g')
    save('source_checks.json', dict(all_passed=True, trades=len(t), exact_signal_bars=True,
         baseline_and_orange_summaries_reproduced=True, state_counts=t.slope_state.value_counts().to_dict()))
    save('output_hashes.json', {p.name: sha(p) for p in OUT.glob('*.csv')})
    print(pd.DataFrame(summaries).to_string(index=False))
    print(pd.DataFrame(groups).query("period == '2016-26'").to_string(index=False))


if __name__ == '__main__':
    main()
