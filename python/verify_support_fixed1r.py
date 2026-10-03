"""Independent saved-output verification for Q10's fixed-exit comparison."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_support_fixed1r import STUDY
from analyze_price_levels import SOURCES, PERIODS, sha256


def main():
    c = pd.read_csv(STUDY/'potential_signals.csv', parse_dates=['signal_time', 'submission_time'])
    a = pd.read_csv(STUDY/'attempts.csv', parse_dates=['signal_time', 'submission_time'])
    t = pd.read_csv(STUDY/'trades.csv', parse_dates=['signal_time', 'submission_time', 'entry_time', 'exit_time'])
    groups = pd.read_csv(STUDY/'groups.csv')
    for f in (c, a, t):
        assert not f.duplicated(['source', 'event_id']).any()
        known = f.status == 'eligible'
        geometry = known & (f.signal_open > f.low) & (f.signal_low <= f.low)
        classes = f.group.isin(['touch_only', 'breach_reclaim', 'breach_unrecovered', 'breach_exact_close'])
        assert geometry.equals(classes)
        assert (f.signal_close < f.signal_open).all() and f.red_run.between(1, 3).all()
        f['interaction'] = geometry
    assert np.allclose(t.net, t.trade_profit-1.05)
    assert np.allclose(t.net_r, t.net/(2*(t.signal_high-t.signal_low)))
    assert (t.entry_time.dt.normalize() == t.exit_time.dt.normalize()).all()
    assert (t.exit_time >= t.entry_time).all()
    assert (t.entry_time >= t.submission_time).all()
    assert ((t.exit_reason == 5) == (t.exit_class == 'take_profit')).all()
    attached = pd.read_csv(STUDY/'orders_audit.csv')
    assert np.allclose(attached.tp-attached.entry, attached.entry-attached.sl)

    checks = 0
    for source in SOURCES:
        for period in PERIODS:
            cc, aa, tt = (f[(f.source == source) & (f.period == period)] for f in (c, a, t))
            assert set(aa.event_id) == set(cc.loc[cc.baseline_attempt, 'event_id'])
            assert set(tt.event_id) == set(aa.loc[aa.filled, 'event_id'])
            assert set(tt.event_id) == set(cc.loc[cc.filled, 'event_id'])
            for year in ['all']+sorted(str(y) for y in aa.year.unique()):
                g = groups[(groups.source == source) & (groups.period == period) & (groups.year.astype(str) == year)].set_index('group')
                allrow, hit, rest = (g.loc[name] for name in ('all', 'interaction', 'every_other'))
                for col in ('potential_signals', 'attempts', 'fills', 'unfilled_attempts', 'potential_without_attempt',
                            'net', 'gains', 'losses', 'exit_stop', 'exit_take_profit', 'exit_other_session'):
                    assert np.isclose(hit[col]+rest[col], allrow[col], atol=1e-7), (source, period, year, col)
                disjoint = g.loc[['no_contact', 'touch_only', 'breach_reclaim', 'breach_unrecovered',
                                  'breach_exact_close', 'opened_at_or_below', 'unavailable']]
                assert np.isclose(disjoint.net.sum(), allrow.net)
                assert disjoint.fills.sum() == allrow.fills
                subset = tt if year == 'all' else tt[tt.year == int(year)]
                for label, observed in [('all', subset), ('interaction', subset[subset.interaction]), ('every_other', subset[~subset.interaction])]:
                    row = g.loc[label]
                    assert row.fills == len(observed)
                    assert np.isclose(row.net, observed.net.sum())
                    if len(observed):
                        assert np.isclose(row.avg_net_r, observed.net_r.mean())
                        assert np.isclose(row.win_rate, (observed.net > 0).mean())
                    assert row.exit_stop+row.exit_take_profit+row.exit_other_session == row.fills
                    assert sum(row[k] for k in ('r_le_minus1', 'r_minus1_to_zero', 'r_zero', 'r_zero_to_1', 'r_ge_1')) == row.fills
                    checks += 1
                if year == 'all':
                    equity = 0.; peak = 0.; worst = 0.
                    for profit in subset.sort_values('exit_time').net:
                        equity += profit
                        peak = max(peak, equity)
                        worst = max(worst, peak-equity)
                    assert np.isclose(worst, allrow.attributed_closed_dd)
                    assert np.isclose(hit.baseline_dd_net_contribution+rest.baseline_dd_net_contribution, -worst)
    # Every source's full baseline must be the identical population and result.
    allgroups = groups[(groups.group == 'all') & (groups.year.astype(str) == 'all')]
    for _, g in allgroups.groupby('period'):
        for field in ('potential_signals', 'attempts', 'fills', 'net', 'pf', 'avg_net_r'):
            assert g[field].nunique() == 1
    contrasts = json.loads((STUDY/'contrasts.json').read_text())
    for r in contrasts:
        for field in ('pf', 'avg_net_r'):
            x, y = r['candidate_metrics'][field], r['complement_metrics'][field]
            if x is not None and y is not None:
                assert np.isclose(r['differences'][field]['difference'], x-y)
    provenance = json.loads((STUDY/'provenance.json').read_text())
    for f in provenance['files']:
        assert sha256(f['path']) == f['sha256'], f['path']
    result = dict(status='passed', geometry_rows_checked=len(c)+len(a)+len(t),
                  whole_population_table_checks=checks, comparison_checks=len(contrasts),
                  hashes_checked=len(provenance['files']), orders_checked=len(attached),
                  verifier_sha256=sha256(Path(__file__)))
    (STUDY/'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
