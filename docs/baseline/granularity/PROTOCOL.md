# Fixed-grid NQ price-resolution experiment

2026-10-09. Follow-up to [NQ versus ES](../nq-vs-es/RESULTS.md). Recorded before new strategy results.

Question: does RTL's advantage over the every-bar market-buy control decline consistently when NQ prices are rounded onto wider grids, and does this persist across grid origins?

## Fixed design

- Source: `MNQcontDTBNT20102026_2`, the existing continuous NQ custom symbol.
- Existing test span and settings: 2010-06-07 to the exclusive MT5 ToDate 2026-07-14 (last tested day July 13); report 2010-15, 2016-19 and 2020-26 separately.
- Grids: 0.25, 0.50, 1.00 and 2.00 points (1, 2, 4 and 8 native ticks).
- Every distinct lattice-valid origin: j times 0.25 points, j=0 through k-1. 15 variants, each with RTL and control: 30 jobs.
- Quantize all M1 OHLC using nearest-grid rounding with exact half ties upward. In native ticks u: q=o+k*floor((u-o)/k+0.5). Native k=1 is the identity. Preserve timestamps, volumes and spread.
- Synthetic symbols copy source settings, retaining native trade tick 0.25 and $2/point. This changes data resolution, not exchange tick size. Native uses the original symbol.
- Existing signal-colour EA: RTL red cap3 and the market control buying at every eligible bar open while flat. Same RR1 bar-close exit, trade windows, early-close calendar, flatten, M30, tester Model1, 1 lot, spread and execution settings. Live trading disabled.

## Outcomes and uncertainty

- Primary descriptive contrast: mean gross R(RTL)-mean gross R(control), for each grid and origin. This is a strategy comparison, not an isolated causal estimate of entry selection.
- Show each strategy's gross R, trades, win rate, median risk, native ticks and grid steps. Net results with the existing fixed $1.05 per trade are secondary.
- Show every origin plus equal-weight origin means, origin minimum/maximum, and contrast changes versus native. Never pick the best origin or pool origins' trades.
- Resample the same source-session days jointly across all arms, 2,000 replicates with fixed seed, including zero-trade days; 95% intervals. Successive-day dependence and broader exploratory selection are not fully captured.
- Describe period-specific curves and origin sensitivity without optimizing a cutoff. No independent out-of-sample or monotonicity claim, and no new trading filter.

## Checks and interpretation

- Native RTL/control must reproduce previous signal-colour ledgers before interpreting coarse results.
- Verify source/import yearly M1 counts and spans, OHLC ordering, grid membership, copied symbol settings, ledger grid ranges, control entry times and dollar value inferred from stop losses.
- Record descriptive M30 red/green/doji/zero-range counts, median point/native-tick/grid-step ranges, and static cap3 signal eligibility lost or gained. Static signals are not orders/fills: occupancy and pending-order persistence differ.
- Quantization also changes candle colour, equal highs, red streaks, risk geometry and generated M1 OHLC paths. Robust deterioration supports sensitivity to this bundle, not proof of an order-book mechanism or transferability to ES.
- This uses the existing M1 OHLC tester, not exchange tick replay. No performance tuning after these results.

## Reproduction

Use project venv to run `python/prepare_granularity.py`, `python/run_granularity.py`, then `python/analyze_granularity.py`. Inputs, hashes, import diagnostics and results live in `Reports/granularity_20261009/`.

