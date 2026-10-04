# Previous-week-low contact: yearly comparison

2026-10-04 · [Q13 robustness results](WEEKLY_LOW_ROBUSTNESS_RESULTS.md) ·
[Reproduce this view](../../python/summarize_weekly_low_years.py)

This is a clearer presentation of existing Q13 outcomes, with the other-RTL
average alongside PWL. It adds no trades or selection rules. PWL means broad
exact-price contact; original RTL exit and $1.05 round-trip cost. Other RTL
means every other qualifying red signal's filled trades in the same year,
including signals for which the level was unavailable. R is net of costs.

| Year | PWL trades | PWL avg R | Other RTL avg R | Difference | Weekly events |
|---|---:|---:|---:|---:|---:|
| 2016 | 24 | +0.089 | -0.118 | +0.207 | 13 |
| 2017 | 26 | +0.254 | -0.017 | +0.271 | 13 |
| 2018 | 35 | +0.064 | +0.035 | +0.029 | 15 |
| 2019 | 16 | +0.547 | +0.074 | +0.473 | 9 |
| 2020 | 17 | +0.060 | +0.082 | -0.022 | 9 |
| 2021 | 20 | +0.074 | +0.047 | +0.027 | 10 |
| 2022 | 47 | -0.147 | +0.050 | -0.197 | 17 |
| 2023 | 27 | +0.310 | +0.052 | +0.258 | 12 |
| 2024 | 22 | -0.076 | +0.085 | -0.161 | 8 |
| 2025 | 23 | +0.277 | +0.030 | +0.247 | 12 |
| 2026* | 19 | +0.220 | +0.085 | +0.136 | 8 |

*2026 is partial, through July 13. Weekly events group repeated trades sharing
the same source week and contract; adjacent events need not be independent.

The relative pattern is positive in all four earlier years, though 2018 is
close to zero. Recently it alternates: slightly negative, slightly positive,
negative, positive, negative, positive, positive. This does not show a smooth
decline followed by a uniquely large rebound in 2025-2026. Calling it random
would also go beyond what these small samples establish.

Three distinctions explain the apparent difference from the dollar summary:

- **2023 was already a strong relative year.** Its +0.258R advantage exceeds
  2025's +0.247R and 2026's +0.136R. The largest annual advantage is 2019.
- **Loss-making PWL years matter more than a broad baseline deterioration.**
  In 2022 and 2024 PWL mean R is negative while other RTL mean R stays positive.
  Those years contain 69/175 recent PWL trades (39%); 2022 alone has 47, the
  largest yearly contact sample. The recent aggregate mixes those frequent
  weak trades with less frequent good years.
- **Dollars and normalized R describe different weights.** With one contract,
  a trade's dollars equal its net R times its own initial dollar risk. Thus
  2020-2024 contact trades total +2.260R but -$819.15, while 2025-2026 total
  +10.559R and +$5,072.90. Dollar concentration does not imply that the
  normalized advantage existed only in the last two years.

For descriptive context, giving each recent year equal weight yields a mean
annual difference of +0.041R. Weighting those annual differences by PWL trade
counts yields +0.0147R, close to the period's +0.0136R aggregate comparison.
The small discrepancy comes from using each year's comparator rather than
the whole-period comparator. Equal-year weights change the question and do
not improve an actual strategy's return or establish a regime rule.

## The same years at event level

Sum and median here refer to each event's total R from all its filled contact
trades. The last column averages each event's per-trade mean R equally.

| Year | Events | Positive total R | Sum of event R | Median event total R | Equal-event avg R/trade |
|---|---:|---:|---:|---:|---:|
| 2016 | 13 | 8/13 | +2.140 | +0.928 | +0.234 |
| 2017 | 13 | 9/13 | +6.605 | +0.324 | +0.259 |
| 2018 | 15 | 6/15 | +2.230 | -0.132 | +0.160 |
| 2019 | 9 | 7/9 | +8.744 | +1.193 | +0.723 |
| 2020 | 9 | 6/9 | +1.014 | +0.846 | +0.264 |
| 2021 | 10 | 5/10 | +1.480 | +0.301 | +0.273 |
| 2022 | 17 | 8/17 | -6.932 | -0.105 | -0.063 |
| 2023 | 12 | 7/12 | +8.379 | +0.515 | +0.771 |
| 2024 | 8 | 4/8 | -1.681 | -0.288 | +0.177 |
| 2025 | 12 | 4/12 | +6.370 | -0.500 | +0.000 |
| 2026* | 8 | 4/8 | +4.189 | +0.014 | +0.132 |

In 2025 only 4/12 events have positive total R, and the median event loses
0.5R, despite strong annual PF/mean R. Several productive events carry that
year, rather than uniformly better performance at most weekly lows. In 2023,
7/12 events are positive and the median total is +0.515R. Positive event rate
alone also does not settle relative trade performance: 2020 has 6/9 positive
events but trails other RTL slightly in average R.

The yearly view identifies where variation comes from: interleaved good and
bad years, differing trade frequency, risk weighting and event concentration.
It cannot establish whether volatility, trend conditions or sampling noise
caused that variation. Preserve the inconclusive Q13 conclusion; a regime
explanation would require a separately specified comparison.

Verification: all Q13 input/output hashes match. The generation script checks
all 11 yearly comparisons against saved filled trades and reconciles the 126
event/year sums to the same 276 contacts. No new MT5 run was needed.
