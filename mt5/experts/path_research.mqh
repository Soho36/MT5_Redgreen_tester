// Passive tester-only path observer. No trade requests or original state writes.
// Include after the original EA's global declarations.
#ifndef PATH_RESEARCH_MQH
#define PATH_RESEARCH_MQH

struct PathResearchState
{
   bool active;
   ulong position_id, entry_order, entry_deal;
   long entry_time_msc, first_quote_time_msc, last_quote_msc, hit05_msc, hit1_msc;
   datetime hit05_bar, hit1_bar;
   double fill, requested_entry, sl, requested_risk, actual_risk;
   double entry_bid, min_bid, max_bid, min_before1, last_quote_bid;
   int quote_samples;
};
PathResearchState g_pr;
int g_prTrades = INVALID_HANDLE, g_prBars = INVALID_HANDLE;
int g_prChecks = INVALID_HANDLE, g_prOrders = INVALID_HANDLE, g_prSummary = INVALID_HANDLE;
int g_prErrors = 0, g_prExported = 0;
long g_prMaxEntryLagMsc = 0;
double g_prProfit = 0.0;
datetime g_prLastBar = 0;
bool g_prReady = false;

void PathResearchError(string text)
{
   g_prErrors++;
   Print("PATH OBSERVER ERROR: ", text);
}

string PathTime(long time_msc)
{
   if(time_msc == 0) return "";
   return TimeToString((datetime)(time_msc / 1000), TIME_DATE|TIME_SECONDS);
}

string PathBar(datetime bar)
{
   return (bar == 0 ? "" : TimeToString(bar, TIME_DATE|TIME_SECONDS));
}

long PathNowMsc()
{
   MqlTick tick;
   if(SymbolInfoTick(_Symbol, tick)) return tick.time_msc;
   return (long)TimeCurrent() * 1000;
}

int PathOpen(string suffix)
{
   string name = "path_" + g_runTag + "_" + suffix + ".csv";
   int handle = FileOpen(name, FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_WRITE, '\t');
   if(handle == INVALID_HANDLE) PathResearchError("cannot open " + name);
   return handle;
}

void PathResearchInit()
{
   ZeroMemory(g_pr);
   g_prTrades = PathOpen("trades"); g_prBars = PathOpen("bars");
   g_prChecks = PathOpen("checks"); g_prOrders = PathOpen("orders");
   g_prSummary = PathOpen("summary");
   g_prReady = (g_prTrades != INVALID_HANDLE && g_prBars != INVALID_HANDLE &&
                g_prChecks != INVALID_HANDLE && g_prOrders != INVALID_HANDLE && g_prSummary != INVALID_HANDLE);
   if(!g_prReady) return;
   FileWrite(g_prTrades,"position_id","entry_order","entry_deal","exit_deal",
             "entry_time","exit_time","entry_time_msc","exit_time_msc","first_quote_time_msc",
             "actual_fill","requested_entry","initial_sl","requested_risk","actual_risk",
             "entry_bid","min_bid","max_bid","mae_R","mfe_R",
             "first_hit_05_msc","first_hit_05_bar","first_hit_1_msc","first_hit_1_bar",
             "max_mae_before_first_hit_1R","exit_price","exit_reason","trade_profit","quote_samples");
   FileWrite(g_prBars,"closed_bar_open","closed_close","eval_time_msc","eval_time",
             "current_position_id","locked_entry","locked_risk","locked_set","bid","ask");
   FileWrite(g_prChecks,"position_id","check_time_msc","check_time","closed_bar_open","closed_close",
             "locked_entry","locked_risk","locked_set","target","condition",
             "actual_fill","actual_risk","requested_risk","bid","ask");
   FileWrite(g_prOrders,"order","result_deal","retcode","arm_time_msc","arm_time",
             "signal_bar_open","signal_open","signal_high","signal_low","signal_close",
             "requested_entry","initial_sl","signal_mode","order_type","bid","ask");
   FileWrite(g_prSummary,"run_tag","exported_positions","history_entries","history_exits",
             "tester_trades","exported_profit","history_profit","tester_profit",
             "observer_errors","active_at_end","counts_match","profit_match","max_entry_lag_msc");
}

