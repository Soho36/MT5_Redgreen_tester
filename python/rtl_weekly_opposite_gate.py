"""Independent completed-week gate and native RTL experiment analysis."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import rtl_weekly_engine as e
import analyze_rtl_vwap_cross as cx
from prepare_rtl_weekly_opposite_gate import ROOT,RUN,DOC,BASE,DATA,SYMBOL,tag,sha
from rtl_news_window_engine import simulate
from build_news_windows import window_ids
from analyze_rtl_news_days import session_envelopes,envelope_dd,DTYPE,maxdd
from analyze_rtl_vwap_slope import metrics
from rtl_sell_limit_fade import label_native

PERIODS={
    '2010-15':('2010-01-01','2016-01-01'),
    '2016-19':('2016-01-01','2020-01-01'),
    '2020-Sep2026':('2020-01-01','2026-10-01'),
    'Oct-Nov13_2026':('2026-10-01','2026-11-14'),
    '2016-Sep2026':('2016-01-01','2026-10-01'),
    '2016-Nov13_2026':('2016-01-01','2026-11-14'),
}

def weekly_bars(bars):
    """Build Monday-Friday weeks from raw minutes, retaining actual availability."""
    key=e.week_keys(bars['day'])
    starts=np.flatnonzero(np.r_[True,np.diff(key)!=0])
    ends=np.r_[starts[1:]-1,len(key)-1]
    return pd.DataFrame(dict(
        week=key[starts].astype('datetime64[D]'),
        first=e.stamp_array(bars['day'][starts],bars['minute'][starts]),
        last=e.stamp_array(bars['day'][ends],bars['minute'][ends],3),
        open=bars['o'][starts],high=np.maximum.reduceat(bars['h'],starts),
        low=np.minimum.reduceat(bars['l'],starts),close=bars['c'][ends]))

def decisions(weeks):
    """Evaluate only rows with a subsequent week's first quote, never the final row."""
    enabled=True
    green=red=None
    rows=[]
    for i in range(len(weeks)-1):
        w=weeks.iloc[i]
        before=enabled
        trigger='none'
        if w.close<w.open and green is not None and w.close<green.low:
            enabled=False
            trigger='halt'
        elif w.close>w.open and red is not None and w.close>red.high:
            enabled=True
            trigger='resume'
        rows.append(dict(effective=weeks.iloc[i+1]['first'],week=w.week,
            open=w.open,high=w.high,low=w.low,close=w.close,
            green_week=pd.NaT if green is None else green.week,
            green_low=0. if green is None else green.low,
            red_week=pd.NaT if red is None else red.week,
            red_high=0. if red is None else red.high,
            before=int(before),enabled=int(enabled),trigger=trigger))
        if w.close>w.open:
            green=w
        elif w.close<w.open:
            red=w
    return pd.DataFrame(rows)

def halt_windows(events,end):
    rows=[]
    start=None
    for r in events.itertuples():
        if not r.enabled and start is None:
            start=r.effective
        elif r.enabled and start is not None:
            rows.append(dict(start=start,end=r.effective))
            start=None
    if start is not None:
        rows.append(dict(start=start,end=pd.Timestamp(end)))
    return pd.DataFrame(rows,columns=['start','end'])

def monday_label(values):
    s=pd.Series(pd.to_datetime(values))
    # MT5 may label W1 Sunday, although source quotes run Monday-Friday.
    return s+pd.to_timedelta(s.dt.dayofweek.eq(6).astype(int),unit='D')

def verify_weekly(arm,expected):
    saved=pd.read_csv(RUN/f'weekly_gate_{tag(arm)}.csv',sep='\t',parse_dates=['effective','week'])
    saved['week']=monday_label(saved.week).to_numpy()
    for name in ('green_week','red_week'):
        v=pd.to_datetime(saved[name].where(saved[name].ne(0)),unit='s')
        saved[name]=monday_label(v).to_numpy()
    cols=list(expected.columns)
    pd.testing.assert_frame_equal(saved[cols].reset_index(drop=True),expected.reset_index(drop=True),
                                  check_dtype=False,check_exact=True)
    return dict(weekly_decisions=len(saved),all_weekly_ohlc_and_references_match=True,
                state_changes=int(saved.before.ne(saved.enabled).sum()),
                pending_at_halt=int(saved.loc[saved.enabled.eq(0),'pending_before'].sum()),
                positions_at_halt=int(saved.loc[saved.enabled.eq(0),'positions_before'].sum()))

