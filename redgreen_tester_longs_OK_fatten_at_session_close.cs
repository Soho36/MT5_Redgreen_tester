//+------------------------------------------------------------------+
//| Red-Green Breakout EA: dynamic exit + optional flatten cutoff    |
//+------------------------------------------------------------------+
#property strict

input double Lots         = 1.0;
input double RiskReward   = 1.0;   // close on bar close when >= 1R
input int    Slippage     = 5;

// flattening switch
input bool   UseFlatten   = true;  // if false → no flattening
input int    FlattenHour  = 2;     
input int    FlattenMinute= 30;

//--------------------- Helpers ------------------------------------//
bool IsFlattenTime(datetime barOpen)
{
   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   return (dt.hour == FlattenHour && dt.min == FlattenMinute);
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

      if(typ == POSITION_TYPE_BUY)
      {
         req.type  = ORDER_TYPE_SELL;
         req.price = SymbolInfoDouble(sym, SYMBOL_BID);
      }
      else
      {
         req.type  = ORDER_TYPE_BUY;
         req.price = SymbolInfoDouble(sym, SYMBOL_ASK);
      }

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

void ManageOpenPosition()
{
   if(!PositionSelect(_Symbol)) return;

   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl    = PositionGetDouble(POSITION_SL);
   double vol   = PositionGetDouble(POSITION_VOLUME);
   long   typ   = PositionGetInteger(POSITION_TYPE);

   // This EA only opens longs; safety check:
   if(typ != POSITION_TYPE_BUY) return;

   double risk = entry - sl;
   if(risk <= 0.0) return;

   // just-closed bar close
   double barClose = iClose(_Symbol, _Period, 1);

   if(barClose >= entry + risk * RiskReward)
   {
      Print("✅ ≥ ", RiskReward, "R at bar close → closing at market");

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action    = TRADE_ACTION_DEAL;
      req.symbol    = _Symbol;
      req.volume    = vol;
      req.type      = ORDER_TYPE_SELL;                         // close buy
      req.price     = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      req.deviation = Slippage;

      if(!OrderSend(req, res))
         Print("❌ Close fail err=", GetLastError());
      else
         Print("✅ Position closed");
   }
   else
   {
      Print("⏳ Not yet ", RiskReward, "R on close → hold");
   }
}

//--------------------- EA Core ------------------------------------//
int OnInit() { return(INIT_SUCCEEDED); }

void OnTick()
{
   static datetime lastBar = 0;
   datetime barOpen = iTime(_Symbol, _Period, 0);

   // run only once per bar
   if(barOpen == lastBar) return;
   lastBar = barOpen;

   // 1) Optional flattening
   if(UseFlatten && IsFlattenTime(barOpen))
   {
      Print("🌙 Flatten cutoff reached (", FlattenHour, ":", FlattenMinute, ") → closing everything");
      CloseAllPositions();
      CancelAllOrders();
      return;
   }

   // 2) If we have a position, manage dynamic exit
   if(PositionsTotal() > 0)
   {
      ManageOpenPosition();
      return;
   }

   // 3) No position: check red-candle setup
   double o1 = iOpen(_Symbol, _Period, 1);
   double h1 = iHigh(_Symbol, _Period, 1);
   double l1 = iLow(_Symbol, _Period, 1);
   double c1 = iClose(_Symbol, _Period, 1);

   Print("Bar[1] O=", o1, " H=", h1, " L=", l1, " C=", c1);

   if(c1 < o1) // red candle
   {
      Print("🔴 Red candle → refresh BuyStop");
      CancelOldBuyStops();

      double entry = h1;
      double stop  = l1;
      double risk  = entry - stop;
      if(risk <= 0.0) return;

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action       = TRADE_ACTION_PENDING;
      req.symbol       = _Symbol;
      req.volume       = Lots;
      req.type         = ORDER_TYPE_BUY_STOP;
      req.price        = entry;
      req.sl           = stop;
      req.deviation    = Slippage;
      req.type_filling = ORDER_FILLING_RETURN;

      if(!OrderSend(req, res))
         Print("❌ Place BuyStop fail err=", GetLastError());
      else
         Print("🚀 BuyStop placed @", entry, " SL=", stop);
   }
}