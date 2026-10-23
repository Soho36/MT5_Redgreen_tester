# RTL: daily trend and volatility do not identify a reliable skip condition

2026-10-23. RTL only, current uncapped M30 / RR1 baseline, one MNQ-valued contract,
$1.05 per completed trade. [Saved plan](PLAN.md) · [Frozen protocol](PROTOCOL.md).

## Decision and plan progress

**No group qualifies as an unfavorable-period filter.** All six primary groups
made positive net dollars in both 2016-19 and 2020-September 2026. That is a
historical attribution result, not proof that every condition is safe or profitable
in future. Four non-bull groups lack the required independent-week coverage in at
least one era, and every group-mean 99.1667% interval includes zero.

Plan steps **1-5 are complete**: save, freeze, reconcile, diagnose, apply the screen.
Steps **6-8 are not triggered** because there is no qualifying gate to freeze,
compare with reduced exposure, or replay in MT5. Step 9 needs a surviving rule and
future observations. The strategy remains unchanged. No new filtered strategy or
hedge has been backtested in this study.

## What the diagnosis tells us

- **Bearish daily conditions are not uniformly unfavorable.** In 2020-September
  2026, bear/normal trades contributed $3,926 and bear/elevated trades $480.
  These are subsets of the baseline, not the result of an executable filtering EA.
- **Dollar risk changes substantially.** Mean planned risk per contract was $21.72
  in 2016-19 and $78.95 recently. Within the recent period it ranged from $66.99
  (bull/normal) to $128.65 (neutral/elevated). Elevated volatility does not uniformly
  remove the edge: neutral/elevated is profitable, though its dollar swings are large.
- **Costs explain the arithmetic gap between gross and net R.** The whole baseline
  earned +0.0807 / +0.0715 gross R per trade across the two eras; mean commission was
  0.0951 / 0.0239 R, leaving -0.0143 / +0.0476 net R. This is a measured cost/risk
  difference, not evidence that a volatility filter solves it.
- **R and dollars can disagree.** Earlier bull/normal earned -0.0396 average net R
  but +$1,971 at one contract. Dollar results weight each trade by its stop risk;
  average R gives each trade equal weight. A negative average R alone does not
  justify dropping a positive-dollar group from this fixed-contract baseline.
- **Two recent groups are fragile after costs.** Neutral/normal earned $223 and
  bear/elevated $480. An extra assumed $1 per trade makes them -$222 and -$346.
  Neither establishes a repeatable loss at the frozen base cost. Cost allowances
  are assumptions; measured execution costs would be needed for a cost-aware gate.

The first study does not support switching off RTL solely because the daily market
is bearish or volatility is elevated. The separate cost/risk and intraday-choppiness
hypotheses remain in the saved plan; this result does not validate them.

## Definitions and data boundary

Daily trend uses the previous completed close, SMA50 and SMA200. Volatility is the
previous session's 20-return sample standard deviation, ranked against 252 earlier
volatility observations. Above the trailing 75th percentile is elevated; otherwise
normal. All labels are known at the actual buy-stop submission time. The 70th/80th
percentiles and removal of contract-switch returns were fixed sensitivities.

The 25,833-row full ledger reconciles to MT5 orders/deals. The primary study contains
16,668 trades: 6,167 earlier and 10,501 recent. Pre-2016 provides warmup only. The
last source session, 2026-10-01, ends at 02:59 and has a forced `end of test` exit;
its one trade (+$135 gross, +$133.95 net) is excluded before group analysis.
Including it reconciles to the previously published recent baseline: 10,502 trades,
$38,533.90 net. The main recent figures here are $38,399.95 through September 30.

![RTL group returns and initial dollar risk](../../../Reports/rtl_market_regimes_20261023/regime_diagnosis.png)

## 2016-19 primary groups

