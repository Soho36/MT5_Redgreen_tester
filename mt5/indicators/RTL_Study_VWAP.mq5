// Historical overlay: legacy M30 decision values or daily/monthly VWAP labels.
#property strict
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots 2
#property indicator_label1 "Decision VWAP (last completed M30)"
#property indicator_type1 DRAW_LINE
#property indicator_color1 clrDodgerBlue
#property indicator_width1 2
#property indicator_label2 "Decision VWAP minus A20"
#property indicator_type2 DRAW_LINE
#property indicator_color2 clrDarkOrange
#property indicator_style2 STYLE_DASH
#property indicator_width2 1

input string FeatureFile="rtl_vwap_replay_20261026_features.csv";
input bool DailyDecisionAtOpen=false; // D1 only: false=completed day's values, true=EA's next-day decision values
double VwapLine[],LowerLine[],Values[],Ranges[];
double Closes[];
datetime Available[],Sessions[],LabelBars[];
bool Known[];
int Count=0;
bool Daily=false;

int MonthKey(datetime value)
{
   MqlDateTime dt;TimeToStruct(value,dt);
   return dt.year*100+dt.mon;
}

int OnInit()
{
   Count=0;
   if((_Symbol!="MNQcontDTBNT20102026_2" && _Symbol!="MNQcontDTBNT20261114") ||
      (_Period!=PERIOD_M30 && _Period!=PERIOD_D1))
   { Print("RTL Study VWAP requires the matching historical MNQ custom symbol on M30 or D1."); return INIT_FAILED; }
   SetIndexBuffer(0,VwapLine,INDICATOR_DATA);
   SetIndexBuffer(1,LowerLine,INDICATOR_DATA);
   ArraySetAsSeries(VwapLine,false); ArraySetAsSeries(LowerLine,false);
   for(int p=0;p<2;p++) PlotIndexSetDouble(p,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   IndicatorSetString(INDICATOR_SHORTNAME,"RTL study VWAP / cutoff (available at bar open)");
   IndicatorSetInteger(INDICATOR_DIGITS,2);
   int h=FileOpen(FeatureFile,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(h==INVALID_HANDLE) { Print("Missing frozen VWAP feature file: ",FeatureFile); return INIT_FAILED; }
   string first=FileReadString(h);
   Daily=(first=="date");
   string names[7]={"available_epoch","session_epoch","bar_epoch","close","vwap","a20","known"};
   if(Daily) {names[0]="date";names[1]="available";names[2]="month";}
   if(first!=names[0] || (Daily && _Period!=PERIOD_D1) || (!Daily && _Period!=PERIOD_M30))
   { Print("VWAP file format/timeframe mismatch: daily monthly file requires D1; legacy file requires M30.");FileClose(h);return INIT_FAILED; }
   for(int k=1;k<7;k++)
      if(FileReadString(h)!=names[k]) { Print("Unexpected VWAP file header at column ",k+1);FileClose(h); return INIT_FAILED; }
   if(Daily)
   {
      IndicatorSetString(INDICATOR_SHORTNAME,DailyDecisionAtOpen ? "Monthly VWAP / daily A20 (decision at open)" : "Monthly VWAP / daily A20 (completed day)");
      PlotIndexSetString(0,PLOT_LABEL,"Monthly VWAP");
      PlotIndexSetString(1,PLOT_LABEL,"Monthly VWAP minus daily A20");
   }
   while(!FileIsEnding(h))
   {
      datetime x=(datetime)FileReadNumber(h);
      if(x==0 && FileIsEnding(h)) break;
      long y=(long)FileReadNumber(h),z=(long)FileReadNumber(h);
      datetime at=Daily ? (datetime)y : x;
      datetime bar=Daily ? x : (datetime)z;
      datetime session=Daily ? (datetime)z : (datetime)y;
      double close=FileReadNumber(h),vwap=FileReadNumber(h),a20=FileReadNumber(h);
      bool known=(FileReadNumber(h)==1);
      bool invalidPeriod=Daily ? (at!=bar+86400 || bar%86400!=0 || z!=MonthKey(bar)) :
                                  (at!=bar+1800 || session!=bar-bar%86400);
      if(invalidPeriod || (Count>0 && at<=Available[Count-1]) ||
         !MathIsValidNumber(close) || !MathIsValidNumber(vwap) || !MathIsValidNumber(a20) ||
         close<=0 || (known && (vwap<=0 || a20<=0)))
      { Print("Invalid VWAP feature row ",Count+1);FileClose(h); return INIT_FAILED; }
      ArrayResize(Available,Count+1,20000); ArrayResize(Sessions,Count+1,20000);
      ArrayResize(Values,Count+1,20000); ArrayResize(Ranges,Count+1,20000); ArrayResize(Known,Count+1,20000);
      ArrayResize(LabelBars,Count+1,20000);ArrayResize(Closes,Count+1,20000);
      Available[Count]=at; Sessions[Count]=session; Values[Count]=vwap; Ranges[Count]=a20; Known[Count]=known;
      LabelBars[Count]=bar;Closes[Count]=close;
      Count++;
   }
   FileClose(h);
   Print("Loaded ",Count," ",Daily ? "daily/monthly" : "M30/session"," VWAP rows from Common\\Files\\",FeatureFile);
   return Count>0 ? INIT_SUCCEEDED : INIT_FAILED;
}

int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],
                const double &open[],const double &high[],const double &low[],const double &close[],
                const long &tick_volume[],const long &volume[],const int &spread[])
{
   ArraySetAsSeries(time,false);
   ArraySetAsSeries(close,false);
   int begin=(prev_calculated>0 && prev_calculated<=rates_total) ? prev_calculated-1 : 0;
   for(int i=begin;i<rates_total;i++)
   {
      VwapLine[i]=EMPTY_VALUE; LowerLine[i]=EMPTY_VALUE;
      // Daily close mode plots a label on its own completed candle. Open mode
      // preserves the legacy causal decision overlay and the session-reset gap.
      datetime bound=(Daily && !DailyDecisionAtOpen) ? time[i]+86400 : time[i];
      int left=0,right=Count-1,j=-1;
      while(left<=right)
      {
         int mid=(left+right)/2;
         if(Available[mid]<=bound) { j=mid; left=mid+1; } else right=mid-1;
      }
      if(j<0) continue;
      if(Daily && !DailyDecisionAtOpen)
      {
         if(LabelBars[j]!=time[i] || Available[j]>TimeCurrent()) continue;
         if(MathAbs(Closes[j]-close[i])>_Point) continue; // wrong/mismatched historical chart
         VwapLine[i]=Values[j]; // VWAP exists even during A20 warm-up
         if(Known[j]) LowerLine[i]=Values[j]-Ranges[j];
      }
      else if(Daily)
      {
         if(i==0 || LabelBars[j]!=time[i-1] || Sessions[j]!=MonthKey(time[i]) || !Known[j]) continue;
         if(MathAbs(Closes[j]-close[i-1])>_Point) continue;
         VwapLine[i]=Values[j];LowerLine[i]=Values[j]-Ranges[j];
      }
      else if(Known[j] && Sessions[j]==time[i]-time[i]%86400)
      { VwapLine[i]=Values[j]; LowerLine[i]=Values[j]-Ranges[j]; }
   }
   return rates_total;
}