void PathResearchPrice(double bid, long time_msc, datetime bar, bool quote)
{
   if(!g_pr.active || !MathIsValidNumber(bid) || bid <= 0) return;
   if(time_msc < g_pr.entry_time_msc)
   {
      PathResearchError("sample before entry for " + (string)g_pr.position_id);
      return;
   }
   if(quote && time_msc == g_pr.last_quote_msc && bid == g_pr.last_quote_bid) return;
   g_pr.min_bid = MathMin(g_pr.min_bid,bid);
   g_pr.max_bid = MathMax(g_pr.max_bid,bid);
   if(g_pr.hit1_msc == 0) g_pr.min_before1 = MathMin(g_pr.min_before1,bid);
   if(g_pr.hit05_msc == 0 && bid >= g_pr.fill + 0.5 * g_pr.actual_risk)
   {
      g_pr.hit05_msc = time_msc; g_pr.hit05_bar = bar;
   }
   if(g_pr.hit1_msc == 0 && bid >= g_pr.fill + g_pr.actual_risk)
   {
      g_pr.hit1_msc = time_msc; g_pr.hit1_bar = bar;
   }
   if(quote)
   {
      g_pr.quote_samples++;
      g_pr.last_quote_msc = time_msc; g_pr.last_quote_bid = bid;
   }
}

bool PathResearchStart(ulong identifier, const MqlTick &tick)
{
   if(!HistorySelectByPosition(identifier))
   {
      PathResearchError("entry history absent for " + (string)identifier);
      return false;
   }
   ulong entry_deal = 0;
   int entries = 0;
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(deal,DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
      if(HistoryDealGetInteger(deal,DEAL_TYPE) != DEAL_TYPE_BUY ||
         MathAbs(HistoryDealGetDouble(deal,DEAL_VOLUME)-1.0) > 1e-9)
      {
         PathResearchError("unsupported entry for " + (string)identifier);
         return false;
      }
      entry_deal=deal; entries++;
   }
   if(entries != 1)
   {
      PathResearchError("entry count differs from one for " + (string)identifier);
      return false;
   }
   ulong order=(ulong)HistoryDealGetInteger(entry_deal,DEAL_ORDER);
   double fill=HistoryDealGetDouble(entry_deal,DEAL_PRICE);
   long entry_msc=HistoryDealGetInteger(entry_deal,DEAL_TIME_MSC);
   long entry_lag=tick.time_msc-entry_msc;
   if(entry_lag > g_prMaxEntryLagMsc) g_prMaxEntryLagMsc=entry_lag;
   if(entry_lag != 0)
      PathResearchError("first quote differs from entry by " + (string)entry_lag + " ms for " + (string)identifier);
   if(!HistoryOrderSelect(order))
   {
      PathResearchError("original order absent for " + (string)identifier);
      return false;
   }
   double requested=HistoryOrderGetDouble(order,ORDER_PRICE_OPEN);
   double sl=HistoryOrderGetDouble(order,ORDER_SL);
   if(sl <= 0 || fill <= sl || requested <= sl)
   {
      PathResearchError("invalid original risk for " + (string)identifier);
      return false;
   }
   ZeroMemory(g_pr);
   g_pr.active=true; g_pr.position_id=identifier;
   g_pr.entry_deal=entry_deal; g_pr.entry_order=order; g_pr.entry_time_msc=entry_msc;
   g_pr.first_quote_time_msc=tick.time_msc;
   g_pr.fill=fill; g_pr.requested_entry=requested; g_pr.sl=sl;
   g_pr.requested_risk=requested-sl; g_pr.actual_risk=fill-sl;
   g_pr.entry_bid=tick.bid; g_pr.min_bid=tick.bid; g_pr.max_bid=tick.bid;
   g_pr.min_before1=tick.bid;
   PathResearchPrice(tick.bid,tick.time_msc,iTime(_Symbol,_Period,0),true);
   return true;
}

