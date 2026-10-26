# Weekly RTL controls: plain long and random timing (protocol)

Fixed 2026-10-27, before any control result. User request after the
[weekly flatten study](RESULTS.md): "run the plain-long control for weekly RTL: same
holding with a market entry instead of the buy stop, plus random timing."
Exploratory and descriptive; no adoption rule. Primary RTL figures are the existing
`W1 flatten` ledger (roll-adjusted levels, flattened every session).

## Controls

All use the primary setup: weekly bars, live 01:00 to the cutoff, flatten at the cutoff
and buy back at the next open with the same stop and target, roll-adjusted levels,
profit in raw prices, $1.05 per round turn, one MNQ, exit after a week closes at or
above entry + 1R, one trade at a time, no entry in a week whose open ended a trade by
target (EA order of checks).

1. **Plain long (primary control).** The weekly form of the repo's market-buy control
   (signal-colour study, `SignalMode = 3`): at the first session of every week while no
   trade is open, buy at that session's first open; stop = entry - the previous week's
   range. No candle pattern.
2. **Red week, market entry.** Same signals and stop as RTL (a red week; stop at its
   low), but buy at the next week's first open instead of the buy stop above its high.
   No trade if that open is at or below the red week's low.
3. **Random timing of the same holding.** Take RTL's own in-market sessions (every session
   with a piece in `W1 flatten`) and shift that whole pattern in time: every circular
   shift by at least 60 sessions, inside each era. Each shifted session earns being long
   one MNQ from the session's first open to its flatten, minus $1.05. RTL's unshifted
   pattern is scored the same way (whole sessions), so this tests its timing at session
   level; RTL's real ledger differs by entering and stopping inside sessions.

## Reading rules (fixed now)

- The buy stop adds to the plain long if RTL minus control 1 in mean gross R per trade is
  positive in 2016-19 and 2020-26 and the 2020-26 95% interval (independent trade
  bootstraps, 10,000 draws) is above zero. Same reading for RTL minus control 2.
- RTL's timing beats random timing if its session pattern earns more than at least 95%
  of the shifts in both eras.
- Net R, net dollars, drawdown, worst day and yearly figures are reported for context.

## Validation

- The market-entry code path must reproduce, trade by trade, a fresh MT5 W1 tester run
  of the frozen signal-colour EA (`RTL_signal.mq5`, `SignalMode = 3`, flatten and
  trade windows off), with the simulator's hold / raw / MT5-fill / ask-entry settings.
  Market-entry ledgers can miss a trade stopped on the next tick: check the count against
  MT5's own trade statistics.
- Unit tests for both market-entry controls; an independent recomputation of the
  random-timing shifts.

Eras by first-fill date for trades, by session date for the random-timing test:
2016-19, 2020-26 (to 2026-09-30); 2010-15 reference only.
