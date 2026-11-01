// Tester-only blue session VWAP slope gate. Exported real-volume labels, not synthetic tester volume.
input bool UseSlopeGate = false;
datetime sr_available[], sr_session[], sr_bar[];
double sr_close[], sr_delta[];
bool sr_known[];
int sr_count=0, sr_log=INVALID_HANDLE;
bool SlopeReplayInit()
{
   if(!MQLInfoInteger(MQL_TESTER)) { Print("Slope replay is tester-only"); return false; }
   int f=FileOpen("rtl_slope_replay_20261101_features.tsv",FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(f==INVALID_HANDLE) return false;
   string header[6]={"available","session","bar","close","delta","known"};
   for(int i=0;i<6;i++) if(FileReadString(f)!=header[i]) { FileClose(f); return false; }
   while(!FileIsEnding(f))
   {
      datetime available=(datetime)FileReadNumber(f);
      if(available==0 && FileIsEnding(f)) break;
      datetime session=(datetime)FileReadNumber(f), bar=(datetime)FileReadNumber(f);
      double close=FileReadNumber(f), delta=FileReadNumber(f);
      bool known=FileReadNumber(f)==1;
      if(available!=bar+1800 || session!=bar-bar%86400 || (sr_count>0 && available<=sr_available[sr_count-1]))
      { FileClose(f); return false; }
      int n=sr_count+1;
      ArrayResize(sr_available,n,20000); ArrayResize(sr_session,n,20000); ArrayResize(sr_bar,n,20000);
      ArrayResize(sr_close,n,20000); ArrayResize(sr_delta,n,20000); ArrayResize(sr_known,n,20000);
      sr_available[sr_count]=available; sr_session[sr_count]=session; sr_bar[sr_count]=bar;
      sr_close[sr_count]=close; sr_delta[sr_count]=delta; sr_known[sr_count]=known; sr_count++;
   }
   FileClose(f);
   if(sr_count==0) return false;
   sr_log=FileOpen("slope_decisions_"+g_runTag+".tsv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(sr_log==INVALID_HANDLE) return false;
   FileWrite(sr_log,"time","signal_bar","signal_close","delta","known","blocked");
   return true;
}
bool SlopeReplayAllows(datetime barOpen,double close1)
{
   datetime signal=iTime(_Symbol,_Period,1), now=TimeCurrent();
   int lo=0,hi=sr_count-1,j=-1;
   while(lo<=hi) { int m=(lo+hi)/2; if(sr_available[m]<=now) {j=m;lo=m+1;} else hi=m-1; }
   // Original baseline includes an October trade after the frozen feature window.
   // Keep it in OFF for whole-ledger reconciliation; strict ON blocks unknowns.
   if(signal>sr_bar[sr_count-1])
   {
      FileWrite(sr_log,TimeToString(barOpen,TIME_DATE|TIME_SECONDS),TimeToString(signal,TIME_DATE|TIME_SECONDS),
                DoubleToString(close1,10),0,0,(int)UseSlopeGate);
      return !UseSlopeGate;
   }
   if(j<0 || sr_bar[j]!=signal || MathAbs(sr_close[j]-close1)>_Point)
   { Print("SLOPE LABEL MISMATCH at ",TimeToString(signal)); ExpertRemove(); return false; }
   bool known=sr_known[j] && sr_session[j]==barOpen-barOpen%86400;
   bool blocked=UseSlopeGate && (!known || sr_delta[j]<=0.0);
   FileWrite(sr_log,TimeToString(barOpen,TIME_DATE|TIME_SECONDS),TimeToString(signal,TIME_DATE|TIME_SECONDS),
             DoubleToString(close1,10),DoubleToString(sr_delta[j],14),(int)known,(int)blocked);
   return !blocked;
}
void SlopeReplayClose() { if(sr_log!=INVALID_HANDLE) {FileClose(sr_log);sr_log=INVALID_HANDLE;} }
