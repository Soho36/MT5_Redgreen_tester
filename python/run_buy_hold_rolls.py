"""Exact-start native hold and explicit roll-boundary close/reopen comparison."""
import json
import shutil
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from project_paths import PROJECT_ROOT as ROOT
from rtl_weekly_engine import MINUTES, ROLLS
from run_rtl_vwap_replay import INSTALL, SOURCE_DATA, COMMON, digest, hidden_process, save_json
from run_buy_hold import SOURCE as BASE_SOURCE

RUN=ROOT/'Reports/buy_hold_20261108/exact_start'
SYMBOL='MNQ_BuyHold_20261108'
FOLDER='CodexBuyHold'

def idle():
 r=subprocess.run(['tasklist','/FI','IMAGENAME eq terminal64.exe','/FO','CSV','/NH'],capture_output=True,text=True,check=True)
 assert 'terminal64.exe' not in r.stdout.lower(),'Preserve active terminal'

def compile_file(path):
 log=path.with_suffix('.compile.log')
 hidden_process([str(INSTALL/'MetaEditor64.exe'),'/compile:'+str(path),'/log:'+str(log)],timeout=180)
 s=log.read_text(encoding='utf-16')
 assert 'Result: 0 errors, 0 warnings' in s,s

def clone():
 RUN.mkdir(parents=True,exist_ok=True)
 assert not (RUN/'clone.completed.json').exists()
 idle()
 src=r'''#property strict
void OnStart()
{
 string name="MNQ_BuyHold_20261108", source="MNQcontDTBNT20102026_2";
 bool custom=false;
 if(SymbolExist(name,custom)) { Print("Preserve existing symbol"); return; }
 if(!CustomSymbolCreate(name,"CodexInstruments",source)) return;
 CustomSymbolSetString(name,SYMBOL_DESCRIPTION,"Buy hold 20261108; exact source plus June 4 warmup only");
 SymbolSelect(source,true); SymbolSelect(name,true);
 int f=FileOpen("buyhold_clone_20261108.tsv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
 FileWrite(f,"year","source_count","copied_count","read_count","prices_equal");
 for(int y=2010;y<=2026;y++)
 {
  datetime a=StringToTime(IntegerToString(y)+".01.01"), z=StringToTime(IntegerToString(y+1)+".01.01")-1;
  MqlRates rates[],back[];
  int n=-1;
  for(int t=0;t<120;t++) { n=CopyRates(source,PERIOD_M1,a,z,rates); if(n>0) break; Sleep(250); }
  if(n<=0) { FileClose(f); return; }
  int wrote=CustomRatesReplace(name,a,z,rates);
  int got=-1;
  for(int t=0;t<120;t++) { got=CopyRates(name,PERIOD_M1,a,z,back); if(got==n) break; Sleep(250); }
  bool equal=(got==n && wrote==n);
  if(equal) for(int k=0;k<n;k++)
   if(rates[k].time!=back[k].time || rates[k].open!=back[k].open || rates[k].high!=back[k].high || rates[k].low!=back[k].low || rates[k].close!=back[k].close || rates[k].tick_volume!=back[k].tick_volume || rates[k].spread!=back[k].spread || rates[k].real_volume!=back[k].real_volume) { equal=false; break; }
  FileWrite(f,y,n,wrote,got,equal); FileFlush(f);
  if(!equal) { FileClose(f); return; }
 }
 MqlRates pad[]; ArrayResize(pad,1380);
 for(int i=0;i<1380;i++)
 {
  pad[i].time=D'2010.06.04 01:00:00'+i*60;
  pad[i].open=1831.75; pad[i].high=1831.75; pad[i].low=1831.75; pad[i].close=1831.75;
  pad[i].tick_volume=4; pad[i].real_volume=4; pad[i].spread=1;
 }
 int added=CustomRatesUpdate(name,pad);
 FileClose(f);
 if(added!=1380) return;
 int done=FileOpen("buyhold_clone_20261108.done",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
 FileWriteString(done,"1380 warmup bars; all source bars unchanged"); FileClose(done);
}
'''
 path=RUN/'CloneBuyHold20261108.mq5'; path.write_text(src,encoding='utf-8'); compile_file(path)
 target=SOURCE_DATA/'MQL5/Scripts'/FOLDER; target.mkdir(parents=True,exist_ok=True)
 assert not (target/path.with_suffix('.ex5').name).exists()
 shutil.copyfile(path.with_suffix('.ex5'),target/path.with_suffix('.ex5').name)
 ini=RUN/'clone.ini'
 ini.write_text('[Charts]\nMaxBars=10000000\n[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[StartUp]\nScript=CodexBuyHold\\CloneBuyHold20261108\nSymbol=MNQcontDTBNT20102026_2\nPeriod=M1\nShutdownTerminal=1\n',encoding='utf-16')
 p=hidden_process([str(INSTALL/'terminal64.exe'),'/config:'+str(ini)],timeout=300,cwd=INSTALL)
 assert (COMMON/'buyhold_clone_20261108.done').exists()
 shutil.copyfile(COMMON/'buyhold_clone_20261108.tsv',RUN/'clone_verification.tsv')
 save_json(RUN/'clone.completed.json',p)
 print('Exact source clone verified; warmup only before test period.',flush=True)

