# RTL blue VWAP slope only: scope amendment

Recorded 2026-11-01 after the initial descriptive tables were computed and checked.
The user narrowed the first study to the slope of blue session VWAP alone, without
the orange condition. The original [plan](SLOPE_PROTOCOL.md) and initial evidence
remain preserved; this amendment does not claim to precede those outcomes.

The published comparison is **baseline RTL versus RTL with rising VWAP only**.
No requirement for signal price to be above either blue VWAP or the orange cutoff.
No GG test. The exact slope definition, periods, costs, data and availability checks
remain those of the original plan: VWAP at the completed M30 signal close minus
VWAP at the preceding M30 close; both within the same session and exactly 30 minutes
apart. Positive slope permits a new order; negative, zero or unknown blocks it.
Slope does not need A20 and is not rechecked at a subsequent fill.

Publish the already verified `baseline` and `rising` policy rows, annual rows,
unconditional up/down/flat/unknown groups and unknown reasons. The only diagnostic
comparisons are `known_baseline` (all trades with measurable slope) and
`rising_risk_scaled_baseline` (fractional exposure control). Exclude all orange
policies and orange-conditioned groups from the publication and extracted tables.
No new masks, thresholds, windows or trade outcomes are calculated.

Read the original verification and source/output hashes before publication. Save
the exact selected rows and a manifest under `Reports/rtl_vwap_slope_blue_20261101/`;
verify they equal the originals, and that daily curves and group metrics refer to
the unconditional rising-only policy. Publish `SLOPE_RESULTS.md` and a two-policy
equity/drawdown chart; update journal, status and index.

This remains descriptive baseline-trade omission on previously studied NQ history.
Later orders freed by skipped trades require a separate native replay. No EA change
or adoption decision follows from this study.
