// Q24 buy the reclaim of a broken swing-low level (research only). Frozen protocol:
// docs/levels/SUPPORT_RECLAIM_PROTOCOL.md. Mirrors python/support_reclaim.py, which uses the frozen Q11 level map
// (python/level_visit.py): swing lows (N=5) in a one-week window (session of s + 5 previous), known once pivot + N
// <= s - 1, merged greedily from the lowest within D; L = lowest member's low; a level is identified by that member.
// Intact = no close < L - D after the latest member; departed = a close >= L + A. A = mean of the 14 true ranges before
// s (same contract), D = 0.5 x A. Bar s = the last closed bar breaks a live level if open(s) >= L and
// close(s) < L - BreakDepthA x A; the lowest broken level is used. Order: buy stop at L, stop low(s), if
// L - low(s) >= MinRiskA x A and the ask is below L. A break spends its level (recorded on every bar by SROnNewBar).
// Requires contract_rolls.mqh (CR_DATE/CR_ID). Floating-point expressions follow the Python order.
//
// ReclaimMode 1 = classify + log only (no orders; output identical to the verified classify-only run).
// ReclaimMode 2 = primary: buy stop at L, stop low(s), on bars whose status is "order".
// ReclaimMode 3 = control C1: the same bars, buy stop at high(s), stop low(s).
// Order life: OrderLife bars (cancelled at the open of bar t + OrderLife), or earlier: on a touch of low(s)
// (bid <= low(s) on any tick, SROnTick) if CancelOnLow; by the window exit / flatten ("external"); or when a new order
// replaces it. A breakdown skipped for min risk or a gap does not replace a pending order. After a fill the parent's
// long exit applies (bar-close target at entry + RiskReward x R).

input int    ReclaimMode   = 1;     // 1 classify only, 2 primary (buy stop at L), 3 control C1 (buy stop at high(s))
input int    OrderLife     = 3;     // bars an unfilled order lives
input bool   CancelOnLow   = true;  // cancel an unfilled order when the bid touches low(s) (Q24 follow-up: false)
input double BreakDepthA   = 0.0;   // break threshold below the level, x A (primary 0, S1 0.5)
input double MinRiskA      = 0.25;  // minimum risk L - low(s), x A
input int    LevelN        = 5;     // swing-low strength
input int    LevelSessions = 5;     // previous sessions in the window

#define SR_BARS 1500

enum SRStatus { SR_ORDER=0, SR_GAP=1, SR_MINRISK=2, SR_NO_BREAK=3, SR_NO_LEVEL=4, SR_MISSING=5, SR_ROLL=6, SR_ATR=7 };
string SR_NAMES[8] = {"order","gap_above","min_risk","no_break","no_level","missing_history","contract_roll","invalid_atr"};
int    g_srFile = INVALID_HANDLE, g_srFills = INVALID_HANDLE, g_srCancels = INVALID_HANDLE;
int    g_srErrors = 0, g_srSendErrors = 0, g_srCancelErrors = 0, g_srPlaced = 0, g_srFilled = 0;
int    g_srCancelTouch = 0, g_srCancelExpired = 0, g_srCancelReplaced = 0, g_srCancelExternal = 0;
// The order resting now.
ulong    g_srTicket = 0;
datetime g_srOrdBar = 0, g_srOrdS = 0, g_srOrdKey = 0;
double   g_srOrdEntry = 0, g_srOrdStop = 0, g_srOrdLevel = 0;
int      g_srOrdAge = 0;
int    g_srCounts[8];
// Spent levels (defining pivot times), pruned once far outside any window.
datetime g_srSpent[];
int      g_srNs = 0;
// The latest new-bar classification, read by SROnBar on the same tick.
datetime g_srBar = 0, g_srS = 0, g_srKey = 0, g_srT0 = 0;
double   g_srLevel = 0, g_srEntry = 0, g_srStop = 0, g_srRisk = 0, g_srAtr = 0;
int      g_srSt = SR_MISSING, g_srMembers = 0, g_srKnown = 0, g_srLevels = 0, g_srLive = 0, g_srBroken = 0;
bool     g_srRed = false, g_srSame = false;

int SRContract(datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   int ymd = d.year * 10000 + d.mon * 100 + d.day;
   int id = -1;
   for(int k = 0; k < CR_COUNT && CR_DATE[k] <= ymd; k++) id = CR_ID[k];
   return id;
}

