//+------------------------------------------------------------------+
//| Red-Green Breakout EA: dynamic exit + time + month + weekday filters |
//| SHORT VERSION: Sells at low of green candle, SL above high       |
//+------------------------------------------------------------------+
#property strict

input double Lots           = 1.0;
input double RiskReward     = 1.0;
input int    Slippage       = 5;

// ======== Additional TP-limit order functionality ========
input bool UseScaleInLimit = true;		  	// USE SCALE-IN LIMIT

input bool   UseLimit1           = true;	// LIMIT1	
input double LimitOffsetPercent1 = 25.0;  	// Limit 1 offset % (0%=entry, 100%=SL)
input double LimitLots1          = 1.0;

input bool   UseLimit2           = false;	// LIMIT2
input double LimitOffsetPercent2 = 50.0;  	// Limit 2 offset %
input double LimitLots2          = 1.5;

input bool   UseLimit3           = false;	// LIMIT3
input double LimitOffsetPercent3 = 75.0;  	// Limit 3 offset %
input double LimitLots3          = 2.0;

input bool   UseLimit4           = false;	// LIMIT4
input double LimitOffsetPercent4 = 90.0;  	// Limit 4 offset %
input double LimitLots4          = 2.5;


// ======== CANDLE RANGE FILTER ========
input bool   UseCandleRangeFilter = false;  // ENABLE/DISABLE CANDLE RANGE FILTER
input double MaxCandleRange       = 50.0;   // Maximum allowed candle range in points
input double MinCandleRange       = 5.0;    // Minimum allowed candle range in points

// ======== WEEKDAY FILTERING OPTIONS ========
enum WEEKDAY_FILTER_MODE
{
   WEEKDAY_DISABLED,       // No weekday filtering
   WEEKDAY_INDIVIDUAL,     // Select individual weekdays
   WEEKDAY_GROUPED         // Select weekday groups
};

input WEEKDAY_FILTER_MODE WeekdayFilterMode = WEEKDAY_DISABLED;  // WEEKDAY FILTERING MODE

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

input MONTH_FILTER_MODE MonthFilterMode = MONTH_DISABLED;  // MONTH FILTERING MODE

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

// flattening end session
input bool   UseFlattenEnd     = true;	// USE FLATTENING END SESSION
input int    FlattenHourEnd    = 23;
input int    FlattenMinuteEnd  = 30;

// ======== TIME WINDOW FILTERING ========
// All intervals are 30 minutes. Total: 48 slots covering 00:00–24:00
input bool   UseTradeWindow   = true;	// USE TIME TRADE WINDOW

// ========== SESSION 1: MARKET CLOSED (00:00-01:00) ==========
input bool W0000W0030 = false;  // 00:00–00:30 (Market Closed)
input bool W0030W0100 = false;  // 00:30–01:00 (Market Closed)

// ========== SESSION 2: MORNING SESSION (01:00-10:00) ==========
input bool W0100W0130 = false;  // 01:00–01:30 (Morning Session)
input bool W0130W0200 = false;  // 01:30–02:00 (Morning Session)
input bool W0200W0230 = false;  // 02:00–02:30 (Morning Session)
input bool W0230W0300 = false;  // 02:30–03:00 (Morning Session)
input bool W0300W0330 = false;  // 03:00–03:30 (Morning Session)
input bool W0330W0400 = false;  // 03:30–04:00 (Morning Session)
input bool W0400W0430 = false;  // 04:00–04:30 (Morning Session)
input bool W0430W0500 = false;  // 04:30–05:00 (Morning Session)
input bool W0500W0530 = false;  // 05:00–05:30 (Morning Session)
input bool W0530W0600 = false;  // 05:30–06:00 (Morning Session)
input bool W0600W0630 = false;  // 06:00–06:30 (Morning Session)
input bool W0630W0700 = false;  // 06:30–07:00 (Morning Session)
input bool W0700W0730 = false;  // 07:00–07:30 (Morning Session)
input bool W0730W0800 = false;  // 07:30–08:00 (Morning Session)
input bool W0800W0830 = false;  // 08:00–08:30 (Morning Session)
input bool W0830W0900 = false;  // 08:30–09:00 (Morning Session)
input bool W0900W0930 = false;  // 09:00–09:30 (Morning Session)
input bool W0930W1000 = false;  // 09:30–10:00 (Morning Session)

