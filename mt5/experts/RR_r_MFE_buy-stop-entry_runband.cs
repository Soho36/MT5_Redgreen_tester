//+------------------------------------------------------------------+
//| Red-Green Breakout EA: dynamic exit + time window + candle range filters |
//| RUNBAND variant of RR_r_MFE_buy-stop-entry: same buy-stop entry, plus |
//|  + consecutive red-run BAND filter (MinRedRun / MaxRedRun)            |
//|  + LOCATION filter (skip signals closing near the range low)          |
//| With all filters off it trades exactly like the base EA.              |
//| Logs red_run and location per trade for analysis.                     |
//+------------------------------------------------------------------+
#property strict

input double Lots           = 1.0;
input double RiskReward     = 1.0;
input int    Slippage       = 5;

// ======== RED-RUN BAND FILTER ========
// Only arm the entry when the number of consecutive red candles ending at the
// signal candle (index 1) is within [MinRedRun .. MaxRedRun].
//   MinRedRun = 1  -> original behaviour (any single red candle qualifies)
//   MaxRedRun = 0  -> no upper cap (disabled)
// Example: MinRedRun=1, MaxRedRun=2  ==> "skip the signal once the run > 2".
input int    MinRedRun = 1;  // Minimum consecutive reds required (>=1)
input int    MaxRedRun = 0;  // Maximum consecutive reds allowed (0 = no cap)

// ======== LOCATION FILTER ========
// location = (c1 - LL) / (HH - LL) over the last LocationLookback bars
// INCLUDING the signal candle: 0 = signal closed at the range low (falling
// knife), 1 = at the range high (shallow pullback). Skip the signal when
// location < MinLocation. Same formula as analyze_features.py.
//   MinLocation = 0 -> disabled (original behaviour)
// Experimental: see RESEARCH_RESULTS.md for actual MT5 validation results.
input double MinLocation      = 0.0;  // Minimum location in the range (0 = off)
input int    LocationLookback = 20;   // Bars in the high-low range (incl. signal)

// Optional research export only; 0 preserves the existing CSV schema.
// 51 bars = signal plus 50 preceding closed bars. Entry rules are unchanged.
input int    SnapshotBars = 0;       // Raw OHLC bars to log (0 = disabled)

// ======== CANDLE RANGE FILTER ========
input bool   UseCandleRangeFilter = false;  // ENABLE/DISABLE CANDLE RANGE FILTER
input double MaxCandleRange       = 50.0;   // Maximum allowed candle range in points
input double MinCandleRange       = 5.0;    // Minimum allowed candle range in points

// flattening end session
input bool   UseFlattenEnd     = true;	// USE FLATTENING END SESSION
input int    FlattenHourEnd    = 23;
input int    FlattenMinuteEnd  = 30;

// ======== TIME WINDOW FILTERING ========
// no-trading window (block new trades between these times) - Mixed intervals with session borders
input bool   UseTradeWindow   = true;	// USE TIME TRADE WINDOW

// ======== Run-tag input ========
// Leave EMPTY to derive the label from whichever trade window is enabled — then
// the filename can never disagree with the data inside it. Set a value only to
// force a custom name.
input string RunTag = "";   // filename prefix for the MAEMFE CSVs ("" = auto)

// ========== SESSION 1: MARKET CLOSED (00:00-01:00) ==========
input bool W0000W0100 = false;  // 00:00–01:00 (Market Closed)

// ========== SESSION 2: MORNING SESSION (01:00-10:00) ==========
// 01:00-02:00 split into 30-min intervals
input bool W0100W0130 = false;  // 01:00–01:30 (Morning Session)
input bool W0130W0200 = false;  // 01:30–02:00 (Morning Session)

// 1-hour intervals for 02:00-10:00
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

bool windows[26] =  // Total slots: 1 + 2 + 8 + 13 + 2 = 26
{
   // ===== SESSION 1: MARKET CLOSED (00:00-01:00) =====
   W0000W0100,

   // ===== SESSION 2: MORNING SESSION (01:00-10:00) =====
   W0100W0130, W0130W0200,
   W0200W0300, W0300W0400, W0400W0500, W0500W0600,
   W0600W0700, W0700W0800, W0800W0900, W0900W1000,

   // ===== SESSION 3: MAIN SESSION (10:00-23:00) =====
   W1000W1100, W1100W1200, W1200W1300, W1300W1400,
   W1400W1500, W1500W1600, W1600W1700, W1700W1800,
   W1800W1900, W1900W2000, W2000W2100, W2100W2200,
   W2200W2300,

   // ===== SESSION 4: EVENING SESSION (23:00-00:00) =====
   W2300W2330, W2330W0000
};

