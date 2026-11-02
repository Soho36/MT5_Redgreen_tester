//+------------------------------------------------------------------+
//| Session VWAP Lines: the two lines of the VWAP gate on the chart's |
//| own symbol, e.g. MNQZ26, on any timeframe up to H4. Computed from |
//| the symbol's 1-minute and M30 bars; no data file.                 |
//|  blue line   = session VWAP up to each bar's close                |
//|  orange line = VWAP + Z x A20 (Z = -1: VWAP - A20), where A20 is  |
//|                the mean true range of the last 20 completed M30   |
//|                bars at that bar's close                           |
//| The session is the CME day: it starts at 16:00 Chicago time.      |
//| At each M30 close the lines equal the EA's values (rule in        |
//| rtl_session_vwap.mqh). The forming bar's VWAP moves until it      |
//| closes. Strategy Tester: minute volume is synthetic, so VWAP      |
//| there is a plain average; use RTL_Session_VWAP with LabelFile.    |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property indicator_chart_window
#property indicator_buffers 7
#property indicator_plots 2
#property indicator_label1 "Session VWAP"
#property indicator_type1 DRAW_LINE
#property indicator_color1 clrDodgerBlue
#property indicator_width1 2
#property indicator_label2 "VWAP + Z x A20"
#property indicator_type2 DRAW_LINE
#property indicator_color2 clrDarkOrange
#property indicator_style2 STYLE_DASH
#property indicator_width2 1

enum SERVER_CLOCK
{
   CLOCK_AUTO    = 0,  // Auto: custom symbol = session clock, broker symbol = UTC
   CLOCK_SESSION = 1,  // Server time is the session clock (research futures)
   CLOCK_UTC     = 2   // UTC (AMP live symbols, e.g. MNQZ26)
};
enum VWAP_VOLUME
{
   VWAP_VOLUME_AUTO = 0,  // Real volume when present, else tick volume
   VWAP_VOLUME_REAL = 1,  // Real (exchange) volume only
   VWAP_VOLUME_TICK = 2   // Tick volume only
};

input double       FarBelowZ    = -1.0;  // orange line distance in A20 units
input VWAP_VOLUME  VolumeSource = VWAP_VOLUME_AUTO;
input SERVER_CLOCK ServerClock  = CLOCK_AUTO;
input int          MaxDays      = 60;    // calendar days to draw (0 = all; 60 days fit MT5's default 100k "Max bars in chart")

double VwapLine[], GateLine[];
double PvReal[], VolReal[], PvTick[], VolTick[], SumDay[];   // running session sums at each bar's close
bool     g_utc       = false;
int      g_first     = 0;
int      g_total     = 0;       // rates_total of the last OnCalculate
bool     g_pending   = false;   // the history was not ready: the timer (or next tick) recomputes all bars
bool     g_warned    = false;
uint     g_loadStart = 0;
datetime g_m1First   = 0;

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

// The session's start in server time.
datetime SessionStart(datetime server)
{
   return SessionDay(server) - (datetime)(SessionClock(server) - server);
}

