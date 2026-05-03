//+------------------------------------------------------------------+
//| Red-Green Breakout EA: dynamic exit + time + month + weekday filters |
//| WITH FIXED TP CALCULATION (uses original risk)                  |
//+------------------------------------------------------------------+
#property strict

input double Lots           = 1.0;
input double RiskReward     = 1.0;
input int    Slippage       = 5;

// ======== EXIT STRATEGY SETTINGS ========
enum EXIT_STRATEGY
{
   EXIT_MARKET_CLOSE,   // Close at market when next candle closes at/above target
   EXIT_ATTACHED_TP     // Attach Take Profit to position at R/R distance (SAFE)
};

input EXIT_STRATEGY ExitStrategy = EXIT_ATTACHED_TP;  // Exit strategy
input double        TakeProfitRR = 1.0;               // R/R distance for Take Profit (can be different from RiskReward)

// ======== BREAKEVEN SETTINGS ========
input bool   UseBreakeven      = true;               // Enable/disable breakeven feature
input double BreakevenTrigger  = 1.0;                // R/R level to trigger breakeven (usually 1.0 for 1:1)
input double BreakevenOffset   = 0.0;                // Offset from entry in points (0 = 1 tick below entry)

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
// no-trading window (block new trades between these times) - 1-HOUR INTERVALS
input bool   UseTradeWindow   = true;
input bool W0000W0100 = false;  // 00:00–01:00
input bool W0100W0200 = false;  // 01:00–02:00
input bool W0200W0300 = false;  // 02:00–03:00
input bool W0300W0400 = false;  // 03:00–04:00
input bool W0400W0500 = false;  // 04:00–05:00
input bool W0500W0600 = false;  // 05:00–06:00
input bool W0600W0700 = false;  // 06:00–07:00
input bool W0700W0800 = false;  // 07:00–08:00
input bool W0800W0900 = false;  // 08:00–09:00
input bool W0900W1000 = false;  // 09:00–10:00
input bool W1000W1100 = false;  // 10:00–11:00
input bool W1100W1200 = false;  // 11:00–12:00
input bool W1200W1300 = false;  // 12:00–13:00
input bool W1300W1400 = false;  // 13:00–14:00
input bool W1400W1500 = false;  // 14:00–15:00
input bool W1500W1600 = false;  // 15:00–16:00
input bool W1600W1700 = false;  // 16:00–17:00
input bool W1700W1800 = false;  // 17:00–18:00
input bool W1800W1900 = false;  // 18:00–19:00
input bool W1900W2000 = false;  // 19:00–20:00
input bool W2000W2100 = false;  // 20:00–21:00
input bool W2100W2200 = false;  // 21:00–22:00
input bool W2200W2300 = false;  // 22:00–23:00
input bool W2300W0000 = false;  // 23:00–00:00

bool windows[24] =
{
   W0000W0100, W0100W0200, W0200W0300, W0300W0400,
   W0400W0500, W0500W0600, W0600W0700, W0700W0800,
   W0800W0900, W0900W1000, W1000W1100, W1100W1200,
   W1200W1300, W1300W1400, W1400W1500, W1500W1600,
   W1600W1700, W1700W1800, W1800W1900, W1900W2000,
   W2000W2100, W2100W2200, W2200W2300, W2300W0000
};

// ======== MAE / MFE (FLOATING PNL BASED) ========
double g_maeMoney   = 0.0;   // most negative floating PnL
double g_mfeMoney   = 0.0;   // most positive floating PnL
bool   g_tracking   = false;
ulong  g_ticket     = 0;

datetime g_entryTime = 0;
string   g_csvName   = "trade_stats.csv";

// Track trade-specific values
double   g_originalRisk = 0.0;     // Original risk in points
double   g_originalEntry = 0.0;    // Original entry price
double   g_originalSL = 0.0;       // Original stop loss
bool     g_breakevenMoved = false; // Whether we've already moved SL to breakeven

