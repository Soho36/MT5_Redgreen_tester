# Q13: is the previous-week-low result broadly distributed?

2026-10-04 · [Protocol](WEEKLY_LOW_ROBUSTNESS_PROTOCOL.md) ·
[Analysis](../../python/analyze_weekly_low_robustness.py) ·
[Summary data](../../Reports/levels/weekly_low_robustness_20261004/summary.csv) ·
[Weekly events](../../Reports/levels/weekly_low_robustness_20261004/weekly_events.csv)

**The earlier advantage is distributed across years and survives single-event
deletions. Recent dollar profit is concentrated in a few years/weeks/trades,
and its small average-R advantage is fragile.** The result is not purely one
outlier: pooled deletions, symmetric trimming and equal-event weighting retain
positive comparisons. These diagnostics do not establish a reliable filter.

Same Q12 population and original RTL exit: 101 contact fills in 2016-2019 and
175 in 2020-2026; exact range contact with the previous calendar week's low,
no open/close-side requirement; $1.05 round-trip cost. This audit creates no
new observations and changes no trading rule. 2026 ends July 13.

## How many distinct events?

A weekly-level event is identified by the source calendar week and contract,
active in the following week. Repeated trades at that level are one cluster;
equal prices in different weeks are different events. Adjacent weeks can still
be dependent, so these counts are not a measured effective independent sample.

| Measure | 2016-2019 | 2020-2026 | Combined |
|---|---:|---:|---:|
| Contact trades | 101 | 175 | 276 |
| Events with potential contact signals | 69 | 112 | 181 |
| Events with filled contact trades | 50 | 76 | 126 |
| Events with exactly one fill | 25 | 33 | 58 |
| Trades belonging to events with multiple fills | 76 | 142 | 218 |
| Maximum fills at one weekly level | 7 | 9 | 9 |
| Events with positive net dollars | 29/50 | 37/76 | 66/126 |
| Events with positive total R | 30/50 | 38/76 | 68/126 |

Thus 79% of the 276 trades belong to repeated-trade events. Treating all 276
as independent would ignore substantial clustering. Only half of the recent
filled events have positive total R; positive aggregate profit is not a uniform
feature of weekly contacts.

## Yearly distribution

Differences compare contact with every other qualifying red signal's filled
trades in the same year. PF is calculated in dollars at one contract; mean R
normalizes each trade by its own initial risk, so the two can disagree.

| Year | Contact fills | Weekly events | Contact net $ | Contact PF | Contact mean R | Mean-R difference |
|---|---:|---:|---:|---:|---:|---:|
| 2016 | 24 | 13 | 206.80 | 1.847 | +0.089 | +0.207 |
| 2017 | 26 | 13 | 167.70 | 1.916 | +0.254 | +0.271 |
| 2018 | 35 | 15 | -190.75 | 0.833 | +0.064 | +0.029 |
| 2019 | 16 | 9 | 273.20 | 2.483 | +0.546 | +0.473 |
| 2020 | 17 | 9 | 28.15 | 1.034 | +0.060 | -0.022 |
| 2021 | 20 | 10 | -2.00 | 0.998 | +0.074 | +0.027 |
| 2022 | 47 | 17 | -1,316.85 | 0.690 | -0.148 | -0.197 |
| 2023 | 27 | 12 | 555.15 | 1.609 | +0.310 | +0.258 |
| 2024 | 22 | 8 | -83.60 | 0.936 | -0.076 | -0.161 |
| 2025 | 23 | 12 | 2,423.85 | 2.743 | +0.277 | +0.247 |
| 2026 partial | 19 | 8 | 2,649.05 | 3.121 | +0.221 | +0.136 |

Mean R beats the rest in 8/11 years, but dollar PF beats it in only 6/11.
Recent contact net is **+$4,253.75**. Of that, 2025 plus partial 2026 contribute
**+$5,072.90**; 2020-2024 together contribute **-$819.15**. The dollar result
is therefore materially concentrated at the end of the sample.

## Remove a year or a weekly event

Each deletion removes that calendar year/week from both contact and complement;
these are sensitivity checks, not rules to exclude losing periods.

| Scope | Positive mean-R difference after deleting one year | After deleting one contact week | Positive PF difference after year / week deletion |
|---|---:|---:|---:|
| 2016-2019 | 4/4 | 50/50 | 4/4; 50/50 |
| 2020-2026 | 4/7 | 69/76 | 7/7; 76/76 |
| Combined | 11/11 | 126/126 | 11/11; 126/126 |

The earlier mean-R advantage remains +0.164 to +0.286 when any year is removed.
Recently, omitting 2023, 2025 or 2026 changes the +0.0136R advantage to
-0.0311R, -0.0226R or -0.0022R respectively. Seven single-week deletions also
make it negative (worst -0.0192R). Recent PF still exceeds the complement under
every single-year/week deletion. This is a specific weakness of the tiny
normalized-return advantage, not a claim that one deletion destroys every metric.

