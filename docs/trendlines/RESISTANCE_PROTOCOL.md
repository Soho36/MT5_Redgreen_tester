# Q15: do red signals at falling trendline resistance beat every other signal?

**Frozen 2026-10-04** with the user's approval of the draft as written, before
any Q15 outcome was computed. This study is exploratory: all data and the Q6-Q14 results have
been seen, including Q14's negative result for rising support lines.

**Idea.** RTL buys a stop at a red candle's high. When that red candle has just
pushed up into a falling resistance line from below, the buy stop sits at or
near the line, so a fill is a break of the line from below. Does that break
make a better RTL trade than every other signal?

**Line source in this study:** falling lines through two confirmed M30 swing
**highs** in a rolling one-week window. Every Q15 table must name the window
and N.

## Same as Q14 (unchanged, see the [Q14 protocol](TRENDLINE_PROTOCOL.md))

- **Population and exit:** RTL baseline population and original exit, $1.05
  cost and periods. Reuse Q10's hash-verified census: 52,070 signals, 35,632
  attempts and 14,968 fills. No new MT5 run.
- **Units:** A = lagged ATR(14) at the signal; D = 0.5 x A.
- **Window:** one week (current session plus 5 previous), roll exclusion.
- **Lines:** 10-bar minimum anchor separation, slope floor 0.02 x A per bar.
  Projection per M30 bar.
- **Comparisons:** groups ordering, every-other-signal complement, bootstrap
  (2,000 calendar-month blocks, seed 20261004).
- **Gate and sensitivities:** two weeks N = 5 and one week N = 3; no search
  beyond them.

## What changes: everything is mirrored to highs

Code: [`python/trendline_resistance.py`](../../python/trendline_resistance.py).
It negates prices (high <-> -low, open/close -> -open/-close) and applies the
frozen Q14 code; true range is unchanged.

- **Swing highs:** high strictly above the 5 highs before, at or above the 5
  after; same contract; known once bar i+5 has closed before the signal opens.
- **Anchors (consecutive lower highs):** for each known swing high j, anchor i
  is the latest earlier known swing high with a higher high. Dropped if
  j - i < 10, not replaced.
- **Line:** through (i, high[i]) and (j, high[j]), falling at least 0.02 x A
  per bar. V is its value at the signal bar.
- **Valid:** no high between the anchors more than D above the line.
- **State (bars after j, before the signal):** *broken* = a close more than D
  above the line; *departed* = a close at least A below it.
- **Contact:** signal high >= V - D and signal low <= V + D.

## Groups (mutually exclusive, in this order)

1. **Unavailable:** missing history, roll, invalid A.
2. **Resistance test (primary candidate):** contacts a valid, unbroken,
   departed falling line from below, and signal high <= V + D.
3. **Poke-through:** contacts such a line, but the high is more than D above it.
4. **Broken contact:** contacts only broken lines (price returning to a line it
   already broke upward).
5. **Not-departed contact:** contacts unbroken lines that price never left by
   1 x A.
6. **No contact.**

**Broad contact** (the Q12 question) is groups 2, 3 and 5: any contact with an
unbroken falling line.

**Descriptive labels inside group 2 (never candidates).** Describe the line
nearest the signal high when several qualify.

- *Entry at or above V* (buy stop on the line, so a fill is a break) *versus
  entry below V*.
- *(signal high - V) / A.*
- *First retest versus later.*
- *Slope.*
- *Anchor separation.*
- *Bars since anchor j.*
- *Opens above V.*
- *Number of qualifying lines.*
- *Overlap with Q14 trendline-support candidates* (the signal sits on both a
  rising and a falling line).

## Outcomes and follow-up gate

As Q14. Report per setting, period, year and group, with exact partition
reconciliation. Fill conversion matters especially here, because a fill is the
break.

Primary contrast: resistance test minus every other signal (PF and average net
R). The broad contrast is also run against available no-contact signals.

The Q11 gate applies to the primary and to broad contact:

- >= 200 fills per group and period;
- candidate PF > 1;
- PF and average R better than the complement in both periods;
- average R better in >= 7 of 11 years;
- both sensitivities point the same way.

Passing only justifies specifying a full MT5 rerun. Failing ends the search; no
other N, window, slope or separation.

## What was seen while drafting (no outcomes)

Classification counts only, from 5,000 sampled signals; no P&L or R. One week,
N = 5:

- about 9% of signals are resistance tests in both periods (roughly 540 / 860
  fills at the average fill rate);
- 24% are broken-line contacts;
- 12% are broad contact.

Example charts show lines through descending swing highs with candidates
pressing into them from below. The definitions are Q14's, mirrored; nothing was
tuned for Q15.

## Verification and outputs

- Unit tests: [`python/test_trendline_resistance.py`](../../python/test_trendline_resistance.py).
  They build falling-line scenarios directly from highs, so they also test the
  mirroring.
- An independent re-derivation on raw highs, without the mirror or the study
  code. Hashes of inputs, code and this protocol.
- Outputs: `Reports/trendlines/trendline_resistance_<date>/`; results doc
  `docs/trendlines/TRENDLINE_RESISTANCE_RESULTS.md`. Charts:
  `python plot_trendline_example.py START END --resistance`.
- This attributes existing fills; it does not simulate a filter. One-minute OHLC
  only.
