"""Independent verification of the warning-based skip rules.

Separately written event scans for both rules, loop-built features and the first
verifier's zigzag; recomputes masks, ledger partitions, drawdowns, every circular
shift and the decision.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import verify_rtl_downtrend_oracle as first
import verify_rtl_pullback_stats as stats_check

STUDY = first.ROOT / 'Reports/rtl_warning_rules_20261025'
PROTOCOL = first.ROOT / 'docs/baseline/rtl-warning-rules/PROTOCOL.md'
EXPECTED_PROTOCOL = '39522fbe9a34172e17c71ca575ed11528cfe09b2f95687d3fc8a50cd25dc8d35'
CUTOFFS = first.ROOT / 'Reports/rtl_pullback_stats_20261025/cutoffs.csv'
BOUNCE = ('rise_5', 'rise_10', 'rise_20', 'zscore_5', 'zscore_10', 'zscore_20')
PRIMARY = ('A|rise_5|M20', 'B|0.02|rise_5', 'B|0.03|rise_5', 'B|0.05|rise_5')


def scan_a(stop, bounce, timeout):
    """Jump from stop to stop; skipped sessions run from the day after a stop."""
    skipped, t, n = set(), 0, len(stop)
    while t < n:
        if not stop[t]:
            t += 1
            continue
        u = t+1
        while u < n:
            skipped.add(u)
            if bounce[u] or u-t >= timeout:
                break
            u += 1
        t = u+1
    return np.array([p in skipped for p in range(n)])


def scan_b(segments, bounce, n):
    skipped = set()
    for s in segments:
        stop = s['stop_confirm']
        limit = n-1 if s['censored'] else s['resume_confirm']
        end = next((u for u in range(stop, limit+1) if bounce[u]), limit)
        skipped.update(range(stop+1, end+1))
    return np.array([p in skipped for p in range(n)])


def main():
    checks = {}
    provenance = json.loads((STUDY/'provenance.json').read_text(encoding='utf-8'))
    checks['protocol_unchanged'] = first.sha(PROTOCOL, True) == EXPECTED_PROTOCOL == provenance['protocol_sha256_crlf_normalized']
    checks['outputs_match_provenance'] = all(first.sha(STUDY/name) == d for name, d in provenance['outputs_sha256'].items())
    checks['cutoffs_unchanged'] = first.sha(CUTOFFS) == provenance['inputs_sha256'][str(CUTOFFS)]
    daily = pd.read_csv(first.SOURCE/'features_d1_20.csv', usecols=['bar_time', 'open', 'close'],
                        parse_dates=['bar_time'], index_col='bar_time')
    daily = daily.loc[daily.index <= '2026-09-30']
    rolls = pd.read_csv(first.ROLLS, parse_dates=['date'])
    switches = [d for d in rolls.loc[rolls.symbol != rolls.symbol.shift(), 'date'].iloc[1:] if d <= daily.index[-1]]
    sessions = daily.index
    closes = {'roll_adjusted': first.adjusted(daily, switches), 'raw': daily.close.to_numpy(dtype=float)}
    cutoffs = pd.read_csv(CUTOFFS)
    saved_masks = pd.read_csv(STUDY/'masks.csv', parse_dates=['session'], index_col='session')
    built, mask_ok = {}, saved_masks.index.equals(sessions)
    for series, c in closes.items():
        frame = stats_check.loop_features(c)
        valid = frame.notna().all(axis=1).to_numpy()
        cut = cutoffs.loc[cutoffs.series.eq(series) & cutoffs.level.eq('primary')].set_index('predictor')
        stop = valid & (frame.rise_5.to_numpy() >= cut.loc['rise_5', 'stop_cutoff'])
        bounce = {p: valid & (frame[p].to_numpy() <= cut.loc[p, 'resume_cutoff']) for p in BOUNCE}
        for p in BOUNCE:
            for timeout in (10, 20, 40):
                built[(series, f'A|{p}|M{timeout}')] = scan_a(stop, bounce[p], timeout)
        for x in (.02, .03, .05):
            segments = first.pivots(c, x)
            for p in BOUNCE:
                built[(series, f'B|{x:g}|{p}')] = scan_b(segments, bounce[p], len(c))
            built[(series, f'zigzag|{x:g}')] = first.explicit_mask(segments, sessions, 'live_zigzag')
    for (series, rule), mask in built.items():
        mask_ok &= np.array_equal(mask, saved_masks[f'{series}|{rule}'].to_numpy())
    checks['masks_reproduced'] = bool(mask_ok)
    trades = pd.read_csv(first.SOURCE/'trades.csv', usecols=['session', 'net_dollars', 'net_r', 'era', 'primary'],
                         parse_dates=['session'])
    trades = trades.loc[trades.primary]
    rules = pd.read_csv(STUDY/'rules.csv')
    rows_ok, shift_ok, verdict = True, True, {}
    for era, (start, stop) in first.ERAS.items():
        calendar = sessions[(sessions >= start) & (sessions < stop)]
        part = trades.loc[trades.era.eq(era)]
        position = sessions.get_indexer(part.session)
        pnl = part.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.).to_numpy()
        base, base_r = part.net_dollars.sum(), part.net_r.mean()
        for (series, rule), mask in built.items():
            row = rules.loc[rules.era.eq(era) & rules.series.eq(series) & rules.rule.eq(rule)].iloc[0]
            skipped = mask[position]
            kept = part.loc[~skipped]
            curve = pnl*~mask[sessions.get_indexer(calendar)]
            values = [int(skipped.sum()), base, kept.net_dollars.sum(), kept.net_r.mean(), first.daily_dd(curve)]
            saved = [row.skipped_trades, row.baseline_net_dollars, row.retained_net_dollars, row.retained_mean_r, row.retained_daily_dd]
            rows_ok &= np.allclose(values, saved, atol=1e-6, rtol=0)
            era_mask = mask[sessions.get_indexer(calendar)]
            nets = np.array([(pnl*~np.roll(era_mask, k)).sum() for k in range(len(calendar))])
            p975 = float(np.quantile(nets, .975))
            shift_ok &= np.isclose(p975, row.shift_net_p975, atol=1e-6)
            verdict.setdefault((series, rule), []).append(
                dict(promising=bool(curve.sum() > base and kept.net_r.mean() > base_r and curve.sum() > p975),
                     positive=bool(curve.sum() > base)))
    checks['ledger_partitions_and_drawdowns'] = bool(rows_ok)
    checks['all_circular_shifts_recomputed'] = bool(shift_ok)
    decision = json.loads((STUDY/'decision.json').read_text(encoding='utf-8'))
    same = True
    for rule in PRIMARY:
        passed = all(v['promising'] for v in verdict[('roll_adjusted', rule)])
        robust = all(v['positive'] for v in verdict[('raw', rule)])
        if rule.startswith('A'):
            robust &= all(v['positive'] for m in (10, 40) for v in verdict[('roll_adjusted', f'A|rise_5|M{m}')])
        label = 'promising' if passed and robust else 'fragile' if passed else 'not promising'
        same &= decision['primary'][rule]['label'] == label
    checks['decision_reproduced'] = bool(same)
    result = dict(all_passed=all(checks.values()), checks=checks, verified_rule_rows=len(rules))
    (STUDY/'independent_verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    assert result['all_passed']


if __name__ == '__main__':
    main()
