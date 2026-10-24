"""Execute the frozen early-signal addendum to the downtrend crystal ball.

Same trades, closes, zigzag and controls as analyze_rtl_downtrend_oracle; only
the skip windows move earlier. Ledger omission only.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import analyze_rtl_downtrend_oracle as oracle
import analyze_rtl_market_regimes as prior
import analyze_rtl_price_structure as structure

STUDY = oracle.ROOT / 'Reports/rtl_downtrend_early_20261025'
ADDENDUM = oracle.ROOT / 'docs/baseline/rtl-downtrend-oracle/EARLY_PROTOCOL.md'
ADDENDUM_SHA256 = '655edc14bda6f3dd2faf54c907c17a5d8237622cd5902f8c598c3c0fd0eabe05'
EARLY = (1, 2, 3, 5)
RULES = ('oracle_d0',) + tuple(f'early_e{e}' for e in EARLY) + tuple(f'early_stop_e{e}' for e in EARLY)
DECISION_EARLY = 2


def parse(rule):
    """(sessions early, whether the resume also comes early)."""
    if rule == 'oracle_d0':
        return 0, True
    if rule.startswith('early_stop_e'):
        return int(rule.removeprefix('early_stop_e')), False
    return int(rule.removeprefix('early_e')), True


def early_mask(segments, length, rule):
    """Skip windows moved e sessions earlier; clipped at the first session, overlaps merged."""
    early, resume_early = parse(rule)
    mask = np.zeros(length, dtype=bool)
    for segment in segments:
        first = max(segment['peak']+1-early, 0)
        last = min(segment['trough']-(early if resume_early else 0), length-1)
        if last >= first:
            mask[first:last+1] = True
    return mask


def decide(rules):
    """Addendum decision, applied mechanically."""
    passing = {}
    for (series, x), part in rules.groupby(['series', 'size']):
        passing[f'{series}|{x}'] = [rule for rule in RULES if parse(rule)[0] >= DECISION_EARLY and all(
            bool(r.beats_baseline and r.beats_shift_p975) for r in part.loc[part.rule.eq(rule)].itertuples())]
    primary = any(v for k, v in passing.items() if k.startswith('roll_adjusted'))
    raw = any(v for k, v in passing.items() if k.startswith('raw'))
    return dict(passing_rules=passing, summary=dict(pullback_statistic_worth_building=primary,
                                                    raw_series_agrees=primary == raw, decision_early=DECISION_EARLY))


def main():
    assert oracle.text_digest(ADDENDUM) == ADDENDUM_SHA256, 'Frozen addendum hash mismatch: no outcomes computed'
    inputs = oracle.check_provenance()
    inputs[str(ADDENDUM)+' (CRLF-normalized)'] = ADDENDUM_SHA256
    inputs[str(oracle.__file__)] = prior.digest(oracle.__file__)
    print('Frozen addendum, original protocol and source hashes verified.', flush=True)
    STUDY.mkdir(parents=True, exist_ok=True)
    trades = structure.load_trades()
    trades = trades.loc[trades.primary].copy()
    daily, switches = oracle.load_daily()
    sessions = daily.index
    closes = {'roll_adjusted': oracle.roll_adjusted_closes(daily, switches), 'raw': daily.close.astype(float)}
    trades['position'] = sessions.get_indexer(trades.session)
    assert (trades.position >= 0).all()
    masks = {}
    for series in oracle.SERIES:
        for x in oracle.SIZES:
            segments = oracle.zigzag(closes[series].to_numpy(), x)
            for rule in RULES:
                masks[(series, x, rule)] = early_mask(segments, len(sessions), rule)
            assert np.array_equal(masks[(series, x, 'oracle_d0')], oracle.skip_mask(segments, len(sessions), 'oracle_d0'))
    rows = []
    for era, (start, stop) in oracle.ERAS.items():
        calendar = sessions[(sessions >= start) & (sessions < stop)]
        part = trades.loc[trades.era == era]
        session_pnl = part.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.).to_numpy()
        session_hours = (part.groupby('session').holding_minutes.sum()/60).reindex(calendar, fill_value=0.).to_numpy()
        era_positions = sessions.get_indexer(calendar)
        for (series, x, rule), mask in masks.items():
            row = oracle.evaluate(part, calendar, era_positions, mask, session_pnl, session_hours)
            assert np.isclose(row['retained_net_dollars']+row['skipped_net_dollars'], row['baseline_net_dollars'], atol=1e-6)
            early, resume_early = parse(rule)
            rows.append(dict(era=era, series=series, size=x, rule=rule, sessions_early=early,
                             resume_early=resume_early, **row))
        print(f'{era}: {len(masks)} rules evaluated.', flush=True)
    rules = pd.DataFrame(rows)
    # The on-time reference must reproduce the first study exactly.
    first = pd.read_csv(oracle.STUDY/'rules.csv')
    reference = rules.loc[rules.rule.eq('oracle_d0')].merge(first.loc[first.rule.eq('oracle_d0')],
                                                            on=['era', 'series', 'size'], suffixes=('', '_first'))
    assert len(reference) == 16
    for field in ('retained_net_dollars', 'retained_daily_dd', 'shift_net_p975', 'share_shifts_net_at_least_rule'):
        assert np.allclose(reference[field], reference[field+'_first'], atol=1e-6, rtol=0), field
    decision = decide(rules)
    rules.to_csv(STUDY/'rules.csv', index=False, float_format='%.15g')
    pd.DataFrame({f'{s}|{x}|{r}': m for (s, x, r), m in masks.items()},
                 index=sessions.rename('session')).to_csv(STUDY/'masks.csv')
    prior.save_json(STUDY/'decision.json', decision)
    assert oracle.text_digest(ADDENDUM) == ADDENDUM_SHA256
    generated = ('rules.csv', 'masks.csv', 'decision.json')
    prior.save_json(STUDY/'provenance.json', dict(
        study='RTL downtrend crystal ball, early signals', addendum_sha256_crlf_normalized=ADDENDUM_SHA256,
        inputs_sha256=inputs, outputs_sha256={name: prior.digest(STUDY/name) for name in generated},
        early_sessions=EARLY, decision_early=DECISION_EARLY, on_time_reference_matches_first_study=True,
        software=dict(numpy=np.__version__, pandas=pd.__version__), strategy_changed=False, exploratory_only=True))
    view = rules.loc[rules.series.eq('roll_adjusted'), ['era', 'size', 'rule', 'gain_pct', 'skipped_mean_r',
                                                        'retained_mean_r', 'beats_shift_p975']]
    print(view.to_string(index=False, float_format=lambda v: f'{v:.3f}'), flush=True)
    print(json.dumps(decision, indent=2), flush=True)


if __name__ == '__main__':
    main()
