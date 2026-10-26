# GG on weekly candles, flattened every session: protocol

Fixed 2026-10-27, before any GG weekly result. User request: after the weekly RTL
study, "run GG strategy". Exploratory and descriptive; no adoption rule.

GG is RTL with the signal colour flipped (`GG_r_MFE_buy-stop-entry_runband.cs`): a
**green** week (close > open) arms a buy stop at its high for the next week, stop at its
low; a red or doji week leaves a pending order in place; a new green week replaces it.
Everything else is copied unchanged from the RTL weekly studies:

- [Weekly flatten protocol](../rtl-weekly-flatten/PROTOCOL.md): flatten at the 23:30 or
  early-close cutoff, buy back at the next open, weekly-close 1R exit, roll-adjusted levels
  (raw as sensitivity), held and MT5-style variants, $1.05 per round turn and +$1/+$2
  stress, eras 2016-19 and 2020-26 (to 2026-09-30), 2010-15 reference.
- [Control protocol](../rtl-weekly-flatten/CONTROL_PROTOCOL.md): plain long (shared with
  RTL, strategy-free), green week with a market entry at the next week's open (stop at the
  green week's low), and random timing of GG's own in-market sessions. Same reading rules.
  Random timing is scored on sessions GG was long **from the open** (the corrected
  definition from the RTL study; the fill day is excluded because it is selected by the
  breakout). The "every held session" version is reported for comparison only.
- GG M30 baseline: the existing uncapped MT5 ledger
  (`Reports/timeframe_baseline_20261015`, GG M30 RR 1).
- Descriptive extra: weekly RTL and weekly GG together, one contract each.

## Validation before reading results

1. The simulator's M30 mode with the green signal reproduces the GG M30 MT5 ledger trade
   by trade (entry and exit minutes, profit).
2. A fresh MT5 W1 run of the frozen GG source (`GG_timeframe.mq5`, 2026-10-15; flatten
   and trade windows off) is reproduced trade by trade by `W1 hold MT5-style`.
3. The RTL results are unchanged after the colour switch is added.
