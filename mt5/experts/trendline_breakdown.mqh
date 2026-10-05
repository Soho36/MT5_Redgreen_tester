// Q21 short the breakdown of a rising trendline (research only). Frozen protocol:
// docs/trendlines/BREAKDOWN_SHORT_PROTOCOL.md. Mirrors python/trendline_breakdown.py, which builds on the frozen
// Q14/Q20 line code: consecutive higher M30 swing lows (N=5) in a one-week window, anchors >= 10 bars apart, line
// rising >= 0.02 x A per bar, valid, intact and departed - all evaluated at the open of bar s = the last closed bar,
// from bars before s. A = mean of the 14 true ranges before s (same contract), D = 0.5 x A.
// A line is live if no close since its first departure (close >= V + A) was below V - BreakDepthA x A. Bar s breaks
// it if close(s) < V(s) - BreakDepthA x A. A red s that breaks a live line -> sell stop at low(s), stop high(s), for
// bar t only. Spending is stateful: A is re-measured every bar, so a break is recorded at the bar it happens (with
// that bar's A) and the line stays spent - one signal per line. TBOnNewBar classifies every new bar (eligible or not)
// and records breaks; TBOnBar logs / acts at eligible bars t (flat, inside a trade window, before the flatten).
// Requires contract_rolls.mqh (CR_DATE/CR_ID). Floating-point expressions follow the Python order.
//
// BreakMode 1 = classify + log only (no orders). The trading modes are added after this log is verified.

input int    BreakMode     = 1;     // 1 classify only
input double BreakDepthA   = 0.0;   // break threshold below the line, x A (primary 0, S1 0.5)
input int    BreakN        = 5;     // swing-low strength
input int    BreakSessions = 5;     // previous sessions in the window
input int    BreakMinSep   = 10;    // minimum anchor separation, bars
input double BreakMinSlope = 0.02;  // minimum rise per bar, x A

#define TB_BARS 1500

enum TBStatus { TB_ORDER=0, TB_GAP=1, TB_NOT_RED=2, TB_NO_BREAK=3, TB_NO_LINE=4, TB_MISSING=5, TB_ROLL=6, TB_ATR=7 };
string TB_NAMES[8] = {"order","gap_below","not_red","no_break","no_line","missing_history","contract_roll","invalid_atr"};
int    g_tbFile = INVALID_HANDLE;
int    g_tbErrors = 0;
int    g_tbCounts[8];
// Spent lines (anchor times), pruned once anchor 1 is far outside any window.
datetime g_spA1[], g_spA2[];
int      g_nsp = 0;
// The latest new-bar classification, read by TBOnBar on the same tick.
datetime g_tbBar = 0, g_tbS = 0, g_tbA1 = 0, g_tbA2 = 0;
double   g_tbLine = 0, g_tbEntry = 0, g_tbStop = 0, g_tbAtr = 0;
int      g_tbSt = TB_MISSING, g_tbKnown = 0, g_tbArmed = 0, g_tbLive = 0, g_tbBroken = 0;
bool     g_tbRed = false, g_tbSame = false;

int TBContract(datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   int ymd = d.year * 10000 + d.mon * 100 + d.day;
   int id = -1;
   for(int k = 0; k < CR_COUNT && CR_DATE[k] <= ymd; k++) id = CR_ID[k];
   return id;
}

bool TBIsSpent(datetime a1, datetime a2)
{
   for(int q = 0; q < g_nsp; q++) if(g_spA1[q] == a1 && g_spA2[q] == a2) return true;
   return false;
}

void TBSpend(datetime a1, datetime a2)
{
   if(TBIsSpent(a1, a2)) return;
   ArrayResize(g_spA1, g_nsp + 1, 256); ArrayResize(g_spA2, g_nsp + 1, 256);
   g_spA1[g_nsp] = a1; g_spA2[g_nsp] = a2; g_nsp++;
}

void TBPruneSpent(datetime now)
{
   int w = 0;
   for(int q = 0; q < g_nsp; q++)
      if(g_spA1[q] >= now - 30 * 86400) { g_spA1[w] = g_spA1[q]; g_spA2[w] = g_spA2[q]; w++; }
   g_nsp = w;
}

double TBLine(const double &l[], int i, int j, double k)
{
   return l[i] + (l[j] - l[i]) * (k - i) / (j - i);
}

