// Standalone pullback entry: at most one buy limit, no initial buy-stop fill.
input bool LimitOnly = true;
input double LimitOffsetPercent = 90.0; // high - percent * (high-low)
input bool WaitForHigh = true;          // archive behaviour: observe high first
double g_limitSignalHigh=0, g_limitSignalLow=0, g_limitOrderPrice=0;
datetime g_limitSignalTime=0, g_limitBreakoutTime=0;
bool g_limitArmed=false, g_limitAttempted=false;
int g_limitSetups=0, g_limitTriggers=0, g_limitsPlaced=0;
int g_limitsSkipped=0, g_limitsRejected=0, g_limitCancelErrors=0;

void ResetLimitSetup()
{
   g_limitArmed=false;
   g_limitAttempted=false;
   g_limitSignalHigh=0;
   g_limitSignalLow=0;
   g_limitOrderPrice=0;
   g_limitSignalTime=0;
   g_limitBreakoutTime=0;
}

void CancelLimitPending()
{
   for(int i=OrdersTotal()-1; i>=0; i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0 || OrderGetString(ORDER_SYMBOL)!=_Symbol || OrderGetInteger(ORDER_TYPE)!=ORDER_TYPE_BUY_LIMIT) continue;
      MqlTradeRequest req={}; MqlTradeResult res={};
      req.action=TRADE_ACTION_REMOVE; req.order=ticket;
      if(!OrderSend(req,res) || res.retcode!=TRADE_RETCODE_DONE)
      {
         g_limitCancelErrors++;
         Print("LIMIT_ONLY_CANCEL_ERROR ",res.retcode);
      }
   }
}

void ProcessLimitSetup()
{
   if(!LimitOnly || !g_limitArmed || g_limitAttempted || PositionSelect(_Symbol)) return;
   datetime bar=iTime(_Symbol,_Period,0);
   if(!IsTradeWindow(bar) || (UseFlattenEnd && IsAtOrAfterFlattenTime(bar))) return;
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   if(WaitForHigh && ask<g_limitSignalHigh) return;
   g_limitAttempted=true;
   if(WaitForHigh) { g_limitBreakoutTime=TimeCurrent(); g_limitTriggers++; }
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   double price=g_limitSignalHigh-(g_limitSignalHigh-g_limitSignalLow)*LimitOffsetPercent/100.0;
   price=NormalizeDouble(MathCeil(price/tick-1e-8)*tick,_Digits);
   price=MathMax(price,NormalizeDouble(g_limitSignalLow+tick,_Digits));
   g_limitOrderPrice=price;
   double gap=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if(price>=g_limitSignalHigh || price>=ask || ask-price<gap || price-g_limitSignalLow<gap)
   {
      g_limitsSkipped++;
      Print("LIMIT_ONLY_SKIP price=",price," ask=",ask);
      return;
   }
   MqlTradeRequest req={}; MqlTradeResult res={};
   req.action=TRADE_ACTION_PENDING;
   req.symbol=_Symbol;
   req.volume=Lots;
   req.type=ORDER_TYPE_BUY_LIMIT;
   req.price=price;
   req.sl=g_limitSignalLow;
   req.deviation=Slippage;
   req.type_filling=ORDER_FILLING_RETURN;
   req.comment="limit_only";
   if(!OrderSend(req,res) || (res.retcode!=TRADE_RETCODE_DONE && res.retcode!=TRADE_RETCODE_PLACED))
   {
      g_limitsRejected++;
      Print("LIMIT_ONLY_REJECT ",res.retcode);
      return;
   }
   g_limitsPlaced++;
}

void ArmLimitSetup(double high, double low)
{
   ResetLimitSetup();
   g_limitSignalHigh=high;
   g_limitSignalLow=low;
   g_limitSignalTime=iTime(_Symbol,_Period,1);
   g_limitArmed=true;
   g_limitSetups++;
   ProcessLimitSetup();
}
