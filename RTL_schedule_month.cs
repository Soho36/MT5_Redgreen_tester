//+------------------------------------------------------------------+
//| Red-Green Breakout EA: dynamic exit + time + month filters       |
//+------------------------------------------------------------------+
#property strict

input double Lots           = 1.0;
input double RiskReward     = 1.0;
input int    Slippage       = 5;

// ======== MONTH FILTERING OPTIONS ========
enum MONTH_FILTER_MODE
{
   MONTH_DISABLED,       // No month filtering
   MONTH_INDIVIDUAL,     // Select individual months
   MONTH_GROUPED         // Select month groups
};

input MONTH_FILTER_MODE MonthFilterMode = MONTH_DISABLED;  // Month filtering mode

// Individual months selection
input bool TradeJanuary    = false;  // January
input bool TradeFebruary   = true;  // February
input bool TradeMarch      = false;  // March
input bool TradeApril      = false;  // April
input bool TradeMay        = false;  // May
input bool TradeJune       = false;  // June
input bool TradeJuly       = false;  // July
input bool TradeAugust     = false;  // August
input bool TradeSeptember  = false;  // September
input bool TradeOctober    = false;  // October
input bool TradeNovember   = false;  // November
input bool TradeDecember   = false;  // December

// Month groups for seasonal trading
input bool TradeWinter     = false;  // Dec, Jan, Feb
input bool TradeSpring     = false;  // Mar, Apr, May
input bool TradeSummer     = false;  // Jun, Jul, Aug
input bool TradeAutumn     = false;  // Sep, Oct, Nov

// ======== SESSION FILTERING ========
// flattening during session
input bool   UseFlattenDur     = false;
input int    FlattenHourDur    = 14;
input int    FlattenMinuteDur  = 00;

// flattening end session
input bool   UseFlattenEnd     = true;
input int    FlattenHourEnd    = 23;
input int    FlattenMinuteEnd  = 30;

// ======== TIME WINDOW FILTERING ========
// no-trading window (block new trades between these times)
input bool   UseTradeWindow   = true;
input bool W00 = false;  // 00:00–00:30
input bool W01 = false;  // 00:30–01:00
input bool W02 = false;  // 01:00–01:30
input bool W03 = false;  // 01:30–02:00
input bool W04 = false;  // 02:00–02:30
input bool W05 = false;  // 02:30–03:00
input bool W06 = false;  // 03:00–03:30
input bool W07 = false;  // 03:30–04:00
input bool W08 = false;  // 04:00–04:30
input bool W09 = false;  // 04:30–05:00
input bool W10 = false;  // 05:00–05:30
input bool W11 = false;  // 05:30–06:00
input bool W12 = false;  // 06:00–06:30
input bool W13 = false;  // 06:30–07:00
input bool W14 = false;  // 07:00–07:30
input bool W15 = false;  // 07:30–08:00
input bool W16 = false;  // 08:00–08:30
input bool W17 = false;  // 08:30–09:00
input bool W18 = false;  // 09:00–09:30
input bool W19 = false;  // 09:30–10:00
input bool W20 = false;  // 10:00–10:30
input bool W21 = false;  // 10:30–11:00
input bool W22 = false;  // 11:00–11:30
input bool W23 = false;  // 11:30–12:00
input bool W24 = false;  // 12:00–12:30
input bool W25 = false;  // 12:30–13:00
input bool W26 = false;  // 13:00–13:30
input bool W27 = false;  // 13:30–14:00
input bool W28 = false;  // 14:00–14:30
input bool W29 = false;  // 14:30–15:00
input bool W30 = false;  // 15:00–15:30
input bool W31 = false;  // 15:30–16:00
input bool W32 = false;  // 16:00–16:30
input bool W33 = false;  // 16:30–17:00
input bool W34 = false;  // 17:00–17:30
input bool W35 = false;  // 17:30–18:00
input bool W36 = false;  // 18:00–18:30
input bool W37 = false;  // 18:30–19:00
input bool W38 = false;  // 19:00–19:30
input bool W39 = false;  // 19:30–20:00
input bool W40 = false;  // 20:00–20:30
input bool W41 = false;  // 20:30–21:00
input bool W42 = false;  // 21:00–21:30
input bool W43 = false;  // 21:30–22:00
input bool W44 = false;  // 22:00–22:30
input bool W45 = false;  // 22:30–23:00
input bool W46 = false;  // 23:00–23:30
input bool W47 = false;  // 23:30–00:00

bool windows[48] =
{
   W00, W01, W02, W03, W04, W05,
   W06, W07, W08, W09, W10, W11,
   W12, W13, W14, W15, W16, W17,
   W18, W19, W20, W21, W22, W23,
   W24, W25, W26, W27, W28, W29,
   W30, W31, W32, W33, W34, W35,
   W36, W37, W38, W39, W40, W41,
   W42, W43, W44, W45, W46, W47
};

// ======== HELPER FUNCTIONS ========
bool IsFlattenTimeDur(datetime barOpen)
{
   MqlDateTime dt; TimeToStruct(barOpen, dt);
   return (dt.hour == FlattenHourDur && dt.min == FlattenMinuteDur);
}

bool IsFlattenTimeEnd(datetime barOpen)
{
   MqlDateTime dt; TimeToStruct(barOpen, dt);
   return (dt.hour == FlattenHourEnd && dt.min == FlattenMinuteEnd);
}

bool IsTradeWindow(datetime barOpen)
{
   if(!UseTradeWindow)
      return true;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);

   int slot = (dt.hour * 60 + dt.min) / 30;
   return windows[slot];
}

