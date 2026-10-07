# Q16: is the Q15 falling-resistance result broadly distributed?

Specified 2026-10-04 at the user's request, before computing any Q16 diagnostic.
Q15 results, its yearly differences and its post-hoc caveats are already known.
This is a robustness audit of the same fills, using Q13's diagnostics unchanged
where they apply. It is not new evidence and not a search for a better subgroup.

## Fixed population

- Q15 primary candidate: one week, N = 5, group `resistance_test`. The
  complement is every other qualifying red signal.
- Original RTL exit, $1.05 cost, the same periods and the same complement.
- Reproduce 412 / 693 candidate fills and Q15's PF, net and mean R before any
  new calculation. Verify Q15's input and output hashes.
- **Primary = the whole frozen candidate group.** The narrow post-hoc version
  (entry below V, i.e. signal high < line value) is reported only as a
  secondary label, with a summary, yearly table and week bootstrap. It is never
  the basis for a decision.

## Clusters

- **Line event:** first-anchor time + second-anchor time (each bar of the
  continuous reference belongs to one contract, so this fixes the contract) of the line
  that classified the signal (Q15's nearest qualifying line). Several trades
  at the same line are one cluster; this is the counterpart of Q13's weekly
  level. A line can span calendar weeks.
- **Calendar week:** the Monday-based week of the signal, as in Q13. It is the
  resampling unit and the unit for week deletion and week concentration.

Neither cluster proves independence; neighbouring lines and weeks share regimes.

## Diagnostics (Q13 items, fixed before running)

Report earlier and recent periods separately, with pooled results as a
supplement. 2026 is partial.

1. **Yearly table.** For candidate and rest: counts, net $, PF, mean/median R
   and the mean-R difference, plus distinct filled line events and excess R.
2. **Line-event ledger.** Per line:
   - signals, attempts, fills, net $, sum and mean R;
   - positive-event fractions;
   - repeat-trade share and the maximum number of fills per line;
   - trade-weighted versus equal-event-weighted mean R;
   - a same-week comparator: each candidate trade's R minus the mean R of
     non-candidate trades in its calendar week, averaged per line (missing
     comparators reported).
3. **Concentration.**
   - The largest 1/5/10/20 winning trades, 1/3/5/10 line events and 1/3/5/10
     calendar weeks, ranked separately by net $ and by sum R.
   - Their share of gross positive contributions and of total net (net shares
     can exceed 100%).
   - Excess R relative to the period's every-other mean R (an arithmetic
     benchmark only).
4. **Fragility.**
   - Remove the top 1/5/10/20 candidate trades by each ranking, and the top
     1/3/5/10 line events and weeks. Recompute the PF and mean-R differences
     against the unchanged complement (an intentionally asymmetric stress).
   - Symmetric 5% and 10% per-tail trimmed mean R for both groups.
5. **Deletion.** Leave one year out of both groups, within each period and
   pooled. Separately, leave each candidate calendar week out of both groups.
   Report sign survival and ranges. Never select a period to exclude in trading.
6. **Bootstrap.** Paired calendar-week bootstrap: 5,000 resamples, seed
   20261004, all weeks retained including those without candidates. Report
   descriptive 95% intervals for the PF and mean-R differences. Q15's monthly
   intervals stay as context.

All diagnostics are descriptive. There is no pass/fail threshold here.

The decision already taken stands: the next step is a stand-alone,
candidate-only MT5 EA under its own protocol. This audit informs how that
run's results are read, and whether the user still wants it. It does not
change the frozen candidate definition.

## Audit and outputs

- Verify Q15 manifests (inputs and outputs). Map anchor bar indices to times
  from the M30 reference, and check that both anchors precede every signal.
- Reconcile line-event, week and year sums to all candidate trades and Q15
  totals. Unit tests cover line identity, deletion semantics, trimming and
  cluster resampling.
- Outputs: `Reports/trendlines/resistance_concentration_20261004/`. Results
  doc: `docs/setups/trendlines/downtrend-breakout-long/q16-resistance-concentration/RESULTS.md`. No MT5 run.
