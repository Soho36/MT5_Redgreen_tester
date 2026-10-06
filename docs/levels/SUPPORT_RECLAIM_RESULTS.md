# Q24: buy the reclaim of a broken swing-low level

2026-10-07 · [Frozen protocol](SUPPORT_RECLAIM_PROTOCOL.md) (frozen `57bc971`) ·
[Analysis](../../python/analyze_support_reclaim.py) · [EA include](../../mt5/experts/support_reclaim.mqh) ·
[Trade checks](../../python/verify_support_reclaim_trade.py) ·
Run folder: `Reports/levels/support_reclaim_runs_20261007/`

## Answer

**No. The buy stop at the broken level fails the frozen rule.** In dollars it
is profitable in both decision periods (PF 1.042 / 1.063), but per unit of risk
it loses (mean net R -0.073 / -0.051), and in 2020-26 it is worse than simply
buying the high of the same breakdown candles (C1, mean R +0.047). It beats C1
in 5 of 11 years. Nothing adopted.

| Period | Run | Trades | Net $ | PF | Mean net R | Median R | Win % | Closed DD $ |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2016-19 | **Primary** (buy stop at L) | 433 | +218 | **1.042** | **-0.073** | -1.03 | 41.3 | 417 |
| 2016-19 | C1 (buy stop at the candle high) | 188 | +250 | 1.074 | -0.109 | -0.92 | 42.6 | 571 |
| 2016-19 | S1 primary (close > 0.5 x A below L) | 176 | +311 | 1.114 | +0.029 | -0.47 | 47.2 | 413 |
| 2016-19 | S1 C1 | 88 | +560 | 1.379 | +0.009 | -0.14 | 47.7 | 254 |
| 2020-26 | **Primary** | 756 | +1,905 | **1.063** | **-0.051** | -1.01 | 37.6 | 2,394 |
| 2020-26 | C1 | 263 | +2,145 | 1.126 | +0.047 | -0.28 | 46.0 | 3,598 |
| 2020-26 | S1 primary | 289 | +16 | 1.001 | -0.039 | -1.01 | 41.5 | 2,687 |
| 2020-26 | S1 C1 | 127 | +1,517 | 1.174 | +0.078 | -0.15 | 48.0 | 2,397 |
| 2010-15 | Primary | 571 | -325 | 0.921 | -0.005 | -1.06 | 40.6 | 535 |
| 2010-15 | C1 | 251 | +529 | 1.269 | +0.093 | -0.03 | 49.4 | 284 |

For context, the RTL baseline is PF 1.106 / 1.107, mean R -0.004 / +0.060.

**Reading rule (frozen):**

| Condition | 2016-19 | 2020-26 |
|---|---|---|
| >= 200 trades | pass (433) | pass (756) |
| PF > 1 | pass (1.042) | pass (1.063) |
| Mean net R > 0 | **fail** (-0.073) | **fail** (-0.051) |
| Mean R > C1 | pass (-0.073 vs -0.109) | **fail** (-0.051 vs +0.047) |
| S1: PF > 1 | pass (1.114) | pass (1.001) |
| S1: mean R > its C1 | pass (+0.029 vs +0.009) | **fail** (-0.039 vs +0.078) |
| Mean R beats C1 in >= 7 of 11 years | **fail: 5 of 11** | |

Paired week-block bootstrap of primary minus C1 mean R (5,000 resamples, seed
20261007): [-0.119, +0.193] in 2016-19 and [-0.245, +0.043] in 2020-26.

**Skips (min risk 0.25 x A, the user's request):** 76 of 1,198 breakdowns in
2016-19 (6.3%), 150 of 2,006 in 2020-26 (7.5%), 117 of 1,677 in 2010-15
(7.0%). None under S1. Price gapped back above the level at the next open in
28 / 28 cases.

## What happens to the orders

| Period | Orders | Filled | Cancelled: low touched first | Expired (3 bars) | Window / flatten | Replaced |
|---|---:|---:|---:|---:|---:|---:|
| 2016-19 | 1,088 | 433 (40%) | 633 (58%) | 14 | 5 | 3 |
| 2020-26 | 1,818 | 756 (42%) | 1,029 (57%) | 19 | 10 | 4 |

- **Most breakdowns keep going.** In 57-58% of cases price trades below the
  breakdown candle's low before it comes back to the level.
- **Reclaims are fast or not at all:** 93% of fills come in the first bar of
  the order's life; only 14 / 19 orders expire after 3 bars.
- **A third of fills are stopped in the bar they fill** (144 / 433 and
  259 / 756). The level that was just reclaimed often caps the move, and the
  stop at the candle low is close.

## Why PF > 1 but mean R < 0

The trades with a small risk lose most often, and the larger-risk trades carry
the dollars. The R-size label (descriptive, post hoc) shows it in both
periods:

| Risk L - low(s) | 2016-19 trades / PF / R | 2020-26 trades / PF / R |
|---|---|---|
| 0.25-0.5 x A | 78 / 0.534 / -0.299 | 159 / 0.883 / -0.153 |
| 0.5-1 x A | 155 / 0.880 / -0.173 | 287 / 0.838 / -0.172 |
| 1-1.5 x A | 97 / 1.317 / +0.114 | 156 / 1.100 / +0.111 |
| > 1.5 x A | 103 / 1.156 / +0.074 | 154 / 1.355 / +0.117 |

A risk of at least 1 x ATR is positive in both periods; below it, both lose.
The minimum-risk floor of 0.25 x A was well below where the trade starts to
work. This is a label seen after the outcomes, on data examined before: it is
**not a lead under the frozen rule**, and testing a 1 x A floor would need
new, untouched data (forward or demo).

The S1 sensitivity, whose breaks are deeper and risks larger (median 1.3-1.5 x
A), is closer to break-even in R (+0.029 / -0.039), consistent with this.

## C1, the RTL entry on the same candles

Buying the breakdown candle's high fills much less often (188 / 263 trades:
the high is further away), but its fills are better per unit of risk in
2020-26 and 2010-15. It rarely stops in the fill bar (12-16 trades). The
reclaim entry gets in earlier and cheaper, and more often gets stopped
straight away.

