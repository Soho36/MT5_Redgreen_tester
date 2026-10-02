// Research-only hooks used by python/prepare_averaging_study.py.
// Netting account, one basket, original protective stop, one add at most.
input double AverageNearStopR = 0.0; // 0 disables; otherwise fraction above SL
input bool AverageTarget = false;   // bar-close target from current average entry
ulong g_addTicket = 0;
bool g_addAttempted = false;
double g_addLimit = 0.0;
int g_addStatus = 0; // 0 off, 1 accepted, 2 invalid level, 3 rejected
int g_addRejected = 0;
int g_addSkipped = 0;
int g_addPlaced = 0;
int g_cancelErrors = 0;
int g_orphanCloseErrors = 0;

// A single synthetic tick (or a real gap) can execute the parent's SL before
// the add limit. Transaction callbacks cannot interpose between those fills.
// Never let that replacement position survive as a new independent trade.
bool CloseOrphanedAdd()
{
   if(!g_tracking || !PositionSelect(_Symbol)) return true;
   if((ulong)PositionGetInteger(POSITION_IDENTIFIER)==g_ticket) return true;
   MqlTradeRequest req = {};
   MqlTradeResult res = {};
   req.action=TRADE_ACTION_DEAL;
   req.symbol=_Symbol;
   req.position=(ulong)PositionGetInteger(POSITION_TICKET);
   req.volume=PositionGetDouble(POSITION_VOLUME);
   req.type=ORDER_TYPE_SELL;
   req.price=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   req.deviation=Slippage;
   if(!OrderSend(req,res) || res.retcode!=TRADE_RETCODE_DONE)
   {
      g_orphanCloseErrors++;
      Print("AVERAGE_ORPHAN_CLOSE_ERROR retcode=",res.retcode);
      return false;
   }
   return !PositionSelect(_Symbol);
}

void CancelAveragingOrder()
{
   if(g_addTicket == 0 || !OrderSelect(g_addTicket)) return;
   MqlTradeRequest req = {};
   MqlTradeResult res = {};
   req.action = TRADE_ACTION_REMOVE;
   req.order = g_addTicket;
   if(!OrderSend(req, res) || res.retcode != TRADE_RETCODE_DONE)
   {
      g_cancelErrors++;
      Print("AVERAGE_CANCEL_ERROR ticket=", g_addTicket, " retcode=", res.retcode);
   }
}

void PlaceAveragingOrder()
{
   if(AverageNearStopR <= 0 || g_addAttempted || !g_initialSet) return;
   if(!PositionSelect(_Symbol)) return;
   g_addAttempted = true;
   double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double stop = g_initialEntry - g_initialRisk;
   g_addLimit = NormalizeDouble(MathCeil((stop + AverageNearStopR * g_initialRisk) / tick - 1e-8) * tick, _Digits);
   g_addLimit = MathMax(g_addLimit, NormalizeDouble(stop + tick, _Digits));
   double gap = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(g_addLimit >= g_initialEntry || g_addLimit >= ask || g_addLimit - stop < gap || ask - g_addLimit < gap)
   {
      g_addSkipped++;
      g_addStatus = 2;
      Print("AVERAGE_SKIP limit=", g_addLimit, " stop=", stop, " ask=", ask);
      return;
   }
   MqlTradeRequest req = {};
   MqlTradeResult res = {};
   req.action = TRADE_ACTION_PENDING;
   req.symbol = _Symbol;
   req.volume = Lots;
   req.type = ORDER_TYPE_BUY_LIMIT;
   req.price = g_addLimit;
   req.sl = stop;
   req.deviation = Slippage;
   req.type_filling = ORDER_FILLING_RETURN;
   req.comment = "near_stop_add";
   if(!OrderSend(req, res) || (res.retcode != TRADE_RETCODE_DONE && res.retcode != TRADE_RETCODE_PLACED))
   {
      g_addRejected++;
      g_addStatus = 3;
      Print("AVERAGE_REJECT retcode=", res.retcode);
      return;
   }
   g_addTicket = res.order;
   g_addStatus = 1;
   g_addPlaced++;
}

