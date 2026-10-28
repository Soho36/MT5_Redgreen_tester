//+------------------------------------------------------------------+
//| RTL Session VWAP: the VWAP gate of RR_r_MFE_buy-stop-entry_vwap,  |
//| drawn on any symbol's M30 chart and computed from its 1-minute    |
//| bars (no data files). Same definitions as rtl_session_vwap.mqh:   |
//|  blue line   = session VWAP up to each bar's close                |
//|  orange line = gate line VWAP + Z x A20 (Z = -1: VWAP - A20)      |
//|  red x       = red bar closing below the gate line, with the next |
//|                bar in the same session: the EA places no buy stop |
//|                at its high (other EA filters are not drawn)       |
//| Values on the forming bar change until it closes.                 |
//| Strategy Tester (visual mode): MT5 rebuilds 1-minute bars with    |
//| synthetic volume there, so set LabelFile to the precomputed       |
//| labels in Common\Files to draw the real VWAP, as the EA does.     |
//+------------------------------------------------------------------+
#property strict
#property indicator_chart_window
#property indicator_buffers 7
#property indicator_plots 3
#property indicator_label1 "Session VWAP"
#property indicator_type1 DRAW_LINE
#property indicator_color1 clrDodgerBlue
#property indicator_width1 2
#property indicator_label2 "Gate line (VWAP + Z x A20)"
#property indicator_type2 DRAW_LINE
#property indicator_color2 clrDarkOrange
#property indicator_style2 STYLE_DASH
#property indicator_width2 1
#property indicator_label3 "No buy stop (red close below gate line)"
#property indicator_type3 DRAW_ARROW
#property indicator_color3 clrRed
#property indicator_width3 1

enum SERVER_CLOCK
{
   CLOCK_AUTO    = 0,  // Auto: custom symbol = session clock, broker symbol = UTC
   CLOCK_SESSION = 1,  // Server time is the session clock (research futures, exported stocks)
   CLOCK_UTC     = 2   // UTC (AMP live symbols, e.g. MNQZ26)
};
enum VWAP_VOLUME
{
   VWAP_VOLUME_AUTO = 0,  // Real volume when present, else tick volume
   VWAP_VOLUME_REAL = 1,  // Real (exchange) volume only
   VWAP_VOLUME_TICK = 2   // Tick volume only
};

input double       FarBelowZ    = -1.0;  // gate threshold in A20 units (EA: VwapFarBelowZ)
input int          AnchorMinute = 0;     // VWAP start, minutes after the session date's midnight (EA: VwapAnchorMinute)
input VWAP_VOLUME  VolumeSource = VWAP_VOLUME_AUTO;
input SERVER_CLOCK ServerClock  = CLOCK_AUTO;
input int          MaxBars      = 3000;  // M30 bars to compute (0 = all; 3000 needs ~90k 1-minute bars, under MT5's default 100k "Max bars in chart")
input string       LabelFile    = "";    // "" = compute from 1-minute bars; tester: e.g. rtl_vwap_features_NVDA.csv (EA: VwapLabelFile)

double VwapLine[], GateLine[], Mark[];
double PvReal[], VolReal[], PvTick[], VolTick[];   // running session sums at each bar's close
bool   g_utc   = false;
int    g_first = 0;
datetime g_fileBar[];
double   g_fileVwap[], g_fileA20[];
int      g_fileCount = 0;
int      g_lastError = 0;
bool     g_pending   = false;   // the 1-minute history was not ready: the timer (or next tick) recomputes all bars
uint     g_loadStart = 0;
datetime g_m1First   = 0;
int      g_total     = 0;       // rates_total of the last OnCalculate

