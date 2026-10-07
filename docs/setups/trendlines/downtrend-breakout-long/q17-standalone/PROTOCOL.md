# Q17: does the falling-resistance candidate keep its edge when traded alone?

**Frozen 2026-10-04** with the user's approval of the draft as written, before
the trading run. Decided with the user:

- **Option B:** a stand-alone, candidate-only EA, so these trades are seen
  separately from every other signal.
- **Primary group:** the whole frozen Q15 candidate group.
- **Narrow version:** entry below the line, reported as a secondary label only.
- **Order:** the Q16 concentration audit first (done).

This is the clean "is the edge real" measurement. It is not yet a decision to
add anything to the main strategy. Sizing or combination is decided later,
after the results.

## Why a separate run

Q15 attributed existing baseline fills. In the baseline, a candidate can be
blocked by an open position or a pending order from a non-candidate signal.
Traded alone, those slots are free, so the set of trades and their sequence
change. Only a full MT5 run measures what the candidate rule actually trades.

## EA and execution (fixed)

**Source.** The EA is a copy of the Q10 baseline research EA
(`Reports/trend_rr_20261002/RTL_trend_rr.mq5`, the `f50_baseline` inputs)
plus one include, [`mt5/experts/resistance_gate.mqh`](../../../../../mt5/experts/resistance_gate.mqh).
[`python/prepare_resistance_standalone.py`](../../../../../python/prepare_resistance_standalone.py)
generates the copy, the roll table and the INIs, and refuses to overwrite a
completed run.

**Gate.** The gate runs where the baseline would place its buy stop, after
the existing filters (MaxRedRun = 3, time windows). It applies the frozen Q15
definition on raw highs:

- one-week window, N = 5;
- consecutive lower highs >= 10 bars apart, falling >= 0.02 x A per bar;
- an unbroken, departed line;
- signal high within +/-D of the line, at most D above it.

**A rejected signal.** A signal that is not a resistance test is rejected
exactly like a MaxRedRun rejection: the previous pending buy stop is
cancelled and no order is placed. Each candidate's order therefore lives
exactly as long as it would in the baseline (until the next red bar, the
window end or the flatten). Only position and order availability change.

**Everything else unchanged:**

- buy stop at the red high and stop at its low;
- bar-close-qualified exit at >= 1R, session/early-close flattening;
- one contract, MaxRedRun = 3, all 24 enabled hourly windows;
- symbol `MNQcontDTBNT20102026_2`, M30, one-minute OHLC (Model=1);
- full history 2010-06-07 to 2026-07-14.

Costs are modelled in Python as $1.05 per round trip;
net R = net / (2 x signal range).

**Periods:** 2016-01-01 to 2020-01-01 and 2020-01-02 to 2026-07-14, as before.

## Pre-trade verification (done, no outcomes)

A classify-only run (GateMode = 1: every signal is logged, no order is ever
placed) reproduced Q15 exactly ([check](../../../../../python/verify_resistance_gate.py)):

- all 52,070 census signals were classified, with 0 group mismatches;
- 4,580 / 4,580 candidates match;
- all 18,384 contacted lines have identical anchors;
- line values and ATR agree to about 5e-11 (CSV rounding).

The EA compiled with 0 errors and 0 warnings; the test passed in 14.6 s.

## What the trading run reports

Per period and per year:

- trades, net $, net PF, average and median net R, and win rate;
- exit mix and average signal range;
- closed-trade max drawdown and longest losing run;
- the largest-trade share of net.

Week-block bootstrap (5,000 resamples, seed 20261004) 95% intervals for
stand-alone mean R and PF.

**Comparisons, all descriptive:**

1. **The Q15 attribution** of the same candidates inside the baseline:
   412 / 693 fills, PF 1.325 / 1.332, mean R +0.093 / +0.110.
2. **The baseline full strategy**: PF 1.106 / 1.107, mean R -0.004 / +0.060.
3. **Trade identity.** For signals that traded in both the baseline and the
   stand-alone run, entry, exit and net should be identical. Count matches
   and explain any difference.
4. **Freed trades.** Report the stand-alone trades that could not trade in the
   baseline separately: this is the new information.

**Secondary label (not a decision basis):** entry below the line (signal high
< line value), from the gate log.

## Reading rule (fixed now)

The candidate **survives its own execution** if, in both periods:

- stand-alone PF > 1;
- mean net R > 0;
- mean net R exceeds the baseline full strategy's mean R (-0.004 / +0.060);
- mean R is above the baseline's in >= 7 of 11 years (years with >= 10 trades).

Otherwise it does not survive. The result is reported either way.

**What a pass means, and what it does not:**

- A pass means the candidate rule is a real stand-alone edge under one-minute
  OHLC execution.
- It does not mean it should be added to RTL. Combination, sizing (e.g. a
  larger size on candidate signals) or a separate strategy are later
  decisions with their own protocol.
- No parameter is tuned after this run. Generated-tick execution is not run
  (the user's 2026-10-02 preference); its sensitivity remains an open caveat.

## Outputs

`Reports/trendlines/resistance_standalone_20261004/` holds the source, binary,
compile log, INIs, MT5 reports, ledgers, gate logs, verification files and
provenance. Results doc: `docs/setups/trendlines/downtrend-breakout-long/q17-standalone/RESULTS.md`.
