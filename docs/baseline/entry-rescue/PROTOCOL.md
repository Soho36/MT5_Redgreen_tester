# Rejected-entry rescue: protocol

Fixed 2026-11-13, before any rescue result was computed. Exploratory and
descriptive, with no adoption rule fixed in advance; the user decides.

## Question

On 2026-11-13 at 01:30 a live GG entry (buy stop-limit at the green candle's high,
28495) was rejected: the new bar's first trade was already at or above the
level ("stop price must be above trade price"). The MT5 EA and the minute engine
reject the same case (`bar1 high <= first price of the new bar`), so the measured
trade lists never contain these signals. The user reports it happens about once
or twice a week, mostly by a few ticks between bars rather than at session gaps.

Proposal: instead of skipping, place a **buy limit at the same level** (the
signal high, same stop at the signal low, same target rule) and cancel it if it
has not filled within **1 minute**.

## Engine

`rtl_weekly_engine.simulate_m30_ea` (MT5 M30 EA emulation, 1-minute OHLC tick
model, MT5 tester fills at the level), copied into the study with one change:
where the engine counts a rejection, a rescue variant places the limit instead.

- Placed at the first tick of the new M30 bar, as the stop would have been.
- Fills at the first later tick at or below the level, at the level. It is never
  checked on the tick it was placed (that tick is at or above the level).
- Lives for W minutes of clock time from placement (W = 1 is the proposal); it is
  removed earlier by everything that removes a pending stop (new signal, blocked
  window, flatten, fallback, gate skip). Once filled it is an ordinary trade:
  same stop, same bar-close R:R target, same flatten.
- With W = none the copy must reproduce the engine's trades exactly.

Sensitivities: W = 2, 5 and 25 minutes (25 = NinjaTrader's existing expiry for a
triggered but unfilled entry).

## Population

Both live strategies, uncapped, all 01:00-23:30 windows, R:R 1, 1 MNQ:

- RTL (red signal) and GG (green signal);
- VWAP gate **on (primary, as live)** and off. Gate decisions come from the
  MT5 EA's own label file (`Reports/gg_vwap_ea_20261030/rtl_vwap_replay_20261026_features.csv`)
  with the EA's lookup: newest label available at the order bar, known only for
  that bar's session date, skip when known and close < VWAP - 1 x A20.

Data: NQ continuous 1-minute, 2010-06-07 to 2026-09-30 (end of the label file).

## Validation (before results are read)

1. W = none equals `simulate_m30_ea` exactly for all four strategy/gate runs.
2. GG gate off and on reproduce the MT5 ledgers in
   `Reports/gg_vwap_ea_20261030` (entry times) through 2026-09-30.

## Reporting

Eras 2010-15 (reference), 2016-19, 2020-26. Costs $1.05 per round turn; net R =
net dollars / (fill - stop) dollars.

- Rejections: count per year and per week (2025-26), overshoot in ticks (first
  price minus the level), and whether the bar opened a session (first minute after
  a gap of more than 5 minutes).
- Rescue: fill rate; rescued trades' count, mean net R (bootstrap 95% interval,
  10,000 draws), win rate, net dollars; compared with the strategy's normal trades.
  Split by overshoot (1-2 ticks, 3-8, more) and session open vs intrabar.
- Whole strategy, variant vs baseline: trades, net dollars, mean net R, and
  baseline trades displaced (a rescued trade can occupy the position when a later
  signal arrives).
