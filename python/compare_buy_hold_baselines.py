"""Matched-date, cost-inclusive RTL/GG versus passive hold comparison."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from project_paths import PROJECT_ROOT as ROOT
from rtl_weekly_engine import MINUTES, ROLLS, load_minutes
from verify_exclude16_replay import DTYPE, maxdd, equity_metrics
from run_rtl_vwap_replay import digest, save_json

RUN=ROOT/'Reports/buy_hold_20261108/comparison'
BASE=ROOT/'Reports/rtl_gg_exclude16_20261101'
PERIODS={'Full 2010-26':('2010-06-07','2026-10-02'),
         '2010-15':('2010-06-07','2016-01-01'),
         '2016-19':('2016-01-01','2020-01-01'),
         '2016-26':('2016-01-01','2026-10-02'),
         '2020-26':('2020-01-01','2026-10-02')}
RUN.mkdir(parents=True,exist_ok=True)
rows=[];paths={};raw_inputs={}
assert json.loads((BASE/'verification.json').read_text())['all_passed']
assert json.loads((BASE/'equity_native_crosscheck.json').read_text())['all_passed']
VARIANTS={
 'RTL':'rtl_base_all','RTL + VWAP':'rtl_vwap_all',
 'RTL + VWAP + exclude 16-17':'rtl_vwap_skip',
 'GG':'gg_base_all','GG + VWAP':'gg_vwap_all',
 'GG + VWAP + exclude 16-17':'gg_vwap_skip',
}
for strategy,suffix in VARIANTS.items():
 tag='ex16_20261101_'+suffix
 p=BASE/f'window_equity_{tag}.bin'
 data=np.memmap(p,dtype=DTYPE,mode='r')
 trades=pd.read_csv(BASE/(tag+'_trades.csv'))
 exits=np.sort(pd.to_datetime(trades.exit_time).to_numpy(dtype='datetime64[s]').astype(np.int64))
 assert np.all(np.diff(data['time'])>=0)
 done=json.loads((BASE/(tag+'.completed.json')).read_text())
 assert digest(p)==done['outputs'][p.name]
 raw_inputs[str(p)]=digest(p)
 stat=pd.read_csv(BASE/f'rtlvwap_{tag}_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
 assert stat.risk_reward==1 and stat.max_red_run==0 and stat.min_location==0
 assert bool(stat.vwap_gate)==('vwap' in suffix)
 cfg=(BASE/(tag+'.ini')).read_text(encoding='utf-16').splitlines()
 assert ('W1600W1700=false' in cfg)==suffix.endswith('skip')
 assert len(trades)==stat.trades
 assert abs(trades.trade_profit.sum()-stat.net_profit)<1e-7
 assert abs(data['balance'][-1]-500000-trades.trade_profit.sum())<1e-7
 assert abs(maxdd(data['equity'])-stat.equity_dd)<1e-7
 # Keep the last native observation of each second for portfolio alignment/plots.
 last=np.r_[np.flatnonzero(np.diff(data['time'])),len(data)-1]
 t=np.asarray(data['time'][last]); e=np.asarray(data['equity'][last])-500000-1.05*np.searchsorted(exits,t,side='right')
 paths[strategy]=(t,e)
 for period,(start,end) in PERIODS.items():
  lo=int(pd.Timestamp(start).timestamp()); hi=int(pd.Timestamp(end).timestamp())
  part=trades.loc[(pd.to_datetime(trades.exit_time)>=start)&(pd.to_datetime(trades.exit_time)<end)]
  assert not ((pd.to_datetime(trades.entry_time)<start)&(pd.to_datetime(trades.exit_time)>=start)).any()
  m=equity_metrics(data,start,end,exits)
  net=float(part.trade_profit.sum()-len(part)*1.05)
  rows.append(dict(period=period,strategy=strategy,positions=len(part),max_contracts=1,net=net,
                   equity_dd=m['sampled_equity_dd'],gross=float(part.trade_profit.sum()),
                   fees=len(part)*1.05,drawdown_method='native intraday observations, commission at exit'))
 print(strategy,'full net',rows[-5]['net'],'observations',len(data),flush=True)
 del data,last

# Portfolio is one contract in each strategy: up to two total. Align last observation
# per second, carrying each leg forward. It is not a one-contract strategy.
for label,names in {
 'RTL + GG (2 contracts)':('RTL','GG'),
 'RTL + GG + VWAP (2 contracts)':('RTL + VWAP','GG + VWAP'),
 'RTL + GG + VWAP + exclude 16-17 (2 contracts)':('RTL + VWAP + exclude 16-17','GG + VWAP + exclude 16-17'),
}.items():
 u=np.union1d(paths[names[0]][0],paths[names[1]][0]); total=np.zeros(len(u))
 for name in names:
  t,e=paths[name]; ix=np.searchsorted(t,u,side='right')-1
  total+=np.where(ix>=0,e[np.maximum(ix,0)],0)
 paths[label]=(u,total)
 for period,(start,end) in PERIODS.items():
  lo=int(pd.Timestamp(start).timestamp());hi=int(pd.Timestamp(end).timestamp())
  a,z=np.searchsorted(u,[lo,hi]); before=total[a-1] if a else 0.
  net=float(total[z-1]-before)
  components=[r for r in rows if r['period']==period and r['strategy'] in names]
  assert abs(net-sum(r['net'] for r in components))<1e-7
  rows.append(dict(period=period,strategy=label,positions=sum(r['positions'] for r in components),max_contracts=2,
   net=net,equity_dd=maxdd(np.r_[before,total[a:z]]),gross=sum(r['gross'] for r in components),fees=sum(r['fees'] for r in components),
   drawdown_method='sum of native last observation per second; carry forward'))

print('Loading raw minutes',flush=True)
b=load_minutes(None)
t=b['day']*86400+b['minute']*60
o,h,l,c=(b[k] for k in 'ohlc')
rd=pd.read_csv(ROLLS)
rolltimes=pd.to_datetime(rd.date).to_numpy(dtype='datetime64[s]').astype(np.int64)
switches=np.searchsorted(t,rolltimes)[1:]
assert len(switches)==66
passive_daily=[]
for period,(start,end) in PERIODS.items():
 a,z=np.searchsorted(t,[int(pd.Timestamp(start).timestamp()),int(pd.Timestamp(end).timestamp())]);z-=1
 for name in ['Hold raw series','Hold with rollovers']:
  aa=np.r_[a,switches[(switches>a)&(switches<=z)]] if name=='Hold with rollovers' else np.array([a])
  zz=np.r_[aa[1:]-1,z]
  realized=0.;peak=0.;dd=0.;gross=0.
  daily_t=[];daily_e=[]
  for j,(x,y) in enumerate(zip(aa,zz)):
   entry=o[x]+.25
   high=realized+(h[x:y+1]-entry)*2
   low=realized+(l[x:y+1]-entry)*2
   running=np.maximum.accumulate(np.r_[peak,high])[1:]
   dd=max(dd,float((running-low).max()));peak=max(peak,float(high.max()))
   g=float((c[y]-entry)*2);gross+=g
   # Charge full commission on close, matching baseline observer convention.
   realized+=g-1.05;dd=max(dd,peak-realized)
   daily=np.r_[np.flatnonzero(np.diff(b['day'][x:y+1])),y-x]+x
   equity=realized-g+1.05+(c[daily]-entry)*2
   equity[-1]-=1.05
   daily_t.extend(t[daily]+59);daily_e.extend(equity)
  rows.append(dict(period=period,strategy=name,positions=len(aa),max_contracts=1,net=realized,
   equity_dd=dd,gross=gross,fees=len(aa)*1.05,drawdown_method='minute highs/lows, commission at exit'))
  if period=='Full 2010-26':
   paths[name]=(np.array(daily_t),np.array(daily_e))
   prior=json.loads((ROOT/'Reports/buy_hold_20261108/exact_start/verification.json').read_text())
   expected=next(r for r in prior['results'] if r['mode']==('hold' if name=='Hold raw series' else 'roll'))
   assert abs(realized-expected['net'])<1e-7
   assert abs(dd-expected['net_equity_drawdown'])<1e-7

s=pd.DataFrame(rows);s['net_dd']=s.net/s.equity_dd
# The extension must not change any previously reported baseline/passive number.
old=pd.read_csv(RUN/'baseline_only_comparison.csv').set_index(['period','strategy'])
new=s.set_index(['period','strategy']).loc[old.index]
for col in ['positions','max_contracts','net','equity_dd','gross','fees','net_dd']:
 np.testing.assert_allclose(new[col],old[col],rtol=0,atol=1e-7)
# Daily snapshots only for the chart; all table DD values above use intraday paths.
calendar=np.r_[t[np.flatnonzero(np.diff(b['day']))]+59,t[-1]+59]
chart=pd.DataFrame({'time':pd.to_datetime(calendar,unit='s')})
for name,(pt,pe) in paths.items():
 ix=np.searchsorted(pt,calendar,side='right')-1
 chart[name]=np.where(ix>=0,pe[np.maximum(ix,0)],0)
from add_session_hold_comparison import extend,plot,SESSION
s,chart=extend(s,chart)
s.to_csv(RUN/'comparison.csv',index=False,float_format='%.10f')
chart.to_csv(RUN/'daily_equity.csv',index=False)
plot(chart)
save_json(RUN/'verification.json',dict(all_passed=True,source_rows=len(t),baseline_inputs=raw_inputs,
 source_sha256=digest(MINUTES),roll_sha256=digest(ROLLS),matched_full_passive_to_native=True,
 baseline_ending_balance_and_gross_dd_match_native=True,portfolio_net_matches_sum=True,
 original_comparison_unchanged=True,variants=VARIANTS,
 session_benchmark_verified=True,session_verification_sha256=digest(SESSION/'verification.json'),
 fee_convention='1.05 per completed position, charged on exit',
 portfolio_dd_caveat='last native observation per second; may omit intra-second fluctuations',
 comparison_sha256=digest(RUN/'comparison.csv')))
print(s[['period','strategy','positions','net','equity_dd','net_dd']].to_string(index=False),flush=True)

