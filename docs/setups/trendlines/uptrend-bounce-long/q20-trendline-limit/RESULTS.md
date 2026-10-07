# Q20: buy limit resting on a rising trendline

2026-10-05 · [Frozen protocol](PROTOCOL.md) (frozen `4c86411`) ·
[Analysis](../../../../../python/analyze_trendline_limit.py) · [EA include](../../../../../mt5/experts/trendline_limit.mqh) ·
[Trade checks](../../../../../python/verify_trendline_limit_trade.py) ·
Run folder: `Reports/trendlines/trendline_limit_runs_20261005/`

## Answer

**No. A buy limit resting on the frozen Q14 rising lines loses money in both
decision periods. It fails the frozen rule on its own numbers, before the
control matters.** PF is 0.773 in 2016-19 and 0.969 in 2020-26; mean net R is
-0.238 and -0.023. It beats the matched control's mean R in 2 of 9 eligible
years. Every sensitivity also loses money in at least one period. No
filter, no strategy, nothing adopted.

This rejects the frozen **1R bar-close exit** configuration. Other RiskReward
values were not tested, so it does not establish that every target or every
trendline buy-limit strategy loses money.

| Period | Run | Trades | Net $ | PF | Mean net R | Win % | Closed DD $ |
|---|---|---:|---:|---:|---:|---:|---:|
| 2016-19 | **Primary** (line, stop 0.5 x A) | 1,484 | -2,502 | **0.773** | **-0.238** | 30.9 | 2,713 |
| 2016-19 | C1 (same bars, random distance) | 426 | -84 | 0.955 | -0.067 | 39.0 | 266 |
| 2016-19 | C2 (every bar, random distance) | 435 | -149 | 0.922 | -0.094 | 38.4 | 310 |
| 2020-26 | **Primary** | 2,370 | -1,707 | **0.969** | **-0.023** | 32.9 | 3,118 |
| 2020-26 | C1 | 516 | -702 | 0.916 | -0.037 | 36.2 | 1,081 |
| 2020-26 | C2 | 542 | +269 | 1.032 | +0.015 | 37.6 | 784 |
| 2010-15 | Primary | 2,031 | -2,532 | 0.698 | -0.335 | 30.8 | 2,617 |
| 2010-15 | C1 | 584 | -824 | 0.572 | -0.427 | 30.3 | 824 |

For context, the RTL baseline is PF 1.106 / 1.107, mean R -0.004 / +0.060.
That is a different mechanic and not a decision basis.

**Reading rule (frozen):**

| Condition | 2016-19 | 2020-26 |
|---|---|---|
| >= 200 trades | pass (1,484) | pass (2,370) |
| PF > 1 | **fail** (0.773) | **fail** (0.969) |
| Mean net R > 0 | **fail** (-0.238) | **fail** (-0.023) |
| Mean R > C1 | **fail** (-0.238 vs -0.067) | pass (-0.023 vs -0.037) |
| Trade-through: PF > 1 and mean R > its C1 | **fail** (0.743; -0.282 vs -0.084) | **fail** (0.957; -0.035 vs -0.024) |
| Stop 0.25 x A beats its C1 | **fail** (-0.381 vs -0.326) | pass (+0.005 vs -0.076) |
| Stop 1.0 x A beats its C1 | **fail** (-0.160 vs +0.066) | **fail** (-0.063 vs +0.045) |
| Mean R beats C1 in >= 7 of 11 years | **fail: 2 of 9 eligible** (2021, 2025) | |

Paired week-block bootstrap of primary minus C1 (5,000 resamples, seed
20261005): mean R difference [-0.345, +0.008] in 2016-19 and [-0.116, +0.145]
in 2020-26. PF difference [-0.448, +0.060] and [-0.152, +0.246]. Neither
interval favours the line.

## Why it loses: price usually goes through the line

- **45% of primary trades are stopped out in the bar they fill.** That is
  1,727 of 3,854 trades in 2016-26; the control's rate is 37%.
