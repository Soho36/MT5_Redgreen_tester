"""Independent minute replay and audit of daily RTL/monthly VWAP screening."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import rtl_weekly_engine as e
import analyze_rtl_vwap_cross as cx
from verify_exclude16_replay import DTYPE,maxdd
from prepare_rtl_daily_vwap import ROOT,RUN,DOC,DATA,SYMBOL,tag,sha

PERIODS={'2010-15':('2010-01-01','2016-01-01'),'2016-19':('2016-01-01','2020-01-01'),
 '2020-Sep2026':('2020-01-01','2026-10-01'),'Oct-Nov13_2026':('2026-10-01','2026-11-14'),
 '2016-Nov13_2026':('2016-01-01','2026-11-14'),'full':('2010-01-01','2026-11-14')}

def verify_features(bars,features):
    """Separate M1 reduction and explicit day-by-day cumulative/rolling calculation."""
    starts=np.flatnonzero(np.r_[True,np.diff(bars['day'])!=0])
    ends=np.r_[starts[1:]-1,len(bars['day'])-1]
    np.testing.assert_array_equal(features.index.to_numpy(dtype='datetime64[D]').astype('int64'),bars['day'][starts])
    for name,value in [('open',bars['o'][starts]),('high',np.maximum.reduceat(bars['h'],starts)),
                       ('low',np.minimum.reduceat(bars['l'],starts)),('close',bars['c'][ends])]:
        np.testing.assert_array_equal(features[name],value)
    volume=pd.read_csv(DATA,sep='\t',usecols=['<VOL>'])['<VOL>'].to_numpy(float)
    assert len(volume)==len(bars['o'])
    month=None;cum_pv=cum_vol=0.;ranges=[];previous=None
    for j,(a,b) in enumerate(zip(starts,ends)):
        r=features.iloc[j];date=features.index[j];m=(date.year,date.month)
        if m!=month:month=m;cum_pv=cum_vol=0.
        pv=np.dot((bars['h'][a:b+1]+bars['l'][a:b+1]+bars['c'][a:b+1])/3,volume[a:b+1])
        v=volume[a:b+1].sum();cum_pv+=pv;cum_vol+=v
        np.testing.assert_allclose([r.pv,r.volume,r.vwap],[pv,v,cum_pv/cum_vol],rtol=1e-12,atol=1e-7)
        if previous is not None:ranges.append(max(r.high-r.low,abs(r.high-previous),abs(r.low-previous)))
        if len(ranges)>=20:
            assert r.known
            assert abs(r.a20-sum(ranges[-20:])/20)<1e-9
        else:assert not r.known
        previous=r.close
    return dict(days=len(features),all_daily_ohlc_monthly_vwap_a20_match=True)

def allowed(signal,current_date):
    same=signal.name.year==current_date.year and signal.name.month==current_date.month
    known=bool(same and signal.known)
    return known,not(known and signal.close<signal.vwap-signal.a20)

def simulate(bars,features,start,gate=False):
    """Original RTL broker-before-EA ordering, D1 and held positions, no flatten."""
    day,minute=bars['day'],bars['minute']
    o,h,l,c=(bars[k] for k in 'ohlc')
    lowfirst=e.low_first(o,c)
    times=e.stamp_array(day,minute)
    first=int(np.searchsorted(times,np.datetime64(start)))
    feature_days=features.index.to_numpy(dtype='datetime64[D]').astype(np.int64)
    pos=pend=None;current_day=-1;trades=[];candidates=[];rejected=0
    def close(i,k,price,why):
        nonlocal pos
        trades.append({**pos,'exit_time':e.stamp(day[i],minute[i],k),'exit_price':price,'reason':why})
        pos=None
    for i in range(first,len(o)):
        new=day[i]!=current_day
        if new:current_day=day[i]
        if not new and (pend is None or h[i]<pend['requested']) and (pos is None or l[i]>pos['sl']):continue
        for k,p in enumerate(e.path(o[i],h[i],l[i],c[i],lowfirst[i])):
            if pos is not None and p<=pos['sl']:close(i,k,pos['sl'],'sl')
            if pend is not None and p>=pend['requested']:
                pos={**pend,'entry_time':e.stamp(day[i],minute[i],k),'fill':pend['requested']};pend=None
            if k or not new:continue
            j=int(np.searchsorted(feature_days,day[i]))-1
            if j<0:continue
            r=features.iloc[j]
            if pos is not None:
                if r.close>=2*pos['fill']-pos['sl']:close(i,k,p,'target')
                continue
            if r.close<r.open:
                pend=None
                known,keep=allowed(r,pd.Timestamp(e.stamp(day[i],0,0)))
                blocked=gate and not keep
                candidates.append(dict(time=e.stamp(day[i],minute[i],0),signal=r.name,close=r.close,
                                       known=int(known),blocked=int(blocked),vwap=r.vwap,a20=r.a20 if r.known else 0.))
                if blocked:continue
                if r.high-r.low<=0:continue
                if r.high<=p:rejected+=1;continue
                pend=dict(submitted=e.stamp(day[i],minute[i],0),requested=r.high,sl=r.low)
    if pos is not None:close(len(o)-1,3,c[-1],'end_of_data')
    cols=['submitted','requested','sl','entry_time','fill','exit_time','exit_price','reason']
    return pd.DataFrame(trades,columns=cols),pd.DataFrame(candidates),rejected

def audit_native(arm,bars,features):
    t=cx.parse_report(RUN/(tag(arm)+'.htm'),SYMBOL)
    ledger=pd.read_csv(RUN/f'runband_{tag(arm)}_1.00.csv',sep='\t',encoding='utf-16')
    stats=pd.read_csv(RUN/f'runband_{tag(arm)}_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
    assert len(t)==len(ledger)==int(stats.trades)
    np.testing.assert_array_equal(t.ticket,ledger.ticket)
    np.testing.assert_allclose(t.trade_profit,ledger.trade_profit,rtol=0,atol=1e-8)
    np.testing.assert_allclose(t.trade_profit,2*(t.exit_price-t.fill_price),rtol=0,atol=1e-8)
    assert abs(t.trade_profit.sum()-stats.net_profit)<1e-6
    start=pd.Timestamp((RUN/f'daily_start_{tag(arm)}.csv').read_text().strip())
    replay,candidates,rejected=simulate(bars,features,start,arm=='gated')
    replay.to_csv(RUN/f'replay_{arm}.csv',index=False)
    assert len(t)==len(replay),(arm,len(t),len(replay))
    for name in ('submitted','entry_time','exit_time'):
        np.testing.assert_array_equal(t[name].dt.floor('min'),pd.to_datetime(replay[name]).dt.floor('min'),err_msg=name)
    for a,b in [('requested_price','requested'),('fill_price','fill'),('original_sl','sl'),('exit_price','exit_price')]:
        np.testing.assert_allclose(t[a],replay[b],rtol=0,atol=1e-8,err_msg=a)
    reasons=np.select([t.exit_comment.str.startswith('sl'),t.exit_comment.str.startswith('end of test')],['sl','end_of_data'],'target')
    np.testing.assert_array_equal(reasons,replay.reason)
    saved=pd.read_csv(RUN/f'daily_candidates_{tag(arm)}.csv',sep='\t',parse_dates=['time','signal'])
    assert len(saved)==len(candidates),(len(saved),len(candidates))
    # Generated OHLC minutes with fewer distinct quotes can begin at :01/:30.
    # As for trade fills, compare candidate callback time at minute resolution.
    np.testing.assert_array_equal(saved.time.dt.floor('min'),pd.to_datetime(candidates.time).dt.floor('min'))
    np.testing.assert_array_equal(saved.signal,pd.to_datetime(candidates.signal))
    for name in ('close','known','blocked','vwap','a20'):
        np.testing.assert_allclose(saved[name],candidates[name],rtol=0,atol=1e-8,err_msg=name)
    eq=np.memmap(RUN/f'window_equity_{tag(arm)}.bin',mode='r',dtype=DTYPE)
    assert np.all(np.diff(eq['time'])>=0)
    assert t.exit_time.is_monotonic_increasing
    assert abs(eq['equity'][-1]-eq['balance'][-1])<1e-7
    assert abs(eq['balance'][-1]-500000.-t.trade_profit.sum())<1e-6
    missing=t.exit_time.to_numpy(dtype='datetime64[s]').astype('int64')
    missing=missing[~np.isin(missing,eq['time'])]
    assert len(missing)==0,'An unobserved closure needs an explicit fee observation'
    grossdd=maxdd(np.r_[500000.,eq['equity']])
    assert abs(grossdd-stats.equity_dd)<.011,(grossdd,stats.equity_dd)
    done=json.loads((RUN/(tag(arm)+'.completed.json')).read_text())
    for name,digest in done['outputs'].items():assert sha(RUN/name)==digest,name
    t['risk']=2*(t.requested_price-t.original_sl)
    assert t.risk.gt(0).all()
    t['net']=t.trade_profit-1.05;t['gross_r']=t.trade_profit/t.risk;t['net_r']=t.net/t.risk
    rolls=e.roll_switches(20261113,DATA.with_name(DATA.name.replace('_ohlcv-1m.csv','_rolls.csv')))
    roll_times=pd.to_datetime([str(d) for d in rolls],format='%Y%m%d').to_numpy()
    t['rolls_crossed']=np.searchsorted(roll_times,t.exit_time.to_numpy(),side='right')-np.searchsorted(roll_times,t.entry_time.to_numpy(),side='right')
    t.to_csv(RUN/f'trades_{arm}.csv',index=False)
    check=dict(trades=len(t),all_native_ledger_totals_match=True,all_replayed_trades_match=True,
        all_candidates_match=True,candidates=len(saved),known_candidates=int(saved.known.sum()),blocked_candidates=int(saved.blocked.sum()),
        candidate_intraminute_timestamp_differences=int(saved.time.ne(pd.to_datetime(candidates.time)).sum()),
        month_reset_unknown=int((saved.time.dt.to_period('M')!=saved.signal.dt.to_period('M')).sum()),
        replay_rejected_orders=rejected,start=str(start),gross_equity_dd=grossdd,native_gross_equity_dd=float(stats.equity_dd),
        trades_crossing_rolls=int(t.rolls_crossed.gt(0).sum()),report_sha256=sha(RUN/(tag(arm)+'.htm')))
    print('VERIFIED',arm,json.dumps(check),flush=True)
    return t,eq,check

def period_metrics(t,eq,start,end):
    part=t.loc[t.exit_time.ge(start)&t.exit_time.lt(end)]
    pnl=part.net;loss=-pnl.clip(upper=0).sum()
    lo,hi=[int(pd.Timestamp(x).timestamp()) for x in (start,end)]
    a,b=np.searchsorted(eq['time'],[lo,hi])
    exits=t.exit_time.to_numpy(dtype='datetime64[s]').astype('int64')
    count=np.searchsorted(exits,eq['time'][a:b],side='right')
    reference=500000. if a==0 else float(eq['equity'][a-1]-1.05*np.searchsorted(exits,eq['time'][a-1],side='right'))
    path=np.r_[reference,eq['equity'][a:b]-1.05*count]
    dd=maxdd(path)
    return dict(trades=len(part),net=float(pnl.sum()),gross=float(part.trade_profit.sum()),
        mean_gross_r=float(part.gross_r.mean()),mean_net_r=float(part.net_r.mean()),
        win_rate=float(pnl.gt(0).mean()),profit_factor=float(pnl.clip(lower=0).sum()/loss) if loss else np.nan,
        closed_dd=maxdd(np.r_[0.,pnl.cumsum()]),equity_dd=dd,net_equity_change=float(path[-1]-path[0]),
        net_equity_change_over_dd=float((path[-1]-path[0])/dd) if dd else np.nan,
        net_extra_1_cost=float(pnl.sum()-len(part)),trades_crossing_rolls=int(part.rolls_crossed.gt(0).sum()))

def plot(curves):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True,layout='constrained',height_ratios=[2,1])
    for arm,(t,eq) in curves.items():
        times=pd.to_datetime(eq['time'],unit='s')
        exits=t.exit_time.to_numpy(dtype='datetime64[s]').astype('int64')
        net=eq['equity']-1.05*np.searchsorted(exits,eq['time'],side='right')
        first=int(np.searchsorted(eq['time'],int(pd.Timestamp('2016-01-01').timestamp())))
        origin=net[first-1] if first else 500000.
        # Daily sampled plot, statistics use every native equity observation.
        daily=pd.Series(net[first:]-origin,index=times[first:]).groupby(times[first:].normalize()).last()
        label='Daily RTL' if arm=='baseline' else 'Daily RTL + monthly VWAP gate'
        axes[0].plot(daily.index,daily,label=label)
        axes[1].plot(daily.index,daily-np.maximum.accumulate(np.r_[0.,daily])[1:])
    axes[0].set_title('Daily RTL: monthly VWAP minus daily A20\nPositions held across month-end; raw continuous MNQ, $1.05 per trade')
    axes[0].set_ylabel('Net marked-to-market USD');axes[1].set_ylabel('Daily sampled\nequity drawdown, USD')
    axes[0].legend()
    for ax in axes:ax.grid(alpha=.2);ax.axhline(0,color='gray',lw=.6)
    (DOC/'img').mkdir(exist_ok=True)
    fig.savefig(DOC/'img/equity.png',dpi=150);plt.close(fig)

def main():
    manifest=json.loads((RUN/'manifest.json').read_text())
    for name,digest in manifest['input_hashes'].items():assert sha(Path(name))==digest,name
    bars=e.load_minutes(ROOT/'Reports/rtl_weekly_opposite_gate_20261117/minutes.npz')
    features=pd.read_csv(RUN/'daily_features.csv',parse_dates=['date'],index_col='date',float_precision='round_trip')
    checks=dict(features=verify_features(bars,features),jobs={})
    print('Independent daily features verified',flush=True)
    rows=[];curves={}
    scopes={**PERIODS,**{str(y):(f'{y}-01-01',min(f'{y+1}-01-01','2026-11-14')) for y in range(2010,2027)}}
    for arm in ('baseline','gated'):
        t,eq,check=audit_native(arm,bars,features)
        curves[arm]=(t,eq);checks['jobs'][arm]=check
        for period,(start,end) in scopes.items():rows.append(dict(period=period,arm=arm,**period_metrics(t,eq,start,end)))
    a,b=curves['baseline'][0],curves['gated'][0]
    fields=['submitted','entry_time','exit_time','requested_price','fill_price','original_sl','exit_price']
    joined=a.merge(b,on=fields,how='outer',indicator=True,suffixes=('_base','_gate'))
    checks['trade_attribution']=dict(identical=int(joined._merge.eq('both').sum()),
        baseline_only=int(joined._merge.eq('left_only').sum()),gated_only=int(joined._merge.eq('right_only').sum()))
    joined.to_csv(RUN/'trade_attribution.csv',index=False)
    summary=pd.DataFrame(rows);summary.to_csv(DOC/'summary.csv',index=False)
    checks['all_passed']=True;checks['protocol_sha256']=sha(DOC/'PROTOCOL.md')
    checks['code_sha256']=sha(Path(__file__))
    checks['source_minutes_cache_sha256']=sha(ROOT/'Reports/rtl_weekly_opposite_gate_20261117/minutes.npz')
    checks['summary_sha256']=sha(DOC/'summary.csv')
    (DOC/'verification.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
    plot(curves)
    print(summary.loc[summary.period.isin(PERIODS)].to_string(index=False),flush=True)
    print(checks['trade_attribution'],flush=True)
if __name__=='__main__':main()
