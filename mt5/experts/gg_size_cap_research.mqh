// Tester-only GG size-cap experiment; baseline source stays unchanged.
// A green signal whose range is at least SizeCapRatio times the median range
// of the earlier M30 bars of the same session is rejected.
input bool UseSizeCap = false;
input double SizeCapRatio = 5.0;
input int SizeCapMinPrior = 5;
int sc_file = INVALID_HANDLE;

bool SizeCapInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || _Period != PERIOD_M30) return false;
   if(!MathIsValidNumber(SizeCapRatio) || SizeCapRatio <= 1.0
      || SizeCapMinPrior < 1) return false;
   sc_file = FileOpen("size_cap_" + g_runTag + ".tsv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   if(sc_file == INVALID_HANDLE) return false;
   FileWrite(sc_file,"time","signal_bar","high","low","prior_count","median","ratio","capped");
   return true;
}

// Logs every candidate decision; true when the just-closed signal is rejected.
bool SizeCapReject(double high, double low)
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
   double median = 0, ratio = 0;
   if(count > 0)
   {
      ArraySort(ranges);
      median = (count%2 == 1) ? ranges[count/2]
         : (ranges[count/2-1]+ranges[count/2])/2.0;
      if(median > 0) ratio = (high-low)/median;
   }
   bool capped = UseSizeCap && count >= SizeCapMinPrior && median > 0
      && high-low+1e-9 >= SizeCapRatio*median;
   FileWrite(sc_file,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
      TimeToString(signal,TIME_DATE|TIME_SECONDS),DoubleToString(high,8),
      DoubleToString(low,8),count,DoubleToString(median,8),DoubleToString(ratio,12),
      (int)capped);
   return capped;
}
