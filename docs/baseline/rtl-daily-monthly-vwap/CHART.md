# Plot the daily/monthly VWAP study

Updated 2026-11-18. RTL_Study_VWAP now auto-detects the daily file format;
the original M30 format and decision-at-open behavior remain supported.
Installed in Indicators/CodexVwapVisual, compiled with zero errors/warnings.

1. Open MNQcontDTBNT20261114 on D1.
2. Remove any existing RTL_Study_VWAP instance, refresh Navigator, reattach it.
3. Set FeatureFile to rtl_daily_monthly_vwap_20261118_features.csv (filename
   only, not the project path). The file is installed in MT5 Common/Files.
4. Keep DailyDecisionAtOpen=false to plot completed daily-close values on
   their own candles: blue monthly VWAP, dashed orange VWAP minus daily A20.

DailyDecisionAtOpen=true instead plots the prior completed day's values used
at the current day's open. That mode leaves the first day of each month blank,
matching the EA's unknown-label reset rule. Neither mode shows future labels;
close mode leaves the unfinished day blank. The file ends November 13, 2026;
later days have no values. Values also require matching historical closes.

The change was compiled and installed; the user's chart attachment was not
visually inspected. Installation record/backups: Reports/rtl_daily_monthly_vwap_20261118/indicator/.
