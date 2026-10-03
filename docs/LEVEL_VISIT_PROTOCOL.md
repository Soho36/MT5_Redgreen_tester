# Q11: do red signals at intact one-week M30 swing-low support beat every other signal?

Specified 2026-10-04 with the user, **before computing any Q11 classification or
outcome**. All history and the Q6–Q10 results have already been examined, so
this remains exploratory. Motivation: Q10's original-exit screen, where
previous-week low interactions beat every other signal in both periods
(PF 1.707 / 1.451) but with only 72 / 137 fills. Q11 asks whether intact
swing-low support from the recent week shows the same, with a usable sample.

**Level source used in this study:** confirmed **M30 swing lows** whose pivot
bar lies in a rolling **one-week** window (primary) or **two-week** window
(reported alongside). Session and calendar-week extremes are not used here.
Every Q11 table must name its source and window.

## Baseline and population

- Unchanged RTL research baseline: MaxRedRun=3, MinLocation=0, range filter off,
  all enabled entry windows, one contract, buy stop at the red M30 high,
  protective stop at its low, existing pending-order replacement/cancellation.
- **Original exit:** bar-close-qualified market exit at >=1R, with session and
  calendar flattening. Fixed TP is not used. $2/point, $1.05 round-trip cost.
- Periods: 2016-01-01 to 2020-01-01 and 2020-01-02 to 2026-07-14, exclusive ends.
- Reuse Q10's original-exit populations and verify their hashes first: the
  potential-signal census (19,624 / 32,446), the 35,632 baseline order attempts
  and the 14,968 fills. No new MT5 run. Use the rebuilt M30 reference from the
  `MNQcontDTBNT20102026_2` minute source, verified against the Q8/Q10 copy.

## Volatility unit

A = simple mean of the 14 M30 true ranges **before** the signal bar (signal
excluded), as in Q9, resetting history at contract rolls. A is unavailable with
fewer than 14 prior same-contract bars or if A = 0. **D = 0.5 x A**, taken at the
signal and used for every distance in that signal's classification.

## Swing lows

- Bar i is a swing low with **N = 5** if its low is strictly below each of the
  5 preceding lows and at or below each of the 5 following lows (ties go to the
  earlier bar). Neighbours are consecutive bars of the M30 reference, including
  across overnight/weekend gaps, and must belong to the same contract.
- A swing low is **known** only after bar i+5 has closed, and only if that close
  is at or before the signal bar's open. The signal and later bars never create
  or confirm a level.
- Why N = 5: a low that held for 2.5 hours on each side. N = 2–3 marks minor lows
  every hour or two; with zones of +/-0.5 x A, most red candles would then
  "interact" with something, turning the test back into a location test that
  earlier studies already found negative. **N = 3 is reported as a sensitivity.**

## Window and roll exclusion

- **One week (primary):** pivot bar in the signal's current trading session or the
  previous 5 completed trading sessions. **Two weeks (reported alongside):**
  previous 10 completed sessions. Trading sessions follow the Q6/Q7 full-session
  convention in the rebuilt symbol's clock, not the EA's entry windows.
- The whole window, the bars needed to confirm pivots and the signal must be
  in the same contract; otherwise the signal is **unavailable (roll)**. No
  back-adjustment. Missing history is unavailable with its reason recorded.

## Merging nearby lows into levels

At each signal, sort the window's known swing lows by price. Starting from the
lowest, a level collects consecutive pivots while (highest - lowest) <= D;
the next pivot starts a new level. Level price **L = lowest member low**; zone
Z = [L - D, L + D]. Record member count and first/last member pivot times.

## Level state before the signal

Let t0 be the bar of the level's most recent member pivot. Using only M30 bars
after t0 and before the signal:

- **Broken:** any close below L - D.
- **Departed:** any close at or above L + A (price clearly moved away; this is
  what makes a later return a revisit from above).

If the level is not broken, every close away from the zone since t0 was above
it, so an unbroken, departed level was approached **from above**. Shallow
undercuts (false breakdowns, closes between L - D and L) do not break it.

