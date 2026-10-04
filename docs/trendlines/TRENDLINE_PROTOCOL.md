# Q14: do red signals at rising trendline support beat every other signal?

**Frozen 2026-10-04** with the user's approval of the draft as written, before
any Q14 outcome was computed. All of 2016-2026 and the Q6-Q13 level results have already been
examined, so this study is exploratory. It is kept separate from the horizontal
[level study](../levels/README.md) but asks the same two questions and uses the
same population, exit, comparisons and follow-up gate.

The old [`Trendline_rejection.cs`](../../mt5/Trendline_rejection.cs) supplied
the idea: uptrend support lines through rising swing lows, faded on a closed bar.
It is not reused. It traded a separate fixed-RR system, counted touches per
bar (so the bars next to an anchor counted as confirmation) and judged a line's
whole history with today's ATR.

**Level source in this study:** rising lines through two confirmed M30 swing
lows in a rolling **one-week** window. Horizontal levels are not used. Every
Q14 table must name the window and N.

## Questions

1. **Trendline support (primary, the Q11 question):** is a red signal that
   revisits an intact rising line from above a better RTL trade than every
   other signal?
2. **Broad trendline contact (secondary, the Q12 question):** does any contact
   with an unbroken rising line identify better trades, whatever the departure,
   depth or candle side?

## Baseline and population (unchanged from Q11/Q12)

- RTL research baseline: MaxRedRun=3, MinLocation=0, all enabled entry windows,
  one contract, buy stop at the red M30 high, stop at its low.
- **Original exit:** first bar closing >= entry + 1R, session/calendar flatten.
  $2/point, $1.05 round trip. No fixed TP.
- Periods: 2016-01-01 to 2020-01-01 and 2020-01-02 to 2026-07-14, exclusive ends.
- Reuse Q10's original-exit census and verify its manifest hashes first:
  52,070 potential signals (19,624 / 32,446), 35,632 attempts, 14,968 fills.
  No new MT5 run. M30 reference and roll ledger as in Q11.

## Definitions

Code: [`python/trendline_support.py`](../../python/trendline_support.py).

- **A** = mean of the 14 M30 true ranges before the signal bar, same contract
  (Q11). **D = 0.5 x A**. A and D are taken at the signal and used for every
  distance and slope in that signal's classification.
- **Swing lows:** Q11's N = 5 pivots (strictly below the 5 lows before, at or
  below the 5 after, same contract). A pivot is known only after bar i+5 has
  closed, at or before the signal's open.
- **Window:** both anchors lie in the signal's session or the 5 previous
  sessions, all in the signal's contract (otherwise unavailable: roll).
- **Anchors (consecutive higher lows):** for each known pivot j, anchor i is
  the latest earlier known pivot with a lower low. Every swing low between them
  is at or above low[j], so each j has at most one line. The pair is dropped if
  j - i < 10 bars. It is not replaced by an older low.
- **Line:** through (i, low[i]) and (j, low[j]), projected per M30 bar
  (overnight/weekend gaps count as one bar, as on an MT5 chart). The value at
  the signal bar s is V.
- **Minimum slope:** the line rises >= 0.02 x A per bar (about 1 x A per
  session). Flatter lines are horizontal levels, left to the level study.
- **Valid:** no low between the anchors is more than D below the line.
- **State, using only bars after j and before s:** *broken* = a close more than
  D below the line; *departed* = a close at least A above it.
- **Contact:** signal low <= V + D and signal high >= V - D.

## Groups (mutually exclusive, in this order)

1. **Unavailable:** missing history, roll, or invalid A.
2. **Trendline support (primary candidate):** contacts a valid, unbroken,
   departed line, and signal low >= V - D.
3. **Slice-through:** contacts such a line but the low is more than D below it.
4. **Broken contact:** contacts only broken lines.
5. **Not-departed contact:** contacts only unbroken lines that price never left
   by 1 x A.
6. **No contact.**

The primary complement is every other signal (groups 1 and 3-6). Also report the
available-only complement and each group. **Broad contact** (question 2) is
groups 2, 3 and 5. Broken lines are excluded: unlike a horizontal level, a
broken rising line's projection has no remaining meaning as a price.

**Descriptive labels inside group 2 (never separate candidates).** When several
lines qualify, describe the one nearest the signal low.

- *First retest versus later:* earlier retests are returns to V + D after a
  close >= A above the line, since anchor j or the previous retest.
- *Slope:* in A per bar.
- *Anchor separation.*
- *Bars since anchor j.*
- *Wick reaches V.*
- *Opens below V.*
- *Undercut depth:* (V - low) / A.
- *Number of qualifying lines.*
- *Overlap with Q11 horizontal support revisits:* a confluence count only.

## Sensitivities (fixed now)

The two-week window (10 previous sessions) with N = 5, and one week with N = 3.
Every other definition stays the same. No search over separation, slope, D,
departure or window.

## Outcomes, uncertainty and the follow-up gate (Q11 rule)

For each setting, period, year and group, report:

- potential signals, attempts and fills, and fill conversion;
- net $, net PF, average/median net R and win rate;
- exit reasons, R quantiles and drawdown attribution.

Partitions and net sums must reconcile with the baseline exactly. Primary
contrasts are candidate minus every other signal, in PF and average net R, with
2,000 calendar-month block resamples (seed 20261004) and descriptive 95%
intervals. Broad contact gets the same contrasts and also its contrast with
available no-contact signals.

The primary candidate merits a separately specified full MT5 filter experiment
only if all of the following hold:

- candidate and complement each have >= 200 fills in both periods;
- candidate PF > 1;
- candidate PF and average R exceed the complement in both periods;
- average R is better in >= 7 of 11 eligible years (>= 10 fills per group);
- both sensitivities point the same way in both periods.

Broad contact uses the same gate. If the gate fails, keep the result and do not
search other definitions. If it passes, still adopt nothing: only a full MT5
rerun can measure a filtered strategy. A Q13-style concentration audit follows
only if a lead appears.

## What was seen while drafting (no outcomes)

Classification counts only, from 5,000 sampled signals; no P&L or R was
computed. With all anchor pairs and no slope floor, 19% of signals touched an
intact line, through a fan of about 3 overlapping lines each, and near-flat
lines duplicated horizontal levels. The consecutive-higher-lows rule and the
slope floor were adopted after viewing the example charts. Under the draft
definition, about 9.5% of signals are candidates in both periods (roughly
550 / 900 fills) and 23% are broken-line contacts. Retests were redefined to
require a prior 1 x A departure, so bars beside the anchor do not count.

## Verification and outputs

- Unit tests: [`python/test_trendline_support.py`](../../python/test_trendline_support.py)
  cover projection, pairing, slope, validity, break/departure, retests,
  confirmation timing, contact boundaries and window/roll.
- An independent recomputation for a random sample of signals, written
  without importing the module.
- Hashes of inputs, code and this protocol.
- Outputs: `Reports/trendlines/trendline_support_<date>/`. Results doc:
  `docs/trendlines/TRENDLINE_SUPPORT_RESULTS.md`. Example charts:
  `python/plot_trendline_example.py`.
- This attributes existing fills; it does not simulate a filter. Execution uses
  one-minute OHLC only, with no generated ticks.
