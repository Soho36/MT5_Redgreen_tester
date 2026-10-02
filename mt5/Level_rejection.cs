//+------------------------------------------------------------------+
//|                                            LevelRejectionEA.mq5   |
//|   Native MQL5 port of the old Python "Level_rejection" strategy.  |
//|                                                                   |
//|   - Discovers support/resistance levels from fractal swing pivots |
//|   - Clusters nearby pivots into zones with a tick-normalized       |
//|     tolerance, tracks touch count, and invalidates broken levels  |
//|   - Trades level REJECTION (fade) on a CLOSED bar:                 |
//|       * resistance faded (wick above, close back below) -> SELL   |
//|       * support faded    (wick below, close back above) -> BUY    |
//|   - Places orders directly via CTrade (no Python / no file IPC)   |
//+------------------------------------------------------------------+
#property copyright "Level_rejection port"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

//====================================================================
//  INPUTS
//====================================================================

input group "=== Level discovery ==="
input int      InpPivotLeft        = 2;      // Pivot strength: bars to the left
input int      InpPivotRight       = 2;      // Pivot strength: bars to the right (confirmation delay)
input int      InpScanBars         = 500;    // Bars of history to scan for levels
input double   InpTolATRmult       = 0.5;    // Zone merge tolerance = this x ATR
input int      InpATRPeriod        = 14;     // ATR period (tolerance & optional SL)
input int      InpMinTouches       = 1;      // Min touches for a level to be tradable
input double   InpBreakATRmult     = 0.5;    // Level invalidated when close breaks it by this x ATR

input group "=== Entry (rejection / fade, closed-bar) ==="
input bool     InpRequireBodyDir   = true;   // Rejection bar body must point in trade direction
input double   InpMinPierceATRmult = 0.05;   // Min wick pierce beyond level (x ATR) to count as rejection

input group "=== Risk & orders ==="
input double   InpRiskPercent      = 1.0;    // Risk per trade (% of balance); 0 => use fixed lot
input double   InpFixedLot         = 0.01;   // Fixed lot (used when RiskPercent = 0)
input double   InpRiskReward       = 2.0;    // Take-profit = this x risk
input double   InpSLbufferPoints   = 10;     // Extra SL buffer beyond rejection bar (points)
input int      InpMaxPositions     = 1;      // Max simultaneous positions for this EA
input long     InpMagic            = 20240417;// Magic number

input group "=== Visuals ==="
input bool     InpDrawLevels       = true;   // Draw discovered levels on the chart
input color    InpResistColor      = clrTomato;      // Resistance line colour
input color    InpSupportColor     = clrDodgerBlue;  // Support line colour

//====================================================================
//  GLOBALS
//====================================================================

struct SRLevel
  {
   double            price;        // level price
   bool              isResistance; // true = resistance (from a swing high)
   int               touches;      // how many pivots clustered here
   datetime          created;      // first pivot time
   bool              active;       // false once decisively broken
  };

#define   LVL_PREFIX "LvlRej_"     // chart-object name prefix

SRLevel   g_levels[];
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

   PrintFormat("LevelRejectionEA initialised on %s %s", _Symbol, EnumToString(_Period));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atrHandle != INVALID_HANDLE)
      IndicatorRelease(g_atrHandle);
   ClearLevelObjects();
  }

//+------------------------------------------------------------------+
//| Main: act once per closed bar                                    |
//+------------------------------------------------------------------+
void OnTick()
  {
   datetime curBarTime = iTime(_Symbol, _Period, 0);
   if(curBarTime == g_lastBarTime)
      return;                       // still inside the same bar
   g_lastBarTime = curBarTime;      // a new bar has opened => bar 1 just closed

   double atr = CurrentATR();
   if(atr <= 0)
      return;

   RefreshLevels(atr);              // rebuild / update the level set
   CheckRejectionAndTrade(atr);     // evaluate the just-closed bar (shift 1)
  }

//====================================================================
//  LEVEL DISCOVERY
//====================================================================