## Signal classification

A signal **contacts** a level if signal low <= L + D and signal high >= L - D.
Candle shape and the side of L on which it opens or closes do not matter.
Mutually exclusive groups, in this order:

1. **Unavailable:** roll, missing history or invalid A; keep the reason.
2. **Support revisit (primary candidate):** contacts at least one unbroken,
   departed level.
3. **Broken-level contact:** contacts only broken levels (a test from below,
   i.e. possible resistance, not support).
4. **Not-departed contact:** contacts only unbroken levels that price never left
   by 1 x A (still the same visit/consolidation near the pivot).
5. **No contact:** available, no level contacted (including no swing lows).

Primary complement: **every other signal** (groups 1, 3, 4, 5). Also report the
available-only complement (3–5) and each group alone.

Descriptive labels inside group 2, never separate candidates: wick reaches L
(low <= L) versus near miss (low > L); signal opens below L; signal closes more
than D below L (breaks on the signal); undercut depth (L - low) / A; closes
below L since t0; level age in hours and sessions; member count; signal R / A;
number of qualifying levels. When several levels qualify, describe the one
nearest the signal low. Report overlap with Q10's previous-week interactions.

## Outcomes and uncertainty

As in Q10, for each window, N, period, year and group: potential signals,
attempts, fills, conversion, net $, net PF, average/median net R, net win rate,
exit reasons, R quantiles and average signal range. Partitions and net sums must
reconcile exactly with the baseline. Subset drawdown is attribution only.

Primary differences: candidate minus every other signal in average net R and net
PF, 2,000 calendar-month block resamples, seed 20261004, empty months retained.
Descriptive 95% intervals, unadjusted for multiple comparisons.

## Follow-up rule (fixed now)

The primary candidate (one week, N = 5, group 2) merits a separately specified
full MT5 filter experiment only if: candidate and complement each have >=200
fills in both periods; candidate PF > 1; candidate PF and average net R exceed
the complement in both periods; and average-R superiority holds in >=7 of the 11
yearly slices (>=10 fills in each group for a year to count). In addition, the
two-week window and N = 3 must point the same way in both periods (point
estimates only; they need not pass the gates).

If the rule fails, keep the finding and do not search other N, D, departure or
window values. If it passes, this screen still adopts nothing: removing trades
changes position availability, so only a full rerun with the level logic in the
EA can measure a filtered strategy. That EA and its run need their own protocol.

## Verification and limits

- Unit tests: pivot confirmation timing and ties, no signal/future bars in the
  level map, window and roll boundaries, merging, broken/departed states,
  contact boundaries at exact L +/- D, and A lag/roll reset.
- Independent recomputation of a random sample of signals' level maps and
  classifications; full partition and profit reconciliation; input, script and
  protocol hashes saved in `provenance.json`.
- Outputs: `Reports/levels/level_visit_20261004/`. Results doc:
  `docs/levels/LEVEL_VISIT_RESULTS.md`.
- Swing lows only: resistance turned support (role reversal), resistance above
  entry and older levels are out of scope. One-minute OHLC execution limits
  remain; no generated-tick runs.

## Amendment 2026-10-04: no deep slice-through, before any outcome

Made with the user after viewing example charts of the classification
(`python/plot_level_visit_example.py`), **before any Q11 outcome was computed**.
The charts showed red candles slicing far through a level counted as support
revisits, which is not the rejection the study is about.

- A support revisit now also requires **signal low >= L - D**: the signal may
  undercut the level by at most 0.5 x ATR (false breakdowns still count).
- A signal that contacts an unbroken, departed level but whose low is more than
  D below it goes to a new group, **slice-through**, placed after group 2 in the
  order above. It is part of the "every other signal" complement and reported.
- Contacts with broken levels (price returning from below) stay a separate
  reported group. Whether a long signal at a level approached from below has an
  edge is a separate inbox question, not part of the Q11 candidate.

Nothing else changes: N, D, departure, windows, gates and outputs as above.
