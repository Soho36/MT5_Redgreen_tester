# Entry-context research checklist

Created 2026-09-30. These are hypotheses, not promised improvements. Investigate
one at a time, retain negative findings, and link each completed study here.
Research baseline: `MaxRedRun=3`, `MinLocation=0`, original entry/exit rules.

Current priority: [broad M30 support interaction](../setups/horizontal/README.md). For this
experiment fixed 1R SL/TP is authorized. Any qualifying red candle whose range
contains the known support level belongs in the aggregate, regardless of where
it opens/closes. Candle subtypes are deferred; the speed branch is archived.

## Q1. Can a small green interruption hide a continuing decline?

- [x] Complete first diagnostic study: [results](../baseline/q01-q02-preceding-candles/RESULTS.md).
  Recent N=10–20 weakness did not replicate in 2015–2019; no filter adopted.
- Question: does a short consecutive red run still perform poorly when the
  surrounding bars show a longer interrupted decline?
- Measure red-bar share and downward close-to-close share among N preceding
  bars, alongside the existing consecutive red-run count.
- Example: six reds, one small green, then two reds passes the run cap.
- First study uses the explicit density proxy in the
  [protocol](../baseline/q01-q02-preceding-candles/PROTOCOL.md); it does not yet distinguish the
  body size of the interrupting green bar.
- Follow-up only if justified: distinguish a small green interruption from a
  substantial recovery, using a definition fixed before examining outcomes.

## Q2. Did price recover after breaking an earlier low?

- [x] Complete first diagnostic study: [results](../baseline/q01-q02-preceding-candles/RESULTS.md).
  PF rankings reverse across periods; no recovery requirement adopted.
- Separate no new low, new low with no recovery, and new low with the signal
  closing back above the preceding N-bar low.
- The old `sweep` feature detects the breach only; it never required recovery.
- All information is known when the signal closes. Do not use what happens
  after order placement to classify the entry.
- Definitions and equality cases: [protocol](../baseline/q01-q02-preceding-candles/PROTOCOL.md).

## Q3. Were preceding bars overlapping or progressing steadily?

- [x] Answered 2026-10-02: [Q3 results](../baseline/q03-overlap/RESULTS.md). No overlap/direction group
  loses in both periods at N = 5/10/20; no filter. Overlap is barely correlated with
  `trend_eff` (new information), but it doesn't predict outcomes consistently.
- Measure adjacent high-low range overlap alongside net price movement.
- Motivation: repeatedly crossing the same prices differs from a rising or
  falling staircase, even with similar final location and overall range.
- Before starting: define the normalization, treatment of zero-range bars,
  and whether the signal participates. Avoid duplicating `trend_eff` without
  demonstrating additional information.

## Q4. Is the immediate pullback opposed to the broader move?

- [x] Answered 2026-10-02: [Q4 results](../baseline/q04-context/RESULTS.md). All 4 older/recent direction
  groups are profitable in both periods at (5, 20), (3, 10) and (10, 40); no filter.
- Compare the direction of the recent few bars with an older, non-overlapping
  context window.
- Motivation: a recent decline after an advance differs from a decline inside
  a longer decline; a single aggregate trend measure can hide that distinction.
- Before starting: fix both window lengths and the direction definition.

## Q6. Does proximity to a session/week low identify better entries?

- [x] First screen complete 2026-10-03: [results](../setups/horizontal/support-bounce-long/q06-q07-price-levels/RESULTS.md),
  [protocol](../setups/horizontal/support-bounce-long/q06-q07-price-levels/PROTOCOL.md). Previous-session support within 0.5R has
  inconsistent PF rankings and only 187 earlier-period trades. Far-support
  groups remain profitable at all predefined cutoffs. No filter.
- Current-session and previous-week sources were reported separately; weekly
  near-support samples are sparse. Confirmed swing zones remain untested.

## Q7. Does overhead room to a session/week high affect outcomes?

