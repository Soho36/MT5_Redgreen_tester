"""M30 RTL with a persistent D1 monthly-VWAP-minus-A20 gate."""
import json,re,shutil,sys
from pathlib import Path
import numpy as np
import pandas as pd
import prepare_rtl_weekly_opposite_gate as wp
import prepare_rtl_daily_vwap as dp
import rtl_weekly_opposite_gate as audit
import rtl_daily_vwap as daily
from rtl_news_window_engine import simulate
from build_news_windows import window_ids
from analyze_rtl_news_days import envelope_dd
from analyze_rtl_vwap_slope import metrics

ROOT=wp.ROOT
RUN=ROOT/'Reports/rtl_m30_daily_vwap_gate_20261118'
DOC=ROOT/'docs/baseline/rtl-m30-daily-vwap-gate'
EXPERT='RTL_m30_daily_vwap_gate'
FEATURE=dp.FEATURE
def tag(arm):return 'dreg_20261118_'+arm

def events_from_features(f,bars):
    starts=np.flatnonzero(np.r_[True,np.diff(bars['day'])!=0])
    first=audit.e.stamp_array(bars['day'][starts],bars['minute'][starts])
    assert len(first)==len(f)
    enabled=True;rows=[]
    for i in range(len(f)-1):
        r=f.iloc[i];before=enabled
        if r.known:
            if r.close<r.vwap-r.a20:enabled=False
            elif r.close>r.vwap-r.a20:enabled=True
        rows.append(dict(effective=pd.Timestamp(first[i+1]),signal=f.index[i],close=r.close,
            vwap=r.vwap,a20=r.a20 if r.known else 0.,known=int(r.known),before=int(before),enabled=int(enabled)))
    return pd.DataFrame(rows)

def header():
    h=dp.HEADER[:dp.HEADER.index('bool DailyVwapAllows')]
    h=h.replace('UseDailyVwapGate','UseDailyRegime')
    h=h.replace('daily_candidates_','daily_regime_')
    h=h.replace('FileWrite(dv_log,"time","signal","close","known","blocked","vwap","a20");',
                'FileWrite(dv_log,"effective","signal","close","vwap","a20","known","before","enabled");')
    h+=r'''
bool wg_enabled=true;
long wg_cancelled=0;
int dv_next=0;
void RegimeUpdate()
{
   while(dv_next<dv_count && dv_available[dv_next]<=TimeCurrent())
   {
      int j=dv_next++;
      bool before=wg_enabled;
      if(dv_known[j]!=0) {
         if(dv_close[j]<dv_vwap[j]-dv_a20[j]) wg_enabled=false;
         else if(dv_close[j]>dv_vwap[j]-dv_a20[j]) wg_enabled=true;
      }
      FileWrite(dv_log,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
         TimeToString(dv_dates[j],TIME_DATE),dv_close[j],DoubleToString(dv_vwap[j],12),
         DoubleToString(dv_a20[j],12),dv_known[j],(int)before,(int)wg_enabled);
   }
}
'''
    return h

