# Q23: green signals that break horizontal swing-low support (short mirror of Q18)

2026-10-07 · [Frozen protocol](SUPPORT_BREAKDOWN_PROTOCOL.md) (frozen `0d33caa`) ·
[Analysis](../../python/analyze_support_breakdown.py) · [EA entry](../../mt5/experts/short_mirror.mqh) ·
Outputs: `Reports/levels/support_breakdown_20261006/`

**Level source in this study:** confirmed M30 swing lows (lowest of 5 bars on
each side) in a rolling one-week window, merged within 0.5 x ATR; the level is
the lowest member (the frozen Q11 map, unchanged).

## Answer

**No. It fails stage 1, so there is no stand-alone run, and by the frozen
stopping rule short-side level research ends here.**

Green signals whose sell stop sits at an intact swing-low level approached
from above are a *better* short than every other green signal: the same
direction as Q18 for longs. But they barely break even (PF 0.992 in 2016-19,
1.038 in 2020-26), and the N = 3 sensitivity does not agree. The short mirror
baseline itself loses in every period, so being better than it is not enough.

| Period | Group | Potential signals | Fills | Net $ | PF | Mean net R | Win % |
|---|---|---:|---:|---:|---:|---:|---:|
| 2016-19 | **Breakdown test** | 2,514 | 543 | -54 | **0.992** | **-0.057** | 40.5 |
| 2016-19 | Every other green signal | 18,207 | 5,298 | -5,627 | 0.907 | -0.134 | 37.0 |
| 2016-19 | Mirror baseline, all | 20,721 | 5,841 | -5,682 | 0.916 | -0.127 | 37.3 |
| 2020-26 | **Breakdown test** | 4,156 | 941 | +1,763 | **1.038** | **+0.012** | 40.0 |
| 2020-26 | Every other green signal | 29,616 | 8,628 | -11,970 | 0.965 | -0.043 | 37.3 |
| 2020-26 | Mirror baseline, all | 33,772 | 9,569 | -10,206 | 0.974 | -0.038 | 37.6 |
| 2010-15 | Breakdown test | 3,710 | 895 | -2,002 | 0.712 | -0.320 | 33.3 |
| 2010-15 | Mirror baseline, all | 27,977 | 8,701 | -13,542 | 0.750 | -0.295 | 35.1 |

For comparison, the long side: RTL PF 1.106 / 1.107, Q18's breakout test
1.198 / 1.192.