def native(arm,calendar):
    report=RUN/(tag(arm)+'.htm')
    t=cx.economics(cx.parse_report(report,SYMBOL),cx.INSTRUMENTS['NQ'])
    ledger=pd.read_csv(RUN/f'runband_{tag(arm)}_1.00.csv',sep='\t',encoding='utf-16')
    stats=pd.read_csv(RUN/f'runband_{tag(arm)}_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
    assert len(t)==len(ledger)==int(stats.trades)
    np.testing.assert_array_equal(t.ticket,ledger.ticket)
    np.testing.assert_allclose(t.trade_profit,ledger.trade_profit,rtol=0,atol=1e-8)
    np.testing.assert_allclose(t.trade_profit,2*(t.exit_price-t.fill_price),rtol=0,atol=1e-8)
    assert abs(t.trade_profit.sum()-stats.net_profit)<1e-6
    for name in ('entry_time','exit_time'):
        assert t[name].eq(pd.to_datetime(ledger[name])).all()
        assert t[name].dt.normalize().eq(t.session).all(), 'Daily boundary not flat'
    done=json.loads((RUN/(tag(arm)+'.completed.json')).read_text())
    for name,digest in done['outputs'].items():
        assert sha(RUN/name)==digest,name
    eqpath=RUN/f'window_equity_{tag(arm)}.bin'
    data=np.memmap(eqpath,mode='r',dtype=DTYPE)
    grossdd=maxdd(np.r_[500000.,data['equity']])
    assert abs(grossdd-stats.equity_dd)<.011,(grossdd,stats.equity_dd)
    env=session_envelopes(eqpath,t,calendar)
    return t,env,dict(trades=len(t),report_sha256=sha(report),native_gross_equity_dd=float(stats.equity_dd),
                      rebuilt_gross_equity_dd=grossdd,ledger_and_native_totals_match=True,
                      flat_daily_boundaries=True)

def verify_replay(t,replay):
    # Preserve established ~100 M30 bar tester startup, exclude only its first session.
    start=t.submitted.min().normalize()+pd.Timedelta(days=1)
    a=t.loc[t.submitted.ge(start)].reset_index(drop=True)
    b=replay.loc[replay.submitted.ge(start)].reset_index(drop=True)
    assert len(a)==len(b),(len(a),len(b))
    for name in ('submitted','entry_time','exit_time'):
        np.testing.assert_array_equal(a[name].dt.floor('min'),pd.to_datetime(b[name]).dt.floor('min'),err_msg=name)
    for native_name,replay_name in [('requested_price','requested'),('original_sl','sl'),('fill_price','fill'),('exit_price','exit_price')]:
        np.testing.assert_allclose(a[native_name],b[replay_name],rtol=0,atol=1e-8,err_msg=native_name)
    x=a.copy()
    x['reason']=np.select([x.exit_comment.str.startswith('sl'),x.exit_comment.str.startswith('end of test')],
                          ['sl','end_of_data'],'market')
    x=label_native(x,e.load_cutoffs())
    np.testing.assert_array_equal(x.reason,b.reason.replace('fallback','flatten'))
    return dict(from_date=str(start.date()),trades=len(a),all_trade_fields_and_exit_reasons_match=True)

def paired_interval(delta,draws=10000,seed=20261117):
    blocks=delta.groupby(delta.index.to_period('W-SUN')).sum().to_numpy()
    rng=np.random.default_rng(seed)
    totals=[]
    for start in range(0,draws,500):
        totals.extend(blocks[rng.integers(len(blocks),size=(min(500,draws-start),len(blocks)))].sum(axis=1))
    return np.quantile(totals,[.025,.975]).tolist()

def audit_old_baseline(t):
    path=BASE/'runband_tf_20261015_rtl_m30_rr1p0_1.00.csv'
    old=pd.read_csv(path,sep='\t',encoding='utf-16')
    a=t.loc[t.exit_time.lt('2026-10-01')].reset_index(drop=True)
    old=old.loc[pd.to_datetime(old.exit_time).lt('2026-10-01')].reset_index(drop=True)
    assert len(a)==len(old),(len(a),len(old))
    for name in ('entry_time','exit_time'):
        np.testing.assert_array_equal(a[name],pd.to_datetime(old[name]))
    np.testing.assert_allclose(a.trade_profit,old.trade_profit,rtol=0,atol=1e-8)
    np.testing.assert_allclose(a.requested_price-a.original_sl,old.candle_range,rtol=0,atol=1e-8)
    return dict(trades=len(a),all_times_pnl_and_signal_ranges_match=True,source_sha256=sha(path))

def plot(trades,env,windows,calendar):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    days=calendar[calendar>='2016-01-01']
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True,layout='constrained',height_ratios=[2,1])
    colours={'baseline':'#2563eb','weekly_gate':'#ea580c'}
    for arm,label in [('baseline','Unchanged RTL'),('weekly_gate','RTL + weekly gate')]:
        balance=env[arm].reindex(days).net.cumsum()
        axes[0].plot(days,balance,label=label,color=colours[arm],lw=1.4)
        peak=np.maximum.accumulate(np.r_[0.,balance.to_numpy()])[1:]
        axes[1].plot(days,balance-peak,color=colours[arm],lw=1.)
    for r in windows.itertuples():
        for ax in axes:
            ax.axvspan(r.start,r.end,color='#94a3b8',alpha=.13,lw=0)
    axes[0].set_title('RTL with the completed-week opposite-colour gate\n1 MNQ, $1.05 per trade; shaded weeks halt entries')
    axes[0].set_ylabel('Cumulative net USD')
    axes[1].set_ylabel('Daily balance\ndrawdown, USD')
    axes[0].legend(loc='upper left')
    for ax in axes:
        ax.grid(alpha=.2)
        ax.axhline(0,color='gray',lw=.6)
    axes[0].set_xlim(days.min(),days.max())
    (DOC/'img').mkdir(exist_ok=True)
    fig.savefig(DOC/'img/equity.png',dpi=150)
    plt.close(fig)