//+------------------------------------------------------------------+
//| Rebuild the level list from fractal pivots over InpScanBars.     |
//| Pivots are clustered into zones; touches accumulate; levels that |
//| price has decisively closed through are dropped.                 |
//+------------------------------------------------------------------+
void RefreshLevels(double atr)
  {
   ArrayResize(g_levels, 0);

   int bars = MathMin(InpScanBars, Bars(_Symbol, _Period) - 2);
   double tol = atr * InpTolATRmult;

   // Scan from oldest to newest. A pivot at shift s needs InpPivotRight
   // confirmed bars to its right (newer) and InpPivotLeft to its left.
   for(int s = bars - InpPivotLeft - 1; s >= 1 + InpPivotRight; s--)
     {
      if(IsPivotHigh(s))
         AddOrMergeLevel(iHigh(_Symbol, _Period, s), true, iTime(_Symbol, _Period, s), tol);
      else if(IsPivotLow(s))
         AddOrMergeLevel(iLow(_Symbol, _Period, s), false, iTime(_Symbol, _Period, s), tol);
     }

   InvalidateBrokenLevels(atr);

   if(InpDrawLevels)
      DrawLevels();
  }

//+------------------------------------------------------------------+
//| Fractal swing high: high[s] strictly greater than the InpPivotLeft|
//| bars on the left and InpPivotRight bars on the right.            |
//+------------------------------------------------------------------+
bool IsPivotHigh(int s)
  {
   double h = iHigh(_Symbol, _Period, s);
   for(int k = 1; k <= InpPivotLeft; k++)
      if(h <= iHigh(_Symbol, _Period, s + k))
         return(false);
   for(int k = 1; k <= InpPivotRight; k++)
      if(h <= iHigh(_Symbol, _Period, s - k))
         return(false);
   return(true);
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
//| Add a pivot as a new level, or merge it into an existing one if  |
//| within tolerance (touch count grows, price averaged).            |
//+------------------------------------------------------------------+
void AddOrMergeLevel(double price, bool isResistance, datetime t, double tol)
  {
   for(int i = 0; i < ArraySize(g_levels); i++)
     {
      if(MathAbs(price - g_levels[i].price) <= tol)
        {
         // running average keeps the zone centred on all its touches
         g_levels[i].price = (g_levels[i].price * g_levels[i].touches + price)
                             / (g_levels[i].touches + 1);
         g_levels[i].touches++;
         return;
        }
     }

   int n = ArraySize(g_levels);
   ArrayResize(g_levels, n + 1);
   g_levels[n].price        = price;
   g_levels[n].isResistance = isResistance;
   g_levels[n].touches      = 1;
   g_levels[n].created      = t;
   g_levels[n].active       = true;
  }

//+------------------------------------------------------------------+
//| Deactivate levels the market has closed decisively through.      |
//+------------------------------------------------------------------+
void InvalidateBrokenLevels(double atr)
  {
   double closeLast = iClose(_Symbol, _Period, 1);
   double breakDist = atr * InpBreakATRmult;

   for(int i = 0; i < ArraySize(g_levels); i++)
     {
      if(g_levels[i].isResistance && closeLast > g_levels[i].price + breakDist)
         g_levels[i].active = false;
      if(!g_levels[i].isResistance && closeLast < g_levels[i].price - breakDist)
         g_levels[i].active = false;
     }
  }

//====================================================================
//  ENTRY: level rejection on the closed bar (shift 1)
//====================================================================

void CheckRejectionAndTrade(double atr)
  {
   if(CountMyPositions() >= InpMaxPositions)
      return;

   // The just-closed rejection candidate bar and the bar before it.
   double prevClose = iClose(_Symbol, _Period, 2);
   double h1 = iHigh(_Symbol, _Period, 1);
   double l1 = iLow(_Symbol, _Period, 1);
   double c1 = iClose(_Symbol, _Period, 1);
   double o1 = iOpen(_Symbol, _Period, 1);

   double minPierce = atr * InpMinPierceATRmult;

   for(int i = 0; i < ArraySize(g_levels); i++)
     {
      if(!g_levels[i].active || g_levels[i].touches < InpMinTouches)
         continue;

      double level = g_levels[i].price;

      // --- Faded RESISTANCE -> SELL: approached from below, wick pierced
      //     above by >= minPierce, but the bar closed back below it. -----
      if(prevClose < level && h1 >= level + minPierce && c1 < level)
        {
         if(InpRequireBodyDir && c1 >= o1)   // want a bearish rejection body
            continue;
         double sl = h1 + InpSLbufferPoints * _Point;
         OpenTrade(ORDER_TYPE_SELL, sl);
         return;
        }

      // --- Faded SUPPORT -> BUY: approached from above, wick pierced
      //     below by >= minPierce, but the bar closed back above it. ------
      if(prevClose > level && l1 <= level - minPierce && c1 > level)
        {
         if(InpRequireBodyDir && c1 <= o1)   // want a bullish rejection body
            continue;
         double sl = l1 - InpSLbufferPoints * _Point;
         OpenTrade(ORDER_TYPE_BUY, sl);
         return;
        }
     }
  }

//====================================================================
//  ORDER PLACEMENT
//====================================================================

void OpenTrade(ENUM_ORDER_TYPE type, double slPrice)
  {
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (type == ORDER_TYPE_BUY) ? ask : bid;

   double risk = MathAbs(entry - slPrice);
   if(risk <= 0)
      return;

   double tpPrice = (type == ORDER_TYPE_BUY)
                    ? entry + risk * InpRiskReward
                    : entry - risk * InpRiskReward;

   slPrice = NormalizeDouble(slPrice, _Digits);
   tpPrice = NormalizeDouble(tpPrice, _Digits);

   double lot = CalcLot(risk);
   if(lot <= 0)
      return;

   bool ok = (type == ORDER_TYPE_BUY)
             ? g_trade.Buy(lot, _Symbol, 0.0, slPrice, tpPrice, "LvlRej")
             : g_trade.Sell(lot, _Symbol, 0.0, slPrice, tpPrice, "LvlRej");

   if(ok)
      PrintFormat("%s %.2f lots @~%.*f  SL %.*f  TP %.*f",
                  (type == ORDER_TYPE_BUY ? "BUY" : "SELL"),
                  lot, _Digits, entry, _Digits, slPrice, _Digits, tpPrice);
   else
      PrintFormat("Order failed: retcode=%d %s", g_trade.ResultRetcode(),
                  g_trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
//| Lot from risk %, or fixed lot. Normalised to broker constraints. |
//+------------------------------------------------------------------+
double CalcLot(double riskPriceDist)
  {
   double lot = InpFixedLot;

   if(InpRiskPercent > 0.0)
     {
      double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      if(tickVal > 0 && tickSize > 0)
        {
         double moneyRisk = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0;
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

//+------------------------------------------------------------------+
//| Draw each active level as a ray from its first pivot to the right.|
//| Colour = support/resistance; the touch count is in the tooltip.  |
//+------------------------------------------------------------------+
void DrawLevels()
  {
   ClearLevelObjects();
   datetime rightEdge = iTime(_Symbol, _Period, 0);

   for(int i = 0; i < ArraySize(g_levels); i++)
     {
      if(!g_levels[i].active || g_levels[i].touches < InpMinTouches)
         continue;

      string name = StringFormat("%s%d", LVL_PREFIX, i);
      double p    = g_levels[i].price;

      if(!ObjectCreate(0, name, OBJ_TREND, 0, g_levels[i].created, p, rightEdge, p))
         continue;

      ObjectSetInteger(0, name, OBJPROP_COLOR,
                       g_levels[i].isResistance ? InpResistColor : InpSupportColor);
      ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1 + MathMin(g_levels[i].touches - 1, 3));
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetString(0, name, OBJPROP_TOOLTIP,
                      StringFormat("%s  %.*f  (touches: %d)",
                                   g_levels[i].isResistance ? "Resistance" : "Support",
                                   _Digits, p, g_levels[i].touches));
     }
   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
//| Remove all objects this EA created.                              |
//+------------------------------------------------------------------+
void ClearLevelObjects()
  {
   ObjectsDeleteAll(0, LVL_PREFIX);
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
