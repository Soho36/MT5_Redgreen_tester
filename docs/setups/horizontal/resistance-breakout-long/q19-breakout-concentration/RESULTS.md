# Q19: is the Q18 breakout result broadly distributed?

2026-10-05 · [Protocol](PROTOCOL.md) ·
[Analysis](../../../../../python/analyze_breakout_concentration.py) ·
[Level events](../../../../../Reports/levels/breakout_concentration_20261005/level_events.csv) ·
[Concentration tables](../../../../../Reports/levels/breakout_concentration_20261005/concentration.csv)

**Yes. The breakout advantage is spread across about 2,250 levels and 524
weeks, with at most 5 trades on any level. It survives every single-year
and single-week deletion, in both populations and both periods.**

It is a small per-trade edge, not a few events. It is somewhat thinner than
Q16's: symmetric trimming halves the 2016-19 gap, and removing the best 10
trades from the candidates only erases it.

Against the baseline, the week-clustered intervals for the mean-R difference
just include zero in each period, but exclude it pooled.

| Population | Candidate | Comparator |
|---|---|---|
| **Primary** | the stage-2 stand-alone trades (1,083 / 2016-19, 1,685 / 2020-26) | the full baseline strategy |
| Secondary | the stage-1 attribution (751 / 1,181) | every other signal (the Q16 setup) |

Same original exit and $1.05 cost; 2026 ends July 13. No new observations.

## Two different intervals

Q18 reported that the stand-alone run's **own mean R** has a 2020-26 interval
of [+0.049, +0.174]: the expectancy is very likely positive. This audit asks
the stricter question: is it **better than the baseline**? That difference
is smaller (+0.050R recently), and its paired week interval is
[-0.005, +0.109], just including zero. Both statements hold at once: "very
likely profitable per trade" and "probably, but not certainly, better than
plain RTL".

## How clustered are the trades?

A level event is a level price plus its latest member pivot.

| Measure | Stand-alone 2016-19 | Stand-alone 2020-26 | Attribution 2016-19 | Attribution 2020-26 |
|---|---:|---:|---:|---:|
| Trades | 1,083 | 1,685 | 751 | 1,181 |
| Distinct levels with trades | 866 | 1,382 | 632 | 1,002 |
| Levels with exactly one trade | 684 | 1,130 | 529 | 844 |
| Max trades at one level | 5 | 4 | 5 | 4 |
| Levels with positive net $ | 426 (49%) | 686 (50%) | 300 (47%) | 494 (49%) |
| Weeks with trades / positive net $ | 192 / 97 | 332 / 201 | 188 / 95 | 317 / 175 |

As in Q16, almost every level contributes one or two trades, so the
effective number of clusters is close to the number of trades.

**Equal weighting by level.** Each level weighted equally gives mean R
+0.180 / +0.206 (stand-alone), above the trade-weighted +0.062 / +0.110. Each
breakout trade beats the comparator's trades in its own week by an average of
**+0.157 / +0.118R**. Every trade has a same-week comparator. About half of
the levels are individually positive: a skewed payoff, as for RTL itself.

## Year by year (stand-alone versus baseline)

| Year | Trades | Levels | Net $ | PF | Mean R | Mean-R diff | PF diff |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2016 | 256 | 205 | -344 | 0.858 | -0.082 | +0.032 | -0.104 |
| 2017 | 279 | 227 | -106 | 0.936 | -0.019 | -0.007 | -0.177 |
| 2018 | 271 | 211 | +1,336 | 1.382 | +0.214 | +0.178 | +0.295 |
| 2019 | 277 | 223 | +856 | 1.278 | +0.130 | +0.051 | +0.055 |
| 2020 | 276 | 216 | +2,239 | 1.310 | +0.168 | +0.086 | +0.215 |
| 2021 | 258 | 219 | +70 | 1.010 | -0.016 | -0.064 | -0.014 |
| 2022 | 240 | 195 | +2,784 | 1.279 | +0.170 | +0.126 | +0.211 |
| 2023 | 257 | 212 | +1,881 | 1.281 | +0.180 | +0.123 | +0.148 |
| 2024 | 242 | 202 | +1,237 | 1.153 | +0.084 | +0.002 | -0.045 |
| 2025 | 271 | 226 | +3,072 | 1.267 | +0.116 | +0.082 | +0.199 |
| 2026 partial | 141 | 112 | +746 | 1.087 | +0.037 | -0.051 | -0.102 |

Mean R beats the baseline in 8 of 11 years. Dollar PF beats it in only 6.
The weak years are 2016-2017, 2021 and partial 2026; 2024 is a tie. The good
years are spread over 2018-2025, not bunched.

## Remove a year or a week

Each deletion removes that calendar unit from both groups.

| Population, period | Mean-R diff > 0 after one-year deletion | Range | After one-week deletion | PF diff > 0 (year; week) |
|---|---:|---:|---:|---:|
| Stand-alone 2016-19 | 4/4 | +0.029 to +0.092 | 192/192 | 3/4; 192/192 |
| Stand-alone 2020-26 | 7/7 | +0.037 to +0.071 | 332/332 | 7/7; 332/332 |
| Attribution 2016-19 | 4/4 | +0.029 to +0.086 | 188/188 | 3/4; 188/188 |
| Attribution 2020-26 | 7/7 | +0.044 to +0.110 | 317/317 | 7/7; 317/317 |

