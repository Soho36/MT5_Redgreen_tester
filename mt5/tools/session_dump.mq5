//+------------------------------------------------------------------+
//| Session dump: writes the open time of every bar the tester sees. |
//| Research tool only - places no orders. Used to measure the real  |
//| session shape per date (first/last bar, early closes, shifts).   |
//+------------------------------------------------------------------+
#property strict

input string OutFile = "session_bars.csv";   // written to Common\Files

int      g_file = INVALID_HANDLE;
datetime g_lastBar = 0;

int OnInit()
{
   g_file = FileOpen(OutFile, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(g_file == INVALID_HANDLE)
   {
      Print("Cannot open ", OutFile, " err=", GetLastError());
      return INIT_FAILED;
   }
   FileWriteString(g_file, "bar_time\ttick_volume\n");
   return INIT_SUCCEEDED;
}

void OnTick()
{
   datetime t = iTime(_Symbol, _Period, 0);
   if(t == g_lastBar) return;
   g_lastBar = t;
   FileWriteString(g_file, TimeToString(t, TIME_DATE|TIME_MINUTES) + "\t"
                   + (string)iTickVolume(_Symbol, _Period, 1) + "\n");
}

void OnDeinit(const int reason)
{
   if(g_file != INVALID_HANDLE) FileClose(g_file);
}
