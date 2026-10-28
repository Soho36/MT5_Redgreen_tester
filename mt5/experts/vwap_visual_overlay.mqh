// Display-only helper for the manual tester copy; never changes trading state.
input bool ShowStudyOverlay=true;
int g_visualHandle=INVALID_HANDLE;
int g_visualChecks=0,g_visualErrors=0;

bool StudyVisualInit()
{
   if(!ShowStudyOverlay) return true;
   g_visualHandle=iCustom(_Symbol,PERIOD_M30,"CodexVwapVisual\\RTL_Study_VWAP",VwapReplayFeatures);
   if(g_visualHandle==INVALID_HANDLE) { Print("Study indicator could not load: ",GetLastError()); return false; }
   if(MQLInfoInteger(MQL_VISUAL_MODE))
   {
      if(!ChartIndicatorAdd(0,0,g_visualHandle)) { Print("Study overlay attachment failed: ",GetLastError()); return false; }
      ChartSetInteger(0,CHART_SHOW_TRADE_HISTORY,true);
      ChartSetInteger(0,CHART_SHOW_TRADE_LEVELS,true);
      ChartRedraw();
   }
   return true; // Keep handle for MT5's post-test chart as well.
}

void StudyVisualCandidate(ulong order,uint retcode,bool sent)
{
   if(!ShowStudyOverlay) return;
   // Cross-check the indicator buffer used on the chart against the gate's
   // separate as-of lookup. Also runs in nonvisual tester verification.
   double v[1],lower[1];
   bool ok=CopyBuffer(g_visualHandle,0,0,1,v)==1 && CopyBuffer(g_visualHandle,1,0,1,lower)==1;
   if(ok && g_vrCandidateKnown)
      ok=MathAbs(v[0]-g_vrVwap[g_vrFeatureIndex])<1e-8 &&
         MathAbs(lower[0]-(g_vrVwap[g_vrFeatureIndex]-g_vrA20[g_vrFeatureIndex]))<1e-8;
   else if(ok) ok=(v[0]==EMPTY_VALUE && lower[0]==EMPTY_VALUE);
   g_visualChecks++;
   if(!ok) { g_visualErrors++; VwapReplayError("chart indicator and gate feature disagree"); }
   if(!MQLInfoInteger(MQL_VISUAL_MODE)) return;
   string name="RTL_VWAP_candidate_"+IntegerToString(g_vrCandidates);
   datetime at=(datetime)(g_vrCandidateMsc/1000);
   color shade=g_vrCandidateBlocked ? clrTomato : (order>0 ? clrMediumSeaGreen : clrSilver);
   int code=g_vrCandidateBlocked ? 251 : 159;
   string decision=g_vrCandidateBlocked ? "BLOCKED by VWAP" : (order>0 ? "Buy-stop request accepted (not necessarily filled)" : "No order accepted");
   ObjectCreate(0,name,OBJ_ARROW,0,at,g_vrSignalClose);
   ObjectSetInteger(0,name,OBJPROP_ARROWCODE,code);
   ObjectSetInteger(0,name,OBJPROP_COLOR,shade);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,2);
   string tip=decision+"\nDecision: "+TimeToString(at,TIME_DATE|TIME_SECONDS)+
      "\nSignal: "+TimeToString(g_vrSignalBar,TIME_DATE|TIME_MINUTES)+
      "\nSignal close: "+DoubleToString(g_vrSignalClose,2);
   if(g_vrCandidateKnown)
   {
      int j=g_vrFeatureIndex;
      tip+="\nVWAP: "+DoubleToString(g_vrVwap[j],4)+" | A20: "+DoubleToString(g_vrA20[j],4)+
           "\nCutoff: "+DoubleToString(g_vrVwap[j]-g_vrA20[j],4)+
           "\nz: "+DoubleToString((g_vrSignalClose-g_vrVwap[j])/g_vrA20[j],4);
   }
   else tip+="\nVWAP/A20 unknown for this session: gate permits request";
   tip+="\nGate: "+(UseVwapReplayGate ? "ON" : "OFF")+" | order: "+(string)order+" | retcode: "+(string)retcode;
   ObjectSetString(0,name,OBJPROP_TOOLTIP,tip);
   ChartRedraw();
}

void StudyVisualFinish()
{
   int h=FileOpen("visual_"+g_runTag+"_checks.csv",FILE_WRITE|FILE_CSV|FILE_COMMON,'\t');
   if(h!=INVALID_HANDLE)
   {
      FileWrite(h,"indicator_checks","indicator_errors");
      FileWrite(h,g_visualChecks,g_visualErrors);
      FileClose(h);
   }
   Print("Study overlay checks: ",g_visualChecks,"; errors: ",g_visualErrors);
}
