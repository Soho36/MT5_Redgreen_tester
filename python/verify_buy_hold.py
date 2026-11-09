"""Independently verify each native hold/roll fill and full-minute equity path."""
import json
import numpy as np
import pandas as pd
from run_buy_hold_rolls import RUN
from rtl_weekly_engine import MINUTES, ROLLS
from run_rtl_vwap_replay import save_json, digest

b=pd.read_csv(MINUTES,sep='\t')
stamps=b['<DATE>']+' '+b['<TIME>']
dates=b['<DATE>'].str.replace('.','-',regex=False).to_numpy()
rolls=pd.read_csv(ROLLS)
starts=np.array([np.flatnonzero(dates==d)[0] for d in rolls.date])
ends=np.r_[starts[1:]-1,len(b)-1]
o,h,l,c=[b['<'+k+'>'].to_numpy(float) for k in ['OPEN','HIGH','LOW','CLOSE']]
assert np.all(np.diff(starts)>0) and starts[0]==0
clone=pd.read_csv(RUN/'clone_verification.tsv',sep='\t')
assert clone.source_count.sum()==len(b) and clone.prices_equal.all()
assert (clone.source_count==clone.copied_count).all() and (clone.read_count==clone.source_count).all()
summary=[]
for mode in ['hold','roll']:
 tag='buyhold_exact_20261108_'+mode
 fills=pd.read_csv(RUN/(tag+'_deals.csv'),sep='\t')
 stats=pd.read_csv(RUN/(tag+'_stats.csv'),sep='\t').iloc[0]
 ins=fills[fills.entry==0].reset_index(drop=True)
 outs=fills[fills.entry==1].reset_index(drop=True)
 aa,zz=(np.array([0]),np.array([len(b)-1])) if mode=='hold' else (starts,ends)
 assert len(ins)==len(outs)==len(aa)==stats.trades
 assert (ins.type==0).all() and (outs.type==1).all() and (fills.volume==1).all()
 assert (fills.commission==0).all() and (fills.swap==0).all()
 assert stats.tick_value/stats.tick_size==2
 assert ins.time.iloc[0]=='2010.06.07 01:00:00'
 assert outs.time.iloc[-1]=='2026.10.01 02:59:59'
 gross=0.; peak=0.; dd=0.; netpeak=0.; netdd=0.; worst=0.; endpoint_check=[]
 for j,(a,z) in enumerate(zip(aa,zz)):
  # Match the minute in the raw source, independently of the generated roll schedule.
  assert ins.time.iloc[j][:16]==stamps.iloc[a][:16]
  assert outs.time.iloc[j][:16]==stamps.iloc[z][:16]
  assert abs(ins.price.iloc[j]-o[a]-.25)<1e-9
  assert outs.price.iloc[j]==c[z]
  pnl=(c[z]-ins.price.iloc[j])*2
  assert abs(outs.profit.iloc[j]-pnl)<1e-8
  high=gross+(h[a:z+1]-ins.price.iloc[j])*2
  low=gross+(l[a:z+1]-ins.price.iloc[j])*2
  running=np.maximum.accumulate(np.r_[peak,high])[1:]
  current=running-low
  i=int(current.argmax())
  if current[i]>dd:
   dd=float(current[i]); trough_time=stamps.iloc[a+i]
  # Half of $1.05 on entry and half on close, per contract position.
  fees=j*1.05+.525
  nh=high-fees; nl=low-fees
  nr=np.maximum.accumulate(np.r_[netpeak,nh])[1:]
  netdd=max(netdd,float((nr-nl).max()))
  netpeak=max(netpeak,float(nh.max()))
  peak=max(peak,float(high.max())); worst=min(worst,float(low.min()))
  gross+=pnl
  netdd=max(netdd,netpeak-(gross-(j+1)*1.05))
  endpoint_check.append(dict(entry=ins.time.iloc[j],exit=outs.time.iloc[j],profit=pnl))
 assert abs(gross-fills.profit.sum())<1e-8 and abs(gross-stats.profit)<1e-8
 assert abs(dd-stats.equity_dd)<.011,(mode,dd,stats.equity_dd)
 expected=pd.read_csv(RUN/'expected_roll_trades.csv') if mode=='roll' else None
 if expected is not None:
  assert np.all(expected.entry.to_numpy()==o[aa]) and np.all(expected.exit.to_numpy()==c[zz])
  assert np.all(expected.entry_time.str.replace('-','.',regex=False).to_numpy()==ins.time.to_numpy())
  assert np.all(expected.exit_time.str.replace('-','.',regex=False).to_numpy()==outs.time.to_numpy())
 row=dict(mode=mode,positions=len(aa),rollovers=len(aa)-1,entry_time=ins.time.iloc[0],exit_time=outs.time.iloc[-1],
  first_entry=float(ins.price.iloc[0]),last_exit=float(outs.price.iloc[-1]),mt5_gross=gross,
  modeled_commission=len(aa)*1.05,net=gross-len(aa)*1.05,equity_drawdown=dd,net_equity_drawdown=netdd,
  drawdown_trough=trough_time,worst_unrealized_account_pnl=worst,all_fills_verified=True,
  native_equity_drawdown_verified=True,report=tag+'.htm')
 summary.append(row)
save_json(RUN/'verification.json',dict(all_passed=True,rows=len(b),source_sha256=digest(MINUTES),roll_sha256=digest(ROLLS),results=summary))
print(json.dumps(summary,indent=2))
