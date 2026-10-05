// Q20 buy limit resting on a rising trendline (research only). Frozen protocol:
// docs/trendlines/TRENDLINE_LIMIT_PROTOCOL.md. Mirrors python/trendline_limit.py, which builds on the frozen
// Q14 line code (python/trendline_support.py): consecutive higher M30 swing lows (N=5) in a one-week window
// (bar t's session + 5 previous), anchors >= 10 bars apart, line rising >= 0.02 x A per bar, valid, intact and
// departed. A = mean of the 14 true ranges before bar t (same contract), D = 0.5 x A. Evaluated at the open of
// every eligible bar t (flat, inside a trade window, before the flatten) from closed bars only.
// Requires contract_rolls.mqh (CR_DATE/CR_ID). Floating-point expressions follow the Python order.
//
// LimitMode 1 = classify + log only (no orders; output identical to the verified classify-only run).
// LimitMode 2 = primary: buy limit at the nearest armed line below the ask. A fill consumes that line's episode;
//               the line re-arms after a close >= line + A(t) at or after the fill bar (judged with A at bar t).
// LimitMode 3 = control C1: bars where the classification (fills ignored) has a line below the ask; limit at
//               open - delta x A with delta from LimitDeltaFile. C1 re-arms after a fill at P on a close >= P + A(t).
// LimitMode 4 = control C2: as C1 on every eligible bar with a valid A, whether or not a line exists.
// LimitTickOffset moves limit and stop down by that many ticks (trade-through sensitivity).

input int    LimitMode       = 1;     // 1 classify only, 2 primary, 3 control C1, 4 control C2
input int    LimitN          = 5;     // swing-low strength
input int    LimitSessions   = 5;     // previous sessions in the window
input int    LimitMinSep     = 10;    // minimum anchor separation, bars
input double LimitMinSlope   = 0.02;  // minimum rise per bar, x A
input double LimitStopA      = 0.5;   // stop distance below the limit, x A
input int    LimitTickOffset = 0;     // limit and stop this many ticks lower
input string LimitDeltaFile  = "";    // C1/C2 delta table in Common\Files: unix_time,delta

#define TL_BARS 1500
#define TL_EPS  1e-9                  // same constant as python/trendline_limit.py

enum TLStatus { TL_ORDER=0, TL_NO_LINE=1, TL_ABOVE=2, TL_MISSING=3, TL_ROLL=4, TL_ATR=5 };
string TL_NAMES[6] = {"order","no_line","above_price","missing_history","contract_roll","invalid_atr"};
int    g_tlFile = INVALID_HANDLE, g_tlFills = INVALID_HANDLE;
int    g_tlErrors = 0, g_tlSendErrors = 0, g_tlCancelErrors = 0, g_tlNoDelta = 0, g_tlPlaced = 0, g_tlFilled = 0;
int    g_tlCounts[6];
// Consumed episodes (primary): line anchors and the bar of each fill.
datetime g_cA1[], g_cA2[], g_cFillBar[];
int      g_nc = 0;
// Control arming: the latest control fill.
bool     g_ctlFilled = false;
double   g_ctlFillPrice = 0;
datetime g_ctlFillBar = 0;
// The order resting now (set on placement, read on a fill).
datetime g_ordBar = 0, g_ordA1 = 0, g_ordA2 = 0;
double   g_ordLimit = 0, g_ordStop = 0, g_ordLine = 0, g_ordDelta = 0;
// Control delta table.
datetime g_dT[];
double   g_dV[];
int      g_nd = 0;

int TLContract(datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   int ymd = d.year * 10000 + d.mon * 100 + d.day;
   int id = -1;
   for(int k = 0; k < CR_COUNT && CR_DATE[k] <= ymd; k++) id = CR_ID[k];
   return id;
}

double TLLine(const double &l[], int i, int j, double k)
{
   return l[i] + (l[j] - l[i]) * (k - i) / (j - i);
}

double TLFloorTick(double x, double tick)
{
   return MathFloor(x / tick + TL_EPS) * tick;
}

