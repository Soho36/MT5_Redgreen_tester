# Q19: is the Q18 breakout result broadly distributed?

Specified 2026-10-05 at the user's request, before computing any Q19 diagnostic.
Q18's results, yearly figures and caveats are known. This is a descriptive
robustness audit using Q16's diagnostics ([protocol](../trendlines/RESISTANCE_CONCENTRATION_PROTOCOL.md))
unchanged where they apply. There is no pass/fail threshold, and it is not a
search for a better subgroup.

## Populations

1. **Primary: the stage-2 stand-alone trades.** This is the evidence that
   passed: 1,083 / 1,685 trades from the candidate-only EA. The comparator is
   the full baseline strategy (5,697 / 9,271 fills), as in the Q17/Q18 reading
   rule. The two sets share 734 / 1,151 identical trades, so they are not
   independent. Every comparison is descriptive.
2. **Secondary: the stage-1 attribution.** Q18 `breakout_test` fills (751 /
   1,181) versus every other signal in the baseline. This is the exact
   counterpart of Q16.

For both, reproduce Q18's counts, net, PF and mean R first; verify the Q18
stage-1 and stage-2 hashes. Original RTL exit, $1.05 cost, the usual periods
(2026 partial). The post-hoc "entry below L" version is reported as a secondary
label only (summary, yearly table, week bootstrap), never as a decision basis.

## Clusters

- **Level event:** level price L plus the time of its latest member pivot
  (the stage-2 gate log or the stage-1 map). Trades at the same level are
  one cluster. A level that gains a new member becomes a new event.
- **Calendar week:** the Monday-based week of the signal. It is the
  resampling, deletion and week-concentration unit.

Neither cluster proves independence.

## Diagnostics (Q16 items)

Per period, plus pooled as a supplement:

1. **Yearly table.** Counts, net, PF, mean and median R, and the mean-R
   difference; distinct level events and excess R.
2. **Level-event ledger.**
   - Fills per level, repeat-trade share and positive-event fractions.
   - Trade-weighted versus equal-event mean R.
   - A same-week comparator: candidate R minus the comparator's mean R in the
     same calendar week, averaged per level (missing comparators reported).
3. **Concentration.**
   - The largest 1/5/10/20 trades, 1/3/5/10 level events and 1/3/5/10 weeks,
     ranked by net $ and by sum R.
   - Their share of gross positive and of total net.
   - Excess R versus the comparator's mean.
4. **Fragility.**
   - Remove those top units from the candidate only and recompute the PF and
     mean-R differences (an adverse stress).
   - Symmetric 5% and 10% per-tail trims for both groups.
5. **Deletion.** Leave one year out of both groups; leave each candidate week
   out of both groups. Report sign survival and ranges.
6. **Bootstrap.** Paired calendar-week bootstrap: 5,000 resamples, seed
   20261004, empty weeks retained. Report descriptive 95% intervals for the
   PF and mean-R differences.

## Outputs

- `Reports/levels/breakout_concentration_20261005/` and results doc
  `docs/levels/BREAKOUT_CONCENTRATION_RESULTS.md`.
- Reconcile level, week and year sums to all candidate trades. Unit tests
  cover level identity and the generic concentration code.
- No MT5 run.
