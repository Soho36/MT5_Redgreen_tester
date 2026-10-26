# RTL on weekly candles with a session flatten: protocol

Fixed 2026-10-27, before any weekly result was computed. User request: trade RTL
on weekly candles, but flatten at every session close and reopen at the next
session open, because an MT5 W1 run holds positions overnight and over weekends,
which a prop account cannot do. Exploratory, descriptive: no adoption rule.

## Strategy (unchanged RTL rules on W1 bars)

- Weekly bar = Monday-Friday session dates (session clock Chicago + 8 h), built
  from the NQ continuous 1-minute source. Same as MT5 W1 bars on this data.
- Signal: a red week (close < open). At the first session of the next week, a
  buy stop at the week's high, stop at its low (MinRedRun 1, no cap, no filters).
  A green or doji week leaves an existing pending order in place, as in the EA.
  A new red week replaces it. An order that would sit at or below the opening
  price is rejected, as MT5 rejects it.
- Exit: the original bar-close target: after a week closes at or above
  entry + 1R, the trade ends. Otherwise the stop at the red week's low.
- While a trade is open, new red weeks place no order (one trade at a time). A
  week in which the target ends the trade places no order (EA order of checks).

## Session flatten and reopen (the new part)

- Live only from the first bar of each session to the flatten cutoff: 23:30, or
  the early-close calendar time. At the cutoff bar's open, close the position and
  suspend the pending order. If a session has no bar at or after its cutoff, close
  at that session's last bar.
- Next session open: if a trade is alive, buy again at the first bar's open, same
  stop and target reference. If that open is at or below the stop, the trade is
  over (stopped while flat; no extra loss). A suspended pending order fills at the
  open when the open is at or above its level (the breakout happened while flat).
- Nothing that happens while flat (23:30-01:00) counts: only live hours trigger
  fills and stops.
- Stops and buy stops inside a session fill at their level, or at the bar's
  opening price when a 1-minute bar opens beyond it.
- Target reference: the first fill price and its risk (fill - stop). R per trade =
  net dollars / first-fill risk dollars. Each daily piece is a separate round turn.

## Prices and rolls

Profit is always measured in raw prices: every daily piece starts and ends inside
one session, so in one contract. **Primary signal levels are roll-adjusted**
(ratio back-adjustment at each contract switch, as in the weekly-gate study),
because a recent NQ roll gap can be a large part of a weekly range. Raw levels
(what MT5 uses on the raw symbol) are a sensitivity.

## Variants

| Name | Overnight | Levels | Fills |
|---|---|---|---|
| **W1 flatten (primary)** | flat at cutoff, reopen at next open | roll-adjusted | level, or worse open |
| W1 flatten raw | same | raw | same |
| W1 hold | held through nights and weekends | roll-adjusted, +$1.05 per roll crossed | level, or worse gap open |
| W1 hold MT5-style | held | raw | MT5 tester: always at the level |
| M30 baseline | existing MT5 ledger, uncapped, RR 1 | raw | MT5 |

Costs $1.05 per round turn (each daily piece is one); stress +$1 and +$2 per
round turn, as in earlier studies. One MNQ contract, $2 per point.

## Eras and reporting

Trades by first-fill date: 2016-19 and 2020-26 (through 2026-09-30, the last
complete session); 2010-15 reference only (different session hours). Report
trades, pieces per trade, win %, gross and net R per trade, total net R, net $,
PF, max drawdown on closed pieces ($ at one contract and in R at equal risk per
trade), median risk $, yearly net, and a trade bootstrap interval of mean net R.
Count reopen gap stops, flat-time breakout fills and rejected orders. Show what
flattening changes: same trades held versus flattened.

## Validation before reading results

1. Run the simulator in M30 mode with the EA's own flatten logic on raw prices.
   It must reproduce the MT5 M30 RTL ledger (25,833 trades) trade by trade:
   submission, levels, fill and exit times (to the minute) and prices.
2. Run the MT5 tester on W1 (UseFlattenEnd = false, UseTradeWindow = false) and
   reproduce it with the W1 hold MT5-style variant trade by trade.
3. Unit tests for the flatten/reopen rules on synthetic bars; an independent
   check of every primary piece against the 1-minute data.

Any mismatch is explained before results are interpreted.
