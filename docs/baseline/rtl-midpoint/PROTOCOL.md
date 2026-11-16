# RTL entry at the red candle midpoint

2026-11-16. User-requested exploratory experiment; final rules fixed before
inspecting any profit results. User confirmed high-low midpoint, including
wicks, and BUY STOPS ONLY: skip if the price is already above the midpoint.

## Rules

- Signal: completed red M30 candle, exactly as ordinary RTL.
- Entry: `(high + low) / 2`, rounded UP to the next tradable 0.25 tick when
  halfway between ticks. Place a buy stop only when this price is strictly
  above the current ask. Otherwise cancel the previous order and skip.
  No buy limits, no high-breakout prerequisite. A signal closing at its low
  remains valid; the stop becomes active only after the buy stop fills.
- Stop: unchanged, at the red signal candle's low.
- Exit: unchanged RTL bar-close exit. After an M30 candle closes at or above
  `actual_fill + 1 * (actual_fill - original_stop)`, sell at the next bar's
  first quote. An exact midpoint makes this threshold the signal high;
  tick rounding can put it one tick higher. A touch alone is not an exit.
- All other rules unchanged: red replaces pending order, green/doji leaves it;
  one position; 01:00-23:30 entry windows; 23:30 flatten, fallback and early-close
  calendar; one MNQ; no additional filter, run cap, or sizing change.

## Runs and evaluation

Separate tester-only `RTL_midpoint` and native RTL control, built from frozen
`Reports/timeframe_baseline_20261015/RTL_timeframe.mq5` and its baseline INI.
M30, 1-minute OHLC, `MNQcontDTBNT20102026_2`, 2010-06-07 to 2026-10-15.
Report 2010-15, 2016-19, 2020-September 2026 and pooled 2016-26, $2/point,
$1.05 per round turn. Net dollars, mean net/gross R on actual entry risk,
win rate, profit factor, daily closed-balance drawdown, annual results,
and another $1/trade cost sensitivity. Daily drawdown is not equity drawdown.
Independently replay raw minutes and compare every native trade after tester
startup. Control must reproduce the existing native RTL ledger byte for byte.

Hypothesis: lower entry and smaller target improve results. Competing
possibility: losing high-breakout confirmation and paying larger costs per
unit of risk. Evaluate both eras and mean net R, not win rate alone.
No parameter search, baseline/live changes, or adoption decision.
Previously examined history and assumed intraminute paths are exploratory.

## Preparation history (before inspecting outcomes)

An initial three-job batch had been launched while the order-type reply was
in transit. It also included buy limits, and its protective check incorrectly
skipped buy-stop signals closing at their low. Ten boundary tests exposed that
unwanted restriction. The complete initial batch is preserved under
`Reports/rtl_midpoint_20261116/initial_build`; none of its outcomes are used.
The final source removes buy limits and the extra restriction, and reruns
both control and requested experiment. The archived protocol records the
initial assumptions. This final protocol supersedes them.