## Year by year (primary vs C1, mean net R)

| Year | Primary trades | Primary R | C1 trades | C1 R | Primary better |
|---|---:|---:|---:|---:|---|
| 2016 | 106 | -0.102 | 50 | -0.267 | yes |
| 2017 | 96 | -0.161 | 43 | -0.288 | yes |
| 2018 | 111 | +0.044 | 46 | -0.053 | yes |
| 2019 | 120 | -0.084 | 49 | +0.155 | no |
| 2020 | 109 | +0.070 | 40 | -0.017 | yes |
| 2021 | 131 | +0.002 | 44 | +0.368 | no |
| 2022 | 122 | -0.186 | 37 | -0.444 | yes |
| 2023 | 118 | -0.114 | 46 | -0.097 | no |
| 2024 | 106 | -0.162 | 33 | +0.150 | no |
| 2025 | 118 | +0.135 | 43 | +0.166 | no |
| 2026 partial | 52 | -0.167 | 20 | +0.279 | no |

## Other descriptive labels (primary; not candidates)

Full table: `labels.csv`. Fills in the 1st bar are the bulk (PF 1.054 /
1.054). Morning orders are 0.965 / 1.696 and single-member levels 1.032 /
1.179; no label other than risk >= 1 x A is above PF 1 with positive R in both
periods.

## Verification

- **Classify-only regression:** the trading build's ReclaimMode = 1 log is
  byte-identical to the verified classify-only log (EA = Python on all
  184,888 bars).
- **Every trading run (4) replayed against that log: 0 mismatches** in
  status, bar s, level, defining pivot, line counts, colour, contract, bid,
  ask, action and order prices (entry L or high(s), stop low(s)).
- **Order life replayed on one-minute data, every order (14,541): 0
  unexplained disagreements.**
  - Each order's outcome (fill, cancel on a touch of low(s), 3-bar expiry,
    window/flatten, replacement) is predicted from the minute highs and lows
    and the deadlines, and matches MT5.
  - Same-minute fill-and-touch cases (OHLC-ambiguous): 90 / 3 / 19 / 2.
  - Placement-tick touches: 128 / 128 / 102 / 103 orders whose bar opened at
    or below low(s). The open tick precedes the order, so it cannot cancel it;
    nearly all were cancelled on the next tick.
  - One bar-boundary fill (S1 primary).
- **Execution fact found (not a protocol change).** Inside a minute the
  tester's ticks carry the source file's spread, 1 point = 0.01, which is
  below the 0.25 tick. A buy stop on the tick grid therefore fills only when
  the **bid** trades at the entry. With an assumed one-tick spread, 329 of
  4,350 primary orders would disagree; with this rule, none. (Bar-open quotes
  show ask = bid + 0.25, which earlier docs described; within the minute it is
  0.01.)
- **Execution audit, every run:** every fill is at or above its entry with the
  logged stop, within the 3-bar life; the ledger matches the fills; one
  position at a time; every trade exits its session; MT5 trades and net match
  the ledger; 0 send, cancel, close or log errors.
- Logged-bar differences (a fill or a stop on a bar's first tick): all
  explained, 0 unexplained.

## Limits

- One level definition (frozen Q11), one break rule, a 3-bar order life and
  the baseline 1R exit. Other stops, floors and lives were not run.
- One-minute OHLC with the tester's intrabar spread; no real ticks or queue.
- All years had been examined in earlier studies. The risk >= 1 x A split is
  post hoc.

## Exploratory follow-up: no cancellation on a touch of the low (written before the runs)

**The user's request, 2026-10-07, after the results above.** The cancel-on-
touch rule was added to the user's design while drafting; the user's own
version keeps the order. A second red bar that takes out the signal candle's
low does not invalidate the setup: if a later bar reclaims the level, the
order fills and the stop sits at the signal candle's low (it is attached to the
order but only acts once the position is live). 57-58% of Q24's orders were
cancelled by that rule.

Fixed before running:

- The same EA and inputs as Q24 except **CancelOnLow = false**: an unfilled
  buy stop lives its 3 bars (or until the window exit / flatten or a
  replacing order), whatever price does below the candle low. Runs: primary,
  C1, S1 primary and S1 C1, all without the cancellation.
- Read with Q24's frozen rule unchanged (C1 without cancellation as the
  control): >= 200 trades, PF > 1, mean net R > 0, mean R > C1 in both
  periods; >= 7 of 11 years; S1 PF > 1 and mean R > its C1. Also: the Q24
  order and cancellation counts, fills by bar of life, stops in the fill bar,
  2010-15, the bootstrap (seed 20261007).
- Exploratory: chosen after seeing Q24, on data already examined. A pass
  justifies only forward / demo evidence, not adoption. Nothing else is tried
  in this follow-up (no risk floor change).