bool TLLoadDeltas()
{
   int f = FileOpen(LimitDeltaFile, FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(f == INVALID_HANDLE) return false;
   FileReadString(f); FileReadString(f);                       // header
   ArrayResize(g_dT, 200000, 200000); ArrayResize(g_dV, 200000, 200000);
   while(!FileIsEnding(f))
   {
      string a = FileReadString(f), b = FileReadString(f);
      if(a == "") break;
      if(g_nd >= ArraySize(g_dT)) { ArrayResize(g_dT, g_nd + 50000); ArrayResize(g_dV, g_nd + 50000); }
      g_dT[g_nd] = (datetime)StringToInteger(a);
      g_dV[g_nd] = StringToDouble(b);
      g_nd++;
   }
   FileClose(f);
   for(int k = 1; k < g_nd; k++) if(g_dT[k] <= g_dT[k - 1]) return false;   // must be sorted, unique
   return g_nd > 0;
}

bool TLDelta(datetime t, double &delta)
{
   int lo = 0, hi = g_nd - 1;
   while(lo <= hi)
   {
      int mid = (lo + hi) / 2;
      if(g_dT[mid] == t) { delta = g_dV[mid]; return true; }
      if(g_dT[mid] < t) lo = mid + 1; else hi = mid - 1;
   }
   return false;
}

bool TLInit()
{
   if(LimitMode < 1 || LimitMode > 4 || LimitN < 1 || LimitSessions < 0 || LimitMinSep < 1 || LimitStopA <= 0
      || LimitTickOffset < 0) return false;
   if(LimitMode >= 3 && !TLLoadDeltas()) { Print("Q20: delta table missing or invalid: ", LimitDeltaFile); return false; }
   g_tlFile = FileOpen(g_runTag + "_limit.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(g_tlFile == INVALID_HANDLE) return false;
   if(LimitMode == 1)
      FileWrite(g_tlFile, "bar_time", "open", "ask", "bid", "status", "line", "limit", "stop", "anchor1_time",
                "anchor2_time", "atr", "known_pivots", "lines_armed", "lines_below");
   else
   {
      FileWrite(g_tlFile, "bar_time", "open", "ask", "bid", "status", "line", "limit", "stop", "anchor1_time",
                "anchor2_time", "atr", "known_pivots", "lines_armed", "lines_below", "delta", "action");
      g_tlFills = FileOpen(g_runTag + "_fills.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
      if(g_tlFills == INVALID_HANDLE) return false;
      FileWrite(g_tlFills, "fill_time", "fill_price", "sl", "order_bar", "order_limit", "order_stop", "line",
                "anchor1_time", "anchor2_time", "delta");
   }
   return true;
}

void TLDeinit()
{
   if(g_tlFile != INVALID_HANDLE) FileClose(g_tlFile);
   if(g_tlFills != INVALID_HANDLE) FileClose(g_tlFills);
   g_tlFile = INVALID_HANDLE; g_tlFills = INVALID_HANDLE;
   int f = FileOpen(g_runTag + "_limit_stats.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(f == INVALID_HANDLE) return;
   if(LimitMode == 1)
   {
      FileWrite(f, "limit_mode", "log_errors", "tick", "order", "no_line", "above_price", "missing_history",
                "contract_roll", "invalid_atr");
      FileWrite(f, LimitMode, g_tlErrors, DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE), 10),
                g_tlCounts[0], g_tlCounts[1], g_tlCounts[2], g_tlCounts[3], g_tlCounts[4], g_tlCounts[5]);
   }
   else
   {
      FileWrite(f, "limit_mode", "stop_a", "tick_offset", "log_errors", "send_errors", "cancel_errors", "no_delta",
                "placed", "filled", "deltas_loaded", "tick", "order", "no_line", "above_price", "missing_history",
                "contract_roll", "invalid_atr");
      FileWrite(f, LimitMode, LimitStopA, LimitTickOffset, g_tlErrors, g_tlSendErrors, g_tlCancelErrors, g_tlNoDelta,
                g_tlPlaced, g_tlFilled, g_nd, DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE), 10),
                g_tlCounts[0], g_tlCounts[1], g_tlCounts[2], g_tlCounts[3], g_tlCounts[4], g_tlCounts[5]);
   }
   FileClose(f);
}

