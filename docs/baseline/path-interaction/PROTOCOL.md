# NQ / coarse NQ / ES path interaction experiment

2026-10-09. Recorded before new path outcomes. Follow-up to [fixed-grid resolution](../granularity/RESULTS.md) and [NQ versus ES](../nq-vs-es/RESULTS.md).

## Question and fixed histories

Within comparable signal-candle size, entry year and entry session groups, how do complete RTL and every-bar market-control paths differ between native NQ, the existing ES-like coarsened NQ, and ES? Examine adverse/favourable excursion, stop before reaching +1R, +1R reach, and retention at the subsequent M30 close.

Use the six original paired signal-colour arms: RTL red cap3 and market-buy control on `MNQcontDTBNT20102026_2`, `MNQcoarseDTBNT20102026`, and `MEScontDTBNT20102026`. Coarse NQ is the prior yearly grid (`build_coarse_nq.K`: 0.50-1.50 points, nearest ties-to-even), rather than a grid chosen using the new performance curves. Native NQ/ES step is 0.25 points. All symbol trade ticks remain 0.25. Dollar values are $2/point on MNQ/coarse and $5/point on MES; paths are normalized to risk.

Same dates and original INI settings: FromDate 2010-06-07, exclusive ToDate 2026-07-14; M30, M1 OHLC tester, RR1 bar-close market exit, one lot, original windows, early-close calendar, flatten/fallback, no trailing stop. No new filters or parameter optimization. Analyze 2010-15, 2016-19, 2020-26 and full span separately.

## Complete path collection and reproduction gate

A separate observer wraps a copy of the original EA's OnTick before and after its unchanged strategy handler. It observes actual tester Bid quotes from position opening through exit and includes the terminal deal price. It does not submit orders, change strategy globals or replace the original logger. Track POSITION_IDENTIFIER / DEAL_POSITION_ID, initializing market entries after the original handler so immediate stops are included. A replacement position is finalized before initializing the next one. Record original order metadata when submitted, including the preceding available M30 signal bar; a pending buy stop can persist, so entry's preceding bar is not necessarily the signal.

Export complete per-position paths, original successful entry orders, every observed M30 closed bar, and actual ManageOpenPosition target checks. Bind observations to original order/deal identities, requested entry and original SL, actual fill, timestamps and exit reason. Preserve both requested risk (original requested entry minus original SL) and actual filled risk (actual fill minus original SL).

Each of the six jobs must reproduce its prior RAW trade ledger byte for byte. The path ledger must then match its already-audited COMPLETE orders/deals in count, entry/exit times, profits and original risk, including formerly omitted fast-stop controls and corrected logger-risk rows. Observer errors, missing/duplicate positions, wrong risk, changed trades or unreconciled tester totals stop analysis. Export actual locked EA targets separately from per-position risk; flag stale-reference discrepancies without fixing strategy behavior.

## Path outcomes

- Primary path MAE is nonnegative `(actual fill - minimum Bid)/actual filled risk`, floored at zero. MFE is nonnegative `(maximum Bid - actual fill)/actual filled risk`, floored at zero. Use the entire observed holding period and terminal exit price; no pre-entry minute extrema or after-exit continuation is credited.
- Record first +0.5R/+1R touch in chronological tester quotes, its time and M30 bar. Record maximum adverse excursion before the first +1R touch for reachers. Financial expectancy retains requested/signal-risk normalization to reconcile prior studies.
- Stop-first means an actual SL exit before any +1R touch. Stop after +1R is separate. Session flatten, other exits and paths reaching neither barrier are not automatically counted as stop-first. Report all event shares and denominators.
- For +1R reachers, identify the first closing evaluation of that SAME M30 touch bar. Split outcomes: stopped before an eligible check, administrative exit before an eligible check, no available check/censor, checked with close below actual +1R target, checked with close at/above actual +1R target. The target condition is >=, matching the EA.
- Report qualifying close probability among ALL +1R reachers and conditional on an eligible surviving check. Flatten runs before target management at cutoff; reaching +1R and a hypothetical later price close does not count as a surviving target check.
- Source M30 close at/above target after an exited trade can be reported only as a separately labelled hypothetical continuation diagnostic. Export actual EA target/condition to distinguish rule execution, stale-reference cases and geometric target retention.

## Comparable groups, support and weights

All primary matching variables are available before outcomes: ENTRY calendar year, ENTRY source-clock session, and original SIGNAL candle range / effective data-grid step. Source clock is America/Chicago with US DST plus eight hours, as in build_continuous.py; it is not Tallinn civil time.

Sessions are 01:00-16:30 (pre-cash), 16:30-20:00 (early cash), and 20:00-23:30 (late cash). Step-count bins are [0,8), [8,16), [16,24), [24,32), [32,48), [48,64), [64,128), [128,infinity). Effective coarse grid uses the SIGNAL year's fixed K, not the eventual fill year. Session, year and step bin define a cell.

Primary common support requires at least 30 trades and at least 10 distinct ENTRY dates in every one of the six instrument/strategy arms in a cell. Give each common cell weight proportional to the minimum trade count across those six arms, normalized once before resampling. Use these same cells/weights for both strategies, so differences between their adjusted summaries are comparable.

Also report a broader coarse-NQ/ES four-arm comparison using its own common cells and minimum-count weights; three-instrument overlap may retain a small fraction of native NQ. Report native-quarter-tick size matching as a sensitivity (same bins, signal range / 0.25), since effective coarse steps and actual trade ticks differ. Never conceal changed estimands: report retained cells, trades and entry-day coverage for each arm, size/session strata, and all unadjusted results. Bins leave residual size variation; matching does not establish causality.

Known ES source-hole dates 2020-02-28 and 2020-06-30 are excluded from ALL arms in primary matching. Cross-date trades are also excluded from matched analyses. Preserve complete full-sample totals, enumerate these exclusions and report their unadjusted context. No additional outcome-driven exclusion or matching choice.

## Uncertainty and artifacts

Use 1,000 common resamples of whole source-calendar ENTRY days jointly across instruments/strategies within each period, retaining zero-trade dates. Fixed seed 20261009 with deterministic period offsets. Common support and weights stay fixed; recompute cell means/probabilities within each resample. If any retained arm/cell has zero denominator, reject/retry that complete common draw and report retry count rather than silently changing support or weights. Report paired 95% percentile intervals for adjusted contrasts. This does not capture longer serial dependence, uncertainty in selected weights, multiple-comparison selection or broader exploratory selection.

Store generated EA/includes/INIs, frozen protocol/source/input hashes, complete reports, original raw ledgers, observer outputs, checks and analysis tables in `Reports/path_experiment_20261009/`. Final interpretation belongs in RESULTS.md. Generated tester quotes are synthetic M1 OHLC paths; conclusions concern this tester and these strategy-conditioned observed holding periods, not exchange tick replay, an ES order-book mechanism or a validated trading rule.
