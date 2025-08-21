//+------------------------------------------------------------------+
//| Simple Red-Green Breakout EA (Keeps only 1 pending order)        |
//+------------------------------------------------------------------+
#property strict

input double Lots = 1.0;
input double RiskReward = 1.0;   // Reward-to-risk multiplier
input int Slippage = 5;

//+------------------------------------------------------------------+
int OnInit()
{
   return(INIT_SUCCEEDED);
}
//+------------------------------------------------------------------+
void OnTick()
{
   // Work only on a new candle
   static datetime lastBarTime = 0;
   datetime currBarTime = iTime(_Symbol, _Period, 0);

   if (currBarTime == lastBarTime) return;
   lastBarTime = currBarTime;

   // If there is already an open position, do nothing
   if (PositionsTotal() > 0)
      return;

   // Candle data (previous bar)
   double prevOpen  = iOpen(_Symbol, _Period, 1);
   double prevHigh  = iHigh(_Symbol, _Period, 1);
   double prevLow   = iLow(_Symbol, _Period, 1);
   double prevClose = iClose(_Symbol, _Period, 1);

   Print("Checking candle O=", prevOpen, " H=", prevHigh, " L=", prevLow, " C=", prevClose);

   // Check only if red candle
   if (prevClose < prevOpen)
   {
      Print("🔴 Red candle detected → Cancelling old BuyStops and placing new one...");

      // --- Cancel existing pending BuyStops ---
      for (int i = OrdersTotal() - 1; i >= 0; i--)
      {
         ulong ticket = OrderGetTicket(i);
         if (ticket == 0) continue;   // safety

         if (OrderSelect(ticket))
         {
            int type = (int)OrderGetInteger(ORDER_TYPE);

            if (type == ORDER_TYPE_BUY_STOP)
            {
               MqlTradeRequest cancel = {};
               MqlTradeResult  cancel_result = {};

               cancel.action = TRADE_ACTION_REMOVE;
               cancel.order  = ticket;

               if (!OrderSend(cancel, cancel_result))
                  Print("❌ Failed to cancel order #", ticket, " error=", GetLastError());
               else
                  Print("✅ Cancelled old Buy Stop, ticket=", ticket);
            }
         }
      }

      // --- Place new BuyStop above red candle ---
      double entryPrice = prevHigh;
      double stopPrice  = prevLow;
      double risk       = entryPrice - stopPrice;

      if (risk > 0)
      {
         double tpPrice = entryPrice + RiskReward * risk;

         MqlTradeRequest request = {};
         MqlTradeResult  result  = {};

         request.action       = TRADE_ACTION_PENDING;
         request.symbol       = _Symbol;
         request.volume       = Lots;
         request.type         = ORDER_TYPE_BUY_STOP;
         request.price        = entryPrice;
         request.sl           = stopPrice;
         request.tp           = tpPrice;
         request.deviation    = Slippage;
         request.type_filling = ORDER_FILLING_RETURN;

         if (OrderSend(request, result))
            Print("🚀 Placed Buy Stop at ", entryPrice, " SL=", stopPrice, " TP=", tpPrice);
         else
            Print("❌ Failed to place Buy Stop, error=", GetLastError());
      }
   }
}
