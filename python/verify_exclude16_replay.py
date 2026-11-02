"""Reconcile eight native window/VWAP jobs and calculate generic equity drawdowns."""
import json
import sys
import numpy as np
import pandas as pd

import analyze_rtl_vwap_cross as cx
from analyze_rtl_vwap_slope import ROOT,CROSS,PERIODS,metrics,sha
from prepare_exclude16_replay import RUN,FEATURE

DTYPE=np.dtype([('time','<i8'),('balance','<f8'),('equity','<f8'),('closed','<i8')])
CONTROLS={
    ('rtl',False):ROOT/'Reports/ym_baselines_20261023/runband_ymbase_20261023_rtl_nq_1.00.csv',
    ('rtl',True):ROOT/'Reports/rtl_vwap_ea_20261028/rtlvwap_vwapea_20261028_file_1.00.csv',
    ('gg',False):ROOT/'Reports/gg_vwap_ea_20261030/rtlvwap_ggvwap_20261030_off_1.00.csv',
    ('gg',True):ROOT/'Reports/gg_vwap_ea_20261030/rtlvwap_ggvwap_20261030_on_1.00.csv'}


def maxdd(values):
    return float(np.max(np.maximum.accumulate(values)-values)) if len(values) else 0.


def equity_metrics(data,start,end,exits):
    lo=int(pd.Timestamp(start).timestamp());hi=int(pd.Timestamp(end).timestamp())
    a,b=np.searchsorted(data['time'],[lo,hi])
    part=data[a:b]
    assert len(part)>0
    before=data[a-1] if a else part[0]
    # Native deal timestamps are authoritative. Some transaction callbacks did
    # not expose DEAL_ENTRY in the original observer; do not use its counter.
    count=np.searchsorted(exits,part['time'],side='right')
    reference=float(before['equity']-1.05*np.searchsorted(exits,before['time'],side='right'))
    net=part['equity']-1.05*count
    path=np.r_[reference,net]
    gross=np.r_[float(before['equity']),part['equity']]
    days=part['time']//86400
    # Carry the last observed equity into each date as its opening reference.
    # This counts any overnight gap against the new date, relevant to trailing equity.
    boundaries=np.r_[0,np.flatnonzero(np.diff(days))+1,len(days)]
    worst=0.
    for i,j in zip(boundaries[:-1],boundaries[1:]):
        initial=net[i-1] if i else reference
        worst=max(worst,maxdd(np.r_[initial,net[i:j]]))
    # A separate linear state machine verifies vectorized DD without allocating a loop per tick.
    peak=reference;independent=0.
    for chunk in np.array_split(net,100):
        if not len(chunk):continue
        local=np.maximum.accumulate(np.r_[peak,chunk])[1:]
        independent=max(independent,float((local-chunk).max()));peak=max(peak,float(chunk.max()))
    assert abs(independent-maxdd(path))<1e-7
    late=part['equity']-1.05*np.searchsorted(exits,part['time'],side='left')
    timing_difference=abs(maxdd(path)-maxdd(np.r_[reference,late]))
    return dict(sampled_equity_dd=maxdd(path),sampled_gross_equity_dd=maxdd(gross),
                fee_timestamp_dd_sensitivity=timing_difference,
                worst_session_equity_dd=worst,equity_observations=len(part))


