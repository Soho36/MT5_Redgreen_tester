"""Independent verification of the downtrend crystal-ball study.

Rebuilds zigzag pivots with a vectorized segment search, masks from explicit
session ranges, ledger partitions, drawdowns, every circular shift and the
protocol decision, then compares them with the saved outputs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / 'Reports/rtl_downtrend_oracle_20261024'
SOURCE = ROOT / 'Reports/rtl_price_structure_20261024'
PROTOCOL = ROOT / 'docs/baseline/rtl-downtrend-oracle/PROTOCOL.md'
ROLLS = Path(r'F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_rolls.csv')
EXPECTED_PROTOCOL = 'a39d490acc8897adf206da557c1786d07adfeef1fb209ba3d6e5d3c73afa2ffa'
SIZES = (.02, .03, .05, .10)
DELAYS = (0, 1, 2, 3, 5, 10, 20)
ERAS = {'2016-19': ('2016-01-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01')}


def sha(path, normalize=False):
    data = Path(path).read_bytes()
    return hashlib.sha256(data.replace(b'\r\n', b'\n') if normalize else data).hexdigest()


def last_index(values, target):
    return int(np.flatnonzero(values == target)[-1])


def pivots(c, x):
    """Vectorized alternative: search each leg with running extremes."""
    n = len(c)
    running_high, running_low = np.maximum.accumulate(c), np.minimum.accumulate(c)
    down = np.flatnonzero(c <= running_high*(1-x))
    up = np.flatnonzero(c >= running_low*(1+x))
    if not len(down) and not len(up):
        return []
    segments = []
    if len(down) and (not len(up) or down[0] <= up[0]):
        i = int(down[0])
        state, current = -1, dict(peak=last_index(c[:i+1], running_high[i]), stop_confirm=i)
    else:
        i, state = int(up[0]), 1
    while True:
        tail = c[i:]
        if state == -1:
            low = np.minimum.accumulate(tail)
            hits = np.flatnonzero(tail >= low*(1+x))
            if not len(hits):
                segments.append(dict(current, trough=i+last_index(tail, low[-1]), resume_confirm=None, censored=True))
                return segments
            k = i+int(hits[0])
            segments.append(dict(current, trough=i+last_index(c[i:k], low[hits[0]-1]), resume_confirm=k, censored=False))
            i, state = k, 1
        else:
            high = np.maximum.accumulate(tail)
            hits = np.flatnonzero(tail <= high*(1-x))
            if not len(hits):
                return segments
            k = i+int(hits[0])
            current = dict(peak=i+last_index(c[i:k], high[hits[0]-1]), stop_confirm=k)
            i, state = k, -1
            if k == n:
                return segments


def adjusted(daily, switches):
    """Returns with each switch-day return replaced by close/open, anchored on the last raw close."""
    ratio = daily.close/daily.close.shift()
    for switch in switches:
        ratio.loc[switch] = daily.close.loc[switch]/daily.open.loc[switch]
    growth = ratio.iloc[1:].to_numpy()
    values = np.empty(len(daily))
    values[-1] = daily.close.iloc[-1]
    for position in range(len(daily)-2, -1, -1):
        values[position] = values[position+1]/growth[position]
    return values


def explicit_mask(segments, sessions, rule):
    chosen = set()
    for s in segments:
        if rule == 'live_zigzag':
            stop = len(sessions)-1 if s['censored'] else s['resume_confirm']
            chosen.update(range(s['stop_confirm']+1, stop+1))
        else:
            d = int(rule[len('oracle_d'):])
            chosen.update(range(s['peak']+1+d, s['trough']+d+1))
    return np.array([position in chosen for position in range(len(sessions))])


def daily_dd(values):
    peak = balance = worst = 0.
    for value in values:
        balance += value
        peak = max(peak, balance)
        worst = max(worst, peak-balance)
    return worst


def main():
    checks = {}
    provenance = json.loads((STUDY/'provenance.json').read_text(encoding='utf-8'))
    prior = json.loads((SOURCE/'provenance.json').read_text(encoding='utf-8'))
    checks['protocol_unchanged'] = sha(PROTOCOL, True) == EXPECTED_PROTOCOL == provenance['protocol_sha256_crlf_normalized']
    checks['inputs_match_price_structure'] = all(sha(SOURCE/name) == prior['outputs_sha256'][name]
                                                 for name in ('trades.csv', 'features_d1_20.csv'))
    checks['rolls_match'] = sha(ROLLS) == prior['inputs_sha256'][str(ROLLS)]
    checks['outputs_match_provenance'] = all(sha(STUDY/name) == digest for name, digest in provenance['outputs_sha256'].items())

    daily = pd.read_csv(SOURCE/'features_d1_20.csv', usecols=['bar_time', 'open', 'close'],
                        parse_dates=['bar_time'], index_col='bar_time')
    daily = daily.loc[daily.index <= '2026-09-30']
    rolls = pd.read_csv(ROLLS, parse_dates=['date'])
    changed = rolls.symbol != rolls.symbol.shift()
    switches = [d for d in rolls.loc[changed, 'date'].iloc[1:] if d <= daily.index[-1]]
    sessions = daily.index
    closes = {'roll_adjusted': adjusted(daily, switches), 'raw': daily.close.to_numpy(dtype=float)}
    checks['roll_switches'] = len(switches) == provenance['roll_switches']

    saved_segments = pd.read_csv(STUDY/'segments.csv')
    masks = pd.read_csv(STUDY/'masks.csv', parse_dates=['session'], index_col='session')
    checks['mask_sessions'] = masks.index.equals(sessions)
    segment_ok, mask_ok, built = True, True, {}
    for series, c in closes.items():
        for x in SIZES:
            mine = pivots(c, x)
            saved = saved_segments.loc[saved_segments.series.eq(series) & np.isclose(saved_segments['size'], x)]
            fields = ['peak', 'stop_confirm', 'trough']
            segment_ok &= len(mine) == len(saved) and all(
                [m[f] for f in fields] == [int(v) for v in row[fields]] and m['censored'] == bool(row.censored)
                and (m['resume_confirm'] is None) == pd.isna(row.resume_confirm)
                and (m['resume_confirm'] is None or m['resume_confirm'] == int(row.resume_confirm))
                for m, (_, row) in zip(mine, saved.iterrows()))
            for m in mine:   # zigzag properties: each leg is at least x
                segment_ok &= c[m['trough']] <= c[m['peak']]*(1-x)
            for rule in [f'oracle_d{d}' for d in DELAYS]+['live_zigzag']:
                mask = explicit_mask(mine, sessions, rule)
                built[(series, x, rule)] = mask
                mask_ok &= np.array_equal(mask, masks[f'{series}|{x}|{rule}'].to_numpy())
    checks['segments_reproduced'] = bool(segment_ok)
    checks['masks_reproduced'] = bool(mask_ok)

    trades = pd.read_csv(SOURCE/'trades.csv', usecols=['session', 'net_dollars', 'net_r', 'holding_minutes', 'era', 'primary'],
                         parse_dates=['session'])
    trades = trades.loc[trades.primary]
    checks['primary_counts'] = trades.groupby('era').size().to_dict() == {'2016-19': 6167, '2020-26': 10501}
    rules = pd.read_csv(STUDY/'rules.csv')
    rows_ok, shift_ok, decision_rows = True, True, []
    for era, (start, stop) in ERAS.items():
        calendar = sessions[(sessions >= start) & (sessions < stop)]
        part = trades.loc[trades.era.eq(era)]
        position = sessions.get_indexer(part.session)
        pnl = part.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.).to_numpy()
        base = part.net_dollars.sum()
        for (series, x, rule), mask in built.items():
            row = rules.loc[rules.era.eq(era) & rules.series.eq(series) & np.isclose(rules['size'], x) & rules.rule.eq(rule)].iloc[0]
            skipped = mask[position]
            kept = part.loc[~skipped]
            era_mask = mask[sessions.get_indexer(calendar)]
            kept_curve = pnl*~era_mask
            values = [len(part), int(skipped.sum()), base, kept.net_dollars.sum(), part.loc[skipped].net_dollars.sum(),
                      kept.net_r.mean(), int(era_mask.sum()), daily_dd(kept_curve)]
            saved = [row.trades, row.skipped_trades, row.baseline_net_dollars, row.retained_net_dollars,
                     row.skipped_net_dollars, row.retained_mean_r, row.skipped_sessions, row.retained_daily_dd]
            rows_ok &= np.allclose(values, saved, atol=1e-6, rtol=0)
            nets = np.array([(pnl*~np.roll(era_mask, k)).sum() for k in range(len(calendar))])
            p975 = float(np.quantile(nets, .975))
            shift_ok &= np.isclose(p975, row.shift_net_p975, atol=1e-6) and np.isclose(
                (nets >= kept_curve.sum()-1e-9).mean(), row.share_shifts_net_at_least_rule)
            decision_rows.append(dict(era=era, series=series, size=x, rule=rule,
                                      passes=bool(kept_curve.sum() > base and kept_curve.sum() > p975)))
    checks['ledger_partitions_and_drawdowns'] = bool(rows_ok)
    checks['all_circular_shifts_recomputed'] = bool(shift_ok)
    frame = pd.DataFrame(decision_rows)
    worthwhile = {}
    for series in closes:
        part = frame.loc[frame.series.eq(series)]
        late = part.loc[part.rule.isin([f'oracle_d{d}' for d in DELAYS if d >= 3]+['live_zigzag'])]
        both = late.groupby(['size', 'rule']).passes.all()
        worthwhile[series] = bool(both.any())
    decision = json.loads((STUDY/'decision.json').read_text(encoding='utf-8'))
    checks['decision_reproduced'] = (worthwhile['roll_adjusted'] == decision['summary']['further_downtrend_research_worthwhile']
                                     and (worthwhile['roll_adjusted'] == worthwhile['raw']) == decision['summary']['raw_series_agrees'])
    result = dict(all_passed=all(checks.values()), checks=checks, verified_rules=len(rules),
                  independent_methods=['vectorized zigzag leg search', 'explicit session-range masks',
                                       'return-based roll adjustment', 'per-shift np.roll loop', 'loop drawdown'])
    (STUDY/'independent_verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    assert result['all_passed']


if __name__ == '__main__':
    main()