The one sign change is 2016-19 PF without 2018: -0.059 stand-alone, -0.053
attribution. Mean R stays positive. No single week moves any difference by
more than about 0.01R.

## Big winners

| Share of period net, ranked by net $ (stand-alone) | 2016-19 | 2020-26 | Q16 (for contrast) |
|---|---:|---:|---:|
| Largest trade | 16% | 16% | 11% / 10% |
| Best 5 trades | 50% | 40% | 51% / 38% |
| Best 5 trades / gross winning dollars | 7% | 7% | 13% / 9% |
| Largest level / period net | 16% | 16% | 11% / 10% (line) |
| Largest week / period net | 15% | 17% | 15% / 14% |

**Adverse removal stress** (deleting winners from the candidates only):

- **Top 5 trades by dollars:** the mean-R difference stays positive (+0.059 /
  +0.039); PF turns slightly negative earlier (-0.023), positive recently.
- **Top 10 trades by R:** the mean-R difference falls to +0.003 / +0.012.
- **Top 20:** negative (-0.037 / -0.014).

As in Q16, a small edge with a skewed payoff disappears when the right tail is
removed from one side only.

**Symmetric trimming (the fair version):**

| Removed from each tail | 2016-19 breakout / baseline mean R | Diff | 2020-26 breakout / baseline mean R | Diff |
|---|---:|---:|---:|---:|
| None | +0.062 / -0.004 | +0.066 | +0.110 / +0.060 | +0.050 |
| 5% | -0.070 / -0.105 | +0.034 | -0.009 / -0.048 | +0.039 |
| 10% | -0.129 / -0.158 | +0.029 | -0.068 / -0.106 | +0.038 |

The gap survives trimming but shrinks: about half in 2016-19 and a quarter
in 2020-26. Part of the advantage comes from better large winners, and part
from a shift of the whole distribution. Q16's gap did not shrink.

## Uncertainty of the difference

Paired calendar-week bootstrap (5,000 draws, all weeks retained):

| Population | Period | Mean-R diff [95%] | PF diff [95%] |
|---|---|---:|---:|
| Stand-alone vs baseline | 2016-19 | +0.066 [-0.008, +0.141] | +0.058 [-0.096, +0.237] |
| Stand-alone vs baseline | 2020-26 | +0.050 [-0.005, +0.109] | +0.097 [-0.035, +0.244] |
| Stand-alone vs baseline | Pooled | +0.056 **[+0.008, +0.102]** | +0.091 [-0.030, +0.218] |
| Attribution vs rest | 2016-19 | +0.061 [-0.040, +0.163] | +0.105 [-0.122, +0.370] |
| Attribution vs rest | 2020-26 | +0.070 [-0.009, +0.154] | +0.097 [-0.089, +0.312] |
| Attribution vs rest | Pooled | +0.066 **[+0.001, +0.130]** | +0.098 [-0.070, +0.286] |

The pooled mean-R intervals just exclude zero; per period they just include
it. The stand-alone and baseline runs share 734 / 1,151 identical trades. The
paired resampling keeps that dependence, but the intervals remain descriptive
and are not adjusted for the many level studies.

## Secondary label: entry below the level (post-hoc, not a candidate)

| Population | Period | Trades | PF | Mean R | Week-bootstrap mean-R diff |
|---|---|---:|---:|---:|---:|
| Stand-alone | 2016-19 | 669 | 1.243 | +0.121 | +0.125 [+0.016, +0.238] |
| Stand-alone | 2020-26 | 1,038 | 1.231 | +0.111 | +0.051 [-0.025, +0.130] |
| Attribution | 2016-19 | 431 | 1.247 | +0.110 | +0.122 [-0.018, +0.259] |
| Attribution | 2020-26 | 678 | 1.206 | +0.132 | +0.081 [-0.022, +0.187] |

Steadier across the two periods than the whole group, but chosen after seeing
results. It stays a label.

## Verification

- Q18 stage-1 (16 files, plus outputs) and stage-2 (10 files) hashes were
  verified.
- Counts and net reproduce Q18 for both populations: 1,083 / 1,685 and
  751 / 1,181 trades.
- Every trade has a level identity whose latest member precedes the signal.
- Level, week and year sums reconcile to all trades.
- Tests: a new level-identity test, plus Q16's tests for the shared
  concentration code.
- Outputs: `Reports/levels/breakout_concentration_20261005/`. No MT5 run.

## What this means

The audit gives no reason to doubt Q18 on concentration grounds. The result
is broad, not a few lucky weeks or levels, and nothing hinges on 2026.

The remaining doubts are the ones Q18 already listed:

- the comparison with plain RTL is statistically marginal per period;
- 2016-2017 lose money;
- 2010-2015 go the other way;
- execution beyond the one-minute OHLC model is untested.

Forward or demo evidence is the natural next step.
