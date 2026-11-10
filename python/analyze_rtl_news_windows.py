"""Verify native intraday exclusions against an independent full minute replay."""
import html
import json
import numpy as np
import pandas as pd
from prepare_rtl_news_windows import ROOT,RUN,DOC,BASE,TAG,TIME_CSV,WINDOW_CSV,sha
from analyze_rtl_news_days import session_envelopes,envelope_dd,CAL,DTYPE,maxdd,PERIODS,metrics
import analyze_rtl_vwap_cross as cx
from verify_rtl_failed_breakout_short import load_quote_index
from rtl_news_window_engine import simulate
from rtl_weekly_engine import load_cutoffs
from build_news_windows import window_ids

OLD=ROOT/'Reports/rtl_news_days_20261110'

def paired_week_interval(difference,draws=10000,seed=20261110):
    sums=difference.groupby(difference.index.to_period('W-SUN')).sum().to_numpy()
    rng=np.random.default_rng(seed);totals=[]
    for start in range(0,draws,500):
        totals.extend(sums[rng.integers(len(sums),size=(min(500,draws-start),len(sums)))].sum(axis=1))
    return np.quantile(totals,[.025,.975]).tolist()

def order_times(path):
    times=[];section=False
    with path.open(encoding='utf-16') as stream:
        for line in stream:
            if '>Orders<' in line:section=True
            if '>Deals<' in line:break
            if not section or '<tr' not in line or '</tr>' not in line:continue
            cells=[html.unescape(cx.TAG.sub('',t)).strip() for t in cx.CELL.findall(line)]
            if cells and cx.STAMP.match(cells[0]) and len(cells)==11 and cells[3]=='buy stop':times.append(cells[0])
    return pd.to_datetime(times,format='%Y.%m.%d %H:%M:%S')

def verify_simulation(q,trades,windows,mode):
    sim,rejected=simulate(q.b,windows,mode,load_cutoffs())
    sim=sim.loc[pd.to_datetime(sim.entry_time).dt.floor('min')>=trades.entry_time.min().floor('min')].reset_index(drop=True)
    assert len(sim)==len(trades),(mode,len(sim),len(trades))
    for key in ('entry_time','exit_time'):
        assert np.array_equal(pd.to_datetime(sim[key]).dt.floor('min'),trades[key].dt.floor('min')),(mode,key)
    assert np.array_equal(pd.to_datetime(sim.submitted).dt.floor('30min'),trades.submitted.dt.floor('30min'))
    for a,b in [('requested','requested_price'),('sl','original_sl'),('fill','fill_price'),('exit_price','exit_price')]:
        np.testing.assert_allclose(sim[a],trades[b],atol=1e-7,rtol=0,err_msg=f'{mode} {a}')
    sim.to_csv(RUN/f'independent_mode_{mode}_trades.csv',index=False)
    return dict(trades=len(sim),rejected_orders=rejected,news_exits=int(sim.reason.eq('news').sum()),
                all_prices_and_submission_bars_match=True,all_fill_exit_minutes_match=True)

def audit_actions(q,job,trades,windows,data):
    mode=job['mode'];tag=job['tag']
    actions=pd.read_csv(RUN/f'news_actions_{tag}.csv',sep='\t',parse_dates=['time','start','end'])
    if mode==0:
        assert actions.empty
        return dict(disabled=True)
    assert (window_ids(order_times(RUN/(tag+'.htm')),windows)<0).all(),'Submission inside window'
    assert actions.orders_after.eq(0).all()
    if mode==2:assert actions.positions_after.eq(0).all()
    starts=windows.start.to_numpy(dtype='datetime64[s]').astype('int64')
    ends=windows.end.to_numpy(dtype='datetime64[s]').astype('int64')
    first_quotes={}
    for w,(start,end) in enumerate(zip(starts,ends)):
        if start<int(data['time'][0]) or start>int(data['time'][-1]):continue
        idx=int(np.searchsorted(q.minute_epoch,start))
        if idx==len(q.minute_epoch) or q.minute_epoch[idx]>=end:continue
        first_quotes[w]=next(q.quotes(idx,idx+1))[0]
    first=actions.loc[actions['first'].eq(1)].set_index('window')
    assert set(first.index)==set(first_quotes),(set(first.index)^set(first_quotes))
    assert first.index.is_unique
    for a in actions.itertuples():
        assert a.start==windows.iloc[a.window].start and a.end==windows.iloc[a.window].end
        assert a.start<=a.time<a.end
    assert np.array_equal(first.time.to_numpy(dtype='datetime64[s]').astype('int64'),[first_quotes[w] for w in first.index])
    fill_windows=window_ids(trades.entry_time,windows)
    boundary=trades.loc[fill_windows>=0]
    for t,w in zip(boundary.itertuples(),fill_windows[fill_windows>=0]):
        assert t.entry_time==pd.Timestamp(first_quotes[w],unit='s'),('late window fill',t)
    exposures=[]
    for w,first_epoch in first_quotes.items():
        start,end=windows.iloc[w][['start','end']]
        exposed=trades.loc[trades.entry_time.lt(end)&trades.exit_time.gt(start)]
        for t in exposed.itertuples():
            seconds=(min(t.exit_time,end)-max(t.entry_time,start)).total_seconds()
            if seconds>0:exposures.append(dict(window=w,ticket=t.ticket,seconds=seconds))
        if mode==2:
            assert not (trades.entry_time.lt(end)&trades.exit_time.gt(pd.Timestamp(first_epoch,unit='s'))).any(),('surviving exposure',w)
    pd.DataFrame(exposures,columns=['window','ticket','seconds']).to_csv(RUN/f'{tag}_exposure.csv',index=False)
    delays=(first.time-first.start).dt.total_seconds()
    return dict(windows=len(first),cancelled_orders=int(actions.orders_before.sum()),
        boundary_fills=len(boundary),forced_closes=int(actions.positions_before.sum()) if mode==2 else 0,
        post_callback_flat=mode==2,positions_with_window_exposure=len({r['ticket'] for r in exposures}),
        exposure_minutes=sum(r['seconds'] for r in exposures)/60,
        delayed_first_quotes=int(delays.gt(0).sum()),max_delay_seconds=float(delays.max()),
        all_submissions_outside_windows=True,first_quotes_match_raw_data=True)

