"""Independent minute-OHLC replay of RTL with frozen intraday news exclusions.

Broker SL and pending fills precede the EA callback. Uses the established
minute path; comparison with native timestamps is at minute precision.
"""
import numpy as np
import pandas as pd
import rtl_weekly_engine as e
from build_news_windows import window_ids

def simulate(bars,windows,mode,cutoffs=None):
    assert mode in (0,1,2)
    cutoffs=cutoffs or {}
    date,day,minute=(bars[k] for k in ('date','day','minute'))
    o,h,l,c=(bars[k] for k in 'ohlc');n=len(o)
    slot=day*48+minute//30;lf=e.low_first(o,c)
    blocked=window_ids(pd.to_datetime(day*86400+minute*60,unit='s'),windows)>=0 if mode else np.zeros(n,bool)
    trades=[];rejected=0;pend=pos=None;last_flat=prev_date=0;bar1=cur=None;cur_slot=-1
    def close(i,k,price,why):
        nonlocal pos
        trades.append({**pos,'exit_time':e.stamp(day[i],minute[i],k),'exit_price':price,'reason':why})
        pos=None
    for i in range(n):
        new=slot[i]!=cur_slot
        if new:
            bar1=cur;cur=[o[i],h[i],l[i],c[i]];cur_slot=slot[i]
        else:
            cur[1]=max(cur[1],h[i]);cur[2]=min(cur[2],l[i]);cur[3]=c[i]
        action=blocked[i] and (pend is not None or (mode==2 and pos is not None))
        if not new and not action and (pend is None or h[i]<pend['requested']):
            if pos is None or l[i]>pos['sl']:continue
        for k,p in enumerate(e.path(o[i],h[i],l[i],c[i],lf[i])):
            if pos is not None and p<=pos['sl']:close(i,k,pos['sl'],'sl')
            if pend is not None and p>=pend['requested']:
                pos={**pend,'entry_time':e.stamp(day[i],minute[i],k),'fill':pend['requested']};pend=None
            if blocked[i]:
                pend=None
                if mode==2 and pos is not None:close(i,k,p,'news')
            if k or not new:continue
            bar_date,bar_min=date[i],minute[i]//30*30
            if prev_date and bar_date!=prev_date and last_flat!=prev_date:
                last_flat=prev_date
                if pos is not None:close(i,k,p,'fallback')
                pend=None
            prev_date=bar_date
            if bar_min>=cutoffs.get(bar_date,e.CUTOFF):
                if last_flat!=bar_date:
                    last_flat=bar_date
                    if pos is not None:close(i,k,p,'flatten')
                    pend=None
                continue
            if pos is not None:
                if bar1[3]>=pos['fill']+(pos['fill']-pos['sl']):close(i,k,p,'target')
                continue
            if blocked[i]:continue
            if bar_min<60:
                pend=None;continue
            if bar1 is not None and bar1[3]<bar1[0]:
                pend=None
                if bar1[1]-bar1[2]<=0:continue
                if bar1[1]<=p:
                    rejected+=1;continue
                pend={'submitted':e.stamp(day[i],minute[i],0),'requested':bar1[1],'sl':bar1[2]}
    if pos is not None:close(n-1,3,c[n-1],'end_of_data')
    columns=['submitted','requested','sl','entry_time','fill','exit_time','exit_price','reason']
    return pd.DataFrame(trades,columns=columns),rejected
