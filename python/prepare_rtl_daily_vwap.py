"""Prepare daily RTL with monthly real-volume VWAP; no month-end flatten."""
import json,re,shutil
import numpy as np
import pandas as pd
from project_paths import PROJECT_ROOT as ROOT
from prepare_rtl_weekly_opposite_gate import sha,DATA,SYMBOL,BASE

RUN=ROOT/'Reports/rtl_daily_monthly_vwap_20261118'
DOC=ROOT/'docs/baseline/rtl-daily-monthly-vwap'
EXPERT='RTL_daily_monthly_vwap'
FEATURE='rtl_daily_monthly_vwap_20261118_features.csv'
def tag(arm): return 'dvw_20261118_'+arm

def build_features(source=DATA):
    chunks=[]
    for raw in pd.read_csv(source,sep='\t',chunksize=400000):
        date=pd.to_datetime(raw['<DATE>'],format='%Y.%m.%d')
        vol=raw['<VOL>'].to_numpy(float)
        assert np.isfinite(vol).all() and (vol>0).all()
        f=pd.DataFrame(dict(date=date,open=raw['<OPEN>'],high=raw['<HIGH>'],low=raw['<LOW>'],close=raw['<CLOSE>'],
                            volume=vol,pv=(raw['<HIGH>']+raw['<LOW>']+raw['<CLOSE>'])/3*vol))
        chunks.append(f.groupby('date',sort=True).agg(open=('open','first'),high=('high','max'),low=('low','min'),
                      close=('close','last'),volume=('volume','sum'),pv=('pv','sum')))
    f=pd.concat(chunks).groupby(level=0,sort=True).agg(open=('open','first'),high=('high','max'),low=('low','min'),
                      close=('close','last'),volume=('volume','sum'),pv=('pv','sum'))
    f['month']=f.index.year*100+f.index.month
    f['vwap']=f.pv.groupby(f.month).cumsum()/f.volume.groupby(f.month).cumsum()
    prev=f.close.shift()
    f['tr']=pd.concat([f.high-f.low,(f.high-prev).abs(),(f.low-prev).abs()],axis=1).max(axis=1)
    f.iloc[0,f.columns.get_loc('tr')]=np.nan
    f['a20']=f.tr.rolling(20,min_periods=20).mean()
    f['known']=f.a20.gt(0)
    return f

HEADER=r'''
input bool UseDailyVwapGate=false;
datetime dv_dates[],dv_available[];
double dv_close[],dv_vwap[],dv_a20[];
int dv_month[],dv_known[];
int dv_count=0,dv_log=INVALID_HANDLE;
bool dv_first=true;
bool DailyVwapInit()
{
   int f=FileOpen("rtl_daily_monthly_vwap_20261118_features.csv",FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(f==INVALID_HANDLE) return false;
   for(int i=0;i<7;i++) FileReadString(f);
   while(!FileIsEnding(f))
   {
      datetime date=(datetime)FileReadNumber(f);
      if(date<=0) break;
      datetime available=(datetime)FileReadNumber(f);
      int month=(int)FileReadNumber(f);
      double c=FileReadNumber(f),v=FileReadNumber(f),a=FileReadNumber(f);
      int known=(int)FileReadNumber(f);
      if(available!=date+86400 || (dv_count>0 && date<=dv_dates[dv_count-1])) {FileClose(f);return false;}
      ArrayResize(dv_dates,dv_count+1);ArrayResize(dv_available,dv_count+1);
      ArrayResize(dv_month,dv_count+1);ArrayResize(dv_close,dv_count+1);
      ArrayResize(dv_vwap,dv_count+1);ArrayResize(dv_a20,dv_count+1);ArrayResize(dv_known,dv_count+1);
      dv_dates[dv_count]=date;dv_available[dv_count]=available;dv_month[dv_count]=month;
      dv_close[dv_count]=c;dv_vwap[dv_count]=v;dv_a20[dv_count]=a;dv_known[dv_count]=known;dv_count++;
   }
   FileClose(f);
   dv_log=FileOpen("daily_candidates_"+g_runTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(dv_log==INVALID_HANDLE) return false;
   FileWrite(dv_log,"time","signal","close","known","blocked","vwap","a20");
   return dv_count>0;
}
bool DailyVwapAllows(double close1)
{
   datetime date=iTime(_Symbol,PERIOD_D1,1);
   int lo=0,hi=dv_count-1,j=-1;
   while(lo<=hi) {int mid=(lo+hi)/2;
      if(dv_dates[mid]==date) {j=mid;break;}
      if(dv_dates[mid]<date) lo=mid+1; else hi=mid-1;
   }
   if(j<0 || dv_available[j]>TimeCurrent() || MathAbs(dv_close[j]-close1)>_Point)
   {Print("DAILY_FEATURE_ERROR");ExpertRemove();return false;}
   MqlDateTime dt;TimeToStruct(TimeCurrent(),dt);
   bool known=dv_known[j]!=0 && dv_month[j]==dt.year*100+dt.mon;
   bool blocked=UseDailyVwapGate && known && close1<dv_vwap[j]-dv_a20[j];
   FileWrite(dv_log,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
       TimeToString(date,TIME_DATE),close1,(int)known,(int)blocked,
       DoubleToString(dv_vwap[j],12),DoubleToString(dv_a20[j],12));
   return !blocked;
}
'''