def native(job,q,windows,calendar):
    tag=job['tag'];done=json.loads((RUN/(tag+'.completed.json')).read_text())
    assert done['report_sha256']==sha(RUN/(tag+'.htm'))
    for name,h in done['outputs'].items():assert sha(RUN/name)==h
    t=cx.economics(cx.parse_report(RUN/(tag+'.htm'),cx.INSTRUMENTS['NQ']['symbol']),cx.INSTRUMENTS['NQ'])
    raw=pd.read_csv(RUN/job['outputs'][0],sep='\t',encoding='utf-16').set_index('ticket').loc[t.ticket]
    stats=pd.read_csv(RUN/job['outputs'][1],sep='\t',encoding='utf-16').iloc[0]
    assert len(t)==len(raw)==int(stats.trades)
    np.testing.assert_allclose(t.trade_profit,raw.trade_profit,atol=1e-7,rtol=0)
    np.testing.assert_allclose(t.requested_price-t.original_sl,raw.candle_range,atol=1e-7,rtol=0)
    for key in ('entry_time','exit_time'):
        assert np.array_equal(t[key],pd.to_datetime(raw[key]))
        assert (t[key].dt.normalize()==t.session).all()
    assert abs(t.trade_profit.sum()-stats.net_profit)<1e-6
    if job['mode']==0:assert (RUN/job['outputs'][0]).read_bytes()==(BASE/f'rtlvwap_{TAG}_1.00.csv').read_bytes()
    path=RUN/f'window_equity_{tag}.bin';data=np.memmap(path,mode='r',dtype=DTYPE)
    grossdd=maxdd(np.r_[500000.,data['equity']])
    assert abs(grossdd-stats.equity_dd)<.011,(tag,grossdd,stats.equity_dd)
    simulation=verify_simulation(q,t,windows,job['mode'])
    actions=audit_actions(q,job,t,windows,data)
    extended=calendar.union(pd.DatetimeIndex(t.session.unique())).sort_values()
    env=session_envelopes(path,t,extended)
    stress=t.copy();stress.net_dollars-=1;stress.net_r=stress.net_dollars/stress.initial_risk_dollars
    stress_env=session_envelopes(path,stress,extended,cost=2.05)
    t.to_csv(RUN/(tag+'_trades.csv'),index=False,float_format='%.17g')
    env.to_csv(RUN/(tag+'_envelopes.csv'),float_format='%.17g')
    check=dict(policy=job['policy'],trades=len(t),gross_equity_dd=grossdd,native_gross_equity_dd=float(stats.equity_dd),
               native_ledger_and_stats=True,simulation=simulation,actions=actions,flat_daily_boundaries=True,
               direct_and_compressed_dd_match=True,zero_profit_fee_events_added=env.attrs['virtual_zero_profit_closures'])
    print('Verified',job['policy'],len(t),'native trades and independent replay',flush=True)
    return t,env,stress_env,check