// Session names for display purposes
string GetSessionName(int slot)
{
   if(slot == 0) return "MARKET CLOSED";
   if(slot >= 1 && slot <= 10) return "MORNING";
   if(slot >= 11 && slot <= 23) return "MAIN";
   if(slot >= 24 && slot <= 25) return "EVENING";
   return "UNKNOWN";
}

// Global variables
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
int    g_redRun      = 0;    // consecutive red-run length that armed the entry (logged to CSV)
double g_location    = 0.0;  // location of the signal close in its range (logged to CSV)
double g_snapshot[];
int g_snapshotCount = 0;
datetime g_signalTime = 0;

datetime g_entryTime = 0;
string   g_csvName   = "trade_stats.csv";
string   g_runTag    = "";   // resolved in OnInit, reused by OnTester

// ======== HELPER FUNCTIONS ========

bool IsFlattenTimeEnd(datetime barOpen)
{
   MqlDateTime dt; TimeToStruct(barOpen, dt);
   return (dt.hour == FlattenHourEnd && dt.min == FlattenMinuteEnd);
}

// Count consecutive red candles ending at the last CLOSED candle (index 1),
// walking back until a non-red candle is hit. Returns 0 if index 1 is not red.
int ConsecutiveRedRun()
{
   int count = 0;
   int bars  = Bars(_Symbol, _Period);
   int maxLook = 500; // safety cap so a pathological history can't hang the loop

   for(int i = 1; i < bars && i <= maxLook; i++)
   {
      if(iClose(_Symbol, _Period, i) < iOpen(_Symbol, _Period, i))
         count++;
      else
         break;
   }
   return count;
}

// Where the signal candle (index 1) closed inside the high-low range of the
// last LocationLookback bars, including itself: 0 = at the low, 1 = at the high.
// Returns -1 if the range cannot be computed.
double SignalLocation()
{
   // Require the complete window; never silently use a shorter history.
   MqlRates bars[];
   ArraySetAsSeries(bars, true);
   if(CopyRates(_Symbol, _Period, 1, LocationLookback, bars) != LocationLookback)
      return -1.0;

   double hh = bars[0].high;
   double ll = bars[0].low;
   for(int i = 1; i < LocationLookback; i++)
   {
      hh = MathMax(hh, bars[i].high);
      ll = MathMin(ll, bars[i].low);
   }
   if(hh <= ll) return -1.0;

   double location = (bars[0].close - ll) / (hh - ll);
   if(!MathIsValidNumber(location) || location < 0.0 || location > 1.0)
      return -1.0;
   return location;
}

bool IsTradeWindow(datetime barOpen)
{
   if(!UseTradeWindow)
      return true;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);

   int totalMinutes = dt.hour * 60 + dt.min;
   int slot;

   // Session 1: 00:00-01:00 - 1-hour interval
   if(totalMinutes < 60)
   {
      slot = 0;
   }
   // Session 2: 01:00-10:00 - mixed intervals
   else if(totalMinutes >= 60 && totalMinutes < 600) // 01:00 to 10:00
   {
      if(totalMinutes < 120) // 01:00-02:00 (30-min slots)
      {
         slot = 1 + ((totalMinutes - 60) / 30);
      }
      else // 02:00-10:00 (hourly slots)
      {
         slot = 3 + (dt.hour - 2);  // slots 3-10
      }
   }
   // Session 3: 10:00-23:00 - hourly intervals
   else if(totalMinutes >= 600 && totalMinutes < 1380) // 10:00 to 23:00
   {
      slot = 11 + (dt.hour - 10);  // slots 11-23
   }
   // Session 4: 23:00-00:00 - 30-min intervals
   else // 23:00-00:00
   {
      slot = 24 + ((totalMinutes - 1380) / 30);  // slots 24-25
   }

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

