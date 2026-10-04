// Q20 buy limit resting on a rising trendline (research only). Frozen protocol:
// docs/trendlines/TRENDLINE_LIMIT_PROTOCOL.md. Mirrors python/trendline_limit.py, which builds on the frozen
// Q14 line code (python/trendline_support.py): consecutive higher M30 swing lows (N=5) in a one-week window
// (bar t's session + 5 previous), anchors >= 10 bars apart, line rising >= 0.02 x A per bar, valid, intact and
// departed. A = mean of the 14 true ranges before bar t (same contract), D = 0.5 x A. Evaluated at the open of
// every eligible bar t from closed bars only. Requires contract_rolls.mqh (CR_DATE/CR_ID).
// Floating-point expressions follow the Python order so line values agree exactly.
//
// LimitMode 1 = classify + log only: no order is ever sent. The trading modes are added after the
// classify-only check (protocol: "Verification (before any trading run)").

input int    LimitMode     = 1;     // 1 classify + log only (no orders)
input int    LimitN        = 5;     // swing-low strength
input int    LimitSessions = 5;     // previous sessions in the window
input int    LimitMinSep   = 10;    // minimum anchor separation, bars
input double LimitMinSlope = 0.02;  // minimum rise per bar, x A
input double LimitStopA    = 0.5;   // stop distance below the limit, x A

#define TL_BARS 1500
#define TL_EPS  1e-9                // same constant as python/trendline_limit.py

enum TLStatus { TL_ORDER=0, TL_NO_LINE=1, TL_ABOVE=2, TL_MISSING=3, TL_ROLL=4, TL_ATR=5 };
string TL_NAMES[6] = {"order","no_line","above_price","missing_history","contract_roll","invalid_atr"};
int    g_tlFile = INVALID_HANDLE;
int    g_tlErrors = 0;
int    g_tlCounts[6];

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

bool TLInit()
{
   if(LimitMode != 1 || LimitN < 1 || LimitSessions < 0 || LimitMinSep < 1 || LimitStopA <= 0) return false;
   g_tlFile = FileOpen(g_runTag + "_limit.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(g_tlFile == INVALID_HANDLE) return false;
   FileWrite(g_tlFile, "bar_time", "open", "ask", "bid", "status", "line", "limit", "stop", "anchor1_time",
             "anchor2_time", "atr", "known_pivots", "lines_armed", "lines_below");
   return true;
}

void TLDeinit()
{
   if(g_tlFile != INVALID_HANDLE) FileClose(g_tlFile);
   g_tlFile = INVALID_HANDLE;
   int f = FileOpen(g_runTag + "_limit_stats.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(f == INVALID_HANDLE) return;
   FileWrite(f, "limit_mode", "log_errors", "tick", "order", "no_line", "above_price", "missing_history",
             "contract_roll", "invalid_atr");
   FileWrite(f, LimitMode, g_tlErrors, DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE), 10),
             g_tlCounts[0], g_tlCounts[1], g_tlCounts[2], g_tlCounts[3], g_tlCounts[4], g_tlCounts[5]);
   FileClose(f);
}

// The order the primary would rest during the bar opening at barOpen. Closed bars only (shift >= 1);
// bar t is the virtual index n, one past the copied array.
int TLClassify(datetime barOpen, double ask, double &line, double &limit, double &stop, datetime &a1, datetime &a2,
               double &atr, int &known, int &armed, int &below)
{
   line = 0; limit = 0; stop = 0; a1 = 0; a2 = 0; atr = 0; known = 0; armed = 0; below = 0;
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
   // Armed lines (valid, intact, departed); keep the highest value strictly below the ask.
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

// Called at the open of every eligible bar (flat, inside a trade window, before the flatten).
void TLOnBar(datetime barOpen)
{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double line, limit, stop, atr; datetime a1, a2; int known, armed, below;
   int st = TLClassify(barOpen, ask, line, limit, stop, a1, a2, atr, known, armed, below);
   g_tlCounts[st]++;
   if(FileWrite(g_tlFile, TimeToString(barOpen, TIME_DATE|TIME_SECONDS), DoubleToString(iOpen(_Symbol, _Period, 0), 2),
      DoubleToString(ask, 2), DoubleToString(bid, 2), TL_NAMES[st], DoubleToString(line, 10), DoubleToString(limit, 2),
      DoubleToString(stop, 2), (a1 > 0 ? TimeToString(a1, TIME_DATE|TIME_SECONDS) : ""),
      (a2 > 0 ? TimeToString(a2, TIME_DATE|TIME_SECONDS) : ""), DoubleToString(atr, 10), known, armed, below) == 0)
      g_tlErrors++;
}
