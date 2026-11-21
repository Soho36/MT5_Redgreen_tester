"""Independent raw-minute signal/exit verification and native study reporting."""
import json
import shutil
import numpy as np
import pandas as pd
from run_news_first_minute import ROOT,RUN,DOC,CAL,sha
from verify_rtl_failed_breakout_short import load_quote_index
from rtl_weekly_engine import load_cutoffs
from analyze_rtl_news_days import session_envelopes,envelope_dd,DTYPE,maxdd
from analyze_rtl_vwap_slope import PERIODS

def decision(o,h,l,c,bid,ask,distance=0):
    if c==o:return 'doji',0,0.,0.
    side=1 if c>o else -1;sl=l if side==1 else h;tp=h if side==1 else l
    entry=ask if side==1 else bid;closing=bid if side==1 else ask
    if side*(tp-c)<=0:status='zero_target_wick'
    elif side*(tp-entry)<=0 or side*(entry-sl)<=0:status='invalid_entry_levels'
    elif side*(tp-closing)<distance or side*(closing-sl)<distance:status='broker_stop_distance'
    else:status='entered'
    return status,side,sl,tp

def replay(q,row,entry_time,entry_price,cutoffs):
    day=int(pd.Timestamp(entry_time).normalize().timestamp());cut=day+cutoffs.get(int(row.date),1410)*60
    ent=int(pd.Timestamp(entry_time).timestamp());a=int(np.searchsorted(q.minute_epoch,ent//60*60));b=int(np.searchsorted(q.minute_epoch,day+86400))
    spread=row.ask-row.bid;ambiguous=False
    for i in range(a,b):
        # Exchange-traded custom futures: attached stops/targets trigger on Last
        # (the OHLC path), including shorts; market short exits still pay Ask.
        shift=0 if row.direction==1 else spread
        if q.b['l'][i]<=min(row.sl,row.tp) and q.b['h'][i]>=max(row.sl,row.tp):ambiguous=True
        for t,p in q.quotes(i,i+1):
            if t<=ent:continue
            closing=p+shift
            if row.direction*(p-row.sl)<=0:return t,row.sl,'sl',ambiguous
            if row.direction*(p-row.tp)>=0:return t,row.tp,'tp',ambiguous
            if t>=cut:return t,closing,'flatten',ambiguous
    raise AssertionError('Unclosed trade '+str(entry_time))

def main():
    manifest=json.loads((RUN/'manifest.json').read_text());assert sha(CAL)==manifest['calendar_sha256']
    assert sha(DOC/'PROTOCOL.md')==manifest['protocol_sha256']
    for n,h in manifest['prepared'].items():assert sha(RUN/n)==h
    q=load_quote_index();cutoffs=load_cutoffs();print('Raw M1 source verified',len(q.minute_epoch),flush=True)
    events=pd.read_csv(CAL);events=events.loc[events.event.isin(['CPI','PAYROLLS'])&events.research_time.str.endswith('15:30:00')]
    calframe=pd.read_csv(ROOT/'Reports/rtl_vwap_cross_20261027/calendars.csv',parse_dates=['session'])
    calendar=pd.DatetimeIndex(calframe.loc[calframe.instrument.eq('NQ'),'session']).sort_values()
    rows=[];checks=[];alltrades={};skiprows=[]
    scopes={**PERIODS,**{str(y):(f'{y}-01-01',min(f'{y+1}-01-01','2026-10-01')) for y in range(2010,2027)}}
    for job in manifest['jobs']:
        tag=job['tag'];policy=job['policy'];done=json.loads((RUN/(tag+'.completed.json')).read_text())
        for n,h in done['outputs'].items():assert sha(RUN/n)==h
        assert sha(RUN/(tag+'.htm'))==done['report_sha256']
        d=pd.read_csv(RUN/f'decisions_{tag}.csv',parse_dates=['time']);deals=pd.read_csv(RUN/f'deals_{tag}.csv',parse_dates=['time'])
        stats=pd.read_csv(RUN/f'stats_{tag}.csv').iloc[0]
        eligible=events if policy=='both' else events.loc[events.event.eq('CPI' if policy=='cpi' else 'PAYROLLS')]
        expected_dates=set(eligible.date.str.replace('-','').astype(int))&set(q.b['date'])
        assert set(d.date)==expected_dates and d.date.is_unique
        for r in d.itertuples():
            day=int(pd.Timestamp(str(r.date)).timestamp());sig=day+930*60;entry=day+931*60
            a=np.searchsorted(q.minute_epoch,sig);b=np.searchsorted(q.minute_epoch,entry)
            if b==len(q.minute_epoch) or q.minute_epoch[b]!=entry:
                assert r.status=='missing_entry_minute';continue
            if a==len(q.minute_epoch) or q.minute_epoch[a]!=sig:
                assert r.status=='missing_signal';continue
            o,h,l,c=[q.b[k][a] for k in 'ohlc']
            np.testing.assert_allclose([r.open,r.high,r.low,r.close],[o,h,l,c],rtol=0,atol=1e-8)
            t,p=next(q.quotes(b,b+1));assert int(r.time.timestamp())==t
            assert abs(p-r.bid)<1e-8
            status,side,sl,tp=decision(o,h,l,c,r.bid,r.ask,r.stops_distance)
            assert r.status==status,(r,status)
            assert r.direction==side and r.sl==sl and r.tp==tp
        assert set(deals.entry)<= {0,1};assert deals.volume.eq(1).all();assert deals[['commission','swap']].eq(0).all().all()
        trades=[]
        for position,g in deals.groupby('position',sort=False):
            assert len(g)==2 and g.entry.tolist()==[0,1]
            enter,leave=g.iloc[0],g.iloc[1];r=d.loc[d.deal.eq(enter.deal)].iloc[0]
            assert r.status=='entered' and enter.type==(0 if r.direction==1 else 1) and leave.type==1-enter.type
            assert enter.time==r.time
            price=r.ask if r.direction==1 else r.bid;assert abs(enter.price-price)<1e-7
            assert abs(enter.sl-r.sl)<1e-7 and abs(enter.tp-r.tp)<1e-7
            t,p,why,ambiguous=replay(q,r,enter.time,enter.price,cutoffs)
            assert pd.Timestamp(t,unit='s').floor('min')==leave.time.floor('min'),(position,t,leave.time)
            assert abs(p-leave.price)<1e-7,(position,p,leave.price)
            assert int(leave.reason)=={'sl':4,'tp':5,'flatten':3}[why]
            gross=(leave.price-enter.price)*r.direction*2
            assert abs(gross-g.profit.sum())<.011
            risk=abs(enter.price-r.sl)*2
            trades.append(dict(ticket=position,session=enter.time.normalize(),entry_time=enter.time,exit_time=leave.time,
                direction=r.direction,entry_price=enter.price,exit_price=leave.price,sl=r.sl,tp=r.tp,
                trade_profit=g.profit.sum(),net_dollars=g.profit.sum()-1.05,net_r=(g.profit.sum()-1.05)/risk,
                risk_dollars=risk,reward_risk=abs(r.tp-enter.price)/abs(enter.price-r.sl),exit_reason=why,ambiguous_minute=ambiguous))
        tr=pd.DataFrame(trades);assert len(tr)==stats.trades==d.status.eq('entered').sum()
        assert abs(tr.trade_profit.sum()-stats.profit)<1e-6
        data=np.memmap(RUN/f'window_equity_{tag}.bin',dtype=DTYPE,mode='r');grossdd=maxdd(np.r_[500000.,data['equity']])
        assert abs(grossdd-stats.equity_dd)<.011
        env=session_envelopes(RUN/f'window_equity_{tag}.bin',tr,calendar)
        tr.to_csv(RUN/f'{policy}_trades.csv',index=False);alltrades[policy]=tr
        for period,(start,end) in scopes.items():
            p=tr.loc[tr.session.ge(start)&tr.session.lt(end)];days=calendar[(calendar>=start)&(calendar<end)]
            net=p.net_dollars;daily=net.groupby(p.session).sum().reindex(days,fill_value=0.)
            dd=envelope_dd(env.reindex(days,fill_value=0.))[0];loss=-net[net<0].sum()
            rows.append(dict(policy=policy,period=period,trades=len(p),net=float(net.sum()),gross=float(p.trade_profit.sum()),
                win_rate=float(net.gt(0).mean()),profit_factor=float(net[net>0].sum()/loss) if loss else None,
                mean_net_r=float(p.net_r.mean()),avg_net=float(net.mean()),daily_dd=maxdd(np.r_[0,daily.cumsum()]),equity_dd=dd,
                stress_net=float(net.sum()-len(p)),median_reward_risk=float(p.reward_risk.median()),ambiguous_trades=int(p.ambiguous_minute.sum())))
        for status,count in d.status.value_counts().items():skiprows.append(dict(policy=policy,status=status,count=int(count)))
        checks.append(dict(policy=policy,events_observed=len(d),trades=len(tr),decisions_match=True,all_entries_and_exits_match=True,
            gross_equity_dd=grossdd,ambiguous_trades=int(tr.ambiguous_minute.sum()),forced_closes=int(tr.exit_reason.eq('flatten').sum()),
            missing_calendar_dates=sorted(set(eligible.date.str.replace('-','').astype(int))-expected_dates)))
        print('Verified',policy,len(tr),'trades',flush=True)
    fields=['session','entry_time','exit_time','direction','entry_price','exit_price','sl','tp','trade_profit']
    union=pd.concat([alltrades['cpi'],alltrades['payrolls']]).sort_values('entry_time').reset_index(drop=True)
    pd.testing.assert_frame_equal(alltrades['both'][fields].reset_index(drop=True),union[fields],check_dtype=False)
    summary=pd.DataFrame(rows);summary.to_csv(RUN/'summary.csv',index=False)
    skips=pd.DataFrame(skiprows);skips.to_csv(RUN/'decisions_summary.csv',index=False)
    verification=dict(all_passed=True,jobs=checks,subset_union_exact=True,code_sha256=sha(__file__),files={p.name:sha(p) for p in RUN.glob('*.csv')})
    (RUN/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    for name in ['summary.csv','decisions_summary.csv','verification.json']:shutil.copyfile(RUN/name,DOC/name)
    print(summary.loc[summary.period.isin(PERIODS)].to_string(index=False));print(skips.to_string(index=False))

if __name__=='__main__':main()
