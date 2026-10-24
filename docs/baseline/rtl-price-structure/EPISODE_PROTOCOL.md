# RTL flagged episodes: frozen profit-location protocol

2026-10-24. Saved before calculating new conditional outcomes. User authorized
locating profits within flagged periods and asked about twenty-bar sensitivity
and agreement among moving averages. This diagnoses existing labels; no new gate
or threshold search. [Previous protocol](PROTOCOL.md), [previous results](RESULTS.md).

## Inputs and fixed scope

Use the already verified Reports/rtl_price_structure_20261024 feature panels,
trade ledger, thresholds and provenance. Reconcile original uncapped RTL M30/RR1
raw ledger in Reports/timeframe_baseline_20261015, including mae_money/mfe_money,
and its saved RTL_timeframe.mq5 against the original manifest hashes.
One contract, $2/point, $1.05 cost; planned original risk as R denominator.
Eras remain 2016-19 and 2020-September 2026 (16,668 total eligible trades).
Exclude incomplete October 1 and all later data before new attribution.

Four separate flags, retaining ORIGINAL pre-2016 cutoffs:
1. D1 low_eff_high_overlap.
2. M30 low_eff_high_overlap.
3. M30 high_overlap_high_wick (regardless of efficiency).
4. M30 low_eff_high_overlap_high_wick.
Twenty observations is primary; repeat the same attribution at 10/40 as fixed
sensitivity. No choosing a best window, merging flags, or new MA outcome test.

## Episodes and timing

For each flag/window independently, an episode is a maximal consecutive run of
TRUE valid feature rows, not a run of trades. Include observations without trades;
invalid windows break runs. Use all available pre-2016 history to identify starts.
Build on rows whose available_at is strictly before 2026-10-01; no synthetic bars
or session resets. D1 availability = source date + one calendar day midnight;
M30 availability = bar open + 30 minutes, as in the original study.

Store episode start/last-true/first-following-false availability, bar length and
elapsed clock time. Do not split episodes at era/year boundaries. Flag episodes
left-censored if their start cannot be observed after a preceding valid false,
and right-censored if no subsequent false is observed by the study endpoint.
Use a separate censored phase; do not pretend a final truncated run has ended.

At actual order submission, fill and exit, select last availability <= timestamp.
For selected trades, verify submission flags exactly match the previous study.
At fill/exit distinguish same_episode, unflagged, later_episode; unknown if outside
available coverage. A later episode means the submission episode already cleared,
even if the market is flagged again. Record submit-to-fill delay and whether fill
and exit occur at/after the first clear timestamp of the original episode.

Episode phase at submission is explicitly RETROSPECTIVE: for an uncensored run
of length m>=3, position j is one-based, q=(j-0.5)/m. early q<=1/3, middle
1/3<q<=2/3, late q>2/3. Runs of length 1/2 are short_episode. Censored runs are
censored regardless of apparent length. None of these future-length labels is
an executable predictor. Also report causal age bins 1, 2-3, 4-8, 9+ completed
flagged observations at submission, to separate episode age from hindsight phase.

## Range and logged trade envelope

At submission freeze H=max(high), L=min(low) over the same last n completed
OHLC candles used by the flag. The range uses n candles, although efficiency
requires an additional starting close. The boundaries never expand after entry.
Save headroom_R=(H-requested_entry)/(requested_entry-original_stop), descriptive.

Current saved EA OnTick samples POSITION_PROFIT; SaveClosedTrackedTrade includes
realized gross exit PnL before writing MAE/MFE. With one contract and $2/point:
sampled_max_price=fill_price+mfe_money/2;
sampled_min_price=fill_price+mae_money/2.
Do not subtract research costs or clamp with zero; the ask fill can differ from
the sampled bid envelope. Keep fill-price placement separate. Assert maximum >=
exit price >= minimum and maximum >= minimum; reconcile source gross PnL exactly.
These are logged tester bid/exit bounds, not live tick data or timestamps of
extrema. Do not use a whole entry/exit-minute high that might occur after exit.

Four exclusive path groups: contained (max<=H and min>=L), upper_only (max>H,
min>=L), lower_only (max<=H,min<L), both (max>H,min<L). Strict comparisons; touching
a boundary is contained. Also partition fill and exit endpoints as above/inside/
below this frozen range. An upper excursion followed by an inside exit is not
the same as a sustained breakout. Do not infer time/order or causation from bounds.

## Outputs and reconciliation

For every flag/window/era, save selected trade attribution and episode inventory.
Summaries by all, retrospective phase, causal age, path group, fill episode state,
exit episode state, fill location, exit location, and phase x path group. Report
trade counts, winners/losers, active episodes/sessions/weeks, gross/net dollars,
positive net dollars, absolute negative net dollars, net R mean, PF, holding and
submission delay. Shares of winning dollars and losing dollars use their own
positive denominators; net contributions alone can be misleading. Partitions
must sum exactly to the prior study's selected counts, dollars and R totals.
Provide per-episode trade counts and PnL (including zero-trade episodes in inventory).
Keep n=10/40 and both eras visible, with n=20 primary report and compact figure.

This is attribution, not a statistical filter-selection exercise: no new bootstrap
or automatic promotion rule. Small cells and few episodes are explicitly weak
evidence. Repeated historical use, modelled fills and hindsight phase limit
interpretation. A profitable contained-path group supports profit opportunities
within the frozen range; it does not prove future containment was predictable.
Profits associated with upper escapes and/or cleared episodes may motivate a
later timing hypothesis, but do not establish a causal or executable restart rule.

Independently check hashes, joins, extrema conversion, literal episode boundaries,
range slices, censoring, all output partitions and summaries. Test flag gaps,
short/right-censored runs, exact availability boundaries, equal-price touches,
and future-price perturbations (causal fields unchanged; retrospective phase may
change). Save verification/provenance and update plan/status/journal after results.

## Separate MA agreement proposal (not tested here)

User proposes slope agreement across lengths 5..200. For SMA one-bar slope,
SMA_L(t)-SMA_L(t-1)=(C[t]-C[t-L])/L exactly; sign agreement is therefore agreement
among horizon returns, not independent votes. Step-5 sampling gives 31 of 40 votes
to lengths >=50. Consider a fixed spread 5,10,20,40,80,160,200 or equal horizon-band
weighting rather than accidentally overweighting slow horizons. This is a design
proposal only, not an outcome-selected alternative.

Separate up, down and mixed/flat; define a normalized slope deadband before any
outcome test. Distinguish short-down/long-up pullbacks from the opposite conflict.
Agreement describes history and cannot remove lag; waiting for broad agreement
may exclude reversals. Assess this only after the present attribution, with a
separate frozen protocol and explicit transition/restart accounting.
