
input bool UseDailyRegime=false;
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
   dv_log=FileOpen("daily_regime_"+g_runTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(dv_log==INVALID_HANDLE) return false;
   FileWrite(dv_log,"effective","signal","close","vwap","a20","known","before","enabled");
   return dv_count>0;
}

bool wg_enabled=true;
long wg_cancelled=0;
int dv_next=0;
void RegimeUpdate()
{
   while(dv_next<dv_count && dv_available[dv_next]<=TimeCurrent())
   {
      int j=dv_next++;
      bool before=wg_enabled;
      if(dv_known[j]!=0) {
         if(dv_close[j]<dv_vwap[j]-dv_a20[j]) wg_enabled=false;
         else if(dv_close[j]>dv_vwap[j]-dv_a20[j]) wg_enabled=true;
      }
      FileWrite(dv_log,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
         TimeToString(dv_dates[j],TIME_DATE),dv_close[j],DoubleToString(dv_vwap[j],12),
         DoubleToString(dv_a20[j],12),dv_known[j],(int)before,(int)wg_enabled);
   }
}
