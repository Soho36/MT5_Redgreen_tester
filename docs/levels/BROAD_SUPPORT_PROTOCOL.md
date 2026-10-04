# Q12: broad contact with support-origin levels

Specified 2026-10-04 before computing Q12 outcomes, following the user's request
to test every red candle interacting with support and retain previously broken
levels throughout the rolling window. Q10/Q11 outcomes and subgroup tables have
already been examined: this is an exploratory extension, not an untouched test.

## Question and fixed definitions

Does broad contact identify better existing RTL trades than every other
qualifying red signal? A support-origin level remains eligible regardless of
previous breaks, prior departure, approach direction, signal penetration depth,
or signal open/close side. Price activity around a level is not by itself
evidence of a profitable long entry.

Primary: Q11's confirmed M30 swing lows, N=5, current session plus five completed
sessions. Keep Q11's causal confirmation, contract-roll exclusions, lagged
ATR(14), D=0.5 ATR, and greedy merging unchanged. Contact means the red candle's
range overlaps [L-D,L+D]. There is no broken/departed state in eligibility.
Pivots expire only through the rolling window, subject to the existing roll
exclusion; merged zones are still recomputed with the signal's lagged ATR.
Keep two weeks/N=5 and one week/N=3 as the two fixed sensitivities.

Secondary context: current-session, previous-session and previous-week lows
already known before the signal. Contact means low <= level <= high (an exact
price, not an ATR zone, preserving the original session/week question). Include
signals opening at or below the level and any previous breaches. Do not pool
these different sources or select the best after seeing results. A current
session low updates causally as the session develops; a previous-week low is a
calendar-week extreme, not a rolling swing low.

## Population and outcomes

Reuse Q10's original RTL bar-close-qualified >=1R exit, protective stop, pending
order rules, MaxRedRun=3, all enabled windows, session flattening, $2/point and
$1.05 round-trip cost. Fixed +1R TP is not this baseline. Preserve the 52,070
potential signals, 35,632 attempts and 14,968 fills across 2016-2019 and 2020-2026
(period boundaries unchanged from Q11). "All red signals" means this qualifying
baseline population, not reds excluded by its existing red-run/session rules.

For each definition and period/year report contact, every other signal, available
no-contact and unavailable, plus baseline totals. Compare PF and average net R;
report counts, fill conversion, net profit, win rate, R distribution and exit
reasons. Attribute baseline drawdown contributions without calling them filtered
strategy drawdown. Bootstrap candidate-minus-complement and candidate-minus-
available-no-contact differences using 2,000 paired calendar-month resamples,
seed 20261004. Intervals are descriptive and unadjusted for multiple comparisons.
Keep Q11's old categories only as an explanatory breakdown, not eligibility.

Reuse Q11's follow-up gate for the primary/sensitivities: >=200 fills in both
groups and periods; contact PF>1 and higher PF/mean R in both periods; mean R
better in >=7/11 eligible years; both sensitivities point the same way in both
periods. Passing would only justify specifying a full strategy rerun. Failing
means no broad filter supported by this screen, not that all possible levels
have been disproven. No search for new window/N/zone/shape thresholds.

## Verification and outputs

- Fail on any missing or mismatched upstream manifest entry before loading.
- Independently compute broad contact from prices; check all swing classifications
  against the union of Q11's four contact categories, without changing Q11 files.
- Rebuild session/week maps from M30 prices and compare saved Q10 levels/status.
- Reconcile every partition's signals, attempts, fills and net with baseline;
  test confirmation, expiry, roll/ATR exclusions and unrestricted contact cases.
- Save input/code/protocol hashes, verification, classified signals, filled
  trades, groups, contrasts and decision to
  `Reports/levels/broad_support_20261004/`. Version the results in
  `docs/levels/BROAD_SUPPORT_RESULTS.md`.

This is attribution of existing fills, not hypothetical fills for every red
candle: excluding signals changes later order/position availability. Original
one-minute OHLC execution limitations remain; no new MT5 or generated-tick run.