// ========== SESSION 3: MAIN SESSION (10:00-23:00) ==========
input bool W1000W1030 = false;  // 10:00–10:30 (Main Session)
input bool W1030W1100 = false;  // 10:30–11:00 (Main Session)
input bool W1100W1130 = false;  // 11:00–11:30 (Main Session)
input bool W1130W1200 = false;  // 11:30–12:00 (Main Session)
input bool W1200W1230 = false;  // 12:00–12:30 (Main Session)
input bool W1230W1300 = false;  // 12:30–13:00 (Main Session)
input bool W1300W1330 = false;  // 13:00–13:30 (Main Session)
input bool W1330W1400 = false;  // 13:30–14:00 (Main Session)
input bool W1400W1430 = false;  // 14:00–14:30 (Main Session)
input bool W1430W1500 = false;  // 14:30–15:00 (Main Session)
input bool W1500W1530 = false;  // 15:00–15:30 (Main Session)
input bool W1530W1600 = false;  // 15:30–16:00 (Main Session)
input bool W1600W1630 = false;  // 16:00–16:30 (Main Session)
input bool W1630W1700 = false;  // 16:30–17:00 (Main Session)
input bool W1700W1730 = false;  // 17:00–17:30 (Main Session)
input bool W1730W1800 = false;  // 17:30–18:00 (Main Session)
input bool W1800W1830 = false;  // 18:00–18:30 (Main Session)
input bool W1830W1900 = false;  // 18:30–19:00 (Main Session)
input bool W1900W1930 = false;  // 19:00–19:30 (Main Session)
input bool W1930W2000 = false;  // 19:30–20:00 (Main Session)
input bool W2000W2030 = false;  // 20:00–20:30 (Main Session)
input bool W2030W2100 = false;  // 20:30–21:00 (Main Session)
input bool W2100W2130 = false;  // 21:00–21:30 (Main Session)
input bool W2130W2200 = false;  // 21:30–22:00 (Main Session)
input bool W2200W2230 = false;  // 22:00–22:30 (Main Session)
input bool W2230W2300 = false;  // 22:30–23:00 (Main Session)

// ========== SESSION 4: EVENING SESSION (23:00-00:00) ==========
input bool W2300W2330 = false;  // 23:00–23:30 (Evening Session)
input bool W2330W0000 = false;  // 23:30–00:00 (Evening Session)

bool windows[48] =  // Total slots: 2 + 18 + 26 + 2 = 48
{
   // ===== SESSION 1: MARKET CLOSED (00:00-01:00) ===== slots 0-1
   W0000W0030, W0030W0100,

   // ===== SESSION 2: MORNING SESSION (01:00-10:00) ===== slots 2-19
   W0100W0130, W0130W0200,
   W0200W0230, W0230W0300,
   W0300W0330, W0330W0400,
   W0400W0430, W0430W0500,
   W0500W0530, W0530W0600,
   W0600W0630, W0630W0700,
   W0700W0730, W0730W0800,
   W0800W0830, W0830W0900,
   W0900W0930, W0930W1000,

   // ===== SESSION 3: MAIN SESSION (10:00-23:00) ===== slots 20-45
   W1000W1030, W1030W1100,
   W1100W1130, W1130W1200,
   W1200W1230, W1230W1300,
   W1300W1330, W1330W1400,
   W1400W1430, W1430W1500,
   W1500W1530, W1530W1600,
   W1600W1630, W1630W1700,
   W1700W1730, W1730W1800,
   W1800W1830, W1830W1900,
   W1900W1930, W1930W2000,
   W2000W2030, W2030W2100,
   W2100W2130, W2130W2200,
   W2200W2230, W2230W2300,

   // ===== SESSION 4: EVENING SESSION (23:00-00:00) ===== slots 46-47
   W2300W2330, W2330W0000
};

