//+------------------------------------------------------------------+
//| Green-Red Breakout EA (SHORT): dynamic exit + time + month + weekday filters |
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

input bool   UseLimit2           = true;	// LIMIT2
input double LimitOffsetPercent2 = 50.0;  	// Limit 2 offset %
input double LimitLots2          = 1.5;

input bool   UseLimit3           = true;	// LIMIT3
input double LimitOffsetPercent3 = 75.0;  	// Limit 3 offset %
input double LimitLots3          = 2.0;

input bool   UseLimit4           = true;	// LIMIT4
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
input int    FlattenHourEnd    = 20;
input int    FlattenMinuteEnd  = 00;

// ======== TIME WINDOW FILTERING ========
input bool   UseTradeWindow   = true;	// USE TIME TRADE WINDOW

// ========== SESSION 1: MARKET CLOSED (00:00-01:00) ==========
input bool W0000W0100 = false;  // 00:00–01:00 (Market Closed)

// ========== SESSION 2: MORNING SESSION (01:00-10:00) ==========
input bool W0100W0130 = false;  // 01:00–01:30 (Morning Session)
input bool W0130W0200 = false;  // 01:30–02:00 (Morning Session)

input bool W0200W0300 = false;  // 02:00–03:00 (Morning Session)
input bool W0300W0400 = false;  // 03:00–04:00 (Morning Session)
input bool W0400W0500 = false;  // 04:00–05:00 (Morning Session)
input bool W0500W0600 = false;  // 05:00–06:00 (Morning Session)
input bool W0600W0700 = false;  // 06:00–07:00 (Morning Session)
input bool W0700W0800 = false;  // 07:00–08:00 (Morning Session)
input bool W0800W0900 = false;  // 08:00–09:00 (Morning Session)
input bool W0900W1000 = false;  // 09:00–10:00 (Morning Session)

// ========== SESSION 3: MAIN SESSION (10:00-23:00) ==========
input bool W1000W1100 = false;  // 10:00–11:00 (Main Session)
input bool W1100W1200 = false;  // 11:00–12:00 (Main Session)
input bool W1200W1300 = false;  // 12:00–13:00 (Main Session)
input bool W1300W1400 = false;  // 13:00–14:00 (Main Session)
input bool W1400W1500 = false;  // 14:00–15:00 (Main Session)
input bool W1500W1600 = false;  // 15:00–16:00 (Main Session)
input bool W1600W1700 = false;  // 16:00–17:00 (Main Session)
input bool W1700W1800 = false;  // 17:00–18:00 (Main Session)
input bool W1800W1900 = false;  // 18:00–19:00 (Main Session)
input bool W1900W2000 = false;  // 19:00–20:00 (Main Session)
input bool W2000W2100 = false;  // 20:00–21:00 (Main Session)
input bool W2100W2200 = false;  // 21:00–22:00 (Main Session)
input bool W2200W2300 = false;  // 22:00–23:00 (Main Session)

// ========== SESSION 4: EVENING SESSION (23:00-00:00) ==========
input bool W2300W2330 = false;  // 23:00–23:30 (Evening Session)
input bool W2330W0000 = false;  // 23:30–00:00 (Evening Session)

bool windows[26] =
{
   W0000W0100,
   W0100W0130, W0130W0200,
   W0200W0300, W0300W0400, W0400W0500, W0500W0600,
   W0600W0700, W0700W0800, W0800W0900, W0900W1000,
   W1000W1100, W1100W1200, W1200W1300, W1300W1400,
   W1400W1500, W1500W1600, W1600W1700, W1700W1800,
   W1800W1900, W1900W2000, W2000W2100, W2100W2200,
   W2200W2300,
   W2300W2330, W2330W0000
};

string GetSessionName(int slot)
{
   if(slot == 0) return "MARKET CLOSED";
   if(slot >= 1 && slot <= 10) return "MORNING";
   if(slot >= 11 && slot <= 23) return "MAIN";
   if(slot >= 24 && slot <= 25) return "EVENING";
   return "UNKNOWN";
}

// Global variables
bool   g_limitPlacedAfterEntry = false;
double g_signalHigh = 0.0;
double g_signalLow  = 0.0;
bool   g_wasInPosition = false;
double g_initialEntry = 0.0;
double g_initialRisk  = 0.0;
bool   g_initialSet   = false;

// ======== MAE / MFE (FLOATING PNL BASED) ========
double g_maeMoney   = 0.0;
double g_mfeMoney   = 0.0;
bool   g_tracking   = false;
ulong  g_ticket     = 0;
double g_candleRange = 0.0;

datetime g_entryTime = 0;
string   g_csvName   = "trade_stats_short.csv";

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
   
   int totalMinutes = dt.hour * 60 + dt.min;
   int slot;
   
   if(totalMinutes < 60)
      slot = 0;
   else if(totalMinutes >= 60 && totalMinutes < 600)
   {
      if(totalMinutes < 120)
         slot = 1 + ((totalMinutes - 60) / 30);
      else
         slot = 3 + (dt.hour - 2);
   }
   else if(totalMinutes >= 600 && totalMinutes < 1380)
      slot = 11 + (dt.hour - 10);
   else
      slot = 24 + ((totalMinutes - 1380) / 30);
   
   return windows[slot];
}

void DisplayTradeWindowStatus(datetime barOpen)
{
   if(!UseTradeWindow) return;
   
   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   
   int totalMinutes = dt.hour * 60 + dt.min;
   string borderLine = "";
   
   if(totalMinutes == 60)
      borderLine = "═══════════════ MORNING SESSION START ═══════════════";
   else if(totalMinutes == 600)
      borderLine = "════════════════ MAIN SESSION START ════════════════";
   else if(totalMinutes == 1380)
      borderLine = "═══════════════ EVENING SESSION START ═══════════════";
   
   if(borderLine != "")
      Print(borderLine);
}

