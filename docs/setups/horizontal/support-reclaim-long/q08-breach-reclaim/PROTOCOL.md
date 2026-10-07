# Q8: does a support breach followed by a reclaim predict an upward response?

Frozen 2026-10-03 before computing new classifications/outcomes. User selected
the support-reclaim question and provided a discussion distinguishing it from
the separate resistance-touch/path study. This study implements the support
comparison only; examples in that discussion are not observations.

## Scope and populations

- Primary reference: **current-session low**, motivated by the Q6/Q7 finding.
  Previous-session and previous-week lows are separately reported comparisons,
  not alternate winners. Use the exact Q6/Q7 map construction, frozen before
  the signal opens, with the same full-session dates and roll exclusions.
- Use the established M30 RTL baseline, MaxRedRun=3, MinLocation=0, RR=1,
  original windows, one contract, calendar/fallback flattening, OHLC model.
  Periods remain 2016-01-01 to 2020-01-01 and 2020-01-02 to 2026-07-14,
  with exclusive end dates. All history has previously been inspected.
- **Price-response population:** all qualifying order attempts logged by the
  fixed-1R run in `Reports/trend_rr_20261002/`, selected by submission time.
  The logger runs before OrderSend, so these are attempts, not proof of broker
  acceptance. Include attempts that never fill. Check every logged signal's
  OHLC, timestamps and red-run cap, verify the saved run parameters and errors,
  and reconcile its filled trades with the original baseline exports.
- **Trade population:** original filled trades in `Reports/entry_shape_20261002/`.
  Attach the level/classification to the original signal, not the later entry.
  Retain $1.05 round-trip commission and $2/point; net R divides net dollars by
  the original signal range times $2. Signal-level future price returns are not
  trade PnL and have no hypothetical fills or costs applied.
- Rebuild price/level references and repeat baseline audits. Save input,
  dependency and protocol hashes. Do not alter the old Q6/Q7 results or gates.

## Classification known at the signal close

Let L be the pre-existing low, O/H/S/C the signal open/high/low/close, and
R = H-S > 0. All RTL signal candles are red. NQ price increments in these
exports are 0.25 points; verify prices lie on this grid.

Use mutually exclusive groups in this order:

1. **Unavailable:** map has no history or crosses a contract roll; keep the reason.
2. **Opened at/below level:** O <= L. Keep separate so a signal already below
   the level is not mistaken for a fresh downward breach. Record gap-down from
   prior close >= L to O < L separately as metadata, without a new filter.
3. **No contact:** S > L.
4. **Touch only:** S = L.
5. **Breach + reclaim:** O > L, S < L and C > L.
6. **Breach + unrecovered:** O > L, S < L and C < L.
7. **Breach + exact close:** O > L, S < L and C = L; not silently pooled with
   reclaim or unrecovered.

The primary contrast is reclaim versus unrecovered. The broader **all fresh
breaches** group (reclaim + unrecovered + exact close) is descriptive; it overlaps
the reclaim group and is not an independent control. No-contact/touch groups are
context, not substitutes for the primary control.

Save exact penetration in ticks and R for every fresh breach. Primary breach is
at least 1 tick; predefined sensitivity samples require at least 2 or 4 ticks,
without redefining shallower breaches as no contact. Descriptive penetration
bins: 1 tick, 2-4 ticks, 5-8 ticks, >8 ticks. No optimized cutoff.

## Independent post-signal price response

To avoid calling the already-observed reclaim itself a predicted reversal,
measure **additional upward movement after the signal closes**.

- Primary horizon: 3 subsequent M30 bars (90 minutes). Neighbors: 1 and 6 bars.
- Endpoint return = (future close - signal close) / R.
- Primary upward-response event: endpoint return >= +0.5R. Also report the
  share strictly > 0, mean/median endpoint return, and maximum upward/downward
  excursion from signal close over that same window in R.
- Require every expected M30 bar, within the signal's same trading session,
  and require submission in the next M30 slot (before its end). Otherwise mark
  unavailable; do not roll across overnight/holiday gaps or early closes.
  Report counts and exclusion reasons per group/horizon.
- These outcomes use future prices only as labels. They never enter a signal's
  classification. No assumption about within-bar high/low ordering is needed:
  endpoints and separate maxima/minima do not claim which barrier was hit first.
- All logged attempts remain subject to the baseline's position availability;
  this is not a census of every red candle or every market breach. Distinct
  attempts may have overlapping future windows; use calendar-month blocks.

## Trade outcomes and reporting

For each source, group, period and year report n, net dollars, net PF, average
net R, net win rate, average/median MAE and MFE in R, and average signal range.
For all attempts report future response metrics and whether a matched baseline
trade filled. Include both source-specific coverage and a common sample eligible
for all three sources (per horizon for price response). Preserve yearly and
penetration-bin tables, even for sparse groups; flag n < 200 in period contrasts.

Primary differences are reclaim minus unrecovered in mean endpoint R and in
the probability of >= +0.5R at 3 bars, and mean net trade R. Use 2,000 paired
calendar-month block bootstrap resamples, seed 20261003, with all months retained.
Intervals are descriptive 95%, unadjusted for multiple comparisons.

## Interpretation and follow-up gates

Answer the direction, size, uncertainty and counts; do not force a binary
market-behavior claim from a filter-selection rule. A stronger reclaim pattern
in only one period is period-dependent; missing counts mean inconclusive.

A primary-source candidate for a separately specified full MT5 filter experiment
requires all of the following, fixed now:

- At 1-tick breach and 3-bar horizon, both groups have >=200 attempts in each
  period. Reclaim has higher mean endpoint R and a higher +0.5R response rate
  in both periods, with both descriptive difference intervals above zero.
- Filled reclaim trades have >=200 trades per period, as does unrecovered;
  reclaim has net PF > 1, PF greater than unrecovered, and greater average net R
  in both periods. No requirement that the unrecovered group itself must lose.
- Positive price-response differences persist at both 1- and 6-bar horizons,
  both 2- and 4-tick samples, and on the common-source 3-bar sample, with >=200
  attempts per group/period for each comparison. These sensitivity intervals
  need not exclude zero.

If these gates fail, retain the finding and do not search a new cutoff/source.
No live EA change. Any future strategy improvement claim requires a full MT5
rerun; removing existing trade rows cannot model changed position availability.
This does not identify stop orders, prove a causal liquidity mechanism, or show
that lows outperform equally distant non-level prices. OHLC execution limitations
remain; no generated-tick runs are authorized by this protocol.
