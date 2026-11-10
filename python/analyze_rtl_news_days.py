"""Audit native news exclusions, reconstruct equity, and run matched-day controls."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from build_news_calendar import ROOT,RUN,OUT,DOC,sha
from prepare_rtl_news_days import BASE,TAG,POLICIES
from analyze_rtl_vwap_slope import PERIODS,metrics
import analyze_rtl_vwap_cross as cx
from verify_exclude16_replay import DTYPE,maxdd

COST=1.05
DRAWS=10000
SEED=20261110
CAL=ROOT/'Reports/rtl_vwap_cross_20261027/calendars.csv'

def event_masks(calendar,events):
    return {name:calendar.isin(events.loc[events.event.isin(types),'date'])
            for name,types in {'skip_cpi':['CPI'],'skip_payrolls':['PAYROLLS'],
                               'skip_fomc':['FOMC'],'skip_all':['CPI','PAYROLLS','FOMC']}.items()}

def session_envelopes(path,trades,calendar):
    """Sufficient statistics for exact DD under whole-session omission.

    Store each day's net change, min/max relative equity, and internal DD. With
    flat boundaries these reproduce any concatenation of retained session paths.
    """
    data=np.memmap(path,mode='r',dtype=DTYPE)
    times=data['time']
    assert np.all(np.diff(times)>=0)
    exits=np.sort(trades.exit_time.to_numpy().astype('datetime64[s]').astype(np.int64))
    # The passive observer deduplicates unchanged gross equity. A zero-profit
    # closing deal can therefore have no saved sample, but its external fee must
    # still be charged at that close, not on the following day's first quote.
    missing_closures=exits[~np.isin(exits,times)]
    if len(missing_closures):
        closing=trades.set_index('exit_time').loc[pd.to_datetime(missing_closures,unit='s')]
        assert closing.trade_profit.eq(0).all(),'Unobserved nonzero closing deal'
        indices=np.searchsorted(times,missing_closures,side='right')-1
        assert (indices>=0).all()
        virtual=np.array(data[indices],copy=True)
        assert np.allclose(virtual['equity'],virtual['balance'],atol=1e-7,rtol=0)
        virtual['time']=missing_closures
        data=np.concatenate([data,virtual])
        data=data[np.argsort(data['time'],kind='stable')]
        times=data['time']
    count=np.searchsorted(exits,times,side='right')
    equity=data['equity']-COST*count
    days=times//86400
    bounds=np.r_[0,np.flatnonzero(np.diff(days))+1,len(data)]
    rows=[]
    previous=500000.
    for a,b in zip(bounds[:-1],bounds[1:]):
        date=pd.Timestamp(int(days[a]),unit='D')
        path=np.r_[0.,equity[a:b]-previous]
        assert abs(data['equity'][b-1]-data['balance'][b-1])<1e-7,('nonflat',date)
        rows.append(dict(session=date,net=path[-1],low=path.min(),high=path.max(),dd=maxdd(path)))
        previous=float(equity[b-1])
    daily=pd.DataFrame(rows).set_index('session')
    ledger=trades.groupby('session').net_dollars.sum()
    np.testing.assert_allclose(daily.net,ledger.reindex(daily.index,fill_value=0.),atol=2e-7,rtol=0)
    missing=daily.loc[~daily.index.isin(calendar)]
    assert missing[['net','low','high','dd']].abs().max().fillna(0).max()<1e-7
    daily=daily.reindex(calendar,fill_value=0.)
    daily.attrs['virtual_zero_profit_closures']=len(missing_closures)
    # Independently compare compressed DD against the full native path for each era.
    for name,(start,end) in PERIODS.items():
        a,b=np.searchsorted(times,[int(pd.Timestamp(start).timestamp()),int(pd.Timestamp(end).timestamp())])
        initial=equity[a-1] if a else 500000.
        direct=maxdd(np.r_[initial,equity[a:b]])
        part=daily.loc[(daily.index>=start)&(daily.index<end)]
        assert abs(envelope_dd(part)[0]-direct)<1e-6,(name,direct,envelope_dd(part))
    return daily

def envelope_dd(daily,keep=None):
    if keep is None:keep=np.ones((1,len(daily)),dtype=bool)
    else:keep=np.atleast_2d(keep)
    net=keep*daily.net.to_numpy()
    before=np.cumsum(net,axis=1)-net
    high=before+keep*daily.high.to_numpy()
    low=before+keep*daily.low.to_numpy()
    prior_peak=np.maximum.accumulate(np.c_[np.zeros(len(keep)),high],axis=1)[:,:-1]
    dd=np.maximum(prior_peak-low,keep*daily.dd.to_numpy()).max(axis=1)
    return dd

def matched_random(daily,removed,seed=SEED,draws=DRAWS):
    rng=np.random.default_rng(seed)
    labels=daily.index.year*10+daily.index.dayofweek
    strata=[(np.flatnonzero(labels==k),int(removed[labels==k].sum())) for k in np.unique(labels)]
    output=[]
    for start in range(0,draws,250):
        n=min(250,draws-start)
        keep=np.ones((n,len(daily)),bool)
        for ids,count in strata:
            if count:
                chosen=np.argsort(rng.random((n,len(ids))),axis=1)[:,:count]
                keep[np.arange(n)[:,None],ids[chosen]]=False
        net=(keep*daily.net.to_numpy()).sum(axis=1)
        dd=envelope_dd(daily,keep)
        output.append(pd.DataFrame(dict(net=net,equity_dd=dd,net_dd=np.divide(net,dd,out=np.full(n,np.nan),where=dd>0))))
    return pd.concat(output,ignore_index=True)

def weekly_interval(daily,removed,seed=SEED,draws=DRAWS):
    difference=-daily.net.to_numpy()*removed
    weeks=daily.index.to_period('W-SUN')
    sums=pd.Series(difference).groupby(weeks).sum().to_numpy()
    rng=np.random.default_rng(seed)
    totals=[]
    for start in range(0,draws,500):
        totals.extend(sums[rng.integers(len(sums),size=(min(500,draws-start),len(sums)))].sum(axis=1))
    return np.quantile(totals,[.025,.975]).tolist()

def validate_native(job,baseline,events,calendar):
    tag=job['tag']
    done=json.loads((RUN/(tag+'.completed.json')).read_text())
    assert done['report_sha256']==sha(RUN/(tag+'.htm'))
    for name,value in done['outputs'].items():assert sha(RUN/name)==value,name
    trades=cx.economics(cx.parse_report(RUN/(tag+'.htm'),cx.INSTRUMENTS['NQ']['symbol']),cx.INSTRUMENTS['NQ'])
    raw=pd.read_csv(RUN/job['outputs'][0],sep='\t',encoding='utf-16')
    stats=pd.read_csv(RUN/job['outputs'][1],sep='\t',encoding='utf-16').iloc[0]
    assert len(trades)==len(raw)==int(stats.trades)
    np.testing.assert_allclose(raw.set_index('ticket').loc[trades.ticket,'trade_profit'],trades.trade_profit,atol=1e-7,rtol=0)
    assert abs(trades.trade_profit.sum()-stats.net_profit)<1e-6
    assert (trades.entry_time.dt.normalize()==trades.session).all()
    assert (trades.exit_time.dt.normalize()==trades.session).all()
    removed=np.zeros(len(baseline),bool) if job['mask']==0 else event_masks(pd.DatetimeIndex(baseline.session),events)[job['policy']]
    expected=baseline.loc[~removed].reset_index(drop=True)
    fields=['submitted','requested_price','original_sl','entry_time','fill_price','exit_time','exit_price','trade_profit']
    pd.testing.assert_frame_equal(trades[fields].reset_index(drop=True),expected[fields],check_dtype=False,check_exact=True)
    if job['mask']==0:
        assert (RUN/job['outputs'][0]).read_bytes()==(BASE/f'rtlvwap_{TAG}_1.00.csv').read_bytes()
    path=RUN/f'window_equity_{tag}.bin'
    # Calendar extends through the final tester date for the accounting audit.
    extended=calendar.union(pd.DatetimeIndex(trades.session.unique())).sort_values()
    daily=session_envelopes(path,trades,extended)
    trades.to_csv(RUN/(tag+'_trades.csv'),index=False,float_format='%.17g')
    return trades,daily,dict(policy=job['policy'],trades=len(trades),exact_session_omission=True,flat_boundaries=True,
                             independent_full_path_dd=True,output_hashes=True,
                             zero_profit_fee_events_added=daily.attrs['virtual_zero_profit_closures'])

def main():
    manifest=json.loads((RUN/'manifest.json').read_text())
    assert sha(DOC/'PROTOCOL.md')==manifest['protocol_sha256']
    assert sha(OUT/'us_major_news_2010_2026.csv')==manifest['calendar_sha256']
    for name,value in manifest['prepared_sha256'].items():assert sha(RUN/name)==value
    events=pd.read_csv(OUT/'us_major_news_2010_2026.csv',parse_dates=['date'])
    calframe=pd.read_csv(CAL,parse_dates=['session'])
    calendar=pd.DatetimeIndex(calframe.loc[calframe.instrument.eq('NQ'),'session']).sort_values()
    assert sha(CAL)=='64be3ff61751cc8237c82f5c4adad9e70e73f698d59715195c5e8586b0866141'
    # Parse the old native baseline afresh rather than trust a derived CSV.
    baseline=cx.economics(cx.parse_report(BASE/(TAG+'.htm'),cx.INSTRUMENTS['NQ']['symbol']),cx.INSTRUMENTS['NQ'])
    olddone=json.loads((BASE/(TAG+'.completed.json')).read_text())
    assert sha(BASE/f'rtlvwap_{TAG}_1.00.csv')==olddone['outputs'][f'rtlvwap_{TAG}_1.00.csv']
    rows=[];checks=[];all_trades={};all_daily={}
    scopes=dict(PERIODS)
    scopes.update({str(y):(f'{y}-01-01',min(f'{y+1}-01-01','2026-10-01')) for y in range(2010,2027)})
    for job in manifest['jobs']:
        trades,daily,check=validate_native(job,baseline,events,calendar)
        checks.append(check);all_trades[job['policy']]=trades;all_daily[job['policy']]=daily
        print('Verified',job['policy'],len(trades),'trades',flush=True)
        for period,(start,end) in scopes.items():
            days=calendar[(calendar>=start)&(calendar<end)]
            part=trades.loc[trades.session.ge(start)&trades.session.lt(end)]
            env=daily.reindex(days,fill_value=0.)
            m=metrics(part,days);dd=envelope_dd(env)[0]
            basepart=baseline.loc[baseline.session.ge(start)&baseline.session.lt(end)]
            skip=np.zeros(len(days),bool) if job['mask']==0 else event_masks(days,events)[job['policy']]
            rows.append(dict(policy=job['policy'],period=period,sessions=len(days),removed_sessions=int(skip.sum()),
                             removed_trades=len(basepart)-len(part),**m,equity_dd=dd,net_equity_dd=m['net_dollars']/dd,
                             avg_net_trade=m['net_dollars']/len(part),worst_session_dd=float(env.dd.max())))
    summary=pd.DataFrame(rows)
    for policy,native in all_daily.items():
        expected=all_daily['control'].reindex(native.index,fill_value=0.).copy()
        if policy!='control':expected.loc[event_masks(native.index,events)[policy],:]=0.
        np.testing.assert_allclose(native[['net','low','high','dd']],expected[['net','low','high','dd']],atol=1e-6,rtol=0)
    summary.to_csv(RUN/'summary.csv',index=False,float_format='%.17g')
    daily=all_daily['control'].reindex(calendar,fill_value=0.)
    daily.to_csv(RUN/'baseline_session_envelopes.csv',float_format='%.17g')
    comparisons=[];sensitivity=[]
    for p,(start,end) in PERIODS.items():
        env=daily.loc[(daily.index>=start)&(daily.index<end)]
        for policy,removed in event_masks(env.index,events).items():
            observed=summary.loc[summary.policy.eq(policy)&summary.period.eq(p)].iloc[0]
            control=summary.loc[summary.policy.eq('control')&summary.period.eq(p)].iloc[0]
            placebo=matched_random(env,removed)
            placebo.to_csv(RUN/f'placebo_{p}_{policy}.csv',index=False)
            ci=weekly_interval(env,removed)
            comparisons.append(dict(period=p,policy=policy,net_change=observed.net_dollars-control.net_dollars,
                equity_dd_change=observed.equity_dd-control.equity_dd,net_change_ci_low=ci[0],net_change_ci_high=ci[1],
                random_net_median=placebo.net.median(),random_dd_median=placebo.equity_dd.median(),
                net_percentile=float((placebo.net<=observed.net_dollars).mean()*100),
                dd_better_percent=float((placebo.equity_dd>=observed.equity_dd).mean()*100),
                net_dd_percentile=float((placebo.net_dd<=observed.net_equity_dd).mean()*100)))
        print('Completed matched-day controls',p,flush=True)
    # Omit the entire calendar years affected by identified publication disruptions.
    # Compressing years changes the path: these are explicit alternate samples.
    for label,years in [('omit_2013_2025_2026',{2013,2025,2026}),('omit_2020_2025_2026',{2020,2025,2026})]:
        for p,(start,end) in PERIODS.items():
            days=calendar[(calendar>=start)&(calendar<end)&~calendar.year.isin(years)]
            for policy,trades in all_trades.items():
                part=trades.loc[trades.session.isin(days)]
                env=all_daily[policy].reindex(days,fill_value=0.)
                m=metrics(part,days);dd=envelope_dd(env)[0]
                sensitivity.append(dict(sensitivity=label,period=p,policy=policy,**m,equity_dd=dd,net_equity_dd=m['net_dollars']/dd))
    pd.DataFrame(comparisons).to_csv(RUN/'comparisons.csv',index=False)
    pd.DataFrame(sensitivity).to_csv(RUN/'schedule_sensitivity.csv',index=False)
    verification=dict(all_passed=True,jobs=checks,draws=DRAWS,seed=SEED,
                      protocol_sha256=sha(DOC/'PROTOCOL.md'),calendar_sha256=manifest['calendar_sha256'],
                      source_calendar_sha256=sha(CAL),baseline_report_sha256=sha(BASE/(TAG+'.htm')),
                      output_sha256={p.name:sha(p) for p in RUN.glob('*.csv')},code_sha256=sha(__file__))
    (RUN/'verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
    print(summary.loc[summary.period.isin(['2016-19','2020-26','2016-26']),
          ['period','policy','trades','net_dollars','equity_dd','net_equity_dd']].to_string(index=False))

if __name__=='__main__':main()
