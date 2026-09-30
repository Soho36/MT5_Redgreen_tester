# Exit thresholds: full MT5 comparison

Completed 2026-09-30 under the [frozen protocol](EXIT_THRESHOLD_PROTOCOL.md).
**Keep the existing 1R bar-close baseline for now. The 2R bar-close arm is a
research candidate, but its recent-period advantage is entangled with positions
carrying across dates when the intended flatten callback is absent.**

## Results

Twelve complete MT5 runs: five bar-close thresholds plus a fixed attached 1R TP,
each in 2015-2019 and 2020-2026 through July 13. MaxRedRun=3, MinLocation=0,
one contract, M30 on the same custom MNQ/NQ proxy history, M1 OHLC model.
Net figures subtract $1 per completed trade. DD below is **net closed-balance
drawdown**, not floating-equity drawdown. Both periods were previously examined.

| Exit rule | 2015-19 trades | Net $ | Net DD $ | Net/DD | Net avg R |
|---|---:|---:|---:|---:|---:|
| Bar close >=0.75R | 7,556 | 6,409 | 1,557.5 | 4.11 | -0.0180 |
| Bar close >=1.00R | 7,052 | 8,008 | 1,382.5 | 5.79 | -0.0065 |
| Bar close >=1.25R | 6,647 | 9,172 | 1,415.0 | 6.48 | +0.0105 |
| Bar close >=1.50R | 6,316 | 8,180 | 1,693.5 | 4.83 | +0.0126 |
| Bar close >=2.00R | 5,860 | 9,994 | 1,478.5 | 6.76 | +0.0215 |
| Fixed TP 1.00R | 7,739 | 2,934 | 1,666.5 | 1.76 | -0.0487 |

| Exit rule | 2020-26 trades | Net $ | Net DD $ | Net/DD | Net avg R |
|---|---:|---:|---:|---:|---:|
| Bar close >=0.75R | 9,773 | 29,178.5 | 5,050.5 | 5.78 | +0.0450 |
| Bar close >=1.00R | 9,147 | 37,291.0 | 5,134.5 | 7.26 | +0.0601 |
| Bar close >=1.25R | 8,616 | 35,875.5 | 5,270.5 | 6.81 | +0.0607 |
| Bar close >=1.50R | 8,202 | 38,983.5 | 5,797.5 | 6.72 | +0.0691 |
| Bar close >=2.00R | 7,569 | 39,958.0 | 5,234.5 | 7.63 | +0.0762 |
| Fixed TP 1.00R | 10,035 | 26,730.5 | 4,805.0 | 5.56 | +0.0305 |

2R increases net dollars 24.8% / 7.2%, while net balance DD increases 6.9% /
1.9%. Mean holding time increases from 113 to 164 minutes earlier and from
110 to 163 minutes recently. Trade counts fall by approximately 17% in both
periods. Average net R improves in both; it is not merely a dollar-PF effect.
However, native **gross floating-equity DD** increases from $1,252.5 to $1,531
earlier and $4,943.5 to $5,412.5 recently. Closed and open drawdown answer
different questions; the smaller closed-DD percentage is not the full risk story.

There is no uniformly better nearby setting: 1.25R loses net profit and raises
DD in the recent period; 1.5R raises profit modestly with substantially larger
DD. 2R is the upper boundary of this predefined grid, not a proven optimum.
Do not expand a fine grid merely because its endpoint looks strongest.

## Fixed TP now tested as a complete strategy

The fixed-TP control confirms the earlier [MFE estimate](EXIT_AND_DATA_REVIEW.md)
direction, including changed entry availability. It adds 687 / 888 trades but
reduces net profit by $5,074 / $10,560.50 versus the bar-close 1R controls.

The earlier same-entry estimates were $3,867 / $26,345; actual fixed-TP runs
produce $2,934 / $26,730.50. The estimate was informative, but cannot substitute
for a full run. The fixed TP is attached when the buy stop is placed; qualifying
bar-close exits are disabled, while the original SL and flatten logic remain.
The archived TP EA includes other historical mechanics, including breakeven,
so this control was derived from the current runband instead.

