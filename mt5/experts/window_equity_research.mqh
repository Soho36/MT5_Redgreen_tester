// Passive tester-only balance/equity observations. Binary rows: int64 seconds,
// float64 balance, float64 equity, int64 cumulative completed round trips.
int we_file=INVALID_HANDLE;
long we_closed=0,we_last_closed=-1,we_rows=0;
double we_balance=0,we_equity=0;
bool WindowEquityInit()
{
   if(!MQLInfoInteger(MQL_TESTER)) return false;
   we_file=FileOpen("window_equity_"+g_runTag+".bin",FILE_WRITE|FILE_BIN|FILE_COMMON);
   return we_file!=INVALID_HANDLE;
}
void WindowEquitySample()
{
   if(we_file==INVALID_HANDLE) return;
   double b=AccountInfoDouble(ACCOUNT_BALANCE),e=AccountInfoDouble(ACCOUNT_EQUITY);
   if(we_rows>0 && b==we_balance && e==we_equity && we_closed==we_last_closed) return;
   FileWriteLong(we_file,(long)TimeCurrent());FileWriteDouble(we_file,b);
   FileWriteDouble(we_file,e);FileWriteLong(we_file,we_closed);
   we_balance=b;we_equity=e;we_last_closed=we_closed;we_rows++;
}
void WindowEquityTransaction(const MqlTradeTransaction &trans)
{
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD && trans.deal>0)
   {
      long entry=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY) we_closed++;
   }
   WindowEquitySample();
}
void WindowEquityClose()
{
   WindowEquitySample();
   if(we_file!=INVALID_HANDLE) {FileClose(we_file);we_file=INVALID_HANDLE;}
}
