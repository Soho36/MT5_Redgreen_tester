# Standalone buy-limit screen — 2026-10-02

The user requested a separate limit-only EA and accepted 1-minute OHLC for raw
screening. No further generated-tick runs are part of this experiment.

The default follows `mt5/archive/RR_r_MFE_limit-entry.cs`: a qualifying closed
red M30 candle arms a setup. Once ask reaches its high, submit one buy limit;
there is no buy-stop position. `WaitForHigh=false` also supports immediate
placement after the signal candle closes, for a separately named experiment.

For candle high H and low L, entry is H-offset*(H-L). Freeze offsets at 80%,
90% (primary), and 95%, corresponding to 20%, 10%, and 5% of the candle range
above the stop. Round upward to the next 0.25 tick and keep at least one tick
above L. Skip prices that cannot be submitted as a valid buy limit; do not
substitute a market order or retry an invalid setup.

One MNQ-priced contract, stop L, unchanged original bar-close threshold
H+(H-L), executed through the baseline's bar-close exit routine. No averaging
or target recalculation from the limit fill. Preserve baseline red-run filters,
session window, early-close calendar and flattening. A new qualifying red candle
replaces the unfilled setup; a rejected red cancels it. Green candles leave it
alone unless another existing baseline cancellation rule applies.

Run unchanged buy-stop controls and the three offsets on the clean symbol
MNQcontDTBNT20102026_2 for 2016-01-01 to 2020-01-01 and 2020-01-02 to
2026-07-14. Model=1 only. Deduct $1.05 per completed contract and show an
additional $1 cost stress. Report net, PF, closed-trade balance drawdown,
net/DD, win rate and annual results. Also retain MT5 gross equity drawdown.
This is descriptive screening; do not select new offsets after viewing outcomes.

Reconcile every export to MT5 aggregate statistics and full HTML deal/order
reports. Verify controls reproduce the previous OHLC baseline, all variant
entries are buy limits, stop/target/rounding match the signal, exposure is
one contract, and no trade crosses a date boundary. Fail the audit for order
rejections, cancellation errors or missing trade rows.

These are independent strategies, not an exact extraction of the prior
averaging leg: while flat they may accept signals the original buy-stop
strategy would miss while holding a position. The high trigger is an observed
quote, not a simulated buy-stop fill. OHLC cannot resolve the actual ordering
of prices within each minute, so fill/stop sequencing and small near-stop
losses are approximate. No live deployment is part of this screen.