// Latest consumed-episode fill bar for a line (0 = never filled).
datetime TLConsumedBar(datetime a1, datetime a2)
{
   datetime best = 0;
   for(int q = 0; q < g_nc; q++) if(g_cA1[q] == a1 && g_cA2[q] == a2 && g_cFillBar[q] > best) best = g_cFillBar[q];
   return best;
}

// The bar t classification. Closed bars only (shift >= 1); bar t is the virtual index n, one past the array.
// consume: skip primary lines whose episode was consumed by a fill and has not re-armed.
// ctlArmed (out): control arming at bar t from the latest control fill.
int TLClassify(datetime barOpen, double ask, bool consume, double &line, double &limit, double &stop,
               datetime &a1, datetime &a2, double &atr, int &known, int &armed, int &below, bool &ctlArmed)
{
   line = 0; limit = 0; stop = 0; a1 = 0; a2 = 0; atr = 0; known = 0; armed = 0; below = 0; ctlArmed = true;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_M30, 1, TL_BARS, r);
   if(n < 50) return TL_MISSING;
   int s = n;                                    // bar t
   double l[], c[], h[]; int con[]; datetime day[];
   ArrayResize(l, n); ArrayResize(c, n); ArrayResize(h, n); ArrayResize(con, n); ArrayResize(day, n);
   for(int k = 0; k < n; k++)
   {
      h[k] = r[k].high; l[k] = r[k].low; c[k] = r[k].close;
      day[k] = r[k].time - (r[k].time % 86400);
      con[k] = TLContract(r[k].time);
   }
   int conT = TLContract(barOpen);
   datetime dayT = barOpen - (barOpen % 86400);
   // Window: first bar of the LimitSessions-th previous distinct session date before bar t's date.
   int dates = 1, start = -1;
   datetime prev = dayT;
   for(int k = s - 1; k >= 0; k--)
   {
      if(day[k] != prev)
      {
         dates++;
         if(dates > LimitSessions + 1) { start = k + 1; break; }
         prev = day[k];
      }
   }
   // The copy reached the first bar of history and holds exactly enough sessions: the window starts there.
   if(start < 0 && n < TL_BARS && dates == LimitSessions + 1) start = 0;
   if(start < 0) return TL_MISSING;              // copied history too short to see the window start
   for(int k = start; k < s; k++) if(con[k] != conT) return TL_ROLL;
   if(s - 14 < 1) return TL_ATR;
   double sum = 0;
   for(int k = s - 14; k <= s - 1; k++)
   {
      if(con[k] != conT) return TL_ATR;
      double tr = h[k] - l[k];
      if(con[k - 1] == con[k]) tr = MathMax(tr, MathMax(MathAbs(h[k] - c[k - 1]), MathAbs(l[k] - c[k - 1])));
      sum += tr;
   }
   double a = sum / 14.0;
   if(a <= 0) return TL_ATR;
   atr = a;
   double d = 0.5 * a;
   // Control arming: a close >= P + A(t) at or after the latest control fill's bar (within the copied bars).
   if(g_ctlFilled)
   {
      ctlArmed = false;
      for(int k = 0; k < s && !ctlArmed; k++) if(r[k].time >= g_ctlFillBar && c[k] >= g_ctlFillPrice + a) ctlArmed = true;
   }
   // Known swing lows: pivot bar in the window, confirmed (i + N closed) before bar t opens.
   int piv[]; int np = 0;
   for(int i = start; i + LimitN <= s - 1; i++)
   {
      if(i - LimitN < 0) continue;
      bool ok = true;
      for(int k = i - LimitN; k <= i + LimitN && ok; k++) if(con[k] != con[i]) ok = false;
      for(int k = 1; k <= LimitN && ok; k++) if(!(l[i] < l[i - k]) || !(l[i] <= l[i + k])) ok = false;
      if(ok) { ArrayResize(piv, np + 1); piv[np++] = i; }
   }
   known = np;
   // Armed lines (valid, intact, departed, episode not consumed); keep the highest value strictly below the ask.
   int pi = -1, pj = -1; double pv = 0;
   for(int m = 1; m < np; m++)
   {
      int j = piv[m], i = -1;
      for(int q = m - 1; q >= 0; q--) if(l[piv[q]] < l[j]) { i = piv[q]; break; }
      if(i < 0 || j - i < LimitMinSep) continue;
      if(!((l[j] - l[i]) / (j - i) >= LimitMinSlope * a)) continue;
      bool valid = true;
      for(int k = i + 1; k < j && valid; k++) if(l[k] < TLLine(l, i, j, k) - d) valid = false;
      if(!valid) continue;
      bool broken = false, departed = false;
      for(int k = j + 1; k < s; k++)
      {
         double lv = TLLine(l, i, j, k);
         if(c[k] < lv - d) broken = true;
         if(c[k] >= lv + a) departed = true;
      }
      if(broken || !departed) continue;
      if(consume)
      {
         datetime fb = TLConsumedBar(r[i].time, r[j].time);
         if(fb > 0)
         {
            bool rearmed = false;
            for(int k = 0; k < s && !rearmed; k++) if(r[k].time >= fb && c[k] >= TLLine(l, i, j, k) + a) rearmed = true;
            if(!rearmed) continue;
         }
      }
      armed++;
      double v = TLLine(l, i, j, s);
      if(!(v < ask)) continue;
      below++;
      if(pi < 0 || v > pv || (v == pv && (j > pj || (j == pj && i > pi)))) { pi = i; pj = j; pv = v; }
   }
   if(armed == 0) return TL_NO_LINE;
   if(pi < 0) return TL_ABOVE;
   double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   line = pv;
   limit = TLFloorTick(pv, tick);
   stop = TLFloorTick(limit - LimitStopA * a, tick);
   a1 = r[pi].time; a2 = r[pj].time;
   return TL_ORDER;
}