- [x] First screen complete 2026-10-03: [results](../setups/horizontal/support-bounce-long/q06-q07-price-levels/RESULTS.md),
  [protocol](../setups/horizontal/support-bounce-long/q06-q07-price-levels/PROTOCOL.md). Previous-session resistance within 1R is
  profitable in both periods (PF 1.110 / 1.196), as are the predefined neighbors.
  No avoidance filter; common-population checks reach the same decision.
- Current-session limited-room trades have higher PF than more-room trades in
  both periods, contrary to the initial hypothesis. Secondary observation only;
  no post-hoc filter selected and no full filtered-strategy run triggered.

## Q8. Does a breach followed by a reclaim predict a better upward response?

- [x] First support-reclaim study complete 2026-10-03:
  [results](../setups/horizontal/support-reclaim-long/q08-breach-reclaim/RESULTS.md), [protocol](../setups/horizontal/support-reclaim-long/q08-breach-reclaim/PROTOCOL.md).
- Current-session reclaim attempts more often finish >=+0.5R above signal close
  after 90 minutes: 35.7% vs 29.6% earlier, 31.5% vs 28.4% recently. This narrower
  probability result persists at 2/4 ticks and appears in 9/11 yearly slices.
- Mean forward return does not improve in both periods, and filled-trade PF
  reverses ranking (1.031 vs 1.260 earlier, 1.280 vs 0.955 recently). No filter.