// ======== CSV FUNCTIONS ========
void TakeResearchSnapshot()
{
   if(SnapshotBars == 0) return;
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, _Period, 1, SnapshotBars, rates);
   g_snapshotCount = MathMax(copied, 0);
   g_signalTime = (g_snapshotCount > 0 ? rates[0].time : 0);
   ArrayResize(g_snapshot, 4 * g_snapshotCount);
   for(int i = 0; i < g_snapshotCount; i++)
   {
      g_snapshot[4*i] = rates[i].open;
      g_snapshot[4*i+1] = rates[i].high;
      g_snapshot[4*i+2] = rates[i].low;
      g_snapshot[4*i+3] = rates[i].close;
   }
}

void SaveSnapshotTradeStats(double realized, datetime entryTime, datetime exitTime, double candleRange)
{
   // Text output avoids FileWrite's argument limit for wide bar snapshots.
   int f = FileOpen(g_csvName, FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_WRITE|FILE_COMMON);
   if(f == INVALID_HANDLE)
   {
      Print("Snapshot file open failed ", GetLastError());
      return;
   }
   if(FileSize(f) == 0)
   {
      string header = "ticket\tentry_time\texit_time\tmae_money\tmfe_money\ttrade_profit"
                      "\tcandle_range\tred_run\tlocation\tsignal_time\tperiod_sec";
      for(int i = 1; i <= SnapshotBars; i++)
         header += StringFormat("\to%d\th%d\tl%d\tc%d", i, i, i, i);
      FileWriteString(f, header + "\n");
   }
   string line = (string)(long)g_ticket
                 + "\t" + TimeToString(entryTime, TIME_DATE|TIME_SECONDS)
                 + "\t" + TimeToString(exitTime, TIME_DATE|TIME_SECONDS)
                 + "\t" + DoubleToString(g_maeMoney, 8)
                 + "\t" + DoubleToString(g_mfeMoney, 8)
                 + "\t" + DoubleToString(realized, 8)
                 + "\t" + DoubleToString(candleRange, _Digits)
                 + "\t" + (string)g_redRun
                 + "\t" + DoubleToString(g_location, 10)
                 + "\t" + TimeToString(g_signalTime, TIME_DATE|TIME_SECONDS)
                 + "\t" + (string)PeriodSeconds(_Period);
   for(int i = 0; i < 4 * SnapshotBars; i++)
      line += "\t" + (i < 4 * g_snapshotCount ? DoubleToString(g_snapshot[i], _Digits) : "");
   FileSeek(f, 0, SEEK_END);
   FileWriteString(f, line + "\n");
   FileClose(f);
}

void SaveTradeStats(double realized, datetime entryTime, datetime exitTime, double candleRange)
{
   if(SnapshotBars > 0)
   {
      SaveSnapshotTradeStats(realized, entryTime, exitTime, candleRange);
      return;
   }
   int f = FileOpen(g_csvName, FILE_READ|FILE_WRITE|FILE_CSV|FILE_SHARE_WRITE|FILE_COMMON);
   if(f == INVALID_HANDLE)
   {
      Print("File open failed ", GetLastError());
      return;
   }

   // A new Unicode CSV may already contain its two-byte BOM.
   if(FileSize(f) <= 2)
      FileWrite(f, "ticket", "entry_time", "exit_time", "mae_money", "mfe_money", "trade_profit", "candle_range", "red_run", "location");

   FileSeek(f, 0, SEEK_END);
   FileWrite(
      f,
      (long)g_ticket,
      TimeToString(entryTime, TIME_DATE|TIME_SECONDS),
      TimeToString(exitTime, TIME_DATE|TIME_SECONDS),
      g_maeMoney,
      g_mfeMoney,
      realized,
      candleRange,
      g_redRun,
      DoubleToString(g_location, 10)
   );

   FileClose(f);
}

