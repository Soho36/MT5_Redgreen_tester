"""Passive one-contract long, flattened and reopened every research session.

Uses the RTL/GG 23:30 cutoff and existing early-close calendar. Tester-only.
The final quote is used if a session has no quote at/after cutoff, including
end-of-dataset. The schedule is a historical benchmark, not a live fallback rule.
"""
import json
import re
import shutil
import numpy as np
import pandas as pd
from project_paths import PROJECT_ROOT as ROOT
from rtl_weekly_engine import MINUTES, CALENDAR, load_cutoffs
from verify_rtl_failed_breakout_short import QuoteIndex
from run_rtl_vwap_replay import INSTALL, SOURCE_DATA, COMMON, digest, hidden_process, save_json
from run_buy_hold_rolls import SYMBOL, FOLDER, idle, compile_file

RUN=ROOT/'Reports/buy_hold_20261108/session_flat'
EXACT=ROOT/'Reports/buy_hold_20261108/exact_start'
TAG='buyhold_session_20261108'
EXPERT='BuyHoldSession20261108'
PERIODS={'Full 2010-26':('2010-06-07','2026-10-02'),'2010-15':('2010-06-07','2016-01-01'),
 '2016-19':('2016-01-01','2020-01-01'),'2016-26':('2016-01-01','2026-10-02'),
 '2020-26':('2020-01-01','2026-10-02')}


def minute_data():
 b=pd.read_csv(MINUTES,sep='\t')
 stamp=pd.to_datetime(b['<DATE>']+' '+b['<TIME>'],format='%Y.%m.%d %H:%M:%S')
 t=stamp.to_numpy(dtype='datetime64[s]').astype(np.int64)
 bars={'day':t//86400,'minute':t%86400//60,
       **{k:b['<'+v+'>'].to_numpy(float) for k,v in zip('ohlc',['OPEN','HIGH','LOW','CLOSE'])},
       'tick_volume':b['<TICKVOL>'].to_numpy()}
 return b,t,bars


def prepare():
 RUN.mkdir(parents=True,exist_ok=True)
 assert not (RUN/'prepared.json').exists(),'Preserve prepared study'
 b,t,bars=minute_data(); quotes=QuoteIndex(bars);cutoffs=load_cutoffs()
 starts=np.r_[0,np.flatnonzero(np.diff(bars['day']))+1];ends=np.r_[starts[1:],len(t)]
 rows=[]
 for a,z in zip(starts,ends):
  day=int(b['<DATE>'].iloc[a].replace('.',''));cut=cutoffs.get(day,1410)
  x=a+int(np.searchsorted(bars['minute'][a:z],cut))
  if x<z:
   tx,px=next(quotes.quotes(x,x+1));reason='cutoff';last=x-1
  else:
   x=z-1;tx,px=list(quotes.quotes(x,x+1))[-1];reason='last_available';last=x
  te,pe=next(quotes.quotes(a,a+1))
  assert te<tx and te//86400==tx//86400
  rows.append(dict(session=b['<DATE>'].iloc[a],entry_epoch=te,exit_epoch=tx,
   entry_time=str(pd.Timestamp(te,unit='s')),exit_time=str(pd.Timestamp(tx,unit='s')),
   entry_bid=pe,entry=pe+.25,exit=px,gross=(px-pe-.25)*2,net=(px-pe-.25)*2-1.05,
   first_index=int(a),exit_index=int(x),last_exposed_index=int(last),cutoff_minute=cut,reason=reason))
 ledger=pd.DataFrame(rows);assert len(ledger)==4203
 ledger.to_csv(RUN/'expected_trades.csv',index=False)
 source=(EXACT/'BuyHoldExact20261108_roll.mq5').read_text(encoding='utf-8')
 for name,col in [('entryTimes','entry_epoch'),('exitTimes','exit_epoch')]:
  source,n=re.subn(r'long '+name+r'\[\]=\{[^}]+\};',
   'long '+name+'[]={'+','.join(map(str,ledger[col]))+'};',source)
  assert n==1
 source=source.replace('Roll hold','Session hold')
 (RUN/(EXPERT+'.mq5')).write_text(source,encoding='utf-8')
 config=(EXACT/'buyhold_exact_20261108_roll.ini').read_text(encoding='utf-16')
 config=config.replace('BuyHoldExact20261108_roll',EXPERT).replace('buyhold_exact_20261108_roll',TAG)
 (RUN/(TAG+'.ini')).write_text(config,encoding='utf-16')
 save_json(RUN/'prepared.json',dict(source_sha256=digest(MINUTES),calendar_sha256=digest(CALENDAR),
  sessions=len(ledger),fallback_sessions=ledger.loc[ledger.reason.eq('last_available'),'session'].tolist(),
  prepared_sha256={p.name:digest(p) for p in RUN.iterdir() if p.suffix in ['.mq5','.ini','.csv']}))
 print('Prepared',len(ledger),'sessions; net estimate',round(ledger.net.sum(),2),
       'fallbacks',int(ledger.reason.eq('last_available').sum()),flush=True)


