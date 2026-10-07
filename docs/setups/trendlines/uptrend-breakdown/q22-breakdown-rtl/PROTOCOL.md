# Q22: are RTL long signals at or after a rising-line break different?

**Frozen 2026-10-06** at the user's choice of framing (two-sided; break bar
plus the next 10 bars), before any Q22 outcome or count was computed. All of
2010-2026 and the Q6-Q21 results have been seen, so this is exploratory.

**The question (the user's choice, 2026-10-06, after Q21).** Q21 showed that
shorting the break of a rising Q14 line loses: the break does not follow
through. Can the break instead be used on the **long** side, with the drift?
Two directions are tested with one frozen gate each:

- **worse:** RTL signals at or just after a break are worse than every other
  signal, so a **skip filter** would help;
- **better:** they are better, a **failed-breakdown long** (the RTL buy stop at
  the high of the candle that broke the line, or soon after).

This is an RTL attribution study like Q14: existing baseline fills, no new MT5
run for the gate.

**Prior evidence, stated up front:**

- **[Q14](../../uptrend-bounce-long/q14-trendline-support/RESULTS.md):** RTL signals touching only a
  *Q14-broken* line (a close more than D below it earlier) had PF 1.084 / 1.265
  (1,238 / 1,923 fills), against 1.167 / 1.112 for signals with no line
  contact. That is a different definition (contact with a line broken any time
  earlier, by more than D). Q14's rule forbade promoting it.
- **[Q21](../q21-breakdown-short/RESULTS.md):** a sell stop at the low of a red
  breakdown candle loses even before costs (PF 0.893 / 0.916). The candle's
  low is not followed through. The RTL long buys the same candle's **high**.
  How those long trades did has not been computed.
- So the "better" direction has more support than the "worse" one, but neither
  is established.

## Baseline and population (unchanged from Q14)

- RTL research baseline: MaxRedRun = 3, MinLocation = 0, all enabled entry
  windows, one contract, buy stop at the red M30 high, stop at its low.
- **Original exit:** first bar closing >= entry + 1R, session/calendar
  flatten. $2/point, $1.05 round trip.
- Periods: 2016-01-01 to 2020-01-01 and 2020-01-02 to 2026-07-14.
- Reuse Q10's original-exit census and verify its manifest hashes first:
  52,070 potential signals (19,624 / 32,446), 35,632 attempts, 14,968 fills.
  No new MT5 run.

## Definitions

**Break events** are Q21's, computed by the verified Q21 code
([`trendline_breakdown.py`](../../../../../python/trendline_breakdown.py), EA = Python on
every bar):

- frozen Q14 lines evaluated at the open of bar k from bars before k;
- a line is live if, since its first departure, no close has been below it;
- bar k **breaks** a line if close(k) < V(k) and the line is live and not spent;
- every bar of the history is evaluated in order, and a break spends the line
  (one break per line);
- **any colour** counts as a break event here.

For an RTL signal with signal bar s (the red candle):

1. **Breakdown signal (group A, primary):** bar s itself breaks at least one
   line. Because RTL signals are red, these are exactly Q21's red breakdown
   candles; the RTL order is the buy stop at their high.
2. **Post-break signal (group B, secondary):** not in A, and some bar k with
   1 <= s - k <= 10 (the 10 M30 bars before s, same contract as s) breaks a
   line.
3. **Every other signal:** the rest, including signals where lines are
   unavailable (window, roll, ATR).

Groups A and B are each compared with **every other signal** (all signals
not in that group). This is the complement a filter would keep, and the
population a stand-alone long would be compared with.

**Sensitivity (fixed now): S1**, Q21's deeper break. A break needs
close(k) < V(k) - 0.5 x A(k), and a line stays live until that happens. Groups A
and B are re-formed with S1 break events. Nothing else is varied; the 10-bar
window is not searched.

## Outcomes, uncertainty and the two-sided gate

For each break definition (primary, S1), period, year and group, report:

- potential signals, attempts and fills, and fill conversion;
- net $, net PF, average / median net R and win rate;
- exit reasons and R quantiles.

Partitions and net sums must reconcile with the baseline exactly. Contrasts
are group minus every other signal, in PF and average net R, with Q11's
2,000 calendar-month block resamples (seed 20261004) as descriptive 95%
intervals.

**"Better" gate (a failed-breakdown long candidate).** Group A merits a
separately specified MT5 experiment only if all hold:

- group and complement each have >= 200 fills in both periods;
- group PF > 1 in both periods;
- group PF and average R exceed the complement in both periods;
- average R is better in >= 7 of 11 eligible years (>= 10 fills per group);
- S1 group A also has PF and average R above its complement in both periods.

**"Worse" gate (a skip-filter candidate).** Group A merits a separately
specified MT5 filter experiment only if all hold:

- group and complement each have >= 200 fills in both periods;
- group PF and average R are below the complement in both periods;
- average R is worse in >= 7 of 11 eligible years (>= 10 fills per group);
- S1 group A also has PF and average R below its complement in both periods.

Group B uses the same two gates, as a secondary question. At most one
direction can pass for a group. If no gate passes, keep the result and do not
search other windows or definitions. If a gate passes, still adopt nothing: a
filter or a stand-alone long must be measured by its own MT5 run. Concentration
(Q13/Q16-style) is audited only if a lead appears.

## Descriptive labels (group A, never candidates)

- break depth (V(s) - close(s)) / A and bar range / A;
- opened above the line or not;
- number of lines broken;
- time-of-day segment;
- daily regime at the signal (Q10 bull / bear / neutral).

## Verification and outputs

- Unit tests for the group assignment: A versus B; the 10-bar window edges
  (1 and 10 bars before s count, 0 and 11 do not); same contract; S1.
- Cross-check: for every census signal whose submission bar is in the
  verified Q21 classify-only log, membership of A must equal that log's
  "red break" status for the same bar s (0 mismatches), for primary and S1.
- Partitions reconcile with the Q10 totals; hashes of inputs, code and this
  protocol.
- Code: `python/analyze_breakdown_rtl.py`, tests in
  `python/test_breakdown_rtl.py`. Outputs: `Reports/trendlines/breakdown_rtl_<date>/`.
  Results doc: `docs/setups/trendlines/uptrend-breakdown/q22-breakdown-rtl/RESULTS.md`.
- This attributes existing fills; it does not simulate a filter or a
  stand-alone long. One-minute OHLC execution limits remain.

## What was seen while drafting

Only the Q14 and Q21 results quoted above. No Q22 group count or outcome was
computed. Group counts may be shown before outcomes.
