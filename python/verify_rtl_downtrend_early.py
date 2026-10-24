"""Independent verification of the early-signal crystal-ball addendum.

Reuses the first verifier's separately written zigzag and roll adjustment, then
rebuilds early masks from explicit session ranges, ledger partitions,
drawdowns, every circular shift and the addendum decision.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import verify_rtl_downtrend_oracle as first

STUDY = first.ROOT / 'Reports/rtl_downtrend_early_20261025'
ADDENDUM = first.ROOT / 'docs/baseline/rtl-downtrend-oracle/EARLY_PROTOCOL.md'
EXPECTED_ADDENDUM = '655edc14bda6f3dd2faf54c907c17a5d8237622cd5902f8c598c3c0fd0eabe05'
EARLY = (1, 2, 3, 5)
RULES = ['oracle_d0'] + [f'early_e{e}' for e in EARLY] + [f'early_stop_e{e}' for e in EARLY]


def explicit_mask(segments, length, rule):
    chosen = set()
    for s in segments:
        if rule == 'oracle_d0':
            start, stop = s['peak']+1, s['trough']
        elif rule.startswith('early_stop_e'):
            e = int(rule[len('early_stop_e'):])
            start, stop = s['peak']+1-e, s['trough']
        else:
            e = int(rule[len('early_e'):])
            start, stop = s['peak']+1-e, s['trough']-e
        chosen.update(p for p in range(start, stop+1) if 0 <= p < length)
    return np.array([p in chosen for p in range(length)])


def main():
    checks = {}
    provenance = json.loads((STUDY/'provenance.json').read_text(encoding='utf-8'))
    checks['addendum_unchanged'] = first.sha(ADDENDUM, True) == EXPECTED_ADDENDUM == provenance['addendum_sha256_crlf_normalized']
    checks['original_protocol_unchanged'] = first.sha(first.PROTOCOL, True) == first.EXPECTED_PROTOCOL
    checks['outputs_match_provenance'] = all(first.sha(STUDY/name) == digest for name, digest in provenance['outputs_sha256'].items())
    daily = pd.read_csv(first.SOURCE/'features_d1_20.csv', usecols=['bar_time', 'open', 'close'],
                        parse_dates=['bar_time'], index_col='bar_time')
    daily = daily.loc[daily.index <= '2026-09-30']
    rolls = pd.read_csv(first.ROLLS, parse_dates=['date'])
    switches = [d for d in rolls.loc[rolls.symbol != rolls.symbol.shift(), 'date'].iloc[1:] if d <= daily.index[-1]]
    sessions = daily.index
    closes = {'roll_adjusted': first.adjusted(daily, switches), 'raw': daily.close.to_numpy(dtype=float)}
    masks = pd.read_csv(STUDY/'masks.csv', parse_dates=['session'], index_col='session')
    first_masks = pd.read_csv(first.STUDY/'masks.csv', parse_dates=['session'], index_col='session')
    built, mask_ok = {}, masks.index.equals(sessions)
    for series, c in closes.items():
        for x in first.SIZES:
            segments = first.pivots(c, x)
            for rule in RULES:
                mask = explicit_mask(segments, len(sessions), rule)
                built[(series, x, rule)] = mask
                mask_ok &= np.array_equal(mask, masks[f'{series}|{x}|{rule}'].to_numpy())
            mask_ok &= np.array_equal(built[(series, x, 'oracle_d0')], first_masks[f'{series}|{x}|oracle_d0'].to_numpy())
    checks['masks_reproduced_and_on_time_matches_first_study'] = bool(mask_ok)
    trades = pd.read_csv(first.SOURCE/'trades.csv', usecols=['session', 'net_dollars', 'net_r', 'era', 'primary'],
                         parse_dates=['session'])
    trades = trades.loc[trades.primary]
    rules = pd.read_csv(STUDY/'rules.csv')
    rows_ok, shift_ok, passes = True, True, []
    for era, (start, stop) in first.ERAS.items():
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
            curve = pnl*~era_mask
            values = [int(skipped.sum()), base, kept.net_dollars.sum(), kept.net_r.mean(), int(era_mask.sum()), first.daily_dd(curve)]
            saved = [row.skipped_trades, row.baseline_net_dollars, row.retained_net_dollars, row.retained_mean_r,
                     row.skipped_sessions, row.retained_daily_dd]
            rows_ok &= np.allclose(values, saved, atol=1e-6, rtol=0)
            nets = np.array([(pnl*~np.roll(era_mask, k)).sum() for k in range(len(calendar))])
            p975 = float(np.quantile(nets, .975))
            shift_ok &= np.isclose(p975, row.shift_net_p975, atol=1e-6)
            passes.append(dict(series=series, size=x, rule=rule, ok=bool(curve.sum() > base and curve.sum() > p975)))
    checks['ledger_partitions_and_drawdowns'] = bool(rows_ok)
    checks['all_circular_shifts_recomputed'] = bool(shift_ok)
    frame = pd.DataFrame(passes)
    eligible = frame.loc[frame.rule.str.extract(r'(\d+)$')[0].astype(int).ge(2) & frame.rule.ne('oracle_d0')]
    both = eligible.groupby(['series', 'size', 'rule']).ok.all()
    worthwhile = {series: bool(both.loc[series].any()) for series in closes}
    decision = json.loads((STUDY/'decision.json').read_text(encoding='utf-8'))
    checks['decision_reproduced'] = (worthwhile['roll_adjusted'] == decision['summary']['pullback_statistic_worth_building']
                                     and (worthwhile['roll_adjusted'] == worthwhile['raw']) == decision['summary']['raw_series_agrees'])
    result = dict(all_passed=all(checks.values()), checks=checks, verified_rules=len(rules))
    (STUDY/'independent_verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    assert result['all_passed']


if __name__ == '__main__':
    main()