def native():
 idle();assert not (RUN/'native.completed.json').exists()
 frozen=json.loads((RUN/'prepared.json').read_text())
 for n,h in frozen['prepared_sha256'].items():assert digest(RUN/n)==h,n
 src=RUN/(EXPERT+'.mq5');compile_file(src)
 target=SOURCE_DATA/'MQL5/Experts'/FOLDER/src.with_suffix('.ex5').name
 assert not target.exists();shutil.copyfile(src.with_suffix('.ex5'),target)
 assert all(not (COMMON/(TAG+s)).exists() for s in ['_deals.csv','_stats.csv'])
 print('Running session-flat MT5 benchmark',flush=True)
 process=hidden_process([str(INSTALL/'terminal64.exe'),'/config:'+str(RUN/(TAG+'.ini'))],timeout=900,cwd=INSTALL)
 assert process['returncode']==0,process
 for suffix in ['_deals.csv','_stats.csv']:shutil.copyfile(COMMON/(TAG+suffix),RUN/(TAG+suffix))
 shutil.copyfile(SOURCE_DATA/(TAG+'.htm'),RUN/(TAG+'.htm'))
 for p in SOURCE_DATA.glob(TAG+'*.png'):shutil.copyfile(p,RUN/p.name)
 save_json(RUN/'native.completed.json',dict(**process,binary_sha256=digest(src.with_suffix('.ex5')),
  outputs={p.name:digest(p) for p in RUN.glob(TAG+'*') if p.suffix in ['.csv','.htm']}))
 print(pd.read_csv(RUN/(TAG+'_stats.csv'),sep='\t').to_string(index=False),flush=True)


