# Q18: red signals that break horizontal swing-high resistance

2026-10-04 · [Frozen protocol](BREAKOUT_PROTOCOL.md) ·
Stage 1: [analysis](../../python/analyze_breakout.py), [independent check](../../python/verify_breakout.py) ·
Stage 2: [EA gate](../../mt5/experts/level_gate.mqh), [gate check](../../python/verify_breakout_gate.py),
[analysis](../../python/analyze_breakout_standalone.py) ·
Outputs: `Reports/levels/breakout_20261004/`, `Reports/levels/breakout_standalone_20261004/`

**Level source in this study:** confirmed M30 swing highs (highest of 5 bars on
each side) whose pivot is in a rolling one-week window (current session plus 5
previous sessions), merged within 0.5 x ATR; the level is the highest member.

## Answer

**Yes, it passes both frozen stages. It is the first level or line
definition in Q6-Q18 to do so.**

- **Stage 1 (attribution):** red signals whose buy stop sits at an intact
  swing-high level approached from below beat every other signal in both
  periods. Both sensitivities agree.
- **Stage 2 (traded alone):** in its own MT5 run, the candidate-only rule keeps
  the advantage and passes the Q17 reading rule:
  - mean net R +0.062 / +0.110 versus the full baseline's -0.004 / +0.060;
  - PF 1.164 / 1.204;
  - better than the baseline in 8 of 11 years;
  - the recent mean-R interval excludes zero.

**What it is not yet.** It is not a confirmed strategy change. All data had
been seen before, the 2016-2019 evidence is weak, and the pre-2016 years go
the other way. Execution was modelled with one-minute OHLC only. Per the
frozen protocol, a pass adopts nothing by itself. The stopping rule is not
triggered.

## Stage 1: attribution on the baseline fills

One week, N = 5, original exit:

| Period | Group | Fills | Net $ | PF | Mean net R | Win % |
|---|---|---:|---:|---:|---:|---:|
| 2016-19 | **Breakout test** | 751 | +1,471 | **1.198** | **+0.049** | 43.0 |
| 2016-19 | Every other signal | 4,946 | +5,014 | 1.093 | -0.012 | 43.4 |
| 2020-26 | **Breakout test** | 1,181 | +8,265 | **1.192** | **+0.121** | 44.5 |
| 2020-26 | Every other signal | 8,090 | +29,716 | 1.095 | +0.051 | 42.8 |

**Gate.**

- Better in 8 of 11 years; both sensitivities pass on their own.
  - Two weeks: PF 1.202 / 1.228, R +0.042 / +0.134.
  - N = 3: PF 1.231 / 1.235, R +0.069 / +0.121.
- Monthly-block intervals for the primary all include zero: PF +0.105
  [-0.109, +0.347] / +0.097 [-0.106, +0.318]; mean R +0.061 [-0.041, +0.160] /
  +0.070 [-0.017, +0.153].
- **Broad contact** (context only, about 60% of signals) is worse than the
  rest earlier and better recently, so it fails.

**Other groups.** Broken-upward contacts are near the baseline: PF 1.008 /
1.144. Within them, true retests (low held above L - D) are PF 0.955 / 1.150,
so role reversal shows nothing distinctive.

## Stage 2: candidate-only EA, traded alone

**Construction and gate check.** The EA is built exactly as in Q17: the
baseline research EA plus [`level_gate.mqh`](../../mt5/experts/level_gate.mqh),
with non-candidates rejected like a MaxRedRun rejection.

- A classify-only run reproduced stage 1 on all **52,070** census signals,
  with 0 group mismatches.
- 8,174 / 8,174 candidates match.
- Identical level prices, latest-member times and member counts on all
  29,759 contacts.
- The EA compiled with 0 errors and 0 warnings.

