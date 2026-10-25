"""Independent verification of the weekly signal gate.

Weekly bars, colours, signals and gate states by explicit loops; roll
adjustment by backward factor accumulation; circular shifts by prefix sums over
the gate-off runs (no FFT); ledger partitions, drawdowns and the decision.
"""
from __future__ import annotations

import bisect
import json

import numpy as np
import pandas as pd

import verify_rtl_downtrend_oracle as first

STUDY = first.ROOT / 'Reports/rtl_weekly_gate_20261025'
PROTOCOL = first.ROOT / 'docs/baseline/rtl-weekly-gate/PROTOCOL.md'
EXPECTED_PROTOCOL = '28fccc0ca54af3621c295828f1272976728633d2e24024a7e764a668e704d2f6'
M30 = first.ROOT / 'Reports/trend_rr_20261002/m30_reference.csv'
VARIANTS = (('roll_adjusted', 'touch'), ('roll_adjusted', 'week_close'),
            ('roll_adjusted', 'close_confirmed'), ('raw', 'touch'))


def adjusted_bars(raw, switch_dates):
    dates = [t.normalize() for t in raw.bar_time]
    first_bar = {d: dates.index(d) for d in switch_dates}
    gaps = {first_bar[d]: raw.open[first_bar[d]]/raw.close[first_bar[d]-1] for d in switch_dates}
    factor, running = np.empty(len(raw)), 1.
    for i in range(len(raw)-1, -1, -1):
        factor[i] = running
        if i in gaps:
            running *= gaps[i]
    out = raw.copy()
    for column in ('open', 'high', 'low', 'close'):
        out[column] = raw[column]*factor
    return out


def weeks_by_loop(bars):
    weeks = {}
    for i, row in enumerate(bars.itertuples(index=False)):
        day = row.bar_time.normalize()
        key = day-pd.Timedelta(days=day.dayofweek)
        if key not in weeks:
            weeks[key] = dict(first=i, open=row.open, high=row.high, low=row.low)
        w = weeks[key]
        w.update(last=i, close=row.close, high=max(w['high'], row.high), low=min(w['low'], row.low))
    return [weeks[k] for k in sorted(weeks)]


def gate_by_loop(bars, weeks, variant):
    events = {}
    for prev, this in zip(weeks, weeks[1:]):
        if prev['close'] == prev['open']:
            continue
        sell = prev['close'] > prev['open']
        if variant == 'close_confirmed':
            if (sell and this['close'] < prev['low']) or (not sell and this['close'] > prev['high']):
                events[this['last']] = sell
            continue
        for i in range(this['first'], this['last']+1):
            if (sell and bars.low.iat[i] < prev['low']) or (not sell and bars.high.iat[i] > prev['high']):
                events[this['last'] if variant == 'week_close' else i] = sell
                break
    off, state = np.zeros(len(bars), dtype=bool), False
    for i in range(len(bars)):
        state = events.get(i, state)
        off[i] = state
    return off


def run_shift_nets(pnl, off):
    """Exact circular shifts via prefix sums over the runs of the off mask."""
    n = len(pnl)
    prefix = np.r_[0., np.cumsum(np.r_[pnl, pnl])]
    edges = np.flatnonzero(np.diff(np.r_[0, off.astype(int), 0]))
    runs = list(zip(edges[::2], edges[1::2]-1))
    shifts = np.arange(n)
    skipped = np.zeros(n)
    for a, b in runs:
        start = (a+shifts) % n
        skipped += prefix[start+b-a+1]-prefix[start]
    return pnl.sum()-skipped