def verify():
 b,t,bars=minute_data();f=pd.read_csv(RUN/(TAG+'_deals.csv'),sep='\t')
 ins=f.loc[f.entry.eq(0)].reset_index(drop=True);outs=f.loc[f.entry.eq(1)].reset_index(drop=True)
 stat=pd.read_csv(RUN/(TAG+'_stats.csv'),sep='\t').iloc[0]
 assert len(ins)==len(outs)==4203==stat.trades
 assert ins.type.eq(0).all() and outs.type.eq(1).all() and f.volume.eq(1).all()
 assert f.commission.eq(0).all() and f.swap.eq(0).all()
 assert stat.tick_value/stat.tick_size==2
 # Parse calendar separately and derive each session from raw dates, then compare fills.
 cal=CALENDAR.read_text(encoding='utf-8')
 cd=list(map(int,re.search(r'EC_DATE\[EC_COUNT\] = \{([^}]+)',cal).group(1).split(',')))
 cm=list(map(int,re.search(r'EC_FLAT_MIN\[EC_COUNT\] = \{([^}]+)',cal).group(1).split(',')))
 ec=dict(zip(cd,cm));q=QuoteIndex(bars);paths=[];verified=[]
 for j,(date,g) in enumerate(b.groupby('<DATE>',sort=False)):
  a=int(g.index[0]);z=int(g.index[-1]); cutoff=ec.get(int(date.replace('.','')),1410)
  eligible=g.index[bars['minute'][g.index]>=cutoff]
  lastbar=not len(eligible);x=z if lastbar else int(eligible[0]);last=x if lastbar else x-1
  et,ep=next(q.quotes(a,a+1));xt,xp=(list(q.quotes(x,x+1))[-1] if lastbar else next(q.quotes(x,x+1)))
  assert ins.time[j]==pd.Timestamp(et,unit='s').strftime('%Y.%m.%d %H:%M:%S')
  assert outs.time[j]==pd.Timestamp(xt,unit='s').strftime('%Y.%m.%d %H:%M:%S')
  assert ins.price[j]==ep+.25 and outs.price[j]==xp
  profit=(xp-ins.price[j])*2
  assert outs.profit[j]==profit
  # Intraday high/low extrema only while held; exclude post-exit cutoff-minute prices.
  high=(bars['h'][a:last+1]-ins.price[j])*2
  low=(bars['l'][a:last+1]-ins.price[j])*2
  assert len(high)>0
  paths.append((high,low,profit,et,xt))
  verified.append(dict(session=date,entry_time=ins.time[j],exit_time=outs.time[j],gross=profit,net=profit-1.05))
 pd.DataFrame(verified).to_csv(RUN/'verified_trades.csv',index=False)
 assert abs(sum(p[2] for p in paths)-stat.profit)<1e-7
 rows=[];daily=[]
 for period,(start,end) in PERIODS.items():
  lo=int(pd.Timestamp(start).timestamp());hi=int(pd.Timestamp(end).timestamp())
  net=gross=peak=gpeak=dd=gdd=0.;count=0
  for high,low,profit,et,xt in paths:
   if not lo<=et<hi:continue
   rh=np.r_[net+high,net+profit];rl=np.r_[net+low,net+profit]
   gh=np.r_[gross+high,gross+profit];gl=np.r_[gross+low,gross+profit]
   dd=max(dd,float((np.maximum.accumulate(np.r_[peak,rh])[1:]-rl).max()))
   gdd=max(gdd,float((np.maximum.accumulate(np.r_[gpeak,gh])[1:]-gl).max()))
   peak=max(peak,float(rh.max()));gpeak=max(gpeak,float(gh.max()))
   net+=profit-1.05;gross+=profit;count+=1;dd=max(dd,peak-net)
   if period=='Full 2010-26':daily.append(dict(time=str(pd.Timestamp(xt,unit='s')),equity=net))
  rows.append(dict(period=period,strategy='Hold, flatten/reopen each session',positions=count,max_contracts=1,
   net=net,equity_dd=dd,gross=gross,fees=count*1.05,net_dd=net/dd,
   drawdown_method='verified native fills, raw minute extrema only while held; commission on exit'))
  if period=='Full 2010-26':assert abs(gdd-stat.equity_dd)<1e-7,(gdd,stat.equity_dd)
 pd.DataFrame(rows).to_csv(RUN/'summaries.csv',index=False,float_format='%.10f')
 pd.DataFrame(daily).to_csv(RUN/'daily_equity.csv',index=False)
 save_json(RUN/'verification.json',dict(all_passed=True,sessions=4203,all_native_fills_verified=True,
  gross_equity_dd_matches_mt5=True,source_sha256=digest(MINUTES),calendar_sha256=digest(CALENDAR),
  summaries_sha256=digest(RUN/'summaries.csv'),results=rows))
 print(pd.DataFrame(rows)[['period','positions','net','equity_dd','net_dd']].to_string(index=False),flush=True)

if __name__=='__main__':
 import sys
 {'prepare':prepare,'native':native,'verify':verify}[sys.argv[1]]()