bool SRIsSpent(datetime key)
{
   for(int q = 0; q < g_srNs; q++) if(g_srSpent[q] == key) return true;
   return false;
}

void SRSpend(datetime key)
{
   if(SRIsSpent(key)) return;
   ArrayResize(g_srSpent, g_srNs + 1, 256);
   g_srSpent[g_srNs++] = key;
}

void SRPruneSpent(datetime now)
{
   int w = 0;
   for(int q = 0; q < g_srNs; q++) if(g_srSpent[q] >= now - 30 * 86400) g_srSpent[w++] = g_srSpent[q];
   g_srNs = w;
}

bool SRInit()
{
   if(ReclaimMode < 1 || ReclaimMode > 3 || OrderLife < 1 || !MathIsValidNumber(BreakDepthA) || BreakDepthA < 0 || !MathIsValidNumber(MinRiskA)
      || MinRiskA < 0 || LevelN < 1 || LevelSessions < 0) return false;
   g_srFile = FileOpen(g_runTag + "_reclaim.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(g_srFile == INVALID_HANDLE) return false;
   if(ReclaimMode == 1)
      FileWrite(g_srFile, "bar_time", "s_time", "open", "ask", "bid", "status", "level", "key_time", "t0_time", "members",
                "atr", "entry", "stop", "risk", "known_pivots", "levels", "levels_live", "levels_broken", "s_red",
                "same_contract");
   else
   {
      FileWrite(g_srFile, "bar_time", "s_time", "open", "ask", "bid", "status", "level", "key_time", "t0_time", "members",
                "atr", "entry", "stop", "risk", "known_pivots", "levels", "levels_live", "levels_broken", "s_red",
                "same_contract", "pending_at_open", "order_entry", "order_stop", "action");
      g_srFills = FileOpen(g_runTag + "_fills.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
      g_srCancels = FileOpen(g_runTag + "_cancels.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
      if(g_srFills == INVALID_HANDLE || g_srCancels == INVALID_HANDLE) return false;
      FileWrite(g_srFills, "fill_time", "fill_price", "sl", "order_bar", "s_time", "order_entry", "order_stop", "level",
                "key_time", "age");
      FileWrite(g_srCancels, "cancel_time", "order_bar", "order_entry", "order_stop", "age", "reason", "bid");
   }
   return true;
}

void SRDeinit()
{
   if(g_srFile != INVALID_HANDLE) FileClose(g_srFile);
   if(g_srFills != INVALID_HANDLE) FileClose(g_srFills);
   if(g_srCancels != INVALID_HANDLE) FileClose(g_srCancels);
   g_srFile = INVALID_HANDLE; g_srFills = INVALID_HANDLE; g_srCancels = INVALID_HANDLE;
   int f = FileOpen(g_runTag + "_reclaim_stats.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(f == INVALID_HANDLE) return;
   if(ReclaimMode == 1)
   {
      FileWrite(f, "reclaim_mode", "break_depth_a", "min_risk_a", "log_errors", "tick", "order", "gap_above", "min_risk",
                "no_break", "no_level", "missing_history", "contract_roll", "invalid_atr");
      FileWrite(f, ReclaimMode, BreakDepthA, MinRiskA, g_srErrors,
                DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE), 10), g_srCounts[0], g_srCounts[1],
                g_srCounts[2], g_srCounts[3], g_srCounts[4], g_srCounts[5], g_srCounts[6], g_srCounts[7]);
   }
   else
   {
      FileWrite(f, "reclaim_mode", "break_depth_a", "min_risk_a", "order_life", "cancel_on_low", "log_errors", "send_errors",
                "cancel_errors", "close_errors", "placed", "filled", "cancel_touch_low", "cancel_expired",
                "cancel_replaced", "cancel_external", "order", "gap_above", "min_risk", "no_break", "no_level",
                "missing_history", "contract_roll", "invalid_atr");
      FileWrite(f, ReclaimMode, BreakDepthA, MinRiskA, OrderLife, (int)CancelOnLow, g_srErrors, g_srSendErrors, g_srCancelErrors,
                tr_closeErrors, g_srPlaced, g_srFilled, g_srCancelTouch, g_srCancelExpired, g_srCancelReplaced,
                g_srCancelExternal, g_srCounts[0], g_srCounts[1], g_srCounts[2], g_srCounts[3], g_srCounts[4],
                g_srCounts[5], g_srCounts[6], g_srCounts[7]);
   }
   FileClose(f);
}

// Bar t classification. r[] holds closed bars only (shift >= 1); bar s = n - 1 is the breakdown candidate and every
// level is judged from bars before s, as at the open of s. Levels bar s breaks are added to the spent list.
int SRClassify(datetime barOpen, double ask, datetime &sTime, double &level, datetime &keyTime, datetime &t0Time,
               int &members, double &entry, double &stop, double &risk, double &atr, int &known, int &nlevels,
               int &nlive, int &nbroken, bool &sRed, bool &sameContract)
{
   sTime = 0; level = 0; keyTime = 0; t0Time = 0; members = 0; entry = 0; stop = 0; risk = 0; atr = 0; known = 0;
   nlevels = 0; nlive = 0; nbroken = 0; sRed = false; sameContract = false;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_M30, 1, SR_BARS, r);
   if(n < 1) return SR_MISSING;
   int s = n - 1;
   double o[], l[], c[], h[]; int con[]; datetime day[];
   ArrayResize(o, n); ArrayResize(l, n); ArrayResize(c, n); ArrayResize(h, n); ArrayResize(con, n); ArrayResize(day, n);
   for(int k = 0; k < n; k++)
   {
      o[k] = r[k].open; h[k] = r[k].high; l[k] = r[k].low; c[k] = r[k].close;
      day[k] = r[k].time - (r[k].time % 86400);
      con[k] = SRContract(r[k].time);
   }
   sTime = r[s].time;
   sRed = (c[s] < o[s]);
   sameContract = (con[s] == SRContract(barOpen));
   if(n < 50) return SR_MISSING;
   int dates = 1, start = -1;
   datetime prev = day[s];
   for(int k = s - 1; k >= 0; k--)
   {
      if(day[k] != prev)
      {
         dates++;
         if(dates > LevelSessions + 1) { start = k + 1; break; }
         prev = day[k];
      }
   }
   if(start < 0 && n < SR_BARS && dates == LevelSessions + 1) start = 0;
   if(start < 0) return SR_MISSING;
   for(int k = start; k <= s; k++) if(con[k] != con[s]) return SR_ROLL;
   if(s - 14 < 1) return SR_ATR;
   double sum = 0;
   for(int k = s - 14; k <= s - 1; k++)
   {
      if(con[k] != con[s]) return SR_ATR;
      double tr = h[k] - l[k];
      if(con[k - 1] == con[k]) tr = MathMax(tr, MathMax(MathAbs(h[k] - c[k - 1]), MathAbs(l[k] - c[k - 1])));
      sum += tr;
   }
   double a = sum / 14.0;
   if(a <= 0) return SR_ATR;
   atr = a;
   double d = 0.5 * a;
   // Known swing lows: pivot bar in the window, confirmed (i + N closed) before bar s opens.
   int piv[]; int np = 0;
   for(int i = start; i + LevelN <= s - 1; i++)
   {
      if(i - LevelN < 0) continue;
      bool ok = true;
      for(int k = i - LevelN; k <= i + LevelN && ok; k++) if(con[k] != con[i]) ok = false;
      for(int k = 1; k <= LevelN && ok; k++) if(!(l[i] < l[i - k]) || !(l[i] <= l[i + k])) ok = false;
      if(ok) { ArrayResize(piv, np + 1); piv[np++] = i; }
   }
   known = np;
   // Order by (low, index), as Python's sorted(pivots, key=(low[i], i)).
   for(int m = 1; m < np; m++)
   {
      int v = piv[m], q = m - 1;
      while(q >= 0 && (l[piv[q]] > l[v] || (l[piv[q]] == l[v] && piv[q] > v))) { piv[q + 1] = piv[q]; q--; }
      piv[q + 1] = v;
   }
   int pick = -1, pT0 = -1, pMembers = 0; double pL = 0;
   datetime newKeys[]; int nnew = 0;
   int k = 0;
   while(k < np)
   {
      int key = piv[k], t0 = piv[k], cnt = 1;
      double L = l[piv[k]];
      k++;
      while(k < np && l[piv[k]] - L <= d) { if(piv[k] > t0) t0 = piv[k]; cnt++; k++; }
      bool broken = false, departed = false;
      for(int j = t0 + 1; j < s; j++)
      {
         if(c[j] < L - d) broken = true;
         if(c[j] >= L + a) departed = true;
      }
      nlevels++;
      if(broken || !departed) continue;
      nlive++;
      if(!(o[s] >= L && c[s] < L - BreakDepthA * a)) continue;
      ArrayResize(newKeys, nnew + 1); newKeys[nnew++] = r[key].time;
      if(SRIsSpent(r[key].time)) continue;
      nbroken++;
      if(pick < 0 || L < pL || (L == pL && key > pick)) { pick = key; pL = L; pT0 = t0; pMembers = cnt; }
   }
   for(int q = 0; q < nnew; q++) SRSpend(newKeys[q]);
   if(!sameContract) return SR_ROLL;   // after the loop: bar s's breaks are recorded either way
   if(nlive == 0) return SR_NO_LEVEL;
   if(pick < 0) return SR_NO_BREAK;
   level = pL; keyTime = r[pick].time; t0Time = r[pT0].time; members = pMembers;
   entry = pL; stop = l[s]; risk = pL - l[s];
   if(risk < MinRiskA * a) return SR_MINRISK;
   if(ask >= pL) return SR_GAP;
   return SR_ORDER;
}

// ---- Trading modes (2 primary: buy stop at L; 3 control C1: buy stop at high(s)) ----

bool SRSelectPending()
{
   return (g_srTicket > 0 && OrderSelect(g_srTicket));
}

void SRLogCancel(string reason)
{
   if(reason == "touch_low") g_srCancelTouch++;
   else if(reason == "expired") g_srCancelExpired++;
   else if(reason == "replaced") g_srCancelReplaced++;
   else g_srCancelExternal++;
   if(FileWrite(g_srCancels, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), TimeToString(g_srOrdBar, TIME_DATE|TIME_SECONDS),
      DoubleToString(g_srOrdEntry, 2), DoubleToString(g_srOrdStop, 2), g_srOrdAge, reason,
      DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_BID), 2)) == 0)
      g_srErrors++;
   g_srTicket = 0;
}

