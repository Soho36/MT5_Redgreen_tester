# Whipsaw follow-up: volatility forecasts and price-path structure

Written 2026-11-12, after the original study and review. Exploratory extension
on reused history, not independent confirmation. The original frozen rule,
protocol and results stay intact. No strategy or live settings change.
The user's mechanism is repeated stop-triggered order flow; frustration is a
consequence. OHLC prices cannot identify stops or establish that mechanism.

## Prior knowledge and data

Already seen: original matched difference +0.360 ATR; review M1 event paths
+0.358; M1-adjusted coefficient +0.151 (0.011 to 0.292) with range and recent5
controls. A quadratic M1 control also remained positive. These are not new tests.
No forecast or geometry-subgroup outcome for this follow-up has yet been run.
Hash this document and feature/analysis code before that run.

Use the original NQ minute cache and M30 data through September 2026. Verify all
seven original input hashes and frozen code/protocol; reproduce 4,180 sessions,
243 primary events, 174 in 2016-26. Keep the original session exclusions, lagged
ATR20 and M30 rule: at least three swings of 0.75 ATR. Neither rectangular nor
expanding geometry is required by it.

Target: next kept session's absolute open-to-close move / event-session ATR20.
Omit missing outcomes. 2010-15 initializes training; evaluate 2016-19, 2020-Sep
2026 and pooled. October/November data are unavailable here; adding them later
is retrospective. Prospective validation begins after specification, excluding
the motivating day.

## Volatility measures

Session M1 movement = square root of summed squared minute-close changes, first
change from session open. This is point-change volatility, not annualized return
volatility or total distance. It excludes overnight/roll gaps. Current movement
and the mean POINT movement over the preceding 5 and 20 kept sessions are each
divided by the current session's lagged ATR20. Histories exclude today.
Also retain preceding-five-session mean true range / ATR20.
A fixed sensitivity uses five-minute bucket closes for all three movement
features; first change still from session open. No frequency optimization.

## Forecast comparison

Refit each January 1, using all earlier feature sessions whose NEXT-session
outcome is also before January 1. Hold coefficients fixed for that year.
Scale using training data only. Ridge minimizes sum squared errors plus
10 times sum squared standardized slopes; intercept unpenalized. Clip negative
forecasts to zero. No hyperparameter search.

- Baseline: log1p(current range/ATR, M1 movement/ATR, prior5 movement/ATR,
  prior20 movement/ATR, prior5 true range/ATR); signed session body/ATR;
  current and next-session CPI/payroll/FOMC indicators; Tuesday-Friday dummies;
  event-session roll indicator.
- Plus whipsaw: baseline plus unchanged primary flag.
- Plus structure (secondary): plus-whipsaw plus bounded-initial-swings,
  expanding-initial-swings and bilateral-failure indicators, all zero outside
  primary whipsaw sessions.
- Five-minute sensitivity: baseline and plus-whipsaw, replacing all three
  movement features with the five-minute versions.

Primary metric: mean squared error reduction, baseline minus plus-whipsaw,
on ALL evaluation sessions. Positive is better. Report relative MSE reduction,
MAE, event-only results, each year and both eras as secondary views.
Paired month bootstrap: resample whole calendar months 5,000 times, seed
20261112; hold predictions fixed. Intervals describe scored-history uncertainty
conditional on fitted forecasts, not full model-estimation uncertainty.

Incremental forecast improvement is demonstrated in this historical exercise
only if pooled primary 95% interval is entirely positive and point estimates
are positive in both eras. Otherwise report unresolved/not improved, as
appropriate. Secondary comparisons cannot rescue it. Even a pass is exploratory,
not independent validation or a trading edge.

## Structure (secondary)

Trace the same M30 zigzag: initial extreme, reversal-confirmed extremes, terminal
extreme. Classify the first four alternating endpoints (initial three legs).
If leg three is still active at close, its endpoint is the observed terminal
extreme, not a future-confirmed pivot. Labels are known at session close and
describe the INITIAL sequence, not necessarily the entire day's geometry.

- Bounded: the two highs differ by at most 0.10 ATR AND the two lows do too.
- Expanding: second high exceeds first by more than 0.10 ATR AND second low
  falls below first by more than 0.10 ATR.
- Other: drift, contraction or mixed geometry. Do not call this rectangular.

Failed breaks use the previous kept session's high/low, fixed before today.
The FIRST breach per side must reach at least 0.05 ATR beyond the boundary;
a return is a close inside that boundary on the breach bar or next three M30
bars (four closing opportunities). A later retry cannot rescue an expired first
breach. Both sides must qualify for bilateral failure. On contract-roll dates,
previous raw levels are incomparable: label unavailable, bilateral indicator
zero, and use the common roll control in every model. These are price proxies,
not observed stop executions.

Report subgroup counts, next move, share >=1 ATR and observed minus plus-whipsaw
forecast, with month intervals. Structure-model improvement is secondary.
No subgroup is adopted as a rule; small groups and multiple comparisons limit
inference. Example charts show event sessions only, choosing first and middle
event by date in each geometry group, without inspecting subsequent returns.

## Timing and other checks

Record the close of the M30 bar where swing three is first detectable, never
backdate to the extreme. Describe remaining-session displacement and range
from NEXT bar open; exclude recognition bar. No remaining bars means missing,
not zero. This is not a fill simulation.

Reproduce the prior M1-adjusted coefficient and add one descriptive regression
with prior5/prior20 M1 movement, retaining original year/size-group effects and
month bootstrap. These do not measure forecast improvement or causal shares.

Save features/predictions under Reports/whipsaw_followup_20261112; publish
compact tables, chart, design record and RESULTS.md. Tests cover session
boundaries, lagging, causal pivot confirmation, first-break chronology,
year-boundary purging, training-only scaling, future-data invariance and paired
month resampling. No trading rule is developed in this extension.

Background: [realized volatility](https://www.chicagofed.org/publications/working-papers/2008/wp-14)
and [chronological evaluation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).
The choices above are this study's exploratory specification.

