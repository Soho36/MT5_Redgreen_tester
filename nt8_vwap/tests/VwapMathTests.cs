using System;
using NinjaTrader.NinjaScript;

internal static class VwapMathTests
{
    private static int checks;
    private static void Check(bool condition, string message)
    {
        checks++;
        if (!condition) throw new Exception(message);
    }
    private static void Near(double actual, double expected, string message)
    {
        Check(Math.Abs(actual - expected) < 1e-10, message + ": " + actual + " != " + expected);
    }
    private static DateTime T(string value) { return DateTime.Parse(value, System.Globalization.CultureInfo.InvariantCulture); }

    public static int Main()
    {
        try
        {
            WeightedAndCutoff();
            A20AndGate();
            SessionClock();
            HistoryCoverage();
            Console.WriteLine("PASS: " + checks + " assertions against RTLSessionVWAP.cs calculation core.");
            return 0;
        }
        catch (Exception ex) { Console.Error.WriteLine(ex); return 1; }
    }

    private static void WeightedAndCutoff()
    {
        DateTime anchor = T("2026-10-28 17:00:00");
        DateTime[] times = { anchor, anchor.AddMinutes(1), anchor.AddMinutes(2), anchor.AddMinutes(3) };
        double[] high = { 900, 12, 24, 10000 }, low = { 900, 8, 18, 10000 };
        double[] close = { 900, 10, 18, 10000 }, volume = { 10000, 1, 3, 9999999 };
        double result;
        Func<bool> calculate = () => RtlVwapMath.TryVwap(times.Length, i => times[i],
            i => high[i], i => low[i], i => close[i], i => volume[i],
            anchor, times[2], true, out result);
        Check(RtlVwapMath.TryVwap(times.Length, i => times[i], i => high[i], i => low[i],
            i => close[i], i => volume[i], anchor, times[2], true, out result), "weighted VWAP known");
        Near(result, 17.5, "HLC3 weighted by volume; anchor minute excluded; closing minute included; future minute excluded");
        volume[3] = double.NaN;
        Check(RtlVwapMath.TryVwap(times.Length, i => times[i], i => high[i], i => low[i],
            i => close[i], i => volume[i], anchor, times[2], true, out result), "future invalid volume cannot contaminate signal");
        Near(result, 17.5, "future data independent");
        Check(RtlVwapMath.TryVwap(times.Length, i => times[i], i => high[i], i => low[i],
            i => close[i], i => volume[i], times[1], times[2], true, out result), "custom anchor accepted");
        Near(result, 20, "custom anchor only includes minute after anchor");
        Check(!RtlVwapMath.TryVwap(2, i => times[i], i => high[i], i => low[i],
            i => close[i], i => volume[i], anchor, times[2], true, out result), "stale minute series unknown");
        Check(!RtlVwapMath.TryVwap(times.Length, i => times[i], i => high[i], i => low[i],
            i => close[i], i => volume[i], anchor, anchor, true, out result), "pre-anchor unknown");
        Check(!RtlVwapMath.TryVwap(times.Length, i => times[i], i => high[i], i => low[i],
            i => close[i], i => volume[i], anchor, times[2], false, out result), "partial startup history unknown");
        volume[1] = volume[2] = 0;
        Check(!calculate(), "zero session volume unknown");
        volume[1] = -1;
        Check(!calculate(), "invalid negative volume unknown");
        volume[1] = double.NaN;
        Check(!calculate(), "invalid NaN volume unknown");
        volume[1] = 1;
        high[1] = double.PositiveInfinity;
        Check(!calculate(), "invalid price unknown");
        Check(!RtlVwapMath.TryVwap(0, i => times[i], i => high[i], i => low[i],
            i => close[i], i => volume[i], anchor, times[2], true, out result), "empty minute history unknown");
        Check(RtlVwapMath.LastAtOrBefore(times.Length, i => times[i], anchor.AddSeconds(-1)) == -1, "cutoff before history");
        Check(RtlVwapMath.LastAtOrBefore(times.Length, i => times[i], times[2]) == 2, "equal cutoff included");
        Check(RtlVwapMath.LastAtOrBefore(times.Length, i => times[i], times[3].AddSeconds(1)) == 3, "cutoff after history bounded");
    }