// Flush a tracked close, including a tester-forced close after the last tick.
void SaveClosedTrackedTrade()
{
   if(!g_tracking || PositionSelect(_Symbol)) return;
   if(!HistorySelect(g_entryTime - 86400, TimeCurrent())) return;

   double realized = 0.0;
   datetime exitTime = 0;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(deal, DEAL_POSITION_ID) != g_ticket) continue;
      realized += HistoryDealGetDouble(deal, DEAL_PROFIT);
      if(HistoryDealGetInteger(deal, DEAL_ENTRY) == DEAL_ENTRY_OUT)
      {
         exitTime = (datetime)HistoryDealGetInteger(deal, DEAL_TIME);
         break;
      }
   }
   if(exitTime == 0) return;
   g_maeMoney = MathMin(g_maeMoney, realized);
   g_mfeMoney = MathMax(g_mfeMoney, realized);
   SaveTradeStats(realized, g_entryTime, exitTime, g_candleRange);
   g_tracking = false;
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

   double vol = PositionGetDouble(POSITION_VOLUME);
   long   typ = PositionGetInteger(POSITION_TYPE);

   if(typ != POSITION_TYPE_BUY) return;

   if(!g_initialSet || g_initialRisk <= 0.0)
   {
      Print("⚠️ Initial reference not set → skipping TP logic");
      return;
   }

   double barClose = iClose(_Symbol, _Period, 1);

   double target = g_initialEntry + g_initialRisk * RiskReward;

   if(barClose >= target)
   {
      Print("✅ Fixed R:R reached → closing ALL positions");

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action    = TRADE_ACTION_DEAL;
      req.symbol    = _Symbol;
      req.volume    = vol; // closes full net position
      req.type      = ORDER_TYPE_SELL;
      req.price     = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      req.deviation = Slippage;

      if(!OrderSend(req, res))
         Print("❌ Close fail err=", GetLastError());
      else
         Print("✅ Position closed at fixed R:R");
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
   Print("║                    EA SETTINGS                             ║");
   Print("╚════════════════════════════════════════════════════════════╝");
   Print("Lots: ", Lots, ", RiskReward: ", RiskReward);

   // Display red-run band filter
   Print("┌────────────────────────────────────────────────────────────┐");
   Print("│ RED-RUN BAND FILTER                                        │");
   Print("├────────────────────────────────────────────────────────────┤");
   Print("│ Min consecutive reds: ", (MinRedRun < 1 ? 1 : MinRedRun));
   Print("│ Max consecutive reds: ", (MaxRedRun > 0 ? (string)MaxRedRun : "no cap"));
   Print("└────────────────────────────────────────────────────────────┘");

   // Display location filter
   Print("┌────────────────────────────────────────────────────────────┐");
   Print("│ LOCATION FILTER                                            │");
   Print("├────────────────────────────────────────────────────────────┤");
   if(MinLocation > 0.0)
      Print("│ Skip if signal close < ", DoubleToString(MinLocation, 2),
            " of the ", LocationLookback, "-bar range");
   else
      Print("│ Status: DISABLED");
   Print("└────────────────────────────────────────────────────────────┘");

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

   // Display time window settings
   Print("┌────────────────────────────────────────────────────────────┐");
   Print("│ TIME WINDOW FILTERING - SESSIONS                           │");
   Print("├────────────────────────────────────────────────────────────┤");
   Print("│ Status: ", UseTradeWindow ? "ENABLED" : "DISABLED");
   if(UseTradeWindow)
   {
      Print("├────────────────────────────────────────────────────────────┤");
      Print("│ SESSION 1: MARKET CLOSED (00:00-01:00) - 1 hour           │");
      Print("├────────────────────────────────────────────────────────────┤");
      Print("│ SESSION 2: MORNING (01:00-10:00)                          │");
      Print("│   - 01:00-02:00: 30-min intervals                         │");
      Print("│   - 02:00-10:00: 1-hour intervals                         │");
      Print("├────────────────────────────────────────────────────────────┤");
      Print("│ SESSION 3: MAIN (10:00-23:00) - 1-hour intervals          │");
      Print("├────────────────────────────────────────────────────────────┤");
      Print("│ SESSION 4: EVENING (23:00-00:00) - 30-min intervals       │");
   }
   Print("└────────────────────────────────────────────────────────────┘");

   // Display flattening times
   Print("┌────────────────────────────────────────────────────────────┐");
   Print("│ FLATTEN TIMES                                              │");
   Print("├────────────────────────────────────────────────────────────┤");
   Print("│ End of Session: ", UseFlattenEnd ? "Yes (" + (string)FlattenHourEnd + ":" + (string)FlattenMinuteEnd + ")" : "No");
   Print("└────────────────────────────────────────────────────────────┘");
}

// ======== RUN LABEL ========
// Append a tag once; skips duplicates so the two 01:00-02:00 half-windows
// (and the two 23:00-00:00 ones) collapse to a single label.
void AddWinTag(string &lbl, const string t)
{
   if(StringFind("+" + lbl + "+", "+" + t + "+") >= 0) return;
   lbl = (lbl == "" ? t : lbl + "+" + t);
}

