# MaxRedRun train/test on clean data

2026-10-01 · Runs: `Reports/maxredrun_clean_20261001/` · Analysis: `python/analyze_maxredrun_clean_study.py`
Symbol: `MNQcontDTBNT20102026_2`

## Protocol (fixed before running)

**Question:** does the red-run cap, first chosen on the old data (winner: 3), hold up on the
rebuilt data?

**Setup:** current runband EA, RR 1.0, calendar on, fallback on, trail off, 1 contract.
Same rule as the original 2026-09-29 test, except training starts in 2016, because pre-2016
data has different market hours.

1. **Train, 2016-01-01 → 2020-01-01:** `MaxRedRun` ∈ {0 (off), 1, 2, …, 7}, 8 single runs.
   Winner = highest **gross PF**. A tie within 0.005 goes to the larger cap (off counts as the
   largest, the least restrictive).
2. **Test, 2020-01-02 → 2026-07-14:** the winner, frozen, vs off.

**How to read it:** the winner's PF and DD should beat off in the test period, as cap 3 did on
the old data (PF up, DD −17%, profit flat). Caveat: 2020–26 has been seen before, and cap 3 was
evaluated on it. This is a robustness check on clean data, not a fresh out-of-sample test.

## Summary

- **Training picked cap 1** (gross PF 1.239). Cap 3 came second (1.215), outside the 0.005 tie
  margin. As on the old data, caps 1 and 3 lead, 2 dips between them, and every cap from 1 to 6
  beats off.
- **The frozen test confirms the direction:** on 2020–26, cap 1 raises net PF 1.098 → 1.134, cuts
  DD by 30% (5,768 → 4,030) and raises average R +0.048 → +0.064 vs off.
- **But it costs 23% of profit** ($39.4k → $30.3k), because it skips 38% of trades.
- **Cap 3 (current baseline)** sits in between: PF 1.108, DD −16%, profit −2.4%, and the best
  net/DD (7.95 vs 7.52 for cap 1 and 6.83 for off). Cap 3's 2020–26 numbers were seen before, so
  they're a reference, not a test.
- **Conclusion:** the red-run cap is confirmed on clean data. The exact value is a trade-off,
  not a single right answer: **1 = maximum risk reduction, 3 = balanced**. This matches the
  original finding (low caps best risk-adjusted, higher caps more profit).

## Results (net of $1/trade; DD = net closed-balance drawdown; no trade crosses a date)

**Train, 2016–19** (selection by gross PF):

| MaxRedRun | 1 | 2 | 3 | 4 | 5 | 6 | 7 | off |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Trades | 3,931 | 5,185 | 5,697 | 5,961 | 6,067 | 6,112 | 6,148 | 6,167 |
| Gross $ | 8,894 | 10,096 | 12,467 | 12,036 | 11,505 | 11,124 | 10,549 | 10,892 |
| **Gross PF** | **1.239** | 1.192 | 1.215 | 1.194 | 1.180 | 1.172 | 1.161 | 1.166 |
| Net $ | 4,962 | 4,911 | 6,770 | 6,075 | 5,438 | 5,012 | 4,401 | 4,725 |
| Net DD | 1,257 | 1,676 | 1,427 | 2,068 | 2,042 | 2,058 | 2,025 | 2,166 |

**Test, 2020–26:**

| Rule | Trades | Gross PF | Net $ | Net PF | Net DD $ | Net / DD | Avg net R |
|---|---:|---:|---:|---:|---:|---:|---:|
| Off | 10,165 | 1.125 | **39,398** | 1.098 | 5,768 | 6.83 | +0.048 |
| **Cap 1 (frozen winner)** | 6,258 | **1.164** | 30,298 | **1.134** | **4,030** | 7.52 | **+0.064** |
| *Cap 3 (reference; seen before)* | *9,271* | *—* | *38,444* | *1.108* | *4,837* | *7.95* | *+0.061* |

## Verification

- All 10 runs reconcile trade counts and gross PnL with MT5 stats; each run's `max_red_run`
  matches its job; no trade crosses a date.
- Cap-3 reference row: `Reports/rr_clean_20261001` (RR 1.0, same symbol and EA).

```powershell
.\venv\Scripts\python.exe python\prepare_maxredrun_clean_study.py              # training jobs
.\python\run_exit_study.ps1 -StudyDir Reports\maxredrun_clean_20261001 -ExpertName RTL_runband_cal -InstallFolder ClaudeEarlyClose
.\venv\Scripts\python.exe python\analyze_maxredrun_clean_study.py              # applies the selection rule
.\venv\Scripts\python.exe python\prepare_maxredrun_clean_study.py --test-cap 1 # adds the frozen test jobs
# run the runner again (completed jobs are skipped), then analyze again
```
