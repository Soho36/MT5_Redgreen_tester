# Q21: short the breakdown of a rising trendline

2026-10-06 · [Frozen protocol](BREAKDOWN_SHORT_PROTOCOL.md) (frozen `04630e8`) ·
[Analysis](../../python/analyze_trendline_breakdown.py) · [EA include](../../mt5/experts/trendline_breakdown.mqh) ·
[Trade checks](../../python/verify_trendline_breakdown_trade.py) ·
Run folder: `Reports/trendlines/trendline_breakdown_runs_20261006/`

## Answer

**No. Shorting a red M30 candle that closes below a rising Q14 line, with a
sell stop at its low, loses money in both decision periods. It fails the
frozen rule.** PF is 0.893 in 2016-19 and 0.916 in 2020-26; mean net R is
-0.081 and -0.025. It loses before costs too. The break *is* a slightly
better short than any red candle in the same regime (C1), but every variant of
this short loses on NQ. No filter, no strategy, nothing adopted.

This rejects the frozen **1R bar-close exit** configuration, with an order
living one bar. Other targets, stops and order lives were not tested.

| Period | Run | Trades | Net $ | PF | Mean net R | Win % | Closed DD $ |
|---|---|---:|---:|---:|---:|---:|---:|
| 2016-19 | **Primary** (any close below the line) | 558 | -1,144 | **0.893** | **-0.081** | 38.4 | 1,550 |
| 2016-19 | S1 (close > 0.5 x A below) | 573 | -1,190 | 0.891 | -0.087 | 39.1 | 1,662 |
| 2016-19 | C1 (any red bar, armed-line regime) | 3,797 | -4,518 | 0.899 | -0.142 | 36.8 | 5,582 |
| 2016-19 | C2 (any red bar) | 6,211 | -13,445 | 0.840 | -0.149 | 36.5 | 14,573 |
| 2020-26 | **Primary** | 928 | -5,070 | **0.916** | **-0.025** | 40.3 | 8,253 |
| 2020-26 | S1 | 972 | -6,106 | 0.904 | -0.030 | 39.6 | 7,684 |
| 2020-26 | C1 | 6,210 | -8,879 | 0.964 | -0.044 | 38.1 | 13,802 |
| 2020-26 | C2 | 10,450 | -14,326 | 0.969 | -0.032 | 38.5 | 19,125 |
| 2010-15 | Primary | 775 | -1,550 | 0.800 | -0.154 | 38.3 | 1,762 |
| 2010-15 | C1 | 5,025 | -9,464 | 0.717 | -0.293 | 34.7 | 9,583 |

For context, the RTL baseline (long) is PF 1.106 / 1.107, mean R -0.004 /
+0.060. That is a different mechanic and not a decision basis.

**Reading rule (frozen):**

| Condition | 2016-19 | 2020-26 |
|---|---|---|
| >= 200 trades | pass (558) | pass (928) |
| PF > 1 | **fail** (0.893) | **fail** (0.916) |
| Mean net R > 0 | **fail** (-0.081) | **fail** (-0.025) |
| Mean R > C1 | pass (-0.081 vs -0.142) | pass (-0.025 vs -0.044) |
| S1: PF > 1 | **fail** (0.891) | **fail** (0.904) |
| S1: mean R > C1 | pass (-0.087 vs -0.142) | pass (-0.030 vs -0.044) |
| Mean R beats C1 in >= 7 of 11 years | **fail: 6 of 11** (2016, 2017, 2021, 2023, 2025, 2026) | |

Paired week-block bootstrap of primary minus C1 (5,000 resamples, seed
20261006): mean R difference [-0.031, +0.153] in 2016-19 and [-0.058, +0.094]
in 2020-26. PF difference [-0.157, +0.184] and [-0.190, +0.114]. Both intervals
include zero, so even the advantage over C1 is not established.

## Why it loses: the 1R target is reached less often than the stop

- **Stops dominate:** 51% of primary trades stop out, 32% reach the 1R
  bar-close target and 17% are flattened at the session end. Win rate is
  38-40% against a symmetric 1R stop and target. The median trade is -1.0R in
  every run.
- **It is not cost.** The breakdown candle is wide (1R averages 19.9 points
  in 2016-19 and 68 points in 2020-26), so the $1.05 round trip is only 0.06R
  and 0.02R. Gross before costs is still -$559 and -$4,096.
