"""One-contract long hold benchmark, raw continuous NQ with MNQ economics."""
import json
import shutil
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from project_paths import PROJECT_ROOT as ROOT
from rtl_weekly_engine import MINUTES
from run_rtl_vwap_replay import INSTALL, SOURCE_DATA, COMMON, digest, hidden_process, save_json

RUN = ROOT / 'Reports/buy_hold_20261108'
EXPERT = 'BuyHold_dataset_20261108'
TAG = 'buy_hold_20261108'
FOLDER = 'CodexBuyHold'

SOURCE = r'''
#property strict
input string RunTag="buy_hold_20261108";
bool attempted=false;
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;
 if(_Symbol!="MNQcontDTBNT20102026_2") return INIT_PARAMETERS_INCORRECT;
 return INIT_SUCCEEDED;
}
void OnTick()
{
 if(attempted) return;
 attempted=true;
 MqlTradeRequest r={}; MqlTradeResult s={};
 r.action=TRADE_ACTION_DEAL; r.symbol=_Symbol; r.volume=1.0;
 r.type=ORDER_TYPE_BUY; r.price=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
 r.type_filling=ORDER_FILLING_FOK; r.magic=20261108;
 r.comment="Hold entire dataset";
 if(!OrderSend(r,s) || s.retcode!=TRADE_RETCODE_DONE)
 { Print("ENTRY FAILED ",s.retcode," ",s.comment); TesterStop(); }
}
double OnTester()
{
 HistorySelect(0,TimeCurrent());
 int f=FileOpen(RunTag+"_deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
 FileWrite(f,"time","entry","type","volume","price","profit","commission","swap","reason");
 for(int i=0;i<HistoryDealsTotal();i++)
 {
  ulong d=HistoryDealGetTicket(i);
  if(HistoryDealGetString(d,DEAL_SYMBOL)!=_Symbol) continue;
  FileWrite(f,TimeToString((datetime)HistoryDealGetInteger(d,DEAL_TIME),TIME_DATE|TIME_SECONDS),
   HistoryDealGetInteger(d,DEAL_ENTRY),HistoryDealGetInteger(d,DEAL_TYPE),
   DoubleToString(HistoryDealGetDouble(d,DEAL_VOLUME),2),DoubleToString(HistoryDealGetDouble(d,DEAL_PRICE),8),
   DoubleToString(HistoryDealGetDouble(d,DEAL_PROFIT),8),DoubleToString(HistoryDealGetDouble(d,DEAL_COMMISSION),8),
   DoubleToString(HistoryDealGetDouble(d,DEAL_SWAP),8),HistoryDealGetInteger(d,DEAL_REASON));
 }
 FileClose(f);
 f=FileOpen(RunTag+"_stats.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
 FileWrite(f,"profit","equity_dd","trades","point","tick_size","tick_value","swap_long");
 FileWrite(f,TesterStatistics(STAT_PROFIT),TesterStatistics(STAT_EQUITY_DD),TesterStatistics(STAT_TRADES),
 SymbolInfoDouble(_Symbol,SYMBOL_POINT),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),
 SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_LONG));
 FileClose(f);
 return TesterStatistics(STAT_PROFIT);
}
'''