def build_source():
    s=(BASE/'RTL_timeframe.mq5').read_text(encoding='utf-8')
    assert sha(BASE/'RTL_timeframe.mq5')=='8995d0ed6f97f21b15f4ce31f862fb8f642a1eae5a4e28c6bc371cb928165810'
    edits=[
      ('// ======== EA CORE ========','#include "daily_monthly_vwap.mqh"\n#include "window_equity_research.mqh"\n\n// ======== EA CORE ========'),
      ('int OnInit()\n{','int OnInit()\n{\n   if(!MQLInfoInteger(MQL_TESTER) || _Period!=PERIOD_D1 || UseFlattenEnd || UseTradeWindow) return INIT_FAILED;'),
      ('   DisplaySettings();\n   return(INIT_SUCCEEDED);','   if(!DailyVwapInit() || !WindowEquityInit()) return INIT_FAILED;\n   DisplaySettings();\n   return(INIT_SUCCEEDED);'),
      ('void OnTick()','void StrategyTick()'),
      ('\t   double entry = h1;','\t   if(!DailyVwapAllows(c1)) return;\n\t   double entry = h1;')]
    for old,new in edits:
        assert s.count(old)==1,repr(old)
        s=s.replace(old,new)
    return s+r'''
void OnTick()
{
   if(dv_first) {
      int f=FileOpen("daily_start_"+g_runTag+".csv",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
      if(f!=INVALID_HANDLE) {FileWriteString(f,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS));FileClose(f);}
      dv_first=false;
   }
   WindowEquitySample();StrategyTick();WindowEquitySample();
}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
{WindowEquityTransaction(trans);}
void OnDeinit(const int reason)
{WindowEquityClose();if(dv_log!=INVALID_HANDLE) FileClose(dv_log);}
'''

def main():
    assert not (RUN/'manifest.json').exists(),'Preserve prepared run'
    RUN.mkdir(exist_ok=True,parents=True)
    f=build_features()
    f.to_csv(RUN/'daily_features.csv',index_label='date',float_format='%.17g')
    dates=f.index.to_numpy(dtype='datetime64[s]').astype(np.int64)
    labels=pd.DataFrame(dict(date=dates,available=dates+86400,month=f.month.to_numpy(),close=f.close.to_numpy(),
                              vwap=f.vwap.to_numpy(),a20=f.a20.fillna(0).to_numpy(),known=f.known.astype(int).to_numpy()))
    labels.to_csv(RUN/FEATURE,sep='\t',index=False,float_format='%.17g')
    src=build_source()
    (RUN/(EXPERT+'.mq5')).write_text(src,encoding='utf-8')
    (ROOT/'mt5/experts'/(EXPERT+'.mq5')).write_text(src,encoding='utf-8')
    (RUN/'daily_monthly_vwap.mqh').write_text(HEADER,encoding='utf-8')
    (ROOT/'mt5/experts/daily_monthly_vwap.mqh').write_text(HEADER,encoding='utf-8')
    shutil.copyfile(BASE/'early_closes.mqh',RUN/'early_closes.mqh')
    shutil.copyfile(ROOT/'mt5/experts/window_equity_research.mqh',RUN/'window_equity_research.mqh')
    jobs=[]
    for arm in ('baseline','gated'):
        text=(BASE/'tf_20261015_rtl_m30_rr1p0.ini').read_text(encoding='utf-16')
        changes=dict(Expert='CodexResearch\\'+EXPERT+'.ex5',Symbol=SYMBOL,Period='D1',ToDate='2026.11.14',
                     RunTag=tag(arm),Report=tag(arm)+'.htm',UseFlattenEnd='false',UseTradeWindow='false')
        for key,value in changes.items():
            assert len(re.findall('^'+key+'=.*$',text,re.M))==1,key
            text=re.sub('^'+key+'=.*$',lambda _:key+'='+value,text,flags=re.M)
        text=text.replace('[TesterInputs]','[TesterInputs]\nUseDailyVwapGate='+str(arm=='gated').lower())
        (RUN/(tag(arm)+'.ini')).write_text(text,encoding='utf-16')
        outputs=[f'runband_{tag(arm)}_1.00.csv',f'runband_{tag(arm)}_1.00_stats.csv',
                 f'window_equity_{tag(arm)}.bin',f'daily_candidates_{tag(arm)}.csv',f'daily_start_{tag(arm)}.csv']
        jobs.append(dict(tag=tag(arm),arm=arm,outputs=outputs,inputs_files=[FEATURE]))
    paths=[DOC/'PROTOCOL.md',DATA,BASE/'RTL_timeframe.mq5',ROOT/'python/prepare_rtl_daily_vwap.py',
           *RUN.glob('*.mq5'),*RUN.glob('*.mqh'),*RUN.glob('*.ini'),RUN/FEATURE,RUN/'daily_features.csv']
    manifest=dict(expert=EXPERT,symbol=SYMBOL,jobs=jobs,input_hashes={str(p):sha(p) for p in paths})
    (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Prepared',len(f),'daily labels and two native jobs',flush=True)
if __name__=='__main__':main()

