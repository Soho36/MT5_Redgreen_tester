# GG entry at the green close

Use the archived ungated NQ M30 GG expert and settings from the October 23 instrument baseline. Run one native MT5 control with its buy stop at the green candle's high and one variant that buys at market on the first available quote after the candle closes. Evaluate every eligible signal while flat in each arm. If the quote is at or below the signal low, the market entry has no valid initial risk and is skipped.

Keep the stop at the green candle's low. From the actual fill, calculate 1R as the distance to the stop. At an M30 close at or above entry plus 1R, the existing EA exits at the next quote. Keep the original session windows, early closes, flatten fallback, one contract and 1-minute OHLC model.

Compare net dollars after $1.05 per trade, number of trades, net profit factor and maximum daily-close drawdown using order submission sessions. Report June 2010–2015, 2016–2019, 2020–September 2026 and the pooled 2016–September 2026 sample. Reconcile the control with the archived GG ledger, both arms with MT5 deals, and entry prices and stops with the recorded bars.