bool TBInit()
{
   if(BreakMode != 1 || !MathIsValidNumber(BreakDepthA) || BreakDepthA < 0 || BreakN < 1 || BreakSessions < 0
      || BreakMinSep < 1) return false;
   g_tbFile = FileOpen(g_runTag + "_breakdown.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(g_tbFile == INVALID_HANDLE) return false;
   FileWrite(g_tbFile, "bar_time", "s_time", "open", "ask", "bid", "status", "line", "entry", "stop", "anchor1_time",
             "anchor2_time", "atr", "known_pivots", "lines_armed", "lines_live", "lines_broken", "s_red",
             "same_contract");
   return true;
}

void TBDeinit()
{
   if(g_tbFile != INVALID_HANDLE) FileClose(g_tbFile);
   g_tbFile = INVALID_HANDLE;
   int f = FileOpen(g_runTag + "_breakdown_stats.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(f == INVALID_HANDLE) return;
   FileWrite(f, "break_mode", "break_depth_a", "log_errors", "tick", "order", "gap_below", "not_red", "no_break",
             "no_line", "missing_history", "contract_roll", "invalid_atr");
   FileWrite(f, BreakMode, BreakDepthA, g_tbErrors, DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE), 10),
             g_tbCounts[0], g_tbCounts[1], g_tbCounts[2], g_tbCounts[3], g_tbCounts[4], g_tbCounts[5], g_tbCounts[6],
             g_tbCounts[7]);
   FileClose(f);
}

// Bar t classification. r[] holds closed bars only (shift >= 1); bar s = n - 1 is the breakdown candidate and every
// line is judged from bars before s, as at the open of s. Lines bar s breaks are added to the spent list.
int TBClassify(datetime barOpen, double bid, datetime &sTime, double &line, double &entry, double &stop,
               datetime &a1, datetime &a2, double &atr, int &known, int &armed, int &live, int &broken,
               bool &sRed, bool &sameContract)
{
   sTime = 0; line = 0; entry = 0; stop = 0; a1 = 0; a2 = 0; atr = 0; known = 0; armed = 0; live = 0; broken = 0;
   sRed = false; sameContract = false;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_M30, 1, TB_BARS, r);
   if(n < 1) return TB_MISSING;
   int s = n - 1;
   double o[], l[], c[], h[]; int con[]; datetime day[];
   ArrayResize(o, n); ArrayResize(l, n); ArrayResize(c, n); ArrayResize(h, n); ArrayResize(con, n); ArrayResize(day, n);
   for(int k = 0; k < n; k++)
   {
      o[k] = r[k].open; h[k] = r[k].high; l[k] = r[k].low; c[k] = r[k].close;
      day[k] = r[k].time - (r[k].time % 86400);
      con[k] = TBContract(r[k].time);
   }
   sTime = r[s].time;
   sRed = (c[s] < o[s]);
   sameContract = (con[s] == TBContract(barOpen));
   if(n < 50) return TB_MISSING;
   // Window: first bar of the BreakSessions-th previous distinct session date before bar s's date.
   int dates = 1, start = -1;
   datetime prev = day[s];
   for(int k = s - 1; k >= 0; k--)
   {
      if(day[k] != prev)
      {
         dates++;
         if(dates > BreakSessions + 1) { start = k + 1; break; }
         prev = day[k];
      }
   }
   // The copy reached the first bar of history and holds exactly enough sessions: the window starts there.
   if(start < 0 && n < TB_BARS && dates == BreakSessions + 1) start = 0;
   if(start < 0) return TB_MISSING;
   for(int k = start; k <= s; k++) if(con[k] != con[s]) return TB_ROLL;
   if(s - 14 < 1) return TB_ATR;
   double sum = 0;
   for(int k = s - 14; k <= s - 1; k++)
   {
      if(con[k] != con[s]) return TB_ATR;
      double tr = h[k] - l[k];
      if(con[k - 1] == con[k]) tr = MathMax(tr, MathMax(MathAbs(h[k] - c[k - 1]), MathAbs(l[k] - c[k - 1])));
      sum += tr;
   }
   double a = sum / 14.0;
   if(a <= 0) return TB_ATR;
   atr = a;
   double d = 0.5 * a;
   // Known swing lows: pivot bar in the window, confirmed (i + N closed) before bar s opens.
   int piv[]; int np = 0;
   for(int i = start; i + BreakN <= s - 1; i++)
   {
      if(i - BreakN < 0) continue;
      bool ok = true;
      for(int k = i - BreakN; k <= i + BreakN && ok; k++) if(con[k] != con[i]) ok = false;
      for(int k = 1; k <= BreakN && ok; k++) if(!(l[i] < l[i - k]) || !(l[i] <= l[i + k])) ok = false;
      if(ok) { ArrayResize(piv, np + 1); piv[np++] = i; }
   }
   known = np;
   // Armed lines (valid, intact, departed before s); live ones (no close below V - BreakDepthA x A after the first
   // departure); broken by s. Report the highest V(s) among the broken.
   int pi = -1, pj = -1; double pv = 0;
   datetime newA1[], newA2[]; int nnew = 0;
   for(int m = 1; m < np; m++)
   {
      int j = piv[m], i = -1;
      for(int q = m - 1; q >= 0; q--) if(l[piv[q]] < l[j]) { i = piv[q]; break; }
      if(i < 0 || j - i < BreakMinSep) continue;
      if(!((l[j] - l[i]) / (j - i) >= BreakMinSlope * a)) continue;
      bool valid = true;
      for(int k = i + 1; k < j && valid; k++) if(l[k] < TBLine(l, i, j, k) - d) valid = false;
      if(!valid) continue;
      bool isBroken = false, departed = false, spent = false;
      for(int k = j + 1; k < s; k++)
      {
         double lv = TBLine(l, i, j, k);
         if(c[k] < lv - d) isBroken = true;
         if(departed && c[k] < lv - BreakDepthA * a) spent = true;
         if(c[k] >= lv + a) departed = true;
      }
      if(isBroken || !departed) continue;
      armed++;
      if(spent) continue;
      double v = TBLine(l, i, j, s);
      bool breaks = (c[s] < v - BreakDepthA * a);
      if(breaks) { ArrayResize(newA1, nnew + 1); ArrayResize(newA2, nnew + 1); newA1[nnew] = r[i].time; newA2[nnew] = r[j].time; nnew++; }
      if(TBIsSpent(r[i].time, r[j].time)) continue;
      live++;
      if(!breaks) continue;
      broken++;
      if(pi < 0 || v > pv || (v == pv && (j > pj || (j == pj && i > pi)))) { pi = i; pj = j; pv = v; }
   }
   for(int q = 0; q < nnew; q++) TBSpend(newA1[q], newA2[q]);
   if(!sameContract) return TB_ROLL;              // after the loop: bar s's breaks are recorded either way
   if(armed == 0) return TB_NO_LINE;
   if(pi < 0) return TB_NO_BREAK;
   line = pv; a1 = r[pi].time; a2 = r[pj].time;
   if(!sRed) return TB_NOT_RED;
   entry = l[s]; stop = h[s];
   if(bid <= entry) return TB_GAP;
   return TB_ORDER;
}

