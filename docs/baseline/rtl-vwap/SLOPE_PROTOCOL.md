# RTL: rising session VWAP as an entry filter

Plan recorded 2026-11-01 before computing slope labels or their outcomes. User
requested RTL only. Descriptive study on already examined NQ history; no fresh
confirmation claim, threshold search, EA change or automatic MT5 replay.

## Definition

At submission, compare the completed signal M30 candle's session VWAP with the
preceding M30 candle's session VWAP: `delta = VWAP[t] - VWAP[t-1]`.
Both must be available, finite, exactly 30 minutes apart and in the same session,
with strictly positive added volume. No difference across session resets or gaps.
Join features with `available_at <= submitted`; the feature must be the signal
candle (high = requested buy stop, low = original stop, close < open). Labels
from another submission session are unknown. Slope needs no A20 warmup.

- Rising: delta > 0; trading enabled.
- Falling: delta < 0; new entries disabled.
- Flat: delta = 0; new entries disabled.
- Unknown: new entries disabled under the strict rising-only policy; report the
  reason and outcome separately. No threshold around zero is optimized.

Units are price points per 30 minutes, not screen angle. Include the signal
candle in the slope: this is the direction known when placing the order, not a
trend measured before the signal candle. Slope sign is mechanically related to
the latest candle's volume-weighted price relative to preceding session VWAP;
it is not an independent confirmation indicator.

## Fixed sample and policies

Use the reconciled and independently verified RTL NQ baseline, frozen full-session
HLC3/real-volume features and session calendar in `Reports/rtl_vwap_cross_20261027/`.
Same baseline settings and economics: one contract, $2 per point, $1.05 cost/trade.
Periods by submission session: 2016-19, 2020-Sep 2026, pooled 2016-Sep 2026;
secondary 2010-15. Exclude October 2026.

Compare baseline, current orange close filter, rising VWAP only, and orange plus
rising. Orange means skip signal close < VWAP - A20, equality/unknown kept as
before. For slope, flat and unknown are blocked. Also show baseline and orange on
the common slope-known subset to distinguish direction from availability effects.
No GG analysis. No other slope windows, smoothing, thresholds or entry changes.

Measures: retained count, net dollars, mean gross/net R, dollar PF, win rate,
daily-close DD, net/DD, planned initial risk retained; annual versions. Daily P&L
uses submission sessions and the complete frozen calendar as in previous studies.
Group outcomes by up/down/flat/unknown crossed with orange eligibility; report
unknown reasons. Report delta median and extrema, plus normalized delta/A20 where
available, for description only. Fixed exposure controls: scale baseline to rising
policy's retained planned risk, and orange to orange-plus-rising's retained risk.
These fractional-size controls are descriptive, not one-contract executable policies.

## Limits and checks

Ledger omission retains original fills/exits; it does not create later orders made
possible by skipped trades or recheck slope at fill. Native replay is a separate
experiment. Hash source data, protocol and analysis code before outcomes; require
the earlier independent verification to have passed. Reproduce existing baseline
and orange summaries. Check causal feature matching, signal OHLC, session resets,
gaps, positive added volume and partitions/profit reconciliation. Unit-test boundary
cases on synthetic bars. Independently rejoin frozen features, compute slope via
the cumulative-VWAP update identity, and recompute labels, summaries and daily paths.

Save evidence under `Reports/rtl_vwap_slope_20261101/`; publish
`SLOPE_RESULTS.md`, chart and code; update journal/status/index. No adoption verdict.