def prepare():
    assert not (RUN/'manifest.json').exists(),'Preserve prepared run'
    RUN.mkdir(parents=True,exist_ok=True)
    # Existing daily features were independently checked before this experiment.
    frozen=json.loads((dp.RUN/'manifest.json').read_text())
    for p in [dp.RUN/FEATURE,dp.RUN/'daily_features.csv',wp.DATA]:
        assert wp.sha(p)==frozen['input_hashes'][str(p)],str(p)
    shutil.copyfile(dp.RUN/FEATURE,RUN/FEATURE)
    src=wp.build_source().replace('weekly_opposite_gate.mqh','daily_regime.mqh')
    src=src.replace('WeeklyGateInit','DailyVwapInit').replace('WeeklyGateUpdate','RegimeUpdate')
    src=src.replace('UseWeeklyGate','UseDailyRegime').replace('wg_file','dv_log').replace('WEEKLY_GATE_CANCELLED','DAILY_GATE_CANCELLED')
    h=header()
    for path,text in [(RUN/(EXPERT+'.mq5'),src),(ROOT/'mt5/experts'/(EXPERT+'.mq5'),src),
                      (RUN/'daily_regime.mqh',h),(ROOT/'mt5/experts/daily_regime.mqh',h)]:
        path.write_text(text,encoding='utf-8')
    for name in ('early_closes.mqh','window_equity_research.mqh'):
        shutil.copyfile(wp.RUN/name,RUN/name)
    jobs=[]
    for arm in ('baseline','gated'):
        ini=(wp.BASE/'tf_20261015_rtl_m30_rr1p0.ini').read_text(encoding='utf-16')
        changes=dict(Expert='CodexResearch\\'+EXPERT+'.ex5',Symbol=wp.SYMBOL,ToDate='2026.11.14',RunTag=tag(arm),Report=tag(arm)+'.htm')
        for key,value in changes.items():
            assert len(re.findall('^'+key+'=.*$',ini,re.M))==1
            ini=re.sub('^'+key+'=.*$',lambda _:key+'='+value,ini,flags=re.M)
        ini=ini.replace('[TesterInputs]','[TesterInputs]\nUseDailyRegime='+str(arm=='gated').lower())
        (RUN/(tag(arm)+'.ini')).write_text(ini,encoding='utf-16')
        jobs.append(dict(tag=tag(arm),arm=arm,inputs_files=[FEATURE],outputs=[
            f'runband_{tag(arm)}_1.00.csv',f'runband_{tag(arm)}_1.00_stats.csv',
            f'window_equity_{tag(arm)}.bin',f'daily_regime_{tag(arm)}.csv']))
    paths=[DOC/'PROTOCOL.md',Path(__file__),wp.DATA,dp.RUN/'daily_features.csv',RUN/FEATURE,
           wp.BASE/'RTL_timeframe.mq5',*RUN.glob('*.mq5'),*RUN.glob('*.mqh'),*RUN.glob('*.ini')]
    (RUN/'manifest.json').write_text(json.dumps(dict(expert=EXPERT,jobs=jobs,input_hashes={str(p):wp.sha(p) for p in paths}),indent=2))
    print('Prepared two M30 daily-regime runs',flush=True)

