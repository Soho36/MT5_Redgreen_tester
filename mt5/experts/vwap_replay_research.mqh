// Isolated tester-only VWAP candidate gate and passive complete-history exports.
#ifndef VWAP_REPLAY_RESEARCH_MQH
#define VWAP_REPLAY_RESEARCH_MQH

input bool UseVwapReplayGate=false;
input string VwapReplayFeatures="rtl_vwap_replay_20261026_features.csv";
datetime g_vrAvailable[],g_vrSession[],g_vrBar[];
double g_vrClose[],g_vrVwap[],g_vrA20[];
bool g_vrKnown[];
int g_vrCount=0,g_vrErrors=0,g_vrCandidates=0,g_vrBlocked=0;
int g_vrCandidateFile=INVALID_HANDLE,g_vrEquityFile=INVALID_HANDLE;
long g_vrEquityRows=0,g_vrLastMsc=0;
double g_vrLastBalance=0,g_vrLastEquity=0;
datetime g_vrLastDate=0;
bool g_vrSampled=false,g_vrCandidatePending=false;
int g_vrFeatureIndex=-1,g_vrPostOrders=0;
bool g_vrCandidateKnown=false,g_vrCandidateBlocked=false;
long g_vrCandidateMsc=0;
datetime g_vrSignalBar=0;
double g_vrOpen=0,g_vrHigh=0,g_vrLow=0,g_vrSignalClose=0;

void VwapReplayError(string message)
{
   g_vrErrors++;
   Print("VWAP REPLAY ERROR: ",message);
}

int VwapReplayOpen(string suffix)
{
   int handle=FileOpen("vwap_"+g_runTag+"_"+suffix+".csv",FILE_WRITE|FILE_CSV|FILE_COMMON,'\t');
   if(handle==INVALID_HANDLE) VwapReplayError("cannot open "+suffix);
   return handle;
}

bool VwapReplayInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || _Period!=PERIOD_M30 || MathAbs(Lots-1.0)>1e-9 ||
      MathAbs(SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE)-0.25)>1e-9 ||
      MathAbs(SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE)/SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE)-2.0)>1e-9)
   { VwapReplayError("tester/M30/one-lot/MNQ-value guard failed"); return false; }
   int h=FileOpen(VwapReplayFeatures,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(h==INVALID_HANDLE) { VwapReplayError("feature input unavailable"); return false; }
   string headers[7]={"available_epoch","session_epoch","bar_epoch","close","vwap","a20","known"};
   for(int j=0;j<7;j++)
      if(FileReadString(h)!=headers[j]) { FileClose(h); VwapReplayError("feature header differs"); return false; }
   while(!FileIsEnding(h))
   {
      datetime available=(datetime)FileReadNumber(h);
      if(available==0 && FileIsEnding(h)) break;
      datetime session=(datetime)FileReadNumber(h),bar=(datetime)FileReadNumber(h);
      double close=FileReadNumber(h),vwap=FileReadNumber(h),a20=FileReadNumber(h);
      bool known=(FileReadNumber(h)==1);
      if(available!=bar+1800 || session!=bar-bar%86400 ||
         (g_vrCount>0 && available<=g_vrAvailable[g_vrCount-1]) ||
         !MathIsValidNumber(close) || close<=0 ||
         (known && (!MathIsValidNumber(vwap) || !MathIsValidNumber(a20) || vwap<=0 || a20<=0)))
      { FileClose(h); VwapReplayError("invalid feature input row"); return false; }
      int n=g_vrCount+1;
      ArrayResize(g_vrAvailable,n,20000); ArrayResize(g_vrSession,n,20000); ArrayResize(g_vrBar,n,20000);
      ArrayResize(g_vrClose,n,20000); ArrayResize(g_vrVwap,n,20000); ArrayResize(g_vrA20,n,20000);
      ArrayResize(g_vrKnown,n,20000);
      g_vrAvailable[g_vrCount]=available; g_vrSession[g_vrCount]=session; g_vrBar[g_vrCount]=bar;
      g_vrClose[g_vrCount]=close; g_vrVwap[g_vrCount]=vwap; g_vrA20[g_vrCount]=a20; g_vrKnown[g_vrCount]=known;
      g_vrCount=n;
   }
   FileClose(h);
   if(g_vrCount==0) { VwapReplayError("empty features"); return false; }
   g_vrCandidateFile=VwapReplayOpen("candidates");
   g_vrEquityFile=FileOpen("vwap_"+g_runTag+"_equity.bin",FILE_WRITE|FILE_BIN|FILE_COMMON);
   if(g_vrCandidateFile==INVALID_HANDLE || g_vrEquityFile==INVALID_HANDLE)
   { VwapReplayError("output open failed"); return false; }
   FileWrite(g_vrCandidateFile,"candidate_id","time","time_msc","signal_bar","signal_open","signal_high","signal_low","signal_close",
             "feature_available","feature_session","feature_bar","feature_close","vwap","a20","z","known","blocked","gate_enabled",
             "post_maintenance_orders","order","retcode","send_success");
   return true;
}

