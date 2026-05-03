//+------------------------------------------------------------------+
//| Green-Red Breakout EA (SHORT ONLY): dynamic exit + no-trade win   |
//+------------------------------------------------------------------+
#property strict

input double Lots           = 1.0;
input double RiskReward     = 1.0;
input int    Slippage       = 5;

// flattening during session
input bool   UseFlattenDur     = true;
input int    FlattenHourDur    = 14;
input int    FlattenMinuteDur  = 00;

// flattening end session
input bool   UseFlattenEnd     = true;
input int    FlattenHourEnd    = 20;
input int    FlattenMinuteEnd  = 00;

// ======== TIME WINDOW FILTERING ========
// no-trading window (block new trades between these times)
input bool   UseTradeWindow   = true;
input bool W0000W0030 = false;  // 00:00–00:30
input bool W0030W0100 = false;  // 00:30–01:00
input bool W0100W0130 = false;  // 01:00–01:30
input bool W0130W0200 = false;  // 01:30–02:00
input bool W0200W0230 = false;  // 02:00–02:30
input bool W0230W0300 = false;  // 02:30–03:00
input bool W0300W0330 = false;  // 03:00–03:30
input bool W0330W0400 = false;  // 03:30–04:00
input bool W0400W0430 = false;  // 04:00–04:30
input bool W0430W0500 = false;  // 04:30–05:00
input bool W0500W0530 = false;  // 05:00–05:30
input bool W0530W0600 = false;  // 05:30–06:00
input bool W0600W0630 = false;  // 06:00–06:30
input bool W0630W0700 = false;  // 06:30–07:00
input bool W0700W0730 = false;  // 07:00–07:30
input bool W0730W0800 = false;  // 07:30–08:00
input bool W0800W0830 = false;  // 08:00–08:30
input bool W0830W0900 = false;  // 08:30–09:00
input bool W0900W0930 = false;  // 09:00–09:30
input bool W0930W1000 = false;  // 09:30–10:00
input bool W1000W1030 = false;  // 10:00–10:30
input bool W1030W1100 = false;  // 10:30–11:00
input bool W1100W1130 = false;  // 11:00–11:30
input bool W1130W1200 = false;  // 11:30–12:00
input bool W1200W1230 = false;  // 12:00–12:30
input bool W1230W1300 = false;  // 12:30–13:00
input bool W1300W1330 = false;  // 13:00–13:30
input bool W1330W1400 = false;  // 13:30–14:00
input bool W1400W1430 = false;  // 14:00–14:30
input bool W1430W1500 = false;  // 14:30–15:00
input bool W1500W1530 = false;  // 15:00–15:30
input bool W1530W1600 = false;  // 15:30–16:00
input bool W1600W1630 = false;  // 16:00–16:30
input bool W1630W1700 = false;  // 16:30–17:00
input bool W1700W1730 = false;  // 17:00–17:30
input bool W1730W1800 = false;  // 17:30–18:00
input bool W1800W1830 = false;  // 18:00–18:30
input bool W1830W1900 = false;  // 18:30–19:00
input bool W1900W1930 = false;  // 19:00–19:30
input bool W1930W2000 = false;  // 19:30–20:00
input bool W2000W2030 = false;  // 20:00–20:30
input bool W2030W2100 = false;  // 20:30–21:00
input bool W2100W2130 = false;  // 21:00–21:30
input bool W2130W2200 = false;  // 21:30–22:00
input bool W2200W2230 = false;  // 22:00–22:30
input bool W2230W2300 = false;  // 22:30–23:00
input bool W2300W2330 = false;  // 23:00–23:30
input bool W2330W0000 = false;  // 23:30–00:00

bool windows[48] =
{
   W0000W0030, W0030W0100, W0100W0130, W0130W0200, W0200W0230, W0230W0300,
   W0300W0330, W0330W0400, W0400W0430, W0430W0500, W0500W0530, W0530W0600,
   W0600W0630, W0630W0700, W0700W0730, W0730W0800, W0800W0830, W0830W0900,
   W0900W0930, W0930W1000, W1000W1030, W1030W1100, W1100W1130, W1130W1200,
   W1200W1230, W1230W1300, W1300W1330, W1330W1400, W1400W1430, W1430W1500,
   W1500W1530, W1530W1600, W1600W1630, W1630W1700, W1700W1730, W1730W1800,
   W1800W1830, W1830W1900, W1900W1930, W1930W2000, W2000W2030, W2030W2100,
   W2100W2130, W2130W2200, W2200W2230, W2230W2300, W2300W2330, W2330W0000
};

//---------------- Helpers ----------------//
bool IsFlattenTimeDur(datetime t){MqlDateTime d;TimeToStruct(t,d);return d.hour==FlattenHourDur && d.min==FlattenMinuteDur;}
bool IsFlattenTimeEnd(datetime t){MqlDateTime d;TimeToStruct(t,d);return d.hour==FlattenHourEnd && d.min==FlattenMinuteEnd;}

