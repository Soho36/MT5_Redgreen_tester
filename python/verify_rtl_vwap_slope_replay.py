"""Verify native slope replay decisions, ledger reconciliation and economics."""
import json
import numpy as np
import pandas as pd

import analyze_rtl_vwap_cross as cx
from analyze_rtl_vwap_slope import ROOT, CROSS, PERIODS, metrics, sha
from prepare_rtl_vwap_slope_replay import RUN, FEATURE


def main():
    manifest=json.loads((RUN/'manifest.json').read_text())
    for n,h in manifest['prepared_sha256'].items(): assert sha(RUN/n)==h,n
    for job in manifest['jobs']:
        done=json.loads((RUN/(job['tag']+'.completed.json')).read_text())
        for n,h in done['outputs'].items(): assert sha(RUN/n)==h
    off,on=[j['tag'] for j in manifest['jobs']]
    base=ROOT/'Reports/ym_baselines_20261023/runband_ymbase_20261023_rtl_nq_1.00.csv'
    assert (RUN/f'rtlvwap_{off}_1.00.csv').read_bytes()==base.read_bytes(),'OFF must reproduce original ledger'
    f=pd.read_csv(CROSS/'features_NQ.csv',float_precision='round_trip')
    for c in ('bar_time','available_at','feature_session'): f[c]=pd.to_datetime(f[c])
    prev=f.shift()
    valid=(f.feature_session.eq(prev.feature_session)&f.bar_time.sub(prev.bar_time).eq(pd.Timedelta(minutes=30))
           &np.isfinite(f.vwap)&np.isfinite(prev.vwap)&f.vwap_available&prev.vwap_available.eq(True)
           &f.cum_volume.gt(prev.cum_volume)&prev.cum_volume.gt(0))
    delta=f.vwap-prev.vwap
    def lookup(time,signal):
        pos=np.searchsorted(f.available_at.to_numpy(),time.to_numpy(),side='right')-1
        assert (pos>=0).all()
        r=f.iloc[pos].reset_index(drop=True)
        exact=r.bar_time.eq(signal).to_numpy()
        assert (exact|signal.gt(f.bar_time.iloc[-1])).all(),'missing label within feature coverage'
        known=exact&valid.iloc[pos].to_numpy()&r.feature_session.eq(time.dt.normalize()).to_numpy()
        return r,delta.iloc[pos].to_numpy(),known
    checks={}
    for tag,enabled in ((off,False),(on,True)):
        d=pd.read_csv(RUN/f'slope_decisions_{tag}.tsv',sep='\t')
        time=pd.to_datetime(d.time); signal=pd.to_datetime(d.signal_bar)
        r,diff,known=lookup(time,signal)
        inside=signal.le(f.bar_time.iloc[-1]).to_numpy()
        np.testing.assert_allclose(d.signal_close[inside],r.close[inside],rtol=0,atol=1e-7)
        np.testing.assert_allclose(d.delta[inside&valid.iloc[np.searchsorted(f.available_at.to_numpy(),time.to_numpy(),side='right')-1].to_numpy()],
                                   diff[inside&valid.iloc[np.searchsorted(f.available_at.to_numpy(),time.to_numpy(),side='right')-1].to_numpy()],rtol=0,atol=1e-9)
        assert np.array_equal(d.known.astype(bool),known)
        expected=enabled&(~known|(diff<=0))
        assert np.array_equal(d.blocked.astype(bool),expected)
        checks[tag]=dict(candidates=len(d),blocked=int(d.blocked.sum()),known=int(d.known.sum()))
    spec=cx.INSTRUMENTS['NQ']
    frames={}
    for tag,curve in ((off,'baseline'),(on,'replay')):
        parsed=cx.parse_report(RUN/(tag+'.htm'),spec['symbol'])
        econ=cx.economics(parsed,spec)
        # Native profit and independent price arithmetic must agree, before external costs.
        np.testing.assert_allclose(econ.trade_profit,(econ.exit_price-econ.fill_price)*2,rtol=0,atol=1e-7)
        stat=pd.read_csv(RUN/f'rtlvwap_{tag}_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
        assert len(econ)==stat.trades and abs(econ.trade_profit.sum()-stat.net_profit)<1e-6
        ledger=pd.read_csv(RUN/f'rtlvwap_{tag}_1.00.csv',sep='\t',encoding='utf-16')
        assert len(ledger)==len(econ)
        native=ledger.set_index('ticket').loc[econ.ticket]
        np.testing.assert_allclose(native.trade_profit,econ.trade_profit,rtol=0,atol=1e-7)
        for c in ('entry_time','exit_time'):
            assert np.array_equal(pd.to_datetime(native[c]).to_numpy(),econ[c].to_numpy())
        if curve=='replay':
            decisions=pd.read_csv(RUN/f'slope_decisions_{on}.tsv',sep='\t')
            decisions.index=pd.to_datetime(decisions.time)
            assert decisions.index.is_unique
            accepted=decisions.reindex(econ.submitted.dt.floor('30min'))
            assert accepted.blocked.eq(0).all()
            # The preceding observed bar can be earlier than wall-clock t-30m.
            signal=pd.to_datetime(accepted.signal_bar).reset_index(drop=True)
            r,diff,known=lookup(econ.submitted.reset_index(drop=True),signal.reset_index(drop=True))
            assert known.all() and (diff>0).all()
            np.testing.assert_allclose(econ.requested_price,r.high,rtol=0,atol=1e-7)
            np.testing.assert_allclose(econ.original_sl,r.low,rtol=0,atol=1e-7)
        frames[curve]=econ.loc[econ.session<'2026-10-01'].copy()
        if curve=='replay': frames[curve].to_csv(RUN/'replay_trades.csv',index=False,float_format='%.17g')
    omission=pd.read_csv(ROOT/'Reports/rtl_vwap_slope_20261101/trades.csv',parse_dates=['session'])
    frames['omission']=omission.loc[omission.slope_state.eq('up')]
    cal=pd.read_csv(CROSS/'calendars.csv',parse_dates=['session'])
    cal=pd.DatetimeIndex(cal.loc[cal.instrument.eq('NQ'),'session']).sort_values()
    rows=[]
    scopes=list(PERIODS.items())+[(str(y),(f'{y}-01-01',min(f'{y+1}-01-01','2026-10-01'))) for y in range(2010,2027)]
    for period,(start,end) in scopes:
        days=cal[(cal>=start)&(cal<end)]
        for curve,frame in frames.items():
            part=frame.loc[frame.session.ge(start)&frame.session.lt(end)]
            m=metrics(part,days)
            daily=part.groupby('session').net_dollars.sum().reindex(days,fill_value=0.)
            peak=balance=dd=0.
            for x in daily:
                balance+=x; peak=max(peak,balance); dd=max(dd,peak-balance)
            assert abs(dd-m['daily_close_dd'])<1e-7
            if period in PERIODS and curve!='replay':
                ref=pd.read_csv(ROOT/'Reports/rtl_vwap_slope_20261101/summaries.csv')
                ref=ref.loc[ref.period.eq(period)&ref.policy.eq('baseline' if curve=='baseline' else 'rising')].iloc[0]
                for c in ('trades','net_dollars','net_mean_r','daily_close_dd'): assert abs(m[c]-ref[c])<1e-6
            rows.append(dict(period=period,curve=curve,**m))
    table=pd.DataFrame(rows)
    table.to_csv(RUN/'summaries.csv',index=False,float_format='%.17g')
    result=dict(all_passed=True,off_ledger_byte_identical=True,decision_checks=checks,
                every_replay_trade_from_rising_signal=True,native_profit_arithmetic_checked=True,
                baseline_and_omission_reproduced=True,independent_daily_dd_checked=True)
    (RUN/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2));print(table.loc[table.period.isin(PERIODS)].to_string(index=False))


if __name__=='__main__': main()