- **It is not the fill bar.** Only 6-8% of primary trades (2016-26) stop out in the bar
  they fill (Q20's buy limit: 45%). The entry is clean. Price simply does not
  continue down by another full candle range more often than it recovers it.
- **Any red-candle short loses on NQ.** C2 (every red bar) has PF 0.840 /
  0.969 and C1 0.899 / 0.964. The line break improves on them a little in mean
  R, but not enough to cross zero.
- **Not even the 2022 bear market helps.** The primary lost $2,316 in 2022
  (mean R -0.082) while C1 made $5,930 (+0.058).

## Year by year (primary vs C1, mean net R)

| Year | Primary trades | Primary mean R | C1 trades | C1 mean R | Primary better |
|---|---:|---:|---:|---:|---|
| 2016 | 141 | -0.055 | 830 | -0.107 | yes |
| 2017 | 113 | +0.007 | 962 | -0.305 | yes |
| 2018 | 156 | -0.167 | 991 | -0.075 | no |
| 2019 | 148 | -0.083 | 1,014 | -0.082 | no |
| 2020 | 145 | -0.016 | 976 | +0.003 | no |
| 2021 | 134 | +0.038 | 935 | -0.061 | yes |
| 2022 | 143 | -0.082 | 870 | +0.058 | no |
| 2023 | 137 | -0.022 | 964 | -0.116 | yes |
| 2024 | 135 | -0.145 | 960 | -0.078 | no |
| 2025 | 147 | +0.108 | 1,011 | -0.035 | yes |
| 2026 partial | 87 | -0.090 | 494 | -0.093 | yes |

The primary's mean R is positive only in 2017, 2021 and 2025. S1 beats C1 in
8 of 11 years but is positive only in 2022, 2023 and 2025.

## Descriptive labels (primary; not candidates)

Full table: `labels.csv` in the run folder. **No cell has PF > 1 in both
periods.** The best-looking cells flip between periods:

- close in 20-50% of the bar: PF 0.957 / 1.147;
- break depth <= 0.25 x A: 1.066 / 0.910;
- >= 2 earlier retests: 1.126 / 0.907;
- anchor separation 10-20 bars: 1.120 / 0.857.

Breaks of two or more lines at once are the worst cell in both periods
(PF 0.608 / 0.706, 58 / 93 trades). Bars that opened already below the line
(a gap through it) are 13% of trades and mixed (0.995 / 0.707).

## Verification

- **Classify-only regression:** the trading build's BreakMode = 1 log is
  byte-identical to the verified classify-only log (EA = Python on all
  184,888 bars; see the [protocol](BREAKDOWN_SHORT_PROTOCOL.md#pre-trade-verification-done-2026-10-06-no-outcomes)).
- **Every trading run (4) was replayed against that log.** The
  classification does not depend on fills, so each logged row must carry its
  bar's verified classification, and the action follows from it.
  - **0 mismatches** in status, bar s, line, anchors, line counts, colour,
    contract, bid, action and order prices (sell stop = low(s), stop = high(s)).
  - Logged rows: 174,880 (primary), 174,560 (S1), 137,364 (C1), 105,259 (C2).
  - Primary and S1 placed at most one order per line.
- **Execution audit, every run:**
  - every fill is a short from a logged order, at or below its entry, with the
    logged stop;
  - the ledger matches the fills (time, price, stop, planned R, signal bar),
    is short in every row, and has RiskReward = 1.0 in every row;
  - one position at a time; every trade exits the session it entered;
  - MT5 trade count and net match the ledger;
  - 0 log, send, cancel or close errors.
- **Short-side build:** the long-only parent gained a direction flag (risk =
  sl - entry for a short), a mirrored bar-close exit (buy to cover after a
  close <= entry - 1R), a direction-aware ledger and qualified flag, and a
  window exit that cancels the sell stop. The diff against the parent touches
  only those lines. RiskReward sets the target in every regime (the Q20
  audit's BullRR/BearRR bug is excluded).
- **Bar-boundary effect (documented, not corrected), as in Q20.** The tester
  matches stops and pending orders on a bar's first tick, before OnTick.
  - 1-11 fills per run (2 of 2,261 primary) come from the previous bar's
    order. Some fall where the M1 data has no minute at the bar open, so the
    bar's first tick comes minutes late (e.g. 2013-07-17 09:31).
  - 1-24 logged bars per run (2 primary) follow a stop hit on the bar's first
    tick, which left the EA flat in time to log the bar.
  - All are explained by those two cases; 0 unexplained.
- **OHLC ambiguity:** in 14 primary trades over the full history, the fill
  minute's high also reached the stop (ask = bid + 1 tick). One-minute OHLC
  decides the order inside such a minute.

## Limits

- One line definition (frozen Q14), one entry rule, the baseline 1R exit and
  one-bar order life. Other targets, stops and order lives were not run, as
  the protocol states, and are not opened now.
- One-minute OHLC with the tester's one-tick spread; no real ticks.
- All years had been examined in earlier studies. NQ's upward drift is the
  headwind for every short tested here.