// Build the label from the ENABLED trade windows, so an export can never be
// mislabelled (e.g. named "2-3" while actually holding 3-4 trades).
string ActiveWindowLabel()
{
   string l = "";
   if(W0000W0100)               AddWinTag(l, "0-1");
   if(W0100W0130 || W0130W0200) AddWinTag(l, "1-2");
   if(W0200W0300)               AddWinTag(l, "2-3");
   if(W0300W0400)               AddWinTag(l, "3-4");
   if(W0400W0500)               AddWinTag(l, "4-5");
   if(W0500W0600)               AddWinTag(l, "5-6");
   if(W0600W0700)               AddWinTag(l, "6-7");
   if(W0700W0800)               AddWinTag(l, "7-8");
   if(W0800W0900)               AddWinTag(l, "8-9");
   if(W0900W1000)               AddWinTag(l, "9-10");
   if(W1000W1100)               AddWinTag(l, "10-11");
   if(W1100W1200)               AddWinTag(l, "11-12");
   if(W1200W1300)               AddWinTag(l, "12-13");
   if(W1300W1400)               AddWinTag(l, "13-14");
   if(W1400W1500)               AddWinTag(l, "14-15");
   if(W1500W1600)               AddWinTag(l, "15-16");
   if(W1600W1700)               AddWinTag(l, "16-17");
   if(W1700W1800)               AddWinTag(l, "17-18");
   if(W1800W1900)               AddWinTag(l, "18-19");
   if(W1900W2000)               AddWinTag(l, "19-20");
   if(W2000W2100)               AddWinTag(l, "20-21");
   if(W2100W2200)               AddWinTag(l, "21-22");
   if(W2200W2300)               AddWinTag(l, "22-23");
   if(W2300W2330 || W2330W0000) AddWinTag(l, "23-24");
   return (l == "" ? "nowin" : l);
}

