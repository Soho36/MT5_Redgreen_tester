# RTL short above VWAP + A20

2026-11-01. User-requested descriptive upper-band experiment on reused NQ
history. Freeze before inspecting new outcomes. No threshold search.

Question: does an overextended green M30 signal offer a shorting edge?
Allow a new short only if its completed signal closes strictly ABOVE
full-session HLC3 VWAP + arithmetic A20. Green-candle sell stop at its low,
stop at high, 1R bar-close exit, no run cap, existing session windows,
early-close calendar and flatten/fallback remain unchanged. Equality and
unknown/stale labels cannot qualify. Gate submission, not later fills.

Use a separate tester-only RTL_short_vwap_upper EA with ShortVwapSide
(below=0, above=1). Above/+1 is its research default. Lower-band reproduction
uses below/-1; the previous installed lower/blue EA is unchanged. Orange is
VWAP + VwapFarBelowZ*A20, so it lies above VWAP for +1. The existing file
already stores VWAP/A20 separately: use the identical causal label bytes.

Native MT5, one MNQ ($2/point), 1-minute OHLC, $1.05 per completed trade,
same NQ symbol/history and dates. First require lower/-1 to reproduce the
previous orange ledger byte for byte and all native totals before upper/+1.
Check every candidate and every original order against frozen labels and
native report/ledger totals. Preserve inputs, compiled source and outputs.

Primary periods: 2016-19 and 2020 through September 2026 by submission
session; 2010-15 and pooled 2016-26 descriptive. Compare unfiltered, lower,
blue, and upper shorts: trades, net $, gross/net mean R, net PF, daily-close
and closed-trade DD, annual stability, and extra $1/$2 costs. Four-week
block-bootstrap intervals are descriptive uncertainty checks. Illustrate
upper shorts plus the original gated RTL long by summing independent one-
MNQ legs, without netting (not a switching or netting-account replay).

Positive net in both primary eras is only a minimum screen. Assess costs,
R expectancy and drawdown. This test does not establish an out-of-sample
edge or authorize live adoption. Also provide and test a reusable label
exporter and brief instructions; no new threshold-specific file is needed.
