//+------------------------------------------------------------------+
//| Green-Red Breakdown EA: Shorts only, dynamic exit + EOD flatten |
//+------------------------------------------------------------------+
#property strict

input double Lots       = 1.0;
input double RiskReward = 1.0;
input int    Slippage   = 5;

//--------------------- Helpers ------------------------------------//
bool IsEndOfDay(datetime barOpen)
{
   int sec = PeriodSeconds(_Period);
   if(sec <= 0 || sec >= 86400) return false;

   int bar_minutes      = sec / 60;
   int last_start_min   = 1440 - bar_minutes;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   int curr_start_min   = dt.hour * 60 + dt.min;

   return (curr_start_min == last_start_min);
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

      if(typ == POSITION_TYPE_SELL)
      {
         req.type  = ORDER_TYPE_BUY;
         req.price = SymbolInfoDouble(sym, SYMBOL_ASK);
      }
      else
      {
         req.type  = ORDER_TYPE_SELL;
         req.price = SymbolInfoDouble(sym, SYMBOL_BID);
      }

      if(!OrderSend(req, res))
         Print("❌ CloseAllPositions failed pos#", ticket, " err=", GetLastError());
      else
         Print("✅ Closed position #", ticket);
   }
}

void CancelOldSellStops()
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(!OrderSelect(ticket)) continue;

      int type = (int)OrderGetInteger(ORDER_TYPE);
      if(type != ORDER_TYPE_SELL_STOP) continue;

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action = TRADE_ACTION_REMOVE;
      req.order  = ticket;

      if(!OrderSend(req, res))
         Print("❌ Failed to cancel SellStop ticket=", ticket, " err=", GetLastError());
      else
         Print("✅ Cancelled SellStop ticket=", ticket);
   }
}

void ManageOpenPosition()
{
   if(!PositionSelect(_Symbol)) return;

   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl    = PositionGetDouble(POSITION_SL);
   double vol   = PositionGetDouble(POSITION_VOLUME);
   long   typ   = PositionGetInteger(POSITION_TYPE);

   // This EA only opens shorts
   if(typ != POSITION_TYPE_SELL) return;

   double risk = sl - entry;
   if(risk <= 0.0) return;

   double barClose = iClose(_Symbol, _Period, 1);

   if(barClose <= entry - risk * RiskReward)
   {
      Print("✅ ≥ ", RiskReward, "R at bar close → closing short at market");

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action    = TRADE_ACTION_DEAL;
      req.symbol    = _Symbol;
      req.volume    = vol;
      req.type      = ORDER_TYPE_BUY;                          // close sell
      req.price     = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      req.deviation = Slippage;

      if(!OrderSend(req, res))
         Print("❌ Close fail err=", GetLastError());
      else
         Print("✅ Short position closed");
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

   if(barOpen == lastBar) return;
   lastBar = barOpen;

   if(IsEndOfDay(barOpen))
   {
      Print("🌙 EOD last bar → flatten everything");
      CloseAllPositions();
      CancelAllOrders();
      return;
   }

   if(PositionsTotal() > 0)
   {
      ManageOpenPosition();
      return;
   }

   double o1 = iOpen(_Symbol, _Period, 1);
   double h1 = iHigh(_Symbol, _Period, 1);
   double l1 = iLow(_Symbol, _Period, 1);
   double c1 = iClose(_Symbol, _Period, 1);

   Print("Bar[1] O=", o1, " H=", h1, " L=", l1, " C=", c1);

   if(c1 > o1) // green candle
   {
      Print("🟢 Green candle → refresh SellStop");
      CancelOldSellStops();

      double entry = l1;
      double stop  = h1;
      double risk  = stop - entry;
      if(risk <= 0.0) return;

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action       = TRADE_ACTION_PENDING;
      req.symbol       = _Symbol;
      req.volume       = Lots;
      req.type         = ORDER_TYPE_SELL_STOP;
      req.price        = entry;
      req.sl           = stop;
      req.deviation    = Slippage;
      req.type_filling = ORDER_FILLING_RETURN;

      if(!OrderSend(req, res))
         Print("❌ Place SellStop fail err=", GetLastError());
      else
         Print("🚀 SellStop placed @", entry, " SL=", stop);
   }
}