bool IsTradeWindow(datetime t)
{
   if(!UseTradeWindow) return true;
   MqlDateTime d; TimeToStruct(t,d);
   return windows[(d.hour*60+d.min)/30];
}

void CancelAllOrders()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong tk=OrderGetTicket(i); if(!OrderSelect(tk)) continue;
      MqlTradeRequest r={}; MqlTradeResult s={};
      r.action=TRADE_ACTION_REMOVE; r.order=tk;
      if(!OrderSend(r,s)) Print("❌ Cancel order fail ",tk);
      else Print("✅ Pending order cancelled ",tk);
   }
}

void CloseAllPositions()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i); if(!PositionSelectByTicket(tk)) continue;
      string sym=PositionGetString(POSITION_SYMBOL);
      double vol=PositionGetDouble(POSITION_VOLUME);
      long typ=PositionGetInteger(POSITION_TYPE);

      MqlTradeRequest r={}; MqlTradeResult s={};
      r.action=TRADE_ACTION_DEAL; r.symbol=sym; r.volume=vol; r.deviation=Slippage;
      r.type = (typ==POSITION_TYPE_SELL ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
      r.price= (typ==POSITION_TYPE_SELL ? SymbolInfoDouble(sym,SYMBOL_ASK)
                                        : SymbolInfoDouble(sym,SYMBOL_BID));

      if(!OrderSend(r,s)) Print("❌ Close pos fail ",tk);
      else Print("✅ Position closed ",tk);
   }
}

void CancelOldSellStops()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong tk=OrderGetTicket(i); if(!OrderSelect(tk)) continue;
      if(OrderGetInteger(ORDER_TYPE)!=ORDER_TYPE_SELL_STOP) continue;

      MqlTradeRequest r={}; MqlTradeResult s={};
      r.action=TRADE_ACTION_REMOVE; r.order=tk;
      if(!OrderSend(r,s)) Print("❌ Failed cancel SellStop ",tk);
      else Print("✅ SellStop cancelled ",tk);
   }
}

void ManageOpenPosition()
{
   if(!PositionSelect(_Symbol)) return;
   if(PositionGetInteger(POSITION_TYPE)!=POSITION_TYPE_SELL) return;

   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double sl=PositionGetDouble(POSITION_SL);
   double vol=PositionGetDouble(POSITION_VOLUME);

   double risk = sl - entry;
   if(risk<=0) return;

   double close1=iClose(_Symbol,_Period,1);

   if(close1 <= entry - risk*RiskReward)
   {
      Print("✅ ≥ ",RiskReward,"R on close → exit SHORT");

      MqlTradeRequest r={}; MqlTradeResult s={};
      r.action=TRADE_ACTION_DEAL;
      r.symbol=_Symbol;
      r.volume=vol;
      r.type=ORDER_TYPE_BUY;
      r.price=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      r.deviation=Slippage;

      if(!OrderSend(r,s)) Print("❌ Exit fail");
      else Print("✅ SHORT closed");
   }
   else
      Print("⏳ RR not reached → hold SHORT");
}

//---------------- EA Core ----------------//
int OnInit(){return INIT_SUCCEEDED;}

void OnTick()
{
   static datetime lastBar=0;
   datetime bar=iTime(_Symbol,_Period,0);
   if(bar==lastBar) return;
   lastBar=bar;

   if(UseFlattenDur && IsFlattenTimeDur(bar))
   {
      Print("⛔ DUR flatten → clear all");
      CloseAllPositions(); CancelAllOrders(); return;
   }

   if(UseFlattenEnd && IsFlattenTimeEnd(bar))
   {
      Print("🌙 END flatten → clear all");
      CloseAllPositions(); CancelAllOrders(); return;
   }

   if(PositionsTotal()>0){ManageOpenPosition(); return;}

   if(!IsTradeWindow(bar))
   {
      Print("⏱ No-trade window → cancel SellStops");
      CancelOldSellStops(); return;
   }

   double o=iOpen(_Symbol,_Period,1);
   double h=iHigh(_Symbol,_Period,1);
   double l=iLow(_Symbol,_Period,1);
   double c=iClose(_Symbol,_Period,1);

   if(c > o) // GREEN candle
   {
      Print("🟢 Green candle → refresh SellStop");
      CancelOldSellStops();

      double entry=l;
      double stop=h;
      double risk=stop-entry;
      if(risk<=0) return;

      MqlTradeRequest r={}; MqlTradeResult s={};
      r.action=TRADE_ACTION_PENDING;
      r.symbol=_Symbol;
      r.volume=Lots;
      r.type=ORDER_TYPE_SELL_STOP;
      r.price=entry;
      r.sl=stop;
      r.deviation=Slippage;
      r.type_filling=ORDER_FILLING_RETURN;

      if(!OrderSend(r,s)) Print("❌ SellStop place fail");
      else Print("🚀 SellStop placed @",entry," SL=",stop);
   }
}
