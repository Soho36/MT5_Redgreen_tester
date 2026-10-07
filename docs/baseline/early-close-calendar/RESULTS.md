# Early-close calendar on the rebuilt data

2026-10-01 · Runs: `Reports/early_close_calendar_20261001/` · Analysis: `python/analyze_calendar_study.py`
Symbol: `MNQcontDTBNT20102026` ([data build](../../reference/DATA_BUILD.md))

## Summary

- **On the rebuilt data, all remaining overnight holds started on early-close days**
  (holidays, plus Good Friday 2023 and the 2018 state funeral). The DST cause is gone.
- **Fix:** new EA input `UseEarlyCloseCalendar` (default `true`). On 262 listed sessions
  the EA flattens at the open of the session's last M30 bar (e.g. 19:30 instead of 23:30)
  and takes no new entries after it. The list (`mt5/experts/early_closes.mqh`) is generated
  from the data and matches the published schedule; see the [data build](../../reference/DATA_BUILD.md).
- **Result:** **0 cross-date trades** in all runs; the longest hold is 16–22 h (one session).
  Profit is essentially unchanged; the overnight trades were small on clean data.
- **RR on clean data:** 2.5R beats 1.0R in **both** periods on net $, PF and average R,
  with equal or similar drawdown. It's now a real candidate, not an overnight artifact.

## Results (net of $1/trade; DD = net closed-balance drawdown)

| Period | RR | Calendar | Trades | Net $ | Net PF | Net DD $ | Avg net R | Cross-date | Longest hold, h |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 2016–19 | 1.0 | off | 5,705 | 6,720 | 1.110 | 1,468 | +0.003 | 18 | 56.5 |
| 2016–19 | 1.0 | **on** | 5,699 | **6,816** | 1.111 | 1,427 | +0.004 | **0** | 17.8 |
| 2016–19 | 2.5 | off | 4,518 | 8,826 | 1.149 | 1,538 | +0.034 | 24 | 56.5 |
| 2016–19 | 2.5 | **on** | 4,514 | **8,858** | 1.150 | 1,538 | +0.025 | **0** | 21.5 |
| 2020–26 | 1.0 | off | 9,284 | 38,286 | 1.108 | 4,837 | +0.060 | 32 | 77.2 |
| 2020–26 | 1.0 | **on** | 9,272 | **38,433** | 1.108 | 4,837 | +0.061 | **0** | 16.4 |
| 2020–26 | 2.5 | off | 7,333 | 40,492 | 1.119 | 4,530 | +0.092 | 36 | 77.2 |
| 2020–26 | 2.5 | **on** | 7,328 | **40,524** | 1.119 | 4,530 | +0.092 | **0** | 22.5 |

## What it means

1. **The strategy is now strictly intraday,** as intended, in every session type.
2. **Most of the earlier "overnight money" was a data artifact.** On the old symbol, 2.5R's
   cross-date trades earned $7.7k (2020–26). On the rebuilt data, before the calendar, they
   earned under $1k: the big gaps came from the DST-shifted weeks.
3. **Results on the rebuilt data match the old ones closely** (2020–26, RR 1.0: $38.4k vs $37.4k),
   so earlier conclusions about entries still hold.
4. **RR 2.5 vs 1.0** (calendar on): +$2.0k (+30%) in 2016–19 and +$2.1k (+5%) in 2020–26,
   PF 1.150 vs 1.111 and 1.119 vs 1.108, higher average R in both. Caveat: 2.5 was singled out
   from a grid on 2020–26 data seen before, and +$2k in 2020–26 is within noise. The
   consistent direction across both periods and all metrics is the real evidence.

## Verification

- Compiled with 0 errors, 0 warnings. The calendar-off control (2016–2026, RR 1.0) reproduces
  all 14,989 trades of the previous EA build field by field.
- All 9 runs reconcile trade counts and gross PnL with MT5 stats. The stats file records
  `early_close_calendar`.
- Note: the imported symbol still contained the pre-2016 tail bars at the time of these runs.
  Periods start in 2016, so they are unaffected.

```powershell
.\venv\Scripts\python.exe python\build_early_close_calendar.py "F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv"
.\venv\Scripts\python.exe python\prepare_calendar_study.py
# compile Reports\early_close_calendar_20261001\RTL_runband_cal.mq5 in MetaEditor
.\python\run_exit_study.ps1 -StudyDir Reports\early_close_calendar_20261001 -ExpertName RTL_runband_cal -InstallFolder ClaudeEarlyClose
.\venv\Scripts\python.exe python\analyze_calendar_study.py
```
