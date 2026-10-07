# Exit threshold comparison

Frozen 2026-09-30 before these new MT5 results. This is exploratory historical
research; both periods have already been inspected. No new default is selected
automatically from the largest score.

## Question and arms

Does changing only the qualifying M30 close improve on the current RR=1 rule?
Test bar-close thresholds 0.75, 1.00, 1.25, 1.50 and 2.00 in each period.
Also run a fixed attached TP at 1.00R as a separate control for the existing
same-entry MFE estimate. Do not expand the grid in response to a local maximum.

Use the current runband source, MaxRedRun=3, MinRedRun=1, MinLocation=0,
LocationLookback=20, Lots=1. Same custom symbol MNQcontDATABENTOcurr6, M30,
1-minute OHLC simulation, zero configured slippage, $500,000 tester deposit,
range filter disabled, existing entry windows, and flatten setting 23:30.
Preserve pending-order and session handling, including any inherited limitations.
Record one signal bar for verifying fills and initial risk; logging alone must
reproduce the old RR=1 trade sequence.

Periods: 2015.01.01 through 2020.01.01 exclusive, and 2020.01.02 through
2026.07.14 exclusive, matching the previous cap-3 runs exactly.

The bar-close arm checks the last completed M30 close and submits a market
exit on the new bar's first tick. It does not guarantee execution at the last
close or at/above the threshold after a price gap. Preserve that actual code
behavior rather than substituting an idealized closing fill.

The experimental fixed-TP arm attaches entry + initial signal range * RR to
the pending buy stop and disables the qualifying-close exit. The original SL
and session flatten stay active. Round a non-tick-aligned TP upward to the next
tick (the 1R control already aligns). Verify actual fills against signal highs;
if they differ, planned TP and actual-fill risk are no longer the same RR.
Generate the experimental source from the current source with guarded text
replacements, retaining source hashes and the complete compiled copy.

## Measurements

Report trade count, gross/net profit factor, net dollars, net closed-balance
maximum drawdown, net/drawdown, gross/net average R, total net R, holding time,
entry-set changes and cross-date holds. Deduct $1 per completed trade in Python,
matching the preceding studies; MT5 PnL/statistics are gross. Show native MT5
gross open-equity drawdown separately; do not label closed-balance drawdown
as open-equity drawdown. Report yearly net dollars and net R for stability.

The primary execution policy here is the existing fixed one-contract setup;
assess net dollars together with drawdown, without treating profit factor alone
as the objective. Average R is a separate ideal equal-risk-weighting diagnostic,
not a claim that integer-contract constant-risk sizing has been tested. If the
two objectives disagree, report that instead of switching the verdict metric.

Compare the full threshold curve and consistency between periods. Added holding
time changes entry availability, so use native MT5 paths for every arm. The
same-entry first-touch estimate is explanatory, not the fixed-TP benchmark.
Do not change time windows, red-run cap, stops, or sizing during this comparison.

## Verification and evidence

Keep unique configs, original trade/stats CSVs, MT5 HTML reports, tester logs,
source and binary hashes, compile log, and a machine-readable manifest.
Require compilation without errors, successful full test completion, no
unexplained order failures, CSV count and profit reconciliation with MT5,
valid signal ranges, consistent entry fills and deal accounting. RR=1 bar-close
controls must reproduce previous cap-3 trades field by field.

Inspect the archive's fixed-TP implementation for context, but derive this arm
from the current runband to avoid introducing old entry/breakeven differences.
Inspect PA_milky_simplified for historical RR evidence and explicitly separate
window-routing/account objectives from this all-hours single-position test.
