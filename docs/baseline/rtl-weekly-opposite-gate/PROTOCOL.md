# RTL: completed-week, most-recent opposite-colour gate

2026-11-17. Rules fixed before calculating this experiment's outcomes.

## User-confirmed rule

Keep RTL's entries, stop, close-confirmed 1R profit exit, session windows and
daily/early-close flattening unchanged. Add a persistent entry gate:

- A completed red week (close < open) disables entries when its close is
  strictly below the low of the most recent earlier green week.
- A completed green week (close > open) enables entries when its close is
  strictly above the high of the most recent earlier red week.
- Search back beyond adjacent weeks. Update the latest red/green reference
  after evaluating every completed week, including while halted.
- Dojis do not replace either reference or switch state; equality is no break.
- Start enabled. With no opposite-colour reference there is no trigger.
- Apply the completed week's decision on the first quote of the next week.
  Never use an unfinished weekly candle. The last dataset week cannot change
  trading until a subsequent week opens.
- Cancel pending entries while halted. Existing positions keep normal RTL
  exits; resumption does not resurrect old orders.

## Data and execution

Two native MT5 tester arms, filter disabled control and filter enabled. Frozen
RTL source: Reports/timeframe_baseline_20261015/RTL_timeframe.mq5. M30,
MaxRedRun=0, MinLocation=0, 1 MNQ, 1-minute OHLC, $1.05 round-trip cost deducted
afterward. No other experimental filters. Tester-only EA, no live changes.

Use the newly verified MNQcontDTBNT20261114 symbol, 2010-06-07 through
2026-11-13; tester end 2026-11-14 exclusive. Weekly OHLC is native MT5 W1 on
the research clock (Monday-Friday source dates), raw continuous-contract
prices as displayed by this custom symbol. Preserve roll gaps; do not choose
a price adjustment based on results. Conclusions are specific to this chart's
session and rollover construction. Initial available history may be partial;
start enabled and accumulate references from completed available weeks.

Orders are processed by MT5 before the EA sees each quote. Any resting order
filled on a boundary quote is an existing position, not a cancellable pending
order. Audit this possibility; normal daily flattening should remove Friday
orders before the weekly change. Log each weekly decision and cancellations.

## Fixed comparisons

Report 2010-15, 2016-19, 2020-September 2026, October 1-November 13 2026,
pooled 2016-September 2026, and 2016-November 13 2026; annual rows too.
The October-November extension is a small additional sample, not independent
forward validation of an idea selected after looking at recent charts.

For each: trade count, net dollars, mean gross/net R, net profit factor,
closed-balance and intraday equity drawdown, net/equity-drawdown, and $1 extra
cost per trade sensitivity. Count halted weeks/sessions and switches. Compare
skipped versus retained baseline trades and any replacement trades. Report a
paired weekly-block bootstrap interval for the net-profit difference (10,000
draws, seed 20261117); descriptive uncertainty, no claim of untouched testing.
Compare drawdown to a uniformly smaller baseline at the gated holding-time
fraction as an exposure control. No tuning or alternate threshold search.

## Verification

Hash source, settings, data and protocol before the run. Reconcile native
reports, ledgers and tester totals. Rebuild W1 OHLC independently from raw M1
data; independently reconstruct every gate decision. Check disabled control
against the saved historical baseline over the common period. Replay all
trades with the existing independent minute engine using derived halt windows,
checking submissions, fill/exit minutes, prices and stops. Reconcile native
gross equity drawdown before deducting costs. Test distant references, dojis,
strict boundaries, reference updates while halted, causal activation, pending
cancellation and preservation of open-position exits.

Report failures or limitations explicitly. Preserve the old weekly-gate study:
its adjacent-week rules were different.

