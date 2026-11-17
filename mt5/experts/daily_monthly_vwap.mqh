
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
