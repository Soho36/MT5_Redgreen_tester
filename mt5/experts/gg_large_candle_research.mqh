// Tester-only GG midpoint stop experiment; baseline source stays unchanged.
input bool UseLargeCandleStop = false;
input double LargeCandleRatio = 3.0;
input int LargeCandleMinPrior = 5;
int gl_file = INVALID_HANDLE;

bool LargeCandleInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || _Period != PERIOD_M30) return false;
   if(!MathIsValidNumber(LargeCandleRatio) || LargeCandleRatio <= 1.0
      || LargeCandleMinPrior < 1) return false;
   gl_file = FileOpen("large_candle_" + g_runTag + ".tsv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   if(gl_file == INVALID_HANDLE) return false;
   FileWrite(gl_file,"time","signal_bar","high","low","prior_count","median","ratio","tightened","stop");
   return true;
}

double LargeCandleStop(double high, double low)
{
   datetime signal = iTime(_Symbol,_Period,1);
   datetime signalClock = SessionClock(signal);
   datetime currentClock = SessionClock(iTime(_Symbol,_Period,0));
   datetime date = signalClock - signalClock % 86400;
   double ranges[];
   int count = 0;
   // At most 48 half-hours per calendar date. Never include signal (shift 1).
   if(date == currentClock-currentClock%86400 && signalClock-date >= 3600)
   {
      for(int shift=2; shift<=50; shift++)
      {
         datetime prior = iTime(_Symbol,_Period,shift);
         if(prior == 0) break;
         datetime clock = SessionClock(prior);
         if(clock < date+3600) break;
         if(clock >= signalClock) continue;
         double width = iHigh(_Symbol,_Period,shift)-iLow(_Symbol,_Period,shift);
         if(width < 0 || !MathIsValidNumber(width)) continue;
         ArrayResize(ranges,count+1);
         ranges[count++] = width;
      }
   }
   double median = 0, ratio = 0, stop = low;
   if(count > 0)
   {
      ArraySort(ranges);
      median = (count%2 == 1) ? ranges[count/2]
         : (ranges[count/2-1]+ranges[count/2])/2.0;
      if(median > 0) ratio = (high-low)/median;
   }
   bool tighten = UseLargeCandleStop && count >= LargeCandleMinPrior && median > 0
      && high-low+1e-9 >= LargeCandleRatio*median;
   if(tighten)
   {
      double tick = SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
      stop = NormalizeDouble(MathRound(((high+low)/2.0)/tick)*tick,_Digits);
      stop = MathMax(low,MathMin(stop,NormalizeDouble(high-tick,_Digits)));
   }
   FileWrite(gl_file,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
      TimeToString(signal,TIME_DATE|TIME_SECONDS),DoubleToString(high,8),
      DoubleToString(low,8),count,DoubleToString(median,8),DoubleToString(ratio,12),
      (int)tighten,DoubleToString(stop,8));
   return stop;
}