## Session handling materially affects the interpretation

The current EA checks exact equality with a **23:30 bar-open callback**.
It has no fallback if that callback does not occur. In each audited 1R/2R arm,
none of the entry dates of cross-date positions has a logged 23:30 flatten
callback. Some trades remain open for several days.

| Period / threshold | Cross-date trades | Net $ from cross-date trades | Net $ from same-date trades | Longest hold, days |
|---|---:|---:|---:|---:|
| 2015-19 / 1R | 63 | 869.0 | 7,139.0 | 5.08 |
| 2015-19 / 2R | 70 | 1,031.0 | 8,963.0 | 5.73 |
| 2020-26 / 1R | 71 | 1,962.5 | 35,328.5 | 3.22 |
| 2020-26 / 2R | 90 | 9,531.5 | 30,426.5 | 4.22 |

Recently, cross-date profit increases **$7,569**, while same-date profit falls
**$4,902**, leaving the overall **$2,667** gain. Thus the headline improvement
does not yet establish that 2R improves the intended intraday strategy.
This partitions native outcomes, not matched trades: deleting overnight rows
would not simulate an alternative flatten rule or its changed entry availability.

The issue appears in the unchanged baseline and is not introduced by the
experimental TP code. Cross-date entries concentrate in March and October/
November: 53 of 70 earlier and 62 of 90 recent 2R cases fall in those months.
For example, the recent 2R log shows callbacks at 00:00 and 00:30 around
2025-03-11/12 but no 23:30 flatten callback for the entry date. This makes the
actual tester session clock and DST-transition weeks worth checking alongside
short sessions. These observations do not yet distinguish history conversion,
symbol/tester session configuration, and missing source bars.

The intended synthetic clock reported by the user remains 01:00-23:59; the
available conversion script implements Chicago plus eight hours. The observed
tester behavior must be reconciled with that intent before changing the default.
Simply changing `==23:30` to `>=23:30` does not solve a day with no later tick,
and flattening next session still retains the overnight price gap. An early
close needs a time known in advance, not hindsight about the last available bar.

## Yearly stability

2R earns more in four of five earlier calendar years and four of seven recent
calendar years (2026 is partial). Recent differences in net dollars, 2R minus 1R:

| Exit year | Difference $ |
|---|---:|
| 2020 | +1,312.5 |
| 2021 | +1,474.5 |
| 2022 | -385.5 |
| 2023 | +125.5 |
| 2024 | -2,144.0 |
| 2025 | +4,778.5 |
| 2026 through July 13 | -2,494.5 |

The recent gain is not broad annual dominance; 2025 contributes more than the
aggregate improvement. Yearly net R and every arm's results are retained too.

## Why the previous project used 1R

The initial review traced inheritance through `PA_milky_simplified` and
`Eval_PA_optimal_path_milky`. The user then identified the actual decision in
`I:\PycharmProjects\Accounts_staggering`; its README and the earlier
`I:\PycharmProjects\Xgboost_RR_model\FORWARD_TESTING_PLAN.md` were inspected on
2026-09-30. None of these external projects was modified.

- `Accounts_staggering/README.md`, "Current decision summary (2026-08-14)" and
  "RR: keep it simple; two old rows were invalid", document the global RR=1
  operational choice. In its in-sample account simulation, 1R had the highest
  reported safety-net attainment (76%), no observed five-or-more-seat shocks,
  and the highest optimistic-mark median among the valid displayed settings.
  These are account-policy outcomes, not proof of a universal trade-level RR
  optimum or a zero future shock probability.
- The old 2R and 2.5R comparisons were invalid because the 16-17 export ended
  prematurely in 2022 and was omitted. Those rows establish neither superiority
  nor inferiority. Our complete all-hours runs supply new trade-level evidence
  for the current cap-3 setup, but do not retroactively repair that account study.
- `Xgboost_RR_model/FORWARD_TESTING_PLAN.md`, sections 12.3-12.4, documents a
  different earlier choice: fixed global RR=1.5 with cap 55%. It retained the
  predeclared control and more account-risk headroom than some more profitable
  alternatives. Per-window RR selection failed its risk-matched comparison.
  Evidence against fitting a different RR to each window does not establish
  that one particular global RR is always best. Here, "fixed RR" describes
  one common parameter; it must not be confused with our attached fixed-TP arm.

- `PA_milky_simplified/ASSUMPTIONS.md` explicitly says RR=1 was the exact tape
  pinned by the parent study so that the first comparison could be differenced
  against it. This documents an inherited comparability baseline; it does not
  establish an optimized exit threshold. The subsequent Accounts_staggering
  record above supplies the missing selection rationale.
- Its later synchronized `rr_curves` study already compares 13 settings from
  0.50 to 3.50. Across 23 overlapping twelve-month windows, RR1 averages $4,187
  net / $3,274.50 realized DD, versus RR2's $5,205.63 / $3,502.08 and RR2.5's
  $5,819.48 / $3,186.47. These are historical window means, not annual forecasts.
- Those studies use separate source-window tapes with Python routing, $1.05
  commission, and often account-survival/withdrawal objectives. They do not use
  this current all-hours cap-3 population, so they cannot replace these tests.
- The earlier project already recorded cross-date holds in its RR1000/session-
  close study. Its source audit also warns that the example EA is not a proven
  generator of every frozen CSV; do not infer exact old exit semantics solely
  from a filename or an RR label.

## Decision and next step

Preserve 1R as the operational research baseline. Keep 2R as a candidate and
retain the negative fixed-TP result. Prioritize reconciling the actual session
clock and missing flatten callbacks, then rerun **1R versus 2R only** under the
same explicitly intended session policy. Following the recovered historical
decision, including 1.5R as the earlier project's fixed control is also a
justified bounded comparison, not a reason to expand a fine grid.

Scope update from the user on 2026-09-30: this project evaluates the technical
trading strategy, with MT5 producing complete paths and Python analyzing them.
Apex/account-lifecycle testing is outside the current scope. The old survival
objective explains the historical choice of 1R but is not the current selection
criterion. Compare trading profit, drawdown, holding behavior, costs and parameter
stability. Keep session-close handling as a separate sensitivity rather than a
prerequisite to all further research. The subsequent [optimization review](RR_OPTIMIZATION_REVIEW.md)
records the user-requested wider grid and correction of its red-run inputs.

This is more informative now than a larger RR grid or a trailing-stop mechanism.
Do not combine time-of-day filtering with the session correction. Existing
historical results remain exploratory; the old per-window OOS evidence does not
turn this new global-RR comparison into an unseen validation.

## Verification and reproduction

- Experimental compile: 0 errors, 0 warnings. Current production source unchanged.
- Both 1R controls reproduce all original fields for 7,052 / 9,147 trades.
- All twelve runs reconcile trade counts, gross profit, gross closed-balance DD,
  deal times/prices/PnL, one-contract sizing and signal-range initial risk.
- All entries equal their signal highs. Fixed-TP fills reconcile to exactly 1R;
  order reasons also reconcile with tester TP/SL trigger logs.
- Every run has completed-test evidence. Logs contain inherited invalid-price
  pending-order rejections (66-73 earlier, 109-110 recent), with no unexplained
  error categories. These rejected orders are retained, not silently repaired.
- Configs, compiled source/binary, hashes, full tester/agent logs, HTML reports,
  trade/stats CSVs and machine-readable results are in
  `Reports/exit_thresholds_20260930/`. No MT5 terminal was already running when
  these tests started; live trading and remote/cloud agents were disabled.

```powershell
# Preparation regenerates the experimental source/configs, not test results.
.\venv\Scripts\python.exe python\prepare_exit_study.py
# Compile Reports/exit_thresholds_20260930/RTL_exit_comparison.mq5 with MetaEditor.
# Only when the AMP terminal is otherwise closed:
.\python\run_exit_study.ps1
.\venv\Scripts\python.exe python\analyze_exit_study.py
.\venv\Scripts\python.exe python\audit_exit_sessions.py
```

The runner skips jobs with completion markers. Optional `--plot` on the analysis
requires Matplotlib; numerical analysis needs only the existing NumPy dependency.
