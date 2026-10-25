# Proposed full replay: RTL signals far below session VWAP

2026-10-26. A concrete follow-up to the completed [attribution study](RESULTS.md).
**Proposal only; not implemented, executed or adopted.** Rationale is historical
risk reduction in both eras, not passing the stricter negative-dollar screen.

## Rule to preserve

At each original RTL candidate submission, use completed-bar full-session HLC3
VWAP and arithmetic 20-bar mean true range A20 exactly as in [PROTOCOL.md](PROTOCOL.md).
Suppress the new order only when completed close < VWAP - A20. Equality permits
entry. Unknown VWAP/A20 permits entry, including session-opening submissions.
VWAP resets each full futures session; minute volume remains actual NQ volume.
No cash-open reset, threshold optimization, extra MA filter or timing hysteresis.

Evaluate afresh at each candidate; the next eligible candidate resumes trading
without waiting for a cross above VWAP. Preserve original signal bookkeeping,
red-run tracking, order-maintenance/cancellation rules, sessions and flattening.
The VWAP rule itself does not cancel accepted orders or close positions. Blocked
orders must not consume a position slot; later signals newly enabled by this
absence must be processed. This is why the existing ledger cannot validate it.

## Required comparisons

- First run gate-off and exactly reproduce the existing eligible 16,668 baseline
  trades and $4,416.65/$38,399.95 net totals. Reconcile every trade, not just profit.
- Run gate-on at the same one-contract size and execution assumptions. Export
  each candidate's VWAP/A20/decision, accepted/canceled orders and complete trades.
- Partition results into unchanged, removed, new and execution-changed trades;
  explain the difference from the ledger-omission result.
- Report both eras and years, net dollars/R, profit factor, time/risk exposure,
  drawdown depth AND duration, open-equity risk under the chosen price resolution,
  and +$1/+$2 round-trip cost stress. Minute-OHLC fills are not measured live slippage.
- Compare with static exposure at matching holding and planned risk, explaining
  that fractional sizing is diagnostic. Retain early/recent cost and 2024 tradeoffs.
- Independently verify causal availability, resets, unknowns and all new paths.

Record the full replay design before reading its outcomes. No live change follows
automatically even if it reproduces the risk tradeoff. Fresh forward execution
and an account-appropriate risk budget remain separate requirements.
