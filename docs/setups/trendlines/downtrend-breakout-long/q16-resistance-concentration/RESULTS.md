# Q16: is the Q15 falling-resistance result broadly distributed?

2026-10-04 · [Protocol](PROTOCOL.md) ·
[Analysis](../../../../../python/analyze_resistance_concentration.py) ·
[Line events](../../../../../Reports/trendlines/resistance_concentration_20261004/line_events.csv) ·
[Concentration tables](../../../../../Reports/trendlines/resistance_concentration_20261004/concentration.csv)

**Yes, much more so than Q13's weekly-low lead. The Q15 advantage is spread
across hundreds of lines and weeks, and it survives every single-year and
single-week deletion in both periods. Symmetric trimming leaves it
unchanged. It is a small per-trade edge, not a few big events.** The
week-clustered intervals for mean R still just include zero, and only an
intentionally adverse removal of the top ~10-20 winners erases it. The
stand-alone EA run remains the right next test.

Same population as Q15: one week, N = 5, 412 / 693 candidate fills, original
RTL exit, $1.05 cost; the complement is every other signal. No new
observations; 2026 ends July 13.

## How clustered are the trades?

A line event is one falling line (its two anchor bars). Repeated trades at that
line are one cluster.

| Measure | 2016-2019 | 2020-2026 | Q13 weekly low (for contrast) |
|---|---:|---:|---:|
| Candidate trades | 412 | 693 | 101 / 175 |
| Distinct lines with fills | 329 | 558 | 50 / 76 events |
| Lines with exactly one fill | 259 | 450 | 25 / 33 |
| Maximum fills at one line | 3 | 5 | 7 / 9 |
| Calendar weeks with candidate fills | 165 | 274 | |
| Lines with positive net $ | 171/329 | 281/558 | 29/50, 37/76 |
| Weeks with positive net $ | 93/165 | 143/274 | |

Almost every line contributes one or two trades. The effective number of
clusters is close to the number of trades, unlike Q13, where 79% of trades sat
in repeated clusters. About half of the lines are profitable. This is a
typical RTL-like payoff (median trade about -1R), where the edge comes from
the size of the winners.

**Equal weighting by line.** Giving each line equal weight gives mean R
**+0.181 / +0.206**, above the trade-weighted +0.093 / +0.110. Each candidate
trade beats the mean of the other trades in its own calendar week by an
average of **+0.208 / +0.180R**, with comparators for all trades. The
per-line median of that difference is near zero (174/329 and 274/558 lines
positive), consistent with a skewed payoff.

## Yearly distribution

| Year | Fills | Lines | Net $ | PF | Mean R | Mean-R diff | PF diff |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2016 | 119 | 92 | +311 | 1.315 | -0.030 | +0.092 | +0.383 |
| 2017 | 83 | 71 | +146 | 1.305 | +0.254 | +0.283 | +0.203 |
| 2018 | 102 | 78 | +503 | 1.289 | +0.131 | +0.103 | +0.219 |
| 2019 | 108 | 88 | +525 | 1.384 | +0.069 | -0.011 | +0.174 |
| 2020 | 107 | 88 | +779 | 1.226 | +0.158 | +0.083 | +0.142 |
| 2021 | 115 | 95 | -114 | 0.970 | +0.101 | +0.058 | -0.059 |
| 2022 | 113 | 84 | +1,882 | 1.457 | +0.115 | +0.077 | +0.415 |
| 2023 | 115 | 90 | +392 | 1.144 | -0.000 | -0.062 | +0.011 |
| 2024 | 99 | 80 | +202 | 1.054 | +0.079 | -0.003 | -0.156 |
| 2025 | 89 | 76 | +1,186 | 1.299 | +0.038 | +0.005 | +0.245 |
| 2026 partial | 55 | 45 | +3,943 | 2.249 | +0.424 | +0.362 | +1.136 |

Candidates are profitable in 10 of 11 years. They beat the rest in mean R in
8/11 years and in PF in 9/11. 2023-2024 are the flat spot: candidates are
still profitable, but no better than the rest.

## Remove a year or a week

Each deletion removes that calendar unit from both groups.

| Scope | Mean-R diff > 0 after deleting one year | Range | After deleting one candidate week | PF diff > 0 (year; week) |
|---|---:|---:|---:|---:|
| 2016-2019 | 4/4 | +0.058 to +0.144 | 165/165 (+0.089 to +0.118) | 4/4; 165/165 |
| 2020-2026 | 7/7 | +0.027 to +0.077 | 274/274 (+0.044 to +0.063) | 7/7; 274/274 |
| Pooled | 11/11 | +0.055 to +0.089 | 439/439 | 11/11; 439/439 |

