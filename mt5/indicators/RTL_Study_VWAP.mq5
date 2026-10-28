// Historical study overlay: values available at each M30 bar's opening time.
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
double VwapLine[],LowerLine[],Values[],Ranges[];
datetime Available[],Sessions[];
bool Known[];
int Count=0;

int OnInit()
{
   if(_Symbol!="MNQcontDTBNT20102026_2" || _Period!=PERIOD_M30)
   { Print("RTL Study VWAP requires MNQcontDTBNT20102026_2, M30; this is a fixed historical dataset."); return INIT_FAILED; }
   SetIndexBuffer(0,VwapLine,INDICATOR_DATA);
   SetIndexBuffer(1,LowerLine,INDICATOR_DATA);
   ArraySetAsSeries(VwapLine,false); ArraySetAsSeries(LowerLine,false);
   for(int p=0;p<2;p++) PlotIndexSetDouble(p,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   IndicatorSetString(INDICATOR_SHORTNAME,"RTL study VWAP / cutoff (available at bar open)");
   IndicatorSetInteger(INDICATOR_DIGITS,2);
   int h=FileOpen(FeatureFile,FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,'\t');
   if(h==INVALID_HANDLE) { Print("Missing frozen VWAP feature file: ",FeatureFile); return INIT_FAILED; }
   string names[7]={"available_epoch","session_epoch","bar_epoch","close","vwap","a20","known"};
   for(int k=0;k<7;k++)
      if(FileReadString(h)!=names[k]) { FileClose(h); return INIT_FAILED; }
   while(!FileIsEnding(h))
   {
      datetime at=(datetime)FileReadNumber(h);
      if(at==0 && FileIsEnding(h)) break;
      datetime session=(datetime)FileReadNumber(h),bar=(datetime)FileReadNumber(h);
      double close=FileReadNumber(h),vwap=FileReadNumber(h),a20=FileReadNumber(h);
      bool known=(FileReadNumber(h)==1);
      if(at!=bar+1800 || session!=bar-bar%86400 || (Count>0 && at<=Available[Count-1]) ||
         close<=0 || (known && (vwap<=0 || a20<=0)))
      { FileClose(h); return INIT_FAILED; }
      ArrayResize(Available,Count+1,20000); ArrayResize(Sessions,Count+1,20000);
      ArrayResize(Values,Count+1,20000); ArrayResize(Ranges,Count+1,20000); ArrayResize(Known,Count+1,20000);
      Available[Count]=at; Sessions[Count]=session; Values[Count]=vwap; Ranges[Count]=a20; Known[Count]=known;
      Count++;
   }
   FileClose(h);
   return Count>0 ? INIT_SUCCEEDED : INIT_FAILED;
}

int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],
                const double &open[],const double &high[],const double &low[],const double &close[],
                const long &tick_volume[],const long &volume[],const int &spread[])
{
   ArraySetAsSeries(time,false);
   int begin=(prev_calculated>0 && prev_calculated<=rates_total) ? prev_calculated-1 : 0;
   for(int i=begin;i<rates_total;i++)
   {
      VwapLine[i]=EMPTY_VALUE; LowerLine[i]=EMPTY_VALUE;
      // Bound lookup by the chart bar's OPEN, never the computer clock.
      int left=0,right=Count-1,j=-1;
      while(left<=right)
      {
         int mid=(left+right)/2;
         if(Available[mid]<=time[i]) { j=mid; left=mid+1; } else right=mid-1;
      }
      if(j>=0 && Known[j] && Sessions[j]==time[i]-time[i]%86400)
      { VwapLine[i]=Values[j]; LowerLine[i]=Values[j]-Ranges[j]; }
   }
   return rates_total;
}
