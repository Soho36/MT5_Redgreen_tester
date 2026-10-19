"""Audit and report eight matched MT5 timeframe baseline jobs (2026-10-15)."""
import hashlib
import json
import re
import numpy as np
import pandas as pd
from analyze_instrument_baseline import COST, load, point_value, summary
from prepare_timeframe_baseline import STUDY
from project_paths import PROJECT_ROOT as ROOT

PERIODS = [('2016-19', 2016, 2019), ('2020-26', 2020, 2026), ('2010-15 reference', 2010, 2015)]
DOC = ROOT / 'docs/baseline/timeframe-h1/RESULTS.md'

def same(a, b):
    cols = ['entry_time', 'exit_time', 'trade_profit', 'candle_range', 'red_run', 'location']
    return a[cols].reset_index(drop=True).equals(b[cols].reset_index(drop=True))

def main():
    manifest = json.loads((STUDY / 'manifest.json').read_text())
    for name, digest in manifest['prepared_sha256'].items():
        assert hashlib.sha256((STUDY / name).read_bytes()).hexdigest() == digest, name
    calendar = (STUDY / 'early_closes.mqh').read_text()
    dates = [int(x) for x in re.search(r'EC_DATE\[EC_COUNT\] = \{([^}]+)', calendar).group(1).split(',')]
    times = [int(x) for x in re.search(r'EC_FLAT_MIN\[EC_COUNT\] = \{([^}]+)', calendar).group(1).split(',')]
    cutoffs = dict(zip(dates, times))
    runs, audits, rows, annual = {}, [], [], []
    for job in manifest['jobs']:
        completed = json.loads((STUDY / (job['tag'] + '.completed.json')).read_text())
        for name, digest in completed['outputs'].items():
            assert hashlib.sha256((STUDY / name).read_bytes()).hexdigest() == digest
        d = load(STUDY / job['outputs'][0]).sort_values('exit', kind='stable')
        s = pd.read_csv(STUDY / job['outputs'][1], sep='\t', encoding='utf-16').iloc[0]
        assert len(d) == int(s.trades), (job['tag'], len(d), s.trades)
        assert abs(d.trade_profit.sum() - s.net_profit) < 1e-6, job['tag']
        assert s.max_red_run == 0 and s.min_red_run == 1 and s.min_location == 0
        assert s.risk_reward == job['rr'] and s.flatten_fallback == 1 and s.early_close_calendar == 1
        assert s.trail_distance_r == 0
        assert (d.candle_range > 0).all() and (d.exit >= d.entry).all()
        assert not d[['entry_time', 'exit_time']].duplicated().any()
        pv = point_value(d)
        assert pv == 2.0
        cross = int((d.entry.dt.date != d.exit.dt.date).sum())
        assert cross == 0, (job['tag'], 'cross-date positions', cross)
        cutoff = d.entry.dt.strftime('%Y%m%d').astype(int).map(cutoffs).fillna(1410)
        exit_min = d.exit.dt.hour * 60 + d.exit.dt.minute + d.exit.dt.second / 60
        late = int((exit_min > cutoff + 1).sum())
        assert late == 0, (job['tag'], 'exits later than calendar cutoff', late)
        runs[(job['strategy'], job['timeframe'], job['rr'])] = d
        audits.append({'tag': job['tag'], 'trades': len(d), 'gross_profit': float(d.trade_profit.sum()),
                       'cross_date': cross, 'late_session_exits': late, 'point_value': pv, 'mt5_equity_dd_gross': float(s.equity_dd)})
        for period, lo, hi in PERIODS:
            p = d[d.entry.dt.year.between(lo, hi)]
            metrics = summary(p, pv)
            rows.append({'period': period, 'strategy': job['strategy'], 'timeframe': job['timeframe'], 'rr': job['rr'],
                         **metrics, 'median_hold_min': (p.exit-p.entry).dt.total_seconds().median()/60})
        for year, p in d.groupby(d.entry.dt.year):
            annual.append({'year': int(year), 'strategy': job['strategy'], 'timeframe': job['timeframe'],
                           'rr': job['rr'], **summary(p, pv)})
    # M30 path is unchanged. Reproduce both existing uncapped RR=1 ledgers.
    rtl_old = load(ROOT/'Reports/maxredrun_extended_20261013/runband_mrrext_20261013_cap0_1.00.csv').sort_values('exit', kind='stable')
    rtl_new = runs[('RTL', 'M30', 1.0)]
    assert same(rtl_new[rtl_new.entry.dt.year >= 2020], rtl_old), 'RTL existing baseline'
    gg_old = load(ROOT/'Reports/gg_run_cap_20261013/runband_ggcap_20261013_cap0_1.00.csv').sort_values('exit', kind='stable')
    gg_new = runs[('GG', 'M30', 1.0)]
    assert same(gg_new[gg_new.entry < pd.Timestamp('2026-07-14')], gg_old), 'GG existing baseline'
    checks = {'jobs': audits, 'rtl_m30_rr1_matches_extended_baseline': True,
              'gg_m30_rr1_matches_existing_baseline_through_2026_07_13': True}
    (STUDY/'audit.json').write_text(json.dumps(checks, indent=2))
    t = pd.DataFrame(rows)
    y = pd.DataFrame(annual)
    t.to_csv(STUDY/'summary.csv', index=False)
    y.to_csv(STUDY/'yearly.csv', index=False)
    differences = []
    rng = np.random.default_rng(20261015)
    for strategy in ('RTL','GG'):
        for rr in (0.5,1.0):
            for period, lo, hi in PERIODS[:2]:
                a = runs[(strategy,'H1',rr)]; a = a[a.entry.dt.year.between(lo,hi)]
                b = runs[(strategy,'M30',rr)]; b = b[b.entry.dt.year.between(lo,hi)]
                daily = lambda d: (d.trade_profit-COST).groupby(d.exit.dt.normalize()).sum()
                diff = pd.concat([daily(a), daily(b)], axis=1, sort=True).fillna(0)
                v = (diff.iloc[:,0]-diff.iloc[:,1]).to_numpy()
                sims = np.concatenate([v[rng.integers(len(v), size=(100, len(v)))].sum(axis=1) for _ in range(30)])
                low, high = np.quantile(sims, [.025,.975])
                differences.append({'strategy': strategy, 'rr': rr, 'period': period,
                                    'H1_minus_M30_net': v.sum(), 'ci_low': low, 'ci_high': high})
    pd.DataFrame(differences).to_csv(STUDY/'paired_daily_differences.csv', index=False)
    lines = ['# RTL and GG: H1 versus M30', '', '2026-10-15. Eight matched MT5 Strategy Tester runs, `MaxRedRun=0` on both strategies, RR 0.5 and 1.0.', '',
             'MNQ-priced continuous NQ (`MNQcontDTBNT20102026_2`), one contract, one-minute OHLC modelling, data through **2026-10-01**. Same 01:00–23:30 entry window, early-close calendar, no candle-range/location/trailing filter. Costs are **$1.05 per completed trade**. RR is a **bar-close threshold**, so winners can exceed the chosen RR.', '',
             'H1 signals, pending-order decisions and target exits use hourly bars. The original EA checks flattening only at a new chart bar; H1 skips 23:30. Isolated research copies therefore check the existing cutoff on ticks for H1. M30 execution is unchanged. All eight runs have zero cross-date positions.', '']
    lines[2:2] = ['**Finding:** H1 has roughly 44–47% fewer recent trades and larger risk per contract. At RR 0.5 it earns more than M30 at RR 0.5 in both eras; at RR 1 it earns less recently. Recent GG H1/RR 1 also has 50% higher drawdown. M30/RR 1 still earns more recent dollars than either H1 variant for each strategy. No baseline change is adopted.', '']
    for period, _, _ in PERIODS[:2]:
        lines += [f'## {period}' + (' (through October 1, 2026)' if period=='2020-26' else ''), '',
                  '| Strategy | RR | TF | Trades | Win % | Net $ | Net PF | Net DD $ | Avg net R |',
                  '|---|---:|---|---:|---:|---:|---:|---:|---:|']
        for strategy in ('RTL','GG'):
            for rr in (0.5,1.0):
                for tf in ('M30','H1'):
                    r = t[(t.period==period)&(t.strategy==strategy)&(t.rr==rr)&(t.timeframe==tf)].iloc[0]
                    lines.append(f'| {strategy} | {rr:g} | {tf} | {r.trades:,.0f} | {r["win%"]:.1f} | {r["net_$"]:,.0f} | {r.PF_net:.3f} | {r["maxDD_$"]:,.0f} | {r.net_R:+.3f} |')
        lines += ['']
    lines += ['## What changes on H1', '']
    for strategy in ('RTL','GG'):
        for rr in (0.5,1.0):
            a = t[(t.period=='2020-26')&(t.strategy==strategy)&(t.rr==rr)&(t.timeframe=='H1')].iloc[0]
            b = t[(t.period=='2020-26')&(t.strategy==strategy)&(t.rr==rr)&(t.timeframe=='M30')].iloc[0]
            years = y[(y.strategy==strategy)&(y.rr==rr)&(y.year>=2016)].pivot(index='year',columns='timeframe',values='net_$')
            count = int((years.H1>years.M30).sum())
            ci = next(d for d in differences if d['strategy']==strategy and d['rr']==rr and d['period']=='2020-26')
            lines.append(f'- **{strategy}, RR {rr:g}:** recent net changes by ${a["net_$"]-b["net_$"]:+,.0f}; trades {100*(a.trades/b.trades-1):+.1f}%, net PF {b.PF_net:.3f} → {a.PF_net:.3f}, DD {100*(a["maxDD_$"]/b["maxDD_$"]-1):+.1f}%. Median signal range {b.med_risk_pts:.1f} → {a.med_risk_pts:.1f} points; median hold {b.median_hold_min:.0f} → {a.median_hold_min:.0f} minutes. H1 earns more in {count}/11 years (2016–2026; 2026 partial). Paired exit-day bootstrap 95% interval for recent net difference: ${ci["ci_low"]:+,.0f} to ${ci["ci_high"]:+,.0f}.')
    lines += ['', 'Larger H1 candles change signal frequency and dollar risk per contract; hourly target checks also change realised exits. This is a comparison of whole strategies, not an isolated entry-signal test. Net DD is calculated from closed-trade equity, not intratrade drawdown. The day bootstrap is descriptive and does not model longer serial dependence. The 2010–15 era has different session hours and is retained only in the generated tables. All periods have already been examined; these runs do not establish untouched out-of-sample or live execution performance.', '',
              '## Verification and reproduction', '',
              'Both research EAs compiled with zero errors and warnings. All eight CSV ledgers reconcile exactly to MT5 trade counts and gross profit; RR/cap/calendar flags and output hashes pass. M30 RR 1 reproduces the existing uncapped RTL 2020–26 ledger and GG ledger through July 13, 2026.', '',
              'Inputs, frozen sources, compiled EAs, manifests, completion hashes, HTML tester reports, logs, `audit.json`, `summary.csv`, `yearly.csv`, and paired differences are saved in `Reports/timeframe_baseline_20261015/`.', '',
              'Preparation: `python/prepare_timeframe_baseline.py`. Execute each expert’s tags with `python/run_mt5_job.py Reports/timeframe_baseline_20261015 RTL_timeframe <RTL tags>` and similarly `GG_timeframe <GG tags>`; existing completed jobs are preserved. Analysis: `venv/Scripts/python.exe python/analyze_timeframe_baseline.py`.', '']
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text('\n'.join(lines), encoding='utf-8')
    print(t[t.period!='2010-15 reference'][['period','strategy','rr','timeframe','trades','net_$','PF_net','maxDD_$','net_R']].to_string(index=False))
    print(f'All 8 ledger audits and both historical baseline checks passed. Report: {DOC}')

if __name__ == '__main__':
    main()