def main():
    manifest=json.loads((RUN/'manifest.json').read_text())
    for name,digest in manifest['input_hashes'].items():
        assert sha(Path(name))==digest,name
    bars=e.load_minutes(RUN/'minutes.npz',source=DATA)
    print('Loaded',len(bars['o']),'verified raw minutes',flush=True)
    calendar=pd.DatetimeIndex(np.unique(bars['day']).astype('datetime64[D]'))
    weeks=weekly_bars(bars)
    events=decisions(weeks)
    windows=halt_windows(events,'2026-11-14')
    weeks.to_csv(DOC/'weeks.csv',index=False)
    events.to_csv(DOC/'weekly_decisions.csv',index=False)
    windows.to_csv(DOC/'halt_periods.csv',index=False)
    checks={'input_hashes_verified':True,'raw_minutes':len(bars['o']),'jobs':{}}
    trades={};env={}
    for arm in ('baseline','weekly_gate'):
        check=verify_weekly(arm,events)
        t,daily,native_check=native(arm,calendar)
        print('Weekly/native accounting verified:',arm,len(t),flush=True)
        replay,rejected=simulate(bars,windows,0 if arm=='baseline' else 1,e.load_cutoffs())
        replay.to_csv(RUN/f'replay_{arm}.csv',index=False)
        check.update(native_check)
        check['replay']=verify_replay(t,replay)
        check['replay_rejections']=rejected
        if arm=='baseline':
            checks['historical_baseline']=audit_old_baseline(t)
        else:
            assert (window_ids(t.submitted,windows)<0).all(),'Submission while halted'
            check['boundary_fills']=int((window_ids(t.entry_time,windows)>=0).sum())
            assert check['boundary_fills']==0
        trades[arm]=t;env[arm]=daily;checks['jobs'][arm]=check
        t.to_csv(RUN/f'trades_{arm}.csv',index=False)
        daily.to_csv(RUN/f'equity_sessions_{arm}.csv')
        print('Independent full minute replay verified:',arm,check['replay'],flush=True)
    # A full replay detects replacement trades, unlike ledger omission.
    keys=['submitted','entry_time','exit_time','requested_price','fill_price','original_sl','exit_price','trade_profit']
    baseline=trades['baseline'];gated=trades['weekly_gate']
    expected=baseline.loc[window_ids(baseline.submitted,windows)<0,keys].reset_index(drop=True)
    pd.testing.assert_frame_equal(expected,gated[keys].reset_index(drop=True),check_exact=True)
    checks['gated_is_exact_retained_subset']=True
    checks['replacement_trades']=0
    rows=[];comparisons=[]
    scopes={**PERIODS,**{str(y):(f'{y}-01-01',min(f'{y+1}-01-01','2026-11-14')) for y in range(2010,2027)}}
    for period,(start,end) in scopes.items():
        days=calendar[(calendar>=start)&(calendar<end)]
        scoped={}
        for arm in ('baseline','weekly_gate'):
            t=trades[arm].loc[trades[arm].session.isin(days)]
            daily=env[arm].reindex(days)
            m=metrics(t,days)
            dd=float(envelope_dd(daily)[0])
            closed=maxdd(np.r_[0.,t.sort_values('exit_time').net_dollars.cumsum()])
            row=dict(period=period,arm=arm,**m,equity_dd=dd,closed_trade_dd=closed,
                net_equity_dd=m['net_dollars']/dd if dd else np.nan,
                net_extra_1_cost=m['net_dollars']-len(t),holding_minutes=float(t.holding_minutes.sum()),
                sessions=len(days),halted_sessions=int((window_ids(days+pd.Timedelta(hours=1),windows)>=0).sum()))
            rows.append(row);scoped[arm]=row
        if period in PERIODS:
            a,b=scoped['baseline'],scoped['weekly_gate']
            fraction=b['holding_minutes']/a['holding_minutes']
            delta=env['weekly_gate'].reindex(days).net-env['baseline'].reindex(days).net
            low,high=paired_interval(delta)
            skipped=baseline.loc[baseline.session.isin(days)&(window_ids(baseline.submitted,windows)>=0)]
            comparisons.append(dict(period=period,net_change=float(delta.sum()),net_change_ci_low=low,
                net_change_ci_high=high,retained_holding_fraction=fraction,
                scaled_baseline_net=a['net_dollars']*fraction,scaled_baseline_equity_dd=a['equity_dd']*fraction,
                skipped_trades=len(skipped),skipped_net=float(skipped.net_dollars.sum()),
                skipped_mean_r=float(skipped.net_r.mean()),
                losses_avoided=float(-skipped.net_dollars.clip(upper=0).sum()),
                profits_missed=float(skipped.net_dollars.clip(lower=0).sum())))
    summary=pd.DataFrame(rows)
    summary.to_csv(DOC/'summary.csv',index=False)
    pd.DataFrame(comparisons).to_csv(DOC/'comparisons.csv',index=False)
    checks['all_passed']=True
    checks['protocol_sha256']=sha(DOC/'PROTOCOL.md')
    checks['code_sha256']={n:sha(ROOT/'python'/n) for n in ['rtl_weekly_opposite_gate.py','rtl_news_window_engine.py','rtl_weekly_engine.py','analyze_rtl_news_days.py']}
    checks['output_sha256']={p.name:sha(p) for p in DOC.glob('*.csv')}
    (DOC/'verification.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
    plot(trades,env,windows,calendar)
    print(summary.loc[summary.period.isin(PERIODS),['period','arm','trades','net_dollars','equity_dd','net_mean_r','net_equity_dd']].to_string(index=False),flush=True)
    print(pd.DataFrame(comparisons).to_string(index=False),flush=True)

if __name__=='__main__':
    main()

