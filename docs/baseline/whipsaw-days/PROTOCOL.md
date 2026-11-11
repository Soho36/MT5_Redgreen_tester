# Whipsaw sessions: do they come before a large move?

Frozen 2026-11-11, before any outcome was computed. An event study on NQ M30
bars. No MT5 run, no strategy or EA change.

## Question

User's idea: a session of failed breakouts in both directions (a "whipsaw") is
often followed by a major move. Two traps can make this look true when it is not.

- **Memory.** A frustrating session followed by a big move is remembered; the
  same session followed by nothing is forgotten. So every such session since
  2010 is found by one fixed rule and counted.
- **Large days follow large days.** A whipsaw session is a large session, and
  after any large session the next one tends to be larger than usual, whatever
  its shape. So "whipsaw days against all days" proves nothing. The fair test is
  "whipsaw days against other days that were just as large": does the *shape*
  of the day add anything to its *size*?

## Data

NQ M30 bars from the checked 1-minute cache
(`python/verify_rtl_failed_breakout_short.py::load_quote_index`; saved copy
`Reports/gg_large_candle_20261109/signal_features.csv`), raw prices, research
clock (Chicago + 8 h). A session is the bars from 01:00 of one calendar date.
Sessions with fewer than 20 bars are dropped first (2025-11-28 and the
unfinished 2026-10-01), so "previous" and "next" always mean the neighbouring
kept session.

Samples, by the date of the event session: main eras 2016-19 and 2020 to
2026-09-30, and the two pooled. 2010-15 (from 2010-07-06) is secondary and
never changes the reading.

## Event, fixed

Everything here is known at the session's close; no later session is read.

- **ATR20** = mean true range of the 20 previous sessions (true range = the
  session's high-low range stretched to the previous close). It is known
  before the session starts and is the yardstick for "a normal day".
- **Path.** A bar that closes at or above its open is walked open, low, high,
  close; any other bar open, high, low, close.
- **Zigzag.** The first swing is confirmed when price is a threshold or more
  away from the lowest or highest price seen so far in the session. After
  that, a swing the other way is confirmed each time price reverses by the
  threshold or more from the extreme of the current swing. The count is the
  number of confirmed swings: a one-way day has 1, a V-shaped day 2, an
  up-down-up day 3.
- **Primary event (whipsaw):** 3 or more swings at 0.75 x ATR20.
- **Neighbours, fixed with it:** 4 or more swings at 0.5 x ATR20 (looser), and
  3 or more swings at 1.0 x ATR20 (stricter).
- **Secondary definition:** an outside day (high above the previous session's
  high and low below its low) that closes back inside the previous session's
  range, ends included.

Counts, made without reading any later session: 243, 549, 63 and 233 of 4,180
sessions (2010-07-06 to 2026-09-30). Primary by era: 69 (2010-15), 60
(2016-19), 114 (2020-26). The analysis must reproduce these before it computes
an outcome. Code: `python/whipsaw_days.py`, frozen with this file.

## Outcomes

For the next session, and for the next three sessions taken together (first
open to third close; if the contract rolls inside the three, the jump from the
old contract's last close to the new contract's first open is taken out). All
are divided by the event session's ATR20, so 1.0 means one normal day's range.

1. **Primary: size of the move** = absolute open-to-close move.
2. Range (high minus low).
3. Share of trend days: absolute open-to-close move at least 0.6 of the range.
4. Signed open-to-close move (does it lean up or down).

Also, for the next session: net dollars and net R of normal GG and normal RTL,
summed over the session's trades (zero when there are none), one MNQ contract,
$1.05 costs. Sources: the saved native ledgers
`Reports/gg_size_cap_20261111/ggcap_20261111_base_control_trades.csv` and
`Reports/rtl_gg_exclude16_20261101/ex16_20261101_rtl_base_all_trades.csv`, rows
with sample = primary, so 2016 to September 2026 only.

## Control, the heart of the study

Size of a day = its own high-low range divided by ATR20.

1. **Matched comparison.** All 4,180 sessions are sorted by size and cut into
   ten equal groups. Each event session is compared with the non-event sessions
   of the same year and the same size group. Result = the average, over event
   sessions, of its outcome minus the mean outcome of its controls. Event
   sessions without a control are left out and counted.
2. **Size-corrected comparison.** Known before any outcome: the top size group
   is wide (1.65 to 5.65 normal ranges), and inside their groups whipsaw days
   are still larger than their controls (2016-26: 1.81 against 1.64; all other
   days average 0.97). That leftover tilts comparison 1 in favour of the idea.
   So the same comparison is also run as a regression: the outcome on the event
   flag and the day's exact size, with a separate level for every
   year-and-size group. The coefficient of the flag is the difference that
   remains between two days of the same year, the same group and the same size.

95% intervals: whole calendar months of the sample are redrawn with
replacement 5,000 times (seed 20261111) and both comparisons recomputed; the
interval runs from the 2.5th to the 97.5th percentile. Months and not days,
because neighbouring days are not independent of each other.

Everything is reported twice: for all sessions, and without scheduled news,
which leaves out every session that is, or is followed by, a CPI, payroll or
FOMC session (`data/calendars/us_major_news_times_2010_2026.csv`). Known
beforehand: 16% of whipsaw days are such sessions against 12% of other days;
the session after is one equally often (12% and 12%).

## Reading, fixed in advance

Judged on the primary event, the primary outcome, the next session, all
sessions. The idea is **supported** only if all four hold:

1. the matched difference is above zero in 2016-19 and in 2020-26;
2. the pooled 2016-26 matched difference has its whole 95% interval above zero;
3. the pooled 2016-26 size-corrected difference has its whole 95% interval
   above zero;
4. both neighbours have a pooled matched difference above zero.

Otherwise the report says that a whipsaw day says no more about the next
session than any equally large day. The three-session outcomes, the other
measures, the secondary definition, the news-free run, 2010-15 and the
strategy ledgers are reported next to this; none of them can rescue a failed
reading. If the reading passes but the news-free pooled matched difference is
not above zero, it is reported as an effect of scheduled news.

If supported, the unchanged rule is applied to ES, YM and RTY (minute files in
`python/analyze_rtl_vwap_cross.py::INSTRUMENTS`; RTY from 2018) and each is
judged by points 1 to 3. They share dates and moves with NQ, so they are a
check for an NQ-only accident and not independent evidence.

Supported would mean "worth watching on forward data". Whatever the result:
no strategy, EA or live setting changes, and no new threshold or definition is
tried after the results are seen.

## Limits, stated beforehand

- This history has been studied many times, and the rule was written after one
  remembered session. That session is later than the data, so it is not in
  the sample.
- About 174 whipsaw sessions in the main eras: only a sizeable effect can be
  seen. "No difference found" means "no large difference".
- Prices are raw. On the 66 contract-roll dates the true range includes the
  jump between contracts, which lifts ATR20 by 0.2% on average (4.7% at most);
  with roll-adjusted levels the four counts would be 244, 554, 63 and 232.
- M30 bars hide the order of moves inside a bar; the bar path is a convention.
- A statistic about sessions, not a trading rule and no claim about fills.

## Checks and outputs

The hashes of this file and of `python/whipsaw_days.py` are written to
`freeze.json` before any outcome code runs; the analysis stops if either has
changed. Focused tests cover the zigzag, the ATR20 look-back, the outside-day
flag, the matching, the regression and the month resampling.
`Reports/whipsaw_days_20261111/` (not in git) holds the session table and
draws; `summary.csv`, one chart and `RESULTS.md` go in this folder.