**Stage-1 gate (frozen, Q18's):**

| Condition | One week, N = 5 (primary) | Two weeks, N = 5 | One week, N = 3 |
|---|---|---|---|
| >= 200 fills, both groups, both periods | pass | pass | pass |
| Candidate PF > 1, both periods | **fail** (0.992 / 1.038) | pass (1.157 / 1.052) | fail (0.960 / 0.972) |
| PF and avg R above every other, both periods | pass | pass | **fail** (2020-26 PF -0.002) |
| Avg R better in >= 7 of 11 years | pass (7) | pass (8) | fail (6) |
| Sensitivities point the same way | **fail** (N = 3) | | |

**Month-block intervals (candidate minus every other, 2,000 resamples):**

| | PF difference | Avg R difference |
|---|---|---|
| Primary, 2016-19 | +0.085 [-0.114, +0.318] | +0.077 [-0.035, +0.184] |
| Primary, 2020-26 | +0.073 [-0.074, +0.232] | +0.054 [-0.020, +0.130] |
| Two weeks, 2016-19 | +0.268 [+0.037, +0.585] | +0.160 [+0.056, +0.258] |
| Two weeks, 2020-26 | +0.089 [-0.057, +0.260] | +0.061 [-0.018, +0.140] |
| N = 3, 2016-19 | +0.051 [-0.106, +0.230] | +0.069 [-0.039, +0.174] |
| N = 3, 2020-26 | -0.002 [-0.133, +0.145] | +0.003 [-0.065, +0.071] |

## Reading it

- **The relative signal is real-looking but small, and the base is negative.**
  The candidate's advantage comes partly from how bad the rest is: green
  signals with no level contact lose most (PF 0.845 / 0.942). Shorting into
  the drift costs 0.127R / 0.038R per trade across all green signals; the
  level selection improves that by about 0.07R / 0.05R, which lifts the
  candidate only to around break-even.
- **The two-week window looks best** (it alone would pass the core rule, with
  the 2016-19 interval excluding zero). It was a pre-declared sensitivity, not
  the primary, and the frozen rule does not allow promoting it.
- **The strict break is not the better half.** Candidates whose low is at or
  below L (a fill trades through the level) have PF 0.971 / 0.941; those
  whose low stays just above L have 1.006 / 1.104. That mirrors Q18, where the
  steadier part was the candle pressing into the zone, not the strict break.
- **Concentrated recent dollars.** 2020-26 net is +$1,763, but 2023 alone is
  -$3,522 and 2024-2025 are +$4,676. The mean R is +0.012.
- **2010-2015 loses heavily** (PF 0.712), as Q18 did.

## Year by year (primary candidate vs every other green signal, avg net R)

| Year | Candidate fills | Candidate avg R | Other avg R | Candidate net $ | Better |
|---|---:|---:|---:|---:|---|
| 2016 | 161 | -0.153 | -0.176 | -23 | yes |
| 2017 | 110 | -0.102 | -0.278 | -2 | yes |
| 2018 | 137 | -0.034 | +0.002 | -268 | no |
| 2019 | 135 | +0.072 | -0.078 | +239 | yes |
| 2020 | 122 | -0.046 | -0.032 | -41 | no |
| 2021 | 145 | +0.057 | -0.026 | -315 | yes |
| 2022 | 179 | +0.025 | +0.060 | +1,229 | no |
| 2023 | 148 | -0.225 | -0.135 | -3,522 | no |
| 2024 | 133 | +0.168 | -0.080 | +1,626 | yes |
| 2025 | 142 | +0.076 | -0.024 | +3,049 | yes |
| 2026 partial | 72 | +0.053 | -0.079 | -264 | yes |

## Descriptive labels (primary candidate; not candidates)

Full table: `labels.csv`. Cells with PF > 1 in both periods: low 0-0.25 x A
above L (1.143 / 1.262), single-member levels (1.149 / 1.085), levels 21-50
bars old (1.026 / 1.338) and older than 50 bars (1.348 / 1.001). Bear regime is 0.942 / 1.266 (60 / 168 fills). All
post hoc, small, and closed by the stopping rule.

## Verification

- **Stage 0 (the mirror baseline run):** the EA diff against the RTL parent
  touches only the Q21 short-side lines and the entry tail; compiled with
  0 errors and 0 warnings.
  - All 60,216 logged attempts are census signals with the same green run and
    submission bar (59,969 placed, 247 refused because price had already gapped
    through the low).
  - All 24,111 trades come from logged attempts and are shorts, filled at or
    below the signal low, with stop = signal high, planned R = signal range
    and RiskReward 1.0.
  - One position at a time; every trade exits its session; MT5 trade count and
    net match the ledger; 0 close, export or cancel errors.
- **Census mirror:** unit tests for green-run counting, doji and red resets,
  zero range, the 01:00 / cutoff boundaries and the period split
  (`test_support_breakdown.py`).
- **Classifier:** the frozen Q11 code unchanged (its own tests pass).
  Independent re-derivation of 1,440 sampled signals on raw lows with plain
  loops (`verify_level_visit.direct`): 0 mismatches.
- Partitions reconcile with the stage-0 ledger in all three settings.
- Hashes in `summary.json`.

## Limits

- Attribution on the mirror baseline's own fills; no stand-alone run (stage 1
  failed).
- One-minute OHLC with the tester's one-tick spread.
- All data had been examined before. The stopping rule closes short-side level
  research; reopening it needs a new external reason agreed with the user.