// Called once per new bar, before the flatten / position / window checks: classifies bar s and records breaks.
void TBOnNewBar(datetime barOpen)
{
   TBPruneSpent(barOpen);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   g_tbBar = barOpen;
   g_tbSt = TBClassify(barOpen, bid, g_tbS, g_tbLine, g_tbEntry, g_tbStop, g_tbA1, g_tbA2, g_tbAtr, g_tbKnown,
                       g_tbArmed, g_tbLive, g_tbBroken, g_tbRed, g_tbSame);
}

// Called at the open of every eligible bar (flat, inside a trade window, before the flatten).
void TBOnBar(datetime barOpen)
{
   if(g_tbBar != barOpen) { g_tbErrors++; return; }   // TBOnNewBar must have run on this bar
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double open = iOpen(_Symbol, _Period, 0);
   g_tbCounts[g_tbSt]++;
   if(FileWrite(g_tbFile, TimeToString(barOpen, TIME_DATE|TIME_SECONDS),
      (g_tbS > 0 ? TimeToString(g_tbS, TIME_DATE|TIME_SECONDS) : ""), DoubleToString(open, 2), DoubleToString(ask, 2),
      DoubleToString(bid, 2), TB_NAMES[g_tbSt], DoubleToString(g_tbLine, 10), DoubleToString(g_tbEntry, 2),
      DoubleToString(g_tbStop, 2), (g_tbA1 > 0 ? TimeToString(g_tbA1, TIME_DATE|TIME_SECONDS) : ""),
      (g_tbA2 > 0 ? TimeToString(g_tbA2, TIME_DATE|TIME_SECONDS) : ""), DoubleToString(g_tbAtr, 10), g_tbKnown,
      g_tbArmed, g_tbLive, g_tbBroken, (int)g_tbRed, (int)g_tbSame) == 0)
      g_tbErrors++;
}
