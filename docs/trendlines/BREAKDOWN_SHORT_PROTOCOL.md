# Q21: short the breakdown of a rising trendline

**Frozen 2026-10-06** at the user's request ("write protocol and freeze it"),
before any Q21 outcome or count was computed. All of 2010-2026 and the Q6-Q20
results have been seen, so this is exploratory.

**The question (the user's proposal, 2026-10-06).** Draw the same rising lines
as Q14/Q20. When a **red** M30 candle closes below a line, sell short at that
candle's low with a sell stop, stop loss at its high. Does this short make
money, and does it beat shorting an ordinary red candle in the same uptrend
regime?

This is an **independent question**, not a fix for Q20 and not an RTL filter.
It is the first short-side study in this project. The entry is the short
mirror of the **GG** continuation idea (a stop order through the signal
candle's extreme in the candle's own direction), not of the RTL baseline (which
buys a red candle's high). Neither GG nor its mirror has been studied in Q1-Q20.

**Prior evidence, stated up front:**

- **[Q20](TRENDLINE_LIMIT_RESULTS.md):** a buy limit at the same lines lost
  money (PF 0.773 / 0.969). 45% of its trades stopped out in the fill bar.
  That is mostly a limit-fill selection effect inside one bar. It does not
  show what follows a bar that *closes* below the line. Reversing Q20 naively
  would not pay either: its gross was about -$940 (2016-19) and +$780 (2020-26),
  so a mirror short of the same trades is negative after $1.05 costs in both
  periods.
- **NQ drifts up.** Every edge found so far is long. The short has to beat
  that drift, so the decision comparison is a short-side control, not PF > 1
  alone.

Expectations are moderate at best. The test is cheap because the Q14/Q20 line
code and the stand-alone EA setup already exist.

## Lines: the frozen Q14 definition

Nothing is re-parameterized. The definitions are those of
[TRENDLINE_PROTOCOL.md](TRENDLINE_PROTOCOL.md) as evaluated per bar in
[TRENDLINE_LIMIT_PROTOCOL.md](TRENDLINE_LIMIT_PROTOCOL.md)
([`trendline_limit.armed_lines`](../../python/trendline_limit.py)).
They are evaluated **at the open of the breakdown candidate bar s**, from bars
before s only:

- **A(s)** = mean of the 14 true ranges of bars s-14..s-1, same contract.
  **D = 0.5 x A(s).**
- **Window:** the session of bar s plus the 5 previous sessions, one contract.
- **Swing lows:** N = 5, known only once pivot + 5 <= s - 1.
- **Anchors:** consecutive higher lows, j - i >= 10 bars, rising >= 0.02 x A
  per bar, **valid** (no low between the anchors more than D below the line).
- **Armed (Q14/Q20):** intact (no close in j+1..s-1 more than D below the line)
  and departed (a close in j+1..s-1 at least A above it).
- **Line value V(k):** projected one step per M30 bar (gaps count as one bar).

So the line was fully drawn on the chart before bar s opened.

## The breakdown signal (primary)

A line is **live** at s if it is armed and **no close since its first
departure** (the first close >= V + A after anchor j) has been below the line,
up to bar s-1. Closes slightly below the line before the first departure are
allowed (Q14's intact rule still caps them at D).

**Bar s breaks the line** if close(s) < V(s), the user's "any close below
the line". Because the line is live, the previous close was at or above it.
That close is the line's first break after departure. The line is then
**spent**: it can never signal again, whether or not a trade follows, so every
line gives at most one signal.

**Signal:** bar s breaks at least one live line **and is red** (close < open).
A green or doji bar that breaks a line gives no trade, and the line is still
spent. If bar s breaks several lines, the reported line is the one with the
highest V(s) (ties: later j, then later i, as in Q14/Q20). The order is the
same whichever line is reported.

## Entry, stop and exit (fixed)

**At the open of bar t = s + 1** (the next M30 bar in the data):

- *Eligible* means: the strategy is flat; bar t opens in an enabled baseline
  window (01:00-23:30, the same 24 windows) and before the flatten or early
  close; bars s and t are in the same contract.
- **Sell stop = low(s); stop loss = high(s).** R = high(s) - low(s) in points.
  Bar prices are on the tick, so there is no rounding.
- If the bid at t's open is already at or below low(s), the price has gapped
  through the entry. **No order is placed**, and no market order is
  substituted.
- **Order life: bar t only.** An unfilled order is cancelled at the open of
  bar t + 1 (or by the window exit / flatten, whichever comes first).

**After a fill:**

- **Exit:** a market exit (buy to cover) after the first M30 bar that closes
  <= entry - 1R. This is the baseline's bar-close target mirrored for a short,
  with RiskReward = 1.0 in every regime (the corrected build; the Q20 audit's
  BullRR/BearRR input bug must not reach this EA).
- The stop is fixed at high(s). Session/early-close flatten and the fallback
  stay on. One position at a time.
- Fill, stop and target inside one bar are resolved by one-minute OHLC.

**Execution facts carried over from Q20:** M30 bars are bid prices, and the
tester quotes ask = bid + 1 tick. A sell stop triggers when the bid reaches
low(s). The stop loss triggers when the ask reaches high(s), i.e. when the bid
is 1 tick below it. Covering at the target pays the ask. These are reported,
not corrected.

**Everything else:**

- one contract, $2/point, $1.05 per round trip modelled in Python;
- net R = net / (2 x R in points);
- symbol `MNQcontDTBNT20102026_2`, M30, one-minute OHLC (Model = 1);
- full history 2010-06-07 to 2026-07-14 in one run, split afterwards.

**Periods:**

- decision periods: 2016-01-01 to 2020-01-01 and 2020-01-02 to 2026-07-14;
- 2010-06-07 to 2016-01-01 is reported separately.

## Controls: is the break special?

**Control C1 (regime-matched, the decision comparison):** the same order,
stop, exit and eligibility, on **every red bar s at which at least one armed
(Q14/Q20) line exists**, whether or not s breaks it. It answers: in the same
rising-line regime, is shorting the low of a red candle that breaks the line
better than shorting the low of any red candle? The primary's signals are a
subset of C1's bars. C1 has no lines to spend, so it signals on every
qualifying red bar.

**Control C2 (unrestricted, context only):** the same on **every red bar**,
with or without lines. It shows what the plain red-candle sell stop (the
short mirror of GG) earns on NQ.

The **RTL baseline** (PF 1.106 / 1.107, mean R -0.004 / +0.060) is context
only, never a decision basis.

## Sensitivity (fixed now)

**S1, deeper break:** the break needs close(s) < V(s) - D, Q14's own "broken"
threshold. A line stays live until its first close more than D below it after
departure (closes within D below are allowed). Everything else is unchanged,
including the red-bar rule and C1, which does not depend on the threshold.

Not run: other line definitions (two weeks, N = 3), other targets or stops,
longer order lives, a trade-through entry. Nothing is searched.

## Reading rule (fixed now)

The primary **passes** if, in both decision periods:

- PF > 1;
- mean net R > 0;
- mean net R > C1's mean net R;
- mean R beats C1 in >= 7 of 11 years (2016-2026; years with >= 10 trades
  in each);
- S1 also has PF > 1 and mean net R > C1's.

A primary with fewer than 200 trades in either period is reported but cannot
pass.

**Also reported, required in the answer but not part of the rule:**

- 2010-2015;
- C2 and the RTL baseline as context;
- the week-block bootstrap (5,000 resamples, seed 20261006) of primary minus
  C1 mean R and PF, as descriptive 95% intervals.

**What a pass means:** shorting a red candle that breaks a rising line beats
shorting any red candle in the same regime, under one-minute OHLC. It adopts
nothing. Combining it with RTL (opposite direction, shared position limit),
sizing and live use would each need their own protocol. Generated-tick
execution is not a criterion (the user's 2026-10-05 decision).

## Reported per run, period and year

- **Volume:** signals, gap skips, orders, fills and fill rate; trades, net $,
  PF, mean and median net R, win %.
- **Exits:** the exit mix (target / stop / flatten); stops in the fill bar;
  fills where the same minute bar also reached the stop (OHLC-ambiguous).
- **Risk:** closed-trade max drawdown, the longest losing run, the largest
  trade's share of net; average R in points and cost as a share of R.

**Descriptive labels (primary only, never candidates):**

- break depth (V(s) - close(s)) / A;
- bar range / A, and where the close sits in the bar;
- opened above the line (open(s) >= V(s)) or not;
- slope (A per bar), anchor separation, bars since anchor j, bars since the
  first departure, retests before the break;
- number of lines broken by bar s;
- time-of-day segment.

## Verification (before any trading run)

- **Unit tests** for the per-bar signal: confirmation timing; armed / live /
  spent lines (a close below spends a line; a close below before departure
  does not); the red-bar rule; the gap skip; the S1 threshold; the reported
  line among several; window / roll, including a roll between s and t.
- **Classify-only EA runs** (orders never sent) at the primary and S1
  thresholds. They log, for every eligible bar t: bar s, status, the reported
  line, anchors, V(s), A(s), entry and stop, line counts (armed / live /
  broken), and whether s is red. C1 and C2 eligibility can be read from the
  same log.
  - A Python implementation built on the Q14/Q20 functions must reproduce
    every logged bar: 0 mismatches in status, line choice, anchors, entry,
    stop and counts (line values and A up to CSV rounding).
  - The logged bars must be exactly the eligible set.
  - Any mismatch is fixed and documented first.
- **Trading runs** are replayed in Python from closed bars and the run's own
  fills: every order matches the classification, and one-signal-per-line
  holds.
- **Execution audit:** every entry is a sell stop at low(s) with stop high(s);
  every fill at or below low(s); orders live one bar only; one position at a time;
  nothing held over the flatten; no send or cancel errors; MT5 reports
  reconcile with the ledgers.
- Hashes of the inputs, code and this protocol.

## Planned files and outputs

- Signal code: `python/trendline_breakdown.py` (built on `trendline_limit.py`
  and `trendline_support.py`); tests in `python/test_trendline_breakdown.py`.
- EA: the baseline research EA with its entry replaced by
  `mt5/experts/trendline_breakdown.mqh`. Classify-only first; the trading build
  adds the short side (sell stop, mirrored stop/target/flatten handling and
  the ledger) and is checked against this log before it runs.
- Generated by `python/prepare_trendline_breakdown.py`, which refuses to
  overwrite a completed run. Checks: `python/verify_trendline_breakdown.py`.
- Outputs: `Reports/trendlines/trendline_breakdown_<date>/`. Results doc:
  `docs/trendlines/BREAKDOWN_SHORT_RESULTS.md`.

## What was seen while drafting

Nothing beyond the published Q14 and Q20 results quoted above. Before the
trading runs, counts may be shown from the classify-only runs, with no P&L or
R: signals, gap skips, lines spent, and C1/C2 bar counts.
