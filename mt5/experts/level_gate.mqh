// Q18 stage-2 horizontal swing-high breakout gate (research only).
// Mirrors python/level_resistance.py (frozen docs/levels/BREAKOUT_PROTOCOL.md) on raw highs:
// confirmed M30 swing highs (N=5) in a one-week window (signal session + 5 previous), merged greedily
// from the highest within D; L = highest member. Broken = a close > L + D after the latest member;
// departed = a close <= L - A. A = mean of the 14 true ranges before the signal (same contract),
// D = 0.5 x A. Requires contract_rolls.mqh (CR_DATE/CR_ID). Expressions follow the Python order.

input int GateMode     = 0;   // 0 off, 1 classify + log only (no orders), 2 candidates only
input int GateN        = 5;   // swing-high strength
input int GateSessions = 5;   // previous sessions in the window

#define GATE_BARS 1500

enum GateGroup { G_TEST=0, G_POKE=1, G_BROKEN=2, G_NOT_DEPARTED=3, G_NONE=4, G_MISSING=5, G_ROLL=6, G_ATR=7 };
string GATE_NAMES[8] = {"breakout_test","poke_through","broken_upward_contact","not_departed_contact",
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

bool GateOpenLog()
{
   if(GateMode == 0) return true;
   g_gateFile = FileOpen(g_runTag + "_gate.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(g_gateFile == INVALID_HANDLE) return false;
   FileWrite(g_gateFile, "signal_time", "group", "level", "t0_time", "members", "atr", "known_pivots",
             "levels", "signal_high", "signal_low", "action");
   return true;
}

void GateCloseLog()
{
   if(g_gateFile != INVALID_HANDLE) FileClose(g_gateFile);
   g_gateFile = INVALID_HANDLE;
}

// Classify the last closed bar (shift 1). Fills the described level when contacted.
int GateClassify(double &level, datetime &t0time, int &members, double &atr, int &known, int &nlevels)
{
   level = 0; t0time = 0; members = 0; atr = 0; known = 0; nlevels = 0;
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
   int dates = 1, start = -1;
   for(int k = s - 1; k >= 0; k--)
   {
      if(day[k] != day[k + 1])
      {
         dates++;
         if(dates > GateSessions + 1) { start = k + 1; break; }
      }
   }
   if(start < 0) return G_MISSING;
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
   // Known swing highs: pivot in the window, confirmed (i + N closed) before the signal opens.
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
   // Sort by (-high, index): highest first, ties to the earlier bar (insertion sort; np is small).
   for(int x = 1; x < np; x++)
   {
      int v = piv[x], y = x - 1;
      while(y >= 0 && (h[piv[y]] < h[v] || (h[piv[y]] == h[v] && piv[y] > v))) { piv[y + 1] = piv[y]; y--; }
      piv[y + 1] = v;
   }
   int group = G_NONE; bool hasTest = false, hasPoke = false, hasBroken = false, hasNear = false;
   double lv[]; int lt0[], lmem[], lg[]; int nl = 0;
   int k2 = 0;
   while(k2 < np)
   {
      double L = h[piv[k2]];
      int t0 = piv[k2], cnt = 1;
      k2++;
      while(k2 < np && L - h[piv[k2]] <= d) { t0 = MathMax(t0, piv[k2]); cnt++; k2++; }
      nlevels++;
      if(!(h[s] >= L - d && l[s] <= L + d)) continue;
      bool broken = false, departed = false;
      for(int k = t0 + 1; k < s; k++)
      {
         if(c[k] > L + d) broken = true;
         if(c[k] <= L - a) departed = true;
      }
      int g;
      if(!broken && departed) g = (h[s] <= L + d) ? G_TEST : G_POKE;
      else g = broken ? G_BROKEN : G_NOT_DEPARTED;
      if(g == G_TEST) hasTest = true;
      if(g == G_POKE) hasPoke = true;
      if(g == G_BROKEN) hasBroken = true;
      if(g == G_NOT_DEPARTED) hasNear = true;
      ArrayResize(lv, nl + 1); ArrayResize(lt0, nl + 1); ArrayResize(lmem, nl + 1); ArrayResize(lg, nl + 1);
      lv[nl] = L; lt0[nl] = t0; lmem[nl] = cnt; lg[nl] = g; nl++;
   }
   if(nl == 0) return G_NONE;
   // Q11 order: test, poke (intact but too deep), any broken, else not departed.
   if(hasTest) group = G_TEST;
   else if(hasPoke) group = G_POKE;
   else if(hasBroken) group = G_BROKEN;
   else group = G_NOT_DEPARTED;
   int pick = -1; double best = 0;
   for(int q = 0; q < nl; q++)
   {
      if(lg[q] != group) continue;
      double dist = MathAbs(h[s] - lv[q]);
      if(pick < 0 || dist < best || (dist == best && lt0[q] > lt0[pick])) { pick = q; best = dist; }
   }
   level = lv[pick]; t0time = r[lt0[pick]].time; members = lmem[pick];
   return group;
}

// Called where the baseline would place an order. Returns true when the order may be placed.
bool GateAllows()
{
   if(GateMode == 0) return true;
   double level, atr; datetime t0time; int members, known, nlevels;
   int g = GateClassify(level, t0time, members, atr, known, nlevels);
   g_gateCounts[g]++;
   bool allow = (GateMode == 2 && g == G_TEST);
   string action = (GateMode == 1 ? "log_only" : (allow ? "placed" : "rejected"));
   if(FileWrite(g_gateFile, TimeToString(iTime(_Symbol, _Period, 1), TIME_DATE|TIME_SECONDS), GATE_NAMES[g],
      DoubleToString(level, 10), (t0time > 0 ? TimeToString(t0time, TIME_DATE|TIME_SECONDS) : ""), members,
      DoubleToString(atr, 10), known, nlevels, iHigh(_Symbol, _Period, 1), iLow(_Symbol, _Period, 1), action) == 0)
      g_gateErrors++;
   return allow;
}
