// Session VWAP and A20 at a completed M30 signal bar, computed inside MT5 from 1-minute bars.
// Same definitions as the VWAP studies (docs/baseline/rtl-vwap/PROTOCOL.md):
//   VWAP = sum((H+L+C)/3 x volume) / sum(volume) over the session's 1-minute bars that end by the
//          signal bar's close; the session is one date on the session clock, from AnchorMinute.
//   A20  = arithmetic mean of the last 20 completed M30 true ranges ending at the signal bar.
//   z    = (signal close - VWAP) / A20; "far below" when z < threshold (-1 in the studies).
// The label is unknown (gate allows the trade) when the signal bar belongs to an earlier session,
// ends before the anchor, has no volume, or fewer than 21 M30 bars exist.
//
// Tester caveat: in the generated-tick models MT5 rebuilds 1-minute bars from its own ticks, so
// their volume is synthetic. In "1 minute OHLC" every minute weighs the same and the computed
// "VWAP" is a plain average of minute typical prices (checked 2026-10-28). For history tests use
// the precomputed labels below (RtlVwapFileLoad); live and demo charts carry the real volume.
#ifndef RTL_SESSION_VWAP_MQH
#define RTL_SESSION_VWAP_MQH

enum VWAP_VOLUME
{
   VWAP_VOLUME_AUTO = 0,  // Real volume when present, else tick volume
   VWAP_VOLUME_REAL = 1,  // Real (exchange) volume only
   VWAP_VOLUME_TICK = 2   // Tick volume only
};

// clockShift: session clock minus server time, in seconds (0 for the research symbols).
bool RtlSessionVwap(const string symbol, datetime barOpen, int clockShift, int anchorMinute,
                    VWAP_VOLUME source, double &vwap)
{
   datetime barEnd  = barOpen + PeriodSeconds(PERIOD_M30);
   datetime clock   = barOpen + clockShift;
   datetime anchor  = clock - clock % 86400 + anchorMinute * 60 - clockShift;   // server time
   if(barEnd <= anchor) return false;
   MqlRates m1[];
   int n = CopyRates(symbol, PERIOD_M1, anchor, barEnd - 1, m1);
   if(n <= 0) return false;
   // Both sums in one pass; AUTO takes real volume when the window has any, never a mix.
   double pvReal = 0.0, volReal = 0.0, pvTick = 0.0, volTick = 0.0;
   for(int i = 0; i < n; i++)
   {
      if(m1[i].time < anchor || m1[i].time >= barEnd) continue;
      double typical = (m1[i].high + m1[i].low + m1[i].close) / 3.0;
      if(m1[i].real_volume > 0) { pvReal += typical * (double)m1[i].real_volume; volReal += (double)m1[i].real_volume; }
      if(m1[i].tick_volume > 0) { pvTick += typical * (double)m1[i].tick_volume; volTick += (double)m1[i].tick_volume; }
   }
   bool real = (source == VWAP_VOLUME_REAL || (source == VWAP_VOLUME_AUTO && volReal > 0.0));
   double pv = real ? pvReal : pvTick, volume = real ? volReal : volTick;
   if(volume <= 0.0) return false;
   vwap = pv / volume;
   return MathIsValidNumber(vwap) && vwap > 0.0;
}

// Mean of the last 20 M30 true ranges ending at bar `shift` (1 = last completed bar).
bool RtlA20(const string symbol, int shift, double &a20)
{
   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(symbol, PERIOD_M30, shift, 21, r) != 21) return false;
   double sum = 0.0;
   for(int i = 0; i < 20; i++)
   {
      double prev = r[i + 1].close;
      sum += MathMax(r[i].high - r[i].low, MathMax(MathAbs(r[i].high - prev), MathAbs(r[i].low - prev)));
   }
   a20 = sum / 20.0;
   return MathIsValidNumber(a20) && a20 > 0.0;
}

// ---- Precomputed labels for tester runs ----
// A tab-separated file in Common\Files, one row per M30 bar, header
//   available_epoch session_epoch bar_epoch close vwap a20 known
// epoch = MT5 server time in seconds, available = bar + 1800, session = the bar's date,
// vwap and a20 are 0 when known = 0. NQ: rtl_vwap_replay_20261026_features.csv (the replay's
// file); stocks: rtl_vwap_features_<SYMBOL>.csv from python/export_stock_mt5.py.
datetime g_rvAvailable[], g_rvSession[], g_rvBar[];
double   g_rvClose[], g_rvVwap[], g_rvA20[];
bool     g_rvKnown[];
int      g_rvCount = 0;

bool RtlVwapFileLoad(const string name)
{
   g_rvCount = 0;
   int h = FileOpen(name, FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, '\t');
   if(h == INVALID_HANDLE) { Print("VWAP label file not found in Common\\Files: ", name); return false; }
   string headers[7] = {"available_epoch", "session_epoch", "bar_epoch", "close", "vwap", "a20", "known"};
   for(int j = 0; j < 7; j++)
      if(FileReadString(h) != headers[j]) { FileClose(h); Print("VWAP label file header differs: ", name); return false; }
   while(!FileIsEnding(h))
   {
      datetime available = (datetime)FileReadNumber(h);
      if(available == 0 && FileIsEnding(h)) break;
      datetime session = (datetime)FileReadNumber(h), bar = (datetime)FileReadNumber(h);
      double close = FileReadNumber(h), vwap = FileReadNumber(h), a20 = FileReadNumber(h);
      bool known = (FileReadNumber(h) == 1);
      if(available != bar + 1800 || session != bar - bar % 86400
         || (g_rvCount > 0 && available <= g_rvAvailable[g_rvCount - 1])
         || !MathIsValidNumber(close) || close <= 0.0
         || (known && (!MathIsValidNumber(vwap) || !MathIsValidNumber(a20) || vwap <= 0.0 || a20 <= 0.0)))
      { FileClose(h); Print("Invalid VWAP label row ", g_rvCount + 1, " in ", name); g_rvCount = 0; return false; }
      int n = g_rvCount + 1;
      ArrayResize(g_rvAvailable, n, 20000); ArrayResize(g_rvSession, n, 20000); ArrayResize(g_rvBar, n, 20000);
      ArrayResize(g_rvClose, n, 20000);     ArrayResize(g_rvVwap, n, 20000);    ArrayResize(g_rvA20, n, 20000);
      ArrayResize(g_rvKnown, n, 20000);
      g_rvAvailable[g_rvCount] = available; g_rvSession[g_rvCount] = session; g_rvBar[g_rvCount] = bar;
      g_rvClose[g_rvCount] = close; g_rvVwap[g_rvCount] = vwap; g_rvA20[g_rvCount] = a20; g_rvKnown[g_rvCount] = known;
      g_rvCount = n;
   }
   FileClose(h);
   if(g_rvCount == 0) Print("Empty VWAP label file ", name);
   return g_rvCount > 0;
}

// Newest row available by `now` (the replay's lookup), or -1.
int RtlVwapFileRow(datetime now)
{
   int left = 0, right = g_rvCount - 1, j = -1;
   while(left <= right)
   {
      int mid = (left + right) / 2;
      if(g_rvAvailable[mid] <= now) { j = mid; left = mid + 1; } else right = mid - 1;
   }
   return j;
}

#endif
