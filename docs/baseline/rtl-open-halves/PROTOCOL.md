# RTL cash-open half-hour study

2026-11-11. User-requested follow-up to the full 16:00-17:00 exclusion.
Frozen unfiltered RTL source/inputs: Reports/rtl_gg_exclude16_20261101.
One contract, MaxRedRun=0, M30, RR=1 bar-close exit, 1-minute OHLC,
$2/point, $1.05 per closed trade externally. No VWAP. Chicago+8 clock.

Four native runs: unchanged control; exclude submissions [16:00,16:30);
exclude [16:30,17:00); exclude both. Modify only the existing window function.
Keep position management, pending cancellation and boundary-fill semantics.
Control/both ledgers must reproduce earlier matching runs byte for byte.
No production-default changes and no extra flatten at the cash open.

Verify report orders/deals against ledger timestamps, prices, economics and
stats. Verify forbidden submissions absent; gross sampled equity DD matches
native DD. Report 2016-19, 2020-Sep2026, pooled 2016-Sep2026, secondary 2010-15
and annual. Exclude incomplete October observations from published metrics.

Descriptive baseline: actual-fill and submission half-hours separately;
entry-origin by exit-half-hour around 16:00-18:00, especially 17:00-18:00.
Show gross wins/losses, net, count, R and stops identified by native comment.
For positions filled before and still open at 16:30, report 0-5, 5-15,
15-30 minute stop events and eventual outcomes with the whole cohort denominator.
Separate earlier orders filled after open from positions already open.
Report before-16:00, 16:00-16:30, 16:30-17:00, 17:00+ origins, prior dates apart.

Historical exploratory association cannot establish volatility as the cause.
Native reruns capture changed opportunities, unlike simple ledger omission.
No further window optimization or adoption verdict.

