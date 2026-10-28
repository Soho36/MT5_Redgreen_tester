"""Full RTL MNQ replay: preserve 1R candle-close exits and add a resting 2R TP."""
from __future__ import annotations
import hashlib
import json
import numpy as np
import pandas as pd
import rtl_weekly_engine as e
from analyze_instrument_baseline import max_dd
from prepare_rtl_intrabar_tp import RUN, PROTOCOL

CACHE = e.ROOT/'Reports/rtl_weekly_flatten_20261027/minutes.npz'
REFERENCE = e.ROOT/'Reports/rtl_market_regimes_20261023/trades.csv'
COST = 1.05
ERAS = {'2010-15 reference': ('2010-01-01','2016-01-01'), '2016-19': ('2016-01-01','2020-01-01'),
        '2020-Sep2026': ('2020-01-01','2026-10-01')}


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def baseline_check(sim):
    mt = pd.read_csv(REFERENCE, parse_dates=['submitted','entry_time','exit_time'])
    sim = sim.loc[sim.entry_time.dt.floor('min') >= mt.entry_time.min().floor('min')].reset_index(drop=True)
    assert len(mt)==len(sim), (len(mt),len(sim))
    checks = {}
    for field in ('entry_time','exit_time','submitted'):
        checks[field] = int((sim[field].dt.floor('min') != mt[field].dt.floor('min')).sum())
    for left, right in [('requested','requested_price'),('fill','fill_price'),('sl','original_sl'),('exit_price','exit_price')]:
        checks[left] = int((~np.isclose(sim[left],mt[right],rtol=0,atol=1e-8)).sum())
    assert not any(checks.values()), checks
    return sim, dict(all_passed=True, trades=len(mt), mismatches=checks), mt.entry_time.min().floor('min')


def enrich(t):
    t = t.copy()
    t['gross'] = (t.exit_price-t.fill)*e.POINT_VALUE
    t['risk_dollars'] = (t.fill-t.sl)*e.POINT_VALUE
    t['gross_r'] = t.gross/t.risk_dollars
    t['net'] = t.gross-COST
    t['net_r'] = t.net/t.risk_dollars
    t['holding_minutes'] = (t.exit_time-t.entry_time).dt.total_seconds()/60
    return t


def metrics(t, extra=0):
    net=t.gross-COST-extra
    daily=net.groupby(t.exit_time.dt.normalize()).sum()
    return dict(trades=len(t), net_dollars=float(net.sum()),
                closed_trade_dd=max_dd(net.to_numpy()), daily_close_dd=max_dd(daily.to_numpy()),
                net_pf=float(net[net>0].sum()/-net[net<0].sum()), win_pct=float(100*(net>0).mean()),
                gross_r=float(t.gross_r.mean()), net_r=float((net/t.risk_dollars).mean()),
                holding_minutes=float(t.holding_minutes.mean()),
                intrabar_tp=int(t.reason.eq('intrabar_tp').sum()),
                close_target=int(t.reason.eq('target').sum()), stops=int(t.reason.eq('sl').sum()),
                flatten=int(t.reason.isin(['flatten','fallback']).sum()))


def main():
    manifest=json.loads((RUN/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['input_hashes'].items():
        assert sha(__import__('pathlib').Path(name))==expected, name
    bars=e.load_minutes(CACHE)
    print('Loaded',len(bars['o']),'minutes; replaying baseline.',flush=True)
    base,rejected=e.simulate_m30_ea(bars, cutoffs=e.load_cutoffs())
    base,check,start=baseline_check(base)
    (RUN/'baseline_validation.json').write_text(json.dumps(check,indent=2)+'\n',encoding='utf-8')
    print('Exact saved MT5 baseline:',check,flush=True)
    variants={'baseline':enrich(base)}
    for label, rr in [('tp2r',2.0)]:
        print('Replaying',label,flush=True)
        sim,rej=e.simulate_m30_ea(bars,cutoffs=e.load_cutoffs(),intrabar_rr=rr)
        sim=sim.loc[sim.entry_time>=start].reset_index(drop=True)
        variants[label]=enrich(sim)
    rows,annual=[],[]
    for name,t in variants.items():
        t.to_csv(RUN/f'trades_{name}.csv',index=False)
        for era,(lo,hi) in ERAS.items():
            p=t.loc[t.entry_time.ge(lo)&t.entry_time.lt(hi)&t.reason.ne('end_of_data')]
            for extra in (0.,1.,2.):
                rows.append(dict(variant=name,era=era,extra_cost=extra,**metrics(p,extra)))
        p=t.loc[t.entry_time.lt('2026-10-01')&t.reason.ne('end_of_data')]
        for year,g in p.groupby(p.entry_time.dt.year):
            annual.append(dict(variant=name,year=year,**metrics(g)))
    summary=pd.DataFrame(rows)
    summary.to_csv(RUN/'summary.csv',index=False)
    pd.DataFrame(annual).to_csv(RUN/'yearly.csv',index=False)
    # Same-entry attribution is descriptive; full replay above is the experiment.
    b=variants['baseline'].copy(); t=variants['tp2r'].copy()
    b['entry_minute']=b.entry_time.dt.floor('min'); t['entry_minute']=t.entry_time.dt.floor('min')
    paired=b.merge(t,on=['entry_minute','requested','sl'],suffixes=('_baseline','_tp2r'),validate='one_to_one')
    paired.to_csv(RUN/'paired_entries.csv',index=False)
    audit=dict(protocol_sha256=sha(PROTOCOL), baseline_check=check,
               cache=str(CACHE),cache_sha256=sha(CACHE),reference_sha256=sha(REFERENCE),
               first_included_entry_minute=str(start), last_minute=str(e.stamp(bars['day'][-1],bars['minute'][-1],3)),
               same_entry_pairs=len(paired), full_baseline_trades=len(b),full_tp_trades=len(t),
               execution='MT5 1-minute OHLC emulation; attached limit fills at level',
               maxdd='Net closed-trade and daily-close balance, not floating equity')
    (RUN/'analysis_audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    print(summary[summary.extra_cost.eq(0)].to_string(index=False,float_format=lambda x:f'{x:,.4f}'),flush=True)


if __name__=='__main__':
    main()
