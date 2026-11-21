# First minute of 15:30 news

Frozen 2026-11-22 before results. Original continuous NQ history with MNQ
valuation, one contract, $2/point, $1.05 external round-trip cost. Full native
MT5 M1 OHLC replay, same source as preceding news studies, through September
2026. CPI and payrolls whose scheduled research time is 15:30 (New York 08:30).
No packed synthetic dates, FOMC, other news, width tuning or strategy filters.

Read exactly the completed 15:30 M1 candle. Green: market buy at the first
available quote in 15:31, TP=signal high, SL=signal low. Red: market sell,
TP=signal low, SL=signal high. Market execution uses that new quote's ask/bid,
not a retroactive fill at the previous candle close. One attempt per session.
Skip doji, missing signal/entry minute, zero favorable wick at the signal close,
or target/stop not strictly on the proper side of executable entry. Honor
broker stop-distance constraints without widening either level. Log every
available event decision and any broker rejection. No retry or re-entry.

Resting TP/SL operate intrabar. Close remaining exposure at the existing
23:30/early-close research cutoff, or first following quote if unavailable.
Tester only; refuse live use and any symbol except the frozen research symbol.

Three runs: CPI+payroll, CPI only, payroll only. The latter two verify the
combined run by decomposition, not select a best subset. Primary eras 2016–19,
2020–September2026 and pooled; 2010–15 secondary. Report trade count, skips,
win rate, PF, net, average net R, daily and intraday equity DD, annual results,
and extra $1/trade stress. No claim of unseen-data confirmation.

Verify each signal against raw M1 OHLC, quote-side entry, exact TP/SL, native
deals/statistics/equity, and independent subsequent minute-path exits. Report
same-minute TP/SL ambiguity and costs/spread/model limitations. Generated OHLC
ticks cannot establish real execution during news. No automatic commit or
production settings change.
