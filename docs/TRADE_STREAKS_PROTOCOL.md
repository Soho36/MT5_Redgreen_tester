# Q24: trade-result streaks — frozen 2026-10-07

Question: do consecutive profitable or losing RTL trades predict the next trade,
and would stopping for the session protect profit or avoid continued losses?
Exhaustion, continuation and independence are competing explanations.

## Population and information timing

Use the saved `trendrr_20261002_f50_baseline` RTL ledger and its signal log:
MaxRedRun=3, fixed 1R bar-close exit, calendar/session flattening, one MNQ-priced
contract, one-minute OHLC. Commission is $1.05 per completed trade; net R is net
dollars divided by 2 times the signal range. Audit against MT5 stats and the
established Q10 unique-trade ledger. No legacy CSVs or short trades.

Report 2016-2019 and 2020-01-02 through 2026-07-13 separately, plus individual
years (partial 2026). Earlier history is excluded. All data have already been
examined; this is exploratory research, not untouched validation.

A win is net dollars > 0, a loss < 0, and zero breaks either streak. Only a
closed trade can update the state. Attach the state at actual order submission,
not at the next trade's exit. Require previous exit <= submission, no overlapping
positions, no cross-session positions, unique trades, positive risks and
chronological timestamps. If these assumptions fail, stop and resolve them.

Primary scope resets at each synthetic exchange-session date (the dataset clock,
not the computer clock). Secondary scope carries across sessions, but resets
at the start of each comparison period. Keep both scopes separate.

## Fixed comparisons

Tabulate **exact preceding lengths** 1, 2, 3, 4, 5, 6, and 7+ separately for wins
and losses, against all other next trades in that scope/period. No preceding
closed trade in the scope is a separate state. Also show threshold groups >=2
through >=6 (overlapping groups, explicitly labelled). A completed five-win run
is not evidence about the sixth trade: that would select runs by their future.

Show n, win rate, Wilson 95% descriptive intervals, mean net R, net dollars,
mean dollars, profit factor, closed-trade drawdown and yearly comparisons.
Use 2,000 calendar-week cluster bootstrap samples for candidate-minus-complement
win-rate and mean-R intervals, retaining zero-trade weeks. Wilson intervals do
not account for dependence; the cluster intervals are the relevant comparisons.

Compare observed sequences with 2,000 shuffles: (1) within calendar month,
preserving changing monthly outcome distributions, and (2) within session,
preserving each day's complete set of dollar/R outcomes and trade times.
Recompute streaks after every shuffle. Shuffling whole net-dollar/net-R pairs
preserves their relationship; it is a statistical null, not a fill simulation.
Report run counts/longest streaks and conditional win-rate/mean-R differences.
Use centered two-sided empirical permutation p-values; Holm-adjust the exact-bin
tests jointly across both scopes, both signs and seven lengths, per period and
metric and shuffle type. Rare empty groups are missing, never zero performance.
Shuffled tests are conditional on their exchangeability assumptions; the
within-session null helps separate sequence effects from favorable/bad days.

Primary motivating examples: next trade after exactly five same-session wins,
and after exactly three same-session losses. Adjacent lengths and both periods
must be visible; do not choose a threshold from the largest isolated result.

## Daily stopping counterfactual

For wins and losses independently, stop after 2/3/4/5/6 consecutive **taken,
closed** trades of that sign, resuming next session. Keep the triggering trade.
Report baseline and each rule's trades, dollars, R, PF, DD, net/DD; removed
trades, affected sessions, net/R of the removed remainder, and yearly effects.
Measure how often the remainder loses dollars and gives back more than half
the positive cumulative session profit at the trigger. Do not discard a
profitable remainder because it contains a losing trade.

This is an exact subset counterfactual for this session-stop rule if there are
no outstanding orders/positions at the trigger: no entries resume that session,
and the baseline is flat before the next session. Nevertheless label it as
saved-ledger evidence; an EA implementation/full MT5 rerun is required before
adoption. Skipping just the next trade or trading only after losses would free
entries, require shadow-history semantics and a full rerun; do not simulate
those by deleting rows. No sizing change or EA modification in this screen.

## Decision rule and limits

A next-trade predictive lead requires >=100 observations in each period, the
same direction of mean-R difference in both, week-bootstrap mean-R intervals
excluding zero in both, Holm-adjusted within-session permutation p < .05 in
both, and >=8/11 years agreeing where both groups exist. Neighboring lengths
must agree in direction. Otherwise call the evidence inconclusive or negative.
Win-rate-only dependence is not a profitable edge; do not infer trend
exhaustion from a result sequence without a separate price-context study.

A session-stop lead requires net/DD >=1.10 times baseline, net >=90% baseline,
DD no larger in both periods, dollar benefit in >=8/11 years and improvement
at both neighboring thresholds. Edge thresholds 2/6 cannot qualify without
both neighbors. A stop after wins need not follow from next-trade loss odds:
the whole rest-of-session return is the relevant counterfactual. A stop after
losses tests continuation of adverse conditions, not a claim that a win is due.
Keep every threshold, costs and known OHLC execution sensitivity visible.

Sources: [NIST runs test](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35d.htm)
for sequence non-randomness; [Bailey et al.](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)
for the distinction between historical selection and out-of-sample evidence.
