# RTL mirrored: sell limit at the red candle's high

2026-11-16. User-requested exploratory experiment. Rules fixed before any result was seen.

## The idea

RTL buys when price breaks the high of a red M30 candle. This experiment takes the other
side at the same price: a sell limit at that high, a stop one candle range above it, and a
profit target at the candle's low or lower.

## Rule

- **Signal:** a completed red M30 candle (`close < open`) while flat, inside RTL's entry
  windows (01:00-23:30). The same candles RTL uses.
- **Entry:** sell limit at the candle's high. RTL's buy stop sits at the same price.
- **Stop:** high + (high - low). One candle range above the entry, as RTL's stop is one
  range below.
- **Exit, primary reading (RTL's exit mirrored):** after the first M30 bar that closes at
  or below the low (entry - 1 range), buy back at the first quote of the next bar. Profit
  is the low "at least", as RTL's is +1R at least.
- **Exit, second reading:** a resting take profit exactly at the low. Run as a separate
  arm, because "take profit at least the low" can be read either way.
- **Order lifetime:** RTL's. A new red candle replaces the resting order, a green or doji
  candle leaves it, a bar outside the windows cancels it, the 23:30 flatten (with the
  fallback and the early-close calendar) cancels it and closes any position. One position
  at a time. An order whose price is not above the market is not placed, as RTL's buy
  stop is rejected at or below the market.
- No filters, no offsets, no tuning.

## Runs

Native MT5 Strategy Tester, new EA `RTL_red_high_sell_limit`
(`mt5/experts/shorts/RTL_red_high_sell_limit.cs`), `MNQcontDTBNT20102026_2`, M30, 1-minute
OHLC, 2010-06-07 to 2026-10-15, one MNQ ($2 per point), $1.05 per round turn charged
afterwards. Two arms: `ExitMode = 0` (bar close) and `ExitMode = 1` (resting take profit).

Every native trade is also rebuilt from the raw minutes with separate Python code
(`python/rtl_sell_limit_fade.py`) and compared with MT5 trade by trade.

## What is reported

Periods by order-submission session: 2010-15, 2016-19, 2020-September 2026. Trades, net
dollars, win rate, profit factor, mean R before and after costs, drawdown, how the trades
ended, and RTL on the same history next to it.

## Expectation, written before the run

A loss. RTL's long earns about +0.07 to +0.09 R per trade before costs on NQ, and this
trade is its counterparty at the entry. In the saved trade paths, 49 of 100 RTL trades
touch +1R, which is this trade's stop, and 44 are stopped at the low without touching it.
With a take profit at the low that is roughly 44 wins against 49 losses of equal size,
about -0.05 R per trade before costs. The bar-close exit should do worse than that: it
keeps a short open after the low is touched, and for RTL's long "holding on" was the
better side at every level measured.

This is history already studied many times and MT5's assumed price order inside each
minute. It cannot confirm an edge; it can show whether the idea is worth a second look.
No baseline or live setting changes.

## Amendment, 2026-11-16, after the first build's two runs

The rule above says no order is placed when its price is not above the market. The first
EA build left that to MT5, as RTL does. MT5 rejects a buy stop at or below the market, but
it accepts a sell limit there and fills it at once at the market price: 324 of 24,424
trades in the bar-close arm. Those runs had been seen (both arms lose) when this was found.

The rule is not changed. The EA now applies it itself (`AllowOrderAtMarket = false`, the
default), and all runs were repeated with the final build. MT5's own handling
(`AllowOrderAtMarket = true`) is kept as two extra arms, reported as a side check; they must
reproduce the first build's ledgers byte for byte.