    private static void A20AndGate()
    {
        double[] h = new double[22], l = new double[22], c = new double[22];
        for (int i = 0; i < 22; i++) { h[i] = 102; l[i] = 98; c[i] = 100; }
        double a20;
        Check(!RtlVwapMath.TryA20(19, i => h[i], i => l[i], i => c[i], out a20), "20 candles insufficient for 20 true ranges");
        h[20] = 112; l[20] = 108; c[20] = 110;
        Check(RtlVwapMath.TryA20(20, i => h[i], i => l[i], i => c[i], out a20), "21 candles sufficient");
        Near(a20, (19 * 4 + 12) / 20.0, "arithmetic 20-TR average includes latest gap and previous close");
        h[0] = 999999;
        Check(RtlVwapMath.TryA20(20, i => h[i], i => l[i], i => c[i], out a20), "prior bar used only for previous close");
        Near(a20, 4.4, "old high does not affect A20");
        h[21] = 999999;
        Check(RtlVwapMath.TryA20(20, i => h[i], i => l[i], i => c[i], out a20), "future candle excluded");
        Near(a20, 4.4, "future high does not affect A20");
        Check(!RtlVwapMath.IsFarBelow(90, 100, 10, -1), "exact gate equality allows");
        Check(RtlVwapMath.IsFarBelow(89.999, 100, 10, -1), "strictly below gate rejects");
        Check(!RtlVwapMath.IsFarBelow(90.001, 100, 10, -1), "above gate allows");
        Check(!RtlVwapMath.IsFarBelow(1, double.NaN, 10, -1), "unknown VWAP allows");
        Check(!RtlVwapMath.IsFarBelow(1, 100, double.NaN, -1), "unknown A20 allows");
        Check(!RtlVwapMath.IsFarBelow(1, 100, 0, -1), "zero A20 allows");
        for (int i = 0; i < 22; i++) { h[i] = l[i] = c[i] = 100; }
        Check(!RtlVwapMath.TryA20(20, i => h[i], i => l[i], i => c[i], out a20), "flat zero A20 unknown");
        h[20] = double.NaN;
        Check(!RtlVwapMath.TryA20(20, i => h[i], i => l[i], i => c[i], out a20), "invalid A20 inputs unknown");
    }

    private static void SessionClock()
    {
        TimeZoneInfo utc = TimeZoneInfo.Utc;
        TimeZoneInfo chicago = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");
        TimeZoneInfo tallinn = TimeZoneInfo.FindSystemTimeZoneById("FLE Standard Time");
        Check(RtlVwapMath.SessionDate(T("2026-07-01 20:59:00"), utc, chicago, 480) == T("2026-07-01"), "summer just before 16 CT rollover");
        Check(RtlVwapMath.SessionDate(T("2026-07-01 21:00:00"), utc, chicago, 480) == T("2026-07-02"), "summer 16 CT rollover");
        Check(RtlVwapMath.SessionDate(T("2026-01-05 21:59:00"), utc, chicago, 480) == T("2026-01-05"), "winter just before 16 CT rollover");
        Check(RtlVwapMath.SessionDate(T("2026-01-05 22:00:00"), utc, chicago, 480) == T("2026-01-06"), "winter 16 CT rollover");
        Check(RtlVwapMath.Anchor(T("2026-07-01 22:00:00"), utc, chicago, 480, 0) == T("2026-07-01 21:00:00"), "summer anchor UTC");
        Check(RtlVwapMath.Anchor(T("2026-01-05 23:00:00"), utc, chicago, 480, 0) == T("2026-01-05 22:00:00"), "winter anchor UTC");
        Check(RtlVwapMath.SessionDate(T("2026-10-29 23:00:00"), tallinn, chicago, 480) == T("2026-10-30"), "Europe/US DST mismatch week handled");
        Check(RtlVwapMath.Anchor(T("2026-10-30 00:00:00"), tallinn, chicago, 480, 0) == T("2026-10-29 23:00:00"), "Europe/US DST mismatch anchor");
        Check(RtlVwapMath.SessionDate(T("2026-07-01 20:59:00"), utc, chicago, 480)
            != RtlVwapMath.SessionDate(T("2026-07-01 22:00:00"), utc, chicago, 480), "previous-session signal distinguishable at next opening");
        TimeZoneInfo newYork = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
        Check(RtlVwapMath.Anchor(T("2026-07-01 14:00:00"), utc, newYork, 0, 570) == T("2026-07-01 13:30:00"), "New York 09:30 custom anchor");
    }

    private static void HistoryCoverage()
    {
        DateTime anchor = T("2026-10-28 16:00:00");
        Check(RtlVwapMath.HasAnchorHistory(anchor, anchor.AddDays(-1), anchor.AddDays(-2)), "prior-day minute history covers anchor");
        Check(RtlVwapMath.HasAnchorHistory(anchor, anchor.AddHours(1).AddMinutes(1), anchor.AddHours(1)), "CME opening minute covers anchored session despite break");
        Check(RtlVwapMath.HasAnchorHistory(anchor, anchor.AddMinutes(1), anchor), "anchor opening minute accepted");
        Check(!RtlVwapMath.HasAnchorHistory(anchor, anchor.AddHours(2), anchor.AddHours(1)), "truncated first session refused");
        Check(!RtlVwapMath.HasAnchorHistory(anchor, anchor.AddMinutes(2), anchor.AddHours(-1)), "truncated session overlapping anchor refused");
    }
}
