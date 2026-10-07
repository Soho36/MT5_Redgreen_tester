# Q17: falling-resistance candidates traded alone

2026-10-04 · [Frozen protocol](PROTOCOL.md) ·
[Analysis](../../../../../python/analyze_resistance_standalone.py) · [EA gate](../../../../../mt5/experts/resistance_gate.mqh) ·
[Gate check](../../../../../python/verify_resistance_gate.py) ·
Run folder: `Reports/trendlines/resistance_standalone_20261004/`

## Answer

**Under the frozen reading rule, the edge does not survive its own
execution.** Traded alone, the candidate rule is profitable in both periods,
with PF 1.24 versus about 1.11 for the full baseline and a smaller drawdown.
Per unit of risk, though, it is no better than the baseline: mean net R is
+0.039 / +0.050 versus -0.004 / +0.060. It beats the baseline's mean R in only
4 of 11 years. The Q15 advantage (+0.093 / +0.110R) shrinks by half or more
once the candidate rule chooses its own trades. No filter, no sizing change.

| Period | Trades | Net $ | PF | Mean net R | Median R | Win % | Closed-trade DD $ |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2016-19 stand-alone | 669 | +1,748 | 1.242 | +0.039 | -1.024 | 43.3 | 453 |
| 2016-19 Q15 attribution | 412 | +1,485 | 1.325 | +0.093 | -1.013 | 45.4 | 352 |
| 2016-19 baseline (all signals) | 5,697 | +6,485 | 1.106 | -0.004 | -1.024 | 43.4 | 1,435 |
| 2020-26 stand-alone | 1,001 | +8,474 | 1.238 | +0.050 | -1.007 | 42.2 | 2,081 |
| 2020-26 Q15 attribution | 693 | +8,270 | 1.332 | +0.110 | -1.006 | 44.0 | 1,485 |
| 2020-26 baseline (all signals) | 9,271 | +37,981 | 1.107 | +0.060 | -1.007 | 43.0 | 4,847 |

**Reading rule (frozen):**

| Condition | Result |
|---|---|
| PF > 1, both periods | pass (1.242 / 1.238) |
| Mean R > 0, both periods | pass (+0.039 / +0.050) |
| Mean R > baseline, both periods | **fail recently** (+0.050 vs +0.060) |
| Mean R > baseline in >= 7 of 11 years | **fail (4 of 11)** |

The week-block bootstrap (5,000 resamples) agrees on the shape. PF stays above
1 (95% intervals [1.008, 1.534] and [1.070, 1.444]), but the mean-R intervals
include zero ([-0.064, +0.153] and [-0.025, +0.127]).

## Why the edge shrank: the freed trades

Execution matches the baseline exactly. All 405 / 678 candidate trades that
also traded in the baseline have **identical entry time, exit time and net**.
The one-minute OHLC fills are the same; nothing about execution changed.

What changed is the set of trades. Without other signals occupying the slot,
the candidate rule takes trades the baseline never could. They happened while
another RTL position or order was active. Of the 669 / 1,001 stand-alone trades,
405 / 678 are shared with the Q15 attribution:

| Period | Subset | Trades | Net $ | PF | Mean R |
|---|---|---:|---:|---:|---:|
| 2016-19 | **Freed** (not tradable in the baseline) | 264 | +218 | 1.080 | -0.051 |
| 2016-19 | Q15 trades displaced by a freed trade | 7 | -45 | 0.445 | -0.205 |
| 2020-26 | **Freed** | 323 | +89 | 1.008 | -0.075 |
| 2020-26 | Q15 trades displaced | 15 | -115 | 0.747 | +0.094 |

The freed trades are about 40% of the stand-alone run and are roughly
break-even. Q15's attribution described only the candidates the baseline
happened to reach, and that subset looked better than the rule as a whole.
This is exactly why the user asked for a stand-alone run.

## Year by year

| Year | Trades | Net $ | PF | Mean R | Baseline mean R | Beats baseline |
|---|---:|---:|---:|---:|---:|---|
| 2016 | 191 | -60 | 0.964 | -0.213 | -0.115 | no |
| 2017 | 149 | +135 | 1.161 | +0.154 | -0.012 | yes |
| 2018 | 163 | +1,204 | 1.468 | +0.208 | +0.036 | yes |
| 2019 | 166 | +468 | 1.220 | +0.061 | +0.079 | no |
| 2020 | 167 | +732 | 1.139 | +0.068 | +0.081 | no |
| 2021 | 161 | -1,002 | 0.813 | -0.073 | +0.048 | no |
| 2022 | 160 | +2,686 | 1.458 | +0.111 | +0.043 | yes |
| 2023 | 166 | +773 | 1.202 | -0.001 | +0.057 | no |
| 2024 | 150 | -611 | 0.896 | -0.036 | +0.082 | no |
| 2025 | 125 | +1,081 | 1.190 | +0.032 | +0.034 | no |
| 2026 partial | 72 | +4,815 | 2.296 | +0.480 | +0.088 | yes |

Partial 2026 supplies $4,815 of the recent $8,474. Without it (a post-hoc
check), 2020-2025 stand-alone is PF 1.115, mean R +0.017 over 929 trades.
That is profitable, but below the baseline's per-risk return.

## Secondary label: entry below the line (not a decision basis)

| Period | Entry below line: trades / PF / mean R | Entry at or above line: trades / PF / mean R |
|---|---|---|
| 2016-19 | 400 / 1.230 / +0.039 | 269 / 1.261 / +0.039 |
| 2020-26 | 585 / 1.404 / +0.100 | 416 / 1.033 / -0.019 |

Traded alone, the narrow version shows no advantage in 2016-19, so the Q15
split does not hold up in both periods either.

## Context and caveats

- **PF and R disagree** in this comparison: PF is in dollars, mean R is per
  unit of risk. The protocol fixed mean R as the decisive measure, as in
  every earlier study. Dollar PF alone would have flattered the rule.
- **Pre-2016 trades are negative** (847 trades, PF 0.75, mean R -0.23). Those
  years had different market hours and are not a reference period; this is
  context only.
- **Generated-tick execution was not run**, as agreed; it would likely reduce
  every figure, as it did for the baseline.

## Verification

- The EA gate reproduced all 52,070 Q15 classifications in a classify-only
  run before trading.
- In the trading run, every one of the 2,517 trades is a gate-approved
  resistance test (5,923 such signals over the full history). Gate, export,
  cancel and orphan errors are zero, and no trade crosses a session.
- The ledger total matches MT5's net profit ($11,526 gross of modelled
  costs, full history).
- Shared trades are identical to the baseline.
- The EA and protocol hashes were checked against the frozen manifest.
  Outputs: `summary.json`, `yearly.csv`, `decision.json`, `audit.json`,
  `standalone_trades.csv`, `provenance.json`, the MT5 HTML report and logs.

## What this means

The falling-resistance study follows the earlier level studies: a real-looking
attribution difference that does not become a better strategy when traded on
its own rules. Q15 and Q16 remain valid descriptions of which baseline fills did
better. They do not justify a filter, a stand-alone strategy or larger size on
these signals. Following the frozen rule, no thresholds are tuned to rescue it.