def main():
    checks = {}
    provenance = json.loads((STUDY/'provenance.json').read_text(encoding='utf-8'))
    checks['protocol_unchanged'] = first.sha(PROTOCOL, True) == EXPECTED_PROTOCOL == provenance['protocol_sha256_crlf_normalized']
    checks['outputs_match_provenance'] = all(first.sha(STUDY/n) == d for n, d in provenance['outputs_sha256'].items())
    checks['m30_unchanged'] = first.sha(M30) == provenance['inputs_sha256'][str(M30)]
    raw = pd.read_csv(M30, parse_dates=['bar_time'])
    raw = raw.loc[raw.bar_time.dt.normalize() <= '2026-09-30'].reset_index(drop=True)
    rolls = pd.read_csv(first.ROLLS, parse_dates=['date'])
    switch_dates = [d for d in rolls.loc[rolls.symbol != rolls.symbol.shift(), 'date'].iloc[1:] if d <= pd.Timestamp('2026-09-30')]
    prices = {'roll_adjusted': adjusted_bars(raw, switch_dates), 'raw': raw}
    saved_weeks = pd.read_csv(STUDY/'weeks.csv')
    week_ok = True
    gates = {}
    for series, variant in VARIANTS:
        weeks = weeks_by_loop(prices[series])
        if variant == 'touch':
            saved = saved_weeks.loc[saved_weeks.series.eq(series)]
            week_ok &= len(saved) == len(weeks) and np.allclose(
                saved[['open', 'high', 'low', 'close']].to_numpy(),
                [[w['open'], w['high'], w['low'], w['close']] for w in weeks], rtol=1e-12)
        gates[(series, variant)] = gate_by_loop(prices[series], weeks, variant)
    checks['weekly_bars_reproduced'] = bool(week_ok)
    labels = pd.read_csv(STUDY/'trade_labels.csv', parse_dates=['submitted'])
    closes = list(raw.bar_time+pd.Timedelta(minutes=30))
    bars = np.array([bisect.bisect_right(closes, s)-1 for s in labels.submitted])
    checks['submission_bars_reproduced'] = bool(np.array_equal(bars, labels.bar.to_numpy()))
    checks['trade_labels_reproduced'] = all(np.array_equal(off[bars], labels[f'skip|{s}|{v}'].to_numpy())
                                            for (s, v), off in gates.items())
    trades = pd.read_csv(first.SOURCE/'trades.csv', usecols=['ticket', 'session', 'net_dollars', 'net_r', 'era', 'primary'],
                         parse_dates=['session'])
    trades = trades.loc[trades.primary].set_index('ticket').loc[labels.ticket].reset_index()
    trades['bar'] = bars
    rules = pd.read_csv(STUDY/'rules.csv')
    daily = pd.read_csv(first.SOURCE/'features_d1_20.csv', usecols=['bar_time'], parse_dates=['bar_time']).bar_time
    rows_ok, shift_ok, verdict = True, True, {}
    for era, (start, stop) in first.ERAS.items():
        calendar = daily[(daily >= start) & (daily < stop)]
        part = trades.loc[trades.era.eq(era)]
        era_bars = [i for i, c in enumerate(closes) if pd.Timestamp(start) <= c < pd.Timestamp(stop)]
        pnl = part.groupby('bar').net_dollars.sum().reindex(era_bars, fill_value=0.).to_numpy()
        session_pnl = part.groupby('session').net_dollars.sum()
        base, base_r = part.net_dollars.sum(), part.net_r.mean()
        for (series, variant), off in gates.items():
            row = rules.loc[rules.era.eq(era) & rules.series.eq(series) & rules.variant.eq(variant)].iloc[0]
            skip = off[part.bar.to_numpy()]
            kept = part.loc[~skip]
            curve = kept.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.).to_numpy()
            values = [int(skip.sum()), base, kept.net_dollars.sum(), kept.net_r.mean(), first.daily_dd(curve)]
            saved = [row.skipped_trades, row.baseline_net_dollars, row.retained_net_dollars, row.retained_mean_r, row.retained_daily_dd]
            rows_ok &= np.allclose(values, saved, atol=1e-6, rtol=0) and np.isclose(session_pnl.sum(), base)
            nets = run_shift_nets(pnl, off[era_bars])
            shift_ok &= np.isclose(nets[0], kept.net_dollars.sum(), atol=1e-6) and np.isclose(
                np.quantile(nets, .975), row.shift_net_p975, atol=1e-6)
            verdict.setdefault((series, variant), []).append(
                dict(promising=bool(kept.net_dollars.sum() > base and kept.net_r.mean() > base_r
                                    and kept.net_dollars.sum() > np.quantile(nets, .975)),
                     positive=bool(kept.net_dollars.sum() > base)))
    checks['ledger_partitions_and_drawdowns'] = bool(rows_ok)
    checks['all_circular_shifts_recomputed'] = bool(shift_ok)
    promising = all(v['promising'] for v in verdict[VARIANTS[0]])
    robust = all(v['positive'] for key in VARIANTS[1:] for v in verdict[key])
    label = 'promising' if promising and robust else 'fragile' if promising else 'not promising'
    decision = json.loads((STUDY/'decision.json').read_text(encoding='utf-8'))
    checks['decision_reproduced'] = decision['primary']['label'] == label
    result = dict(all_passed=all(checks.values()), checks=checks, verified_rows=len(rules))
    (STUDY/'independent_verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    assert result['all_passed']


if __name__ == '__main__':
    main()
