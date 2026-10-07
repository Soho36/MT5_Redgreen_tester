# One near-stop averaging entry

2026-10-01. Exploratory study, defined before examining results.

Keep the clean-data baseline: M30, MaxRedRun=3, RR=1, calendar and flatten
fallback on, one initial contract, symbol MNQcontDTBNT20102026_2.
Periods: 2016-01-01 to 2020-01-01 and 2020-01-02 to 2026-07-14.
All these data have already been examined; neither period is untouched validation.

After the original buy stop fills, place exactly one equal-sized buy limit at
original stop + f * initial fill-to-stop distance. Primary f=0.10; neighbours
0.05 and 0.20. Round upwards to a tick, with at least one tick above the stop.
Keep the original stop for the whole basket. Never widen it or add again.
Cancel an unfilled add when the basket closes, before a discretionary exit,
and at session flatten. Skip an invalid limit; record skips and rejections.
Use a separate research EA on a netting tester account, with live use disabled.

Execution correction identified during reconciliation, before valid results:
MT5 can process the original SL and then the limit on the same synthetic tick,
before the EA can cancel it. Immediately market-close any such replacement
position on the next available EA tick, and include both position identifiers
in the original basket. Record these stop-before-add fills separately. Charge
both contracts and retain actual execution prices; never assume the second
loss is capped at its planned stop distance. Reconcile MT5 trade count to exit
deals (a basket can contain two closed positions). Original-leg fill and exit
times and PnL must still match the control. Initial unreconciled exports are
preserved separately under Reports/averaging_entry_20261001_invalid_v1.

User-confirmed exit: the original bar-close target remains fixed for the entire
basket. No intrabar profit-taking is introduced.

Run an averaging-off control and all three distances in both periods. Require
the off control to reproduce the previous clean-data RR=1 baseline trade by
trade. Reconcile basket gross PnL with MT5, entered and exited volume, and
per-leg attribution. Check no position crosses a session date. Charge $1.05
per round-turn contract; also report $1 for historical comparability.

Report basket count, add fills, net dollars, PF, closed-balance drawdown, MT5
gross equity drawdown, average net R, add-leg PnL and yearly results. R is the
initial single-contract dollar risk. Report basket-risk-normalized R as well.
For equal planned risk, divide the entire basket PnL by 1 + rounded add distance
/ initial risk, including baskets whose limit never fills. This is a fractional
size diagnostic, not an executable one-micro-contract sizing recommendation.

Screen for further research only if all three distances improve net PF and net
profit per closed-balance drawdown in both periods at $1.05, and the primary
10% case improves profit after equal-planned-risk normalization in both periods.
Do not change the adopted baseline automatically. Preserve negative results.

Execution limitation: the data are one-minute OHLC bars, not trade ticks or
order-book data. The existing tester uses one-minute OHLC modelling. A close
limit and stop can be crossed in the same minute, so simulated fill sequencing
and queue assumptions matter. Any promising result needs finer execution data.

Focused sensitivity added after the execution audit, before the corrected
primary results were evaluated: run off and 10% in both periods with Model=0
(Every tick generated from the same M1 bars), saved in the `_ticks` directory.
Do not tune distances on this check. Compare each against its own same-model
control. This is a modelling sensitivity, not real-tick validation; a large
change in the answer makes the hypothesis inconclusive on the available data.

MetaQuotes documents the difference between [generated and real ticks](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation)
and warns that [trade transaction arrival order is not guaranteed](https://www.mql5.com/en/docs/event_handlers/ontradetransaction).
The observed stop-before-limit sequence is established by this study's actual
MT5 deal records, not inferred solely from those general documents.