def prepare():
 from verify_rtl_failed_breakout_short import QuoteIndex
 b=pd.read_csv(MINUTES,sep='\t')
 stamp=pd.to_datetime(b['<DATE>']+' '+b['<TIME>'],format='%Y.%m.%d %H:%M:%S')
 epochs=stamp.to_numpy(dtype='datetime64[s]').astype(np.int64)
 o,h,l,c=[b['<'+k+'>'].to_numpy(float) for k in ['OPEN','HIGH','LOW','CLOSE']]
 rolls=pd.read_csv(ROLLS)
 starts=np.searchsorted(epochs,pd.to_datetime(rolls.date).to_numpy(dtype='datetime64[s]').astype(np.int64))
 assert starts[0]==0 and np.all(np.diff(starts)>0)
 ends=np.r_[starts[1:]-1,len(b)-1]
 bars={'day':epochs//86400,'minute':epochs%86400//60,'o':o,'h':h,'l':l,'c':c,'tick_volume':b['<TICKVOL>'].to_numpy()}
 quotes=QuoteIndex(bars)
 rows=[]; cumulative=0.; maxeq=0.; dd=0.; worst=0.
 for j,(a,z) in enumerate(zip(starts,ends)):
  te,pe=next(quotes.quotes(a,a+1)); tx,px=list(quotes.quotes(z,z+1))[-1]
  assert pe==o[a] and px==c[z]
  assert te//60==epochs[a]//60 and tx//60==epochs[z]//60
  assert te>=1275868800 and tx<1790985600
  highs=cumulative+(h[a:z+1]-pe)*2
  lows=cumulative+(l[a:z+1]-pe)*2
  peaks=np.maximum.accumulate(np.r_[maxeq,highs])[1:]
  local=int(np.argmax(peaks-lows)); candidate=float(peaks[local]-lows[local])
  if candidate>dd: dd=candidate; dd_bar=str(stamp.iloc[a+local])
  maxeq=max(maxeq,float(highs.max())); worst=min(worst,float(lows.min()))
  profit=float((px-pe)*2); cumulative+=profit
  rows.append(dict(contract=rolls.iloc[j].symbol,instrument_id=int(rolls.iloc[j].instrument_id),
   entry_epoch=te,exit_epoch=tx,entry_time=str(pd.Timestamp(te,unit='s')),exit_time=str(pd.Timestamp(tx,unit='s')),
   entry=pe,exit=px,gross=profit,net=profit-1.05,cumulative_gross=cumulative))
 ledger=pd.DataFrame(rows); ledger.to_csv(RUN/'expected_roll_trades.csv',index=False)
 save_json(RUN/'roll_python_result.json',dict(contracts=len(rows),rollovers=len(rows)-1,gross=cumulative,
  net=cumulative-len(rows)*1.05,commission=len(rows)*1.05,maximum_gross_drawdown=dd,drawdown_trough=dd_bar,
  lowest_gross_equity_pnl=worst,raw_gross=float((c[-1]-o[0])*2),removed_boundary_gap_dollars=float((c[-1]-o[0])*2-cumulative),
  execution='Close at last available old-contract quote and reopen at first new-contract quote; flat across those roll boundaries. Hold through all other session gaps.'))
 base=BASE_SOURCE.replace('MNQcontDTBNT20102026_2',SYMBOL)
 # Explicit no-earlier-than-source guard; all warmup bars are outside the test.
 base=base.replace(' if(attempted) return;',' if(TimeCurrent()<D\'2010.06.07 01:00:00\') return;\n if(attempted) return;')
 for mode in ['hold','roll']:
  tag='buyhold_exact_20261108_'+mode; expert='BuyHoldExact20261108_'+mode
  source=base
  if mode=='roll':
   entry=','.join(str(r['entry_epoch']) for r in rows)
   exits=','.join(str(r['exit_epoch']) for r in rows)
   start=source.index('void OnTick()'); end=source.index('double OnTester()')
   lifecycle=r'''
long entryTimes[]={__ENTRIES__};
long exitTimes[]={__EXITS__};
int piece=0;
bool opened=false;
void OnTick()
{
 if(piece>=ArraySize(entryTimes)) return;
 if(!opened && TimeCurrent()>=entryTimes[piece])
 {
  MqlTradeRequest r={}; MqlTradeResult s={};
  r.action=TRADE_ACTION_DEAL; r.symbol=_Symbol; r.volume=1;
  r.type=ORDER_TYPE_BUY; r.price=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
  r.type_filling=ORDER_FILLING_FOK; r.magic=20261108;
  r.comment="Roll hold open";
  if(!OrderSend(r,s) || s.retcode!=TRADE_RETCODE_DONE) { Print("OPEN FAILED ",s.retcode); TesterStop(); return; }
  opened=true;
 }
 if(opened && piece<ArraySize(entryTimes)-1 && TimeCurrent()>=exitTimes[piece])
 {
  if(!PositionSelect(_Symbol)) { Print("POSITION MISSING"); TesterStop(); return; }
  MqlTradeRequest r={}; MqlTradeResult s={};
  r.action=TRADE_ACTION_DEAL; r.symbol=_Symbol; r.volume=1;
  r.position=(ulong)PositionGetInteger(POSITION_TICKET);
  r.type=ORDER_TYPE_SELL; r.price=SymbolInfoDouble(_Symbol,SYMBOL_BID);
  r.type_filling=ORDER_FILLING_FOK; r.magic=20261108;
  r.comment="Roll hold close";
  if(!OrderSend(r,s) || s.retcode!=TRADE_RETCODE_DONE) { Print("CLOSE FAILED ",s.retcode); TesterStop(); return; }
  opened=false; piece++;
 }
}
'''.replace('__ENTRIES__',entry).replace('__EXITS__',exits)
   source=source[:start]+lifecycle+source[end:]
  (RUN/(expert+'.mq5')).write_text(source,encoding='utf-8')
  cfg=(ROOT/'Reports/buy_hold_20261108/buy_hold_20261108.ini').read_text(encoding='utf-16')
  cfg=cfg.replace('MNQcontDTBNT20102026_2',SYMBOL).replace('BuyHold_dataset_20261108.ex5',expert+'.ex5')
  cfg=cfg.replace('buy_hold_20261108.htm',tag+'.htm').replace('RunTag=buy_hold_20261108','RunTag='+tag)
  (RUN/(tag+'.ini')).write_text(cfg,encoding='utf-16')
 save_json(RUN/'prepared.json',dict(source_sha256=digest(MINUTES),roll_sha256=digest(ROLLS),
  prepared_sha256={p.name:digest(p) for p in RUN.glob('*') if p.name.startswith(('BuyHoldExact','buyhold_exact'))}))
 print((RUN/'roll_python_result.json').read_text(),flush=True)

def native(mode):
 idle()
 tag='buyhold_exact_20261108_'+mode; expert='BuyHoldExact20261108_'+mode
 assert not (RUN/(tag+'.completed.json')).exists()
 prepared=json.loads((RUN/'prepared.json').read_text())['prepared_sha256']
 for n in [expert+'.mq5',tag+'.ini']: assert digest(RUN/n)==prepared[n]
 src=RUN/(expert+'.mq5'); compile_file(src)
 target=SOURCE_DATA/'MQL5/Experts'/FOLDER; target.mkdir(parents=True,exist_ok=True)
 assert not (target/src.with_suffix('.ex5').name).exists()
 shutil.copyfile(src.with_suffix('.ex5'),target/src.with_suffix('.ex5').name)
 print('Starting exact-start native '+mode,flush=True)
 p=hidden_process([str(INSTALL/'terminal64.exe'),'/config:'+str(RUN/(tag+'.ini'))],timeout=900,cwd=INSTALL)
 assert p['returncode']==0,p
 for n in [tag+'_deals.csv',tag+'_stats.csv']:
  shutil.copyfile(COMMON/n,RUN/n)
 shutil.copyfile(SOURCE_DATA/(tag+'.htm'),RUN/(tag+'.htm'))
 for img in SOURCE_DATA.glob(tag+'*.png'): shutil.copyfile(img,RUN/img.name)
 save_json(RUN/(tag+'.completed.json'),dict(**p,binary_sha256=digest(src.with_suffix('.ex5'))))
 print(pd.read_csv(RUN/(tag+'_deals.csv'),sep='\t').to_string(index=False),flush=True)
 print(pd.read_csv(RUN/(tag+'_stats.csv'),sep='\t').to_string(index=False),flush=True)

if __name__=='__main__':
 import sys
 action=sys.argv[1]
 if action in ['hold','roll']: native(action)
 else: {'clone':clone,'prepare':prepare}[action]()

