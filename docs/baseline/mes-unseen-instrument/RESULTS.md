# RTL baseline on MES (unseen instrument)

2026-10-08 · Descriptive comparison, no pre-set gate · [Baseline studies](../README.md)

## Summary

- **Question:** does the unchanged RTL baseline (developed on MNQ) work on an instrument it was never tuned
  on: micro E-mini S&P 500 (MES)?
- **Answer: no.** On MES the strategy has **no edge even before costs**. Mean R before costs is −0.039
  (2016–19) and +0.002 (2020–26), against +0.093 / +0.085 on MNQ. The day-bootstrap 95% intervals do not
  overlap in either period. After $1.05 costs MES loses in 15 of 17 years.
- **Meaning:** the MNQ edge does not carry over to the closest related index future. It may be specific to
  NQ, or partly an NQ-sample artefact. Treat MNQ results as unconfirmed on independent data.

## Setup

| | |
|---|---|
| EA | `mt5/experts/RR_r_MFE_buy-stop-entry_runband.cs`, unchanged (RR 1.0, MaxRedRun 3, flatten 23:30 + fallback, early-close calendar, window 01:00–23:30) |
| Tester | M30, Model 1 (1-minute OHLC), 2010-06-07 → 2026-07-14, 1 lot; settings copied from the trend-RR baseline job |
| Symbols | `MNQcontDTBNT20102026_2` ($2/pt) and `MEScontDTBNT20102026` ($5/pt, [data build](../../reference/DATA_BUILD.md#es-build-2026-10-08)); $/pt read back from the ledgers |
| Costs | $1.05 per trade, as in all NQ studies |
| R | trade profit ÷ (signal candle range × $/pt) |
| Check | The MNQ rerun reproduces the trend-RR baseline ledger exactly (23,427 trades) |

The early-close calendar was built from NQ. ES runs on the same CME schedule. Five sessions differ in the
data: three are one stray minute (19:59 vs 20:00), and two are ES data holes, not early closes.

## Results

| Period | Symbol | Trades | Win % | Median risk (pts) | Cost (R) | Mean R gross | Mean R net | PF gross | PF net | Net $ | Max DD $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2010–15 | MNQ | 8,459 | 40.2 | 3.75 | 0.19 | +0.005 | −0.185 | 1.041 | 0.860 | −7,027 | 8,190 |
| 2010–15 | MES | 8,633 | 36.4 | 2.00 | 0.13 | −0.118 | −0.251 | 0.917 | 0.785 | −13,950 | 14,037 |
| 2016–19 | MNQ | 5,697 | 43.6 | 7.25 | 0.10 | +0.093 | −0.004 | 1.215 | 1.106 | +6,485 | 1,435 |
| 2016–19 | MES | 5,922 | 39.7 | 2.50 | 0.10 | −0.039 | −0.143 | 1.044 | 0.930 | −3,923 | 4,988 |
| 2020–26 | MNQ | 9,271 | 43.1 | 27.00 | 0.03 | +0.085 | +0.060 | 1.136 | 1.107 | +37,981 | 4,847 |
| 2020–26 | MES | 9,623 | 40.9 | 6.00 | 0.04 | +0.002 | −0.042 | 1.026 | 0.979 | −4,539 | 7,245 |

Mean R before costs, with 95% intervals from resampling days:

| | 2016–19 | 2020–26 |
|---|---|---|
| MNQ | +0.093 [+0.061, +0.127] | +0.085 [+0.058, +0.111] |
| MES | −0.039 [−0.070, −0.008] | +0.002 [−0.022, +0.027] |

- **By year (net):** MES is positive only in 2023 and 2024 (+$329, +$1,252). MNQ is positive in every year
  from 2017 on. MES mean R is below MNQ's in all 17 years.
- **Costs are not the cause.** Cost per trade in R is similar on both (0.10 vs 0.10 in 2016–19; 0.03 vs 0.04
  in 2020–26). The gap is already there before costs.
- **The win rate is the difference:** it is 2–4 points lower on MES in every period. A win is about +1R or
  more and a loss about −1R, so each point of win rate is worth roughly 0.02 R per trade. That accounts for
  most of the gap in mean R.
- **Different trades, related days:** only 18% of entries fall in the same minute on both symbols. Daily
  net-R correlation is +0.56.
- **Data holes:** 8 MES trades fall on the two ES data-gap days (2020-02-28, 2020-06-30), net −$480.
  This is negligible next to the totals.

## Caveats

- ES candles are coarser in ticks: the median 2020–26 risk is 24 ticks on ES vs 108 on NQ. Tick rounding
  of the stop, entry and 1R target weighs more on ES. This could explain part of the gap, but not a gross
  edge of zero.
- The comparison is one instrument and one fixed rule set. It does not show *why* NQ differs. Candidates
  are NQ's stronger trend over 2010–2026 and its higher intraday volatility relative to tick size.

## Reproduce

```powershell
.\venv\Scripts\python.exe python\prepare_instrument_baseline.py
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\instrument_baseline_20261008 RTL_runband
.\venv\Scripts\python.exe python\analyze_instrument_baseline.py
```
