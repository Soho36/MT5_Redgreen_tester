# Abnormal green M1: full-body follow-up

Fixed 2026-11-24 before inspecting shape counts or filtered results. User asked
how many of the original 446 traded signal candles are full bodied, and to
exclude long wicks. Primary definition: (close-open)/(high-low) >= 0.80.
Both wicks together must occupy <=20% of the entire range. This limits either
wick individually too. Report 70% and 90% neighbours, plus exact wickless count,
without choosing a threshold by profitability. Keep original 10x range trigger,
20-bar reference, entry/stop/1R immediate TP, costs, sessions and order semantics.

First classify the original 446 signals and report counts, share and ledger-only
subset P&L. Then replay the full raw history with the shape gate on all eligible
signals. Rejected signals neither replace pending orders nor create new orders.
Keep previous qualifying pending until fill/replacement/cutoff, as before.
Report new/removed/repriced trades separately: filtering a saved ledger alone
can miss changes in subsequent opportunities. Preserve all original artifacts.

Replay directional, low-first and high-first OHLC paths. Unfiltered control must
match all three original ledgers exactly. Independently verify new signals,
first-touch entry, exits and drawdown. Include eras, annual rows, cost stresses,
profit concentration and paths; this remains exploratory Python OHLC research,
without separately modeled spread. No native MT5 or live/default changes.