- **Stops dominate the exits:** 67% stop, 31% target, 2% session flatten.
- **A touch that holds is rarely a fill.** The tester's ask is one tick above
  the bid, so a fill already needs the bid to trade one tick through the line.
  The fills therefore over-represent bars that keep going. Requiring one more
  tick (trade-through) changes little (PF 0.743 / 0.957).
- **Cost matters in the earlier period.** 1R averages 4.98 points in 2016-19,
  so the $1.05 round trip is 0.15R per trade. Even before costs, 2016-19 loses
  about $940. In 2020-26 (1R = 17.3 points, cost 0.04R), gross is about +$780,
  and costs turn it negative.
- **A wider stop does not rescue it:** stop 1.0 x A gives PF 0.776 / 0.915.
  A tighter one gives 0.698 / 0.993. Only the 1.0 x A control is profitable
  (PF 1.042 / 1.073).

## What the control can and cannot say

The control comparison is a secondary point here, because the primary fails on
its own numbers. Two features of the frozen control matter for reading it:

- **It trades far less**: 426 / 516 trades against 1,484 / 2,370. The primary
  has one episode per line, and another line can carry the next order. C1 has
  a single episode. After a fill at P it waits for a close >= P + A.
- **That wait can last for months.** After a fill in late 2021, C1 placed no
  order in 2022 and only 9 in 2023 (C2 the same). Price stayed below P + A
  through the bear market. C1 therefore skipped most of the 2022 decline,
  which the primary traded (335 trades, mean R -0.052). This makes C1 a weak
  benchmark in those years. Two of the 11 years are ineligible, leaving 9. It
  does not change the answer, because the primary fails PF > 1 and mean R > 0
  regardless.

## Year by year (primary vs C1, mean net R)

| Year | Primary trades | Primary mean R | C1 trades | C1 mean R | Primary better |
|---|---:|---:|---:|---:|---|
| 2016 | 362 | -0.299 | 42 | -0.198 | no |
| 2017 | 356 | -0.281 | 207 | -0.162 | no |
| 2018 | 368 | -0.244 | 89 | +0.058 | no |
| 2019 | 398 | -0.137 | 88 | +0.095 | no |
| 2020 | 382 | -0.183 | 113 | +0.085 | no |
| 2021 | 363 | +0.016 | 121 | -0.206 | yes |
| 2022 | 335 | -0.052 | 0 | - | not eligible |
| 2023 | 346 | +0.017 | 9 | -0.928 | not eligible |
| 2024 | 365 | +0.056 | 120 | +0.085 | no |
| 2025 | 379 | +0.073 | 103 | -0.008 | yes |
| 2026 partial | 200 | -0.133 | 50 | -0.094 | no |

The primary's mean R is positive only in 2021 and 2023-2025. Every year from
2010 to 2020 is negative.

## Descriptive labels (primary; not candidates)

Full table: `labels.csv` in the run folder. None is better in both periods.

- **First retest vs later:** both lose (PF 0.742 / 0.975 first; 0.780 / 0.968
  later).
- **Slope, anchor separation, bars since anchor 2, time of day:** no cell is
  above PF 1 in 2016-19. A few 2020-26 cells reach about PF 1.04-1.05: 10-20
  bar anchor separation, and <= 20 bars since anchor 2. Their 2016-19 cells
  are 0.848 and 0.794.
- **Fill-bar colour and depth below the line are outcomes, not filters.** Both
  are measured on the bar in which the order filled, so they are known only
  after entry.
  - A fill bar that closed green has PF about 5. A fill bar that went more
    than 0.5 x A under the line has, by construction, hit the stop
    (PF 0.03-0.06).
  - They show only that the trade is decided in the fill bar, not which fills
    to take. On candle colour: the entry is colour-blind (as you proposed),
    and the colour only becomes known afterwards.

## Verification

