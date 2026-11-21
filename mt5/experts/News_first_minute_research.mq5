#property strict
#include <Trade/Trade.mqh>
#include "news_first_minute_dates.mqh"
#include "early_closes.mqh"
input int NewsMask=3;
input string RunTag="news_first_minute";
string g_runTag;
#include "window_equity_research.mqh"
CTrade trade;
int decisions=INVALID_HANDLE;
datetime attempted=0;
int DateKey(datetime t) {MqlDateTime d;TimeToStruct(t,d);return d.year*10000+d.mon*100+d.day;}
int Mask(int date) {
   int lo=0,hi=ArraySize(NEWS_DATE)-1;
   while(lo<=hi) {int m=(lo+hi)/2;if(NEWS_DATE[m]==date)return NEWS_FLAGS[m];if(NEWS_DATE[m]<date)lo=m+1;else hi=m-1;}
   return 0;
}
int Cutoff(int date) {for(int i=0;i<EC_COUNT;i++)if(EC_DATE[i]==date)return EC_FLAT_MIN[i];return 1410;}
int OnInit() {
   if(!MQLInfoInteger(MQL_TESTER) || _Symbol!="MNQcontDTBNT20102026_2" || _Period!=PERIOD_M1 || NewsMask<1 || NewsMask>3)return INIT_PARAMETERS_INCORRECT;
   g_runTag=RunTag;trade.SetExpertMagicNumber(20261122);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(0);
   decisions=FileOpen("decisions_"+RunTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(decisions==INVALID_HANDLE || !WindowEquityInit())return INIT_FAILED;
   FileWrite(decisions,"time","date","mask","status","open","high","low","close","bid","ask","direction","sl","tp","retcode","deal","stops_distance");
   return INIT_SUCCEEDED;
}
void StrategyTick() {
   datetime now=TimeCurrent(),day=now-now%86400;int date=DateKey(now),minute=(int)((now-day)/60);
   if(PositionSelect(_Symbol)) {
      datetime entry=(datetime)PositionGetInteger(POSITION_TIME);
      if(entry-entry%86400!=day || minute>=Cutoff(date)) {
         if(!trade.PositionClose(_Symbol) || trade.ResultRetcode()!=TRADE_RETCODE_DONE) {Print("NEWS_CLOSE_ERROR");ExpertRemove();}
      }
   }
   int mask=Mask(date)&NewsMask;
   if(mask==0 || attempted==day || minute<931)return;
   attempted=day;
   MqlTick tick;SymbolInfoTick(_Symbol,tick);
   MqlRates bar[1];int copied=CopyRates(_Symbol,PERIOD_M1,day+930*60,day+930*60,bar);
   double o=0,h=0,l=0,c=0,sl=0,tp=0;int direction=0;string status="";uint ret=0;ulong deal=0;
   double distance=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if(copied==1 && bar[0].time==day+930*60) {o=bar[0].open;h=bar[0].high;l=bar[0].low;c=bar[0].close;}
   if(minute!=931)status="missing_entry_minute";
   else if(copied!=1 || bar[0].time!=day+930*60)status="missing_signal";
   else if(c==o)status="doji";
   else {
      direction=c>o?1:-1;sl=direction==1?l:h;tp=direction==1?h:l;
      double entry=direction==1?tick.ask:tick.bid;
      double closing=direction==1?tick.bid:tick.ask;
      if(direction*(tp-c)<=0)status="zero_target_wick";
      else if(direction*(tp-entry)<=0 || direction*(entry-sl)<=0)status="invalid_entry_levels";
      else if(direction*(tp-closing)<distance || direction*(closing-sl)<distance)status="broker_stop_distance";
      else if(PositionsTotal()>0)status="existing_position";
      else {
         bool ok=direction==1?trade.Buy(1.0,_Symbol,0,sl,tp,"news first minute"):trade.Sell(1.0,_Symbol,0,sl,tp,"news first minute");
         ret=trade.ResultRetcode();deal=trade.ResultDeal();
         status=ok && ret==TRADE_RETCODE_DONE && deal>0?"entered":"rejected";
      }
   }
   FileWrite(decisions,TimeToString(now,TIME_DATE|TIME_SECONDS),date,mask,status,o,h,l,c,tick.bid,tick.ask,direction,sl,tp,ret,deal,distance);
}
void OnTick() {WindowEquitySample();StrategyTick();WindowEquitySample();}
void OnTradeTransaction(const MqlTradeTransaction &t,const MqlTradeRequest &q,const MqlTradeResult &r) {WindowEquityTransaction(t);}
double OnTester() {
   HistorySelect(0,TimeCurrent());
   int f=FileOpen("deals_"+RunTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   FileWrite(f,"deal","position","time","entry","type","price","volume","profit","commission","swap","reason","sl","tp");
   for(int i=0;i<HistoryDealsTotal();i++) {
      ulong d=HistoryDealGetTicket(i);if(HistoryDealGetString(d,DEAL_SYMBOL)!=_Symbol)continue;
      FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),TimeToString((datetime)HistoryDealGetInteger(d,DEAL_TIME),TIME_DATE|TIME_SECONDS),
         HistoryDealGetInteger(d,DEAL_ENTRY),HistoryDealGetInteger(d,DEAL_TYPE),HistoryDealGetDouble(d,DEAL_PRICE),HistoryDealGetDouble(d,DEAL_VOLUME),
         HistoryDealGetDouble(d,DEAL_PROFIT),HistoryDealGetDouble(d,DEAL_COMMISSION),HistoryDealGetDouble(d,DEAL_SWAP),HistoryDealGetInteger(d,DEAL_REASON),HistoryDealGetDouble(d,DEAL_SL),HistoryDealGetDouble(d,DEAL_TP));
   }
   FileClose(f);
   f=FileOpen("stats_"+RunTag+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   FileWrite(f,"trades","profit","equity_dd","balance_dd");
   FileWrite(f,TesterStatistics(STAT_TRADES),TesterStatistics(STAT_PROFIT),TesterStatistics(STAT_EQUITY_DD),TesterStatistics(STAT_BALANCE_DD));FileClose(f);
   return TesterStatistics(STAT_PROFIT);
}
void OnDeinit(const int reason) {WindowEquityClose();if(decisions!=INVALID_HANDLE)FileClose(decisions);}
