// Completed W1 candles only; references are the most recent earlier colour.
input bool UseWeeklyGate=false;
bool wg_enabled=true;
datetime wg_processed=0,wg_green=0,wg_red=0;
double wg_green_low=0,wg_red_high=0;
int wg_file=INVALID_HANDLE;
long wg_cancelled=0;

bool WeeklyGateInit()
{
   wg_file=FileOpen("weekly_gate_"+g_runTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(wg_file==INVALID_HANDLE) return false;
   FileWrite(wg_file,"effective","week","open","high","low","close","green_week","green_low",
             "red_week","red_high","before","enabled","trigger","pending_before","positions_before");
   return true;
}
void WeeklyGateUpdate()
{
   datetime completed=iTime(_Symbol,PERIOD_W1,1);
   if(completed==0 || completed==wg_processed) return;
   MqlRates w[];
   if(CopyRates(_Symbol,PERIOD_W1,1,1,w)!=1) return;
   if(w[0].time!=completed) return;
   bool before=wg_enabled;
   string trigger="none";
   if(w[0].close<w[0].open && wg_green>0 && w[0].close<wg_green_low)
   {wg_enabled=false;trigger="halt";}
   else if(w[0].close>w[0].open && wg_red>0 && w[0].close>wg_red_high)
   {wg_enabled=true;trigger="resume";}
   FileWrite(wg_file,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
             TimeToString(w[0].time,TIME_DATE),w[0].open,w[0].high,w[0].low,w[0].close,
             (long)wg_green,wg_green_low,(long)wg_red,wg_red_high,(int)before,(int)wg_enabled,
             trigger,OrdersTotal(),PositionsTotal());
   if(w[0].close>w[0].open) {wg_green=completed;wg_green_low=w[0].low;}
   if(w[0].close<w[0].open) {wg_red=completed;wg_red_high=w[0].high;}
   wg_processed=completed;
}