void VwapReplaySampleEquity(bool force=false)
{
   if(g_vrEquityFile==INVALID_HANDLE) return;
   long msc=PathNowMsc();
   datetime date=(datetime)(msc/1000); date-=date%86400;
   double balance=AccountInfoDouble(ACCOUNT_BALANCE),equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!MathIsValidNumber(balance) || !MathIsValidNumber(equity)) { VwapReplayError("invalid equity"); return; }
   if(g_vrSampled && msc<g_vrLastMsc) { VwapReplayError("equity time reversed"); return; }
   if(!force && g_vrSampled && balance==g_vrLastBalance && equity==g_vrLastEquity && date==g_vrLastDate) return;
   FileWriteLong(g_vrEquityFile,msc); FileWriteDouble(g_vrEquityFile,balance); FileWriteDouble(g_vrEquityFile,equity);
   g_vrEquityRows++; g_vrSampled=true; g_vrLastMsc=msc;
   g_vrLastBalance=balance; g_vrLastEquity=equity; g_vrLastDate=date;
}

void VwapReplayLogCandidate(ulong order,uint retcode,bool sent)
{
   if(!g_vrCandidatePending) { VwapReplayError("candidate result without candidate"); return; }
   int j=g_vrFeatureIndex;
   FileWrite(g_vrCandidateFile,g_vrCandidates,PathTime(g_vrCandidateMsc),g_vrCandidateMsc,PathBar(g_vrSignalBar),
             DoubleToString(g_vrOpen,8),DoubleToString(g_vrHigh,8),DoubleToString(g_vrLow,8),DoubleToString(g_vrSignalClose,8),
             (j>=0 ? PathBar(g_vrAvailable[j]) : ""),(j>=0 ? PathBar(g_vrSession[j]) : ""),(j>=0 ? PathBar(g_vrBar[j]) : ""),
             (j>=0 ? DoubleToString(g_vrClose[j],16) : ""),
             (g_vrCandidateKnown ? DoubleToString(g_vrVwap[j],16) : ""),
             (g_vrCandidateKnown ? DoubleToString(g_vrA20[j],16) : ""),
             (g_vrCandidateKnown ? DoubleToString((g_vrSignalClose-g_vrVwap[j])/g_vrA20[j],16) : ""),
             (int)g_vrCandidateKnown,(int)g_vrCandidateBlocked,(int)UseVwapReplayGate,g_vrPostOrders,(long)order,retcode,(int)sent);
   g_vrCandidatePending=false;
}

bool VwapReplayCandidate(double o,double h,double l,double c)
{
   if(g_vrCandidatePending) VwapReplayError("unfinished prior candidate");
   g_vrCandidates++; g_vrCandidatePending=true;
   g_vrCandidateMsc=PathNowMsc(); g_vrSignalBar=iTime(_Symbol,_Period,1);
   g_vrOpen=o; g_vrHigh=h; g_vrLow=l; g_vrSignalClose=c; g_vrPostOrders=OrdersTotal();
   datetime now=TimeCurrent(),date=now-now%86400;
   int left=0,right=g_vrCount-1,j=-1;
   while(left<=right)
   {
      int mid=(left+right)/2;
      if(g_vrAvailable[mid]<=now) { j=mid; left=mid+1; } else right=mid-1;
   }
   g_vrFeatureIndex=j;
   g_vrCandidateKnown=(j>=0 && g_vrKnown[j] && g_vrSession[j]==date);
   if(g_vrCandidateKnown && (g_vrBar[j]!=g_vrSignalBar || MathAbs(g_vrClose[j]-c)>1e-8))
   { VwapReplayError("source and tester signal bar differ"); ExpertRemove(); return false; }
   bool unfavorable=g_vrCandidateKnown && c<g_vrVwap[j]-g_vrA20[j];
   g_vrCandidateBlocked=UseVwapReplayGate && unfavorable;
   if(g_vrCandidateBlocked) { g_vrBlocked++; VwapReplayLogCandidate(0,0,false); return false; }
   return true;
}