Pooled figures survive every single-year/week deletion, but pooling hides the
much stronger earlier normalized result. Keep the two periods separate.

## Large winners and profit concentration

| Contribution, ranked by net dollars | 2016-2019 | 2020-2026 |
|---|---:|---:|
| Largest trade / period net | 37.7% | 45.0% |
| Best 5 trades / period net | 139.8% | 111.7% |
| Best 5 trades / gross winning-trade dollars | 28.9% | 31.1% |
| Largest weekly event / period net | 32.3% | 52.7% |
| Best 3 weekly events / period net | 75.7% | 103.7% |
| Best 3 events / sum of positive event net dollars | 24.1% | 42.3% |

Shares above 100% mean the remaining observations sum to a loss; they are not
shares of gross profit. Such concentration can occur in valid trading systems
too, so deleting winners is an intentionally adverse stress, not a significance
test or proof of an invalid strategy.

The recent largest event is the active week beginning **2025-04-07**, referencing
the low of the week beginning March 31: two fills net **$2,239.90**. The largest
single trade is the **2025-04-09 18:30 signal**, net **$1,912.45**, or **+5.395R**.
Removing just that contact trade, leaving the complement fixed, changes the
recent mean-R advantage from **+0.0136R to -0.0170R**. Contact PF remains above
the complement (difference +0.1145).

For perspective, the full recent candidate's excess over its period's other-
trade mean is only **2.376R** in total, while that one trade's excess is 5.335R.
This is an arithmetic benchmark, not realized extra profit from a filter.

Removing the best five dollar winners makes the PF comparison negative in both
periods; mean-R differences become +0.128R / -0.061R. Removing the best five
R winners leaves mean-R differences +0.092R / -0.084R. Full 1/5/10/20 trade and
1/3/5/10 event tables, with the actual IDs, are in
[concentration.csv](../../Reports/levels/weekly_low_robustness_20261004/concentration.csv).

## Evidence against a simple "just outliers" explanation

Trimming the same fraction from both tails of each group's R distribution
retains a relative advantage, although recent trimmed contact expectancy itself
becomes negative:

| Removed from each tail | Earlier contact/rest mean R | Difference | Recent contact/rest mean R | Difference |
|---|---:|---:|---:|---:|
| None | +0.195 / -0.008 | +0.203 | +0.073 / +0.060 | +0.014 |
| 5% | +0.151 / -0.109 | +0.260 | -0.013 / -0.048 | +0.036 |
| 10% | +0.125 / -0.164 | +0.289 | -0.054 / -0.107 | +0.053 |

Median contact R is +0.208 / -0.255, versus -1.025 / -1.007 for the rest.
The contrast is therefore not only in the most extreme winning trades.

Giving each filled weekly event equal weight produces contact mean R
**+0.306 / +0.207**, higher than the trade-weighted +0.195 / +0.073. Compared
with other trades during those same active weeks, the equal-event mean
difference is **+0.281 / +0.176R**. There are valid same-week comparators for all
50 / 76 events, and 29 / 39 events beat them. Changing weights changes the
question; it does not demonstrate that first-touch trading would work, or turn
the result into a verified strategy edge.

## Uncertainty and conclusion

Paired calendar-week bootstrap intervals (5,000 draws, empty weeks retained):

| Period | Mean-R difference [95% interval] | PF difference [95% interval] |
|---|---:|---:|
| 2016-2019 | +0.203 [-0.014, +0.431] | +0.160 [-0.322, +1.075] |
| 2020-2026 | +0.014 [-0.150, +0.194] | +0.288 [-0.238, +1.033] |
| Combined | +0.084 [-0.048, +0.231] | +0.270 [-0.190, +0.947] |

All include zero. Q12's earlier monthly interval for mean R barely excluded
zero; the weekly interval does not. Neither choice proves independence, and
changing the resampling unit is not a reason to select the more favourable
interval. There is no untouched validation sample.

The best-supported answer is mixed: **the earlier advantage is spread through
time, while recent dollar profit is concentrated and recent incremental R is
fragile**. Robust trimming and equal-event comparisons keep the idea interesting,
but do not remove the small-sample and regime uncertainty. Preserve the result
as inconclusive; do not introduce a weekly-low filter or tune smaller subgroups.

## Verification and files

Q12 was committed separately as `7d99d5e`. This follow-up verified all 18 Q12
input hashes and 8 output hashes, reconstructed contact and event identity from
source metadata, and reproduced the 101/175 fill counts and PF/net/R totals.
Event sums reconcile to all 276 contact trades; no event is double-counted across
the period split. Seven tests cover event identity/time boundaries, unavailable
levels, trimming, paired cluster resampling and deletion semantics.

Generated ledgers, yearly tables, deletion tests, concentration/trim tables,
bootstrap summaries and provenance are in
`Reports/levels/weekly_low_robustness_20261004/`. Production code and the original
Q10-Q12 outputs are unchanged. No new MT5 run was needed.