void TLCancel()
{
   for(int k = OrdersTotal() - 1; k >= 0; k--)
   {
      ulong ticket = OrderGetTicket(k);
      if(ticket == 0 || !OrderSelect(ticket)) continue;
      if((int)OrderGetInteger(ORDER_TYPE) != ORDER_TYPE_BUY_LIMIT) continue;
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action = TRADE_ACTION_REMOVE;
      req.order  = ticket;
      if(!OrderSend(req, res) || res.retcode != TRADE_RETCODE_DONE) g_tlCancelErrors++;
   }
}

bool TLSend(double limit, double stop)
{
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action       = TRADE_ACTION_PENDING;
   req.symbol       = _Symbol;
   req.volume       = Lots;
   req.type         = ORDER_TYPE_BUY_LIMIT;
   req.price        = NormalizeDouble(limit, _Digits);
   req.sl           = NormalizeDouble(stop, _Digits);
   req.deviation    = Slippage;
   req.type_filling = ORDER_FILLING_RETURN;
   req.type_time    = ORDER_TIME_GTC;
   if(!OrderSend(req, res) || res.retcode != TRADE_RETCODE_DONE) { g_tlSendErrors++; return false; }
   return true;
}

// Called by the parent EA when a new position appears.
void TLOnFill()
{
   if(LimitMode < 2 || !PositionSelect(_Symbol)) return;
   datetime ft = (datetime)PositionGetInteger(POSITION_TIME);
   double fp = PositionGetDouble(POSITION_PRICE_OPEN), sl = PositionGetDouble(POSITION_SL);
   datetime fillBar = ft - (ft % 1800);
   g_tlFilled++;
   if(LimitMode == 2)
   {
      ArrayResize(g_cA1, g_nc + 1); ArrayResize(g_cA2, g_nc + 1); ArrayResize(g_cFillBar, g_nc + 1);
      g_cA1[g_nc] = g_ordA1; g_cA2[g_nc] = g_ordA2; g_cFillBar[g_nc] = fillBar; g_nc++;
   }
   else { g_ctlFilled = true; g_ctlFillPrice = fp; g_ctlFillBar = fillBar; }
   if(FileWrite(g_tlFills, TimeToString(ft, TIME_DATE|TIME_SECONDS), DoubleToString(fp, 2), DoubleToString(sl, 2),
      TimeToString(g_ordBar, TIME_DATE|TIME_SECONDS), DoubleToString(g_ordLimit, 2), DoubleToString(g_ordStop, 2),
      DoubleToString(g_ordLine, 10), (g_ordA1 > 0 ? TimeToString(g_ordA1, TIME_DATE|TIME_SECONDS) : ""),
      (g_ordA2 > 0 ? TimeToString(g_ordA2, TIME_DATE|TIME_SECONDS) : ""), DoubleToString(g_ordDelta, 10)) == 0)
      g_tlErrors++;
}

