# Tighter stop with a scaled target (RTL, NQ and YM)

2026-10-23 · Exploratory, user idea, no pre-set gate · [Baseline studies](../README.md)

## Summary

- **Question (user):** if the buy stop creates the edge, does a tighter stop help? Stop at entry − k × candle range
  (k = 0.75, 0.5) instead of the candle low, with the 1R bar-close target shrinking with it.
- **Answer: no. Rejected.** Net R per trade (result per dollar risked) is worse than the full stop in 16 of 17 years at
  both k on NQ, and in 16 or 17 of 17 years on YM. Before costs the tighter stop earns the same or less per R
  (NQ 2020–26: +0.072 → +0.052 / +0.064); costs per R rise because the risk is smaller (0.024 → 0.033 / 0.051).
  At one contract NQ 2020–26 falls from $38.4k to $19.3k (k = 0.75) and $13.7k (k = 0.5).
- **Why:** a tighter stop is hit far more often (win rate 43% → 40% → 36% on NQ) and the trades it frees up add more
  entries (+18% / +38%) of no better quality. Exiting at a smaller target also gives up part of the run after the
  breakout, the same lesson as the [trade-path](../trade-paths/RESULTS.md) and earlier exit studies.

## Setup

| | |
|---|---|
| EA | `RTL_stopfrac` = uncapped RTL baseline plus one input `StopFraction` (k): stop at entry − k × candle range, rounded to the tick. The exit code is unchanged and already targets entry + 1 × (entry − stop), so the target scales with the stop. Built by [prepare_stop_fraction.py](../../../python/prepare_stop_fraction.py) |
| Runs | k = 1.0 / 0.75 / 0.5 on NQ (`MNQcontDTBNT20102026_2`) and YM (`MYMcontDTBNT20102026`), M30, 1-minute OHLC, 2010-06-07 → 2026-10-23, every input in the INI; trades before 2026-10-01 |
| R | profit ÷ actual risk (entry − stop) × $/pt, so R is per dollar risked at each k. Costs $1.05 per trade |
| Checks | k = 1.0 reproduces the RTL baseline ledgers exactly (NQ 25,833, YM 26,299 trades). All six ledgers audited against the MT5 reports, no recovered trades, totals match |

## Results

"Diff" = mean gross R minus k = 1, 95% interval resampling days jointly.

| Inst | Period | k | Trades | Win % | Gross R | Diff | Diff 95% | Cost R | Net R | Net $ | PF net | Max DD $ |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| NQ | 2016–19 | 1.0 | 6,167 | 43.4 | +0.081 | | | 0.095 | −0.014 | 4,417 | 1.064 | 2,176 |
| | | 0.75 | 7,412 | 40.0 | +0.064 | −0.016 | −0.037 … +0.004 | 0.132 | −0.068 | 388 | 1.006 | 3,575 |
| | | 0.5 | 8,647 | 35.1 | +0.066 | −0.015 | −0.045 … +0.016 | 0.210 | −0.144 | −3,098 | 0.947 | 5,113 |
| NQ | 2020–26 | 1.0 | 10,501 | 42.8 | +0.072 | | | 0.024 | +0.048 | 38,400 | 1.090 | 5,781 |
| | | 0.75 | 12,430 | 39.8 | +0.052 | −0.020 | −0.035 … −0.004 | 0.033 | +0.019 | 19,282 | 1.048 | 5,551 |
| | | 0.5 | 14,522 | 35.6 | +0.064 | −0.007 | −0.027 … +0.014 | 0.051 | +0.013 | 13,739 | 1.041 | 4,745 |
| YM | 2016–19 | 1.0 | 6,209 | 42.6 | +0.056 | | | 0.126 | −0.070 | 691 | 1.013 | 2,261 |
| | | 0.75 | 7,476 | 38.8 | +0.034 | −0.021 | −0.042 … −0.002 | 0.176 | −0.141 | −2,606 | 0.949 | 3,811 |
| | | 0.5 | 8,760 | 32.9 | −0.004 | −0.060 | −0.091 … −0.029 | 0.284 | −0.288 | −7,480 | 0.834 | 7,825 |
| YM | 2020–26 | 1.0 | 10,889 | 40.7 | +0.014 | | | 0.060 | −0.046 | −2,467 | 0.987 | 5,403 |
| | | 0.75 | 12,870 | 37.9 | +0.010 | −0.004 | −0.019 … +0.011 | 0.083 | −0.073 | −8,368 | 0.952 | 11,243 |
| | | 0.5 | 14,899 | 33.9 | +0.029 | +0.015 | −0.007 … +0.038 | 0.129 | −0.101 | −11,037 | 0.925 | 12,942 |

2010–15 is worse at every k on both (`Reports/stop_fraction_20261023/summary.csv`). Net R by year:
`net_R_by_year.csv`; the tighter stop beats k = 1 in at most 1 of 17 years for any instrument and k.

- **Before costs** the tighter stop is never clearly better: the only positive difference (YM 2020–26, k = 0.5,
  +0.015) has an interval including zero and is outweighed by costs that more than double per R.
- **Sizing by dollar risk does not rescue it:** net R, the per-dollar measure, is lower in every period on both.
- The earlier ledger estimate (tighter stop, target left at the original 1R) looked better per dollar on NQ 2020–26
  only at k = 0.25; that variant is a different trade (reward-to-risk up to 4) and was not consistent across periods.

## Reproduce

```powershell
.\venv\Scripts\python.exe python\prepare_stop_fraction.py
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\stop_fraction_20261023 RTL_stopfrac
.\venv\Scripts\python.exe python\analyze_stop_fraction.py
```