| Group | Trades | Net $ | PF | Gross R/trade | Net R/trade | Mean initial risk $ |
|---|---|---|---|---|---|---|
| Bull / normal | 3,868 | 1,971 | 1.055 | +0.071 | -0.040 | 18 |
| Bull / elevated | 908 | 530 | 1.039 | +0.071 | +0.003 | 30 |
| Neutral / normal | 422 | 539 | 1.130 | +0.103 | +0.012 | 19 |
| Neutral / elevated | 334 | 935 | 1.141 | +0.137 | +0.087 | 38 |
| Bear / normal | 286 | 122 | 1.036 | +0.070 | -0.004 | 22 |
| Bear / elevated | 349 | 320 | 1.053 | +0.138 | +0.085 | 33 |
| All RTL | 6,167 | 4,417 | 1.064 | +0.081 | -0.014 | 22 |

## 2020-26 primary groups

| Group | Trades | Net $ | PF | Gross R/trade | Net R/trade | Mean initial risk $ |
|---|---|---|---|---|---|---|
| Bull / normal | 6,343 | 17,273 | 1.080 | +0.069 | +0.041 | 67 |
| Bull / elevated | 1,572 | 8,785 | 1.109 | +0.068 | +0.050 | 102 |
| Neutral / normal | 445 | 223 | 1.010 | +0.076 | +0.056 | 88 |
| Neutral / elevated | 564 | 7,711 | 1.212 | +0.108 | +0.094 | 129 |
| Bear / normal | 751 | 3,926 | 1.145 | +0.108 | +0.085 | 72 |
| Bear / elevated | 826 | 480 | 1.011 | +0.037 | +0.020 | 94 |
| All RTL | 10,501 | 38,400 | 1.090 | +0.072 | +0.048 | 79 |

## Uncertainty (four-week moving blocks)

Intervals below are exploratory, two-sided and in R/trade. The 99.1667% interval accounts for the six groups within each era.

| Era | Group | Mean net R: 95% | Mean net R: 99.1667% | R vs others | Difference: 95% |
|---|---|---|---|---|---|
| 2016-19 | bull / normal | [-0.082, +0.002] | [-0.096, +0.014] | -0.068 | [-0.147, +0.010] |
| 2016-19 | bull / elevated | [-0.064, +0.061] | [-0.094, +0.080] | +0.020 | [-0.058, +0.092] |
| 2016-19 | neutral / normal | [-0.132, +0.193] | [-0.167, +0.258] | +0.028 | [-0.116, +0.209] |
| 2016-19 | neutral / elevated | [-0.070, +0.351] | [-0.124, +0.561] | +0.107 | [-0.054, +0.376] |
| 2016-19 | bear / normal | [-0.273, +0.234] | [-0.363, +0.358] | +0.011 | [-0.254, +0.242] |
| 2016-19 | bear / elevated | [-0.045, +0.249] | [-0.104, +0.308] | +0.105 | [-0.026, +0.266] |
| 2020-26 | bull / normal | [+0.006, +0.078] | [-0.006, +0.090] | -0.016 | [-0.065, +0.034] |
| 2020-26 | bull / elevated | [-0.008, +0.107] | [-0.029, +0.128] | +0.003 | [-0.060, +0.067] |
| 2020-26 | neutral / normal | [-0.030, +0.180] | [-0.070, +0.254] | +0.009 | [-0.078, +0.135] |
| 2020-26 | neutral / elevated | [-0.012, +0.194] | [-0.061, +0.240] | +0.049 | [-0.060, +0.152] |
| 2020-26 | bear / normal | [+0.012, +0.186] | [-0.020, +0.243] | +0.041 | [-0.038, +0.144] |
| 2020-26 | bear / elevated | [-0.034, +0.083] | [-0.058, +0.117] | -0.030 | [-0.092, +0.038] |

## Dollar risk and daily-close outcomes