def main():
    manifest=json.loads((RUN/'manifest.json').read_text())
    for path,key in [(DOC/'PROTOCOL.md','protocol_sha256'),(TIME_CSV,'calendar_sha256'),(WINDOW_CSV,'windows_sha256')]:
        assert sha(path)==manifest[key]
    for name,h in manifest['prepared_sha256'].items():assert sha(RUN/name)==h
    assert sha(CAL)=='64be3ff61751cc8237c82f5c4adad9e70e73f698d59715195c5e8586b0866141'
    cal=pd.read_csv(CAL,parse_dates=['session']);calendar=pd.DatetimeIndex(cal.loc[cal.instrument.eq('NQ'),'session']).sort_values()
    windows=pd.read_csv(WINDOW_CSV,parse_dates=['start','end'])
    q=load_quote_index();print('Checked raw minute data against cache',len(q.minute_epoch),flush=True)
    trades={};daily={};stress_daily={};checks=[]
    for job in manifest['jobs']:
        p=job['policy'];trades[p],daily[p],stress_daily[p],check=native(job,q,windows,calendar);checks.append(check)
    # Reuse the already verified full-day replay; reconcile its saved summaries below.
    tag='news_20261110_skip_all';oldcheck=json.loads((OLD/'verification.json').read_text());assert oldcheck['all_passed']
    path=OLD/(tag+'_trades.csv');assert sha(path)==oldcheck['output_sha256'][path.name]
    t=pd.read_csv(path,parse_dates=['submitted','entry_time','exit_time','session'],float_precision='round_trip')
    trades['day']=t;extended=calendar.union(pd.DatetimeIndex(t.session.unique())).sort_values()
    eqpath=OLD/f'window_equity_{tag}.bin';oldjob=json.loads((OLD/(tag+'.completed.json')).read_text())
    assert sha(eqpath)==oldjob['outputs'][eqpath.name]
    daily['day']=session_envelopes(eqpath,t,extended)
    stress=t.copy();stress.net_dollars-=1
    stress_daily['day']=session_envelopes(eqpath,stress,extended,cost=2.05)
    scopes={**PERIODS,**{str(y):(f'{y}-01-01',min(f'{y+1}-01-01','2026-10-01')) for y in range(2010,2027)}}
    rows=[];sensitivity=[];comparisons=[]
    for period,(start,end) in scopes.items():
        days=calendar[(calendar>=start)&(calendar<end)]
        for policy,t in trades.items():
            part=t.loc[t.session.isin(days)];env=daily[policy].reindex(days,fill_value=0.)
            m=metrics(part,days);dd=envelope_dd(env)[0]
            stressed=part.copy();stressed.net_dollars-=1;stressed.net_r=stressed.net_dollars/stressed.initial_risk_dollars
            sm=metrics(stressed,days);sdd=envelope_dd(stress_daily[policy].reindex(days,fill_value=0.))[0]
            rows.append(dict(policy=policy,period=period,**m,equity_dd=dd,net_equity_dd=m['net_dollars']/dd,
                avg_net_trade=m['net_dollars']/len(part),stress_net=sm['net_dollars'],stress_equity_dd=sdd,
                stress_profit_factor=sm['profit_factor'],stress_net_equity_dd=sm['net_dollars']/sdd))
            if period in PERIODS and policy!='control':
                delta=env.net-daily['control'].reindex(days,fill_value=0.).net;ci=paired_week_interval(delta)
                comparisons.append(dict(period=period,policy=policy,net_change=float(delta.sum()),ci_low=ci[0],ci_high=ci[1]))
        if period not in PERIODS:continue
        kept=days[~days.year.isin([2013,2025,2026])]
        for policy,t in trades.items():
            part=t.loc[t.session.isin(kept)];dd=envelope_dd(daily[policy].reindex(kept,fill_value=0.))[0];m=metrics(part,kept)
            sensitivity.append(dict(period=period,policy=policy,**m,equity_dd=dd,net_equity_dd=m['net_dollars']/dd))
    summary=pd.DataFrame(rows);old=pd.read_csv(OLD/'summary.csv')
    for policy,oldpolicy in [('control','control'),('day','skip_all')]:
        a=summary.loc[summary.policy.eq(policy)].set_index('period');b=old.loc[old.policy.eq(oldpolicy)].set_index('period').loc[a.index]
        np.testing.assert_allclose(a[['trades','net_dollars','equity_dd']],b[['trades','net_dollars','equity_dd']],rtol=0,atol=1e-6)
    summary.to_csv(RUN/'summary.csv',index=False,float_format='%.17g')
    pd.DataFrame(comparisons).to_csv(RUN/'comparisons.csv',index=False)
    pd.DataFrame(sensitivity).to_csv(RUN/'schedule_sensitivity.csv',index=False)
    result=dict(all_passed=True,jobs=checks,raw_minutes=len(q.minute_epoch),old_day_benchmark_reconciled=True,
        bootstrap_draws=10000,seed=20261110,code_sha256={n:sha(ROOT/'python'/n) for n in ['analyze_rtl_news_windows.py','rtl_news_window_engine.py','analyze_rtl_news_days.py']},
        output_sha256={p.name:sha(p) for p in RUN.glob('*.csv')})
    (RUN/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(summary.loc[summary.period.isin(PERIODS),['period','policy','trades','net_dollars','equity_dd','net_equity_dd','stress_net']].to_string(index=False))

if __name__=='__main__':main()
