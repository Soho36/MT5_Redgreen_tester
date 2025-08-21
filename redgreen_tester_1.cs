//+------------------------------------------------------------------+
//| Simple Red-Green Breakout EA (Backtest version)                  |
//+------------------------------------------------------------------+
#property strict

input double Lots = 1.0;
input double RiskReward = 2.0;  // 1R target
input int Slippage = 5;

// Store state
bool inTrade = false;
double entryPrice, stopPrice, risk;

//+------------------------------------------------------------------+
int OnInit()
{
   return(INIT_SUCCEEDED);
}
//+------------------------------------------------------------------+
void OnTick()
{
   // Only check conditions on a *new bar*
   static datetime lastBarTime = 0;
   datetime currBarTime = iTime(_Symbol, _Period, 0);

   if (currBarTime == lastBarTime) return;
   lastBarTime = currBarTime;

   // Previous and current candle
   double prevOpen  = iOpen(_Symbol, _Period, 2);
   double prevClose = iClose(_Symbol, _Period, 2);
   double prevHigh  = iHigh(_Symbol, _Period, 2);
   double prevLow   = iLow(_Symbol, _Period, 2);

   double currOpen  = iOpen(_Symbol, _Period, 1);
   double currClose = iClose(_Symbol, _Period, 1);
   double currHigh  = iHigh(_Symbol, _Period, 1);

   // Check trade logic
   if (!inTrade)
	   
   {
	   Print("Checking condition: prevC=", prevClose, " prevO=", prevOpen,
         " currC=", currClose, " currO=", currOpen,
         " prevH=", prevHigh, " currH=", currHigh);
      
	  // Red candle followed by green breakout
      if (prevClose < prevOpen && currClose > currOpen && currHigh > prevHigh)
      {
		 Print("Pattern found! Trying to place order...");
         entryPrice = prevHigh;
         stopPrice = prevLow;
         risk = entryPrice - stopPrice;

         if (risk > 0)
         {
            double tpPrice = entryPrice + RiskReward * risk;

            // Place buy stop order
            MqlTradeRequest request;
            MqlTradeResult result;
            ZeroMemory(request);

            request.action   = TRADE_ACTION_PENDING;
            request.symbol   = _Symbol;
            request.volume   = Lots;
            request.type     = ORDER_TYPE_BUY_STOP;
            request.price    = entryPrice;
            request.sl       = stopPrice;
            request.tp       = tpPrice;
            request.deviation= Slippage;
            request.type_filling = ORDER_FILLING_RETURN;

            if (OrderSend(request,result))
            {
               Print("Placed Buy Stop at ", entryPrice, " SL=", stopPrice, " TP=", tpPrice);
               inTrade = true;
            }
         }
      }
   }
   else
   {
      // Reset flag if no open positions
      if (PositionsTotal() == 0 && OrdersTotal() == 0)
      {
         inTrade = false;
      }
   }
}
