"""Analyze Q10's user-requested fixed 1R SL/TP run, including full complements."""
import html
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_support_interaction as base
from analyze_price_levels import ROOT, SOURCES, PERIODS, build_level_maps, sha256, protocol_matches
from analyze_breach_reclaim import attach, read_table
from analyze_averaging_study import validate
from analyze_exit_study import deals, number
from prepare_support_fixed1r import RUN, RUN_TAG
from trend_regimes import ROLLS
from verify_location_validation import read_rows

STUDY = ROOT/'Reports'/'levels'/'support_interaction_fixed1r_20261003'


def audit_run(bars):
    manifest = json.loads((RUN/'manifest.json').read_text())
    job = manifest['jobs'][0]
    assert (RUN/f'{RUN_TAG}.completed.json').exists()
    assert sha256(RUN/'RTL_support_fixed1r.mq5') == manifest['expert_sha256']
    assert sha256(manifest['parent_source']) == manifest['parent_sha256']
    assert protocol_matches(ROOT/'docs/setups/horizontal/support-bounce-long/q10-support-interaction/PROTOCOL.md', manifest['protocol_sha256'])
    rows = read_rows(RUN/job['csv'])
    stats = read_rows(RUN/job['csv'].replace('.csv', '_stats.csv'))[0]
    validate(rows, stats, dict(job, distance=0))
    for k in ('trend_export_errors', 'trend_close_errors', 'cancel_errors', 'orphan_close_errors'):
        assert int(stats[k]) == 0, k
    assert int(stats['max_red_run']) == 3 and float(stats['min_location']) == 0
    assert float(stats['risk_reward']) == 1
    t = pd.DataFrame(rows)
    for col in ('signal_time', 'entry_time', 'exit_time', 'qualified_time'):
        t[col] = pd.to_datetime(t[col].replace('', np.nan), format='%Y.%m.%d %H:%M:%S')
    numeric = ('signal_open', 'signal_high', 'signal_low', 'signal_close', 'candle_range', 'red_run',
               'trade_profit', 'mae_money', 'mfe_money', 'initial_stop', 'base_entry', 'exit_price', 'exit_reason', 'initial_risk_money')
    for col in numeric:
        t[col] = pd.to_numeric(t[col])
    assert t.qualified_time.isna().all()
    assert read_table(RUN/f'{RUN_TAG}_checks.csv').empty, 'Bar-close exit was still active'
    assert t.signal_time.is_unique
    signal = bars.reindex(t.signal_time)
    for col in ('open', 'high', 'low', 'close'):
        assert np.array_equal(signal[col], t[f'signal_{col}']), col
    assert np.array_equal(t.initial_stop, t.signal_low)
    assert np.allclose(t.initial_risk_money, 2*(t.base_entry-t.initial_stop))
    assert np.allclose(t.trade_profit, 2*(t.exit_price-t.base_entry))
    assert t.exit_reason.isin([3, 4, 5]).all(), t.exit_reason.value_counts()
    t['exit_class'] = t.exit_reason.map({3: 'other_session', 4: 'stop', 5: 'take_profit'})
    tp = t.exit_reason == 5
    sl = t.exit_reason == 4
    assert np.allclose(t.loc[tp, 'exit_price'], t.loc[tp, 'signal_high']+t.loc[tp, 'candle_range'])
    assert (t.loc[sl, 'exit_price'] <= t.loc[sl, 'initial_stop']).all()
    actual, _ = deals(RUN/job['report'])
    assert len(actual) == 2*len(t)
    for i, row in enumerate(rows):
        entry, close = actual[2*i:2*i+2]
        assert entry[3:5] == ['buy', 'in'] and close[3:5] == ['sell', 'out']
        assert entry[7] == row['ticket']
        assert entry[0] == row['entry_time'] and close[0] == row['exit_time']
        assert number(entry[5]) == number(close[5]) == 1
        assert number(entry[6]) == float(row['base_entry'])
        assert number(close[6]) == float(row['exit_price'])
        assert abs(number(close[10])-float(row['trade_profit'])) < 1e-8
    # Audit every accepted buy-stop's attached SL/TP, including cancellations.
    orders = []
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', (RUN/job['report']).read_text(encoding='utf-16'), re.S | re.I):
        cells = [html.unescape(re.sub(r'<[^>]+>', '', cell)).strip()
                 for cell in re.findall(r'<td\b[^>]*>(.*?)</td>', row, re.S | re.I)]
        if len(cells) == 11 and cells[3] == 'buy stop':
            entry, stop, target = map(number, cells[5:8])
            assert entry > stop and abs(target-(2*entry-stop)) < 1e-8, cells
            orders.append(cells)
    assert len(orders) >= len(t)
    pd.DataFrame(orders, columns=['order_time', 'order_id', 'symbol', 'type', 'volume', 'entry', 'sl', 'tp', 'end_time', 'state', 'comment']).to_csv(STUDY/'orders_audit.csv', index=False)
    t['net'] = t.trade_profit-1.05
    t['net_r'] = t.net/(2*t.candle_range)
    audit = dict(full_history_trades=len(t), full_history_deals_checked=len(actual), attached_orders_checked=len(orders),
                 entry_prices_different_from_signal_high=int((t.base_entry != t.signal_high).sum()),
                 stops_beyond_requested_price=int((t.loc[sl, 'exit_price'] < t.loc[sl, 'initial_stop']).sum()),
                 full_history_exit_counts=t.exit_class.value_counts().to_dict(), zero_export_and_close_errors=True)
    return t, audit