// Session names for display purposes
string GetSessionName(int slot)
{
   if(slot <= 1)  return "MARKET CLOSED";
   if(slot <= 19) return "MORNING";
   if(slot <= 45) return "MAIN";
   if(slot <= 47) return "EVENING";
   return "UNKNOWN";
}

// Global variables
bool   g_limitPlacedAfterEntry = false;
double g_signalHigh = 0.0;
double g_signalLow  = 0.0;
bool g_wasInPosition = false;
double g_initialEntry = 0.0;
double g_initialRisk  = 0.0;
bool   g_initialSet   = false;

// ======== MAE / MFE (FLOATING PNL BASED) ========
double g_maeMoney   = 0.0;   // most negative floating PnL
double g_mfeMoney   = 0.0;   // most positive floating PnL
bool   g_tracking   = false;
ulong  g_ticket     = 0;
double g_candleRange = 0.0;

datetime g_entryTime = 0;
string   g_csvName   = "trade_stats.csv";

// ======== HELPER FUNCTIONS ========

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

   // Every slot is exactly 30 minutes wide.
   // slot = totalMinutes / 30  →  48 slots covering 00:00–24:00
   int totalMinutes = dt.hour * 60 + dt.min;
   int slot = totalMinutes / 30;

   if(slot < 0 || slot >= 48) return false;

   return windows[slot];
}