| Period | Run | Trades | Net $ | PF | Mean net R | Win % | Closed DD $ |
|---|---|---:|---:|---:|---:|---:|---:|
| 2016-19 | **Breakout, stand-alone** | 1,083 | +1,742 | **1.164** | **+0.062** | 43.4 | 626 |
| 2016-19 | Stage-1 attribution | 751 | +1,471 | 1.198 | +0.049 | 43.0 | 519 |
| 2016-19 | Baseline, all signals | 5,697 | +6,485 | 1.106 | -0.004 | 43.4 | 1,435 |
| 2020-26 | **Breakout, stand-alone** | 1,685 | +12,030 | **1.204** | **+0.110** | 44.2 | 1,727 |
| 2020-26 | Stage-1 attribution | 1,181 | +8,265 | 1.192 | +0.121 | 44.5 | 1,812 |
| 2020-26 | Baseline, all signals | 9,271 | +37,981 | 1.107 | +0.060 | 43.0 | 4,847 |

**Frozen reading rule:** PF > 1 (pass, both periods); mean R > 0 (pass,
both); mean R > baseline (pass, +0.062 vs -0.004 and +0.110 vs +0.060); mean
R above the baseline in >= 7 of 11 years (pass, 8 of 11). **Survives.**

**Week-block bootstrap** (5,000 resamples) of stand-alone mean R:

- 2016-19: [-0.013, +0.140]; PF [0.993, 1.365].
- 2020-26: **[+0.049, +0.174]**; PF [1.058, 1.371].

**Why this differs from Q17:**

- **Identical where shared.** All 734 / 1,151 trades shared with the baseline
  have identical entry, exit and net, so execution is unchanged.
- **The freed trades are not break-even.** The 349 / 534 trades the baseline
  could not take have PF 1.059 / 1.269 and mean R +0.071 / +0.109, about as
  good as the attributed ones. In Q17 they were break-even (R -0.05 / -0.08)
  and diluted the edge. Here the rule holds when it chooses its own trades.
- **Displaced trades are few:** 17 / 30 stage-1 trades are displaced by a
  freed trade.

## Year by year (stand-alone)

| Year | Trades | Net $ | PF | Mean R | Baseline mean R | Beats baseline |
|---|---:|---:|---:|---:|---:|---|
| 2016 | 256 | -344 | 0.858 | -0.082 | -0.115 | yes |
| 2017 | 279 | -106 | 0.936 | -0.019 | -0.012 | no |
| 2018 | 271 | +1,336 | 1.382 | +0.214 | +0.036 | yes |
| 2019 | 277 | +856 | 1.278 | +0.130 | +0.079 | yes |
| 2020 | 276 | +2,239 | 1.310 | +0.168 | +0.081 | yes |
| 2021 | 258 | +70 | 1.010 | -0.016 | +0.048 | no |
| 2022 | 240 | +2,784 | 1.279 | +0.170 | +0.043 | yes |
| 2023 | 257 | +1,881 | 1.281 | +0.180 | +0.057 | yes |
| 2024 | 242 | +1,237 | 1.153 | +0.084 | +0.082 | yes (marginal) |
| 2025 | 271 | +3,072 | 1.267 | +0.116 | +0.034 | yes |
| 2026 partial | 141 | +746 | 1.087 | +0.037 | +0.088 | no |

**Not carried by one year.** Partial 2026 is the weakest recent year. In a
post-hoc check, 2020-2025 alone gives PF 1.224 and mean R +0.117 over 1,544
trades, and 2023-2025 gives PF 1.236, +0.127. The largest trade is 16% of net
in each period.

## Labels (descriptive, not decision bases)

| Label | 2016-19 trades / PF / R | 2020-26 trades / PF / R |
|---|---|---|
| Entry below L (high under the level) | 669 / 1.243 / +0.121 | 1,038 / 1.231 / +0.111 |
| Entry at or above L (fill = strict break) | 414 / 1.040 / -0.033 | 647 / 1.167 / +0.109 |

