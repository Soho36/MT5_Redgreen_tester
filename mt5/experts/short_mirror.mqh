// Q23 short mirror of the RTL entry (research only). Frozen protocol: docs/levels/SUPPORT_BREAKDOWN_PROTOCOL.md.
// Stage 0 population: the last closed M30 candle is green (close > open) with a green run within the parent's
// MinRedRun..MaxRedRun band (1..3) -> sell stop at its low, stop loss at its high, replacing the pending sell stop.
// A red or doji candle leaves the pending order alone, as a green one does in the parent. A rejected green signal
// cancels the pending order, as the parent's rejection does. The parent manages the short with SMManageShort
// (buy to cover after the first bar that closes <= entry - RiskReward x R) and records it in the direction-aware
// ledger (Q21 patches). Requires the parent's g_dir. MinLocation must be 0 (the location filter is not mirrored).

int g_smPlaced = 0, g_smSendFailed = 0, g_smRejected = 0, g_smCancelErrors = 0;

bool SMInit()
{
   return (MinLocation == 0.0);
}

void SMDeinit()
{
   int f = FileOpen(g_runTag + "_short_stats.csv", FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(f == INVALID_HANDLE) return;
   FileWrite(f, "placed", "send_failed", "run_rejected", "cancel_errors", "close_errors", "export_errors");
   FileWrite(f, g_smPlaced, g_smSendFailed, g_smRejected, g_smCancelErrors, tr_closeErrors, tr_exportErrors);
   FileClose(f);
}

// Consecutive green candles ending at the last CLOSED candle (index 1); 0 if index 1 is not green.
int ConsecutiveGreenRun()
{
   int count = 0;
   int bars  = Bars(_Symbol, _Period);
   for(int i = 1; i < bars && i <= 500; i++)
   {
      if(iClose(_Symbol, _Period, i) > iOpen(_Symbol, _Period, i)) count++;
      else break;
   }
   return count;
}

void CancelOldSellStops()
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0 || !OrderSelect(ticket)) continue;
      if((int)OrderGetInteger(ORDER_TYPE) != ORDER_TYPE_SELL_STOP) continue;
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action = TRADE_ACTION_REMOVE;
      req.order  = ticket;
      if(!OrderSend(req, res) || res.retcode != TRADE_RETCODE_DONE) g_smCancelErrors++;
   }
}

// The parent's ManageOpenPosition for a short: buy to cover after the first bar that closes <= entry - RR x R.
void SMManageShort(double vol)
{
   if(!g_initialSet || g_initialRisk <= 0.0 || g_dir != -1)
   {
      Print("Initial short reference not set -> skipping TP logic");
      return;
   }
   double barClose = iClose(_Symbol, _Period, 1);
   double target = g_initialEntry - g_initialRisk * tr_rr;
   LogTrendCheck(barClose, target);
   if(barClose <= target)
   {
      CancelAveragingOrder();
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action    = TRADE_ACTION_DEAL;
      req.symbol    = _Symbol;
      req.volume    = vol;
      req.type      = ORDER_TYPE_BUY;
      req.price     = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      req.deviation = Slippage;
      if(!OrderSend(req, res) || res.retcode != TRADE_RETCODE_DONE)
      { tr_closeErrors++; Print("TREND_CLOSE_ERROR ", res.retcode); }
   }
}

// The mirrored entry: the tail of the parent's OnTick (flat, inside a trade window, before the flatten).
void SMOnBar(datetime barOpen)
{
   double o1 = iOpen(_Symbol, _Period, 1);
   double h1 = iHigh(_Symbol, _Period, 1);
   double l1 = iLow(_Symbol, _Period, 1);
   double c1 = iClose(_Symbol, _Period, 1);
   if(!IsCandleInRange(h1, l1))
   {
      CancelOldSellStops();
      return;
   }
   if(c1 > o1)
   {
      int run    = ConsecutiveGreenRun();
      int minRun = (MinRedRun < 1) ? 1 : MinRedRun;
      if(run < minRun || (MaxRedRun > 0 && run > MaxRedRun))
      {
         g_smRejected++;
         CancelOldSellStops();
         return;
      }
      CancelOldSellStops();
      double entry = l1;
      double stop  = h1;
      double risk  = stop - entry;
      g_candleRange = h1 - l1;
      g_redRun      = run;   // the green run, logged in the red_run column
      g_location    = 0.0;
      if(risk <= 0.0) return;
      LogTrendSignal();
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action       = TRADE_ACTION_PENDING;
      req.symbol       = _Symbol;
      req.volume       = Lots;
      req.type         = ORDER_TYPE_SELL_STOP;
      req.price        = entry;
      req.sl           = stop;
      req.deviation    = Slippage;
      req.type_filling = ORDER_FILLING_RETURN;
      if(!OrderSend(req, res) || res.retcode != TRADE_RETCODE_DONE) g_smSendFailed++;
      else g_smPlaced++;
   }
}
