//+------------------------------------------------------------------+
//| Red-Green Breakout EA: dual RR exits + no-trading window          |
//+------------------------------------------------------------------+
#property strict

input double Lots            = 1.0;
input double RiskReward1     = 1.0;
input double RiskReward2     = 2.0;
input int    Slippage        = 5;
input long   Magic1          = 10001;

// flattening
input bool   UseFlatten      = true;
input int    FlattenHour     = 23;
input int    FlattenMinute   = 30;

// no-trading window (block new trades between these times)
input bool   UseNoTradeWindow   = true;
input int    NoTradeStartHour   = 23;
input int    NoTradeStartMinute = 30;
input int    NoTradeEndHour     = 1;
input int    NoTradeEndMinute   = 0;

//--------------------- Helpers ------------------------------------//
bool IsFlattenTime(datetime barOpen)
{
   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   return (dt.hour == FlattenHour && dt.min == FlattenMinute);
}

bool InNoTradeWindow(datetime barOpen)
{
   if(!UseNoTradeWindow) return false;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);

   int curMinutes = dt.hour * 60 + dt.min;
   int startMins  = NoTradeStartHour * 60 + NoTradeStartMinute;
   int endMins    = NoTradeEndHour   * 60 + NoTradeEndMinute;

   if(startMins <= endMins)
   {
      // same-day window
      return (curMinutes >= startMins && curMinutes < endMins);
   }
   else
   {
      // window crosses midnight
      return (curMinutes >= startMins || curMinutes < endMins);
   }
}

void CancelAllOrders()
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(!OrderSelect(ticket)) continue;

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action = TRADE_ACTION_REMOVE;
      req.order  = ticket;

      if(!OrderSend(req, res))
         Print("❌ CancelAllOrders failed ticket=", ticket, " err=", GetLastError());
      else
         Print("✅ Cancelled order ticket=", ticket);
   }
}

void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; --i)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;

      string sym = PositionGetString(POSITION_SYMBOL);
      double vol = PositionGetDouble(POSITION_VOLUME);
      long   typ = PositionGetInteger(POSITION_TYPE);

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action    = TRADE_ACTION_DEAL;
      req.symbol    = sym;
      req.volume    = vol;
      req.deviation = Slippage;
      req.type  = (typ == POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY);
	  req.price = (typ == POSITION_TYPE_BUY ?
             SymbolInfoDouble(sym, SYMBOL_BID) :
             SymbolInfoDouble(sym, SYMBOL_ASK));


      if(!OrderSend(req, res))
         Print("❌ CloseAllPositions failed pos#", ticket, " err=", GetLastError());
      else
         Print("✅ Closed position #", ticket);
   }
}

void CancelOldBuyStops()
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(!OrderSelect(ticket)) continue;

      int type = (int)OrderGetInteger(ORDER_TYPE);
      if(type != ORDER_TYPE_BUY_STOP) continue;

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action = TRADE_ACTION_REMOVE;
      req.order  = ticket;

      if(!OrderSend(req, res))
         Print("❌ Failed to cancel BuyStop ticket=", ticket, " err=", GetLastError());
      else
         Print("✅ Cancelled BuyStop ticket=", ticket);
   }
}

bool SafeClosePosition(double volume)
{
   if(!PositionSelect(_Symbol)) return false;

   double posVol = PositionGetDouble(POSITION_VOLUME);
   if(posVol <= 0) return false;

   double closeVol = MathMin(volume, posVol);

   long type = PositionGetInteger(POSITION_TYPE);

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = _Symbol;
   req.volume    = closeVol;
   req.deviation = Slippage;

   if(type == POSITION_TYPE_BUY)
   {
      req.type  = ORDER_TYPE_SELL;
      req.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   }
   else
   {
      req.type  = ORDER_TYPE_BUY;
      req.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   }

   if(!OrderSend(req, res))
   {
      Print("❌ SafeClose failed vol=", closeVol, " err=", GetLastError());
      return false;
   }

   Print("✅ SafeClose executed vol=", closeVol);
   return true;
}


//--------------------- Trade Management ----------------------------//
void ManageOpenPositions()
{
   static bool rr1_done = false;
   static datetime last_pos_time = 0;

   if(!PositionSelect(_Symbol)) return;

   datetime t = (datetime)PositionGetInteger(POSITION_TIME);
   if(t != last_pos_time)
   {
      rr1_done = false;
      last_pos_time = t;
      Print("🔄 New position detected — reset RR state");
   }

   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl    = PositionGetDouble(POSITION_SL);
   double vol   = PositionGetDouble(POSITION_VOLUME);

   if(vol <= 0) return;

   double risk = entry - sl;
   if(risk <= 0) return;

   double barClose = iClose(_Symbol, _Period, 1);

   // --- RR1: partial close (HALF OF CURRENT, NOT Lots)
   if(!rr1_done && barClose >= entry + risk * RiskReward1)
   {
      double half = vol / 2.0;

      if(SafeClosePosition(half))
      {
         rr1_done = true;
         Print("✅ RR1 reached → partial close ", half);
      }
   }

   // --- RR2: final exit (CLOSE REMAINDER)
   if(rr1_done && barClose >= entry + risk * RiskReward2)
   {
      if(SafeClosePosition(DBL_MAX))
         Print("✅ RR2 reached → final close");
   }
}



//--------------------- Order Placement -----------------------------//
void PlaceBuyStop(double entry, double stop)
{
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   req.action       = TRADE_ACTION_PENDING;
   req.symbol       = _Symbol;
   req.volume       = Lots * 2.0;   // total size
   req.type         = ORDER_TYPE_BUY_STOP;
   req.price        = entry;
   req.sl           = stop;
   req.deviation    = Slippage;
   req.type_filling = ORDER_FILLING_RETURN;
   req.magic        = Magic1;       // magic irrelevant in netting

   if(!OrderSend(req, res))
      Print("❌ Place BuyStop fail err=", GetLastError());
   else
      Print("🚀 BuyStop placed @", entry, " SL=", stop);
}

//--------------------- EA Core ------------------------------------//
int OnInit() { return(INIT_SUCCEEDED); }

void OnTick()
{
   static datetime lastBar = 0;
   datetime barOpen = iTime(_Symbol, _Period, 0);

   if(barOpen == lastBar) return;
   lastBar = barOpen;

   // Flatten cutoff
   if(UseFlatten && IsFlattenTime(barOpen))
   {
      Print("🌙 Flatten cutoff reached → closing everything");
      CloseAllPositions();
      CancelAllOrders();
      return;
   }

   // No-trading window (force flat + block trades)
   if(InNoTradeWindow(barOpen))
   {
      Print("🚫 In no-trading window → flat only, no new trades");
      CloseAllPositions();
      CancelAllOrders();
      return;
   }

   // Manage open positions
   if(PositionsTotal() > 0)
   {
      ManageOpenPositions();
      return;
   }

   // Red candle setup (only if not in no-trading window)
   double o1 = iOpen(_Symbol, _Period, 1);
   double h1 = iHigh(_Symbol, _Period, 1);
   double l1 = iLow(_Symbol, _Period, 1);
   double c1 = iClose(_Symbol, _Period, 1);

   if(c1 < o1)
   {
      Print("🔴 Red candle → refresh BuyStop");
      CancelOldBuyStops();
      if(h1 - l1 <= 0) return;
      PlaceBuyStop(h1, l1);
   }
}
