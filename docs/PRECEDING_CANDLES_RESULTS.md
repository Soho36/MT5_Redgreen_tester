# Preceding candles: interrupted declines and recovery after a new low

First diagnostic study completed 2026-09-30 under the
[fixed protocol](PRECEDING_CANDLES_PROTOCOL.md). See the
[remaining questions](RESEARCH_QUESTIONS.md).

**Decision: retain the research candidate MaxRedRun=3, MinLocation=0 without
adding either new filter.** There are interesting recent-period associations,
but neither question has a consistent actionable answer across periods.
The first Q1 test is a density proxy; it does not exhaust the small-green-body
interruption hypothesis.

## Data and verification

Actual MT5 runs with the optional runband `SnapshotBars=51` input: signal plus
50 preceding closed bars. Same MNQ M30 settings and 1-minute OHLC model as the
previous frozen-cap runs. Signals are snapshotted at order placement.

- 2015–2019: **7,052 trades**, gross $15,060, net $8,008 at modeled $1/trade.
- 2020–2026: **9,147 trades**, gross $46,438, net $37,291 at modeled $1/trade.
- Every original trade field matches the corresponding earlier cap-3 run;
  counts and gross PnL reconcile with MT5. All 16,199 snapshots are complete.
- Snapshot signal range, red-run count and timing checks passed. Six synthetic
  tests cover chronological order, equality, dojis, signal exclusion, window
  independence and missing history. MetaEditor: 0 errors, 0 warnings.
- Earlier data and recent data have both been viewed previously. These are
  exploratory diagnostics, not untouched out-of-sample tests.

## Q1: interrupted-decline proxy

Among N bars preceding the signal, flag a trade when both the red-bar share
and downward close-to-close share are at least 60%. The flag is evaluated
only within the actual cap-3 trade population. These thresholds were fixed
before the diagnostic run, not selected for the best result.

| N | 2015–2019 flagged n | Flagged net PF | Other net PF | 2020–2026 flagged n | Flagged net PF | Other net PF |
|---|---:|---:|---:|---:|---:|---:|
| 5 | 1,377 | 1.124 | 1.107 | 1,977 | 1.067 | 1.117 |
| 10 | 1,066 | 1.124 | 1.107 | 1,659 | 1.022 | 1.127 |
| 20 | 594 | 1.119 | 1.109 | 991 | 0.948 | 1.131 |
| 50 | 119 | 1.311 | 1.105 | 274 | 1.198 | 1.101 |

In the recent period, N=10–20 isolates lower average gross R as well as lower
PF. At N=20, the gross-R difference (flagged minus other) is -0.098R with a
descriptive monthly-block 95% interval [-0.174, -0.013]. The corresponding
2015–2019 difference is -0.001R, interval [-0.120, +0.112].

Even within the recent period the flagged N=20 group is not a stable loser:
net PF is 0.861 in 2020–2022 but 1.018 in 2023–2026. It remains weaker than
its complement, but that is different from being consistently unprofitable.
At N=50 the ranking changes and the flagged sample is much smaller.

**Conclusion:** worth remembering as a possible period-dependent effect,
not sufficient support for excluding this group. The existence of the recent
N=20 loss is not a license to select N=20 after examining all four horizons.

## Q2: did the signal recover the preceding low?

The signal must strictly break the minimum low of N preceding bars. A close
strictly above that old low is recovered; a close at or below it is unrecovered.
Signals without a breach form a separate control in the detailed tables.

| N | 2015–2019 recovered / unrecovered n | Recovered net PF | Unrecovered net PF | 2020–2026 recovered / unrecovered n | Recovered net PF | Unrecovered net PF |
|---|---:|---:|---:|---:|---:|---:|
| 5 | 939 / 1,377 | 1.026 | 1.152 | 1,367 / 1,671 | 1.191 | 0.995 |
| 10 | 720 / 901 | 1.074 | 1.184 | 958 / 1,100 | 1.153 | 0.963 |
| 20 | 493 / 609 | 0.993 | 1.238 | 640 / 738 | 1.265 | 0.940 |
| 50 | 244 / 278 | 1.065 | 1.332 | 304 / 343 | 1.291 | 0.878 |

The PF ranking reverses across periods at every N, including before commission.
However, average R does not reverse as cleanly: it slightly favors recovered
signals in 2015–2019 at N=5,10,20, with intervals spanning zero. PF weights
dollar gains/losses, while average R normalizes each trade's candle risk; these
are different questions and the table must not be read as universal evidence
that recovery helped or hurt every measure.

At N=20, the recovered-minus-unrecovered gross-R difference is +0.026R
[-0.127, +0.176] in 2015–2019 and +0.133R [-0.004, +0.260] in 2020–2026.
The recent N=50 difference is +0.209R [+0.043, +0.370], but this is one of
many exploratory comparisons, with only 647 breached-low trades.

**Conclusion:** a clearer recent-period PF pattern than Q1, but not consistent
enough across periods to adopt a recovery requirement. The appropriate next
step would be to understand the period/risk-size difference before adding a
filter, rather than simply choosing the recent best-looking horizon.

## What the N comparison established

N changes the population and the question, not just measurement smoothness.
For Q1, 50 bars selects rare sustained declines and changes the observed
ranking. For Q2, the directional PF pattern within each period persists from
5 to 50, but the two periods disagree. More bars do not automatically improve
the signal. There is no justified single best N from this study.

Intervals use 2,000 common-calendar-month resamples, seed 20260930; they are
descriptive, unadjusted for multiple testing, and depend on the block scheme.
The groups are conditional associations within filled cap-3 trades, not causal
effects or complete filtered strategies. No subset drawdown is presented as
the drawdown of a new EA.

## Reproduce and inspect

```powershell
.\venv\Scripts\python.exe -m unittest discover -s python -p "test_*.py" -v
.\venv\Scripts\python.exe python\analyze_preceding_candles.py Reports\preceding_candles_20260930
```

Artifacts in [Reports/preceding_candles_20260930](../Reports/preceding_candles_20260930/):
`train.ini`, `recent.ini`, the `.mq5`/`.ex5` and compiler log, original MT5
HTML reports and snapshot CSVs, `DIAGNOSTICS.md`, `diagnostics.json`,
`buckets.csv`, and `contrasts.csv`. Every share bin, no-breach control, year,
and fixed chronological subdivision is retained, including negative results.

To recollect: compile a `.mq5` copy of
`mt5/experts/RR_r_MFE_buy-stop-entry_runband.cs`, install it in the tester-only
`CodexBarResearch` folder referenced by the saved INIs, and run each INI with
the AMP terminal's `/config:` option while that terminal is otherwise closed.
The saved INIs disable live trading and remote/cloud agents and use unique
run tags. Normal runband exports remain unchanged with `SnapshotBars=0`.
