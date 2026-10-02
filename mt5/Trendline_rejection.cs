//+------------------------------------------------------------------+
//|                                        TrendlineRejectionEA.mq5   |
//|   Sibling of LevelRejectionEA, but for DIAGONAL uptrend support   |
//|   lines instead of horizontal levels.                             |
//|                                                                   |
//|   Scope (kept deliberately small for a first version):            |
//|     - LONGS ONLY                                                   |
//|     - only UPTREND SUPPORT lines (connecting rising swing lows)    |
//|     - few, strict, high-quality lines (anchors spanning ~days)     |
//|     - trade the REJECTION (fade) on a CLOSED bar:                  |
//|         price dips to the line, wicks through, closes back above   |
//|         -> BUY                                                     |
//+------------------------------------------------------------------+
#property copyright "Level_rejection port"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

//====================================================================
//  INPUTS
//====================================================================

input group "=== Pivot / line discovery ==="
input int      InpPivotLeft        = 3;      // Swing-low strength: bars to the left
input int      InpPivotRight       = 3;      // Swing-low strength: bars to the right (confirm delay)
input int      InpScanBars         = 1500;   // Bars of history to scan for pivots
input int      InpMinAnchorSep     = 40;     // Min bars between the two anchor lows (~>=1 day on M30)
input int      InpMaxAnchorSep     = 200;    // Max bars between the two anchor lows (~<=few days on M30)
input int      InpMinTouches       = 3;      // Min touches incl. the 2 anchors (>=3 => 1 confirm touch)
input double   InpTolATRmult       = 0.5;    // Touch tolerance = this x ATR
input double   InpBreakATRmult     = 0.5;    // Line invalidated when a bar closes below by this x ATR
input int      InpMaxLines         = 3;      // Keep at most this many best lines
input int      InpATRPeriod        = 14;     // ATR period (tolerance & sizing)

input group "=== Entry (rejection / fade, closed-bar, longs only) ==="
input bool     InpRequireBodyDir   = true;   // Rejection bar must be bullish (close > open)
input double   InpMinPierceATRmult = 0.05;   // Min wick pierce below the line (x ATR)

input group "=== Risk & orders ==="
input double   InpRiskPercent      = 1.0;    // Risk per trade (% of balance); 0 => fixed lot
input double   InpFixedLot         = 0.01;   // Fixed lot (used when RiskPercent = 0)
input double   InpRiskReward       = 2.0;    // Take-profit = this x risk
input double   InpSLbufferPoints   = 10;     // Extra SL buffer below rejection bar low (points)
input int      InpMaxPositions     = 1;      // Max simultaneous positions for this EA
input long     InpMagic            = 20240418;// Magic number

input group "=== Visuals ==="
input bool     InpDrawLines        = true;   // Draw discovered trend lines
input color    InpLineColor        = clrLimeGreen; // Uptrend support line colour

//====================================================================
//  GLOBALS
//====================================================================

// A diagonal support line, anchored on two rising swing lows.
// Anchors are stored as (time, price); slope is recomputed from the
// live series at evaluation time so it stays correct as bars advance.
struct TrendLine
  {
   datetime          t1;        // older anchor time
   double            p1;        // older anchor price (low)
   datetime          t2;        // newer anchor time
   double            p2;        // newer anchor price (low), p2 > p1
   int               touches;   // touches incl. both anchors
  };

#define   TL_PREFIX "TlRej_"    // chart-object name prefix

TrendLine g_lines[];
CTrade    g_trade;
int       g_atrHandle = INVALID_HANDLE;
datetime  g_lastBarTime = 0;

//====================================================================
//  LIFECYCLE
//====================================================================

int OnInit()
  {
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(20);

   g_atrHandle = iATR(_Symbol, _Period, InpATRPeriod);
   if(g_atrHandle == INVALID_HANDLE)
     {
      Print("Failed to create ATR handle");
      return(INIT_FAILED);
     }

   PrintFormat("TrendlineRejectionEA initialised on %s %s", _Symbol, EnumToString(_Period));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atrHandle != INVALID_HANDLE)
      IndicatorRelease(g_atrHandle);
   ObjectsDeleteAll(0, TL_PREFIX);
  }

//+------------------------------------------------------------------+
//| Act once per closed bar.                                         |
//+------------------------------------------------------------------+
void OnTick()
  {
   datetime curBarTime = iTime(_Symbol, _Period, 0);
   if(curBarTime == g_lastBarTime)
      return;
   g_lastBarTime = curBarTime;

   double atr = CurrentATR();
   if(atr <= 0)
      return;

   RebuildLines(atr);
   if(InpDrawLines)
      DrawLines();
   CheckRejectionAndTrade(atr);
  }

//====================================================================
//  LINE DISCOVERY
//====================================================================

