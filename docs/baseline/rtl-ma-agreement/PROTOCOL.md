# RTL multi-horizon MA slope agreement

Frozen 2026-10-24 before conditional MA outcomes. User authorized this test after
the completed chop/episode attribution. RTL only. This is a new exploratory
hypothesis on repeatedly examined history, not untouched validation data.

## Questions and source

Does clear up/down/mixed MA slope agreement distinguish unfavorable RTL entries?
Does waiting for clear up miss profitable transitions? Are effects stable under
a small fixed set of definitions? Describe both dollars and R, since fixed
one-contract dollar risk changes across trades and eras.

Use verified `Reports/rtl_price_structure_20261024/features_m30_20.csv` OHLC,
bar_time, available_at and switch_bar, and that directory's trades.csv. Check
their hashes against its provenance, and preserve the prior verification trail.
Use observed M30 bars only, no synthetic gaps/weekends. M30 opens are available
30 minutes later, including the just-completed signal bar at actual submission.
Source clock/session conventions remain unchanged. Feature rows available at or
after 2026-10-01 are excluded. Daily MA variants are outside this first test.

Baseline: uncapped RTL M30 RR1, original stop, first qualifying M30-close exit,
session flatten; one MNQ-valued contract, $2/point, $1.05 round-trip cost.
Preserve 25,833 source / 16,668 eligible trades: 6,167 in 2016-19 and 10,501 in
2020-September 2026. Exclude the incomplete October 1 forced tester exit.
Reconcile net dollars $4,416.65 / $38,399.95 and all existing economics exactly.
Calibrate only on price observations available strictly before 2016-01-01.

## Features and frozen variants

Primary SMA lengths L = 5,10,20,40,80,160,200, equal weight. SMA uses closes.
One-observation slope d_L(t)=SMA_L(t)-SMA_L(t-1)=(C_t-C_{t-L})/L.
Compute with this exact identity and independently check explicit rolling means.
TR_t=max(H_t-L_t,abs(H_t-C_{t-1}),abs(L_t-C_{t-1})); first TR is invalid.
A20 is the arithmetic mean of 20 consecutive valid TR values (not Wilder ATR).
Normalized slope z_L=d_L/A20. A20<=0 or missing inputs makes the row invalid.
Use common full-history validity: all closes/TR needed through maximum L=200,
so every variant requires 201 observed closes. Save the earliest consumed bar.

For each L in the union of primary and dense grids, cutoff b_L is the linear
20th percentile of abs(z_L) across common-valid pre-2016 price rows, equal weight
per observation (not per trade). Freeze the resulting numbers. Up vote if z_L>b_L,
down if z_L<-b_L, else flat; equality is flat. No floating tolerance changes a
vote. A zero cutoff leaves exact zero flat. Invalid rows never vote or trade.

Five variants only, no factorial optimization or outcome-selected best setting:

| ID | Grid | Per-length deadband | Votes for clear up/down |
|---|---|---|---|
| primary | seven primary lengths | pre-2016 p20 | >=5 of 7 |
| loose | seven primary lengths | same p20 | >=4 of 7 |
| strict | seven primary lengths | same p20 | >=6 of 7 |
| zero_band | seven primary lengths | zero | >=5 of 7 |
| dense | 5,10,...,200 (40 lengths) | respective pre-2016 p20 | >=29 of 40 |

State=up if up votes meet requirement, down if down votes meet requirement,
otherwise mixed. Requirements exceed half, so up/down cannot coexist. Mixed
includes flat and conflicting slopes. Save vote counts and (up-down)/grid_size.
Dense is a weighting sensitivity: 31 of its 40 votes have length >=50; these
correlated slopes are not independent confirmations.

Primary short direction: majority >=2 of the votes at 5,10,20; long direction:
majority >=2 at 80,160,200. Otherwise that band is flat/mixed. Save all nine
short/long combinations as an orthogonal context on EVERY valid primary row.
Short-down/long-up is labelled pullback; short-up/long-down recovery. Conflicts
can coexist with an overall up/down state, so never assume they imply mixed.

Roll sensitivity: all variants use the same roll-clean mask, requiring no
switch_bar anywhere in the 201 consumed observations. Retain full sample as
primary; report counts/outcomes excluding roll-contaminated windows separately.

## Availability, episodes and transition attribution

Join the latest feature available_at <= actual submitted time, exact matches
allowed. Retain only common-valid study trades. Require all 16,668 to be valid;
otherwise stop and disclose rather than silently changing the population.
Lookup primary state independently at fill and exit. All features use completed
information; open positions never see future labels as entry inputs.

For each variant, state episodes are maximal consecutive valid observations with
the same state. Invalid rows break episodes; first valid episode after an invalid
row is left-censored. Causal state age starts at 1 and counts observed rows, not
wall-clock half hours. Save state, prior episode state, age and episode start.
Age bins: 1,2-3,4-8,9+. They are causal; no future episode phase is an entry input.

