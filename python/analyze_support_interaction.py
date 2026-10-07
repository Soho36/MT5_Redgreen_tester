"""Q10: actual RTL support-interaction trades versus the full complement."""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_price_levels import ROOT, SOURCES, PERIODS, build_level_maps, sha256
from analyze_breach_reclaim import GROUPS, attach, read_table, TREND, TAG
from trend_regimes import ROLLS

UPSTREAM = ROOT / 'Reports' / 'levels' / 'breach_reclaim_20261003'
STUDY = ROOT / 'Reports' / 'levels' / 'support_interaction_20261003'
INTERACTION = ('touch_only', 'breach_reclaim', 'breach_unrecovered', 'breach_exact_close')
CANDIDATES = ('interaction', 'breach_reclaim', 'breach_unrecovered')
LABELS = ('all', 'interaction', 'every_other', 'known_level', 'known_other', 'fresh_breaches') + GROUPS


def membership(f, label):
    hit = f.group.isin(INTERACTION)
    if label == 'all':
        return pd.Series(True, index=f.index)
    if label == 'interaction':
        return hit
    if label == 'every_other':
        return ~hit
    if label == 'known_level':
        return f.status == 'eligible'
    if label == 'known_other':
        return (f.status == 'eligible') & ~hit
    if label == 'fresh_breaches':
        return f.group.isin(INTERACTION[1:])
    return f.group == label


def drawdown_interval(net):
    equity = np.r_[0., np.cumsum(np.asarray(net, dtype=float))]
    drawdown = np.maximum.accumulate(equity) - equity
    end = int(drawdown.argmax())
    peak = int(equity[:end+1].argmax())
    return float(drawdown[end]), peak, end


def census(bars, calendar):
    text = calendar.read_text(encoding='utf-8-sig')
    dates = re.search(r'EC_DATE\[EC_COUNT\] = \{([^}]+)', text)[1].split(',')
    cuts = re.search(r'EC_FLAT_MIN\[EC_COUNT\] = \{([^}]+)', text)[1].split(',')
    flat = dict(zip(dates, map(int, cuts)))
    f = bars.rename(columns={c: 'signal_'+c for c in ('open', 'high', 'low', 'close')}).copy()
    f['signal_time'] = f.index
    f['submission_time'] = pd.Series(bars.index, index=bars.index).shift(-1)
    red = f.signal_close < f.signal_open
    f['red_run'] = red.astype(int).groupby((~red).cumsum()).cumsum()
    f['candle_range'] = f.signal_high - f.signal_low
    f['previous_close'] = f.signal_close.shift(1)
    clock = f.submission_time.dt.hour * 60 + f.submission_time.dt.minute
    cutoff = f.submission_time.dt.strftime('%Y%m%d').map(flat).fillna(1410)
    valid = red & f.red_run.between(1, 3) & (f.candle_range > 0) & (clock >= 60) & (clock < cutoff)
    frames = []
    for period, (start, end) in PERIODS.items():
        chosen = f[valid & f.submission_time.between(start, end, inclusive='left')].copy()
        chosen['period'] = period
        frames.append(chosen)
    f = pd.concat(frames).reset_index(drop=True)
    f['event_id'] = f.signal_time.dt.strftime('%Y%m%d_%H%M')
    f['year'] = f.submission_time.dt.year
    assert f.event_id.is_unique
    return f


def trade_metrics(t):
    x = t.net.to_numpy()
    gains, losses = x[x > 0].sum(), -x[x < 0].sum()
    result = dict(fills=len(t), net=float(x.sum()), gains=float(gains), losses=float(losses),
                  pf=float(gains/losses) if losses else None,
                  avg_net_r=float(t.net_r.mean()) if len(t) else None,
                  median_net_r=float(t.net_r.median()) if len(t) else None,
                  avg_net=float(t.net.mean()) if len(t) else None,
                  win_rate=float((t.net > 0).mean()) if len(t) else None,
                  signal_range=float(t.candle_range.mean()) if len(t) else None,
                  attributed_closed_dd=drawdown_interval(t.sort_values('exit_time').net)[0])
    for name in ('stop', 'target_qualified', 'other_session'):
        result[f'exit_{name}'] = int((t.exit_class == name).sum())
    for label, mask in [('le_minus1', t.net_r <= -1), ('minus1_to_zero', t.net_r.between(-1, 0, inclusive='neither')),
                        ('zero', t.net_r == 0), ('zero_to_1', t.net_r.between(0, 1, inclusive='neither')), ('ge_1', t.net_r >= 1)]:
        result[f'r_{label}'] = int(mask.sum())
    for q in (.05, .25, .75, .95):
        result[f'r_q{int(q*100):02}'] = float(t.net_r.quantile(q)) if len(t) else None
    return result


def contrast(a, b, period):
    start, end = PERIODS[period]
    months = pd.period_range(pd.Timestamp(start), pd.Timestamp(end)-pd.Timedelta(days=1), freq='M')
    draws = np.random.default_rng(20261003).integers(0, len(months), size=(2000, len(months)))
    boot, point = [], []
    for t in (a, b):
        f = pd.DataFrame(dict(month=t.exit_time.dt.to_period('M'), gains=t.net.clip(lower=0),
                              losses=-t.net.clip(upper=0), net_r=t.net_r, count=1))
        blocks = f.groupby('month')[['gains', 'losses', 'net_r', 'count']].sum().reindex(months, fill_value=0).to_numpy()
        sampled = blocks[draws].sum(axis=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            boot.append(dict(pf=sampled[:, 0]/sampled[:, 1], avg_net_r=sampled[:, 2]/sampled[:, 3]))
        point.append(trade_metrics(t))
    output = {}
    for field in ('pf', 'avg_net_r'):
        finite = np.isfinite(boot[0][field]) & np.isfinite(boot[1][field])
        delta = boot[0][field][finite] - boot[1][field][finite]
        lo, hi = np.quantile(delta, [.025, .975]) if len(delta) else (None, None)
        value = point[0][field]-point[1][field] if all(p[field] is not None for p in point) else None
        output[field] = dict(difference=value, lower=float(lo) if lo is not None else None,
                             upper=float(hi) if hi is not None else None, valid_resamples=int(finite.sum()))
    return output


def load():
    upstream = json.loads((UPSTREAM/'provenance.json').read_text())
    for item in upstream['files']:
        assert sha256(item['path']) == item['sha256'], item['path']
    a = pd.read_csv(UPSTREAM/'attempt_features.csv', parse_dates=['signal_time', 'submission_time'])
    t = pd.read_csv(UPSTREAM/'trade_features.csv', parse_dates=['signal_time', 'submission_time', 'entry_time', 'exit_time'])
    ledger_path = TREND/f'runband_{TAG}_1.00.csv'
    ledger = read_table(ledger_path)
    ledger['signal_time'] = pd.to_datetime(ledger.signal_time, format='%Y.%m.%d %H:%M:%S')
    ledger['qualified_time'] = pd.to_datetime(ledger.qualified_time.replace('', np.nan), format='%Y.%m.%d %H:%M:%S')
    ledger['exit_reason'] = pd.to_numeric(ledger.exit_reason)
    ledger['ledger_profit'] = pd.to_numeric(ledger.trade_profit)
    t = t.merge(ledger[['signal_time', 'qualified_time', 'exit_reason', 'ledger_profit']], on='signal_time', validate='many_to_one')
    assert len(t) == 14968*3 and np.allclose(t.ledger_profit, t.trade_profit)
    assert np.allclose(t.net, t.trade_profit-1.05) and np.allclose(t.net_r, t.net/(2*t.candle_range))
    t['exit_class'] = np.select([t.exit_reason == 4, t.qualified_time.notna()], ['stop', 'target_qualified'], default='other_session')
    assert t[t.exit_class == 'other_session'].exit_reason.isin([0, 3]).all(), t.groupby(['exit_class', 'exit_reason']).size()
    ini = (TREND/f'{TAG}.ini').read_text(encoding='utf-16')
    for needle in ('MaxRedRun=3', 'MinLocation=0', 'UseCandleRangeFilter=false', 'BullRR=1.0', 'BearRR=1.0', 'TrailDistanceR=0'):
        assert needle in ini, needle
    windows = re.findall(r'^(W\d{4}W\d{4})=(true|false)', ini, flags=re.M)
    assert len(windows) == 26 and all(v == ('false' if k in ('W0000W0100', 'W2330W0000') else 'true') for k, v in windows)
    bars = pd.read_csv(UPSTREAM/'m30_reference.csv', index_col=0, parse_dates=[0])
    calendar = TREND/'early_closes.mqh'
    c = census(bars, calendar)
    unique = a.drop_duplicates('event_id').set_index('event_id')
    assert unique.index.isin(c.event_id).all()
    check = c.set_index('event_id').reindex(unique.index)
    assert (check.submission_time == unique.submission_time.dt.floor('30min')).all()
    assert np.array_equal(check.red_run, unique.red_run)
    c['baseline_attempt'] = c.event_id.isin(unique.index)
    c['filled'] = c.event_id.isin(t.event_id)
    c = attach(c, build_level_maps(bars, pd.read_csv(ROLLS)))
    pair = c[c.baseline_attempt].merge(a, on=['event_id', 'source'], suffixes=('_census', '_log'), validate='one_to_one')
    assert (pair.group_census == pair.group_log).all() and (pair.status_census == pair.status_log).all()
    assert np.allclose(pair.low_census, pair.low_log, equal_nan=True)
    paths = [UPSTREAM/'attempt_features.csv', UPSTREAM/'trade_features.csv', UPSTREAM/'m30_reference.csv',
             ledger_path, calendar, TREND/f'{TAG}.ini', ROLLS, Path(__file__),
             ROOT/'python/analyze_breach_reclaim.py', ROOT/'python/analyze_price_levels.py',
             ROOT/'docs/setups/horizontal/support-bounce-long/q10-support-interaction/PROTOCOL.md']
    return c, a, t, paths, len(upstream['files'])


def analyse(c, a, t):
    rows, contrasts, decisions, dd_rows = [], [], [], []
    for source in SOURCES:
        for period in PERIODS:
            cc = c[(c.source == source) & (c.period == period)]
            aa = a[(a.source == source) & (a.period == period)]
            tt = t[(t.source == source) & (t.period == period)].sort_values('exit_time')
            dd, peak, trough = drawdown_interval(tt.net)
            dd_events = set(tt.iloc[peak:trough].event_id)
            dd_rows.append(dict(source=source, period=period, closed_dd=dd,
                                first_loss_time=str(tt.iloc[peak].exit_time), trough_time=str(tt.iloc[trough-1].exit_time),
                                affected_trades=trough-peak))
            for year in ['all']+sorted(aa.year.unique().tolist()):
                cy, ay, ty = (x if year == 'all' else x[x.year == year] for x in (cc, aa, tt))
                for label in LABELS:
                    cg, ag, tg = (x[membership(x, label)] for x in (cy, ay, ty))
                    assert len(ag) == int(cg.baseline_attempt.sum()) and len(tg) == int(ag.filled.sum())
                    rows.append(dict(source=source, period=period, year=year, group=label,
                                     potential_signals=len(cg), attempts=len(ag), potential_without_attempt=len(cg)-len(ag),
                                     unfilled_attempts=len(ag)-len(tg), conversion=len(tg)/len(ag) if len(ag) else None,
                                     signal_share=len(ag)/len(ay) if len(ay) else None,
                                     trade_share=len(tg)/len(ty) if len(ty) else None,
                                     baseline_dd_net_contribution=float(tg[tg.event_id.isin(dd_events)].net.sum()) if year == 'all' else None,
                                     **trade_metrics(tg)))
            for candidate in CANDIDATES:
                ma, mt = membership(aa, candidate), membership(tt, candidate)
                x, y = tt[mt], tt[~mt]
                yearly = []
                for year in sorted(tt.year.unique()):
                    xx, yy = x[x.year == year], y[y.year == year]
                    yearly.append(dict(year=int(year), candidate=trade_metrics(xx), complement=trade_metrics(yy)))
                contrasts.append(dict(source=source, period=period, candidate=candidate,
                                      attempts_candidate=int(ma.sum()), attempts_complement=int((~ma).sum()),
                                      candidate_metrics=trade_metrics(x), complement_metrics=trade_metrics(y),
                                      differences=contrast(x, y, period), yearly=yearly))
    for source in SOURCES:
        for candidate in CANDIDATES:
            selected = [x for x in contrasts if x['source'] == source and x['candidate'] == candidate]
            assert len(selected) == 2
            enough = all(x[k]['fills'] >= 200 for x in selected for k in ('candidate_metrics', 'complement_metrics'))
            profitable = all(x['candidate_metrics']['pf'] is not None and x['candidate_metrics']['pf'] > 1 for x in selected)
            better = all(x['differences'][k]['difference'] is not None and x['differences'][k]['difference'] > 0
                         for x in selected for k in ('pf', 'avg_net_r'))
            yearly = [r for x in selected for r in x['yearly']]
            wins = sum(r['candidate']['fills'] >= 10 and r['complement']['fills'] >= 10 and
                       r['candidate']['avg_net_r'] > r['complement']['avg_net_r'] for r in yearly)
            decisions.append(dict(source=source, candidate=candidate, enough_trades=enough, profitable_both=profitable,
                                  better_both=better, better_years=int(wins), full_rerun_candidate=bool(enough and profitable and better and wins >= 7)))
    return rows, contrasts, decisions, dd_rows


def report(rows, decisions):
    f = pd.DataFrame(rows)
    def fmt(v, d=3):
        return 'n/a' if pd.isna(v) else f'{v:,.{d}f}'
    lines = ['# Q10: support interaction versus all other baseline signals', '',
             'Actual baseline outcomes, $1.05 round-trip cost. No filtered-strategy simulation.', '',
             '| Source | Period | Group | Potential signals | Attempts | Fills | Conversion % | Net $ | PF | Avg net R | Win % | Attributed closed DD $ |',
             '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in f[(f.year == 'all') & f.group.isin(['all', 'interaction', 'every_other', 'breach_reclaim', 'breach_unrecovered'])].itertuples():
        lines.append(f'| {r.source} | {r.period} | {r.group} | {r.potential_signals} | {r.attempts} | {r.fills} | {fmt(100*r.conversion, 1)} | {fmt(r.net, 2)} | {fmt(r.pf)} | {fmt(r.avg_net_r)} | {fmt(100*r.win_rate, 1)} | {fmt(r.attributed_closed_dd, 2)} |')
    lines += ['', 'Full rerun screening decisions:', '', '```json', json.dumps(decisions, indent=2), '```', '',
              'All groups and years: groups.csv. Exact candidate/complement intervals and years: contrasts.json.',
              'Potential census, baseline attempts and recorded trades are separate exports. Historical subset drawdowns are attribution only.']
    (STUDY/'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    print('Verifying baseline and enumerating all potential M30 signals...', flush=True)
    c, a, t, paths, checked = load()
    c.to_csv(STUDY/'potential_signals.csv', index=False)
    a.to_csv(STUDY/'attempts.csv', index=False)
    t.to_csv(STUDY/'trades.csv', index=False)
    print('Comparing actual strategy outcomes with the complete complement...', flush=True)
    rows, contrasts, decisions, dd = analyse(c, a, t)
    pd.DataFrame(rows).to_csv(STUDY/'groups.csv', index=False)
    pd.DataFrame(dd).to_csv(STUDY/'baseline_drawdowns.csv', index=False)
    for label, data in [('contrasts', contrasts), ('decisions', decisions)]:
        (STUDY/f'{label}.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    provenance = dict(upstream_hashes_checked=checked, potential_signals=len(c)//3, attempts=len(a)//3,
                      trades=len(t)//3, files=[dict(path=str(p), sha256=sha256(p)) for p in paths])
    (STUDY/'provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    report(rows, decisions)
    print(json.dumps({k: provenance[k] for k in ('potential_signals', 'attempts', 'trades')}))
    print(json.dumps(decisions, indent=2))


if __name__ == '__main__':
    main()