//+------------------------------------------------------------------+
//| Rebuild the set of valid uptrend support lines.                  |
//|   1. collect confirmed swing-low pivots                          |
//|   2. try every rising pair within the allowed bar separation     |
//|   3. keep only lines that sit under the lows, have enough touches |
//|      and are not already broken                                   |
//|   4. de-duplicate and keep the best InpMaxLines                   |
//+------------------------------------------------------------------+
void RebuildLines(double atr)
  {
   ArrayResize(g_lines, 0);

   // --- 1. collect swing lows (oldest first) ---
   datetime pivT[];
   double   pivP[];
   int      pivS[];   // bar shift at scan time
   CollectSwingLows(pivT, pivP, pivS);
   int np = ArraySize(pivP);
   if(np < 2)
      return;

   double tol      = atr * InpTolATRmult;
   double breakD   = atr * InpBreakATRmult;
   double minPierce= atr * InpMinPierceATRmult;

   // --- 2 & 3. build and validate candidate lines ---
   for(int a = 0; a < np - 1; a++)
      for(int b = a + 1; b < np; b++)
        {
         if(pivP[b] <= pivP[a])            // must be a RISING pair (higher low)
            continue;
         int sep = pivS[a] - pivS[b];      // bars between anchors (a is older => larger shift)
         if(sep < InpMinAnchorSep || sep > InpMaxAnchorSep)
            continue;

         TrendLine tl;
         tl.t1 = pivT[a]; tl.p1 = pivP[a];
         tl.t2 = pivT[b]; tl.p2 = pivP[b];
         tl.touches = 0;

         if(ValidateLine(tl, tol, breakD))
            TryKeepLine(tl, tol);
        }

   TrimToBest();
  }

//+------------------------------------------------------------------+
//| Gather confirmed swing-low pivots over the scan window.          |
//+------------------------------------------------------------------+
void CollectSwingLows(datetime &pt[], double &pp[], int &ps[])
  {
   ArrayResize(pt, 0);
   ArrayResize(pp, 0);
   ArrayResize(ps, 0);

   int bars = MathMin(InpScanBars, Bars(_Symbol, _Period) - 2);
   // oldest -> newest so anchor arrays are chronologically ordered
   for(int s = bars - InpPivotLeft - 1; s >= 1 + InpPivotRight; s--)
     {
      if(!IsPivotLow(s))
         continue;
      int n = ArraySize(pp);
      ArrayResize(pt, n + 1);
      ArrayResize(pp, n + 1);
      ArrayResize(ps, n + 1);
      pt[n] = iTime(_Symbol, _Period, s);
      pp[n] = iLow(_Symbol, _Period, s);
      ps[n] = s;
     }
  }

bool IsPivotLow(int s)
  {
   double l = iLow(_Symbol, _Period, s);
   for(int k = 1; k <= InpPivotLeft; k++)
      if(l >= iLow(_Symbol, _Period, s + k))
         return(false);
   for(int k = 1; k <= InpPivotRight; k++)
      if(l >= iLow(_Symbol, _Period, s - k))
         return(false);
   return(true);
  }

//+------------------------------------------------------------------+
//| Project a line's price at an arbitrary bar shift.                |
//| slope is derived live from the two anchors' current shifts.      |
//+------------------------------------------------------------------+
double LineValueAtShift(const TrendLine &tl, int shift)
  {
   int s1 = iBarShift(_Symbol, _Period, tl.t1);
   int s2 = iBarShift(_Symbol, _Period, tl.t2);
   int dBars = s1 - s2;                       // > 0 (t1 older)
   if(dBars == 0)
      return(tl.p2);
   double slopePerBar = (tl.p2 - tl.p1) / dBars;   // > 0 for a rising line
   return(tl.p2 + slopePerBar * (s2 - shift));      // shift < s2 => further right => higher
  }

//+------------------------------------------------------------------+
//| A line is valid if, from the older anchor to the last closed bar:|
//|   - no bar CLOSES below it by more than breakD  (still unbroken) |
//|   - it collects >= InpMinTouches touches (low within tol, no     |
//|     decisive close-through)                                       |
//+------------------------------------------------------------------+
bool ValidateLine(TrendLine &tl, double tol, double breakD)
  {
   int sStart = iBarShift(_Symbol, _Period, tl.t1);
   int touches = 0;

   for(int s = sStart; s >= 1; s--)
     {
      double v  = LineValueAtShift(tl, s);
      double lo = iLow(_Symbol, _Period, s);
      double cl = iClose(_Symbol, _Period, s);

      if(cl < v - breakD)          // decisively closed below => line already broken
         return(false);
      if(MathAbs(lo - v) <= tol)   // low kissed the line
         touches++;
     }

   tl.touches = touches;
   return(touches >= InpMinTouches);
  }

//+------------------------------------------------------------------+
//| Keep a validated line unless a near-duplicate (similar projected |
//| value at the last closed bar) is already stored; then keep the   |
//| one with more touches.                                           |
//+------------------------------------------------------------------+
void TryKeepLine(TrendLine &tl, double tol)
  {
   double vNew = LineValueAtShift(tl, 1);
   for(int i = 0; i < ArraySize(g_lines); i++)
     {
      double vOld = LineValueAtShift(g_lines[i], 1);
      if(MathAbs(vNew - vOld) <= tol)
        {
         if(tl.touches > g_lines[i].touches)
            g_lines[i] = tl;       // replace weaker duplicate
         return;
        }
     }
   int n = ArraySize(g_lines);
   ArrayResize(g_lines, n + 1);
   g_lines[n] = tl;
  }

