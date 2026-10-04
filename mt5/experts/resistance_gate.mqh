// Q15/Q17 falling-trendline resistance gate (research only).
// Mirrors python/trendline_resistance.py (frozen docs/trendlines/RESISTANCE_PROTOCOL.md) on raw highs:
// consecutive lower M30 swing highs (N=5) in a one-week window (signal session + 5 previous),
// anchors >= 10 bars apart, line falling >= 0.02 x A per bar, A = mean of the 14 true ranges
// before the signal (same contract), D = 0.5 x A. Requires contract_rolls.mqh (CR_DATE/CR_ID).
// Floating-point expressions follow the Python order so line values agree exactly.

input int    GateMode     = 0;     // 0 off, 1 classify + log only (no orders), 2 candidates only
input int    GateN        = 5;     // swing-high strength
input int    GateSessions = 5;     // previous sessions in the window
input int    GateMinSep   = 10;    // minimum anchor separation, bars
input double GateMinSlope = 0.02;  // minimum fall per bar, x A

#define GATE_BARS 1500

enum GateGroup { G_TEST=0, G_POKE=1, G_BROKEN=2, G_NOT_DEPARTED=3, G_NONE=4, G_MISSING=5, G_ROLL=6, G_ATR=7 };
string GATE_NAMES[8] = {"resistance_test","poke_through","broken_contact","not_departed_contact",
                        "no_contact","missing_history","contract_roll","invalid_atr"};
int    g_gateFile = INVALID_HANDLE;
int    g_gateErrors = 0;
int    g_gateCounts[8];

int GateContract(datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   int ymd = d.year * 10000 + d.mon * 100 + d.day;
   int id = -1;
   for(int k = 0; k < CR_COUNT && CR_DATE[k] <= ymd; k++) id = CR_ID[k];
   return id;
}

double GateLine(const double &h[], int i, int j, double k)
{
   return h[i] + (h[j] - h[i]) * (k - i) / (j - i);
}