bool PathResearchFinish()
{
   if(!g_pr.active) return true;
   if(!HistorySelectByPosition(g_pr.position_id))
   {
      PathResearchError("close history absent for " + (string)g_pr.position_id);
      return false;
   }
   ulong exit_deal=0;
   int exits=0;
   double profit=0;
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong deal=HistoryDealGetTicket(i);
      profit += HistoryDealGetDouble(deal,DEAL_PROFIT);
      if(MathAbs(HistoryDealGetDouble(deal,DEAL_COMMISSION)) > 1e-9 ||
         MathAbs(HistoryDealGetDouble(deal,DEAL_SWAP)) > 1e-9 ||
         MathAbs(HistoryDealGetDouble(deal,DEAL_FEE)) > 1e-9)
         PathResearchError("unexpected deal fees for " + (string)g_pr.position_id);
      if(HistoryDealGetInteger(deal,DEAL_ENTRY) == DEAL_ENTRY_OUT)
      {
         if(HistoryDealGetInteger(deal,DEAL_TYPE) != DEAL_TYPE_SELL ||
            MathAbs(HistoryDealGetDouble(deal,DEAL_VOLUME)-1.0) > 1e-9)
         {
            PathResearchError("unsupported exit for " + (string)g_pr.position_id);
            return false;
         }
         exit_deal=deal; exits++;
      }
   }
   if(exits != 1)
   {
      PathResearchError("close count differs from one for " + (string)g_pr.position_id);
      return false;
   }
   long exit_msc=HistoryDealGetInteger(exit_deal,DEAL_TIME_MSC);
   double exit_price=HistoryDealGetDouble(exit_deal,DEAL_PRICE);
   long exit_reason=HistoryDealGetInteger(exit_deal,DEAL_REASON);
   if(exit_msc < g_pr.last_quote_msc)
      PathResearchError("observed quote after exit for " + (string)g_pr.position_id);
   // The closing fill is authoritative; do not add a current quote after closure.
   PathResearchPrice(exit_price,exit_msc,(datetime)((exit_msc/1000)/1800*1800),false);
   double mae=MathMax(0.0,(g_pr.fill-g_pr.min_bid)/g_pr.actual_risk);
   double mfe=MathMax(0.0,(g_pr.max_bid-g_pr.fill)/g_pr.actual_risk);
   double pre1=MathMax(0.0,(g_pr.fill-g_pr.min_before1)/g_pr.actual_risk);
   FileWrite(g_prTrades,(long)g_pr.position_id,(long)g_pr.entry_order,(long)g_pr.entry_deal,(long)exit_deal,
             PathTime(g_pr.entry_time_msc),PathTime(exit_msc),g_pr.entry_time_msc,exit_msc,g_pr.first_quote_time_msc,
             DoubleToString(g_pr.fill,8),DoubleToString(g_pr.requested_entry,8),DoubleToString(g_pr.sl,8),
             DoubleToString(g_pr.requested_risk,8),DoubleToString(g_pr.actual_risk,8),
             DoubleToString(g_pr.entry_bid,8),DoubleToString(g_pr.min_bid,8),DoubleToString(g_pr.max_bid,8),
             DoubleToString(mae,10),DoubleToString(mfe,10),g_pr.hit05_msc,PathBar(g_pr.hit05_bar),
             g_pr.hit1_msc,PathBar(g_pr.hit1_bar),DoubleToString(pre1,10),DoubleToString(exit_price,8),
             exit_reason,DoubleToString(profit,8),g_pr.quote_samples);
   g_prExported++; g_prProfit+=profit;
   ZeroMemory(g_pr);
   return true;
}

void PathResearchObserve()
{
   if(!g_prReady) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
   {
      PathResearchError("current quote unavailable");
      return;
   }
   bool present=PositionSelect(_Symbol);
   ulong identifier=present ? (ulong)PositionGetInteger(POSITION_IDENTIFIER) : 0;
   if(g_pr.active && (!present || identifier != g_pr.position_id))
      if(!PathResearchFinish()) return;
   if(!present) return;
   if(PositionGetInteger(POSITION_TYPE) != POSITION_TYPE_BUY ||
      MathAbs(PositionGetDouble(POSITION_VOLUME)-1.0) > 1e-9)
   {
      PathResearchError("unsupported current position");
      return;
   }
   if(!g_pr.active)
   {
      PathResearchStart(identifier,tick);
      return;
   }
   PathResearchPrice(tick.bid,tick.time_msc,iTime(_Symbol,_Period,0),true);
}

void PathResearchBeforeTick()
{
   if(!g_prReady) return;
   PathResearchObserve();
   datetime bar=iTime(_Symbol,_Period,0);
   if(bar == g_prLastBar) return;
   g_prLastBar=bar;
   MqlTick tick; SymbolInfoTick(_Symbol,tick);
   ulong identifier=PositionSelect(_Symbol) ? (ulong)PositionGetInteger(POSITION_IDENTIFIER) : 0;
   FileWrite(g_prBars,PathBar(iTime(_Symbol,_Period,1)),DoubleToString(iClose(_Symbol,_Period,1),8),
             tick.time_msc,PathTime(tick.time_msc),(long)identifier,
             DoubleToString(g_initialEntry,8),DoubleToString(g_initialRisk,8),(int)g_initialSet,
             DoubleToString(tick.bid,8),DoubleToString(tick.ask,8));
}