def prepare():
 RUN.mkdir(parents=True,exist_ok=True)
 if (RUN/'manifest.json').exists(): raise RuntimeError('Preserve existing run')
 b=pd.read_csv(MINUTES,sep='\t')
 o,h,l,c=[b['<'+k+'>'].to_numpy(float) for k in ['OPEN','HIGH','LOW','CLOSE']]
 first,last=b.iloc[0],b.iloc[-1]
 # Both extremes of each minute included; same-minute ordering cannot change the global maximum here.
 peaks=np.maximum.accumulate(h)
 dd=peaks-l
 trough=int(dd.argmax()); peak=int(h[:trough+1].argmax())
 summary=dict(rows=len(b),first_time=first['<DATE>']+' '+first['<TIME>'],
 last_bar=last['<DATE>']+' '+last['<TIME>'],entry_open=float(o[0]),exit_close=float(c[-1]),
 gross_points=float(c[-1]-o[0]),gross_dollars=float((c[-1]-o[0])*2),
 net_after_1_05=float((c[-1]-o[0])*2-1.05),
 max_drawdown_dollars=float(dd[trough]*2),peak_price=float(h[peak]),trough_price=float(l[trough]),
 peak_bar=b.iloc[peak]['<DATE>']+' '+b.iloc[peak]['<TIME>'],
 trough_bar=b.iloc[trough]['<DATE>']+' '+b.iloc[trough]['<TIME>'],
 worst_open_pnl=float((l.min()-o[0])*2),min_price=float(l.min()),
 note='Raw unadjusted continuous-contract series; roll gaps included. $2 per point; one $1.05 round-trip cost. No stops or session exits.')
 assert peak<trough
 save_json(RUN/'python_result.json',summary)
 (RUN/(EXPERT+'.mq5')).write_text(SOURCE,encoding='utf-8')
 config=f'''[Tester]
Expert={FOLDER}\\{EXPERT}.ex5
Symbol=MNQcontDTBNT20102026_2
Period=M1
Optimization=0
Model=1
FromDate=2010.06.07
ToDate=2026.10.02
ForwardMode=0
Deposit=500000
Currency=USD
ProfitInPips=0
Leverage=100
ExecutionMode=0
Visual=0
UseLocal=1
UseRemote=0
UseCloud=0
ShutdownTerminal=1
Report={TAG}.htm
ReplaceReport=0
[TesterInputs]
RunTag={TAG}
[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
'''
 (RUN/(TAG+'.ini')).write_text(config,encoding='utf-16')
 save_json(RUN/'manifest.json',dict(source=str(MINUTES),source_sha256=digest(MINUTES),
 prepared_sha256={p.name:digest(p) for p in RUN.glob('*') if p.suffix in ['.mq5','.ini']},
 symbol='MNQcontDTBNT20102026_2',point_value=2,contracts=1,direction='long'))
 print(json.dumps(summary,indent=2),flush=True)

def native():
 if (RUN/(TAG+'.completed.json')).exists(): raise RuntimeError('Preserve completed run')
 manifest=json.loads((RUN/'manifest.json').read_text())
 for name,sha in manifest['prepared_sha256'].items(): assert digest(RUN/name)==sha
 active=subprocess.run(['tasklist','/FI','IMAGENAME eq terminal64.exe','/FO','CSV','/NH'],capture_output=True,text=True,check=True)
 if 'terminal64.exe' in active.stdout.lower(): raise RuntimeError('Terminal is active; preserve it')
 log=RUN/'compile.log'
 hidden_process([str(INSTALL/'MetaEditor64.exe'),'/compile:'+str(RUN/(EXPERT+'.mq5')),'/log:'+str(log)],timeout=180)
 result=log.read_text(encoding='utf-16')
 assert 'Result: 0 errors, 0 warnings' in result,result
 target=SOURCE_DATA/'MQL5/Experts'/FOLDER
 target.mkdir(parents=True,exist_ok=True)
 for ext in ['.mq5','.ex5']:
  dest=target/(EXPERT+ext)
  assert not dest.exists(),dest
  shutil.copyfile(RUN/dest.name,dest)
 outputs=[TAG+'_deals.csv',TAG+'_stats.csv']
 assert all(not (COMMON/n).exists() for n in outputs)
 save_json(RUN/'native.started.json',dict(binary_sha256=digest(target/(EXPERT+'.ex5'))))
 print('Starting MT5 one-position hold',flush=True)
 process=hidden_process([str(INSTALL/'terminal64.exe'),'/config:'+str(RUN/(TAG+'.ini'))],timeout=900,cwd=INSTALL)
 assert process['returncode']==0,process
 for n in outputs: shutil.copyfile(COMMON/n,RUN/n)
 shutil.copyfile(SOURCE_DATA/(TAG+'.htm'),RUN/(TAG+'.htm'))
 save_json(RUN/(TAG+'.completed.json'),dict(**process,outputs={n:digest(RUN/n) for n in outputs}))
 print(pd.read_csv(RUN/outputs[0],sep='\t').to_string(index=False),flush=True)
 print(pd.read_csv(RUN/outputs[1],sep='\t').to_string(index=False),flush=True)

if __name__=='__main__':
 import sys
 {'prepare':prepare,'native':native}[sys.argv[1]]()
