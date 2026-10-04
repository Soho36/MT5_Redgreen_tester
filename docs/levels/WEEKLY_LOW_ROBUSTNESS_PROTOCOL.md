# Q13: concentration of the previous-week-low result

Specified 2026-10-04 before computing this follow-up. Q12 and its yearly results
are already known. This is an exploratory robustness audit of the same 276
contact fills, not new evidence or a search for another entry filter.

## Fixed population and event definition

Use Q12's previous-week-low exact contact: red signal low <= known previous
calendar-week low <= signal high, regardless of prior breaks or open/close side.
Retain the original RTL exit, costs, red-run/session rules, period boundaries,
and every-other-signal complement. Reproduce 101 / 175 contact fills and the
existing aggregates before any new calculations. Do not alter historical studies.

One **weekly-level event** is the previous source calendar week plus contract,
active during the immediately following calendar week, in the established symbol
clock. Repeated prices in different weeks are different events; multiple trades
at the same week's level are one cluster. Derive identity from source timestamps
and the roll ledger's contract ID, never from rounded price. Report unique events
with potential contact signals, with fills, fills per event, and repeat-trade share.
An event is a cluster, not proof of statistical independence: neighbouring weeks
can share a market regime. No arbitrary intraday episode-gap threshold is added.

## Diagnostics fixed before running

Report earlier/recent periods separately; pooled results are supplementary.

1. Yearly contact/rest counts, net dollars, PF, mean/median R and mean-R difference;
   distinct filled weekly events and R contribution. 2026 is partial.
2. Event ledgers: signals, attempts, fills, net dollars, sum/mean R, and positive
   event fractions. Give both trade-weighted and equal-event-weighted mean R.
   As additional context compare each filled event's mean R with non-contact
   trades in its same active calendar week (report missing comparators).
3. Concentration: contribution of the largest 1/5/10/20 winning trades and largest
   1/3/5/10 weekly events, ranking separately by net dollars and sum R. Report
   their share of gross positive contributions as well as total net (net shares
   can exceed 100%). Express trade/event excess R relative to the fixed period's
   every-other mean R; this arithmetic benchmark is not causal extra profit.
4. Remove the top 1/5/10/20 contact trades by each ranking and recompute PF/mean-R
   differences against the unchanged complement. This is an intentionally
   asymmetric fragility stress, not a fair hypothesis test or tradable rule.
   Also report symmetric 5% and 10% per-tail trimmed mean R for both groups.
5. Leave one year out of both candidate and complement, within each period and
   pooled. Separately leave each contact calendar week out of both groups;
   report sign survival and ranges. Do not select a year/week to exclude in trading.
6. Paired calendar-week bootstrap, 5,000 resamples, seed 20261004, all weeks
   including zero-contact weeks retained; report descriptive 95% intervals for
   PF and mean-R differences. Weekly clusters address within-week repetition,
   not dependence across weeks; preserve Q12's monthly intervals as context.

All diagnostics are descriptive. No new pass/fail threshold, subgroup filter,
EA change, first-touch study or MAE/MFE optimization is introduced. Additional
independent observations cannot be manufactured by slicing this sample.

## Audit and deliverables

Verify all Q12 input and output hashes, reconstruct exact contact and weekly
identity from Q10's saved source metadata, verify that source weeks precede
signals, and reconcile event/year sums to the 276 contact trades and Q12 net/R.
Test event boundaries, trimming, cluster handling and deletion semantics.
Outputs: `Reports/levels/weekly_low_robustness_20261004/`.
Version code/tests, this protocol and `WEEKLY_LOW_ROBUSTNESS_RESULTS.md` in this
folder; raw generated reports stay Git-ignored. No new MT5 run is necessary.