| Era | Group | Mean risk $ | Median risk $ | Mean commission R | Worst day $ | Worst week $ | Daily-close DD $ | Max DD duration days |
|---|---|---|---|---|---|---|---|---|
| 2016-19 | bull / normal | 18 | 12 | 0.111 | -243 | -438 | 1,062 | 832 |
| 2016-19 | bull / elevated | 30 | 20 | 0.068 | -438 | -475 | 1,057 | 673 |
| 2016-19 | neutral / normal | 19 | 14 | 0.091 | -153 | -175 | 376 | 1169 |
| 2016-19 | neutral / elevated | 38 | 28 | 0.050 | -454 | -658 | 1,200 | 821 |
| 2016-19 | bear / normal | 22 | 18 | 0.075 | -184 | -219 | 692 | 1092 |
| 2016-19 | bear / elevated | 33 | 24 | 0.053 | -325 | -570 | 1,171 | 1016 |
| 2016-19 | all | 22 | 15 | 0.095 | -454 | -788 | 2,143 | 906 |
| 2020-26 | bull / normal | 67 | 48 | 0.028 | -1,221 | -1,501 | 5,428 | 493 |
| 2020-26 | bull / elevated | 102 | 77 | 0.018 | -1,671 | -1,883 | 3,328 | 1647 |
| 2020-26 | neutral / normal | 88 | 67 | 0.020 | -674 | -674 | 2,995 | 1325 |
| 2020-26 | neutral / elevated | 129 | 93 | 0.014 | -2,218 | -2,777 | 3,580 | 862 |
| 2020-26 | bear / normal | 72 | 56 | 0.023 | -737 | -929 | 1,243 | 97 |
| 2020-26 | bear / elevated | 94 | 75 | 0.018 | -896 | -1,185 | 3,652 | 1640 |
| 2020-26 | all | 79 | 58 | 0.024 | -2,218 | -2,777 | 5,781 | 283 |

Subset drawdowns do not add to portfolio drawdown; daily-close figures exclude intratrade equity excursions.

## Fixed cost allowances

| Era | Group | Net at $1.05 | Net at $2.05 | Net at $3.05 |
|---|---|---|---|---|
| 2016-19 | bull / normal | 1,971 | -1,897 | -5,765 |
| 2016-19 | bull / elevated | 530 | -378 | -1,286 |
| 2016-19 | neutral / normal | 539 | 117 | -305 |
| 2016-19 | neutral / elevated | 935 | 601 | 267 |
| 2016-19 | bear / normal | 122 | -164 | -450 |
| 2016-19 | bear / elevated | 320 | -29 | -378 |
| 2016-19 | all | 4,417 | -1,750 | -7,917 |
| 2020-26 | bull / normal | 17,273 | 10,930 | 4,587 |
| 2020-26 | bull / elevated | 8,785 | 7,213 | 5,641 |
| 2020-26 | neutral / normal | 223 | -222 | -667 |
| 2020-26 | neutral / elevated | 7,711 | 7,147 | 6,583 |
| 2020-26 | bear / normal | 3,926 | 3,175 | 2,424 |
| 2020-26 | bear / elevated | 480 | -346 | -1,172 |
| 2020-26 | all | 38,400 | 27,899 | 17,398 |

Extra allowances are sensitivity assumptions, not observed execution costs.

## Independent observations and fixed screening result

| Group | Earlier active weeks | Recent active weeks | Qualifies |
|---|---:|---:|---|
| Bull / normal | 139 | 227 | No |
| Bull / elevated | 39 | 66 | No |
| Neutral / normal | 22 | 22 | No |
| Neutral / elevated | 16 | 25 | No |
| Bear / normal | 14 | 27 | No |
| Bear / elevated | 16 | 30 | No |

Every group fails the negative-dollar-and-R requirement. Both bull groups have
enough active weeks; each other group fails the 30-week requirement in at least
one era. No group is below its complement with a 95% interval wholly below zero.
Sparse bootstrap draws with no group trades were excluded and counted: earlier
neutral/normal 1, neutral/elevated 13, bear/normal 11, bear/elevated 9 out of
10,000; recently bear/normal 1 and bear/elevated 1. Other primary groups have none.

## Annual net dollars (descriptive)