def analyze():
    manifest=json.loads((RUN/'manifest.json').read_text())
    for p,digest in manifest['input_hashes'].items():assert wp.sha(Path(p))==digest,p
    bars=audit.e.load_minutes(wp.RUN/'minutes.npz')
    f=pd.read_csv(dp.RUN/'daily_features.csv',parse_dates=['date'],index_col='date',float_precision='round_trip')
    checks=dict(features=daily.verify_features(bars,f),jobs={})
    events=events_from_features(f,bars)
    windows=audit.halt_windows(events,'2026-11-14')
    calendar=pd.DatetimeIndex(np.unique(bars['day']).astype('datetime64[D]'))
    # Reuse the verified native-accounting reader with explicitly rebound run paths.
    audit.RUN=RUN;audit.tag=tag
    trades={};env={};rows=[];comparisons=[]
    for arm in ('baseline','gated'):
        logged=pd.read_csv(RUN/f'daily_regime_{tag(arm)}.csv',sep='\t',parse_dates=['effective','signal'])
        expected=events.copy()
        # The tester replays pre-start labels at its first tick; all are warm-up.
        expected.effective=expected.effective.clip(lower=logged.effective.iloc[0])
        assert len(logged)==len(expected)
        for name in ('effective','signal'):
            np.testing.assert_array_equal(logged[name].dt.floor('min'),expected[name].dt.floor('min'))
        for name in ('close','vwap','a20','known','before','enabled'):
            np.testing.assert_allclose(logged[name],expected[name],rtol=0,atol=1e-8)
        t,d,check=audit.native(arm,calendar)
        replay,rejected=simulate(bars,windows,0 if arm=='baseline' else 1,audit.e.load_cutoffs())
        check['replay']=audit.verify_replay(t,replay)
        check['daily_decisions']=len(logged);check['all_daily_decisions_match']=True
        if arm=='baseline':
            checks['historical_baseline']=audit.audit_old_baseline(t)
            old=wp.RUN/'runband_wopp_20261117_baseline_1.00.csv'
            assert old.read_bytes()==(RUN/f'runband_{tag(arm)}_1.00.csv').read_bytes()
            checks['extended_control_byte_identical']=True
        else:
            assert (window_ids(t.submitted,windows)<0).all()
            check['fills_during_halt']=int((window_ids(t.entry_time,windows)>=0).sum())
        trades[arm]=t;env[arm]=d;checks['jobs'][arm]=check
        t.to_csv(RUN/f'trades_{arm}.csv',index=False);d.to_csv(RUN/f'equity_sessions_{arm}.csv')
        print('VERIFIED',arm,json.dumps(check),flush=True)
    keys=['submitted','entry_time','exit_time','requested_price','fill_price','original_sl','exit_price','trade_profit']
    kept=trades['baseline'].loc[window_ids(trades['baseline'].submitted,windows)<0,keys]
    pd.testing.assert_frame_equal(kept.reset_index(drop=True),trades['gated'][keys].reset_index(drop=True),check_exact=True)
    checks['gated_is_exact_retained_subset']=True
    scopes={**audit.PERIODS,**{str(y):(f'{y}-01-01',min(f'{y+1}-01-01','2026-11-14')) for y in range(2010,2027)}}
    for period,(start,end) in scopes.items():
        days=calendar[(calendar>=start)&(calendar<end)];pair={}
        for arm in ('baseline','gated'):
            t=trades[arm].loc[trades[arm].session.isin(days)]
            m=metrics(t,days);dd=float(envelope_dd(env[arm].reindex(days))[0])
            row=dict(period=period,arm=arm,**m,equity_dd=dd,net_equity_dd=m['net_dollars']/dd if dd else np.nan,
                holding_minutes=float(t.holding_minutes.sum()),net_extra_1_cost=m['net_dollars']-len(t),
                sessions=len(days),halted_sessions=int((window_ids(days+pd.Timedelta(hours=1),windows)>=0).sum()))
            rows.append(row);pair[arm]=row
        if period in audit.PERIODS:
            a,b=pair['baseline'],pair['gated'];fraction=b['holding_minutes']/a['holding_minutes']
            delta=env['gated'].reindex(days).net-env['baseline'].reindex(days).net
            low,high=audit.paired_interval(delta,seed=20261118)
            skipped=trades['baseline'].loc[trades['baseline'].session.isin(days)&(window_ids(trades['baseline'].submitted,windows)>=0)]
            comparisons.append(dict(period=period,net_change=float(delta.sum()),ci_low=low,ci_high=high,
                retained_holding_fraction=fraction,scaled_baseline_net=a['net_dollars']*fraction,
                scaled_baseline_equity_dd=a['equity_dd']*fraction,skipped_trades=len(skipped),
                skipped_net=float(skipped.net_dollars.sum()),skipped_mean_r=float(skipped.net_r.mean())))
    summary=pd.DataFrame(rows)
    summary.to_csv(DOC/'summary.csv',index=False)
    pd.DataFrame(comparisons).to_csv(DOC/'comparisons.csv',index=False)
    events.to_csv(DOC/'daily_decisions.csv',index=False);windows.to_csv(DOC/'halt_periods.csv',index=False)
    checks['all_passed']=True;checks['protocol_sha256']=wp.sha(DOC/'PROTOCOL.md')
    checks['output_sha256']={p.name:wp.sha(p) for p in DOC.glob('*.csv')}
    (DOC/'verification.json').write_text(json.dumps(checks,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True,layout='constrained',height_ratios=[2,1])
    days=calendar[calendar>='2016-01-01']
    for arm,label in [('baseline','Original M30 RTL'),('gated','M30 RTL + daily VWAP gate')]:
        curve=env[arm].reindex(days).net.cumsum()
        axes[0].plot(days,curve,label=label)
        axes[1].plot(days,curve-np.maximum.accumulate(np.r_[0.,curve])[1:])
    axes[0].set_title('M30 RTL with a persistent daily monthly-VWAP-minus-A20 gate\n1 MNQ, $1.05 per trade; completed D1 signals only')
    axes[0].set_ylabel('Cumulative net USD');axes[1].set_ylabel('Daily balance drawdown, USD')
    axes[0].legend()
    for ax in axes:ax.grid(alpha=.2)
    (DOC/'img').mkdir(exist_ok=True);fig.savefig(DOC/'img/equity.png',dpi=150);plt.close(fig)
    print(summary.loc[summary.period.isin(audit.PERIODS),['period','arm','trades','net_dollars','equity_dd','net_mean_r','halted_sessions','sessions']].to_string(index=False),flush=True)
    print(pd.DataFrame(comparisons).to_string(index=False),flush=True)
if __name__=='__main__':
    prepare() if '--prepare' in sys.argv else analyze()

