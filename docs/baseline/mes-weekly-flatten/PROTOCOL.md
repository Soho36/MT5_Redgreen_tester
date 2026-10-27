# RTL on weekly MES candles, flattened every session: protocol

Fixed 2026-10-27, before any MES weekly result. User request: "test MES RTL also.
Possibly bigger weekly candles will provide needed resolution." Exploratory and
descriptive; no adoption rule.

## Why

RTL M30 fails on ES ([MES baseline](../mes-unseen-instrument/RESULTS.md)). The resolution
studies found that the buy-stop gain over a plain long shrinks when candles span few price
steps, and ES M30 candles span far fewer ticks than NQ's. A weekly ES candle spans
hundreds of ticks, so resolution no longer limits it. Caveat fixed now: on NQ, weekly bars
showed no buy-stop gain over the plain long at all
([controls](../rtl-weekly-flatten/CONTROL_RESULTS.md)), so a weekly test checks whether ES
behaves like NQ on weekly bars, not resolution alone.

## Setup

Identical to the NQ weekly studies ([flatten protocol](../rtl-weekly-flatten/PROTOCOL.md),
[control protocol](../rtl-weekly-flatten/CONTROL_PROTOCOL.md)), on ES:

- Data: continuous ES 1-minute source `F:\DATABENTO\ES_16_YEARS\MT5_ES_continuous_2010-2026_ohlcv-1m.csv`
  and its rolls file (same build rules as NQ). One MES contract, $5 per point, $1.05 per
  round turn (+$1/+$2 stress), market buys one tick (0.25) above the open, same early-close
  calendar. Through 2026-09-30.
- RTL W1 flattened (primary; roll-adjusted levels), flattened raw, held, held MT5-style.
- Controls: plain long, red week with a market entry, random timing of RTL's sessions long
  from the open (every held session reported for comparison only).
- ES M30 baseline: the existing uncapped MT5 RTL ledger on `MEScontDTBNT20102026_2`
  (`Reports/ym_baselines_20261023`).
- The two ES data holes (2020-02-28, 2020-06-30 stop mid-session): a position open there is
  closed at the session's last bar. Counted.
- Reported for the resolution question: signal-candle range in ticks (median), ES vs NQ,
  M30 vs W1.

## Reading rules

Same as the NQ controls: the buy stop adds to the plain long if RTL minus plain long (mean
gross R per trade) is positive in 2016-19 and 2020-26 with the 2020-26 95% interval above
zero; RTL's timing beats random if its sessions long from the open earn more than at least
95% of shifts in both eras. Net R, dollars, drawdown and yearly figures for context.

## Validation before reading results

1. The simulator's M30 mode reproduces the ES M30 MT5 RTL ledger trade by trade.
2. A fresh MT5 W1 run of the same frozen RTL source on `MEScontDTBNT20102026_2` (flatten
   and trade windows off) is reproduced trade by trade by `W1 hold MT5-style`.
3. The NQ RTL weekly ledger is unchanged after the simulator is made instrument-aware.
