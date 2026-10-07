# Q22: RTL long signals at or after a rising-line break

2026-10-06 · [Frozen protocol](PROTOCOL.md) (frozen `1112d71`) ·
[Analysis](../../../../../python/analyze_breakdown_rtl.py) · Outputs: `Reports/trendlines/breakdown_rtl_20261006/`

## Answer

**No gate passes; no filter and no new long.** The result points the opposite
way from the prior evidence. RTL buys on the red candle that breaks a rising
line (group A, the buy stop at its high) are **worse** than every other signal
in both periods, and clearly so in 2020-26. The "worse" (skip-filter) gate
fails only because the S1 sensitivity does not agree. Signals in the 10 bars
after a break (group B) are not different.

| Period | Group | Potential signals | Fills | Net $ | Net PF | Avg net R | Win % |
|---|---|---:|---:|---:|---:|---:|---:|
| 2016-19 | **A: signal candle breaks a line** | 850 | **210** | +30 | **1.010** | **-0.070** | 41.4 |
| 2016-19 | Every other than A | 18,774 | 5,487 | +6,456 | 1.111 | -0.002 | 43.4 |
| 2016-19 | B: break in the 10 bars before | 3,630 | 1,084 | +1,764 | 1.136 | -0.032 | 43.2 |
| 2016-19 | Every other than B | 15,994 | 4,613 | +4,721 | 1.097 | +0.002 | 43.4 |
| 2020-26 | **A** | 1,339 | **342** | -3,406 | **0.831** | **-0.069** | 39.5 |
| 2020-26 | Every other than A | 31,107 | 8,929 | +41,387 | 1.123 | +0.065 | 43.1 |
| 2020-26 | B | 5,557 | 1,669 | +5,019 | 1.071 | +0.047 | 42.5 |
| 2020-26 | Every other than B | 26,889 | 7,602 | +32,962 | 1.116 | +0.063 | 43.1 |

Partitions reconcile with the Q10 baseline (5,697 / 9,271 fills, +$6,485 /
+$37,981).

**Gate (frozen):**

| Condition | A "worse" | A "better" | B "worse" | B "better" |
|---|---|---|---|---|
| >= 200 fills, group and complement, both periods | pass | pass | pass | pass |
| Group PF > 1, both periods | - | **fail** (0.831) | - | pass |
| PF and avg R on the gate's side of the complement, both periods | pass | **fail** | **fail** | **fail** |
| Years on the gate's side (>= 7 of 11) | pass (7) | **fail** (4) | **fail** (6) | **fail** (5) |
| S1 agrees in both periods | **fail** | **fail** | **fail** | **fail** |

**Month-block intervals (group minus complement, 2,000 resamples):**

| | PF difference | Avg R difference |
|---|---|---|
| A, 2016-19 | -0.101 [-0.431, +0.393] | -0.069 [-0.241, +0.103] |
| A, 2020-26 | **-0.292 [-0.523, -0.009]** | **-0.134 [-0.239, -0.026]** |
| S1 A, 2016-19 | -0.031 [-0.378, +0.452] | -0.046 [-0.187, +0.109] |
| S1 A, 2020-26 | +0.009 [-0.267, +0.370] | -0.027 [-0.153, +0.105] |
| B, 2016-19 | +0.039 [-0.169, +0.298] | -0.034 [-0.134, +0.068] |
| B, 2020-26 | -0.045 [-0.194, +0.128] | -0.016 [-0.082, +0.053] |

## Reading it

- **Why S1 matters here.** With S1, a break needs a close more than 0.5 x A
  below the line. The S1 group A is mostly the same kind of candle (214 / 316
  fills) but is not worse in 2020-26 (PF 1.115 vs 1.106; avg R +0.034 vs
  +0.061). The weakness of group A therefore depends on the exact break
  definition. That is what the sensitivity is for, and the frozen rule says
  stop.
- **Size, for context only.** Dropping group A from the baseline would change
  attributed net by -$29 in 2016-19 and +$3,406 in 2020-26 (342 fewer trades).
  This is attribution, not a filtered run: a skipped signal frees the position
  for other trades, which Q17 showed can matter.
- **Q14's broken-contact group is not this group.** Q14's group was signals
  touching a line broken any time earlier by more than D (PF 1.084 / 1.265).
  Group A is the breaking candle itself.
- **Together with Q21:** after a red candle breaks a rising line, neither
  shorting its low (Q21) nor buying its high (group A) pays. The break bar is
  a poor place to trade in either direction.

## Year by year (group A vs every other signal, avg net R)

| Year | A fills | A avg R | Other avg R | A worse |
|---|---:|---:|---:|---|
| 2016 | 51 | +0.020 | -0.119 | no |
| 2017 | 49 | -0.089 | -0.009 | yes |
| 2018 | 54 | -0.255 | +0.048 | yes |
| 2019 | 56 | +0.042 | +0.080 | yes |
| 2020 | 46 | +0.153 | +0.079 | no |
| 2021 | 47 | +0.051 | +0.048 | no |
| 2022 | 53 | +0.032 | +0.044 | yes |
| 2023 | 51 | -0.415 | +0.074 | yes |
| 2024 | 61 | -0.018 | +0.087 | yes |
| 2025 | 57 | -0.269 | +0.047 | yes |
| 2026 partial | 27 | +0.110 | +0.087 | no |

## Descriptive labels (group A, primary; not candidates)

Full table: `labels.csv`. Small cells (3-129 trades). Because group A as a
whole is worse, most cells sit below the complement in both periods; the
weakest are breaks of **two or more lines** (PF 0.559 / 0.492, 15 / 34 fills),
bear-regime signals (0.590 / 0.571, 16 / 57) and morning signals before 10:00
(0.856 / 0.600, 51 / 102). Two cells have PF > 1.2 in both periods: break depth
0.5-1 x A (1.238 / 1.513, 52 / 94) and candle range 1.5-2.5 x A (1.298 / 1.257,
60 / 86). All post hoc; none is a lead under the frozen rule.

## Verification

- Q10 manifest verified (all input hashes); census totals 52,070 potential
  signals, 35,632 attempts, 14,968 fills reconciled per period.
- **Break events cross-checked against the verified Q21 classify-only logs**
  (EA = Python): number of lines broken at bar s equal on all 170,256 logged
  bars (rolls excluded), primary and S1; red-break status equal: 0 mismatches.
- Group assignment unit tests: A vs B, 10-bar window edges, same contract,
  start of history (`python/test_breakdown_rtl.py`).
- Hashes of the protocol, inputs, code and both break tables in `summary.json`.

## Limits

- Attribution of existing baseline fills, not a filtered or stand-alone run.
- One line definition (frozen Q14), one window (10 bars), one sensitivity.
  Nothing else is searched.
- All years had been examined before; one-minute OHLC execution limits remain.