def rename_profit_fields(value):
    if isinstance(value, dict):
        return {('exit_take_profit' if k == 'exit_target_qualified' else k): rename_profit_fields(v) for k, v in value.items()}
    if isinstance(value, list):
        return [rename_profit_fields(v) for v in value]
    return value


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    print('Auditing fixed-TP tester trades, orders and unchanged signal census...', flush=True)
    provenance = json.loads((base.UPSTREAM/'provenance.json').read_text())
    for item in provenance['files']:
        assert sha256(item['path']) == item['sha256'], item['path']
    bars = pd.read_csv(base.UPSTREAM/'m30_reference.csv', index_col=0, parse_dates=[0])
    ledger, audit = audit_run(bars)
    raw = read_table(RUN/f'{RUN_TAG}_signals.csv')
    for col in ('signal_time', 'submission_time'):
        raw[col] = pd.to_datetime(raw[col], format='%Y.%m.%d %H:%M:%S')
    for col in ('open', 'high', 'low', 'close', 'red_run'):
        raw[col] = pd.to_numeric(raw[col])
    raw.rename(columns={c: 'signal_'+c for c in ('open', 'high', 'low', 'close')}, inplace=True)
    parts = []
    for period, (start, end) in PERIODS.items():
        f = raw[raw.submission_time.between(start, end, inclusive='left')].copy()
        f['period'] = period
        parts.append(f)
    attempts = pd.concat(parts, ignore_index=True)
    attempts['candle_range'] = attempts.signal_high-attempts.signal_low
    attempts['event_id'] = attempts.signal_time.dt.strftime('%Y%m%d_%H%M')
    attempts['year'] = attempts.submission_time.dt.year
    attempts['filled'] = attempts.signal_time.isin(ledger.signal_time)
    attempts['previous_close'] = bars.close.shift(1).reindex(attempts.signal_time).to_numpy()
    assert attempts.event_id.is_unique and attempts.red_run.between(1, 3).all()
    assert (attempts.signal_close < attempts.signal_open).all()
    ref = bars.reindex(attempts.signal_time)
    for col in ('open', 'high', 'low', 'close'):
        assert np.array_equal(attempts[f'signal_{col}'], ref[col])
    potential = base.census(bars, RUN/'early_closes.mqh')
    assert attempts.event_id.isin(potential.event_id).all()
    check = potential.set_index('event_id').reindex(attempts.event_id)
    assert np.array_equal(check.submission_time, attempts.submission_time.dt.floor('30min'))
    assert np.array_equal(check.red_run, attempts.red_run)
    potential['baseline_attempt'] = potential.event_id.isin(attempts.event_id)
    potential['filled'] = potential.signal_time.isin(ledger.signal_time)
    maps = build_level_maps(bars, pd.read_csv(ROLLS))
    c, a = attach(potential, maps), attach(attempts, maps)
    outcome = ledger[['signal_time', 'entry_time', 'exit_time', 'trade_profit', 'net', 'net_r', 'mae_money', 'mfe_money',
                      'base_entry', 'initial_stop', 'exit_price', 'exit_reason', 'exit_class']]
    t = a[a.filled].merge(outcome, on='signal_time', validate='many_to_one')
    for period, (start, end) in PERIODS.items():
        full = ledger[ledger.entry_time.between(start, end, inclusive='left')]
        selected = t[(t.period == period) & (t.source == 'current_session')]
        assert len(full) == len(selected) and np.isclose(full.net.sum(), selected.net.sum())
    c.to_csv(STUDY/'potential_signals.csv', index=False)
    a.to_csv(STUDY/'attempts.csv', index=False)
    t.to_csv(STUDY/'trades.csv', index=False)
    print('Computing full-complement comparisons for fixed 1R exits...', flush=True)
    # Shared metric engine uses the original profit-exit label internally only.
    analysis_t = t.assign(exit_class=t.exit_class.replace({'take_profit': 'target_qualified'}))
    rows, contrasts, decisions, dd = base.analyse(c, a, analysis_t)
    rows, contrasts = rename_profit_fields(rows), rename_profit_fields(contrasts)
    pd.DataFrame(rows).to_csv(STUDY/'groups.csv', index=False)
    pd.DataFrame(dd).to_csv(STUDY/'baseline_drawdowns.csv', index=False)
    for name, data in [('contrasts', contrasts), ('decisions', decisions), ('run_audit', audit)]:
        (STUDY/f'{name}.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    base.STUDY = STUDY
    base.report(rows, decisions)
    report = STUDY/'report.md'
    report.write_text(report.read_text().replace('Actual baseline outcomes,', 'Actual fixed -1R SL / +1R TP all-signals reference outcomes,'), encoding='utf-8')
    paths = [Path(__file__), ROOT/'python/analyze_support_interaction.py', ROOT/'python/prepare_support_fixed1r.py',
             ROOT/'python/analyze_breach_reclaim.py', ROOT/'python/analyze_price_levels.py',
             base.UPSTREAM/'m30_reference.csv', ROLLS, ROOT/'docs/setups/horizontal/support-bounce-long/q10-support-interaction/PROTOCOL.md',
             RUN/'manifest.json', RUN/'RTL_support_fixed1r.mq5', RUN/'RTL_support_fixed1r.ex5', RUN/'early_closes.mqh',
             RUN/'trend_rr_ledger.mqh', RUN/'trend_rr_research.mqh', RUN/f'{RUN_TAG}.ini', RUN/f'{RUN_TAG}.htm',
             RUN/f'runband_{RUN_TAG}_1.00.csv', RUN/f'runband_{RUN_TAG}_1.00_stats.csv', RUN/f'{RUN_TAG}_signals.csv']
    (STUDY/'provenance.json').write_text(json.dumps(dict(audit=audit, upstream_hashes_checked=len(provenance['files']),
        files=[dict(path=str(p), sha256=sha256(p)) for p in paths]), indent=2), encoding='utf-8')
    print(json.dumps(audit, indent=2))
    print(json.dumps(decisions, indent=2))


if __name__ == '__main__':
    main()