// One row per flat-to-flat basket. Scan every deal (including partial exits).
void SaveAveragingBasket()
{
   if(!g_tracking || PositionSelect(_Symbol)) return;
   CancelAveragingOrder();
   if(!HistorySelect(g_entryTime-1, TimeCurrent())) return;
   double gross=0, costs=0, baseVol=0, addVol=0, outVol=0;
   double baseValue=0, addValue=0, outValue=0;
   double parentOutVol=0, parentOutValue=0, orphanOutVol=0, orphanOutValue=0;
   ulong firstOrder=0;
   datetime exitTime=0, addTime=0;
   datetime baseExitTime=0;
   long exitReason=0;
   int entryDeals=0;
   int exitDeals=0;
   for(int i=0; i<HistoryDealsTotal(); i++)
   {
      ulong deal=HistoryDealGetTicket(i);
      ulong position=(ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID);
      if(position!=g_ticket && (g_addTicket==0 || position!=g_addTicket)) continue;
      long entry=HistoryDealGetInteger(deal, DEAL_ENTRY);
      double volume=HistoryDealGetDouble(deal, DEAL_VOLUME);
      double price=HistoryDealGetDouble(deal, DEAL_PRICE);
      gross += HistoryDealGetDouble(deal, DEAL_PROFIT);
      costs += HistoryDealGetDouble(deal, DEAL_COMMISSION) + HistoryDealGetDouble(deal, DEAL_FEE) + HistoryDealGetDouble(deal, DEAL_SWAP);
      if(entry == DEAL_ENTRY_IN)
      {
         entryDeals++;
         ulong order=(ulong)HistoryDealGetInteger(deal, DEAL_ORDER);
         if(firstOrder==0) firstOrder=order;
         if(order==firstOrder) { baseVol+=volume; baseValue+=volume*price; }
         else
         {
            addVol+=volume; addValue+=volume*price;
            if(addTime==0) addTime=(datetime)HistoryDealGetInteger(deal, DEAL_TIME);
         }
      }
      else if(entry == DEAL_ENTRY_OUT)
      {
         exitDeals++;
         outVol+=volume; outValue+=volume*price;
         exitTime=(datetime)HistoryDealGetInteger(deal, DEAL_TIME);
         exitReason=HistoryDealGetInteger(deal, DEAL_REASON);
         if(position==g_ticket)
         {
            parentOutVol+=volume; parentOutValue+=volume*price;
            baseExitTime=exitTime;
         }
         else { orphanOutVol+=volume; orphanOutValue+=volume*price; }
      }
   }
   if(exitTime==0 || baseVol<=0 || outVol<=0) return;
   double basePrice=baseValue/baseVol, addPrice=(addVol>0 ? addValue/addVol : 0);
   if(parentOutVol<=0) return;
   double exitPrice=parentOutValue/parentOutVol, baseProfit=0, addProfit=0;
   double addExitPrice=(orphanOutVol>0 ? orphanOutValue/orphanOutVol : exitPrice);
   if(!OrderCalcProfit(ORDER_TYPE_BUY, _Symbol, baseVol, basePrice, exitPrice, baseProfit))
      { Print("AVERAGE_CALC_ERROR base"); return; }
   if(addVol>0 && !OrderCalcProfit(ORDER_TYPE_BUY, _Symbol, addVol, addPrice, addExitPrice, addProfit))
      { Print("AVERAGE_CALC_ERROR add"); return; }
   double stop=g_initialEntry-g_initialRisk;
   double initialRiskMoney=0;
   if(!OrderCalcProfit(ORDER_TYPE_BUY, _Symbol, baseVol, basePrice, stop, initialRiskMoney))
      { Print("AVERAGE_CALC_ERROR risk"); return; }
   double plannedAddRisk=0;
   if(g_addStatus==1 && !OrderCalcProfit(ORDER_TYPE_BUY, _Symbol, Lots, g_addLimit, stop, plannedAddRisk))
      { Print("AVERAGE_CALC_ERROR planned"); return; }
   int f=FileOpen(g_csvName, FILE_READ|FILE_WRITE|FILE_CSV|FILE_SHARE_WRITE|FILE_COMMON);
   if(f==INVALID_HANDLE) { Print("AVERAGE_EXPORT_ERROR"); return; }
   if(FileSize(f)<=2)
      FileWrite(f,"ticket","entry_time","exit_time","mae_money","mfe_money","trade_profit","candle_range","red_run","location",
         "base_volume","add_volume","exit_volume","base_entry","add_entry","exit_price","initial_stop","initial_risk_money",
         "planned_add_risk","base_profit","add_profit","broker_costs","add_time","add_limit","add_status","exit_reason","entry_deals",
         "exit_deals","base_exit_time","add_exit_price","orphan_volume");
   FileSeek(f,0,SEEK_END);
   FileWrite(f,(long)g_ticket,TimeToString(g_entryTime,TIME_DATE|TIME_SECONDS),TimeToString(exitTime,TIME_DATE|TIME_SECONDS),
      MathMin(g_maeMoney,gross),MathMax(g_mfeMoney,gross),gross,g_candleRange,g_redRun,DoubleToString(g_location,10),
      baseVol,addVol,outVol,basePrice,addPrice,exitPrice,stop,-initialRiskMoney,-plannedAddRisk,baseProfit,addProfit,costs,
      (addTime>0 ? TimeToString(addTime,TIME_DATE|TIME_SECONDS) : ""),g_addLimit,g_addStatus,exitReason,entryDeals,
      exitDeals,TimeToString(baseExitTime,TIME_DATE|TIME_SECONDS),addExitPrice,orphanOutVol);
   FileClose(f);
   g_tracking=false;
}

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   // A stopped-out parent must not leave a resting limit that reopens a basket.
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD && trans.symbol==_Symbol && !PositionSelect(_Symbol))
      CancelAveragingOrder();
}
