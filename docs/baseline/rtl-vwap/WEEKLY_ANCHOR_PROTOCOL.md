# RTL M30 weekly-anchored VWAP: exploratory screen

Frozen 2026-11-20, before inspecting weekly-anchor outcomes. Test the user's
weekly reset with the existing far-below RTL entry rule and baseline trades.

Build weekly VWAP from the existing validated NQ minute HLC3 price-volume sums
and real volume, accumulated from the first observed bar in each Monday-Sunday
source-date week (Chicago plus 8 hours). Holidays do not move the boundary.
Use the latest completed M30 bar available at submission, including across
daily session boundaries within the same week. At the first submission of a
new week, a prior-week feature is unknown and is kept. Missing or nonpositive
A20 is unknown and kept. Flag strictly close < weekly VWAP - arithmetic A20;
equality is kept. A20 remains the last 20 completed M30 true ranges.

Use the unchanged original RTL baseline and $1.05 per completed trade, 2010-15,
2016-19 and 2020-September 2026; October's incomplete session excluded. Compare
baseline and weekly omission to the original session-VWAP omission with unknowns
retained. Report skipped/retained counts, dollars, mean R, daily-close drawdown,
duration, annual outcomes, exposure and static same-holding/same-risk baselines.
Do not adjust thresholds or select an anchor after seeing results.

The first screen deletes trades from the baseline ledger: it cannot account for
order cancellation or new trades enabled by being flat. It is not a full engine
replay, independent validation or a basis for adoption. Weekly VWAP can span a
futures roll in the raw continuous source, mixing contract price levels; report
that limitation. Repeatedly inspected NQ history and fixed-period selections
are exploratory. Source timestamps and data coverage match the earlier study.

Verify weekly accumulation independently, exact as-of timing, week-boundary
unknown and equality behavior, weekly/session baseline reconciliations, and
economic partitions. Save script, tables and results; no strategy changes.