void PathResearchAfterTick()
{
   PathResearchObserve();
}

void PathResearchTargetCheck(double bar_close,double target)
{
   if(!g_prReady) return;
   PathResearchObserve();
   MqlTick tick; SymbolInfoTick(_Symbol,tick);
   ulong identifier=PositionSelect(_Symbol) ? (ulong)PositionGetInteger(POSITION_IDENTIFIER) : 0;
   FileWrite(g_prChecks,(long)identifier,tick.time_msc,PathTime(tick.time_msc),
             PathBar(iTime(_Symbol,_Period,1)),DoubleToString(bar_close,8),
             DoubleToString(g_initialEntry,8),DoubleToString(g_initialRisk,8),(int)g_initialSet,
             DoubleToString(target,8),(int)(bar_close>=target),
             DoubleToString(g_pr.active ? g_pr.fill : 0.0,8),
             DoubleToString(g_pr.active ? g_pr.actual_risk : 0.0,8),
             DoubleToString(g_pr.active ? g_pr.requested_risk : 0.0,8),
             DoubleToString(tick.bid,8),DoubleToString(tick.ask,8));
}

void PathResearchEntryOrder(const MqlTradeRequest &req,const MqlTradeResult &res)
{
   if(!g_prReady) return;
   MqlTick tick; SymbolInfoTick(_Symbol,tick);
   FileWrite(g_prOrders,(long)res.order,(long)res.deal,res.retcode,tick.time_msc,PathTime(tick.time_msc),
             PathBar(iTime(_Symbol,_Period,1)),DoubleToString(iOpen(_Symbol,_Period,1),8),
             DoubleToString(iHigh(_Symbol,_Period,1),8),DoubleToString(iLow(_Symbol,_Period,1),8),
             DoubleToString(iClose(_Symbol,_Period,1),8),DoubleToString(req.price,8),DoubleToString(req.sl,8),
             SignalMode,(int)req.type,DoubleToString(tick.bid,8),DoubleToString(tick.ask,8));
   PathResearchObserve();
}

void PathResearchFinishTester()
{
   if(!g_prReady) return;
   PathResearchObserve();
   if(g_pr.active && !PositionSelect(_Symbol)) PathResearchFinish();
   int entries=0,exits=0;
   double profit=0;
   if(!HistorySelect(0,TimeCurrent())) PathResearchError("final complete history unavailable");
   else for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong deal=HistoryDealGetTicket(i);
      if(HistoryDealGetString(deal,DEAL_SYMBOL) != _Symbol) continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      long type=HistoryDealGetInteger(deal,DEAL_TYPE);
      if(type==DEAL_TYPE_BUY && entry==DEAL_ENTRY_IN) entries++;
      if(type==DEAL_TYPE_SELL && entry==DEAL_ENTRY_OUT) exits++;
      profit+=HistoryDealGetDouble(deal,DEAL_PROFIT);
   }
   int tester_trades=(int)TesterStatistics(STAT_TRADES);
   double tester_profit=TesterStatistics(STAT_PROFIT);
   bool counts=(g_prExported==entries && entries==exits && exits==tester_trades);
   bool profits=(MathAbs(g_prProfit-profit)<=1e-6 && MathAbs(profit-tester_profit)<=1e-6);
   if(!counts) PathResearchError("complete position count does not reconcile");
   if(!profits) PathResearchError("complete position profit does not reconcile");
   if(g_pr.active) PathResearchError("observer still active at tester end");
   FileWrite(g_prSummary,g_runTag,g_prExported,entries,exits,tester_trades,
             DoubleToString(g_prProfit,8),DoubleToString(profit,8),DoubleToString(tester_profit,8),
             g_prErrors,(int)g_pr.active,(int)counts,(int)profits,g_prMaxEntryLagMsc);
   FileClose(g_prTrades); FileClose(g_prBars); FileClose(g_prChecks);
   FileClose(g_prOrders); FileClose(g_prSummary);
   g_prReady=false;
}

#endif
