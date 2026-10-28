"""Verify both native historical MT5 arms and rebuild final tables from native fills."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
import analyze_rtl_market_regimes as parser
from analyze_instrument_baseline import load
from analyze_rtl_intrabar_tp import ERAS, REFERENCE, enrich, metrics, sha
from prepare_rtl_intrabar_tp import RUN, BASE, EXPERT


def main():
    checks={}
    summaries=[]; annual=[]; native_runs={}
    for variant in ('baseline','tp2r'):
        tag=f'intrabar_tp_20261027_{variant}'
        parser.HTML=RUN/(tag+'.htm')
        native=parser.parse_report()
        raw_path=RUN/f'runband_{tag}_1.00.csv'
        stats_path=RUN/f'runband_{tag}_1.00_stats.csv'
        raw=load(raw_path)
        stats=pd.read_csv(stats_path,sep='\t',encoding='utf-16').iloc[0]
        assert len(native)==len(raw)==int(stats.trades)
        assert (native.ticket==raw.ticket).all()
        assert np.allclose(native.trade_profit,raw.trade_profit,rtol=0,atol=1e-8)
        assert abs(native.trade_profit.sum()-stats.net_profit)<1e-6
        done=json.loads((RUN/(tag+'.completed.json')).read_text(encoding='utf-8'))
        for name,h in done['outputs'].items(): assert sha(RUN/name)==h
        if variant=='baseline':
            old=pd.read_csv(REFERENCE,parse_dates=['submitted','entry_time','exit_time'])
            assert len(old)==len(native)
            for col in ('ticket','submitted','entry_time','exit_time','requested_price','original_sl','fill_price','exit_price','trade_profit'):
                assert (native[col]==old[col]).all(),col
        sim=pd.read_csv(RUN/f'trades_{variant}.csv',parse_dates=['submitted','entry_time','exit_time'])
        assert len(native)==len(sim),(variant,len(native),len(sim))
        counts={}
        for field in ('submitted','entry_time','exit_time'):
            counts[field]=int((native[field].dt.floor('min')!=sim[field].dt.floor('min')).sum())
        for n,s in [('requested_price','requested'),('original_sl','sl'),('fill_price','fill'),('exit_price','exit_price'),('trade_profit','gross')]:
            counts[n]=int((~np.isclose(native[n],sim[s],rtol=0,atol=1e-8)).sum())
        assert not any(counts.values()),(variant,counts)
        tp=native.exit_comment.str.startswith('tp ')
        stop=native.exit_comment.str.startswith('sl ')
        assert np.array_equal(tp,sim.reason.eq('intrabar_tp'))
        assert np.array_equal(stop,sim.reason.eq('sl'))
        if tp.any():
            assert np.allclose(native.loc[tp,'exit_price'],native.loc[tp,'fill_price']+2*(native.loc[tp,'fill_price']-native.loc[tp,'original_sl']),rtol=0,atol=1e-8)
        n=native.rename(columns={'requested_price':'requested','original_sl':'sl','fill_price':'fill'}).copy()
        n['reason']=sim.reason.to_numpy()
        n=enrich(n)
        n.to_csv(RUN/f'native_{variant}.csv',index=False)
        native_runs[variant]=n
        for era,(lo,hi) in ERAS.items():
            p=n.loc[n.entry_time.ge(lo)&n.entry_time.lt(hi)&n.reason.ne('end_of_data')]
            for extra in (0.,1.,2.):
                summaries.append(dict(variant=variant,era=era,extra_cost=extra,**metrics(p,extra)))
        p=n.loc[n.entry_time.lt('2026-10-01')&n.reason.ne('end_of_data')]
        for year,g in p.groupby(p.entry_time.dt.year): annual.append(dict(variant=variant,year=year,**metrics(g)))
        checks[variant]=dict(trades=len(native),native_profit=float(native.trade_profit.sum()),mismatches=counts,
                             native_report_sha256=sha(parser.HTML),native_raw_sha256=sha(raw_path),stats_sha256=sha(stats_path))
    # Keep the final tables native; simulator tables remain available for reproduction.
    summary=pd.DataFrame(summaries)
    summary.to_csv(RUN/'summary_native.csv',index=False)
    pd.DataFrame(annual).to_csv(RUN/'yearly_native.csv',index=False)
    b=native_runs['baseline'];t=native_runs['tp2r']
    pairs=b.merge(t,on=['entry_time','requested','sl'],suffixes=('_base','_tp2r'),validate='one_to_one')
    pairs['net_change']=pairs.net_tp2r-pairs.net_base
    pairs.to_csv(RUN/'paired_native.csv',index=False)
    attribution=[]
    for era,(lo,hi) in ERAS.items():
        a=b[b.entry_time.ge(lo)&b.entry_time.lt(hi)&b.reason.ne('end_of_data')]
        z=t[t.entry_time.ge(lo)&t.entry_time.lt(hi)&t.reason.ne('end_of_data')]
        p=pairs[pairs.entry_time.ge(lo)&pairs.entry_time.lt(hi)&pairs.reason_base.ne('end_of_data')]
        new=z[~z.entry_time.isin(p.entry_time)];removed=a[~a.entry_time.isin(p.entry_time)]
        delta=p.net_change.sum()+new.net.sum()-removed.net.sum()
        assert abs(delta-(z.net.sum()-a.net.sum()))<1e-6
        attribution.append(dict(era=era,shared=len(p),changed_exits=int(p.exit_time_base.ne(p.exit_time_tp2r).sum()),
             shared_net_change=p.net_change.sum(),new_trades=len(new),new_net=new.net.sum(),
             removed_trades=len(removed),removed_net=removed.net.sum(),total_net_change=delta))
    pd.DataFrame(attribution).to_csv(RUN/'attribution_native.csv',index=False)
    checks.update(all_passed=True,baseline_native_exact=True,generated_tick_order='attached TP executable after pending-fill quote',
                  tables_source='native MT5 reports',closed_drawdown='net closed balance; floating drawdown not reconstructed')
    (RUN/'verification.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(checks,indent=2))
    print(summary[summary.extra_cost.eq(0)].to_string(index=False,float_format=lambda x:f'{x:,.4f}'))
    print(pd.DataFrame(attribution).to_string(index=False))


if __name__=='__main__': main()