bool IsMonthAllowed(datetime barOpen)
{
   if(MonthFilterMode == MONTH_DISABLED)
      return true;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   int month = dt.mon;  // 1-12

   // Individual month selection
   if(MonthFilterMode == MONTH_INDIVIDUAL)
   {
      switch(month)
      {
         case 1:  return TradeJanuary;
         case 2:  return TradeFebruary;
         case 3:  return TradeMarch;
         case 4:  return TradeApril;
         case 5:  return TradeMay;
         case 6:  return TradeJune;
         case 7:  return TradeJuly;
         case 8:  return TradeAugust;
         case 9:  return TradeSeptember;
         case 10: return TradeOctober;
         case 11: return TradeNovember;
         case 12: return TradeDecember;
      }
   }
   // Month group selection
   else if(MonthFilterMode == MONTH_GROUPED)
   {
      // Winter: Dec, Jan, Feb
      if(month == 12 || month == 1 || month == 2)
         return TradeWinter;
      // Spring: Mar, Apr, May
      else if(month >= 3 && month <= 5)
         return TradeSpring;
      // Summer: Jun, Jul, Aug
      else if(month >= 6 && month <= 8)
         return TradeSummer;
      // Autumn: Sep, Oct, Nov
      else if(month >= 9 && month <= 11)
         return TradeAutumn;
   }

   return false;  // Should never reach here
}

string GetMonthName(int month)
{
   switch(month)
   {
      case 1:  return "January";
      case 2:  return "February";
      case 3:  return "March";
      case 4:  return "April";
      case 5:  return "May";
      case 6:  return "June";
      case 7:  return "July";
      case 8:  return "August";
      case 9:  return "September";
      case 10: return "October";
      case 11: return "November";
      case 12: return "December";
   }
   return "Unknown";
}

// ======== TRADE MANAGEMENT FUNCTIONS ========
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

// ======== DISPLAY CURRENT SETTINGS ========
void DisplaySettings()
{
   Print("=== EA Settings ===");
   Print("Lots: ", Lots, ", RiskReward: ", RiskReward);

   // Display month settings
   if(MonthFilterMode == MONTH_DISABLED)
      Print("Month Filtering: DISABLED");
   else if(MonthFilterMode == MONTH_INDIVIDUAL)
   {
      Print("Month Filtering: INDIVIDUAL MONTHS");
      Print("Jan:", TradeJanuary, " Feb:", TradeFebruary, " Mar:", TradeMarch,
            " Apr:", TradeApril, " May:", TradeMay, " Jun:", TradeJune);
      Print("Jul:", TradeJuly, " Aug:", TradeAugust, " Sep:", TradeSeptember,
            " Oct:", TradeOctober, " Nov:", TradeNovember, " Dec:", TradeDecember);
   }
   else if(MonthFilterMode == MONTH_GROUPED)
   {
      Print("Month Filtering: SEASONAL GROUPS");
      Print("Winter (Dec-Jan-Feb): ", TradeWinter);
      Print("Spring (Mar-Apr-May): ", TradeSpring);
      Print("Summer (Jun-Jul-Aug): ", TradeSummer);
      Print("Autumn (Sep-Oct-Nov): ", TradeAutumn);
   }

   // Display time window settings
   Print("Time Window Filtering: ", UseTradeWindow ? "ENABLED" : "DISABLED");

   // Display flattening times
   Print("Flatten During: ", UseFlattenDur ? "Yes (" + (string)FlattenHourDur + ":" + (string)FlattenMinuteDur + ")" : "No");
   Print("Flatten End: ", UseFlattenEnd ? "Yes (" + (string)FlattenHourEnd + ":" + (string)FlattenMinuteEnd + ")" : "No");
}

// ======== EA CORE ========
int OnInit()
{
   DisplaySettings();
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   static datetime lastBar = 0;
   datetime barOpen = iTime(_Symbol, _Period, 0);

   if(barOpen == lastBar) return;
   lastBar = barOpen;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   string monthName = GetMonthName(dt.mon);

   // 🔹 Month filtering check
   if(MonthFilterMode != MONTH_DISABLED && !IsMonthAllowed(barOpen))
   {
      Print("📅 Month Filter: ", monthName, " not allowed for trading");
      if(PositionsTotal() == 0)
         CancelOldBuyStops();
      return;
   }

   // 🔹 flatten during session
   if(UseFlattenDur && IsFlattenTimeDur(barOpen))
   {
      Print("Flatten cutoff reached DURING SESSION → closing everything");
      CloseAllPositions();
      CancelAllOrders();
      return;
   }

   // 🔹 flatten end of session
   if(UseFlattenEnd && IsFlattenTimeEnd(barOpen))
   {
      Print("🌙 Flatten cutoff reached → closing everything");
      CloseAllPositions();
      CancelAllOrders();
      return;
   }

   // 🔹 manage existing position
   if(PositionsTotal() > 0)
   {
      ManageOpenPosition();
      return;
   }

   // 🔹 time window check (ENTRY ONLY)
   if(!IsTradeWindow(barOpen))
   {
      Print("⏱ Outside trading window → no new entries");
      CancelOldBuyStops();
      return;
   }

   // Red candle setup (only if all filters pass)
   double o1 = iOpen(_Symbol, _Period, 1);
   double h1 = iHigh(_Symbol, _Period, 1);
   double l1 = iLow(_Symbol, _Period, 1);
   double c1 = iClose(_Symbol, _Period, 1);

   if(c1 < o1)
   {
      Print("🔴 Red candle in ", monthName, " → refresh BuyStop");
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
         Print("🚀 BuyStop placed @", entry, " SL=", stop, " (Month: ", monthName, ")");
   }
}