int OnInit()
{
   if(PeriodSeconds(_Period) > PeriodSeconds(PERIOD_H4))
   {
      Print("Session VWAP Lines draws a session's VWAP: use a chart of H4 or lower");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!MathIsValidNumber(FarBelowZ) || MaxDays < 0)
   {
      Print("Invalid inputs: MaxDays must be >= 0");
      return INIT_PARAMETERS_INCORRECT;
   }
   g_utc = (ServerClock == CLOCK_UTC || (ServerClock == CLOCK_AUTO && !SymbolInfoInteger(_Symbol, SYMBOL_CUSTOM)));
   if(MQLInfoInteger(MQL_TESTER))
      Print("Session VWAP Lines: the tester's minute volume is synthetic, so this VWAP is a plain average of minute prices");
   SetIndexBuffer(0, VwapLine, INDICATOR_DATA);
   SetIndexBuffer(1, GateLine, INDICATOR_DATA);
   SetIndexBuffer(2, PvReal,   INDICATOR_CALCULATIONS);
   SetIndexBuffer(3, VolReal,  INDICATOR_CALCULATIONS);
   SetIndexBuffer(4, PvTick,   INDICATOR_CALCULATIONS);
   SetIndexBuffer(5, VolTick,  INDICATOR_CALCULATIONS);
   SetIndexBuffer(6, SumDay,   INDICATOR_CALCULATIONS);
   for(int p = 0; p < 2; p++) PlotIndexSetDouble(p, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   IndicatorSetInteger(INDICATOR_DIGITS, _Digits);
   IndicatorSetString(INDICATOR_SHORTNAME, "Session VWAP lines (Z " + DoubleToString(FarBelowZ, 2) + ")");
   EventSetTimer(1);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); }

void ClearBar(int i)
{
   VwapLine[i] = GateLine[i] = EMPTY_VALUE;
   PvReal[i] = VolReal[i] = PvTick[i] = VolTick[i] = SumDay[i] = 0.0;
}

