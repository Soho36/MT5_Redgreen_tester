# Archived: intrabar speed and post-signal bounce research

Archived in place at the user's request, 2026-10-03. This branch is no longer
the active research direction. Preserve the evidence; do not restart speed or
immediate-reclaim entry experiments automatically.

## How we reached this point

1. [Q8](../q08-breach-reclaim/RESULTS.md) asked whether a breach followed by a reclaim
   predicted more upward movement. Current-session reclaims more often ended
   +0.5 signal R higher 90 minutes later, but average returns and RTL profitability
   did not consistently improve. The recent increase was two-sided in R units.
2. [Q9](RESULTS.md) inspected the M1 path inside an M30 signal:
   fast recovery within 1–2 minutes versus slow recovery after 6+ minutes,
   matching breach depth, volatility, candle size and timing. It found no
   reliable advantage in returns measured after the completed M30 candle.
   Lagged-volatility normalization also showed that smaller reclaim candle
   ranges contributed to the apparent excess of large R moves.
3. We considered earlier minute entries, approach speed, dwell time and sustained
   recovery. Those proposals were **not tested** and are now parked with this
   branch. A short-lived immediate bounce was not ruled out by Q9.
4. The user redirected the research to the actual M30 strategy question:
   **support-interaction red candles versus every other qualifying red candle**,
   using actual buy-stop outcomes. Fixed -1R SL/+1R TP simplifies this experiment.

## Why this branch is archived

Intrabar timing, matched breach-only comparisons and a +0.5R endpoint after
90 minutes made the investigation harder to interpret and moved it away from
the user's strategy-selection question. A candle's eventual direction within
its signal bar is not the same as the result of the later buy-stop trade.

"Wrong direction" records a decision about research priorities and fit to the
strategy, not proof that speed is universally irrelevant or that every earlier
observation was false. Keep the negative and uncertain findings as context.
The active question does not require a reclaim, a close below support, or any
particular recovery speed. [Current broad definition](../../README.md).

## Retained evidence

- Q8 protocol: [BREACH_RECLAIM_PROTOCOL.md](../q08-breach-reclaim/PROTOCOL.md).
- Q9 protocol: [RECLAIM_SPEED_PROTOCOL.md](PROTOCOL.md).
- Q9 analysis, helpers, tests and verifier remain in `python/` under their
  original names, so the results can be inspected without resurrecting the idea.
- Q8/Q9 raw outputs are in `Reports/levels/breach_reclaim_20261003/` and
  `Reports/levels/reclaim_speed_20261003/`. Archival is a status change, not deletion.
- Q10's historical fresh-interaction tables remain available, but they are not
  a substitute for the newly clarified range-overlap population.