Removing partial 2026, the strongest year, leaves the recent advantage at
+0.027R and PF +0.113. No single week moves the recent advantage by more than
about 0.01R. This is the opposite of Q13, where single deletions flipped the
recent sign.

## Big winners

| Share of period net, ranked by net $ | 2016-2019 | 2020-2026 | Q13 (for contrast) |
|---|---:|---:|---:|
| Largest trade | 11% | 10% | 38% / 45% |
| Best 5 trades | 51% | 38% | 140% / 112% |
| Best 5 trades / gross winning dollars | 13% | 9% | 29% / 31% |
| Largest line event | 11% | 10% | 32% / 53% (weekly event) |
| Largest calendar week | 15% | 14% | |

**Adverse removal stress.** Removing the best winners from the candidates only
leaves the complement untouched, so it is deliberately unfair:

- Removing the best 5 trades by dollars keeps both differences positive in
  both periods (mean R +0.066 / +0.041, PF +0.072 / +0.117).
- Removing the best 10 trades by R makes the recent mean-R difference
  slightly negative (-0.014); recent PF stays ahead (+0.172).
- Removing the best 20 trades by dollars makes PF negative in both periods.

A small edge in a skewed payoff disappears when the right tail is deleted from
one side only. This is expected, not a sign of a fake result.

**Symmetric trimming, the fair version.**

| Removed from each tail | Earlier cand / rest mean R | Diff | Recent cand / rest mean R | Diff |
|---|---:|---:|---:|---:|
| None | +0.093 / -0.012 | +0.105 | +0.110 / +0.056 | +0.054 |
| 5% | -0.004 / -0.112 | +0.108 | +0.006 / -0.052 | +0.058 |
| 10% | -0.062 / -0.166 | +0.104 | -0.057 / -0.109 | +0.053 |

The difference does not shrink with trimming. The advantage is a shift of the
whole distribution, not a product of extreme trades. Absolute expectancy does
depend on the tails: as for the whole RTL strategy, the bar-close exit lives
on its winners.

## Uncertainty

Paired calendar-week bootstrap (5,000 draws, all weeks retained):

| Period | Mean-R diff [95%] | PF diff [95%] |
|---|---:|---:|
| 2016-2019 | +0.105 [-0.037, +0.249] | +0.237 [-0.076, +0.608] |
| 2020-2026 | +0.054 [-0.039, +0.149] | +0.242 [+0.015, +0.520] |
| Pooled | +0.073 [-0.009, +0.157] | +0.241 [+0.027, +0.484] |

The weekly intervals agree with Q15's monthly ones. PF excludes zero recently
and pooled; mean R narrowly includes zero everywhere. There is no untouched
validation sample.

## Secondary label: entry below the line (post-hoc, not a candidate)

This is the narrow version that stays under the line, reported only as a
label as agreed:

| Period | Fills | PF (vs rest) | Mean R (vs rest) | Week-bootstrap mean-R diff |
|---|---:|---:|---:|---:|
| 2016-2019 | 238 | 1.412 (1.088) | +0.146 (-0.012) | +0.158 [-0.030, +0.359] |
| 2020-2026 | 398 | 1.548 (1.090) | +0.191 (+0.056) | +0.135 [+0.011, +0.267] |

It is stronger: mean R beats the rest in 10/11 years (worse in 2023), while
PF is worse in 2021, 2023 and 2024. It was found after seeing Q15, so its intervals are
optimistic. It stays a label in the EA run.

## Verification

- Q15's 17 input and 9 output hashes were verified, and the 412/693 counts,
  PF, net and mean R reproduced.
- Anchors map to times positionally from the M30 reference, and both precede
  every signal. Line, week and year sums reconcile to all 1,105 candidate trades.
- Three new unit tests (line identity across weeks, anchor timing, whole-week
  removal with a fixed complement) pass, and Q13's seven still pass. One
  pandas index-alignment bug in the anchor-time lookup was caught by a test
  before the run.
- Outputs: `Reports/trendlines/resistance_concentration_20261004/`. No MT5 run.

## What this means for the stand-alone EA

The audit gives no reason to stop: the result is not a handful of lucky
weeks. The EA run should show:

- a broadly spread, modest edge;
- many small losses and fewer large winners;
- weaker years such as 2021 and 2023-2024.

A run whose profit came from a few weeks would contradict this audit and
point to an execution difference.
