//+------------------------------------------------------------------+
//| Red-Green Breakout EA: dynamic exit + time + month + weekday filters |
//+------------------------------------------------------------------+
#property strict

input double Lots           = 1.0;
input double RiskReward     = 1.0;
input int    Slippage       = 5;

// ======== CANDLE RANGE FILTER ========
input bool   UseCandleRangeFilter = false;  // Enable/disable candle range filter
input double MaxCandleRange       = 50.0;   // Maximum allowed candle range in points
input double MinCandleRange       = 5.0;    // Minimum allowed candle range in points

// ======== WEEKDAY FILTERING OPTIONS ========
enum WEEKDAY_FILTER_MODE
{
   WEEKDAY_DISABLED,       // No weekday filtering
   WEEKDAY_INDIVIDUAL,     // Select individual weekdays
   WEEKDAY_GROUPED         // Select weekday groups
};

input WEEKDAY_FILTER_MODE WeekdayFilterMode = WEEKDAY_DISABLED;  // Weekday filtering mode

// Individual weekdays selection
input bool TradeMonday     = true;  // Monday
input bool TradeTuesday    = true;  // Tuesday
input bool TradeWednesday  = true;  // Wednesday
input bool TradeThursday   = true;  // Thursday
input bool TradeFriday     = true;  // Friday
input bool TradeSaturday   = true;  // Saturday
input bool TradeSunday     = true;  // Sunday

// Weekday groups for trading patterns
input bool TradeWeekdays   = true;  // Mon-Fri
input bool TradeWeekend    = false; // Sat-Sun

// ======== MONTH FILTERING OPTIONS ========
enum MONTH_FILTER_MODE
{
   MONTH_DISABLED,       // No month filtering
   MONTH_INDIVIDUAL,     // Select individual months
   MONTH_GROUPED         // Select month groups
};

input MONTH_FILTER_MODE MonthFilterMode = MONTH_DISABLED;  // Month filtering mode

// Individual months selection
input bool TradeJanuary    = true;  // January
input bool TradeFebruary   = true;  // February
input bool TradeMarch      = true;  // March
input bool TradeApril      = true;  // April
input bool TradeMay        = true;  // May
input bool TradeJune       = true;  // June
input bool TradeJuly       = true;  // July
input bool TradeAugust     = true;  // August
input bool TradeSeptember  = true;  // September
input bool TradeOctober    = true;  // October
input bool TradeNovember   = true;  // November
input bool TradeDecember   = true;  // December

// Month groups for seasonal trading
input bool TradeWinter     = true;  // Dec, Jan, Feb
input bool TradeSpring     = true;  // Mar, Apr, May
input bool TradeSummer     = true;  // Jun, Jul, Aug
input bool TradeAutumn     = true;  // Sep, Oct, Nov

// ======== SESSION FILTERING ========
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

// ======== MAE / MFE (FLOATING PNL BASED) ========
double g_maeMoney   = 0.0;   // most negative floating PnL
double g_mfeMoney   = 0.0;   // most positive floating PnL
bool   g_tracking   = false;
ulong  g_ticket     = 0;

datetime g_entryTime = 0;
string   g_csvName   = "trade_stats.csv";

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

bool IsCandleInRange(double high, double low)
{
   if(!UseCandleRangeFilter)
      return true;
   
   // Calculate candle range in points
   double rangePoints = (high - low) / _Point;
   
   // Check if range is within allowed limits
   if(rangePoints > MaxCandleRange)
   {
      Print("⚠️ Candle range filter: Range ", DoubleToString(rangePoints, 2), " points > Max ", DoubleToString(MaxCandleRange, 2), " points - Skipping");
      return false;
   }
   
   if(rangePoints < MinCandleRange)
   {
      Print("⚠️ Candle range filter: Range ", DoubleToString(rangePoints, 2), " points < Min ", DoubleToString(MinCandleRange, 2), " points - Skipping");
      return false;
   }
   
   return true;
}

bool IsWeekdayAllowed(datetime barOpen)
{
   if(WeekdayFilterMode == WEEKDAY_DISABLED)
      return true;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   int weekday = dt.day_of_week;  // 0-6, where 0=Sunday, 1=Monday, ..., 6=Saturday

   // Individual weekday selection
   if(WeekdayFilterMode == WEEKDAY_INDIVIDUAL)
   {
      switch(weekday)
      {
         case 1:  return TradeMonday;     // Monday
         case 2:  return TradeTuesday;    // Tuesday
         case 3:  return TradeWednesday;  // Wednesday
         case 4:  return TradeThursday;   // Thursday
         case 5:  return TradeFriday;     // Friday
         case 6:  return TradeSaturday;   // Saturday
         case 0:  return TradeSunday;     // Sunday
      }
   }
   // Weekday group selection
   else if(WeekdayFilterMode == WEEKDAY_GROUPED)
   {
      // Weekdays: Monday-Friday (1-5)
      if(weekday >= 1 && weekday <= 5)
         return TradeWeekdays;
      // Weekend: Saturday-Sunday (6, 0)
      else if(weekday == 6 || weekday == 0)
         return TradeWeekend;
   }

   return false;  // Should never reach here
}