void DisplayTradeWindowStatus(datetime barOpen)
{
   if(!UseTradeWindow) return;
   
   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   
   int totalMinutes = dt.hour * 60 + dt.min;
   string sessionName = "";
   string borderLine = "";
   
   if(totalMinutes < 60)
   {
      sessionName = "MARKET CLOSED";
      borderLine = "═══════════════════════════════════════════════";
   }
   else if(totalMinutes >= 60 && totalMinutes < 600)
   {
      sessionName = "MORNING SESSION";
      if(totalMinutes == 60) // Start of morning session
         borderLine = "═══════════════ MORNING SESSION START ═══════════════";
   }
   else if(totalMinutes >= 600 && totalMinutes < 1380)
   {
      sessionName = "MAIN SESSION";
      if(totalMinutes == 600) // Start of main session
         borderLine = "════════════════ MAIN SESSION START ════════════════";
   }
   else
   {
      sessionName = "EVENING SESSION";
      if(totalMinutes == 1380) // Start of evening session
         borderLine = "═══════════════ EVENING SESSION START ═══════════════";
   }
   
   if(borderLine != "")
      Print(borderLine);
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
void SaveTradeStats(double realized, datetime entryTime, datetime exitTime, double candleRange)
{
   int f = FileOpen(g_csvName, FILE_READ|FILE_WRITE|FILE_CSV|FILE_SHARE_WRITE);
   if(f == INVALID_HANDLE)
   {
      Print("File open failed ", GetLastError());
      return;
   }

   if(FileSize(f) == 0)
      FileWrite(f, "ticket", "entry_time", "exit_time", "mae_money", "mfe_money", "trade_profit", "candle_range");

   FileSeek(f, 0, SEEK_END);
   FileWrite(
      f,
      (long)g_ticket,
      TimeToString(entryTime, TIME_DATE|TIME_SECONDS),
      TimeToString(exitTime, TIME_DATE|TIME_SECONDS),
      g_maeMoney,
      g_mfeMoney,
      realized,
      candleRange
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

void CancelAllSellLimits()
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(!OrderSelect(ticket)) continue;

      int type = (int)OrderGetInteger(ORDER_TYPE);
      if(type != ORDER_TYPE_SELL_LIMIT) continue;

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action = TRADE_ACTION_REMOVE;
      req.order  = ticket;

      if(!OrderSend(req, res))
         Print("❌ Failed to cancel SellLimit ticket=", ticket, " err=", GetLastError());
      else
         Print("🧹 Cancelled SellLimit ticket=", ticket);
   }
}

void ManageOpenPosition()
{
   if(!PositionSelect(_Symbol)) return;

   double vol = PositionGetDouble(POSITION_VOLUME);
   long   typ = PositionGetInteger(POSITION_TYPE);

   if(typ != POSITION_TYPE_SELL) return;

   if(!g_initialSet || g_initialRisk <= 0.0)
   {
      Print("⚠️ Initial reference not set → skipping TP logic");
      return;
   }

   double barClose = iClose(_Symbol, _Period, 1);

   // For shorts: target is entry MINUS risk * RiskReward
   double target = g_initialEntry - g_initialRisk * RiskReward;

   if(barClose <= target)
   {
      Print("✅ Fixed R:R reached → closing ALL positions");

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action    = TRADE_ACTION_DEAL;
      req.symbol    = _Symbol;
      req.volume    = vol;
      req.type      = ORDER_TYPE_BUY;  // buy to close short
      req.price     = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      req.deviation = Slippage;

      if(!OrderSend(req, res))
         Print("❌ Close fail err=", GetLastError());
      else
         Print("✅ Short position closed at fixed R:R");
   }
   else
   {
      Print("⏳ Waiting fixed R:R → target=", target);
   }
}

// ======== DISPLAY CURRENT SETTINGS ========
void DisplaySettings()
{
   Print("╔════════════════════════════════════════════════════════════╗");
   Print("║              EA SETTINGS (SHORT VERSION)                    ║");
   Print("╚════════════════════════════════════════════════════════════╝");
   Print("Lots: ", Lots, ", RiskReward: ", RiskReward);
   Print("LimitLots1: ", LimitLots1, ", RiskReward: ", RiskReward);
   Print("LimitLots2: ", LimitLots2, ", RiskReward: ", RiskReward);
   Print("LimitLots3: ", LimitLots3, ", RiskReward: ", RiskReward);
   Print("LimitLots4: ", LimitLots4, ", RiskReward: ", RiskReward);

   // Display candle range filter settings
   Print("┌────────────────────────────────────────────────────────────┐");
   Print("│ CANDLE RANGE FILTER                                        │");
   Print("├────────────────────────────────────────────────────────────┤");
   Print("│ Status: ", UseCandleRangeFilter ? "ENABLED" : "DISABLED");
   if(UseCandleRangeFilter)
   {
      Print("│ Max Range: ", MaxCandleRange, " points");
      Print("│ Min Range: ", MinCandleRange, " points");
   }
   Print("└────────────────────────────────────────────────────────────┘");

   // Display weekday settings
   Print("┌────────────────────────────────────────────────────────────┐");
   Print("│ WEEKDAY FILTERING                                          │");
   Print("├────────────────────────────────────────────────────────────┤");
   if(WeekdayFilterMode == WEEKDAY_DISABLED)
      Print("│ Status: DISABLED");
   else if(WeekdayFilterMode == WEEKDAY_INDIVIDUAL)
   {
      Print("│ Status: INDIVIDUAL WEEKDAYS");
      Print("│ Mon:", TradeMonday, " Tue:", TradeTuesday, " Wed:", TradeWednesday,
            " Thu:", TradeThursday, " Fri:", TradeFriday);
      Print("│ Sat:", TradeSaturday, " Sun:", TradeSunday);
   }
   else if(WeekdayFilterMode == WEEKDAY_GROUPED)
   {
      Print("│ Status: WEEKDAY GROUPS");
      Print("│ Weekdays (Mon-Fri): ", TradeWeekdays);
      Print("│ Weekend (Sat-Sun): ", TradeWeekend);
   }
   Print("└────────────────────────────────────────────────────────────┘");

   // Display month settings
   Print("┌────────────────────────────────────────────────────────────┐");
   Print("│ MONTH FILTERING                                            │");
   Print("├────────────────────────────────────────────────────────────┤");
   if(MonthFilterMode == MONTH_DISABLED)
      Print("│ Status: DISABLED");
   else if(MonthFilterMode == MONTH_INDIVIDUAL)
   {
      Print("│ Status: INDIVIDUAL MONTHS");
      Print("│ Jan:", TradeJanuary, " Feb:", TradeFebruary, " Mar:", TradeMarch,
            " Apr:", TradeApril, " May:", TradeMay, " Jun:", TradeJune);
      Print("│ Jul:", TradeJuly, " Aug:", TradeAugust, " Sep:", TradeSeptember,
            " Oct:", TradeOctober, " Nov:", TradeNovember, " Dec:", TradeDecember);
   }
   else if(MonthFilterMode == MONTH_GROUPED)
   {
      Print("│ Status: SEASONAL GROUPS");
      Print("│ Winter (Dec-Jan-Feb): ", TradeWinter);
      Print("│ Spring (Mar-Apr-May): ", TradeSpring);
      Print("│ Summer (Jun-Jul-Aug): ", TradeSummer);
      Print("│ Autumn (Sep-Oct-Nov): ", TradeAutumn);
   }
   Print("└────────────────────────────────────────────────────────────┘");

   // Display time window settings
   Print("┌────────────────────────────────────────────────────────────┐");
   Print("│ TIME WINDOW FILTERING - SESSIONS                           │");
   Print("├────────────────────────────────────────────────────────────┤");
   Print("│ Status: ", UseTradeWindow ? "ENABLED" : "DISABLED");
   if(UseTradeWindow)
   {
      Print("├────────────────────────────────────────────────────────────┤");
      Print("│ All sessions use uniform 30-min intervals (48 slots total) │");
      Print("│ SESSION 1: MARKET CLOSED  00:00-01:00  slots  0- 1        │");
      Print("│ SESSION 2: MORNING        01:00-10:00  slots  2-19        │");
      Print("│ SESSION 3: MAIN           10:00-23:00  slots 20-45        │");
      Print("│ SESSION 4: EVENING        23:00-00:00  slots 46-47        │");
   }
   Print("└────────────────────────────────────────────────────────────┘");

   // Display flattening times
   Print("┌────────────────────────────────────────────────────────────┐");
   Print("│ FLATTEN TIMES                                              │");
   Print("├────────────────────────────────────────────────────────────┤");
   Print("│ End of Session: ", UseFlattenEnd ? "Yes (" + (string)FlattenHourEnd + ":" + (string)FlattenMinuteEnd + ")" : "No");
   Print("└────────────────────────────────────────────────────────────┘");
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
   // If user turns it OFF during runtime or optimization, ensure no leftovers:
   if(!UseScaleInLimit)
   {
      CancelAllSellLimits();
      g_limitPlacedAfterEntry = false;
   }

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

      // update excursions
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
               break;
            }
         }
      }

      // realized PnL IS the last excursion
      g_maeMoney = MathMin(g_maeMoney, realized);
      g_mfeMoney = MathMax(g_mfeMoney, realized);

      SaveTradeStats(realized, g_entryTime, exitTime, g_candleRange);

      g_tracking = false;
   }

   static datetime lastBar = 0;
   datetime barOpen = iTime(_Symbol, _Period, 0);
	
   bool isInPosition = PositionSelect(_Symbol);
	
   // 🔹 NEW POSITION DETECTED → initialize R:R reference
   if(isInPosition && !g_wasInPosition)
   {
      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl    = PositionGetDouble(POSITION_SL);

      // For shorts: SL is above entry
      if(sl > 0.0 && sl > entry)
      {
         g_initialEntry = entry;
         g_initialRisk  = sl - entry;
         g_initialSet   = true;

         Print("📌 Initial short trade locked: Entry=", g_initialEntry, " Risk=", g_initialRisk);
      }
      else
      {
         Print("⚠️ Invalid SL or entry → cannot compute risk");
      }
   }

   // 🔴 Position OPENED → place SellLimits (scale-in on retracements upward)
   if(UseScaleInLimit && isInPosition && !g_wasInPosition && !g_limitPlacedAfterEntry && g_signalLow > 0)
   {
      Print("⚡ SellStop triggered → placing SellLimits");

      double range = g_signalHigh - g_signalLow;
      if(range <= 0.0)
      {
         Print("⚠️ Invalid range, skip limit placement");
      }
      else
      {
         double offsets[4] = { LimitOffsetPercent1, LimitOffsetPercent2,
                               LimitOffsetPercent3, LimitOffsetPercent4 };
         double lots[4]    = { LimitLots1, LimitLots2, LimitLots3, LimitLots4 };
         bool   enabled[4] = { UseLimit1, UseLimit2, UseLimit3, UseLimit4 };

         double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
         double ask      = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double minDist  = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;

         for(int i = 0; i < 4; i++)
         {
            if(!enabled[i])
            {
               Print("⏭ Limit ", i+1, " disabled → skipping");
               continue;
            }

            double pct = MathMax(0.0, MathMin(100.0, offsets[i]));
            // For shorts: limit price is ABOVE entry (retracement upward)
            // 0% = entry (signalLow), 100% = SL (signalHigh)
            double limitPrice = g_signalLow + range * (pct / 100.0);

            // align to tick grid
            limitPrice = MathFloor(limitPrice / tickSize) * tickSize;
            limitPrice = NormalizeDouble(limitPrice, _Digits);

            // SellLimit must be above ask + minDist
            if(limitPrice <= ask + minDist)
            {
               Print("⚠️ Limit ", i+1, " too close or below ask (@", limitPrice, ") → skipping");
               continue;
            }

            MqlTradeRequest req = {};
            MqlTradeResult  res = {};
            req.action       = TRADE_ACTION_PENDING;
            req.symbol       = _Symbol;
            req.volume       = lots[i];
            req.type         = ORDER_TYPE_SELL_LIMIT;
            req.price        = limitPrice;
            req.sl           = NormalizeDouble(g_signalHigh, _Digits);
            req.deviation    = Slippage;
            req.type_filling = ORDER_FILLING_RETURN;

            if(!OrderSend(req, res))
               Print("❌ SellLimit ", i+1, " failed err=", GetLastError());
            else
               Print("✅ SellLimit ", i+1, " placed @", limitPrice, " lots=", lots[i]);
         }

         g_limitPlacedAfterEntry = true;
      }
   }

   // 🔴 Position CLOSED → remove SellLimits
   if(UseScaleInLimit && !isInPosition && g_wasInPosition)
   {
      Print("📤 Position closed → cleanup");

      CancelAllSellLimits();

      g_signalHigh = 0.0;
      g_signalLow  = 0.0;
      g_limitPlacedAfterEntry = false;

      // reset initial reference
      g_initialEntry = 0.0;
      g_initialRisk  = 0.0;
      g_initialSet   = false;
   }

   // update state
   g_wasInPosition = isInPosition;
	
   if(barOpen == lastBar) return;
   lastBar = barOpen;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   string monthName = GetMonthName(dt.mon);
   string weekdayName = GetWeekdayName(dt.day_of_week);

   // Display session borders
   DisplayTradeWindowStatus(barOpen);

   // 🔹 Weekday filtering check
   if(WeekdayFilterMode != WEEKDAY_DISABLED && !IsWeekdayAllowed(barOpen))
   {
      Print("📅 Weekday Filter: ", weekdayName, " not allowed for trading");
      if(PositionsTotal() == 0)
         CancelOldSellStops();
      return;
   }

   // 🔹 Month filtering check
   if(MonthFilterMode != MONTH_DISABLED && !IsMonthAllowed(barOpen))
   {
      Print("📅 Month Filter: ", monthName, " not allowed for trading");
      if(PositionsTotal() == 0)
         CancelOldSellStops();
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
      CancelOldSellStops();
      return;
   }

   // Green candle setup (only if all filters pass)
   double o1 = iOpen(_Symbol, _Period, 1);
   double h1 = iHigh(_Symbol, _Period, 1);
   double l1 = iLow(_Symbol, _Period, 1);
   double c1 = iClose(_Symbol, _Period, 1);

   // 🔹 Candle range filter check
   if(!IsCandleInRange(h1, l1))
   {
      Print("⚠️ Candle range outside allowed limits - Skipping signal");
      CancelOldSellStops();
      return;
   }

   // SELL-STOP ORDER AT PREVIOUS GREEN CANDLE LOW
   if(c1 > o1)  // Green candle: close > open
   {
      Print("🟢 Green candle → place SellStop");

      CancelOldSellStops();

      double entry = l1;   // entry at candle low
      double stop  = h1;   // SL above candle high
      double risk  = stop - entry;
      g_candleRange = h1 - l1;

      if(risk <= 0.0) return;

      // store signal for later limit placement
      g_signalHigh = h1;
      g_signalLow  = l1;
      g_limitPlacedAfterEntry = false;

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