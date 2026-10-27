# RTL full-session VWAP: full strategy replay

Frozen 2026-10-26 before replay outcomes. User authorized full replay of the
[saved proposal](REPLAY_PROPOSAL.md). The attribution study is committed as
44f2cff; its observations motivated this test, not independent validation.

## Rule and order handling

Run two arms only: gate off and gate on. Uncapped RTL M30, one contract valued
at $2/point, RR1 original bar-close exit, original stop, time windows, flattening,
calendar and zero trailing distance. Do not optimize threshold, anchor or exit.

At an otherwise eligible new red-signal submission, use the latest completed
feature available_at <= actual tester TimeCurrent. Same-date full-session
minute HLC3 VWAP and arithmetic 20-observed-M30 true-range average A20; suppress
the new buy stop only when signal close < VWAP - A20. Equality permits entry.
Unknown A20/VWAP permits entry; previous-session VWAP is unknown at session open.
Use the independently verified all-bar full_hlc3 panel, not a trade-filtered file.
The EA validates feature signal-bar identity, price and availability; never use
fill/exit data to choose an order. Before the first valid A20, allow the baseline.

Implementation clarification frozen before outcomes: **the original eligible-red
candidate cancellation runs first; the gate then suppresses only the new
replacement order.** Original range/run/location/session cancellations also
remain. Thus an existing pending order can be canceled by normal red-candidate
maintenance even when its replacement is blocked. The VWAP gate adds no separate
cancellation at other times and never closes a position. This resolves the
proposal's otherwise ambiguous combination of preserving maintenance and not
canceling accepted orders. No second pending-lifetime variant will be selected.
Preserve original signal calculations and position management. Skipping orders
must free later opportunities, which a full engine replay must process.

## Exact baseline and environment

Use frozen Reports/timeframe_baseline_20261015/RTL_timeframe.mq5 and original
tf_20261015_rtl_m30_rr1p0.ini, not the subsequently edited main EA. Source hash:
8995d0ed6f97f21b15f4ce31f862fb8f642a1eae5a4e28c6bc371cb928165810.
Symbol MNQcontDTBNT20102026_2, Model=1 minute OHLC, M30, FromDate2010.06.07,
ToDate2026.10.15, same symbol properties/custom history. The actual source ends
October1; preserve the full run for replication, exclude submissions on/after
2026-10-01 from eligible outcomes. Warmup2010-15 retained for engine state.

An isolated portable MT5 tester uses copied binaries, custom-symbol definitions
and only this symbol's history. Do not copy account/login settings or interrupt
the user's running terminal. Disable live trading, DLLs, remote/cloud agents;
local historical tester only. Compile the research copy with zero errors/warnings.
Record executable/build, source/history/config hashes and all outputs.

Gate-off must exactly reproduce the original 25,833 complete trades, including
warmup/partial endpoint, via original ledger and complete MT5 orders/deals; eligible
counts 6,167 and10,501, net $4,416.65/$38,399.95. Compare submissions, requested
entry/stop, fills/exits/times/gross profit/risk, not only aggregate profit.
If platform build changes ticket IDs alone, reconcile by unique submission and
signal identity and disclose that exception; other changes require resolution
before interpreting the gate. Never silently weaken a failed replication gate.

## Logging, economics and attribution

Log all actual eligible red candidates (including blocked attempts), signal OHLC,
VWAP/A20/availability, decision and order result; accepted/canceled order history,
all entry/exit deals and complete trade paths. Cross-check the original logger
against complete history so fast-closing trades cannot disappear.

Use 2016-19 and2020-September2026 eras and annual results. Deduct $1.05 per completed
trade externally, plus +$1/+$2 stress. Preserve original planned entry-minus-stop
risk for R; report actual fill risk separately. Full source-session calendars
include flat days. Report dollars/R, PF, costs, holding/planned-risk exposure,
closed-trade and daily-close DD/depth/duration, worst days/weeks.

Compare baseline, prior ledger omission and actual gated replay. Match trades
by original candidate submission/signal, not ticket IDs across arms. Partition:
unchanged trades (all economic execution fields agree), execution-changed matched
trades, baseline-only removed trades, gated-only new trades. Report counts and
net dollar/R contributions; reconcile gated-minus-baseline exactly. Also explain
gated-minus-ledger-omission with new/removed/changed memberships. Counts of newly
enabled candidates and canceled/expired/filled accepted orders are distinct.

Compare the whole baseline uniformly scaled to actual gated holding-time ratio
and separately planned-dollar-risk ratio, scaling dollar PnL/costs together.
Fractional contracts are diagnostics only. Neither control proves causation.

For modeled open-equity risk, save chronological (time_msc, account balance,
account equity) samples before/after tester ticks and transaction callbacks,
deduplicating identical samples. Reconstruct net equity from gross equity and
cumulative entry costs at entry deal timestamps. Same-millisecond samples all
use charges for entries whose timestamp <= sample time; document this convention.
Reset the equity high-water mark at each era/year start; include initial zero.
Report depth and elapsed calendar duration on this sampled path, separate from
daily closes. Reconcile flat equity/total gross balance with deals and expose
any callback/millisecond limitations. This is simulated minute-OHLC quote risk,
not true historical tick extremes or measured live slippage. MAE alone cannot
establish account drawdown because the ordering of peaks and troughs matters.

## Verification and decision

Independent reconstruction of every candidate as-of label and decision, accepted
order linkage, complete deals/path outcomes, baseline replication, attribution
partitions, all comparisons, daily curves and sampled equity. Targeted tests for
boundary equality, unknown/session reset, future perturbations, original pending
replacement, duplicate/missed/fast trade recording and attribution reconciliation.
Save executable preparation/runner/analyzer/verifier, source/program/data/output
hashes, audits, tables, chart and results; update plan/status/journal and commit.

No new threshold tests, bootstrap significance claims or automatic live/default
changes. A risk-management follow-up remains credible only if full replay
preserves lower DD and a useful profit/DD tradeoff in both eras relative to static
exposure, with duration/cost/annual tradeoffs disclosed. Report a failed or weakened
result plainly. Fresh forward evidence and account suitability remain separate.