//+------------------------------------------------------------------+
//| Sort by touches (desc) and keep at most InpMaxLines.             |
//+------------------------------------------------------------------+
void TrimToBest()
  {
   int n = ArraySize(g_lines);
   for(int i = 0; i < n - 1; i++)
      for(int j = i + 1; j < n; j++)
         if(g_lines[j].touches > g_lines[i].touches)
           {
            TrendLine tmp = g_lines[i];
            g_lines[i] = g_lines[j];
            g_lines[j] = tmp;
           }
   if(n > InpMaxLines)
      ArrayResize(g_lines, InpMaxLines);
  }

//====================================================================
//  ENTRY: rejection off an uptrend support line (long only)
//====================================================================

void CheckRejectionAndTrade(double atr)
  {
   if(CountMyPositions() >= InpMaxPositions)
      return;

   double prevClose = iClose(_Symbol, _Period, 2);
   double l1 = iLow(_Symbol, _Period, 1);
   double c1 = iClose(_Symbol, _Period, 1);
   double o1 = iOpen(_Symbol, _Period, 1);
   double minPierce = atr * InpMinPierceATRmult;

   for(int i = 0; i < ArraySize(g_lines); i++)
     {
      double lvl2 = LineValueAtShift(g_lines[i], 2);   // line under the prev bar
      double lvl1 = LineValueAtShift(g_lines[i], 1);   // line under the rejection bar

      // Faded support -> BUY: was above the line, wick dipped through it
      // by >= minPierce, but the bar closed back above it.
      if(prevClose > lvl2 && l1 <= lvl1 - minPierce && c1 > lvl1)
        {
         if(InpRequireBodyDir && c1 <= o1)
            continue;
         double sl = l1 - InpSLbufferPoints * _Point;
         OpenLong(sl);
         return;
        }
     }
  }

//====================================================================
//  ORDER PLACEMENT
//====================================================================

void OpenLong(double slPrice)
  {
   double entry = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double risk  = entry - slPrice;
   if(risk <= 0)
      return;

   double tpPrice = entry + risk * InpRiskReward;
   slPrice = NormalizeDouble(slPrice, _Digits);
   tpPrice = NormalizeDouble(tpPrice, _Digits);

   double lot = CalcLot(risk);
   if(lot <= 0)
      return;

   if(g_trade.Buy(lot, _Symbol, 0.0, slPrice, tpPrice, "TlRej"))
      PrintFormat("BUY %.2f lots @~%.*f  SL %.*f  TP %.*f",
                  lot, _Digits, entry, _Digits, slPrice, _Digits, tpPrice);
   else
      PrintFormat("Order failed: retcode=%d %s", g_trade.ResultRetcode(),
                  g_trade.ResultRetcodeDescription());
  }

double CalcLot(double riskPriceDist)
  {
   double lot = InpFixedLot;

   if(InpRiskPercent > 0.0)
     {
      double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      if(tickVal > 0 && tickSize > 0)
        {
         double moneyRisk  = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0;
         double lossPerLot = (riskPriceDist / tickSize) * tickVal;
         if(lossPerLot > 0)
            lot = moneyRisk / lossPerLot;
        }
     }

   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(lotStep > 0)
      lot = MathFloor(lot / lotStep) * lotStep;
   lot = MathMax(minLot, MathMin(maxLot, lot));
   return(lot);
  }

//====================================================================
//  HELPERS
//====================================================================

double CurrentATR()
  {
   double buf[];
   if(CopyBuffer(g_atrHandle, 0, 0, 1, buf) != 1)
      return(0.0);
   return(buf[0]);
  }

int CountMyPositions()
  {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
         count++;
     }
   return(count);
  }

//+------------------------------------------------------------------+
//| Draw each kept line from anchor1 through anchor2, ray right.     |
//+------------------------------------------------------------------+
void DrawLines()
  {
   ObjectsDeleteAll(0, TL_PREFIX);

   for(int i = 0; i < ArraySize(g_lines); i++)
     {
      string name = StringFormat("%s%d", TL_PREFIX, i);
      if(!ObjectCreate(0, name, OBJ_TREND, 0,
                       g_lines[i].t1, g_lines[i].p1,
                       g_lines[i].t2, g_lines[i].p2))
         continue;

      ObjectSetInteger(0, name, OBJPROP_COLOR, InpLineColor);
      ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1 + MathMin(g_lines[i].touches - 2, 3));
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetString(0, name, OBJPROP_TOOLTIP,
                      StringFormat("Uptrend support  (touches: %d)", g_lines[i].touches));
     }
   ChartRedraw(0);
  }
//+------------------------------------------------------------------+
