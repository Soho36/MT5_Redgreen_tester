// Tester-only daily trend assignment. No regime is used to filter entries.
input bool GreenSignal=false;
input int FastDays=50;
input double BullRR=1.0;
input double BearRR=1.0;
datetime tr_day=0, tr_previousDay=0, tr_entryPreviousDay=0;
double tr_previousClose=0, tr_fast=0, tr_slow=0;
double tr_entryClose=0, tr_entryFast=0, tr_entrySlow=0, tr_rr=1;
int tr_regime=-2, tr_entryRegime=-2;
int tr_exportErrors=0, tr_closeErrors=0;
int tr_checks=INVALID_HANDLE, tr_signals=INVALID_HANDLE;
double tr_o=0,tr_h=0,tr_l=0,tr_c=0;
datetime tr_qualified=0;

void UpdateTrendDay()
{
   datetime day=iTime(_Symbol,PERIOD_D1,0);
   if(day==tr_day) return;
   tr_day=day;
   tr_previousDay=iTime(_Symbol,PERIOD_D1,1);
   tr_previousClose=iClose(_Symbol,PERIOD_D1,1);
   tr_regime=-2; tr_fast=0; tr_slow=0;
   double closes[]; ArraySetAsSeries(closes,true);
   int copied=CopyClose(_Symbol,PERIOD_D1,1,200,closes);
   if(copied<200) return; // retain trades at 1R during unavailable SMA warmup
   for(int i=0;i<200;i++) tr_slow+=closes[i]/200.0;
   for(int i=0;i<FastDays;i++) tr_fast+=closes[i]/FastDays;
   tr_regime=0;
   if(tr_previousClose>tr_slow && tr_fast>tr_slow) tr_regime=1;
   if(tr_previousClose<tr_slow && tr_fast<tr_slow) tr_regime=-1;
}

void FreezeTrendAtEntry()
{
   UpdateTrendDay();
   tr_entryRegime=tr_regime;
   tr_entryPreviousDay=tr_previousDay;
   tr_entryClose=tr_previousClose;
   tr_entryFast=tr_fast; tr_entrySlow=tr_slow;
   tr_rr=(tr_regime==1 ? BullRR : (tr_regime==-1 ? BearRR : 1.0));
   tr_qualified=0;
}

bool OpenTrendExports()
{
   tr_checks=FileOpen(g_runTag+"_checks.csv",FILE_WRITE|FILE_CSV|FILE_COMMON);
   tr_signals=FileOpen(g_runTag+"_signals.csv",FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(tr_checks==INVALID_HANDLE || tr_signals==INVALID_HANDLE) return false;
   FileWrite(tr_checks,"ticket","check_time","bar_time","bar_close","target","qualified","assigned_rr","regime");
   FileWrite(tr_signals,"signal_time","submission_time","open","high","low","close","red_run","strategy");
   return true;
}

void LogTrendSignal()
{
   g_signalTime=iTime(_Symbol,_Period,1);
   tr_o=iOpen(_Symbol,_Period,1); tr_h=iHigh(_Symbol,_Period,1);
   tr_l=iLow(_Symbol,_Period,1); tr_c=iClose(_Symbol,_Period,1);
   if(FileWrite(tr_signals,TimeToString(g_signalTime,TIME_DATE|TIME_SECONDS),
      TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),tr_o,tr_h,tr_l,tr_c,g_redRun,
      (GreenSignal ? "GG" : "RR"))==0) tr_exportErrors++;
}

void LogTrendCheck(double barClose,double target)
{
   bool qualified=barClose>=target;
   if(qualified && tr_qualified==0) tr_qualified=TimeCurrent();
   if(FileWrite(tr_checks,(long)g_ticket,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
      TimeToString(iTime(_Symbol,_Period,1),TIME_DATE|TIME_SECONDS),barClose,target,(int)qualified,
      tr_rr,tr_entryRegime)==0) tr_exportErrors++;
}

void OnDeinit(const int reason)
{
   if(tr_checks!=INVALID_HANDLE) FileClose(tr_checks);
   if(tr_signals!=INVALID_HANDLE) FileClose(tr_signals);
}