bool IsCandleInRange(double high, double low)
{
   if(!UseCandleRangeFilter)
      return true;
   
   double rangePoints = (high - low) / _Point;
   
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
   int weekday = dt.day_of_week;

   if(WeekdayFilterMode == WEEKDAY_INDIVIDUAL)
   {
      switch(weekday)
      {
         case 1:  return TradeMonday;
         case 2:  return TradeTuesday;
         case 3:  return TradeWednesday;
         case 4:  return TradeThursday;
         case 5:  return TradeFriday;
         case 6:  return TradeSaturday;
         case 0:  return TradeSunday;
      }
   }
   else if(WeekdayFilterMode == WEEKDAY_GROUPED)
   {
      if(weekday >= 1 && weekday <= 5)
         return TradeWeekdays;
      else if(weekday == 6 || weekday == 0)
         return TradeWeekend;
   }

   return false;
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
   int month = dt.mon;

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
   else if(MonthFilterMode == MONTH_GROUPED)
   {
      if(month == 12 || month == 1 || month == 2)
         return TradeWinter;
      else if(month >= 3 && month <= 5)
         return TradeSpring;
      else if(month >= 6 && month <= 8)
         return TradeSummer;
      else if(month >= 9 && month <= 11)
         return TradeAutumn;
   }

   return false;
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

   // For shorts: target is BELOW entry by risk * RiskReward
   double target = g_initialEntry - g_initialRisk * RiskReward;

   if(barClose <= target)
   {
      Print("✅ Fixed R:R reached → closing ALL positions");

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action    = TRADE_ACTION_DEAL;
      req.symbol    = _Symbol;
      req.volume    = vol;
      req.type      = ORDER_TYPE_BUY;
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
   Print("║              EA SETTINGS (SHORT VERSION)                   ║");
   Print("╚════════════════════════════════════════════════════════════╝");
   Print("Lots: ", Lots, ", RiskReward: ", RiskReward);
   Print("LimitLots1: ", LimitLots1);
   Print("LimitLots2: ", LimitLots2);
   Print("LimitLots3: ", LimitLots3);
   Print("LimitLots4: ", LimitLots4);

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

   Print("┌────────────────────────────────────────────────────────────┐");
   Print("│ TIME WINDOW FILTERING - SESSIONS                           │");
   Print("├────────────────────────────────────────────────────────────┤");
   Print("│ Status: ", UseTradeWindow ? "ENABLED" : "DISABLED");
   Print("└────────────────────────────────────────────────────────────┘");

   Print("┌────────────────────────────────────────────────────────────┐");
   Print("│ FLATTEN TIMES                                              │");
   Print("├────────────────────────────────────────────────────────────┤");
   Print("│ End of Session: ", UseFlattenEnd ? "Yes (" + (string)FlattenHourEnd + ":" + (string)FlattenMinuteEnd + ")" : "No");
   Print("└────────────────────────────────────────────────────────────┘");
}

// ======== EA CORE ========
int OnInit()
{
   if(FileIsExist(g_csvName))
   {
      if(FileDelete(g_csvName))
         Print("Old trade_stats_short.csv deleted");
      else
         Print("Failed to delete old CSV. Error=", GetLastError());
   }

   DisplaySettings();
   return(INIT_SUCCEEDED);
}


void OnTick()
{
   // If user turns it OFF during runtime, ensure no leftovers:
   if(!UseScaleInLimit)
   {
      CancelAllSellLimits();
      g_limitPlacedAfterEntry = false;
   }

   // ---- TRACK FLOATING MAE / MFE (tick-based) ----
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

      g_maeMoney = MathMin(g_maeMoney, floating);
      g_mfeMoney = MathMax(g_mfeMoney, floating);
   }
   else if(g_tracking)
   {
      double realized = 0.0;
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

   // 🔴 Position OPENED → place SellLimits (scale-in above entry, toward SL)
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

            // For shorts: limits are ABOVE entry (between entry and SL)
            // 0% = entry (signalLow), 100% = SL (signalHigh)
            double limitPrice = g_signalLow + range * (pct / 100.0);

            // Align to tick grid
            limitPrice = MathCeil(limitPrice / tickSize) * tickSize;
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

      g_initialEntry = 0.0;
      g_initialRisk  = 0.0;
      g_initialSet   = false;
   }

   // Update state
   g_wasInPosition = isInPosition;

   if(barOpen == lastBar) return;
   lastBar = barOpen;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   string monthName   = GetMonthName(dt.mon);
   string weekdayName = GetWeekdayName(dt.day_of_week);

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

   // 🔹 Flatten end of session
   if(UseFlattenEnd && IsFlattenTimeEnd(barOpen))
   {
      Print("🌙 Flatten cutoff reached → closing everything");
      CloseAllPositions();
      CancelAllOrders();
      return;
   }

   // 🔹 Manage existing position
   if(PositionsTotal() > 0)
   {
      ManageOpenPosition();
      return;
   }

   // 🔹 Time window check (ENTRY ONLY)
   if(!IsTradeWindow(barOpen))
   {
      Print("⏱ Outside trading window → no new entries");
      CancelOldSellStops();
      return;
   }

   // Candle data
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
   if(c1 > o1)
   {
      Print("🟢 Green candle → place SellStop");

      CancelOldSellStops();

      double entry = l1;        // Enter on break below the low
      double stop  = h1;        // SL above the high
      double risk  = stop - entry;
      g_candleRange = h1 - l1;

      if(risk <= 0.0) return;

      // Store signal for later limit placement
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
         Print("🔻 SellStop placed @", entry);
   }
}