| Year | Bull normal | Bull elevated | Neutral normal | Neutral elevated | Bear normal | Bear elevated | All RTL |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2016 | -803 | -81 | -261 | 627 | -441 | -13 | -972 |
| 2017 | 340 | 422 | 0 | 0 | 0 | 0 | 761 |
| 2018 | 539 | 61 | 0 | 309 | -219 | -417 | 274 |
| 2019 | 1,895 | 128 | 800 | 0 | 782 | 750 | 4,354 |
| 2020 | 3,477 | -1,287 | 118 | 1,094 | 0 | 0 | 3,402 |
| 2021 | 527 | -216 | 0 | 0 | 0 | 0 | 311 |
| 2022 | -265 | -294 | 75 | 2,872 | 1,934 | -639 | 3,683 |
| 2023 | 1,972 | 0 | 698 | 0 | 1,992 | 0 | 4,661 |
| 2024 | 4,262 | 4,429 | 0 | 971 | 0 | 0 | 9,662 |
| 2025 | 2,659 | 2,555 | -1,787 | 2,876 | 0 | 1,119 | 7,423 |
| 2026 partial | 4,642 | 3,598 | 1,120 | -101 | 0 | 0 | 9,259 |

## Sensitivities and limitations

The 70th-percentile sensitivity relabels 183 / 381 trades (earlier/recent); the
80th relabels 215 / 383. Omitting contract-switch returns changes 42 / 43 trades
across seven session labels in each era. No sensitivity produces a group with
negative dollars and mean net R in both eras. Small dollar totals do change sign:
recent bear/elevated is -$260 at the 80th percentile; recent neutral/normal is
-$96 when switch-date returns are omitted. This fragility argues against precise
cutoffs, rather than supplying a replacement winner.

All tables are from the original strategy's ledger. They do not model orders newly
freed by skipping trades. Balance and daily-close drawdowns omit intratrade equity
excursions. Group drawdown durations include inactive calendar periods; they are
not continuous time in market. The raw continuous trend series still contains
roll gaps; the volatility sensitivity does not repair or validate that trend series.
Historical data have been repeatedly examined. The fixed group family, clustered
intervals and sensitivities reduce some research risks but supply no untouched
validation. One-minute OHLC and unmeasured slippage retain their existing limitations.

## Verification and reproducibility

- All 25,833 raw trades match MT5 order/deal timestamps, profits and planned risks;
  submission precedes entry and there are no cross-date orders/positions or overlaps.
- Independent reconstruction uses original minute closes, saved M30/daily closes,
  literal past-array calculations and a separate HTML parser. Every daily label,
  group assignment, annual/sensitivity summary and candidate decision agrees.
- All 10,000 paired four-week bootstrap draws per era were independently rebuilt
  using week multiplicities; interval bounds agree. Source and output hashes pass.
- The 6,167-trade earlier cap0 run and the 10,502-trade inclusive extended cap0 run
  match exactly on trade times, profit, risk, red-run, location and excursions.
- **16 tests pass**, covering future/current-price perturbations, threshold exclusion,
  warmup, ties, roll gaps, missing sessions, order matching/timing, planned versus
  filled risk, zero-PnL calendar days, and exclusion of partial 2026 from annual gates.
- A separate read-only method review found no material defect. The frozen protocol
  SHA256 remains `c3e8d6035ae712cb0cbf5da666f87d2f4ace29e6722fb314591c7d28464b32fa`.

```powershell
.\venv\Scripts\python.exe python\analyze_rtl_market_regimes.py
.\venv\Scripts\python.exe -m unittest discover -s python -p test_rtl_market_regimes.py -v
.\venv\Scripts\python.exe python\verify_rtl_market_regimes.py
.\venv\Scripts\python.exe python\report_rtl_market_regimes.py
```

Implementation: [analysis](../../../python/analyze_rtl_market_regimes.py),
[independent verifier](../../../python/verify_rtl_market_regimes.py),
[tests](../../../python/test_rtl_market_regimes.py), [renderer](../../../python/report_rtl_market_regimes.py).
Generated evidence is in `Reports/rtl_market_regimes_20261023/`: daily features,
trade attribution, summaries, yearly/sensitivity tables, daily PnL, candidate gates,
source audit, provenance, independent verification, figure and report-artifact hashes.
