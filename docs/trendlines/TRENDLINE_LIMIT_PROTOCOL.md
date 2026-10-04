# Q20: does a buy limit resting on a rising trendline beat a matched dip-buy?

**Frozen 2026-10-05** with the user's approval of the draft as written, before
any Q20 outcome or count was computed. All of
2010-2026 and the Q6-Q19 results have been seen, so this is exploratory.

**The question (the user's proposal, 2026-10-05).** Rest a buy limit on an
intact rising trendline and buy the touch, whatever the candle colour. Is
entering *at the line* better than the same dip-buy at a price with no line?

This is a **new entry mechanic, not an RTL filter.** There is no red signal,
no buy stop and no attribution to baseline fills. The RTL baseline is shown as
context only. The decision comparison is a matched control (below). The Q18
stopping rule does not apply: Q18 passed. The external reason is the user's
different mechanic.

**Prior evidence, stated up front:**

- **[Q14](TRENDLINE_SUPPORT_RESULTS.md):** red signals at the same lines were
  worse than every other signal (PF 1.029 / 0.950). It tested a buy stop at the
  red high, not a fill at the line, so it does not answer Q20. But its
  descriptive labels are not encouraging:
  - slice-throughs more than 0.5 x ATR below an intact line were common
    (331 / 514 fills, against 565 / 821 candidates);
  - "wick reaches the line" had PF 1.025 / 0.800;
  - "undercut 0.25-0.5 x ATR" had PF 1.080 / 0.714.
- **[Limit-only screen](../LIMIT_ONLY_RESULTS.md):** resting buy limits inside
  the red candle lost money in every year 2016-2019. Fills were dominated by
  price going through the level, and costs took a large share of the small risk.

Expectations are low. The test is cheap because the Q14 line code and the
stand-alone EA setup already exist.

## Lines: the frozen Q14 definition, evaluated at every bar

Nothing is re-parameterized. The definitions are those of
[TRENDLINE_PROTOCOL.md](TRENDLINE_PROTOCOL.md) and
[`python/trendline_support.py`](../../python/trendline_support.py). The only
change is the evaluation point. Instead of at a red signal bar, the lines are
evaluated at the **open of every M30 bar t**, using closed bars only.

- **A(t)** = mean of the 14 true ranges of bars t-14..t-1, same contract.
  **D = 0.5 x A(t).** Both are used for every distance and slope at bar t.
- **Window:** the session of bar t plus the 5 previous sessions, all in one
  contract (otherwise no order: roll / missing history).
- **Swing lows:** N = 5, and known only once pivot + 5 <= t - 1.
- **Anchors:** consecutive higher lows, j - i >= 10 bars. The line rises
  >= 0.02 x A per bar and is **valid** (no low between the anchors more than D
  below it).
- **Intact:** no close in bars j+1..t-1 more than D below the line.
- **Departed:** a close in bars j+1..t-1 at least A above the line.
- **Line value V(t):** the line projected to bar t, one step per M30 bar
  (gaps count as one bar, as on an MT5 chart).

## Entry, stop and exit (fixed)

**One trade per episode (arming).** A line is *armed* once it has departed. A
fill consumes the episode. The line re-arms only after a later close at least
A above it (Q14's retest logic: no repeated trades on one touch). Unfilled bars
do not consume the episode.

**Order placement, at the open of every eligible bar t:**

- *Eligible* means:
  - the strategy has no position;
  - bar t opens in an enabled baseline window (01:00-23:30, the same 24 hourly
    windows);
  - bar t opens before the flatten or early close.
- *Line choice:* among the armed, intact, valid lines, take the one with the
  **highest V(t) below the current ask** (the nearest line under price). Ties
  go to the later j, then the later i, as in Q14.
- **Buy limit = V(t) rounded down to the 0.25 tick.**
  - If the ask is at or below that price (the bar opened under the line), no
    order is placed for that bar.
  - No market-order substitute is used.
- **Stop = limit - 0.5 x A(t), rounded down to the tick.** R = limit - stop.
- *Re-pricing:* at the next bar's open, the unfilled order is cancelled and
  re-placed (or modified) at the new V and stop. The line may change if
  another one is now nearest. The order price is constant **within** a bar, so
  it sits at most one bar's slope below the continuously drawn line.

**After a fill:**

- The stop is fixed at the filled order's stop.
- **Exit:** a market exit after the first M30 bar that closes >= entry + 1R,
  as in the baseline. The session/early-close flatten and the fallback stay on.
- A fill and the stop in the same bar are resolved by one-minute OHLC.

**Everything else:**

- one contract, $2/point, $1.05 per round trip modelled in Python;
- net R = net / (2 x R in points);
- symbol `MNQcontDTBNT20102026_2`, M30, one-minute OHLC (Model = 1);
- full history 2010-06-07 to 2026-07-14 in one run, split afterwards.

**Periods:**

- decision periods: 2016-01-01 to 2020-01-01 and 2020-01-02 to 2026-07-14;
- 2010-06-07 to 2016-01-01 is reported separately (see the reading rule).

## The control: is the line price special?

The comparison isolates the **line's price**, not the uptrend around it.

**Control C1 (regime-matched, the decision comparison):**

- *Bars:* the same as the primary. Bar t is eligible only when an armed,
  intact line exists under price, as for the primary. The flat / window rules
  are the same.
- *Price:* instead of V(t), the limit is placed at **open(t) - delta x A(t)**,
  with delta drawn at random.
- *Delta distribution:* delta is drawn from the primary's own placement
  distance distribution, delta = (open - V) / A over all primary placements in
  the classify-only run. It is drawn with replacement, within the same session
  segment (01:00-10:00, 10:00-23:00, 23:00-23:30), seed 20261005. Python writes
  the draw table and the EA reads it. No outcome is used.
- *Stop, exit, rounding, costs:* identical (stop = limit - 0.5 x A).
- *Arming:* after a fill at P, C1 re-arms after a close >= P + A, mirroring the
  primary's re-departure.

**Control C2 (unrestricted dip-buy, context only):**

- the same as C1, but on every eligible bar, whether or not any line exists;
- run at the primary setting only;
- it shows how much any NQ intraday dip-buy with this stop and exit earns.

The **RTL baseline** (PF 1.106 / 1.107, mean R -0.004 / +0.060) is also shown
as context, never as a decision basis.

## Sensitivities (fixed now, each with its own C1)

1. **Trade-through fill:** the limit is placed 1 tick below the rounded V(t),
   and the stop is moved by the same tick. A bare touch of the line then does
   not fill. One-minute OHLC fills limits on touch, and that is optimistic
   exactly for the trades that bounce at the line.
2. **Stop 0.25 x A.**
3. **Stop 1.0 x A.**

These are not run: other line definitions (two weeks, N = 3), other targets,
and first-retest-only. Nothing is searched.

## Reading rule (fixed now)

The primary **passes** if, in both decision periods:

- PF > 1;
- mean net R > 0;
- mean net R > C1's mean net R;
- mean R beats C1 in >= 7 of 11 years (years with >= 10 trades in each);
- the trade-through sensitivity also has PF > 1 and beats its own C1 in mean R;
- both stop sensitivities beat their own C1 in mean R (the same direction).

A primary with fewer than 200 trades in either period is reported but cannot
pass.

**Also reported, required in the answer but not part of the rule:**

- 2010-2015 (Q18 was negative there);
- the week-block bootstrap (5,000 resamples, seed 20261005) of primary minus
  C1 mean R and PF, as descriptive 95% intervals.

**What a pass means:** buying at the line beats buying a random dip in the
same uptrend regime, under one-minute OHLC. It adopts nothing. Combining it
with RTL, sizing and live use would each need their own protocol.
Generated-tick execution is not a criterion (the user's 2026-10-05 decision).
The trade-through sensitivity is this study's execution check.

## Reported per run, period and year

- **Volume:** orders placed, fills and fill rate; trades, net $, PF, mean and
  median net R, win %.
- **Exits:** the exit mix (target / stop / flatten); stops on the fill bar;
  fills where the same minute bar also hit the stop (OHLC-ambiguous).
- **Risk:** closed-trade max drawdown, the longest losing run, the largest
  trade's share of net; average R in points and cost as a share of R.

**Descriptive labels (primary only, never candidates):**

- first retest versus later;
- slope (A per bar);
- anchor separation;
- bars since anchor j;
- fill-bar colour at close (red / green);
- time-of-day segment;
- how far price went below the line on the fill bar, in A.

## Verification (before any trading run)

- **Unit tests** for the per-bar order price:
  - confirmation timing;
  - intact / departed / arming / re-arm after a fill;
  - nearest-line choice;
  - the ask-at-or-below-the-limit skip;
  - rounding;
  - window / roll.
- **Classify-only EA run** (orders never sent). It logs, for every bar: the
  chosen line, anchors, V, A, the limit and stop, and the arm state ignoring
  fills.
  - A Python implementation built on the Q14 functions must reproduce every
    logged bar: 0 mismatches in line choice, anchors and limit price (up to
    CSV rounding).
  - Any mismatch is fixed and documented first.
- **Re-arm check** in the trading run: Python replays the fills and confirms
  that every order respected the episode rule.
- **Execution audit:**
  - every entry is a buy limit at the logged price, with the logged stop;
  - no fill above the limit;
  - one position at a time;
  - nothing held over the flatten;
  - no order rejections or modification errors;
  - MT5 reports reconcile with the ledgers.
- Hashes of the inputs, code and this protocol.

## Planned files and outputs

- Line and price code: `python/trendline_limit.py` (built on
  `trendline_support.py`); tests in `python/test_trendline_limit.py`.
- EA:
  - the baseline research EA with its order placement replaced by
    `mt5/experts/trendline_limit.mqh` (rising lines, mirroring
    `resistance_gate.mqh`, plus the limit / control modes);
  - generated by `python/prepare_trendline_limit.py`, which refuses to
    overwrite a completed run.
- Checks and analysis: `python/verify_trendline_limit.py`,
  `python/analyze_trendline_limit.py`.
- Outputs: `Reports/trendlines/trendline_limit_<date>/`. Results doc:
  `docs/trendlines/TRENDLINE_LIMIT_RESULTS.md`.

## What was seen while drafting

Nothing beyond the published Q14 and limit-only results quoted above. Before
freezing, counts may be shown from the classify-only run, with no P&L or R:
armed bars, placements, the delta distribution, and the touch frequency.
