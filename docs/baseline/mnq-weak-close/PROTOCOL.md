# Short the final half hour of a weak NQ day

Frozen 2026-11-06, before computing outcomes. Compare selling the final half hour of every full US cash session with selling that same interval only when NQ is already below its previous cash-session closing mark. The timing hypothesis follows the rest-of-day predictor in Baltussen et al. Their NQ sample ended May 1, 2020. The short-only rule and its trading costs are our experiment. [Paper](https://academicweb.nd.edu/~zda/intramom.pdf)

## Prices and timing

Use the project's Databento continuous NQ one-minute trades with one MNQ's $2/point economics. At the first price of the 15:30 New York minute on an ordinary cash-session day, mark **weak** if that price is strictly below the same contract's last regular-minute closing price on the preceding US equity trading day. On an early close the reference is the 12:59 minute close, otherwise the 15:59 minute close. Equality joins the nonweak group. Do not trade on early closes, closed cash-market dates, or across a change of front-contract instrument ID. Never substitute a stale prior price.

For the primary simulation, observe the 15:30 open, then enter on the first subsequent MT5-modeled quote in the existing verified one-minute OHLC sequence. If the minute has a sole modeled quote, wait until the 15:31 open. Also run a timing sensitivity fixed in advance: keep exactly the same signal and eligibility, enter at the 15:31 minute open using an observed trade price. This checks dependence on the synthetic within-minute sequence. Cover at the 16:00 minute open. These are futures prices around the cash-session boundary. One trade per selected day, pure time exit, no protective stop or target.

The project timestamps are Chicago local time plus eight hours, hence New York plus seven hours within every US cash session, including DST transition weeks. Use full and half-day US cash-equity holiday rules, including exchange mourning days; use only the exact reference and execution minutes. Record separately missing input and unpriceable sessions. Orders in the control and the complementary nonweak group use the same prices. No parameter or entry-time search. [Data build](../../reference/DATA_BUILD.md) · [NYSE calendar](https://www.nyse.com/trade/hours-calendars) · [Historical XNYS rules](https://github.com/gerrymanoim/exchange_calendars/blob/master/exchange_calendars/exchange_calendar_xnys.py)

## Reporting

Test January 2016–December 2019 and January 2020–September 2026. Also show pooled 2016–September 2026 and the overlapping post-paper window from May 4, 2020. Compare weak, all eligible, and nonweak full sessions. Report trade count, gross and net P&L, mean net dollars per trade, net profit factor, win rate, daily-close drawdown, yearly net and individual trade outcomes. Charge the project's $1.05 round-trip fee; stress another $1 and $2 per trade (respectively one and two adverse 0.25-point ticks per side). Drawdown uses cumulative realized P&L at session end.

For weak-day mean net and weak-minus-all mean net, resample blocks of four consecutive calendar weeks, 5,000 draws with a fixed seed, and report percentile 95% intervals. Examine the direction and size across periods, both fill timings and cost levels. Conclusions concern this historical simulation.
