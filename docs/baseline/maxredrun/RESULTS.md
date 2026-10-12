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
- **2026-10-13 update:** with the data to 2026-10-01, cap 3 no longer lowers drawdown and earns 5.7% less than
  off. Cap 1 still passes. **The user dropped the cap; the baseline is now no cap.** See the
  [extended test](#extended-test-to-2026-10-01-2026-10-13).

## Results (net of $1/trade; DD = net closed-balance drawdown; no trade crosses a date)

**Train, 2016-01-01 → 2020-01-01** (selection by gross PF):

| MaxRedRun | 1 | 2 | 3 | 4 | 5 | 6 | 7 | off |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Trades | 3,931 | 5,185 | 5,697 | 5,961 | 6,067 | 6,112 | 6,148 | 6,167 |
| Gross $ | 8,894 | 10,096 | 12,467 | 12,036 | 11,505 | 11,124 | 10,549 | 10,892 |
| **Gross PF** | **1.239** | 1.192 | 1.215 | 1.194 | 1.180 | 1.172 | 1.161 | 1.166 |
| Net $ | 4,962 | 4,911 | 6,770 | 6,075 | 5,438 | 5,012 | 4,401 | 4,725 |
| Net DD | 1,257 | 1,676 | 1,427 | 2,068 | 2,042 | 2,058 | 2,025 | 2,166 |

**Test, 2020-01-02 → 2026-07-14** (the symbol holds data to 2026-10-01; the end date was kept from earlier studies):

| Rule | Trades | Gross PF | Net $ | Net PF | Net DD $ | Net / DD | Avg net R |
|---|---:|---:|---:|---:|---:|---:|---:|
| Off | 10,165 | 1.125 | **39,398** | 1.098 | 5,768 | 6.83 | +0.048 |
| **Cap 1 (frozen winner)** | 6,258 | **1.164** | 30,298 | **1.134** | **4,030** | 7.52 | **+0.064** |
| *Cap 3 (reference; seen before)* | *9,271* | *—* | *38,444* | *1.108* | *4,837* | *7.95* | *+0.061* |

## Extended test to 2026-10-01 (2026-10-13)

**Why:** the user reran cap 3 and off to the end of the data and saw cap 3 behind. 2026-07-14 → 2026-10-01
(58 trading days) was never used by any study. Protocol fixed before the runs: same EA, symbol and settings,
off / cap 1 / cap 3, 2020-01-01 → 2026-10-13; same reading as above (net PF higher and net DD lower than off).

**Summary**

- **The user's figures are right.** Gross profit to 2026-10-01: off $49,561, cap 3 $46,365, the same as the
  manual runs. Trades before 2026-07-14 reproduce the original three ledgers exactly.
- **Cap 3 no longer passes.** Its drawdown is now higher than off (5,980 vs 5,781), net is 5.7% lower and net
  PF is only 0.006 higher. The drawdown benefit was the reason it was kept.
- **Cap 1, the frozen winner, still passes** on PF and drawdown, at the same price: 23% less profit.
- **The new slice alone decides nothing.** Cap 3 is $1,303 behind off there, with an interval of −3,339 to +687.
  Off itself lost $356 in those 58 days.
- **In dollars, cap 3 and off cannot be told apart:** −$2,212 over the extended test, interval −11,006 to +6,678.
  Per trade the cap still helps a little: mean R +0.012 higher, interval +0.003 to +0.021.

Net of $1.05 a trade (the tables above use $1, so the original-window figures differ slightly):

| Rule | Trades | Net $ | Net PF | Net DD $ | Net / DD | Avg net R |
|---|---:|---:|---:|---:|---:|---:|
| **Extended test, 2020-01-02 → 2026-10-01** | | | | | | |
| Off | 10,502 | 38,534 | 1.091 | 5,781 | 6.67 | +0.048 |
| Cap 1 | 6,449 | 29,830 | 1.125 | 4,036 | 7.39 | +0.063 |
| Cap 3 | 9,565 | 36,322 | 1.097 | 5,980 | 6.07 | +0.059 |
| **Original window, to 2026-07-13** | | | | | | |
| Off | 10,165 | 38,890 | 1.097 | 5,781 | 6.73 | +0.047 |
| Cap 1 | 6,258 | 29,985 | 1.132 | 4,036 | 7.43 | +0.063 |
| Cap 3 | 9,271 | 37,981 | 1.107 | 4,847 | 7.84 | +0.060 |
| **New slice, 2026-07-14 → 2026-10-01** | | | | | | |
| Off | 337 | −356 | 0.984 | 3,010 | | |
| Cap 1 | 191 | −155 | 0.987 | 2,201 | | |
| Cap 3 | 294 | −1,659 | 0.917 | 4,086 | | |

Cap 3 minus off, net $ by entry year:

| 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to 10-01) |
|---:|---:|---:|---:|---:|---:|---:|
| +1,156 | +707 | +747 | +452 | −382 | −2,739 | −2,153 |

- **The cap helped in 2020–23 and cost money in 2024–26.** 2025 and the first half of 2026 were already inside
  the original test; earlier years hid them.
- **One month moved the drawdown.** Cap 3's deepest drawdown now runs 2026-06-16 → 2026-07-30. In July 2026 cap 3
  lost $4,031 and off lost $1,711.
- **Why R and dollars disagree:** trades after more than three reds average about −0.03 R against +0.09 R for the
  rest (off ledger, original window), so removing them raises the average trade. But in 2025–26 they made
  money in dollars (+$1,425 and +$2,382), because their winners came on large candles.
- **Limits:** 58 days is short and the dollar differences are inside the noise in both directions. This shows
  that cap 3 has no demonstrated dollar or drawdown benefit at one contract. It does not show that the cap hurts.
- **Decision (user, 2026-10-13): the cap is dropped. The baseline is `MaxRedRun = 0`.** Studies dated earlier
  used cap 3 and are not rerun. With a fixed contract count the dollar result is what counts, and the cap shows
  nothing there. If sizing ever moves to a fixed dollar risk per trade, the per-trade R result becomes the
  dollar result and the cap is worth testing again.

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
# Extended test (2026-10-13)
.\venv\Scripts\python.exe python\prepare_maxredrun_extended.py
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\maxredrun_extended_20261013 RTL_runband
.\venv\Scripts\python.exe python\analyze_maxredrun_extended.py
```
