# Flatten fallback: fix and RR rerun

2026-10-01 · Runs: `Reports/flatten_fallback_20261001/` · Analysis: `python/analyze_flatten_study.py`

## Summary

- **Bug:** the EA flattened only on a bar opening at exactly 23:30. On early-close
  days (holidays, Black Friday, Dec 24) and in March/Oct–Nov DST-mismatch weeks
  that bar doesn't exist, so positions stayed open for up to **6.5 days**.
- **Fix:** new input `FlattenFallback` (default `true`). The EA now flattens at the
  first bar at or after 23:30. If a date ends with no flatten, it flattens on the
  first bar of the next date. `false` restores the old behaviour exactly.
- **Result:** multi-day holds are gone. The longest hold is now one overnight (or
  one weekend). The RR 1.0 baseline barely changes.
- **Not yet solved:** about 70–95 trades still hold **one overnight gap**, because
  the real session ended early. At higher RR those gaps still carry a lot of money
  (2.5R: $7.7k of $41.6k in 2020–26). Removing them needs a calendar of known
  early closes. See [Next](#next).
- **RR:** after the fix, no RR value wins in dollars in both periods. In average R,
  higher RR wins in both. The choice depends on the sizing policy, which is still
  open. **Keep RR = 1.0.**

## Results (net of $1/trade; DD = net closed-balance drawdown)

| Period | RR | Trades | Net $ | Net PF | Net DD | Avg net R | Cross-date trades | Their net $ | **Same-day net $** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015–19 | 1.0 | 7,194 | 7,172 | 1.098 | 1,434 | −0.012 | 69 | 60 | **7,112** |
| 2015–19 | 1.1 | 7,004 | 7,568 | 1.103 | 1,671 | −0.005 | 69 | 112 | **7,456** |
| 2015–19 | 2.0 | 6,039 | 9,726 | 1.136 | 1,478 | +0.024 | 77 | 721 | **9,005** |
| 2015–19 | 2.5 | 5,698 | 9,740 | 1.139 | 1,451 | +0.023 | 82 | 1,166 | **8,574** |
| 2020–26 | 1.0 | 9,258 | 37,419 | 1.105 | 5,134 | +0.060 | 72 | 1,456 | **35,963** |
| 2020–26 | 1.1 | 9,023 | 41,962 | 1.118 | 4,502 | +0.065 | 74 | 2,098 | **39,864** |
| 2020–26 | 2.0 | 7,746 | 37,376 | 1.108 | 5,158 | +0.076 | 94 | 6,796 | **30,580** |
| 2020–26 | 2.5 | 7,314 | 41,626 | 1.123 | 4,530 | +0.094 | 95 | 7,746 | **33,880** |

Before vs after the fix (old = the earlier runs with fallback off):

| Period / RR | Net $ old → fixed | Cross-date $ old → fixed | Longest hold, h old → fixed |
|---|---|---|---|
| 2015–19 / 1.0 | 8,008 → 7,172 | 869 → 60 | 122 → 75 |
| 2015–19 / 2.0 | 9,994 → 9,726 | 1,031 → 721 | 138 → 57 |
| 2020–26 / 1.0 | 37,291 → 37,419 | 1,962 → 1,456 | 77 → 77 |
| 2020–26 / 1.1 | 42,362 → 41,962 | 2,851 → 2,098 | 77 → 77 |
| 2020–26 / 2.0 | 39,958 → 37,376 | 9,532 → 6,796 | 101 → 77 |
| 2020–26 / 2.5 | 43,701 → 41,626 | 9,381 → 7,746 | 156 → 77 |

## What it means

1. **The baseline was barely affected** (2020–26: +$128; 2015–19: −$836). Earlier
   entry-filter conclusions at RR 1.0 stand.
2. **Higher RR relied on the multi-day holds.** The fix removed $2.1–2.6k of the
   2.0R/2.5R advantage in 2020–26. Counting only same-day trades, 2.0R and 2.5R
   earn *less* than 1.0R in 2020–26 but *more* in 2015–19. The dollar verdict flips
   between periods.
3. **Average R rises with RR in both periods,** even on same-day trades. With
   one contract, big-candle trades rarely reach a distant target before the
   session ends, which hurts dollars. Small-candle trades benefit, which
   helps R.
4. **1.1R looks slightly better than 1.0R in both periods** (+$0.3k / +$3.9k same-day).
   It's a single 0.1 step from a noisy grid, so it's not adopted, but it's worth a
   note.

## Next

- **Flatten before a known early close.** CME publishes holiday and early-close
  times in advance, and DST-mismatch weeks follow fixed rules. A session calendar
  in the EA would remove the remaining overnight gaps without hindsight.
  Then rerun 1.0 and 2.5R.
- **Decide the sizing policy** (fixed contracts vs fixed risk). That decides between
  1R and 2–2.5R.

## Verification

- Compiled with 0 errors, 0 warnings. `FlattenFallback=false` at RR 1.0 reproduces
  all 9,147 trades of `rr_cap3_corrected_20260930` field by field.
- All 9 runs reconcile trade counts and gross PnL with MT5 stats. The stats file
  records `flatten_fallback`.
- Every remaining cross-date trade exits on the first bar of the next date (00:00 or
  01:00). The median hold for those is 7 h.
- **Reproducing older studies:** their INIs don't set `FlattenFallback`, so with the
  new default they'd run with the fix. Add `FlattenFallback=false` to reproduce them.

```powershell
.\venv\Scripts\python.exe python\prepare_flatten_study.py
# compile Reports\flatten_fallback_20261001\RTL_runband_flatfix.mq5 in MetaEditor
.\python\run_exit_study.ps1 -StudyDir Reports\flatten_fallback_20261001 -ExpertName RTL_runband_flatfix -InstallFolder ClaudeFlattenFix
.\venv\Scripts\python.exe python\analyze_flatten_study.py
```
