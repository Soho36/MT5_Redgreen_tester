# M30 RTL with a persistent daily monthly-VWAP gate

2026-11-18. Fixed before outcomes. Original M30 RTL is the control; add only
a daily regime gate in the other arm. No existing M30 VWAP filter.

Use the verified daily/monthly feature file from the daily RTL experiment:
monthly cumulative M1 HLC3 weighted by original exchange volume, and simple
mean of 20 completed DAILY true ranges including the signal day. Same raw
continuous MNQ history through 2026-11-13. No threshold tuning.

After EVERY completed D1 candle, regardless of colour:
close < monthly VWAP - daily A20 disables new entries;
close > that line enables entries; equality preserves state.
Use each completed day's own VWAP, including the final day of a month.
State persists across month-end; resetting VWAP does NOT automatically enable
trading. Evaluate the new month's first day's value only after that day closes.
Unknown warm-up leaves state unchanged; start enabled. No previous-red breakout.
Apply changes on the first next available quote, never within the signal day.
Cancel pending orders while halted. Existing positions retain all normal
M30 RTL exits. Daily/early-close flattening and all baseline windows stay intact.

Two native MT5 tester arms, M30, MNQcontDTBNT20261114, one MNQ, RR1,
uncapped red runs, $1.05 per completed trade, 1-minute OHLC execution.
2010-06-07 through 2026-11-14 exclusive; source and settings hashed before runs.
Use original-volume precomputed features, not tester synthetic tick volume.
Raw roll construction affects daily features; no rolled-futures/live claim.

Compare 2010-15, 2016-19, 2020-Sep2026, Oct1-Nov13, pooled 2016-Sep2026,
2016-Nov13, plus annual rows. Net, trades, mean net/gross R, profit factor,
daily balance and intraday equity DD; extra $1/trade cost.
Count halted sessions and switches; retained/skipped/replacement trades.
Compare with uniform baseline exposure scaling using holding-time fraction.
Paired weekly-block bootstrap for profit difference: 10000 draws, seed20261118.
Descriptive, already-studied history; no independent forward validation.

Verify every daily feature and state, all native report/ledger totals,
control against saved M30 baseline, full independent minute replay,
native gross equity DD then external cost deduction. Test colours irrelevant,
strict boundary, persistence/reset, warm-up, causal next-day activation;
reuse tested pending-cancellation/open-position handling. No live changes.