bool GateOpenLog()
{
   if(GateMode == 0) return true;
   g_gateFile = FileOpen(g_runTag + "_gate.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(g_gateFile == INVALID_HANDLE) return false;
   FileWrite(g_gateFile, "signal_time", "group", "line", "anchor1_time", "anchor2_time", "atr", "known_pivots",
             "contacted", "signal_high", "signal_low", "action");
   return true;
}

void GateCloseLog()
{
   if(g_gateFile != INVALID_HANDLE) FileClose(g_gateFile);
   g_gateFile = INVALID_HANDLE;
}

// Classify the last closed bar (shift 1). Returns a GateGroup; fills line/anchors when contacted.
int GateClassify(double &line, datetime &a1, datetime &a2, double &atr, int &known, int &contacted)
{
   line = 0; a1 = 0; a2 = 0; atr = 0; known = 0; contacted = 0;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_M30, 1, GATE_BARS, r);
   if(n < 50) return G_MISSING;
   int s = n - 1;
   double h[], l[], c[]; int con[]; datetime day[];
   ArrayResize(h, n); ArrayResize(l, n); ArrayResize(c, n); ArrayResize(con, n); ArrayResize(day, n);
   for(int k = 0; k < n; k++)
   {
      h[k] = r[k].high; l[k] = r[k].low; c[k] = r[k].close;
      day[k] = r[k].time - (r[k].time % 86400);
      con[k] = GateContract(r[k].time);
   }
   // Window: first bar of the GateSessions-th previous distinct session date.
   int dates = 1, start = -1;
   for(int k = s - 1; k >= 0; k--)
   {
      if(day[k] != day[k + 1])
      {
         dates++;
         if(dates > GateSessions + 1) { start = k + 1; break; }
      }
   }
   if(start < 0) return G_MISSING;              // copied history too short to see the window start
   for(int k = start; k <= s; k++) if(con[k] != con[s]) return G_ROLL;
   if(s - 14 < 1) return G_ATR;
   double sum = 0;
   for(int k = s - 14; k <= s - 1; k++)
   {
      if(con[k] != con[s]) return G_ATR;
      double tr = h[k] - l[k];
      if(con[k - 1] == con[k]) tr = MathMax(tr, MathMax(MathAbs(h[k] - c[k - 1]), MathAbs(l[k] - c[k - 1])));
      sum += tr;
   }
   double a = sum / 14.0;
   if(a <= 0) return G_ATR;
   atr = a;
   double d = 0.5 * a;
   // Known swing highs: pivot bar in the window, confirmed (i + N closed) before the signal opens.
   int piv[]; int np = 0;
   for(int i = start; i + GateN <= s - 1; i++)
   {
      if(i - GateN < 0) continue;
      bool ok = true;
      for(int k = i - GateN; k <= i + GateN && ok; k++) if(con[k] != con[i]) ok = false;
      for(int k = 1; k <= GateN && ok; k++) if(!(h[i] > h[i - k]) || !(h[i] >= h[i + k])) ok = false;
      if(ok) { ArrayResize(piv, np + 1); piv[np++] = i; }
   }
   known = np;
   // Each contacted valid line gets a group; the signal takes the highest-ranked one.
   int groupOf[]; double vOf[]; int iOf[], jOf[]; int nl = 0;
   for(int m = 1; m < np; m++)
   {
      int j = piv[m], i = -1;
      for(int q = m - 1; q >= 0; q--) if(h[piv[q]] > h[j]) { i = piv[q]; break; }
      if(i < 0 || j - i < GateMinSep) continue;
      if(!((h[i] - h[j]) / (j - i) >= GateMinSlope * a)) continue;
      double v = GateLine(h, i, j, s);
      if(!(h[s] >= v - d && l[s] <= v + d)) continue;
      bool valid = true;
      for(int k = i + 1; k < j && valid; k++) if(h[k] > GateLine(h, i, j, k) + d) valid = false;
      if(!valid) continue;
      bool broken = false, departed = false;
      for(int k = j + 1; k < s; k++)
      {
         double lv = GateLine(h, i, j, k);
         if(c[k] > lv + d) broken = true;
         if(c[k] <= lv - a) departed = true;
      }
      int g;
      if(!broken && departed) g = (h[s] <= v + d) ? G_TEST : G_POKE;
      else g = broken ? G_BROKEN : G_NOT_DEPARTED;
      ArrayResize(groupOf, nl + 1); ArrayResize(vOf, nl + 1); ArrayResize(iOf, nl + 1); ArrayResize(jOf, nl + 1);
      groupOf[nl] = g; vOf[nl] = v; iOf[nl] = i; jOf[nl] = j; nl++;
   }
   contacted = nl;
   if(nl == 0) return G_NONE;
   // Group precedence exactly as in Python: test, poke, (all broken) broken, else not departed.
   int group;
   bool hasTest = false, hasPoke = false, allBroken = true;
   for(int q = 0; q < nl; q++)
   {
      if(groupOf[q] == G_TEST) hasTest = true;
      if(groupOf[q] == G_POKE) hasPoke = true;
      if(groupOf[q] != G_BROKEN) allBroken = false;
   }
   if(hasTest) group = G_TEST;
   else if(hasPoke) group = G_POKE;
   else if(allBroken) group = G_BROKEN;
   else group = G_NOT_DEPARTED;
   // Pool for the described line: the winning group's lines (not-departed: the unbroken ones).
   int pick = -1;
   double bestDist = 0;
   for(int q = 0; q < nl; q++)
   {
      if(groupOf[q] != group) continue;  // broken pool = all lines, since all are broken then
      double dist = MathAbs(h[s] - vOf[q]);
      if(pick < 0 || dist < bestDist || (dist == bestDist && (jOf[q] > jOf[pick] || (jOf[q] == jOf[pick] && iOf[q] > iOf[pick]))))
      { pick = q; bestDist = dist; }
   }
   line = vOf[pick]; a1 = r[iOf[pick]].time; a2 = r[jOf[pick]].time;
   return group;
}

// Called where the baseline would place an order. Returns true when the order may be placed.
bool GateAllows()
{
   if(GateMode == 0) return true;
   double line, atr; datetime a1, a2; int known, contacted;
   int g = GateClassify(line, a1, a2, atr, known, contacted);
   g_gateCounts[g]++;
   bool allow = (GateMode == 2 && g == G_TEST);
   string action = (GateMode == 1 ? "log_only" : (allow ? "placed" : "rejected"));
   if(FileWrite(g_gateFile, TimeToString(iTime(_Symbol, _Period, 1), TIME_DATE|TIME_SECONDS), GATE_NAMES[g],
      DoubleToString(line, 10), (a1 > 0 ? TimeToString(a1, TIME_DATE|TIME_SECONDS) : ""),
      (a2 > 0 ? TimeToString(a2, TIME_DATE|TIME_SECONDS) : ""), DoubleToString(atr, 10), known, contacted,
      iHigh(_Symbol, _Period, 1), iLow(_Symbol, _Period, 1), action) == 0) g_gateErrors++;
   return allow;
}