// Label file (see rtl_session_vwap.mqh): keeps the known rows' bar, VWAP and A20.
bool LoadLabels()
{
   int h = FileOpen(LabelFile, FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   if(h == INVALID_HANDLE) { Print("VWAP label file not found in Common\\Files: ", LabelFile); return false; }
   string headers[7] = {"available_epoch", "session_epoch", "bar_epoch", "close", "vwap", "a20", "known"};
   for(int j = 0; j < 7; j++)
      if(FileReadString(h) != headers[j]) { FileClose(h); Print("VWAP label file header differs: ", LabelFile); return false; }
   datetime last = 0;
   while(!FileIsEnding(h))
   {
      datetime available = (datetime)FileReadNumber(h);
      if(available == 0 && FileIsEnding(h)) break;
      FileReadNumber(h);
      datetime bar = (datetime)FileReadNumber(h);
      FileReadNumber(h);
      double vwap = FileReadNumber(h), a20 = FileReadNumber(h);
      bool known = (FileReadNumber(h) == 1);
      if(bar <= last || available != bar + 1800) { FileClose(h); Print("Invalid VWAP label row in ", LabelFile); return false; }
      last = bar;
      if(!known) continue;
      ArrayResize(g_fileBar, g_fileCount + 1, 20000); ArrayResize(g_fileVwap, g_fileCount + 1, 20000);
      ArrayResize(g_fileA20, g_fileCount + 1, 20000);
      g_fileBar[g_fileCount] = bar; g_fileVwap[g_fileCount] = vwap; g_fileA20[g_fileCount] = a20;
      g_fileCount++;
   }
   FileClose(h);
   if(g_fileCount == 0) Print("No known rows in ", LabelFile);
   return g_fileCount > 0;
}

int FileRow(datetime bar)
{
   int left = 0, right = g_fileCount - 1;
   while(left <= right)
   {
      int mid = (left + right) / 2;
      if(g_fileBar[mid] == bar) return mid;
      if(g_fileBar[mid] < bar) left = mid + 1; else right = mid - 1;
   }
   return -1;
}

datetime NthSunday(int year, int month, int n)
{
   MqlDateTime d = {};
   d.year = year; d.mon = month; d.day = 1;
   datetime first = StructToTime(d);
   TimeToStruct(first, d);
   return first + ((7 - d.day_of_week) % 7 + 7 * (n - 1)) * 86400;
}

// Server time -> session clock, as in the EA: Chicago + 8 h, UTC + 3 h in US daylight time, else + 2 h.
datetime SessionClock(datetime server)
{
   if(!g_utc) return server;
   MqlDateTime dt; TimeToStruct(server, dt);
   datetime dstStart = NthSunday(dt.year, 3, 2) + 8 * 3600;
   datetime dstEnd   = NthSunday(dt.year, 11, 1) + 7 * 3600;
   return server + ((server >= dstStart && server < dstEnd) ? 3 : 2) * 3600;
}

datetime SessionDay(datetime server)
{
   datetime clock = SessionClock(server);
   return clock - clock % 86400;
}

int OnInit()
{
   if(_Period != PERIOD_M30)
   {
      Print("RTL Session VWAP draws the M30 gate of the VWAP EA; open an M30 chart");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!MathIsValidNumber(FarBelowZ) || AnchorMinute < 0 || AnchorMinute >= 1440 || MaxBars < 0)
   {
      Print("Invalid inputs: AnchorMinute must be 0-1439, MaxBars >= 0");
      return INIT_PARAMETERS_INCORRECT;
   }
   g_utc = (ServerClock == CLOCK_UTC || (ServerClock == CLOCK_AUTO && !SymbolInfoInteger(_Symbol, SYMBOL_CUSTOM)));
   if(LabelFile != "")
   {
      if(g_utc) { Print("LabelFile needs a symbol whose server time is the session clock"); return INIT_PARAMETERS_INCORRECT; }
      if(!LoadLabels()) return INIT_FAILED;
   }
   SetIndexBuffer(0, VwapLine, INDICATOR_DATA);
   SetIndexBuffer(1, GateLine, INDICATOR_DATA);
   SetIndexBuffer(2, Mark,     INDICATOR_DATA);
   SetIndexBuffer(3, PvReal,   INDICATOR_CALCULATIONS);
   SetIndexBuffer(4, VolReal,  INDICATOR_CALCULATIONS);
   SetIndexBuffer(5, PvTick,   INDICATOR_CALCULATIONS);
   SetIndexBuffer(6, VolTick,  INDICATOR_CALCULATIONS);
   for(int p = 0; p < 3; p++) PlotIndexSetDouble(p, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetInteger(2, PLOT_ARROW, 251);
   PlotIndexSetInteger(2, PLOT_ARROW_SHIFT, -12);
   IndicatorSetInteger(INDICATOR_DIGITS, _Digits);
   IndicatorSetString(INDICATOR_SHORTNAME, "RTL session VWAP (gate z < " + DoubleToString(FarBelowZ, 2) + ")");
   if(LabelFile == "") EventSetTimer(1);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); }

// Adds the 1-minute bars in [from, to) to the running sums, in time order (the EA's summation order).
bool AddMinutes(datetime from, datetime to, double &pr, double &vr, double &pt, double &vt)
{
   if(to <= from) return true;
   MqlRates m1[];
   ResetLastError();
   int n = CopyRates(_Symbol, PERIOD_M1, from, to - 1, m1);
   if(n <= 0) { g_lastError = GetLastError(); return false; }
   for(int k = 0; k < n; k++)
   {
      if(m1[k].time < from || m1[k].time >= to) continue;
      double typical = (m1[k].high + m1[k].low + m1[k].close) / 3.0;
      if(m1[k].real_volume > 0) { pr += typical * (double)m1[k].real_volume; vr += (double)m1[k].real_volume; }
      if(m1[k].tick_volume > 0) { pt += typical * (double)m1[k].tick_volume; vt += (double)m1[k].tick_volume; }
   }
   return true;
}

void ClearBar(int i)
{
   VwapLine[i] = GateLine[i] = Mark[i] = EMPTY_VALUE;
   PvReal[i] = VolReal[i] = PvTick[i] = VolTick[i] = EMPTY_VALUE;
}

// Computes bars from `start` (-1 = all) of a series given oldest first. Returns false while the
// 1-minute history is not ready: an indicator cannot wait for it, so it asks for the older minutes
// and is called again (for up to 30 s) until the terminal holds them or reaches its
// "Max bars in chart" limit; bars before the minutes it holds stay empty.
bool Fill(const int total, int start, const datetime &time[], const double &open[], const double &high[],
          const double &low[], const double &close[])
{
   if(!SeriesInfoInteger(_Symbol, PERIOD_M1, SERIES_SYNCHRONIZED)) { iTime(_Symbol, PERIOD_M1, 0); return false; }
   bool full = (start < 0);
   if(full)
   {
      g_first = (MaxBars > 0 && total > MaxBars) ? total - MaxBars : 0;
      datetime need = SessionDay(time[g_first]) + AnchorMinute * 60 - (int)(SessionClock(time[g_first]) - time[g_first]);
      g_m1First = (datetime)SeriesInfoInteger(_Symbol, PERIOD_M1, SERIES_FIRSTDATE);
      if(g_m1First > need && Bars(_Symbol, PERIOD_M1) < TerminalInfoInteger(TERMINAL_MAXBARS)
         && (g_loadStart == 0 || GetTickCount() - g_loadStart < 30000))
      {
         if(g_loadStart == 0)
         {
            g_loadStart = GetTickCount();
            Print("RTL Session VWAP: loading 1-minute history from ", TimeToString(need), "...");
         }
         MqlRates probe[];
         CopyRates(_Symbol, PERIOD_M1, need, need + 3600, probe);
         return false;
      }
      for(int i = 0; i < total; i++) ClearBar(i);
      start = g_first;
   }

   int missing = 0, skipped = 0;
   for(int i = start; i < total; i++)
   {
      ClearBar(i);
      datetime day    = SessionDay(time[i]);
      int      shift  = (int)(SessionClock(time[i]) - time[i]);
      datetime anchor = day + AnchorMinute * 60 - shift;   // server time
      datetime barEnd = time[i] + PeriodSeconds(PERIOD_M30);
      if(barEnd <= anchor) continue;
      if(anchor < g_m1First) { skipped++; continue; }   // session starts before the 1-minute history held

      double pr = 0.0, vr = 0.0, pt = 0.0, vt = 0.0;
      datetime from = anchor;
      if(i > g_first && SessionDay(time[i - 1]) == day && VolReal[i - 1] != EMPTY_VALUE)
      {
         pr = PvReal[i - 1]; vr = VolReal[i - 1]; pt = PvTick[i - 1]; vt = VolTick[i - 1];
         from = MathMax(time[i], anchor);
      }
      if(!AddMinutes(from, barEnd, pr, vr, pt, vt)) { missing++; continue; }
      PvReal[i] = pr; VolReal[i] = vr; PvTick[i] = pt; VolTick[i] = vt;

      bool   real = (VolumeSource == VWAP_VOLUME_REAL || (VolumeSource == VWAP_VOLUME_AUTO && vr > 0.0));
      double vol  = real ? vr : vt;
      if(vol <= 0.0) continue;
      double vwap = (real ? pr : pt) / vol;
      if(!MathIsValidNumber(vwap) || vwap <= 0.0) continue;
      VwapLine[i] = vwap;

      if(i < 20) continue;
      double sum = 0.0;   // A20: newest true range first, as RtlA20 sums
      for(int k = i; k > i - 20; k--)
         sum += MathMax(high[k] - low[k], MathMax(MathAbs(high[k] - close[k - 1]), MathAbs(low[k] - close[k - 1])));
      double a20 = sum / 20.0;
      if(a20 <= 0.0) continue;
      GateLine[i] = vwap + FarBelowZ * a20;

      if(i < total - 1 && close[i] < open[i] && close[i] < GateLine[i] && SessionDay(time[i + 1]) == day)
         Mark[i] = high[i];
   }
   // A series not built yet still reports itself synchronized, and requests fail (4401) until it is.
   if(full && missing > 0)
   {
      if(g_loadStart == 0)
      {
         g_loadStart = GetTickCount();
         Print("RTL Session VWAP: waiting for the 1-minute history...");
      }
      if(GetTickCount() - g_loadStart < 30000) return false;
   }
   if(full && skipped > 0)
      Print("RTL Session VWAP: ", skipped, " bars left empty, before the 1-minute history held from ",
            TimeToString(g_m1First), " (raise Tools > Options > Charts > Max bars in chart, or lower MaxBars)");
   if(missing > 0)
      Print("RTL Session VWAP: no 1-minute bars for ", missing, " bars (error ", g_lastError, ")");
   return true;
}

// Charts of custom symbols get no ticks: a pending full pass runs here from the chart's own bars.
void OnTimer()
{
   if(!g_pending) return;
   int n = g_total;
   if(n < 2 || Bars(_Symbol, _Period) != n) return;   // the series changed: OnCalculate takes over
   MqlRates r[];
   if(CopyRates(_Symbol, _Period, 0, n, r) != n) return;
   datetime t[];
   double o[], h[], l[], c[];
   ArrayResize(t, n); ArrayResize(o, n); ArrayResize(h, n); ArrayResize(l, n); ArrayResize(c, n);
   for(int i = 0; i < n; i++) { t[i] = r[i].time; o[i] = r[i].open; h[i] = r[i].high; l[i] = r[i].low; c[i] = r[i].close; }
   if(!Fill(n, -1, t, o, h, l, c)) return;
   g_pending = false;
   ChartRedraw();
}

int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[],
                const double &open[], const double &high[], const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
{
   ArraySetAsSeries(time, false);  ArraySetAsSeries(open, false); ArraySetAsSeries(high, false);
   ArraySetAsSeries(low, false);   ArraySetAsSeries(close, false);
   if(rates_total < 2) return 0;
   g_total = rates_total;
   if(LabelFile != "")
   {
      int from = (prev_calculated <= 0) ? 0 : prev_calculated - 1;
      for(int i = from; i < rates_total; i++)
      {
         ClearBar(i);
         int j = FileRow(time[i]);
         if(j < 0) continue;
         VwapLine[i] = g_fileVwap[j];
         GateLine[i] = g_fileVwap[j] + FarBelowZ * g_fileA20[j];
         if(i < rates_total - 1 && close[i] < open[i] && close[i] < GateLine[i]
            && SessionDay(time[i + 1]) == SessionDay(time[i]))
            Mark[i] = high[i];
      }
      return rates_total;
   }
   bool full = (prev_calculated <= 0 || g_pending);
   if(Fill(rates_total, full ? -1 : MathMax(g_first, prev_calculated - 1), time, open, high, low, close))
      g_pending = false;
   else
   {
      if(full) for(int i = 0; i < rates_total; i++) ClearBar(i);
      g_pending = true;
   }
   return rates_total;
}
