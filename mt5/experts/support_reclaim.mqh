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
// ReclaimMode 1 = classify + log only (no orders). The trading modes are added after this log is verified.

input int    ReclaimMode   = 1;     // 1 classify only
input double BreakDepthA   = 0.0;   // break threshold below the level, x A (primary 0, S1 0.5)
input double MinRiskA      = 0.25;  // minimum risk L - low(s), x A
input int    LevelN        = 5;     // swing-low strength
input int    LevelSessions = 5;     // previous sessions in the window

#define SR_BARS 1500

enum SRStatus { SR_ORDER=0, SR_GAP=1, SR_MINRISK=2, SR_NO_BREAK=3, SR_NO_LEVEL=4, SR_MISSING=5, SR_ROLL=6, SR_ATR=7 };
string SR_NAMES[8] = {"order","gap_above","min_risk","no_break","no_level","missing_history","contract_roll","invalid_atr"};
int    g_srFile = INVALID_HANDLE;
int    g_srErrors = 0;
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
   if(ReclaimMode != 1 || !MathIsValidNumber(BreakDepthA) || BreakDepthA < 0 || !MathIsValidNumber(MinRiskA)
      || MinRiskA < 0 || LevelN < 1 || LevelSessions < 0) return false;
   g_srFile = FileOpen(g_runTag + "_reclaim.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(g_srFile == INVALID_HANDLE) return false;
   FileWrite(g_srFile, "bar_time", "s_time", "open", "ask", "bid", "status", "level", "key_time", "t0_time", "members",
             "atr", "entry", "stop", "risk", "known_pivots", "levels", "levels_live", "levels_broken", "s_red",
             "same_contract");
   return true;
}

void SRDeinit()
{
   if(g_srFile != INVALID_HANDLE) FileClose(g_srFile);
   g_srFile = INVALID_HANDLE;
   int f = FileOpen(g_runTag + "_reclaim_stats.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(f == INVALID_HANDLE) return;
   FileWrite(f, "reclaim_mode", "break_depth_a", "min_risk_a", "log_errors", "tick", "order", "gap_above", "min_risk",
             "no_break", "no_level", "missing_history", "contract_roll", "invalid_atr");
   FileWrite(f, ReclaimMode, BreakDepthA, MinRiskA, g_srErrors,
             DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE), 10), g_srCounts[0], g_srCounts[1],
             g_srCounts[2], g_srCounts[3], g_srCounts[4], g_srCounts[5], g_srCounts[6], g_srCounts[7]);
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

// Called once per new bar, before the flatten / position / window checks: classifies bar s and records breaks.
void SROnNewBar(datetime barOpen)
{
   SRPruneSpent(barOpen);
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
   if(FileWrite(g_srFile, TimeToString(barOpen, TIME_DATE|TIME_SECONDS),
      (g_srS > 0 ? TimeToString(g_srS, TIME_DATE|TIME_SECONDS) : ""), DoubleToString(open, 2), DoubleToString(ask, 2),
      DoubleToString(bid, 2), SR_NAMES[g_srSt], DoubleToString(g_srLevel, 2),
      (g_srKey > 0 ? TimeToString(g_srKey, TIME_DATE|TIME_SECONDS) : ""),
      (g_srT0 > 0 ? TimeToString(g_srT0, TIME_DATE|TIME_SECONDS) : ""), g_srMembers, DoubleToString(g_srAtr, 10),
      DoubleToString(g_srEntry, 2), DoubleToString(g_srStop, 2), DoubleToString(g_srRisk, 2), g_srKnown, g_srLevels,
      g_srLive, g_srBroken, (int)g_srRed, (int)g_srSame) == 0)
      g_srErrors++;
}
