"""Execute the frozen RTL warning-based skip rules.

Rule A: pullback warning stops, bounce warning (or a timeout) resumes.
Rule B: live-zigzag confirmation stops, bounce warning (or zigzag rebound) resumes.
Causal daily decisions; ledger omission only.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import analyze_rtl_downtrend_oracle as oracle
import analyze_rtl_market_regimes as prior
import analyze_rtl_price_structure as structure
import analyze_rtl_pullback_stats as warnings

STUDY = oracle.ROOT / 'Reports/rtl_warning_rules_20261025'
PROTOCOL = oracle.ROOT / 'docs/baseline/rtl-warning-rules/PROTOCOL.md'
PROTOCOL_SHA256 = '39522fbe9a34172e17c71ca575ed11528cfe09b2f95687d3fc8a50cd25dc8d35'
BOUNCE = ('rise_5', 'rise_10', 'rise_20', 'zscore_5', 'zscore_10', 'zscore_20')
STOP = 'rise_5'
TIMEOUTS = (10, 20, 40)
ZIGZAG_SIZES = (.02, .03, .05)
PRIMARY = ('A|rise_5|M20',) + tuple(f'B|{x:g}|rise_5' for x in ZIGZAG_SIZES)


def rule_a(stop_signal, resume_signal, timeout):
    """Skip mask and stop periods; a decision at close t applies from session t+1."""
    mask = np.zeros(len(stop_signal), dtype=bool)
    periods, stopped, start, skipped = [], False, None, 0
    for t in range(len(stop_signal)):
        mask[t] = stopped
        if stopped:
            skipped += 1
            if resume_signal[t] or skipped >= timeout:
                periods.append(dict(stop_close=start, resume_close=t, skipped=skipped,
                                    reason='bounce' if resume_signal[t] else 'timeout'))
                stopped = False
        elif stop_signal[t]:
            stopped, start, skipped = True, t, 0
    if stopped:
        periods.append(dict(stop_close=start, resume_close=None, skipped=skipped, reason='data_end'))
    return mask, periods


def rule_b(segments, bounce, length):
    """Live-zigzag stop; resume after the first bounce close on/after confirmation, else the zigzag rebound."""
    mask, periods = np.zeros(length, dtype=bool), []
    for segment in segments:
        start = segment['stop_confirm']
        last = length-1 if segment['censored'] else segment['resume_confirm']
        hits = np.flatnonzero(bounce[start:last+1])
        if len(hits):
            end, reason = start+int(hits[0]), 'bounce'
        elif segment['censored']:
            end, reason = length-1, 'data_end'
        else:
            end, reason = last, 'zigzag_rebound'
        mask[start+1:end+1] = True
        periods.append(dict(stop_close=start, resume_close=None if reason == 'data_end' else end,
                            skipped=end-start, reason=reason))
    return mask, periods


def build_rules(c, cutoffs, length):
    """All rule masks and stop periods for one close series."""
    frame = warnings.features(c)
    valid = frame.notna().all(axis=1).to_numpy()
    cut = cutoffs.set_index('predictor')
    stop = valid & (frame[STOP].to_numpy() >= cut.loc[STOP, 'stop_cutoff'])
    bounce = {p: valid & (frame[p].to_numpy() <= cut.loc[p, 'resume_cutoff']) for p in BOUNCE}
    masks, periods = {}, {}
    for p in BOUNCE:
        for timeout in TIMEOUTS:
            masks[f'A|{p}|M{timeout}'], periods[f'A|{p}|M{timeout}'] = rule_a(stop, bounce[p], timeout)
    for x in ZIGZAG_SIZES:
        segments = oracle.zigzag(c, x)
        for p in BOUNCE:
            masks[f'B|{x:g}|{p}'], periods[f'B|{x:g}|{p}'] = rule_b(segments, bounce[p], length)
        masks[f'zigzag|{x:g}'] = oracle.skip_mask(segments, length, 'live_zigzag')
    return masks, periods


def decide(rules):
    """Section 4, applied mechanically."""
    def promising(part):
        return bool(len(part) == 2 and (part.retained_net_dollars > part.baseline_net_dollars).all()
                    and (part.retained_mean_r > part.baseline_mean_r).all()
                    and (part.retained_net_dollars > part.shift_net_p975).all())

    def positive(part):
        return bool(len(part) == 2 and (part.gain_dollars > 0).all())

    select = lambda series, rule: rules.loc[rules.series.eq(series) & rules.rule.eq(rule)]
    out = {}
    for rule in PRIMARY:
        passed = promising(select('roll_adjusted', rule))
        checks = {'raw_positive_both_eras': positive(select('raw', rule))}
        if rule.startswith('A'):
            for timeout in (10, 40):
                checks[f'M{timeout}_positive_both_eras'] = positive(select('roll_adjusted', f'A|rise_5|M{timeout}'))
        out[rule] = dict(promising=passed, **checks,
                         label='promising' if passed and all(checks.values()) else 'fragile' if passed else 'not promising')
    return dict(primary=out, summary=dict(promising_rules=[r for r, v in out.items() if v['label'] == 'promising'],
                                          fragile_rules=[r for r, v in out.items() if v['label'] == 'fragile']))


def main():
    assert oracle.text_digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol hash mismatch: no outcomes computed'
    inputs = oracle.check_provenance()
    source = json.loads((warnings.STUDY/'provenance.json').read_text(encoding='utf-8'))
    assert prior.digest(warnings.STUDY/'cutoffs.csv') == source['outputs_sha256']['cutoffs.csv']
    inputs.update({str(PROTOCOL)+' (CRLF-normalized)': PROTOCOL_SHA256,
                   str(warnings.STUDY/'cutoffs.csv'): prior.digest(warnings.STUDY/'cutoffs.csv'),
                   str(oracle.__file__): prior.digest(oracle.__file__), str(warnings.__file__): prior.digest(warnings.__file__)})
    print('Frozen protocol, saved cutoffs and source hashes verified.', flush=True)
    STUDY.mkdir(parents=True, exist_ok=True)
    trades = structure.load_trades()
    trades = trades.loc[trades.primary].copy()
    daily, switches = oracle.load_daily()
    sessions = daily.index
    trades['position'] = sessions.get_indexer(trades.session)
    assert (trades.position >= 0).all()
    cutoffs = pd.read_csv(warnings.STUDY/'cutoffs.csv')
    closes = {'roll_adjusted': oracle.roll_adjusted_closes(daily, switches).to_numpy(), 'raw': daily.close.to_numpy(dtype=float)}
    masks, period_rows = {}, []
    for series, c in closes.items():
        chosen = cutoffs.loc[cutoffs.series.eq(series) & cutoffs.level.eq('primary')]
        series_masks, series_periods = build_rules(c, chosen, len(sessions))
        for rule, mask in series_masks.items():
            masks[(series, rule)] = mask
        for rule, periods in series_periods.items():
            for p in periods:
                period_rows.append(dict(series=series, rule=rule, **p, stop_session=sessions[p['stop_close']],
                                        resume_session=sessions[p['resume_close']] if p['resume_close'] is not None else pd.NaT))
    periods = pd.DataFrame(period_rows)
    rows = []
    for era, (start, stop) in oracle.ERAS.items():
        calendar = sessions[(sessions >= start) & (sessions < stop)]
        part = trades.loc[trades.era == era]
        session_pnl = part.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.).to_numpy()
        session_hours = (part.groupby('session').holding_minutes.sum()/60).reindex(calendar, fill_value=0.).to_numpy()
        era_positions = sessions.get_indexer(calendar)
        in_era = periods.stop_session.ge(start) & periods.stop_session.lt(stop)
        for (series, rule), mask in masks.items():
            row = oracle.evaluate(part, calendar, era_positions, mask, session_pnl, session_hours)
            assert np.isclose(row['retained_net_dollars']+row['skipped_net_dollars'], row['baseline_net_dollars'], atol=1e-6)
            mine = periods.loc[in_era & periods.series.eq(series) & periods.rule.eq(rule)]
            reasons = mine.reason.value_counts(normalize=True)
            rows.append(dict(era=era, series=series, rule=rule, stops=len(mine),
                             median_stop_sessions=float(mine.skipped.median()) if len(mine) else np.nan,
                             share_resumed_by_bounce=float(reasons.get('bounce', 0.)),
                             share_zero_length=float(mine.skipped.eq(0).mean()) if len(mine) else np.nan, **row))
        print(f'{era}: {len(masks)} rules evaluated.', flush=True)
    rules = pd.DataFrame(rows)
    decision = decide(rules)
    rules.to_csv(STUDY/'rules.csv', index=False, float_format='%.15g')
    periods.to_csv(STUDY/'periods.csv', index=False, float_format='%.15g')
    pd.DataFrame({f'{s}|{r}': m for (s, r), m in masks.items()}, index=sessions.rename('session')).to_csv(STUDY/'masks.csv')
    prior.save_json(STUDY/'decision.json', decision)
    assert oracle.text_digest(PROTOCOL) == PROTOCOL_SHA256
    generated = ('rules.csv', 'periods.csv', 'masks.csv', 'decision.json')
    prior.save_json(STUDY/'provenance.json', dict(
        study='RTL warning-based skip rules', protocol_sha256_crlf_normalized=PROTOCOL_SHA256, inputs_sha256=inputs,
        outputs_sha256={name: prior.digest(STUDY/name) for name in generated}, primary_rules=PRIMARY,
        timeouts=TIMEOUTS, zigzag_sizes=ZIGZAG_SIZES, bounce_predictors=BOUNCE,
        software=dict(numpy=np.__version__, pandas=pd.__version__), strategy_changed=False, exploratory_only=True,
        omission='counterfactual ledger omission by submission session, not an MT5 replay'))
    view = rules.loc[rules.series.eq('roll_adjusted') & (rules.rule.isin(PRIMARY) | rules.rule.str.startswith('zigzag')),
                     ['era', 'rule', 'stops', 'median_stop_sessions', 'skipped_session_share', 'gain_pct',
                      'skipped_mean_r', 'retained_mean_r', 'baseline_mean_r', 'beats_shift_p975']]
    print(view.to_string(index=False, float_format=lambda v: f'{v:.3f}'), flush=True)
    print(json.dumps(decision, indent=2), flush=True)


if __name__ == '__main__':
    main()
