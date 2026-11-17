# Daily RTL with monthly VWAP: frozen screening protocol

2026-11-18. User requests daily candles as RTL signals and a calendar month
as the VWAP session. User explicitly chooses holding positions across month-end:
reset VWAP only, no session flattening.

Two native MT5 arms: daily RTL control, and daily RTL rejecting red-candle
candidates whose close is strictly below monthly VWAP minus daily A20.
Buy stop at the red day's high, stop at its low, original close-confirmed
1R exit evaluated at the next daily bar's first quote, one position at a time.
New red signals replace pending orders; a gated red cancels the old order and
withholds its replacement. Green/doji bars preserve pending orders.
Open positions keep normal exits; month changes alone close/cancel nothing.
UseTradeWindow=false, UseFlattenEnd=false, MaxRedRun=0, MinLocation=0.

VWAP: original M1 HLC3 weighted by actual exchange volume, accumulated from
the calendar month's first source session through the completed signal day.
A20: simple mean of the last 20 completed daily true ranges INCLUDING the
signal day, needing 21 daily bars for previous-close history. Strict below
blocks; equality passes. Preserve the old EA's session-reset convention:
on a month's first trading day, the prior month's signal label is unknown
and passes; warm-up unknowns pass. Other missing/inconsistent labels fail.
A20 does not reset monthly. Features are precomputed from original volume
rather than MT5's synthetic tester volumes, and available only after close.

Frozen RTL timeframe source; MNQcontDTBNT20261114, D1, one MNQ, 1-minute OHLC,
2010-06-07 through 2026-11-14 exclusive. $1.05 per completed trade.
Log the tester's actual first callback and reproduce its startup in replay.
Raw continuous prices/native level fills: screen only. Overnight gaps and
contract roll jumps can affect held trades. Count roll-crossing positions;
this is not an executable rolled-futures PnL model.

Report exit-date cohorts: 2010-15, 2016-19, 2020-Sep2026, Oct1-Nov13 2026,
2016-Nov13, full history; annual rows. Trades, net dollars, mean gross/net R,
win rate, PF, closed-trade DD, floating-equity DD, extra $1 cost per trade.
Interval equity DD includes carried-in positions: show net equity change
separately from exit-cohort realized profit. Log candidate known/blocked
counts and differences/replacement trades. No tuning.
This tests daily RTL, not a daily regime gate around M30 RTL. A negative
result does not logically rule out the latter.

Freeze data/source/settings/protocol hashes before runs. Independently check
monthly minute VWAP and daily A20, every candidate decision, and full minute
trade replay (submission, fill/exit minutes, prices, stops, exit reasons).
Reconcile reports, ledgers, tester totals, and native full gross equity DD.
Test resets, causality, warm-up, strict inequality, pending replacement,
green persistence and positions held across month boundaries. Preserve old
studies and all baseline/live settings.