The strict-break half is no better than the baseline in 2016-19. As in Q15,
the steadier part is the red candle that reaches the zone just under
resistance, so the buy stop sits just below the level. Fills there are
usually followed by the break. This is a description; the frozen candidate
is the whole zone.

## Caveats, all of which matter for any next step

1. **2016-2019 is weak.** Net is only +$1,742 over four years; 2016-2017 lose
   money (although 2016 still beats the baseline per unit of risk). The
   bootstrap interval for that period includes zero. Most of the evidence is
   2018 onward.
2. **The pre-2016 years go the other way.** In 2010-2015 the stand-alone run
   loses: 1,530 trades, PF 0.738, mean R -0.256. Its mean R is worse than the
   baseline's in 5 of 6 years, while the baseline itself also loses there (PF
   0.86, R -0.185). Those years had different market hours and are excluded
   from the reference periods by an earlier decision. Still, it is the only
   data outside 2016-2026, and it does not support the effect.
3. **Selection across many studies.** More than ten level and line
   definitions have been examined since Q6. Stages 1-2 limit, but do not remove, the chance of a
   lucky pass, and no untouched historical data remains.
4. **Execution model.** One-minute OHLC only. Buy stops at resistance are
   exactly where intrabar sequencing and slippage matter, and in the averaging study generated
   ticks cut the baseline's net from $37,981 to $19,435 (2020-26) and from
   $6,485 to $612 (2016-19). Not
   run here, as agreed.

## Verification

**Stage 1**

- Q10 and Q11 manifests were hash-verified, and partitions reconcile.
- 1,323 sampled signals were re-derived on raw highs, without the mirror or
  the study code: 0 mismatches.

**Stage 2**

- The MT5 gate matches stage 1 on all 52,070 signals.
- Every one of the 4,298 trades in the trading run (full history) is a
  gate-approved breakout test. Gate, export, cancel and orphan errors are zero,
  and no trade crosses a session.
- The ledger reconciles to MT5's net profit ($15,820.50 before modelled costs).
- EA and protocol hashes match the frozen manifest.

## EA for manual runs

[`mt5/experts/RR_r_MFE_buy-stop-entry_breakout.cs`](../../mt5/experts/RR_r_MFE_buy-stop-entry_breakout.cs)
is the exact stage-2 EA as one file: all includes are inlined and the input defaults equal the
tested run (GateMode=2; 0 gives the plain RTL baseline). It is generated by
[`python/build_breakout_ea.py`](../../python/build_breakout_ea.py) and works in the strategy tester only.
Verified 2026-10-05: a run with no tester inputs (defaults only) reproduced stage 2 trade by trade:
4,298 identical trades, $15,820.50, identical gate counts
(`Reports/levels/breakout_ea_check_20261005/`).

**RiskReward fix (2026-10-05).** In the research parent, the exit target came from the trend-RR
study inputs (BullRR/BearRR, 1.0 in neutral regimes), and `RiskReward` only named the CSVs, so changing
it did nothing (reported by the user). In this `.cs`, `RiskReward` now sets the target. Rechecked: the
defaults (RR 1) still reproduce stage 2 exactly; RR 2 gives different trades (4,087, $16,787.50 before
costs), as it should (`Reports/levels/breakout_ea_rrfix_20261005/`). The Q17/Q18 runs themselves were
at 1R as intended and are unaffected.

## Suggested next steps (each needs the user's decision, and its own protocol where noted)

1. **Execution model (user decision, 2026-10-05).** Generated ticks are not
   a realistic model of the user's execution either, so they are not a
   stopping criterion. A generated-tick run may be done for context only.
2. **Concentration audit** like Q16: level events, weeks and deletions.
   Cheap, and it would show whether 2018+ is broad-based.
3. **Forward evidence.** The only untouched data is the future. Run the
   stand-alone EA on a demo account, or log its signals live, before any money
   depends on it.
4. **Only then** decide how it could be used: stand-alone, combined with RTL,
   or a larger size on candidate signals. That needs its own protocol, as
   agreed after Q17.
