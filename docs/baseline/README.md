# The RTL strategy itself

Studies of the base strategy, not of a price pattern at a level: red M30
candle, buy stop at its high, stop at its low, bar-close exit at 1R, session
flatten. The current rules are in [STATUS.md](../STATUS.md).
[All docs](../README.md).

| Study | Answer |
|---|---|
| [Q1/Q2: preceding candles](q01-q02-preceding-candles/RESULTS.md) ([protocol](q01-q02-preceding-candles/PROTOCOL.md)) | No filter; keep MaxRedRun = 3, MinLocation = 0 |
| [Q3: overlapping vs steady bars](q03-overlap/RESULTS.md) | No filter |
| [Q4: pullback vs broader move](q04-context/RESULTS.md) | No filter |
| [Q5: signal-candle shape](q05-candle-shape/RESULTS.md) | No filter (doji / full body flip between periods) |
| [Time of day](time-of-day/RESULTS.md) | Every session block profitable in both periods; windows unchanged |
| [MaxRedRun on clean data](maxredrun/RESULTS.md) | Cap 1 wins the train/test on PF and DD but costs 23% net; the user kept cap 3 |
| [RR 0.5-5.0 optimization review](rr-optimization/RESULTS.md) | 2.5R the best profit/drawdown candidate in that sample |
| [RR on clean data](rr-clean-data/RESULTS.md) | 2.0 / 2.5 / 3.0 do not all beat 1.0; RR stays 1.0 |
| [Exit threshold](exit-threshold/RESULTS.md) ([protocol](exit-threshold/PROTOCOL.md)) | Keep the 1R bar-close exit |
| [Trailing stop after +1R](trailing-stop/RESULTS.md) | Rejected |
| [Flatten fallback](flatten-fallback/RESULTS.md) | Fix adopted: always flat at session end |
| [Early-close calendar](early-close-calendar/RESULTS.md) | Adopted: no cross-date trades |
| [Near-stop averaging entry](averaging-entry/RESULTS.md) ([protocol](averaging-entry/PROTOCOL.md)) | Keep averaging off |
| [Limit-only entry](limit-only/RESULTS.md) ([protocol](limit-only/PROTOCOL.md)) | Rejected |
| [Trend-conditioned RR](trend-rr/RESULTS.md) ([protocol](trend-rr/PROTOCOL.md)) | Keep fixed 1R |
| [Signal colour + no-pattern control](signal-colour/RESULTS.md) | Edge is the buy stop over a previous high, not the colour (green ≈ red). Buy-stop gain over a plain long: NQ +0.08 R, ES +0.04 R; ES fails because its plain long loses |
| [Why ES differs from NQ](nq-vs-es/RESULTS.md) | Mostly tick granularity: NQ rounded to an ES-like grid loses half (2016–26) to all (2010–15) of its breakout follow-through; ES not generally more mean-reverting |
| [MES: unseen instrument](mes-unseen-instrument/RESULTS.md) | No edge on MES even before costs (mean R −0.04 / +0.00 vs MNQ +0.09 / +0.09) |
| [Q24: trade-result streaks](q24-trade-streaks/RESULTS.md) ([protocol](q24-trade-streaks/PROTOCOL.md)) | No predictive or daily-stop rule passes |
