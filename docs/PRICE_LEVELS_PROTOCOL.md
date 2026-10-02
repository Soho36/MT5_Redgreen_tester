# Q6/Q7: price-level proximity and overhead room

Frozen 2026-10-03 before calculating level-conditioned outcomes. User authorized
the previous-session comparison, with current-session and previous-week sources
reported separately. These are exploratory diagnostics, not a new strategy.

## Data and population

- Reuse the audited `Reports/entry_shape_20261002/` train/recent RTL exports:
  `MNQcontDTBNT20102026_2`, M30, MaxRedRun=3, MinLocation=0, RR=1,
  original entry windows, calendar/fallback flattening, one contract, one-minute
  OHLC. No execution rule changes for this diagnostic.
- Periods: 2016-01-01 to 2020-01-01, and 2020-01-02 to 2026-07-14 (ends exclusive).
  All these data have been inspected previously; neither period is untouched.
- Rebuild M30 reference bars from the continuous minute source described in
  DATA_BUILD.md, dropping the same pre-01:00 tails. Validate all 51 recorded
  candles per trade against that reference and reconcile trade fields with the
  saved RR=1 baseline and totals with the saved tester stats.
- Levels are attached to the original signal, not the later fill. A pending
  order that survives several bars keeps its original signal's level snapshot.
- Net profit = exported gross profit minus $1.05 per round trip. Net R divides
  that by 2 dollars/point times the original signal range. Report both dollars
  and R; dollar PF decides eligibility for a subsequent filter experiment.

## Level sources and timing

Freeze every reference strictly before the signal bar opens. A level is a
historical extreme, not a claim that support/resistance remains unbroken.

1. **Previous session (primary):** high/low of the preceding available completed
   trading session, including overnight trading. Session dates follow the
   rebuilt symbol clock, normally 01:00-23:59; holidays/early closes use actual
   available bars. This is not the preceding calendar day or the EA entry window.
2. **Current session (secondary):** high/low of completed bars in the same session
   strictly earlier than the signal. No previous bar means unavailable, never
   use the signal or completed full-session extreme as a substitute.
3. **Previous week (secondary):** high/low of the preceding completed Monday-
   Friday trading-date week. No rolling five-session window and no current week.

Do not cluster these levels, apply break invalidation, flip their roles, pool
sources into a nearest-level rule, optimize ages, or combine the two questions.
Record the first bar attaining each selected extreme within its source window,
the last included source bar, elapsed hours, and trading-session age. Equal
retests do not reset formation age. Age summaries are descriptive, not filters.

Map bars to the roll ledger using only the latest roll on/before that date.
Exclude a source if any of its bars belong to a different contract from the
signal. A mixed-contract previous week is unavailable in full, not truncated.
Keep missing-history and roll exclusions explicit. Report source-specific
coverage and repeat comparisons on the identical trades eligible for all three
sources. No cross-source claim may be based solely on different populations.

## Measurements

Let E = signal high (planned buy-stop), S = signal low (initial stop), R = E-S.
The saved EA uses those prices; require a red signal and R > 0.

- **Q6 support distance:** d = (S - reference low) / R, signed.
- **Q7 overhead room:** u = (reference high - E) / R, signed.
- For both, descriptive groups are `<0`, `=0`, `(0,0.5]`, `(0.5,1]`, `>1`.
  Negative support distance means the signal low is below the reference, not
  necessarily that the signal crossed it; separately record entirely below,
  spanning, or entirely above the level. Negative overhead room means the
  planned entry is above the reference high. Zero means exact contact.
- Q6 planned contrast: **far support** d > 0.5 versus **near support**
  0 <= d <= 0.5. Negative distances are reported separately, not mixed into far.
  Predefined neighboring thresholds: 0.25 and 0.75R.
- Q7 planned contrast: **limited room** 0 < u <= 1 versus **more room** u > 1.
  Negative and zero distances are separate descriptive groups, not silently
  assigned unlimited room. Predefined neighboring thresholds: 0.5 and 1.5R.

## Reporting and decision rule

Report count, share, total net dollars, net dollar PF, average net dollars, and
average net R for each source/distance group in both periods and every year.
Also report the planned contrast and its difference in mean net R, with a
descriptive 95% interval from 2,000 calendar-month block bootstrap resamples
(seed 20261003, retain months with no trades in a group). These intervals are
not adjusted for multiple comparisons and are not a significance gate.

Only previous-session Q6 far-support and Q7 limited-room are primary filter
candidates. A primary candidate proceeds to a separately frozen full MT5 rerun
only if all of these hold:

- Its net PF is below 1 in both periods, and its comparison group's PF is above
  1 in both periods, with at least 200 trades per group per period.
- The same is true at at least one predefined neighboring threshold.
- The primary-threshold result also passes on the common three-source sample.

Current-session/week results and other descriptive bins do not become winning
filters by post-hoc selection. Retain any reverse-direction findings as
exploratory observations. If no primary candidate qualifies, close this first
screen with no filter; do not search new cutoffs in response to the result.
Subset sums are not a simulated filtered strategy: skipping trades changes
subsequent position availability. Full MT5 validation is necessary before
claiming improved strategy profit or drawdown. Execution remains the accepted
OHLC screen; no generated-tick runs are part of this study.
