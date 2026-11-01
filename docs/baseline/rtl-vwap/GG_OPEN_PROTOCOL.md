# GG signal open versus close at the orange VWAP cutoff

Plan recorded 2026-11-01 before calculating the new labels or outcomes. This is a
descriptive follow-up requested by the user, on already studied NQ history. It is
not a fresh confirmation test and has no pass/fail or adoption decision.

## Fixed comparison

Use the reconciled, independently verified GG baseline ledger from
`Reports/gg_vwap_20261030/trades_GG.csv` and the same frozen NQ features and session
calendar as the earlier GG study. Same one-contract sizing, $2/point and $1.05
per-trade cost. Analyze 2016-19, 2020 through September 2026, pooled 2016-September
2026; show 2010-15 separately as secondary history. Exclude October 2026.

The orange cutoff is signal-bar-close VWAP minus signal-bar-close A20, exactly as
in the earlier study. Change only the signal price used in the comparison:

- Baseline: keep every trade.
- Close rule: skip when signal close < cutoff (existing rule).
- Open rule: skip when signal open < cutoff (new rule).

Equality is kept. Keep unknown values under both rules, using the existing
availability/session/A20 conditions. The open rule is evaluated after the green
signal candle closes, not at its opening time. An opening-time VWAP/A20 comparison
would be a different experiment and is outside this study.

## Measures

Report retained trade count, net dollars, mean net R, win rate, profit factor,
daily-close drawdown and net/drawdown for each policy and era; annual rows; and
fixed exposure controls that scale all baseline daily P&L by each policy's retained
share of total planned initial risk (descriptive, fractional sizing, not executable
one-contract trading). Drawdown uses the original submission-session attribution
and full observed calendar, as in the earlier study.

Separate four groups: skipped by both; additionally skipped by open (open below,
close at/above cutoff); kept by both with known features; unknown and kept. Because
every GG candle is green, the close-skip group must be a subset of the open-skip
group. The incremental group's net is exactly the close-policy net minus the
open-policy net. Report its annual contribution, including 2026.

This is ledger omission: it retains original fills and exits of surviving baseline
trades. It does not replay newly available orders. The earlier GG close-filter
replay differed materially from ledger omission, so these results cannot be
represented as tradable strategy performance. No EA change, parameter sweep,
threshold optimization, or automatic follow-up replay.

## Checks and outputs

Hash protocol and all inputs before analysis; check source-audit output hashes and
frozen features/calendar hashes; check available-at <= submission and same-session
eligibility; match each signal's open/close/high/low to the frozen feature rows;
reproduce existing close labels and baseline/close summary counts, profit and DD;
check green candles, nesting, disjoint groups and profit decomposition.

Independently rejoin the frozen features to the baseline trades and recompute the
new masks, all summary metrics, annual groups and exposure controls in a separate
verifier. Save outputs and hashes under `Reports/gg_vwap_open_20261101/`; publish
`GG_OPEN_RESULTS.md` with a plot and update the research index/status/journal.
