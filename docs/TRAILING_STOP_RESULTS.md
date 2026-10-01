# Trailing stop after +1R

2026-10-01 · Runs: `Reports/trailing_stop_20261001/` · Analysis: `python/analyze_trailing_study.py`

## Protocol (fixed before running)

**Question:** can a trailing stop capture part of the ~0.3–0.4R give-back between a
trade's best point and its bar-close exit, without capping the big runners the way
a resting limit does? The limit version was estimated worse at every level; see
[STATUS](STATUS.md).

**Rule tested.** Everything in the baseline stays unchanged (entry, initial SL,
bar-close ≥ 1R exit, 23:30 flatten with fallback, `MaxRedRun = 3`, RR 1.0, 1 contract).
Added on every tick:
- Once bid ≥ entry + **1.0R** (`TrailStartR = 1.0`), the stop trails at
  highest bid since entry − **D × R** (`TrailDistanceR = D`).
- The stop only moves up, never below the current stop. It's rounded down to the
  tick size and respects the broker's minimum stop distance.
- `TrailDistanceR = 0` disables trailing (the baseline).

**Arms:** D = 0.25, 0.5, 1.0 in 2015-01-01 → 2020-01-01 and 2020-01-02 → 2026-07-14,
plus a trailing-off control in each period (8 runs). The controls must reproduce
the flatten-fixed RR 1.0 runs field by field.

**Decision rule:** a distance is adopted as a candidate only if it beats the
baseline on **both** net $ and average net R, in **both** periods. Otherwise it's
recorded as rejected. No other distances will be tried in response to the results.

**Known limitation:** the tester's 1-minute OHLC model generates only a few prices
per minute. Trailing exits depend on the intrabar path, so they're less exact than
bar-close exits. Tick-data runs would be needed before trading a trailing rule.

## Summary

- **Rejected at all three distances** by the pre-set rule. None beats the baseline
  on both net $ and average net R in both periods.
- **2015–19: every distance is clearly worse** (net $4.1k / $3.5k / $4.6k vs $7.2k).
- **2020–26: mixed.** 0.25R earns more ($41.5k vs $37.4k) with lower DD, but lower
  average R. The extra dollars come from about 870 *extra* trades: exiting sooner
  frees the position for more entries. 0.25R is also the setting most sensitive to
  the tester's coarse intrabar prices, so it's the least trustworthy result here.
- **Conclusion:** a trailing stop doesn't reliably recover the give-back. With the
  resting-limit estimate, this closes the "capture the wick" idea. **Keep the
  bar-close exit.**

## Results (net of $1/trade; DD = net closed-balance drawdown)

| Period | Trail | Trades | Net $ | Net PF | Net DD $ | Avg net R |
|---|---|---:|---:|---:|---:|---:|
| 2015–19 | off (baseline) | 7,194 | **7,172** | **1.098** | 1,434 | **−0.012** |
| 2015–19 | 0.25R | 7,879 | 4,106 | 1.060 | 1,394 | −0.025 |
| 2015–19 | 0.50R | 7,856 | 3,466 | 1.051 | 1,638 | −0.039 |
| 2015–19 | 1.00R | 7,694 | 4,638 | 1.069 | 1,580 | −0.032 |
| 2020–26 | off (baseline) | 9,258 | 37,419 | 1.105 | 5,134 | **+0.060** |
| 2020–26 | 0.25R | 10,125 | **41,523** | **1.127** | 4,578 | +0.059 |
| 2020–26 | 0.50R | 10,096 | 35,093 | 1.108 | 4,566 | +0.047 |
| 2020–26 | 1.00R | 9,854 | 37,570 | 1.117 | **4,435** | +0.049 |

Why it doesn't work: the trail exits winners early on ordinary pullbacks inside the
run. The runners that make the bar-close exit profitable often dip 0.25–1R before
continuing. The trail also changes which trades happen (+500–900 trades), so part of
any difference is a different trade population, not a better exit.

## Verification

- Compiled with 0 errors, 0 warnings. Both trailing-off controls reproduce the
  flatten-fixed RR 1.0 runs field by field (7,194 / 9,258 trades).
- All 8 runs reconcile trade counts and gross PnL with MT5 stats. The stats file
  records `trail_start_r` and `trail_distance_r`.
- There were no failed stop modifications. The trail was active: stop-loss exits
  in 2020–26 rise from 4,984 (off) to 9,098 (0.25R) and 6,610 (1.0R).

```powershell
.\venv\Scripts\python.exe python\prepare_trailing_study.py
# compile Reports\trailing_stop_20261001\RTL_runband_trail.mq5 in MetaEditor
.\python\run_exit_study.ps1 -StudyDir Reports\trailing_stop_20261001 -ExpertName RTL_runband_trail -InstallFolder ClaudeTrailingStop
.\venv\Scripts\python.exe python\analyze_trailing_study.py
```
