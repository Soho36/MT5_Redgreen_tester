//+------------------------------------------------------------------+
//| Red-Green Breakout EA: dynamic exit + no-trading window + MAE/MFE |
//+------------------------------------------------------------------+
#property strict

input double Lots           = 1.0;
input double RiskReward     = 1.0;
input int    Slippage       = 5;

// flattening
input bool   UseFlatten     = true;
input int    FlattenHour    = 23;
input int    FlattenMinute  = 30;

// no-trading window
input bool   UseNoTradeWindow   = true;
input int    NoTradeStartHour   = 23;
input int    NoTradeStartMinute = 30;
input int    NoTradeEndHour     = 1;
input int    NoTradeEndMinute   = 0;

// ---- MAE / MFE ----
double g_entryPrice = 0;
double g_mae = 0;
double g_mfe = 0;
bool   g_tracking = false;
ulong  g_ticket = 0;

string g_csvName = "trade_stats.csv";

//---------------- Helpers ----------------//
bool IsFlattenTime(datetime barOpen)
{
   MqlDateTime dt;
   TimeToStruct(barOpen, dt);
   return (dt.hour == FlattenHour && dt.min == FlattenMinute);
}

bool InNoTradeWindow(datetime barOpen)
{
   if(!UseNoTradeWindow) return false;

   MqlDateTime dt;
   TimeToStruct(barOpen, dt);

   int cur = dt.hour * 60 + dt.min;
   int st  = NoTradeStartHour * 60 + NoTradeStartMinute;
   int en  = NoTradeEndHour   * 60 + NoTradeEndMinute;

   if(st <= en) return (cur >= st && cur < en);
   return (cur >= st || cur < en);
}

void CancelAllOrders()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong t = OrderGetTicket(i);
      if(!OrderSelect(t)) continue;

      MqlTradeRequest r={};
      MqlTradeResult  s={};
      r.action = TRADE_ACTION_REMOVE;
      r.order  = t;
      OrderSend(r,s);
   }
}

void CloseAllPositions()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong t = PositionGetTicket(i);
      if(!PositionSelectByTicket(t)) continue;

      MqlTradeRequest r={};
      MqlTradeResult  s={};

      r.action    = TRADE_ACTION_DEAL;
      r.symbol    = _Symbol;
      r.volume    = PositionGetDouble(POSITION_VOLUME);
      r.deviation = Slippage;

      if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)
      {
         r.type  = ORDER_TYPE_SELL;
         r.price = SymbolInfoDouble(_Symbol,SYMBOL_BID);
      }
      else
      {
         r.type  = ORDER_TYPE_BUY;
         r.price = SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      }

      OrderSend(r,s);
   }
}

void CancelOldBuyStops()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong t = OrderGetTicket(i);
      if(!OrderSelect(t)) continue;
      if(OrderGetInteger(ORDER_TYPE)!=ORDER_TYPE_BUY_STOP) continue;

      MqlTradeRequest r={};
      MqlTradeResult  s={};
      r.action = TRADE_ACTION_REMOVE;
      r.order  = t;
      OrderSend(r,s);
   }
}

//---------------- CSV ----------------//
void SaveTradeStats()
{
   int f = FileOpen(g_csvName,
                    FILE_READ|FILE_WRITE|FILE_CSV|FILE_SHARE_WRITE);

   if(f==INVALID_HANDLE) return;

   if(FileSize(f)==0)
      FileWrite(f,"ticket","entry","mae","mfe");

   FileSeek(f,0,SEEK_END);
   FileWrite(f,(long)g_ticket,g_entryPrice,g_mae,g_mfe);
   FileClose(f);
}

//---------------- Trade mgmt ----------------//
void ManageOpenPosition()
{
   if(!PositionSelect(_Symbol)) return;

   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl    = PositionGetDouble(POSITION_SL);
   double vol   = PositionGetDouble(POSITION_VOLUME);

   double risk = entry - sl;
   if(risk<=0) return;

   double barClose = iClose(_Symbol,_Period,1);

   if(barClose >= entry + risk*RiskReward)
   {
      MqlTradeRequest r={};
      MqlTradeResult  s={};

      r.action    = TRADE_ACTION_DEAL;
      r.symbol    = _Symbol;
      r.volume    = vol;
      r.type      = ORDER_TYPE_SELL;
      r.price     = SymbolInfoDouble(_Symbol,SYMBOL_BID);
      r.deviation = Slippage;

      OrderSend(r,s);
   }
}

//---------------- EA Core ----------------//
int OnInit(){ return INIT_SUCCEEDED; }

void OnTick()
{
   static datetime lastBar=0;
   datetime barOpen=iTime(_Symbol,_Period,0);
   if(barOpen==lastBar) return;
   lastBar=barOpen;

   // 🔹 detect trade closed (observer only)
   if(g_tracking && PositionsTotal()==0)
   {
      SaveTradeStats();
      g_tracking=false;
   }

   // 🔹 flatten
   if(UseFlatten && IsFlattenTime(barOpen))
   {
      CloseAllPositions();
      CancelAllOrders();
      return;
   }

   // 🔹 no-trade window
   if(InNoTradeWindow(barOpen))
   {
      CloseAllPositions();
      CancelAllOrders();
      return;
   }

   // 🔹 manage trade (identical priority)
   if(PositionsTotal()>0)
   {
      ManageOpenPosition();

      // update MAE/MFE AFTER management
      if(PositionSelect(_Symbol))
      {
         if(!g_tracking)
         {
            g_tracking   = true;
            g_ticket     = PositionGetInteger(POSITION_TICKET);
            g_entryPrice = PositionGetDouble(POSITION_PRICE_OPEN);
            g_mae = g_mfe = 0;
         }

         double hi=iHigh(_Symbol,_Period,1);
         double lo=iLow (_Symbol,_Period,1);
         g_mfe=MathMax(g_mfe,hi-g_entryPrice);
         g_mae=MathMax(g_mae,g_entryPrice-lo);
      }
      return;
   }

   // 🔹 setup
   double o=iOpen (_Symbol,_Period,1);
   double h=iHigh (_Symbol,_Period,1);
   double l=iLow  (_Symbol,_Period,1);
   double c=iClose(_Symbol,_Period,1);

   if(c<o)
   {
      CancelOldBuyStops();

      double risk=h-l;
      if(risk<=0) return;

      MqlTradeRequest r={};
      MqlTradeResult  s={};

      r.action       = TRADE_ACTION_PENDING;
      r.symbol       = _Symbol;
      r.volume       = Lots;
      r.type         = ORDER_TYPE_BUY_STOP;
      r.price        = h;
      r.sl           = l;
      r.deviation    = Slippage;
      r.type_filling = ORDER_FILLING_RETURN;

      OrderSend(r,s);
   }
}