def main():
    manifest=json.loads((RUN/'manifest.json').read_text())
    for n,h in manifest['prepared_sha256'].items():assert sha(RUN/n)==h,n
    protocol='EXCLUDE_1630_FLATTEN_AMENDMENT.md' if manifest['jobs'][0].get('flatten') else 'EXCLUDE_16_PROTOCOL.md'
    assert sha(ROOT/'docs/baseline/rtl-vwap'/protocol)==manifest['protocol_sha256']
    f=pd.read_csv(RUN/FEATURE,sep='\t',float_precision='round_trip')
    f.index=pd.to_datetime(f.bar_epoch,unit='s')
    # Independently compare exported values to the frozen full-volume panel.
    panel=pd.read_csv(CROSS/'features_NQ.csv',float_precision='round_trip')
    panel.index=pd.to_datetime(panel.bar_time)
    p=panel.reindex(f.index)
    expected_known=p.a20.gt(0)&p.vwap_available
    assert np.array_equal(f.known.astype(bool),expected_known)
    for c in ('close','vwap','a20'):
        good=expected_known if c!='close' else np.ones(len(f),bool)
        np.testing.assert_allclose(f.loc[good,c],p.loc[good,c],rtol=0,atol=1e-9)
    cal=pd.read_csv(CROSS/'calendars.csv',parse_dates=['session'])
    cal=pd.DatetimeIndex(cal.loc[cal.instrument.eq('NQ'),'session']).sort_values()
    scopes=list(PERIODS.items())+[(str(y),(f'{y}-01-01',min(f'{y+1}-01-01','2026-10-01'))) for y in range(2010,2027)]
    checks=[];rows=[]
    for job in manifest['jobs']:
        tag=job['tag'];done=json.loads((RUN/(tag+'.completed.json')).read_text())
        for n,h in done['outputs'].items():assert sha(RUN/n)==h,n
        ledgerpath=RUN/f'rtlvwap_{tag}_1.00.csv'
        if not job['exclude']:assert ledgerpath.read_bytes()==CONTROLS[job['strategy'],job['vwap']].read_bytes(),tag
        econ=cx.economics(cx.parse_report(RUN/(tag+'.htm'),cx.INSTRUMENTS['NQ']['symbol']),cx.INSTRUMENTS['NQ'])
        ledger=pd.read_csv(ledgerpath,sep='\t',encoding='utf-16')
        native=ledger.set_index('ticket').loc[econ.ticket]
        assert len(native)==len(ledger)==len(econ)
        np.testing.assert_allclose(native.trade_profit,econ.trade_profit,rtol=0,atol=1e-7)
        np.testing.assert_allclose(econ.trade_profit,(econ.exit_price-econ.fill_price)*2,rtol=0,atol=1e-7)
        for c in ('entry_time','exit_time'):assert np.array_equal(pd.to_datetime(native[c]).to_numpy(),econ[c].to_numpy())
        stat=pd.read_csv(RUN/f'rtlvwap_{tag}_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
        assert stat.trades==len(econ) and abs(stat.net_profit-econ.trade_profit.sum())<1e-6
        if job['exclude']:assert not econ.submitted.dt.hour.eq(16).any(),tag
        flatten_checks={}
        if job.get('flatten'):
            events=pd.read_csv(RUN/f'flatten_events_{tag}.tsv',sep='\t')
            eventtime=pd.to_datetime(events.time)
            assert eventtime.dt.normalize().is_unique
            assert (eventtime.dt.hour*60+eventtime.dt.minute).ge(16*60+30).all()
            assert events.positions_after.eq(0).all() and events.orders_after.eq(0).all()
            flat_at=pd.Series(eventtime.to_numpy(),index=eventtime.dt.normalize()).reindex(econ.entry_time.dt.normalize())
            held=(econ.entry_time.to_numpy()<flat_at.to_numpy())&(econ.exit_time.to_numpy()>flat_at.to_numpy())
            assert not held.any(),'position survived forced flatten'
            flatten_checks=dict(flatten_events=len(events),positions_closed=int(events.positions_before.sum()),
                                delayed_events=int((eventtime.dt.hour*60+eventtime.dt.minute).gt(990).sum()))
        decisions=pd.read_csv(RUN/f'vwap_decisions_{tag}.csv',sep='\t',encoding='cp1252')
        signal=pd.to_datetime(decisions.signal_bar);time=pd.to_datetime(decisions.time)
        r=f.reindex(signal).reset_index(drop=True)
        known=r.known.eq(1)&pd.to_datetime(r.session_epoch,unit='s').eq(time.dt.normalize())
        expected=job['vwap']&known&r.close.lt(r.vwap-r.a20)
        assert np.array_equal(decisions.known.astype(bool),known)
        assert np.array_equal(decisions.blocked.astype(bool),expected)
        assert decisions.filter_line.eq('Orange cutoff').all()
        for c in ('vwap','a20'):np.testing.assert_allclose(decisions.loc[known,c],r.loc[known,c],rtol=0,atol=1e-9)
        assert not decisions.time.str.contains(' 16:').any() if job['exclude'] else True
        di=decisions.copy();di.index=pd.to_datetime(di.time)
        accepted=di.reindex(econ.submitted.dt.floor('30min'))
        assert accepted.blocked.eq(0).all()
        signal_rows=panel.reindex(pd.to_datetime(accepted.signal_bar)).reset_index(drop=True)
        inside=signal_rows.high.notna().to_numpy()
        assert econ.submitted.loc[~inside].ge('2026-10-01').all(),'missing signal within published sample'
        np.testing.assert_allclose(econ.requested_price.loc[inside],signal_rows.high.loc[inside],rtol=0,atol=1e-7)
        np.testing.assert_allclose(econ.original_sl.loc[inside],signal_rows.low.loc[inside],rtol=0,atol=1e-7)
        assert (signal_rows.close.loc[inside]<signal_rows.open.loc[inside]).all() if job['strategy']=='rtl' else (signal_rows.close.loc[inside]>signal_rows.open.loc[inside]).all()
        data=np.memmap(RUN/f'window_equity_{tag}.bin',dtype=DTYPE,mode='r')
        assert (np.diff(data['time'])>=0).all() and (np.diff(data['closed'])>=0).all()
        exits=np.sort(econ.exit_time.to_numpy().astype('datetime64[s]').astype(np.int64))
        assert np.searchsorted(exits,data['time'][-1],side='right')==len(econ)
        assert abs(data['balance'][-1]-500000-econ.trade_profit.sum())<1e-6
        assert abs(data['equity'][-1]-data['balance'][-1])<1e-7
        for period,(start,end) in scopes:
            part=econ.loc[econ.session.ge(start)&econ.session.lt(end)]
            days=cal[(cal>=start)&(cal<end)]
            m=metrics(part,days)
            exposure=part.entry_time.lt(pd.to_datetime(part.session)+pd.Timedelta(hours=17)) & part.exit_time.ge(pd.to_datetime(part.session)+pd.Timedelta(hours=16))
            rows.append(dict(strategy=job['strategy'],vwap=job['vwap'],exclude=job['exclude'],flatten=job.get('flatten',False),period=period,
                             **m,**equity_metrics(data,start,end,exits),fills_16=int(part.entry_time.dt.hour.eq(16).sum()),
                             trades_overlapping_16=int(exposure.sum())))
        econ.to_csv(RUN/(tag+'_trades.csv'),index=False,float_format='%.17g')
        checks.append(dict(tag=tag,trades=len(econ),control_byte_identical=not job['exclude'],
                           decisions=len(decisions),blocked=int(expected.sum()),equity_rows=len(data),
                           observer_counter=int(data['closed'][-1]),native_completed_trades=len(econ),
                           external_cost_source='native report exit timestamps',**flatten_checks))
        del data
    table=pd.DataFrame(rows);table.to_csv(RUN/'summaries.csv',index=False,float_format='%.17g')
    result=dict(all_passed=True,jobs=checks,native_ledger_report_economics=True,vwap_decisions=True,
                no_excluded_hour_submissions=True,sampled_equity_reconstruction=True,
                code_sha256=sha(__file__),summaries_sha256=sha(RUN/'summaries.csv'))
    (RUN/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(table.loc[table.period.eq('2016-26')].to_string(index=False))
    print('All eight jobs verified')


if __name__=='__main__':
    if len(sys.argv)>1:RUN=ROOT/sys.argv[1]
    main()