void VwapReplayFinish()
{
   VwapReplaySampleEquity(true);
   if(g_vrCandidatePending) VwapReplayError("candidate unfinished at end");
   int orders=VwapReplayOpen("orders"),deals=VwapReplayOpen("deals"),summary=VwapReplayOpen("summary");
   if(orders==INVALID_HANDLE || deals==INVALID_HANDLE || summary==INVALID_HANDLE) return;
   FileWrite(orders,"order","symbol","type","state","setup_msc","done_msc","position_id","volume_initial","volume_current","price_open","sl","tp","price_current","reason","comment");
   FileWrite(deals,"deal","order","position_id","symbol","type","entry","time_msc","volume","price","profit","commission","swap","fee","reason","comment");
   if(!HistorySelect(0,TimeCurrent())) VwapReplayError("complete history unavailable");
   int no=HistoryOrdersTotal(),nd=HistoryDealsTotal();
   for(int i=0;i<no;i++)
   {
      ulong id=HistoryOrderGetTicket(i);
      FileWrite(orders,(long)id,HistoryOrderGetString(id,ORDER_SYMBOL),HistoryOrderGetInteger(id,ORDER_TYPE),HistoryOrderGetInteger(id,ORDER_STATE),
                HistoryOrderGetInteger(id,ORDER_TIME_SETUP_MSC),HistoryOrderGetInteger(id,ORDER_TIME_DONE_MSC),HistoryOrderGetInteger(id,ORDER_POSITION_ID),
                DoubleToString(HistoryOrderGetDouble(id,ORDER_VOLUME_INITIAL),8),DoubleToString(HistoryOrderGetDouble(id,ORDER_VOLUME_CURRENT),8),
                DoubleToString(HistoryOrderGetDouble(id,ORDER_PRICE_OPEN),8),DoubleToString(HistoryOrderGetDouble(id,ORDER_SL),8),DoubleToString(HistoryOrderGetDouble(id,ORDER_TP),8),
                DoubleToString(HistoryOrderGetDouble(id,ORDER_PRICE_CURRENT),8),HistoryOrderGetInteger(id,ORDER_REASON),HistoryOrderGetString(id,ORDER_COMMENT));
   }
   for(int i=0;i<nd;i++)
   {
      ulong id=HistoryDealGetTicket(i);
      FileWrite(deals,(long)id,HistoryDealGetInteger(id,DEAL_ORDER),HistoryDealGetInteger(id,DEAL_POSITION_ID),HistoryDealGetString(id,DEAL_SYMBOL),
                HistoryDealGetInteger(id,DEAL_TYPE),HistoryDealGetInteger(id,DEAL_ENTRY),HistoryDealGetInteger(id,DEAL_TIME_MSC),
                DoubleToString(HistoryDealGetDouble(id,DEAL_VOLUME),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PRICE),8),DoubleToString(HistoryDealGetDouble(id,DEAL_PROFIT),8),
                DoubleToString(HistoryDealGetDouble(id,DEAL_COMMISSION),8),DoubleToString(HistoryDealGetDouble(id,DEAL_SWAP),8),DoubleToString(HistoryDealGetDouble(id,DEAL_FEE),8),
                HistoryDealGetInteger(id,DEAL_REASON),HistoryDealGetString(id,DEAL_COMMENT));
   }
   FileWrite(summary,"run_tag","gate_enabled","features","candidates","blocked","observer_errors","equity_rows","history_orders","history_deals");
   FileWrite(summary,g_runTag,(int)UseVwapReplayGate,g_vrCount,g_vrCandidates,g_vrBlocked,g_vrErrors,g_vrEquityRows,no,nd);
   FileClose(orders); FileClose(deals); FileClose(summary);
   FileClose(g_vrCandidateFile); FileClose(g_vrEquityFile);
   g_vrCandidateFile=INVALID_HANDLE; g_vrEquityFile=INVALID_HANDLE;
}

#endif