// ======== EA CORE ========
int OnInit()
{
   if(SnapshotBars < 0)
   {
      Print("SnapshotBars must be >= 0");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!MathIsValidNumber(MinLocation) || MinLocation < 0.0 || MinLocation > 1.0
      || LocationLookback < 1)
   {
      Print("Invalid location inputs: MinLocation must be in [0,1], LocationLookback >= 1");
      return INIT_PARAMETERS_INCORRECT;
   }

   // Name the export per window+RiskReward so passes never overwrite each other.
   // Empty RunTag => label derived from the enabled window(s).
   g_runTag  = (RunTag == "" ? ActiveWindowLabel() : RunTag);
   g_csvName = "runband_" + g_runTag + "_" + DoubleToString(RiskReward, 2) + ".csv";
   Print("Run tag: ", g_runTag, "   ->   ", g_csvName);

   // Delete previous stats file if exists
   if(FileIsExist(g_csvName, FILE_COMMON))
   {
      if(FileDelete(g_csvName, FILE_COMMON))
         Print("Old trade_stats.csv deleted");
      else
         Print("Failed to delete old CSV. Error=", GetLastError());
   }

   DisplaySettings();
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| MT5's own figures for this pass, written next to the per-trade    |
//| export. Runs ONCE per pass, so the cost is one file write.        |
//| Purpose is cross-checking, not offloading maths: equity_dd is the |
//| tester's exact drawdown, so Python can verify its reconstruction  |
//| instead of trusting it. lr_correlation scores equity-curve        |
//| straightness (1.0 = perfectly linear), which the per-trade data   |
//| can also give but is handy to have straight from the source.      |
//| One file per pass => parallel agents never share a handle.        |
//+------------------------------------------------------------------+
double OnTester()
{
   SaveClosedTrackedTrade();
   string fn = "runband_" + g_runTag + "_" + DoubleToString(RiskReward, 2) + "_stats.csv";
   int f = FileOpen(fn, FILE_READ|FILE_WRITE|FILE_CSV|FILE_SHARE_WRITE|FILE_COMMON);
   if(f == INVALID_HANDLE)
   {
      Print("Stats file open failed ", GetLastError());
      return(0.0);
   }

   FileWrite(f, "run_tag", "risk_reward", "trades", "net_profit", "gross_profit",
                "gross_loss", "equity_dd", "balance_dd", "profit_factor",
                "expected_payoff", "recovery_factor", "sharpe",
                "min_red_run", "max_red_run", "min_location", "location_lookback", "snapshot_bars");
   FileWrite(f, g_runTag,
                RiskReward,
                (int)TesterStatistics(STAT_TRADES),
                TesterStatistics(STAT_PROFIT),
                TesterStatistics(STAT_GROSS_PROFIT),
                TesterStatistics(STAT_GROSS_LOSS),
                TesterStatistics(STAT_EQUITY_DD),
                TesterStatistics(STAT_BALANCE_DD),
                TesterStatistics(STAT_PROFIT_FACTOR),
                TesterStatistics(STAT_EXPECTED_PAYOFF),
                TesterStatistics(STAT_RECOVERY_FACTOR),
                TesterStatistics(STAT_SHARPE_RATIO),
                MinRedRun, MaxRedRun, MinLocation, LocationLookback, SnapshotBars);
   FileClose(f);
   return(0.0);
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
      SaveClosedTrackedTrade();
   }

   static datetime lastBar = 0;
   datetime barOpen = iTime(_Symbol, _Period, 0);

	bool isInPosition = PositionSelect(_Symbol);

	// 🔹 NEW POSITION DETECTED → initialize R:R reference
	if(isInPosition && !g_wasInPosition)
	{
	   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
	   double sl    = PositionGetDouble(POSITION_SL);

	   if(sl > 0.0 && entry > sl)
	   {
		  g_initialEntry = entry;
		  g_initialRisk  = entry - sl;
		  g_initialSet   = true;

		  Print("📌 Initial trade locked (universal): Entry=", g_initialEntry, " Risk=", g_initialRisk);
	   }
	   else
	   {
		  Print("⚠️ Invalid SL or entry → cannot compute risk");
	   }
	}

	// 🔴 Position CLOSED → reset reference
	if(!isInPosition && g_wasInPosition)
	{
	   Print("📤 Position closed → cleanup");

	   // 🔹 reset initial reference
	   g_initialEntry = 0.0;
	   g_initialRisk  = 0.0;
	   g_initialSet   = false;
	}

	// update state
	g_wasInPosition = isInPosition;

   if(barOpen == lastBar) return;
   lastBar = barOpen;

   // Display session borders
   DisplayTradeWindowStatus(barOpen);

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


   // BUY-STOP ORDER AT PREVIOUS RED CANDLE HIGH
    if(c1 < o1)
	{
	   // 🔹 Filters. A rejected red signal cancels the pending order, just as
	   //     an accepted one would replace it; a green bar (no signal) leaves
	   //     the pending order alone, as in the base EA.
	   int    run    = ConsecutiveRedRun();
	   int    minRun = (MinRedRun < 1) ? 1 : MinRedRun;
	   double loc    = SignalLocation();

	   if(run < minRun)
	   {
	      Print("⛔ Red-run ", run, " < min ", minRun, " - skipping signal");
	      CancelOldBuyStops();
	      return;
	   }
	   if(MaxRedRun > 0 && run > MaxRedRun)
	   {
	      Print("⛔ Red-run ", run, " > max ", MaxRedRun, " - skipping signal");
	      CancelOldBuyStops();
	      return;
	   }
	   if(MinLocation > 0.0 && loc < 0.0)
	   {
	      Print("Location unavailable for the complete lookback - skipping signal");
	      CancelOldBuyStops();
	      return;
	   }
	   if(MinLocation > 0.0 && loc < MinLocation)
	   {
	      Print("⛔ Location ", DoubleToString(loc, 2), " < min ", DoubleToString(MinLocation, 2),
	            " - signal at the bottom of the range, skipping");
	      CancelOldBuyStops();
	      return;
	   }

	   Print("Red candle (run=", run, ", location=", DoubleToString(loc, 2), ") -> place Buy Stop");

	   CancelOldBuyStops();

	   double entry = h1;
	   double stop  = l1;
	   double risk  = entry - stop;
	   g_candleRange = h1 - l1;
	   g_redRun      = run;   // stored for the CSV when this trade closes
	   g_location    = loc;

	   if(risk <= 0.0) return;

	   TakeResearchSnapshot();

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
	   {
	      Print("Place Buy Stop failed err=", GetLastError(),
	            " retcode=", res.retcode);
	   }
	   else
	      Print("Buy Stop placed @", entry);
	}
}
