// Candle-low buy limit, fixed 1:1, any colour. Strategy Tester only.
#property strict
#include <Trade/Trade.mqh>
#include "early_closes.mqh"
input double Lots = 1.0;
input string RunTag = "candlelow_20261123";
CTrade trade;
datetime lastBar=0, previousDate=0, lastFlat=0;
int placed=0, skipped=0, rejected=0;

int Cutoff(datetime bar)
{
   MqlDateTime d; TimeToStruct(bar,d);
   int key=d.year*10000+d.mon*100+d.day;
   for(int i=0;i<EC_COUNT;i++) if(EC_DATE[i]==key) return EC_FLAT_MIN[i];
   return 1410;
}
void Cancel()
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong id=OrderGetTicket(i);
      if(id && OrderGetString(ORDER_SYMBOL)==_Symbol)
         if(!trade.OrderDelete(id)) Print("Cancel failed ",trade.ResultRetcode());
   }
}
void Flatten()
{
   Cancel();
   if(PositionSelect(_Symbol))
      if(!trade.PositionClose(_Symbol)) Print("Close failed ",trade.ResultRetcode());
}
int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || !SymbolInfoInteger(_Symbol,SYMBOL_CUSTOM)) return INIT_FAILED;
   if(Lots<=0 || _Period!=PERIOD_M30) return INIT_PARAMETERS_INCORRECT;
   trade.SetDeviationInPoints(5);
   trade.SetTypeFilling(ORDER_FILLING_RETURN);
   return INIT_SUCCEEDED;
}
void OnTick()
{
   datetime bar=iTime(_Symbol,_Period,0);
   if(bar==lastBar) return;
   lastBar=bar;
   datetime date=bar-bar%86400;
   if(previousDate && date!=previousDate && lastFlat!=previousDate)
   {
      lastFlat=previousDate;
      Flatten();
   }
   previousDate=date;
   int minute=(int)((bar-date)/60);
   if(minute>=Cutoff(bar))
   {
      if(lastFlat!=date) { lastFlat=date; Flatten(); }
      return;
   }
   if(PositionSelect(_Symbol)) return;
   Cancel();
   if(minute<60 || Bars(_Symbol,_Period)<2) return;
   double low=iLow(_Symbol,_Period,1), high=iHigh(_Symbol,_Period,1);
   double range=high-low;
   if(range<=0) return;
   if(low>=SymbolInfoDouble(_Symbol,SYMBOL_ASK)) { skipped++; return; }
   double stop=NormalizeDouble(low-range,_Digits);
   if(!trade.BuyLimit(Lots,low,_Symbol,stop,high,ORDER_TIME_GTC,0,"candle low 1R")
      || (trade.ResultRetcode()!=TRADE_RETCODE_DONE && trade.ResultRetcode()!=TRADE_RETCODE_PLACED)) rejected++;
   else placed++;
}
double OnTester()
{
   int f=FileOpen(RunTag+"_stats.csv",FILE_WRITE|FILE_CSV|FILE_COMMON);
   if(f==INVALID_HANDLE) return 0;
   FileWrite(f,"trades","gross","equity_dd_gross","balance_dd_gross","placed","skipped","rejected");
   FileWrite(f,(int)TesterStatistics(STAT_TRADES),TesterStatistics(STAT_PROFIT),
      TesterStatistics(STAT_EQUITY_DD),TesterStatistics(STAT_BALANCE_DD),placed,skipped,rejected);
   FileClose(f);
   return 0;
}
