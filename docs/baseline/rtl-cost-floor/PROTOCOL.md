# RTL cost floor: skip signals whose risk is too small for the cost (protocol, fixed 2026-11-19 before any run)

**Question (user, 2026-11-19).** The $1.05 per trade is 0.19 R in 2010-15 and 0.02 R since 2020
([volatility study](../volatility-regimes/RESULTS.md)). Does skipping signals where the cost is a large share
of the risk improve RTL natively in MT5?

**Rule.** RTL risk = signal (red) candle range (entry at its high, stop at its low). With a fixed $1.05 cost
and $2 per NQ point, "cost <= c x risk" means "range >= 1.05 / (2c) points". So a cost-share cap is a fixed
minimum candle range, which the EA's existing filter already implements (`UseCandleRangeFilter`,
`MinCandleRange` in symbol points of 0.01; `MaxCandleRange` left out of the way).

| Arm | Max cost share | Skip signal if range below | `MinCandleRange` |
|---|---|---|---|
| control | none | - | filter off |
| floor20 | 20% | 2.625 pts (keeps >= 2.75) | 262.5 |
| floor10 (main) | 10% | 5.25 pts (keeps 5.25) | 524.5 |
| floor05 | 5% | 10.5 pts (keeps 10.5) | 1049.5 |

`MaxCandleRange` = 10,000,000 (no cap). Everything else is the RTL baseline: `RTL_midpoint` with
`UseMidpoint=false` (byte-identical to RTL), symbol `MNQcontDTBNT20102026_2`, M30, 2010-06-07 to 2026-10-15,
one MNQ, RR 1.0, flatten 23:30 with fallback, early-close calendar, the usual trade windows, MaxRedRun 0.
Costs $1.05 per trade, charged afterwards. The control must reproduce the 2026-11-16 baseline ledger byte for byte.

**Reported.** Net, mean net R, trades and closed-trade drawdown for 2010-15, 2016-19, 2020-Sep 2026; equity DD
from MT5 for the whole run; trades the floor freed (orders that only exist because a skipped one did not fill).

**Reading, fixed now.** The floor only removes trades; it can only help if those trades lose after costs.
Count it as an improvement for an era if net rises and closed DD does not rise. The main arm is floor10; 20% and 5%
are neighbours to check it is not a lucky cut. Since 2020 floor10 should barely touch anything (median risk 25 pts);
if it changes 2020-26 materially, look for the reason before reading the early eras. Exploratory, chosen after
seeing the ledger split; no baseline change from this alone.

**Cost caveat.** The real cost in 2010-19 is unknown: MNQ starts May 2019, before that only full NQ
(10x size, roughly half the commission per point). Results are also shown at $0.50 per MNQ-equivalent.