- [Post-hoc dispersion check](../setups/horizontal/support-reclaim-long/q08-breach-reclaim/RESULTS.md#post-hoc-check-direction-or-dispersion):
  reclaims also more often finish <=-0.5R (28.1% vs 24.2% recently, 25.9% vs
  24.2% earlier). The recent excess is wider outcomes, not upward bias; only
  2016-19 leans upward. Reclaim signal ranges are ~20-25% smaller, inflating R.
- Includes 35,632 qualifying order attempts and 14,968 baseline fills. The
  separate resistance-approach/breach/path study remains proposed.

## Q9. Do quick recoveries outperform slow ones at comparable depth and volatility?

**Archived direction, 2026-10-03:** [reason and retained evidence](../setups/horizontal/support-reclaim-long/q09-reclaim-speed/ARCHIVE.md).

- [x] First minute-speed study complete 2026-10-03:
  [results](../setups/horizontal/support-reclaim-long/q09-reclaim-speed/RESULTS.md), [protocol](../setups/horizontal/support-reclaim-long/q09-reclaim-speed/PROTOCOL.md).
- Fast <=2 versus slow >=6 minutes, among final M30 reclaims, leaves 130/218
  current-session matched pairs. Fast +0.5R endpoint rates are 34.6% vs 36.2%
  earlier and 28.4% vs 32.6% recently. Mean-A difference intervals include zero;
  all frozen candidate gates fail. No speed filter or early-entry rule adopted.
- The two-sided R effect is reproduced, but it diminishes/reverses with lagged
  volatility normalization. Smaller reclaim signal ranges explain part of why
  both half-R barriers are easier to reach. Matching also removes the original
  upper-tail advantage; this does not establish a causal explanation.
- Previous-session/week speed matches are too sparse. Immediate-reclaim,
  approach-speed and sustained-recovery proposals are parked, not active work.

## Q10. Are support-interaction red signals better than every other red signal?

**Primary result (2026-10-04): original RTL exit.** Interaction/rest PF:
current session 1.179/1.079 then 1.086/1.114; previous session 1.394/1.087 then
0.911/1.124; **previous week 1.707/1.096 then 1.451/1.098, but only 72/137 fills**.
No candidate. The broad "range overlaps any level" idea was dropped before being
computed: it mixed support tests from above with broken levels tested from below.
Q11 replaces it. Fixed-TP results below are secondary.

- [x] Complete 2026-10-03: [results](../setups/horizontal/support-bounce-long/q10-support-interaction/RESULTS.md),
  [protocol](../setups/horizontal/support-bounce-long/q10-support-interaction/PROTOCOL.md). User explicitly chose fixed
  -1R SL / +1R TP for this experiment; a separate full MT5 reference run produced
  16,395 trades. Compare every qualifying signal across all enabled windows,
  with the full complement; no M1 speed or matched-only control.
- Current-session interaction versus all other PF: 1.226/1.000 in 2016–19,
  1.079/1.084 in 2020–26. Earlier concentration of the edge does not replicate.
  Close-below PF flips 1.356 to 0.958; reclaim is stronger recently, not earlier.
- Previous-week interaction is better in both periods, but only 79/146 trades;
  previous-session rankings reverse. No candidate passes the predefined rule.
- Census includes 52,070 potential signals, 38,853 attempts and 16,395 fills.
  Subset net/DD is attribution, not a support-only backtest. Original RTL
  bar-close exit and production defaults remain unchanged.

## Q11. Do red signals at intact one-week M30 swing-low support beat every other signal?

- [x] Complete 2026-10-04: [results](../setups/horizontal/support-bounce-long/q11-level-visit/RESULTS.md),
  [protocol](../setups/horizontal/support-bounce-long/q11-level-visit/PROTOCOL.md). Candidate/rest PF 1.201/1.087 and
  1.140/1.099; avg R +0.036 / +0.005 better; 7/11 years. Intervals include zero
  and N = 3 disagrees, so no full rerun and no filter. Recently, no-level signals
  do better than candidates. Only 66 candidates overlap Q10's weekly lead.
- Levels: confirmed M30 swing lows (5 bars each side) from the current session
  plus 5 previous sessions, merged within D = 0.5 x ATR(14). Two weeks and N = 3
  reported alongside, not selected afterwards. Original exit.
- Support = price closed >= 1 x ATR above the level after the pivot, then returned
  into L +/- D, with no close more than D below in between. False breakdowns
  (shallow undercuts) count; candle shape and open/close side do not matter.
- Amended before outcomes (2026-10-04, after example charts): the signal low may
  be at most D below the level; deeper slices are a separate reported group.
- Candidate vs every other signal; broken-level contacts (tested from below),
  not-departed contacts and no contact reported separately. Q10 follow-up rule.

## Inbox: new questions

Write any new idea here as soon as it comes up: one line, no analysis needed. When we pick
it up, it gets a number, a fixed protocol before looking at outcomes, and a results doc.

| Added | Question | Status |
|---|---|---|
| 2026-10-07 | Do consecutive profitable/loss-making trades predict exhaustion or recovery, and should trading stop for the session after a streak? | **Q24 complete** ([results](../baseline/q24-trade-streaks/RESULTS.md), [protocol](../baseline/q24-trade-streaks/PROTOCOL.md)): no predictive/stop gate passes; five daily wins too rare; after three losses no win-rate uplift; loss stops are an inconsistent risk trade-off |
| 2026-10-03 | Are red candles **from support levels** better signals than **every other red candle**? | Q10 complete (original exit primary): previous-week lead, too few fills. [Q11](../setups/horizontal/support-bounce-long/q11-level-visit/RESULTS.md) one-week swing-low support: small, unconfirmed edge, no filter |
| 2026-10-04 | Do red signals that **break horizontal swing-high resistance** from below beat every other signal? | **Q18 passes both stages** ([results](../setups/horizontal/resistance-breakout-long/q18-breakout/RESULTS.md)); open lead: execution realism and forward evidence next |
| 2026-10-04 | Do red signals at **rising trendline support** beat every other signal (Q11/Q12 questions for trendlines)? | **Q14 complete** ([results](../setups/trendlines/uptrend-bounce-long/q14-trendline-support/RESULTS.md)): candidates worse than the rest in both periods (PF 1.029/0.950 vs 1.114/1.124); broad contact also worse; no filter. Falling resistance lines: Q15 passed the attribution gate, Q16 not concentrated, but **Q17 stand-alone fails** ([results](../setups/trendlines/downtrend-breakout-long/q17-standalone/RESULTS.md)); no filter |
| 2026-10-04 | Is a level approached **from below** (broken support retested, acting as resistance) also a valid level for long RTL signals? | Proposed; study separately from Q11 support. Q11 reports these contacts as its broken-level group, descriptively only |
| 2026-10-03 | Does **breach/reclaim speed** distinguish exploitable bounces? | **Archived direction** after Q9; retain [evidence and reasons](../setups/horizontal/support-reclaim-long/q09-reclaim-speed/ARCHIVE.md), no automatic follow-up |
| 2026-10-02 | Does the **signal candle's shape** matter: full body (marubozu), doji, shooting star (long upper wick), hammer (long lower wick)? | **Answered as Q5** ([results](../baseline/q05-candle-shape/RESULTS.md)): no shape loses in both periods; no filter |
| 2026-10-03 | Does **nearby support below the signal** distinguish better RTL entries from signals far from support? | **First screen answered as Q6** ([results](../setups/horizontal/support-bounce-long/q06-q07-price-levels/RESULTS.md)): session/week extremes, no filter; swing zones untested |
| 2026-10-03 | Does **room to resistance above the planned entry**, measured in initial R, affect outcomes? | **First screen answered as Q7** ([results](../setups/horizontal/support-bounce-long/q06-q07-price-levels/RESULTS.md)): no filter |
| 2026-10-03 | Does price **approach a known high/low, breach it, then reclaim the range and reverse**, rather than continue through? Does this explain current-session nearby-resistance performance or improve long entries after a low reclaim? | **Support-reclaim screen completed as Q8** ([results](../setups/horizontal/support-reclaim-long/q08-breach-reclaim/RESULTS.md)): more +0.5R responses (mostly two-sided dispersion), no stable RTL improvement; resistance path study pending |
| 2026-10-03 | Does **interaction with an established level** matter: no contact, touch and hold, pierce and reclaim, or close through? | Session/week low behavior screened in Q8 and actual fixed-1R trades versus full complement in [Q10](../setups/horizontal/support-bounce-long/q10-support-interaction/RESULTS.md); pivot zones and resistance path remain proposed |
| 2026-10-03 | Does **level history** matter: age, time since last visit, and first versus repeated retest? | Proposed; count separate visits, not clustered pivots |
| 2026-10-03 | Does a **broken resistance level retested as support** behave differently from support that has never changed role? | Proposed; requires chronological break/retest tracking |
| 2026-10-03 | Does proximity to **previous-session highs/lows or higher-timeframe swing levels**, alone or overlapping local zones, affect outcomes? | Session/week extremes screened in Q6/Q7; higher-timeframe pivots and confluence remain proposed |

### Archived proposals after Q8: speed and possible execution models

**The following is historical planning, superseded on 2026-10-03.** The user's
priority is now broad M30 contact and actual strategy outcomes. These proposals
are not a queue of work to resume. [Archive note](../setups/horizontal/support-reclaim-long/q09-reclaim-speed/ARCHIVE.md).

The first recovery-delay comparison below was completed as
[Q9](../setups/horizontal/support-reclaim-long/q09-reclaim-speed/RESULTS.md). Its negative candidate decision does not test
immediate minute entry or the broader level-interaction population.

At that time the user prioritized speed and noted behavior at older levels. Separate
the speed of the approach/breach from the speed of recovery; a fast downward
breach alone may continue. Record penetration in ticks and lagged-volatility
units, approach movement per minute, delay from first below-level minute to
first minute close back above, minute closes below the level (a dwell proxy),
reclaim distance, and subsequent recrossings. Depth, volatility and time of day
are potential confounders. Minute OHLC cannot reveal seconds spent below the
level or the exact within-minute path; preserve that uncertainty.

First proposed step: describe minute paths within the existing Q8 signal cohort,
with forward returns still starting after the M30 signal closes. Fast/slow bins
and comparisons must be specified before examining their outcomes. Reclaim
stability observed after a decision is an outcome; requiring stability is a
later-entry variant, not information available at the first reclaim.
Report both response tails (e.g. >=+0.5 and <=-0.5), and normalize by a lagged
volatility measure (e.g. ATR before the signal) alongside R: the Q8 excess was
largely two-sided dispersion, so a one-tail rate alone cannot show a bounce.

Possible execution experiments, each separately defined rather than jointly
optimized: enter on a completed-minute reclaim; enter on a later retest of the
reclaimed level; enter after a short hold above the level; use a short time exit
or price target; exit on a renewed failure of the reclaim while retaining a hard
stop. No profitability is established for any of these options.

An early minute-entry strategy needs a new causal event population. Do not
select early entries using the eventual M30 candle color, completed reclaim,
full M30 range, or low that develops after entry. Define events using only
information then available, use volatility measured before the event or actual
entry-to-stop risk, retain failed attempts, and deduplicate repeated crossings.
The Q8 +0.5R result was an endpoint **at 90 minutes**, not a hit probability
within 90 minutes and not a measured 0.5R-target win rate.

For older levels, retain previous-session/week sources separately and define
confirmed swing lows from a fixed broader history before testing. Track when
the level became known, age and previous visits. Do not label a level major
because a later chart shows a strong reversal there. Roll exclusions remain.
Older levels are an extension: Q8's current-session association is not evidence
that the same behavior exists at every age/source.

### Follow-up hypothesis: approach, breach and reclaim

The support part below is now implemented in [Q8](../setups/horizontal/support-reclaim-long/q08-breach-reclaim/RESULTS.md).
Its probability finding is retained, but a post-hoc check shows it is mostly
two-sided dispersion; no filter is adopted. The resistance-path
part remains proposed.

User hypothesis, 2026-10-03: clustered stops may help explain movement toward
and through session extremes, followed by reversal when the move fails to hold.
Keep three empirical claims separate: reaching a level, breaching it, and
reversing after the breach. Q6/Q7 compared entry context with trade profit;
they did not establish any of those event probabilities or the order-flow cause.
OHLC data do not identify stop orders or establish that stops are exhausted.

Two proposed applications to RTL:

- **Long toward an overhead high:** measure whether the pre-existing high is
  reached/breached before the original stop, and whether the subsequent path
  continues above it or closes back below. Events after entry are outcomes,
  never information used retrospectively to approve the original entry.
- **Long after a low reclaim:** distinguish approach from above with no breach,
  a breach with close back above the low, and a breach with close still below
  (exact equality separate). Also keep an already-below-level state separate.
  Compare the unchanged RTL trades. This extends Q2 using session/week anchors
  rather than rolling N-bar lows; Q2's negative result remains part of the evidence.

Current-session extrema are the motivated follow-up source; retain previous
session/week as separate comparisons. Fix breach size, reclaim/continuation
thresholds and observation horizons before running. Track signal formation,
order submission and fill separately. Preserve the existing map timing and
contract-roll exclusions. Reuse minute data and flag unresolved intraminute
event ordering rather than assuming a favorable path or launching tick runs.

For a claim that these levels are unusually likely destinations/reversal points,
compare with non-extreme reference prices matched on distance, direction, time
of day and volatility; nearby prices are mechanically easier to reach. A
trade-entry filter comparison and a level-event study answer different questions.
No change to the frozen Q6/Q7 decision rule and no new filter adopted.

Mechanism background (historical FX evidence, not an NQ result): Carol Osler's
[order study](https://www.newyorkfed.org/research/staff_reports/sr125.html) examines
clustering and different effects of take-profit and stop-loss orders;
[price-cascade study](https://www.newyorkfed.org/research/staff_reports/sr150.html)
finds that triggered stops can reinforce continuation. Reversal after a breach
must therefore be tested against continuation, not presumed from the breach.

### Price-level research scope

Use the old [`Level_rejection.cs`](../../mt5/Level_rejection.cs) as a source of ideas
for level discovery. The first proposed studies add context to the existing RTL
buy-stop baseline; testing the standalone rejection EA would be a separate study.
No level filter or strategy change has been adopted.

Before assigning study numbers, fix the zone boundaries, pivot confirmation
timing, break rule, session definition where relevant, and distance conventions.
For the initial interaction study, freeze the level map before the signal bar
opens, using only pivots confirmed by then. The signal can interact with those
levels but cannot create or move the level against which it is classified.
Measure overhead room from the planned buy-stop entry to the near edge of the
nearest eligible resistance zone, divided by the initial entry-to-stop distance.
Record entry inside a zone and absence of an overhead level as separate cases.

The old EA is not yet a research-grade source of level history: it rebuilds the
map each bar, checks breaks only against the latest close, counts merged pivots
as touches, and can merge support and resistance while retaining the first
pivot's role. Resolve those semantics before using freshness, retest counts, or
role reversal as features. Start with support proximity and overhead room, one
question at a time, under the existing protocol and full-rerun requirements below.

### Choosing the level horizon (2026-10-03)

The proposal below was implemented in the [frozen Q6/Q7 protocol](../setups/horizontal/support-bounce-long/q06-q07-price-levels/PROTOCOL.md).
The [first results](../setups/horizontal/support-bounce-long/q06-q07-price-levels/RESULTS.md) adopt no filter.

Separate **source window** from **age**: a previous-week extreme can have formed
on Monday or Friday. Record both the source and when its extreme was last set
(equal retests are visits, not a reset of formation age).

Proposed first comparison: previous completed session high/low as the primary
reference, with current-session-so-far and previous completed calendar trading
week high/low as two separately reported comparisons. This changes the proposed
first level source from clustered swing zones to simpler session extremes;
pivot-zone discovery and age cutoffs are deferred. Do not combine all sources
into one nearest-level map or choose a winning horizon after seeing results.

For every source, compute the map strictly before the signal bar opens. Current
session extremes use only earlier completed bars; previous week means the
completed Monday-Friday trading-date week, not a rolling five-session window.
Use the rebuilt symbol's full exchange-session convention (normally
01:00-23:59 in its synthetic clock, with actual early closes), not the EA's
entry windows or the computer's local date. The previous session is the previous
completed trading session, not necessarily yesterday. Keep missing history,
no earlier bar in the current session, entry beyond an extreme, and exact level
contact explicit. These reference extremes are not automatically proven or
unbroken support/resistance.

The continuous series uses unadjusted contracts. Exclude a source window that
contains another contract than the signal's contract, flag the reason, and
report common eligible trades alongside source-specific coverage. Do not compare
an old-contract high/low directly with a new-contract entry. Keep the RTL rules
unchanged while comparing proximity and overhead distance in initial R across
2016-2019, 2020-2026, and individual years. This remains a proposed diagnostic
design; exact bins and decision rules must be frozen before outcomes are read.

## Shared lookback questions

- [x] Compare N = 5, 10, 20, 50 for Q1/Q2 using consistent definitions and the same trades.
- N preceding bars means bars 2 through N+1; bar 1 is the completed signal.
  Existing `location_N` is different: it includes the signal in N bars.
- On M30, these are 2.5, 5, 10, 25 hours of bar time, not necessarily elapsed
  time across market closures. Session-boundary variants are separate tests.
- Log at least 51 bars. Extra recorded bars must not silently change a feature.
- Confirm a proposed filter with a full MT5 rerun before claiming a strategy
  improvement; excluding CSV rows changes neither order nor position availability.
- Previously examined 2015–2026 data remain exploratory, even with a frozen
  chronological split. Fresh-data or prospective validation is a separate stage.