void SRCancel(string reason)
{
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action = TRADE_ACTION_REMOVE;
   req.order  = g_srTicket;
   if(!OrderSend(req, res) || res.retcode != TRADE_RETCODE_DONE) { g_srCancelErrors++; return; }
   SRLogCancel(reason);
}

// First thing in OnTick: notice an order cancelled by the parent (window exit, flatten) and cancel on a touch of low(s).
void SROnTick()
{
   if(ReclaimMode < 2 || g_srTicket == 0) return;
   if(!SRSelectPending())
   {
      if(!PositionSelect(_Symbol)) SRLogCancel("external");   // a fill is reported by SROnFill on this tick
      return;
   }
   if(CancelOnLow && SymbolInfoDouble(_Symbol, SYMBOL_BID) <= g_srOrdStop) SRCancel("touch_low");
}

// Called by the parent when a new position appears (after FreezeTrendAtEntry).
void SROnFill()
{
   if(ReclaimMode < 2 || !PositionSelect(_Symbol)) return;
   g_srFilled++;
   if(FileWrite(g_srFills, TimeToString((datetime)PositionGetInteger(POSITION_TIME), TIME_DATE|TIME_SECONDS),
      DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN), 2), DoubleToString(PositionGetDouble(POSITION_SL), 2),
      TimeToString(g_srOrdBar, TIME_DATE|TIME_SECONDS), TimeToString(g_srOrdS, TIME_DATE|TIME_SECONDS),
      DoubleToString(g_srOrdEntry, 2), DoubleToString(g_srOrdStop, 2), DoubleToString(g_srOrdLevel, 2),
      TimeToString(g_srOrdKey, TIME_DATE|TIME_SECONDS), g_srOrdAge) == 0)
      g_srErrors++;
   g_srTicket = 0;
}

bool SRSend(double entry, double stop)
{
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action       = TRADE_ACTION_PENDING;
   req.symbol       = _Symbol;
   req.volume       = Lots;
   req.type         = ORDER_TYPE_BUY_STOP;
   req.price        = NormalizeDouble(entry, _Digits);
   req.sl           = NormalizeDouble(stop, _Digits);
   req.deviation    = Slippage;
   req.type_filling = ORDER_FILLING_RETURN;
   req.type_time    = ORDER_TIME_GTC;
   if(!OrderSend(req, res) || res.retcode != TRADE_RETCODE_DONE) { g_srSendErrors++; return false; }
   g_srTicket = res.order;
   return true;
}

// Called once per new bar, before the flatten / position / window checks: classifies bar s and records breaks.
void SROnNewBar(datetime barOpen)
{
   SRPruneSpent(barOpen);
   if(ReclaimMode >= 2 && SRSelectPending())
   {
      g_srOrdAge++;
      if(g_srOrdAge >= OrderLife) SRCancel("expired");
   }
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   g_srBar = barOpen;
   g_srSt = SRClassify(barOpen, ask, g_srS, g_srLevel, g_srKey, g_srT0, g_srMembers, g_srEntry, g_srStop, g_srRisk,
                       g_srAtr, g_srKnown, g_srLevels, g_srLive, g_srBroken, g_srRed, g_srSame);
}

// Called at the open of every eligible bar (flat, inside a trade window, before the flatten).
void SROnBar(datetime barOpen)
{
   if(g_srBar != barOpen) { g_srErrors++; return; }   // SROnNewBar must have run on this bar
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double open = iOpen(_Symbol, _Period, 0);
   g_srCounts[g_srSt]++;
   if(ReclaimMode >= 2) { SRTradeBar(barOpen, open, ask, bid); return; }
   if(FileWrite(g_srFile, TimeToString(barOpen, TIME_DATE|TIME_SECONDS),
      (g_srS > 0 ? TimeToString(g_srS, TIME_DATE|TIME_SECONDS) : ""), DoubleToString(open, 2), DoubleToString(ask, 2),
      DoubleToString(bid, 2), SR_NAMES[g_srSt], DoubleToString(g_srLevel, 2),
      (g_srKey > 0 ? TimeToString(g_srKey, TIME_DATE|TIME_SECONDS) : ""),
      (g_srT0 > 0 ? TimeToString(g_srT0, TIME_DATE|TIME_SECONDS) : ""), g_srMembers, DoubleToString(g_srAtr, 10),
      DoubleToString(g_srEntry, 2), DoubleToString(g_srStop, 2), DoubleToString(g_srRisk, 2), g_srKnown, g_srLevels,
      g_srLive, g_srBroken, (int)g_srRed, (int)g_srSame) == 0)
      g_srErrors++;
}

// Trading modes at an eligible bar: place (or replace) the buy stop when the classification says "order".
void SRTradeBar(datetime barOpen, double open, double ask, double bid)
{
   bool pending = SRSelectPending();
   string action = "no_order";
   double oEntry = 0, oStop = 0;
   if(g_srSt == SR_ORDER)
   {
      oEntry = (ReclaimMode == 2 ? g_srEntry : iHigh(_Symbol, _Period, 1));
      oStop = g_srStop;
      bool replaced = false;
      if(pending) { SRCancel("replaced"); replaced = true; }
      g_candleRange = oEntry - oStop;   // planned R in points, written to the trade ledger as candle_range
      LogTrendSignal();                 // signal bar s OHLC into the ledger; sets g_signalTime
      if(SRSend(oEntry, oStop))
      {
         g_srPlaced++;
         g_srOrdBar = barOpen; g_srOrdS = g_srS; g_srOrdKey = g_srKey; g_srOrdEntry = oEntry; g_srOrdStop = oStop;
         g_srOrdLevel = g_srLevel; g_srOrdAge = 0;
         action = (replaced ? "replaced" : "placed");
      }
      else action = "send_failed";
   }
   if(FileWrite(g_srFile, TimeToString(barOpen, TIME_DATE|TIME_SECONDS),
      (g_srS > 0 ? TimeToString(g_srS, TIME_DATE|TIME_SECONDS) : ""), DoubleToString(open, 2), DoubleToString(ask, 2),
      DoubleToString(bid, 2), SR_NAMES[g_srSt], DoubleToString(g_srLevel, 2),
      (g_srKey > 0 ? TimeToString(g_srKey, TIME_DATE|TIME_SECONDS) : ""),
      (g_srT0 > 0 ? TimeToString(g_srT0, TIME_DATE|TIME_SECONDS) : ""), g_srMembers, DoubleToString(g_srAtr, 10),
      DoubleToString(g_srEntry, 2), DoubleToString(g_srStop, 2), DoubleToString(g_srRisk, 2), g_srKnown, g_srLevels,
      g_srLive, g_srBroken, (int)g_srRed, (int)g_srSame, (int)pending, DoubleToString(oEntry, 2),
      DoubleToString(oStop, 2), action) == 0)
      g_srErrors++;
}