// Called at the open of every eligible bar (flat, inside a trade window, before the flatten).
void TLOnBar(datetime barOpen)
{
   if(LimitMode >= 2) TLCancel();
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double open = iOpen(_Symbol, _Period, 0);
   double line, limit, stop, atr; datetime a1, a2; int known, armed, below; bool ctlArmed;
   int st = TLClassify(barOpen, ask, LimitMode == 2, line, limit, stop, a1, a2, atr, known, armed, below, ctlArmed);
   g_tlCounts[st]++;
   if(LimitMode == 1)
   {
      if(FileWrite(g_tlFile, TimeToString(barOpen, TIME_DATE|TIME_SECONDS), DoubleToString(open, 2),
         DoubleToString(ask, 2), DoubleToString(bid, 2), TL_NAMES[st], DoubleToString(line, 10), DoubleToString(limit, 2),
         DoubleToString(stop, 2), (a1 > 0 ? TimeToString(a1, TIME_DATE|TIME_SECONDS) : ""),
         (a2 > 0 ? TimeToString(a2, TIME_DATE|TIME_SECONDS) : ""), DoubleToString(atr, 10), known, armed, below) == 0)
         g_tlErrors++;
      return;
   }
   double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double delta = 0, oLimit = 0, oStop = 0;
   string action = "no_order";
   bool want = false;
   if(LimitMode == 2 && st == TL_ORDER)
   {
      oLimit = limit - LimitTickOffset * tick;
      oStop = stop - LimitTickOffset * tick;
      want = true;
   }
   else if(LimitMode >= 3 && (st == TL_ORDER || (LimitMode == 4 && (st == TL_NO_LINE || st == TL_ABOVE))))
   {
      if(!ctlArmed) action = "unarmed";
      else if(!TLDelta(barOpen, delta)) { action = "no_delta"; g_tlNoDelta++; }
      else
      {
         double base = TLFloorTick(open - delta * atr, tick);
         oLimit = base - LimitTickOffset * tick;
         oStop = TLFloorTick(base - LimitStopA * atr, tick) - LimitTickOffset * tick;
         if(oLimit < ask) want = true; else action = "above_price";
      }
   }
   if(want)
   {
      g_candleRange = oLimit - oStop;   // planned R in points, written to the trade ledger as candle_range
      g_signalTime = barOpen;
      g_ordBar = barOpen; g_ordLimit = oLimit; g_ordStop = oStop; g_ordLine = line; g_ordDelta = delta;
      g_ordA1 = a1; g_ordA2 = a2;
      if(TLSend(oLimit, oStop)) { action = "placed"; g_tlPlaced++; }
      else action = "send_failed";
   }
   if(FileWrite(g_tlFile, TimeToString(barOpen, TIME_DATE|TIME_SECONDS), DoubleToString(open, 2),
      DoubleToString(ask, 2), DoubleToString(bid, 2), TL_NAMES[st], DoubleToString(line, 10), DoubleToString(oLimit, 2),
      DoubleToString(oStop, 2), (a1 > 0 ? TimeToString(a1, TIME_DATE|TIME_SECONDS) : ""),
      (a2 > 0 ? TimeToString(a2, TIME_DATE|TIME_SECONDS) : ""), DoubleToString(atr, 10), known, armed, below,
      DoubleToString(delta, 10), action) == 0)
      g_tlErrors++;
}