Primary non-up spells join consecutive valid down/mixed rows, even if down and
mixed alternate. A spell ends at the first up observation; invalid/end boundaries
censor it. Inventory includes zero-trade spells, start/last observation, number
of observations, first-up time if observed and left/right censoring. Ending at
first up is a historical endpoint, not a prediction at spell start. An up spell
after a valid non-up spell is a reentry episode. No era boundary resets episodes.

For each primary non-up submission, save first subsequent up observation if it
occurs before the study cutoff and before any invalid break. Retrospective timing
partition: up_by_fill (first_up<=fill), up_during_trade (fill<first_up<=exit),
up_after_exit (first_up>exit), no_observed_up (right-censored). Also save delay in
observed bars and elapsed minutes, and (close_at_first_up-close_at_submission_row)
/A20_at_submission. These are FUTURE-conditioned diagnostics, not filter inputs.
For primary up submissions, timing is already_up. Separate fill/exit state tables
show actual state when filled/closed. Report up-state causal age after reentry,
and primary non-up spell totals including zero-trade spells. Do not call delay
the number of bars since a true market bottom, or infer an optimal entry time.

## Outcomes and fixed ledger policies

For each variant and era report all/up/down/mixed summaries and yearly versions
(2026 partial), plus roll-clean state summaries. For primary also summarize
short/long context, context x state, state x causal age, fill state, exit state,
retrospective first-up timing x submission state, and up reentry age. Keep counts,
active sessions/weeks/episodes, gross/net dollars, positive winning dollars and
absolute losses, gross/net mean R, dollar PF, planned risk, holding time, cost
stress (+$1/+ $2 per trade), closed-trade and daily-close drawdown/duration.
Use the same full observed-session calendar in each era, including zero-PnL dates.
Partitions must reconcile counts/dollars/R to the original ledger.

Three fixed policies at SUBMISSION only: skip_mixed; skip_down; only_up (skip
down or mixed). No cancellation of already accepted orders; no early closure or
re-entry at confirmation price. This is ledger omission, not a full strategy
replay: skipped positions could free later orders not present in the ledger.
Report retained trades/net/R/drawdowns, losses avoided, winning dollars missed,
holding fraction and planned-risk fraction for all variants/eras. Compare each
to baseline and to the entire baseline scaled to the same retained holding time,
scaling dollar PnL and costs together. Fractional size is a diagnostic comparator,
not an executable one-MNQ sizing rule. R per trade stays unchanged under scaling.

For PRIMARY policies only, 2,000 circular shifts of the skip mask along
chronological entry-time/ticket order, shared offset draws across policies in an
era, seed 20261025. Preserve number skipped and circular trade-order run lengths;
do not claim calendar-duration or volatility matching. Report each retained PnL,
daily-close DD, holding time and results scaled to actual retained holding time.
Save descriptive fractions of shifts beaten for dollars and DD separately.

Uncertainty for PRIMARY up/down/mixed vs its complement: 10,000 paired circular
four-calendar-week blocks per era, seed 20261024, include empty calendar weeks;
sample ceil(nweeks/4) block starts and trim to nweeks. Same draws across groups.
Report percentile intervals for group mean net R and group-minus-complement mean
net R: nominal 95% and 98.33333333333333% (Bonferroni for three primary groups
within an era). Not adjusted for all earlier studies or sensitivity variants.
Save draws or sufficient sampled sums so independent verification can reconstruct
intervals. Flag coverage below 200 trades or 30 active weeks as inadequate.

## Decision and artifacts

No MA setting will be adopted from this ledger study alone. Interpret whether a
policy sacrifices profitable states, reduces losses consistently, and compares
well with equal exposure. A follow-up full replay is warranted only if a PRIMARY
policy's skipped set has negative dollars and mean net R in BOTH eras, at least
200 skipped trades/30 active weeks in each, and retained daily-close DD is lower
than baseline in both. Check sensitivities, annual concentration and uncertainty
before describing it as promising. This is a screen for additional work, not
proof of superiority or a permission to deploy. If it passes, record a concrete
next replay specification; no automatic live/default changes.

Write features, calibration cutoffs, labelled trades, episodes/non-up spells,
summaries/yearly/roll summaries, policies/daily curves, uncertainty and placement
outputs, provenance/audit. Record protocol and input/output/program hashes.
Independent reconstruction must check literal rolling SMA means, TR, cutoffs,
votes/states, all event asof joins, state/non-up boundaries and future timing,
economics, all partitions/policies/drawdowns, bootstrap and placement aggregates.
Focused tests: exact cutoffs, zero/invalid ranges, conflicting bands within clear
state, exact availability, missing-bar gaps, invalid episode breaks, reentries,
censoring, and future-price perturbations leaving earlier causal fields unchanged.
Render a compact chart, verify it visually, and update saved plan/status/journal.

SMA definitions and lag context:
https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential
