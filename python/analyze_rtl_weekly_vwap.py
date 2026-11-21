"""Exploratory weekly VWAP entry-gate screen against the existing RTL ledger."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'Reports/rtl_weekly_vwap_20261120'
PROTOCOL = ROOT/'docs/baseline/rtl-vwap/WEEKLY_ANCHOR_PROTOCOL.md'
F = ROOT/'Reports/rtl_vwap_20261025/features_full_hlc3.csv'
T = ROOT/'Reports/rtl_market_regimes_20261023/trades.csv'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def week(ts):
    x = pd.to_datetime(ts).dt.normalize()
    return x-pd.to_timedelta(x.dt.dayofweek,unit='D')

def weekly_decisions(submitted, available_week, close, vwap, a20):
    known = available_week.eq(week(submitted)) & a20.gt(0) & vwap.notna()
    return known, known & close.lt(vwap-a20)

def main():
    protocol_hash = sha(PROTOCOL)
    f = pd.read_csv(F, parse_dates=['bar_time','available_at','feature_session'], float_precision='round_trip')
    t = pd.read_csv(T, parse_dates=['submitted','entry_time','exit_time','session','week_start'], float_precision='round_trip')
    assert f.bar_time.is_monotonic_increasing and f.bar_time.is_unique and (f.volume>0).all()
    assert (f.available_at == f.bar_time+pd.Timedelta(minutes=30)).all()
    f['week'] = week(f.bar_time)
    f['weekly_vwap'] = f.pv_hlc3.groupby(f.week).cumsum()/f.volume.groupby(f.week).cumsum()
    # Independent scalar reconstruction, including each week's first and final bars.
    sp=sv=0.; old=None
    for row in f[['week','pv_hlc3','volume','weekly_vwap']].itertuples(index=False,name=None):
        w,p,v,result=row
        if w != old: sp=sv=0.; old=w
        sp+=p; sv+=v
        assert np.isclose(result,sp/sv,rtol=1e-12,atol=1e-8)
    cols=['bar_time','available_at','feature_session','week','close','a20','weekly_vwap','vwap','switch_bar']
    x=pd.merge_asof(t.sort_values('submitted'),f[cols].sort_values('available_at'),
                    left_on='submitted',right_on='available_at',direction='backward')
    assert len(x)==len(t) and x.ticket.is_unique and x.available_at.le(x.submitted).all()
    x['known_weekly'],x['weekly_skip']=weekly_decisions(x.submitted,x.week,x.close,x.weekly_vwap,x.a20)
    x['known_session']=x.feature_session.eq(x.session) & x.a20.gt(0) & x.vwap.notna()
    x['session_skip']=x.known_session & x.close.lt(x.vwap-x.a20)
    # Audit against the previous independently checked session-label panel.
    previous=pd.read_csv(ROOT/'Reports/rtl_vwap_20261025/trades.csv',usecols=['ticket','variant','distance'])
    previous=previous.loc[previous.variant.eq('full_hlc3')].set_index('ticket')
    common=x.loc[x.ticket.isin(previous.index)]
    np.testing.assert_array_equal(common.session_skip.to_numpy(), previous.reindex(common.ticket).distance.eq('far_below').to_numpy())
    dates=pd.DatetimeIndex(f.bar_time.dt.normalize().unique()).sort_values()
    periods=[('2010-15','2010-01-01','2016-01-01'),('2016-19','2016-01-01','2020-01-01'),('2020-26','2020-01-01','2026-10-01')]
    results=[]
    def metrics(z,calendar,scale=1.):
        daily=z.groupby('session').net_dollars.sum().reindex(calendar,fill_value=0.)*scale
        e=np.r_[0.,daily.cumsum().to_numpy()]; dd=np.maximum.accumulate(e)-e
        peak=0.; peak_date=calendar[0]; duration=0
        for date,balance in zip(calendar,e[1:]):
            if balance>=peak-1e-9: peak=max(peak,balance); peak_date=date
            else: duration=max(duration,(date-peak_date).days)
        return dict(trades=len(z),net=float(z.net_dollars.sum()*scale),mean_r=float(z.net_r.mean()) if len(z) else None,
                    daily_dd=float(dd.max()),daily_duration_days=int(duration),holding_hours=float(z.holding_minutes.sum()/60*scale),
                    planned_risk=float(z.initial_risk_dollars.sum()*scale))
    for era,start,end in periods:
        part=x.loc[x.session.ge(start)&x.session.lt(end)]
        calendar=dates[(dates>=start)&(dates<end)]
        for p in ('baseline','weekly','session','weekly_skipped','session_skipped','same_holding','same_risk'):
            selected={'weekly':~part.weekly_skip,'session':~part.session_skip,'weekly_skipped':part.weekly_skip,'session_skipped':part.session_skip}.get(p,np.ones(len(part),dtype=bool))
            sub=part.loc[selected]
            scale=(part.loc[~part.weekly_skip].holding_minutes.sum()/part.holding_minutes.sum() if p=='same_holding' else
                   part.loc[~part.weekly_skip].initial_risk_dollars.sum()/part.initial_risk_dollars.sum() if p=='same_risk' else 1.)
            results.append(dict(period=era,policy=p,unknown_weekly=int((~part.known_weekly).sum()),
                                unknown_session=int((~part.known_session).sum()),scale=float(scale),**metrics(sub,calendar,scale)))
        assert part.net_dollars.sum()==part.loc[~part.weekly_skip].net_dollars.sum()+part.loc[part.weekly_skip].net_dollars.sum() or np.isclose(part.net_dollars.sum(),part.loc[~part.weekly_skip].net_dollars.sum()+part.loc[part.weekly_skip].net_dollars.sum())
        for year in sorted(part.session.dt.year.unique()):
            y=part.loc[part.session.dt.year.eq(year)]; cal=calendar[calendar.year==year]
            for p,mask in [('baseline',np.ones(len(y),dtype=bool)),('weekly',~y.weekly_skip),('session',~y.session_skip)]:
                results.append(dict(period=str(year),policy=p,unknown_weekly=int((~y.known_weekly).sum()),unknown_session=int((~y.known_session).sum()),scale=1.,**metrics(y.loc[mask],cal)))
    OUT.mkdir(parents=True,exist_ok=True)
    x.to_csv(OUT/'labelled_trades.csv',index=False,float_format='%.17g')
    pd.DataFrame(results).to_csv(OUT/'results.csv',index=False,float_format='%.17g')
    assert protocol_hash==sha(PROTOCOL)
    (OUT/'audit.json').write_text(json.dumps(dict(protocol_sha256=protocol_hash,features_sha256=sha(F),trades_sha256=sha(T),
        feature_rows=len(f),trade_rows=len(x),session_labels_verified=len(common),weekly_values_independently_checked=len(f),
        roll_bars=int(f.switch_bar.sum()),output_hashes={n:sha(OUT/n) for n in ['results.csv','labelled_trades.csv']}),indent=2)+'\n')
    print(pd.DataFrame(results).query("period in ['2010-15','2016-19','2020-26']").to_string(index=False))

if __name__=='__main__': main()