- **Classify-only run** (no orders): EA = Python on all 184,888 eligible bars
  ([details](PROTOCOL.md#pre-trade-verification-done-2026-10-05-no-outcomes)).
  It was repeated in the trading build (`classify` job), and the log was
  byte-identical.
- **Every trading run (9) was replayed bar by bar in Python** from closed bars
  and the run's own fills.
  - Primary: lines minus consumed episodes. Controls: classify status, control
    arming and the delta table.
  - **0 mismatches** in action, status, limit, stop, anchors and line counts.
    Each run has 17,000-99,000 orders.
- **Execution audit, every run:**
  - every fill comes from a logged order, at or below its limit, with the
    logged stop;
  - the trade ledger matches the fills (time, price, stop, planned R);
  - one position at a time; every trade exits the session it entered;
  - MT5 trade count and net match the ledger;
  - 0 send, cancel or log errors.
- **Bar-boundary effect (documented, not corrected).** The tester matches
  orders on a bar's first tick before the EA re-prices.
  - So 2-4 fills per run (4 of 5,885 primary fills over the full history) come
    from the previous bar's order, on an opening gap.
  - In 0-3 bars per run, a stop hit at the open leaves the EA flat in time to
    log that bar.
  - The order was genuinely live in each case.
- **OHLC ambiguity:** in 7% of primary trades (111 / 162), the fill minute also
  reached the stop. One-minute OHLC decides the order inside such a minute.
- **Control delta check tolerance:** delta was logged with 10 decimals, so it
  is compared to the table at 1e-10. The first check at 5e-11 flagged 2-4
  rounding-only rows per control run, whose limits and stops matched.

## Limits

- One line definition (frozen Q14), one entry rule and the baseline exit.
  Other exits, line definitions and first-touch-only were not run, as the
  protocol states, and are not opened now.
- One-minute OHLC with the tester's one-tick spread; no real ticks or queue
  position. Real queue priority would make bounce fills rarer still.
- All years had been examined in earlier studies.

## Independent audit and RiskReward correction (2026-10-05)

[`audit_trendline_limit_results.py`](../../../../../python/audit_trendline_limit_results.py)
recomputed the trade count, net, PF, mean net R, win rate and closed drawdown
from the original MT5 ledgers for all nine trading runs and all three periods.
All match `summary.json`; 62 recorded source/input/output hashes match. The
annual comparison and the 5,000-resample bootstrap intervals also match.
Audit output: `Reports/trendlines/trendline_limit_audit_20261005/audit.json`.

The inherited research EA contains an input bug: `FreezeTrendAtEntry()` assigns
the exit multiplier from **BullRR/BearRR**, with 1.0 in neutral/warmup regimes.
`ManageOpenPosition()` uses that multiplier; **RiskReward does not control the
target** in the saved Q20 build. It mainly controls the CSV name and reported
setting. All saved trading INIs have RiskReward = BullRR = BearRR = 1.0.
All 30,661 ledger trades have assigned RR = 1.0, and every one of the 38,491
logged target checks matches entry + (entry - initial stop), the M30 reference
close and its qualification flag. Target exits occur at the first qualifying
logged check; all exits meet the session/early-close cutoff. Thus the input bug
does **not** invalidate the reported 1R results. A manual test changing only
RiskReward in that original build still tests 1R.

The completed run folder is preserved. The generator now assigns RiskReward
after freezing the daily labels and rejects nonpositive/nonfinite RR inputs.
[`build_trendline_limit_ea.py`](../../../../../python/build_trendline_limit_ea.py) builds
[`RTL_trendline_limit_manual.mq5`](../../../../../mt5/experts/RTL_trendline_limit_manual.mq5),
a standalone tester EA with the saved primary input defaults, RiskReward as
the target multiplier in every regime, and BullRR/BearRR removed from the input
panel. It compiles with 0 errors and 0 warnings. The corrected build has not
had a fresh MT5 execution run in this audit; the 1R equivalence follows from
the target assignment and the saved all-1R inputs. Changed-RR results remain
unstudied.

The negative result is trustworthy for this configuration and execution model.
The C1 comparison is weaker evidence about whether the line price itself adds
value: its global re-arm lockout differs from the primary's per-line episodes,
and its distance distribution is calibrated using the full history. Neither
comparison nor the exploratory bootstrap is untouched out-of-sample evidence.