string GetWeekdayName(int weekday)
{
   switch(weekday)
   {
      case 1:  return "Monday";
      case 2:  return "Tuesday";
      case 3:  return "Wednesday";
      case 4:  return "Thursday";
      case 5:  return "Friday";
      case 6:  return "Saturday";
      case 0:  return "Sunday";
   }
   return "Unknown";
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

// ======== CSV FUNCTIONS ========
void SaveTradeStats(double realized, datetime entryTime, datetime exitTime)
{
   int f = FileOpen(g_csvName, FILE_READ|FILE_WRITE|FILE_CSV|FILE_SHARE_WRITE);
   if(f == INVALID_HANDLE)
   {
      Print("File open failed ", GetLastError());
      return;
   }

   if(FileSize(f) == 0)
      FileWrite(f, "ticket", "entry_time", "exit_time", "mae_money", "mfe_money", "trade_profit");

   FileSeek(f, 0, SEEK_END);
   FileWrite(
      f,
      (long)g_ticket,
      TimeToString(entryTime, TIME_DATE|TIME_SECONDS),
      TimeToString(exitTime, TIME_DATE|TIME_SECONDS),
      g_maeMoney,
      g_mfeMoney,
      realized
   );

   FileClose(f);
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

   // Display candle range filter settings
   Print("Candle Range Filter: ", UseCandleRangeFilter ? "ENABLED" : "DISABLED");
   if(UseCandleRangeFilter)
   {
      Print("  Max Candle Range: ", MaxCandleRange, " points");
      Print("  Min Candle Range: ", MinCandleRange, " points");
   }

   // Display weekday settings
   if(WeekdayFilterMode == WEEKDAY_DISABLED)
      Print("Weekday Filtering: DISABLED");
   else if(WeekdayFilterMode == WEEKDAY_INDIVIDUAL)
   {
      Print("Weekday Filtering: INDIVIDUAL WEEKDAYS");
      Print("Mon:", TradeMonday, " Tue:", TradeTuesday, " Wed:", TradeWednesday,
            " Thu:", TradeThursday, " Fri:", TradeFriday);
      Print("Sat:", TradeSaturday, " Sun:", TradeSunday);
   }
   else if(WeekdayFilterMode == WEEKDAY_GROUPED)
   {
      Print("Weekday Filtering: WEEKDAY GROUPS");
      Print("Weekdays (Mon-Fri): ", TradeWeekdays);
      Print("Weekend (Sat-Sun): ", TradeWeekend);
   }

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
   // Delete previous stats file if exists
   if(FileIsExist(g_csvName))
   {
      if(FileDelete(g_csvName))
         Print("Old trade_stats.csv deleted");
      else
         Print("Failed to delete old CSV. Error=", GetLastError());
   }

   DisplaySettings();
   return(INIT_SUCCEEDED);
}


void OnTick()
{
   // ---- TRACK FLOATING MAE / MFE (tick-based, broker-safe) ----
   if(PositionSelect(_Symbol))
   {
      double floating = PositionGetDouble(POSITION_PROFIT);

      if(!g_tracking)
      {
         g_tracking  = true;
         g_ticket    = PositionGetInteger(POSITION_TICKET);
         g_entryTime = (datetime)PositionGetInteger(POSITION_TIME);
         g_maeMoney  = floating;
         g_mfeMoney  = floating;

         Print("Tracking started ticket=", g_ticket);
      }

      // 🔹 update excursions
      g_maeMoney = MathMin(g_maeMoney, floating);
      g_mfeMoney = MathMax(g_mfeMoney, floating);
   }
   else if(g_tracking)
   {
      // --- include final realized PnL into MAE/MFE ---
      double realized = 0.0;
      
      // --- include datetime ---
      datetime exitTime = 0;

      if(HistorySelect(g_entryTime - 86400, TimeCurrent()))
      {
         for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
         {
            ulong deal = HistoryDealGetTicket(i);

            if(HistoryDealGetInteger(deal, DEAL_POSITION_ID) != g_ticket)
               continue;

            double profit = HistoryDealGetDouble(deal, DEAL_PROFIT);
            realized += profit;

            if(HistoryDealGetInteger(deal, DEAL_ENTRY) == DEAL_ENTRY_OUT)
            {
               exitTime = (datetime)HistoryDealGetInteger(deal, DEAL_TIME);
               break; // ← exit deal found, stop
            }
         }
      }

      // realized PnL IS the last excursion
      g_maeMoney = MathMin(g_maeMoney, realized);
      g_mfeMoney = MathMax(g_mfeMoney, realized);

      SaveTradeStats(realized, g_entryTime, exitTime);

      g_tracking = false;
   }

   static datetime lastBar = 0;
   datetime barOpen = iTime(_Symbol, _Period, 0);

   if(barOpen == lastBar) return;
   lastBar = barOpen;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   string monthName = GetMonthName(dt.mon);
   string weekdayName = GetWeekdayName(dt.day_of_week);

   // 🔹 Weekday filtering check
   if(WeekdayFilterMode != WEEKDAY_DISABLED && !IsWeekdayAllowed(barOpen))
   {
      Print("📅 Weekday Filter: ", weekdayName, " not allowed for trading");
      if(PositionsTotal() == 0)
         CancelOldBuyStops();
      return;
   }

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

   // 🔹 Candle range filter check
   if(!IsCandleInRange(h1, l1))
   {
      Print("⚠️ Candle range outside allowed limits - Skipping signal");
      CancelOldBuyStops();
      return;
   }

   if(c1 < o1)
   {
      Print("🔴 Red candle on ", weekdayName, " in ", monthName, " → refresh BuyStop");
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
         Print("🚀 BuyStop placed @", entry, " SL=", stop, " (", weekdayName, ", ", monthName, ")");
   }
}