"""Prepare frozen native RTL control, entry exclusion, and flat-window jobs."""
import json
import re
import shutil
import pandas as pd
from build_news_windows import ROOT,OUT,DOC,RUN,WINDOW_CSV,TIME_CSV,sha
from prepare_rtl_news_days import BASE,TAG

EXPERT='RTL_news_windows_research'
POLICIES={'control':0,'entry':1,'flat':2}

def main():
    assert not (RUN/'manifest.json').exists(),'Preserve prepared study'
    windows=pd.read_csv(WINDOW_CSV,parse_dates=['start','end'])
    starts=','.join(map(str,windows.start.to_numpy(dtype='datetime64[s]').astype('int64')))
    ends=','.join(map(str,windows.end.to_numpy(dtype='datetime64[s]').astype('int64')))
    header='''// Frozen scheduled windows, research clock. Tester only.
input int NewsWindowMode=0; // 0=disabled, 1=cancel/block orders, 2=also flatten
datetime NW_START[]={STARTS};
datetime NW_END[]={ENDS};
int nw_file=INVALID_HANDLE,nw_previous=-1;
int NewsWindowIndex(datetime now)
{
   int lo=0,hi=ArraySize(NW_START)-1,result=-1;
   while(lo<=hi) {int mid=(lo+hi)/2;
      if(NW_START[mid]<=now) {result=mid;lo=mid+1;} else hi=mid-1;
   }
   if(result>=0 && now<NW_END[result]) return result;
   return -1;
}
bool NewsWindowInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || NewsWindowMode<0 || NewsWindowMode>2) return false;
   nw_file=FileOpen("news_actions_"+g_runTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\\t');
   if(nw_file==INVALID_HANDLE) return false;
   FileWrite(nw_file,"time","window","start","end","first","orders_before","positions_before","orders_after","positions_after");
   return true;
}
void NewsBeforeTick()
{
   if(NewsWindowMode==0) return;
   datetime now=SessionClock(TimeCurrent());
   int w=NewsWindowIndex(now);
   bool first=(w!=nw_previous);nw_previous=w;
   if(w<0) return;
   int orders=OrdersTotal(),positions=PositionsTotal();
   if(orders>0) CancelAllOrders();
   if(NewsWindowMode==2 && positions>0)
   {
      // Track a possible boundary-quote fill before closing it in this callback.
      // Ordinary StrategyOnTick would otherwise never see that position.
      if(PositionSelect(_Symbol) && !g_tracking)
      {
         g_tracking=true;g_ticket=PositionGetInteger(POSITION_TICKET);
         g_entryTime=(datetime)PositionGetInteger(POSITION_TIME);
         g_maeMoney=PositionGetDouble(POSITION_PROFIT);g_mfeMoney=g_maeMoney;
      }
      CloseAllPositions();SaveClosedTrackedTrade();
   }
   if(first || orders>0 || (NewsWindowMode==2 && positions>0))
      FileWrite(nw_file,TimeToString(now,TIME_DATE|TIME_SECONDS),w,
         TimeToString(NW_START[w],TIME_DATE|TIME_SECONDS),TimeToString(NW_END[w],TIME_DATE|TIME_SECONDS),
         (int)first,orders,positions,OrdersTotal(),PositionsTotal());
   if(OrdersTotal()>0 || (NewsWindowMode==2 && PositionsTotal()>0))
   {Print("NEWS_ACTION_ERROR");ExpertRemove();}
}
'''.replace('STARTS',starts).replace('ENDS',ends)
    (RUN/'news_windows_research.mqh').write_text(header,encoding='utf-8')
    src=(BASE/'RTL_GG_exclude16_replay.mq5').read_text(encoding='utf-8')
    replacements={
      '#include "window_equity_research.mqh"':'#include "window_equity_research.mqh"\n#include "news_windows_research.mqh"',
      'if(!WindowEquityInit()) return INIT_FAILED;':'if(!WindowEquityInit() || !NewsWindowInit()) return INIT_FAILED;',
      '   WindowEquityClose();':'   WindowEquityClose();\n   if(nw_file!=INVALID_HANDLE) FileClose(nw_file);',
      '   // 🔹 time window check (ENTRY ONLY)':'   if(NewsWindowMode>0 && NewsWindowIndex(SessionClock(TimeCurrent()))>=0) return;\n\n   // 🔹 time window check (ENTRY ONLY)',
      'void OnTick() {WindowEquitySample();StrategyOnTick();WindowEquitySample();}':
      'void OnTick() {WindowEquitySample();NewsBeforeTick();WindowEquitySample();StrategyOnTick();WindowEquitySample();}'}
    for anchor,value in replacements.items():
        assert src.count(anchor)==1,anchor
        src=src.replace(anchor,value)
    (RUN/(EXPERT+'.mq5')).write_text(src,encoding='utf-8')
    for name in ('early_closes.mqh','stock_early_closes.mqh','rtl_session_vwap.mqh','window_equity_research.mqh'):
        shutil.copyfile(BASE/name,RUN/name)
    ini=(BASE/(TAG+'.ini')).read_text(encoding='utf-16');jobs=[]
    for policy,mode in POLICIES.items():
        tag='newswin_20261110_'+policy;text=ini
        for key,value in dict(Expert='CodexResearch\\'+EXPERT+'.ex5',Report=tag+'.htm',RunTag=tag,LogVwapDecisions='false').items():
            assert len(re.findall('^'+key+'=.*$',text,re.M))==1
            text=re.sub('^'+key+'=.*$',lambda _:key+'='+value,text,flags=re.M)
        text=text.replace('[TesterInputs]',f'[TesterInputs]\nNewsWindowMode={mode}')
        fields=re.findall(r'^input\s+\w+\s+(\w+)\s*=',src+'\n'+header,re.M)
        given=re.findall(r'^(\w+)=',text.split('[TesterInputs]')[1].split('[',1)[0],re.M)
        assert sorted(fields)==sorted(given)
        (RUN/(tag+'.ini')).write_text(text,encoding='utf-16')
        outputs=[f'rtlvwap_{tag}_1.00.csv',f'rtlvwap_{tag}_1.00_stats.csv',f'window_equity_{tag}.bin',f'news_actions_{tag}.csv']
        jobs.append(dict(tag=tag,policy=policy,mode=mode,outputs=outputs))
    paths=[*RUN.glob('*.mq5'),*RUN.glob('*.mqh'),*RUN.glob('*.ini')]
    manifest=dict(expert=EXPERT,jobs=jobs,protocol_sha256=sha(DOC/'PROTOCOL.md'),
        calendar_sha256=sha(TIME_CSV),windows_sha256=sha(WINDOW_CSV),
        prepared_sha256={p.name:sha(p) for p in paths})
    (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Prepared three native RTL jobs',flush=True)

if __name__=='__main__':main()