// ======== HELPER FUNCTIONS ========
// Function to normalize price to valid tick size
double NormalizePrice(double price)
{
   // Get tick size from symbol info
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0) tickSize = 0.25; // Default for MNQ if not available
   
   // Round to nearest tick
   return MathRound(price / tickSize) * tickSize;
}

// Function to calculate breakeven SL (1 tick below entry + offset)
double CalculateBreakevenSL(double entryPrice, double offsetPoints)
{
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0) tickSize = 0.25;
   
   // Convert offset from points to price
   double offsetPrice = offsetPoints * _Point;
   
   // Breakeven SL = entry + offset - 1 tick (must be strictly below entry for BUY)
   double breakevenSL = entryPrice + offsetPrice - tickSize;
   
   // Normalize to valid tick
   return NormalizePrice(breakevenSL);
}

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

   int slot = dt.hour;  // 1-hour intervals (0-23)
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
      FileWrite(f, "ticket", "entry_time", "exit_time", "mae_money", "mfe_money", "trade_profit", "breakeven_moved", "original_risk");

   FileSeek(f, 0, SEEK_END);
   FileWrite(
      f,
      (long)g_ticket,
      TimeToString(entryTime, TIME_DATE|TIME_SECONDS),
      TimeToString(exitTime, TIME_DATE|TIME_SECONDS),
      g_maeMoney,
      g_mfeMoney,
      realized,
      g_breakevenMoved,
      g_originalRisk
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

// FIXED: Function to modify position with new Stop Loss
bool SetPositionStopLoss(ulong positionTicket, double stopLossPrice)
{
   if(!PositionSelectByTicket(positionTicket))
   {
      Print("❌ Cannot select position for SL modification");
      return false;
   }
   
   // Normalize SL price to valid tick
   stopLossPrice = NormalizePrice(stopLossPrice);
   
   // Get current position data
   double entryPrice = PositionGetDouble(POSITION_PRICE_OPEN);
   double currentTP = PositionGetDouble(POSITION_TP);
   double currentSL = PositionGetDouble(POSITION_SL);
   
   // For BUY positions, SL must be LESS THAN entry (strictly below)
   if(stopLossPrice >= entryPrice)
   {
      Print("❌ Invalid SL: ", stopLossPrice, " >= Entry: ", entryPrice, " - Cannot set SL at or above entry");
      return false;
   }
   
   // Check if SL actually needs to be moved
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(MathAbs(currentSL - stopLossPrice) <= tickSize)
   {
      Print("ℹ️ SL already at breakeven level");
      return true; // Already set correctly
   }
   
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action    = TRADE_ACTION_SLTP;
   req.symbol    = _Symbol;
   req.position  = positionTicket;
   req.sl        = stopLossPrice;  // New SL
   req.tp        = currentTP;       // Keep existing TP
   
   if(!OrderSend(req, res))
   {
      Print("❌ Failed to set Stop Loss err=", GetLastError());
      return false;
   }
   else
   {
      Print("✅ Stop Loss moved from ", currentSL, " to @", stopLossPrice, " for position #", positionTicket);
      return true;
   }
}

// FIXED: Function to modify position with Take Profit (using ORIGINAL risk)
bool SetPositionTakeProfit(ulong positionTicket, double takeProfitPrice)
{
   if(!PositionSelectByTicket(positionTicket))
   {
      Print("❌ Cannot select position for TP modification");
      return false;
   }
   
   // Normalize TP price to valid tick
   takeProfitPrice = NormalizePrice(takeProfitPrice);
   
   // Get current position data
   double entryPrice = PositionGetDouble(POSITION_PRICE_OPEN);
   double currentSL = PositionGetDouble(POSITION_SL);
   double currentTP = PositionGetDouble(POSITION_TP);
   
   // FIXED: For BUY positions, TP must be ABOVE entry
   if(takeProfitPrice <= entryPrice)
   {
      Print("❌ Invalid TP: ", takeProfitPrice, " <= Entry: ", entryPrice, " - TP must be above entry");
      return false;
   }
   
   // Check if TP actually needs to be set/changed
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(MathAbs(currentTP - takeProfitPrice) <= tickSize)
   {
      Print("ℹ️ TP already set correctly");
      return true;
   }
   
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action    = TRADE_ACTION_SLTP;
   req.symbol    = _Symbol;
   req.position  = positionTicket;
   req.sl        = currentSL;  // Keep existing SL
   req.tp        = takeProfitPrice;  // Set normalized TP
   
   if(!OrderSend(req, res))
   {
      Print("❌ Failed to set Take Profit err=", GetLastError());
      return false;
   }
   else
   {
      Print("✅ Take Profit set from ", currentTP, " to @", takeProfitPrice, " for position #", positionTicket);
      return true;
   }
}

// FIXED: Get original risk from position opening
void InitializeTradeTracking()
{
   if(!PositionSelect(_Symbol)) return;
   
   g_ticket = PositionGetInteger(POSITION_TICKET);
   g_entryTime = (datetime)PositionGetInteger(POSITION_TIME);
   g_originalEntry = PositionGetDouble(POSITION_PRICE_OPEN);
   
   // Try to get original SL from deal history
   g_originalRisk = 0;
   g_originalSL = 0;
   
   if(HistorySelect(g_entryTime - 3600, g_entryTime + 3600))
   {
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
      {
         ulong deal = HistoryDealGetTicket(i);
         if(HistoryDealGetInteger(deal, DEAL_POSITION_ID) == g_ticket)
         {
            if(HistoryDealGetInteger(deal, DEAL_ENTRY) == DEAL_ENTRY_IN)
            {
               double dealPrice = HistoryDealGetDouble(deal, DEAL_PRICE);
               double dealSL = HistoryDealGetDouble(deal, DEAL_SL);
               if(dealSL > 0 && MathAbs(dealPrice - g_originalEntry) <= 0.1) // Match within reasonable tolerance
               {
                  g_originalSL = dealSL;
                  g_originalRisk = dealPrice - dealSL;
                  Print("📊 Original risk loaded: ", g_originalRisk, " points (SL @", g_originalSL, ")");
                  break;
               }
            }
         }
      }
   }
   
   // If we couldn't get from history, use current position data
   if(g_originalRisk <= 0)
   {
      g_originalSL = PositionGetDouble(POSITION_SL);
      g_originalRisk = g_originalEntry - g_originalSL;
      Print("📊 Using current SL as original risk: ", g_originalRisk, " points");
   }
   
   g_breakevenMoved = false;
}

// FIXED: Check and move SL to breakeven (1 tick below entry)
void CheckAndMoveToBreakeven()
{
   if(!UseBreakeven) return;
   if(!PositionSelect(_Symbol)) return;
   
   ulong ticket = PositionGetInteger(POSITION_TICKET);
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double currentSL = PositionGetDouble(POSITION_SL);
   double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   long typ = PositionGetInteger(POSITION_TYPE);
   
   if(typ != POSITION_TYPE_BUY) return;
   if(g_originalRisk <= 0.0) return;
   
   // Calculate breakeven trigger level using ORIGINAL risk
   double breakevenTriggerPrice = entry + (g_originalRisk * BreakevenTrigger);
   
   // Calculate breakeven SL as 1 tick below entry + offset
   double breakevenSL = CalculateBreakevenSL(entry, BreakevenOffset);
   
   // Check if we've already moved to breakeven
   if(g_breakevenMoved) return;
   
   // Check if price has reached the trigger level
   if(currentPrice >= breakevenTriggerPrice)
   {
      // Check if current SL is still below breakeven
      if(currentSL < breakevenSL)
      {
         Print("💰 Price reached ", BreakevenTrigger, "R (", currentPrice, ") - Moving SL to breakeven @", breakevenSL, " (1 tick below entry)");
         if(SetPositionStopLoss(ticket, breakevenSL))
         {
            g_breakevenMoved = true;
            Print("✅ Stop Loss moved to breakeven successfully");
         }
      }
      else
      {
         Print("ℹ️ SL already at or above breakeven level");
         g_breakevenMoved = true;
      }
   }
}

// FIXED: Manage Open Position with ORIGINAL risk for TP calculation
void ManageOpenPosition()
{
   if(!PositionSelect(_Symbol)) return;

   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl    = PositionGetDouble(POSITION_SL);
   double vol   = PositionGetDouble(POSITION_VOLUME);
   long   typ   = PositionGetInteger(POSITION_TYPE);
   ulong  ticket = PositionGetInteger(POSITION_TICKET);
   double currentTP = PositionGetDouble(POSITION_TP);

   if(typ != POSITION_TYPE_BUY) return;

   // === CHECK BREAKEVEN CONDITION ===
   CheckAndMoveToBreakeven();

   // === EXIT STRATEGY 1: Close at market when next candle closes at/above target ===
   if(ExitStrategy == EXIT_MARKET_CLOSE)
   {
      double barClose = iClose(_Symbol, _Period, 1);
      
      // Use ORIGINAL risk for target calculation
      if(g_originalRisk > 0)
      {
         if(barClose >= entry + g_originalRisk * RiskReward)
         {
            Print("✅ ≥ ", RiskReward, "R at bar close → closing at market");

            MqlTradeRequest req = {};
            MqlTradeResult  res = {};
            req.action    = TRADE_ACTION_DEAL;
            req.symbol    = _Symbol;
            req.volume    = vol;
            req.type      = ORDER_TYPE_SELL;
            req.price     = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            req.deviation = Slippage;

            if(!OrderSend(req, res))
               Print("❌ Close fail err=", GetLastError());
            else
               Print("✅ Position closed");
         }
      }
   }
   
   // === EXIT STRATEGY 2: Attached Take Profit at R/R distance (SAFE) ===
   else if(ExitStrategy == EXIT_ATTACHED_TP)
   {
      // FIXED: Use ORIGINAL risk for TP calculation, not current SL
      if(g_originalRisk > 0)
      {
         double rawTarget = entry + (g_originalRisk * TakeProfitRR);
         double targetPrice = NormalizePrice(rawTarget);
         
         // Check if TP is already set correctly
         double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
         bool tpCorrect = (MathAbs(currentTP - targetPrice) <= tickSize);
         
         if(!tpCorrect && targetPrice > entry)
         {
            Print("📊 Setting/updating Take Profit to ", TakeProfitRR, "R (", targetPrice, ") using original risk: ", g_originalRisk, " points");
            SetPositionTakeProfit(ticket, targetPrice);
         }
         else if(targetPrice <= entry)
         {
            Print("⚠️ Warning: Calculated TP (", targetPrice, ") is not above entry - check TakeProfitRR setting");
         }
      }
   }
}

// ======== DISPLAY CURRENT SETTINGS ========
void DisplaySettings()
{
   Print("=== EA Settings ===");
   Print("Lots: ", Lots, ", RiskReward: ", RiskReward);
   
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   Print("Symbol: ", _Symbol, ", Tick Size: ", tickSize);
   
   Print("Exit Strategy: ", ExitStrategy == EXIT_MARKET_CLOSE ? "Market close at candle" : "Attached Take Profit (SAFE)");
   if(ExitStrategy == EXIT_ATTACHED_TP)
   {
      Print("  Take Profit R/R: ", TakeProfitRR);
      Print("  TP uses ORIGINAL risk (locked at entry)");
   }
   
   Print("Breakeven Feature: ", UseBreakeven ? "ENABLED" : "DISABLED");
   if(UseBreakeven)
   {
      Print("  Breakeven Trigger: ", BreakevenTrigger, "R");
      Print("  Breakeven Offset: ", BreakevenOffset, " points");
      Print("  Breakeven SL: 1 tick below entry + offset");
   }

   Print("Candle Range Filter: ", UseCandleRangeFilter ? "ENABLED" : "DISABLED");
   if(UseCandleRangeFilter)
   {
      Print("  Max Candle Range: ", MaxCandleRange, " points");
      Print("  Min Candle Range: ", MinCandleRange, " points");
   }

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

   Print("Time Window Filtering: ", UseTradeWindow ? "ENABLED" : "DISABLED");
   Print("Flatten During: ", UseFlattenDur ? "Yes (" + (string)FlattenHourDur + ":" + (string)FlattenMinuteDur + ")" : "No");
   Print("Flatten End: ", UseFlattenEnd ? "Yes (" + (string)FlattenHourEnd + ":" + (string)FlattenMinuteEnd + ")" : "No");
}

// ======== EA CORE ========
int OnInit()
{
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

void OnDeinit(const int reason)
{
   CancelAllOrders();
}

void OnTick()
{
   // ---- TRACK FLOATING MAE / MFE ----
   if(PositionSelect(_Symbol))
   {
      double floating = PositionGetDouble(POSITION_PROFIT);

      if(!g_tracking)
      {
         g_tracking = true;
         InitializeTradeTracking();  // Get original risk when position opens
         
         g_maeMoney = floating;
         g_mfeMoney = floating;

         Print("Tracking started ticket=", g_ticket, " Risk=", g_originalRisk);
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

      SaveTradeStats(realized, g_entryTime, exitTime);

      g_tracking = false;
      g_breakevenMoved = false;
      g_originalRisk = 0;
   }

   static datetime lastBar = 0;
   datetime barOpen = iTime(_Symbol, _Period, 0);

   if(barOpen == lastBar) return;
   lastBar = barOpen;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   string monthName = GetMonthName(dt.mon);
   string weekdayName = GetWeekdayName(dt.day_of_week);

   // Filter checks
   if(WeekdayFilterMode != WEEKDAY_DISABLED && !IsWeekdayAllowed(barOpen))
   {
      Print("📅 Weekday Filter: ", weekdayName, " not allowed for trading");
      if(PositionsTotal() == 0) CancelOldBuyStops();
      return;
   }

   if(MonthFilterMode != MONTH_DISABLED && !IsMonthAllowed(barOpen))
   {
      Print("📅 Month Filter: ", monthName, " not allowed for trading");
      if(PositionsTotal() == 0) CancelOldBuyStops();
      return;
   }

   if(UseFlattenDur && IsFlattenTimeDur(barOpen))
   {
      Print("Flatten cutoff reached DURING SESSION → closing everything");
      CloseAllPositions();
      CancelAllOrders();
      return;
   }

   if(UseFlattenEnd && IsFlattenTimeEnd(barOpen))
   {
      Print("🌙 Flatten cutoff reached → closing everything");
      CloseAllPositions();
      CancelAllOrders();
      return;
   }

   if(PositionsTotal() > 0)
   {
      ManageOpenPosition();
      return;
   }

   if(!IsTradeWindow(barOpen))
   {
      Print("⏱ Outside trading window → no new entries");
      CancelOldBuyStops();
      return;
   }

   // Red candle setup
   double o1 = iOpen(_Symbol, _Period, 1);
   double h1 = iHigh(_Symbol, _Period, 1);
   double l1 = iLow(_Symbol, _Period, 1);
   double c1 = iClose(_Symbol, _Period, 1);

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
      
      entry = NormalizePrice(entry);
      stop = NormalizePrice(stop);
      
      double tp = 0;
      if(ExitStrategy == EXIT_ATTACHED_TP)
      {
         tp = NormalizePrice(entry + (risk * TakeProfitRR));
      }

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action       = TRADE_ACTION_PENDING;
      req.symbol       = _Symbol;
      req.volume       = Lots;
      req.type         = ORDER_TYPE_BUY_STOP;
      req.price        = entry;
      req.sl           = stop;
      
      if(ExitStrategy == EXIT_ATTACHED_TP)
      {
         req.tp = tp;
      }
      
      req.deviation    = Slippage;
      req.type_filling = ORDER_FILLING_RETURN;

      if(!OrderSend(req, res))
         Print("❌ Place BuyStop fail err=", GetLastError());
      else
         Print("🚀 BuyStop placed @", entry, " SL=", stop, " TP=", req.tp, " Risk=", risk, " (", weekdayName, ", ", monthName, ")");
   }
}