// Computes bars from `start` (-1 = all) of a series given oldest first. Returns false while the
// history is not ready: an indicator cannot wait for it, so it asks for the older minutes and is
// called again (for up to 30 s) until the terminal holds them or reaches its "Max bars in chart"
// limit; sessions that start before the minutes it holds stay empty.
bool Fill(const int total, int start, const datetime &time[])
{
   if(!SeriesInfoInteger(_Symbol, PERIOD_M1, SERIES_SYNCHRONIZED)) { iTime(_Symbol, PERIOD_M1, 0); return false; }
   bool full = (start < 0);
   if(full)
   {
      g_first = 0;
      if(MaxDays > 0)
         while(g_first < total - 1 && time[g_first] < time[total - 1] - MaxDays * 86400) g_first++;
      datetime need = SessionStart(time[g_first]);
      g_m1First = (datetime)SeriesInfoInteger(_Symbol, PERIOD_M1, SERIES_FIRSTDATE);
      if(g_m1First > need && Bars(_Symbol, PERIOD_M1) < TerminalInfoInteger(TERMINAL_MAXBARS)
         && (g_loadStart == 0 || GetTickCount() - g_loadStart < 30000))
      {
         if(g_loadStart == 0)
         {
            g_loadStart = GetTickCount();
            Print("Session VWAP Lines: loading 1-minute history from ", TimeToString(need), "...");
         }
         MqlRates probe[];
         CopyRates(_Symbol, PERIOD_M1, need, need + 3600, probe);
         return false;
      }
      start = g_first;
   }

   // A series not built yet still reports itself synchronized, and requests fail (4401) until it is.
   MqlRates m1[], m30[];
   datetime first = full ? SessionStart(time[start]) : time[start];
   ResetLastError();
   int nm1 = CopyRates(_Symbol, PERIOD_M1, first, time[total - 1] + PeriodSeconds(_Period), m1);
   int back = iBarShift(_Symbol, PERIOD_M30, time[start], false);
   int nm30 = (back < 0) ? -1 : CopyRates(_Symbol, PERIOD_M30, 0, back + 23, m30);
   if(nm1 <= 0 || nm30 <= 0)
   {
      if(g_loadStart == 0)
      {
         g_loadStart = GetTickCount();
         Print("Session VWAP Lines: waiting for the 1-minute and M30 history...");
      }
      if(!g_warned && GetTickCount() - g_loadStart >= 30000)
      {
         g_warned = true;
         Print("Session VWAP Lines: history still unavailable (error ", GetLastError(), "), retrying");
      }
      return false;
   }
   if(full) for(int i = 0; i < total; i++) ClearBar(i);

   datetime now = TimeCurrent();
   int a = 0, b = -1, skipped = 0;
   for(int i = start; i < total; i++)
   {
      double pr = 0.0, vr = 0.0, pt = 0.0, vt = 0.0;
      datetime sumDay = 0;
      if(i > g_first && SumDay[i - 1] > 0.0)
      {
         pr = PvReal[i - 1]; vr = VolReal[i - 1]; pt = PvTick[i - 1]; vt = VolTick[i - 1];
         sumDay = (datetime)SumDay[i - 1];
      }
      ClearBar(i);
      datetime barEnd = time[i] + PeriodSeconds(_Period);
      for(; a < nm1 && m1[a].time < barEnd; a++)
      {
         if(m1[a].time < first) continue;
         datetime day = SessionDay(m1[a].time);
         if(day != sumDay) { pr = vr = pt = vt = 0.0; sumDay = day; }
         double typical = (m1[a].high + m1[a].low + m1[a].close) / 3.0;
         if(m1[a].real_volume > 0) { pr += typical * (double)m1[a].real_volume; vr += (double)m1[a].real_volume; }
         if(m1[a].tick_volume > 0) { pt += typical * (double)m1[a].tick_volume; vt += (double)m1[a].tick_volume; }
      }
      PvReal[i] = pr; VolReal[i] = vr; PvTick[i] = pt; VolTick[i] = vt; SumDay[i] = (double)sumDay;
      if(sumDay == 0) continue;
      if(SessionStart(barEnd - 1) < g_m1First) { skipped++; continue; }   // the session starts before the minutes held

      bool   real = (VolumeSource == VWAP_VOLUME_REAL || (VolumeSource == VWAP_VOLUME_AUTO && vr > 0.0));
      double vol  = real ? vr : vt;
      if(vol <= 0.0) continue;
      double vwap = (real ? pr : pt) / vol;
      if(!MathIsValidNumber(vwap) || vwap <= 0.0) continue;
      VwapLine[i] = vwap;

      // The last M30 bar completed at this bar's close; the newest bar may still be forming.
      datetime end = (i == total - 1 && now < barEnd) ? now : barEnd;
      while(b + 1 < nm30 && m30[b + 1].time + 1800 <= end) b++;
      if(b < 20) continue;
      double sum = 0.0;   // A20: newest true range first, as RtlA20 sums
      for(int k = b; k > b - 20; k--)
         sum += MathMax(m30[k].high - m30[k].low,
                        MathMax(MathAbs(m30[k].high - m30[k - 1].close), MathAbs(m30[k].low - m30[k - 1].close)));
      double a20 = sum / 20.0;
      if(a20 > 0.0) GateLine[i] = vwap + FarBelowZ * a20;
   }
   if(full && skipped > 0)
      Print("Session VWAP Lines: ", skipped, " bars left empty, before the 1-minute history held from ",
            TimeToString(g_m1First), " (raise Tools > Options > Charts > Max bars in chart, or lower MaxDays)");
   return true;
}

// A closed market gets no ticks: a pending full pass runs here from the chart's own bars.
void OnTimer()
{
   if(!g_pending) return;
   int n = g_total;
   if(n < 2 || Bars(_Symbol, _Period) != n) return;   // the series changed: OnCalculate takes over
   datetime t[];
   if(CopyTime(_Symbol, _Period, 0, n, t) != n) return;
   if(!Fill(n, -1, t)) return;
   g_pending = false;
   ChartRedraw();
}

int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[],
                const double &open[], const double &high[], const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
{
   ArraySetAsSeries(time, false);
   if(rates_total < 2) return 0;
   g_total = rates_total;
   bool full = (prev_calculated <= 0 || g_pending);
   if(Fill(rates_total, full ? -1 : MathMax(g_first, prev_calculated - 1), time))
      g_pending = false;
   else
   {
      if(full) for(int i = 0; i < rates_total; i++) ClearBar(i);
      g_pending = true;
   }
   return rates_total;
}
