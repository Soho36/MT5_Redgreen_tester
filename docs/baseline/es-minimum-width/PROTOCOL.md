# ES minimum signal width: 50 native ticks

2026-10-11. Recorded before new filter runs. Follow-up to [price resolution](../granularity/RESULTS.md) and [complete trade paths](../path-interaction/RESULTS.md).

## Question and fixed rule

Does the existing RTL strategy improve on ES when the original signal candle must span at least 50 native ticks? Test this one requested threshold, without a sweep, optimization or adoption of a new baseline. Run the every-bar market-buy control as a diagnostic of how the same width condition affects general long exposure.

Use `MEScontDTBNT20102026`, with the same data and settings as the previous complete ES path experiment. Four complete MT5 jobs: RTL baseline, RTL minimum width, market-control baseline and market-control minimum width. RTL uses red cap3; the control buys on eligible bars while flat irrespective of colour, with cap0.

The original built-in filter computes `(signal high - signal low) / _Point`. Its input unit is the symbol's quote point, rather than its exchange tick or an index price point. Verify and record actual symbol metadata before allowing a run:

| Quantity | Expected value |
|---|---:|
| Native trade tick | 0.25 index price points |
| `_Point` | 0.01 index price points |
| Requested minimum | 50 native ticks = 12.50 index price points |
| `MinCandleRange` input | 1250 quote points |
| `MaxCandleRange` input | 100000000 quote points = 1000000 index price points |
| One MES lot, dollar value | $5 per index price point; $1.25 per native tick |
| Minimum requested stop risk at one lot | $62.50 |

The minimum is inclusive: a range of exactly 12.50 passes. The maximum is deliberately nonbinding against the independently validated source M30 maximum of 363 index price points. A metadata guard must fail initialization if `_Point` or native tick differs from the expected units; do not silently reinterpret or adjust the threshold.

## Actual built-in filter behaviour

Baseline jobs copy the prior ES path INIs with `UseCandleRangeFilter=false`. Filtered jobs change only `UseCandleRangeFilter=true`, `MinCandleRange=1250` and `MaxCandleRange=100000000`; remaining strategy and tester inputs are identical to the corresponding baseline.

Use the existing filter exactly as implemented. At a new-bar entry decision while flat, it checks the preceding available M30 candle before the colour/run signal checks. A candle that fails the width condition cancels existing buy-stop orders, including an earlier order armed from a wider candle, even if the new candle is green or otherwise supplies no new signal. Existing-position management runs before this filter, so the condition neither closes nor changes the management of an already open trade. Pending orders can persist across bars that do not reject them.

This tests the full built-in rule, including skipped entries, altered pending-order lifetimes and changed opportunities while flat. It is not equivalent to removing small-width trades from the original ledger. A trade's signal is the candle recorded when its original entry order was armed; a stale pending fill must not be assigned the candle immediately before its eventual entry.

## Frozen run settings and provenance

Use the copied `RTL_width` expert produced from `path_collector_source.build_source()`, with the separate passive path collector and symbol-metadata initialization guard. Do not change original trading state, the existing bar-close exit, order handling or the logger's known behaviour.

Keep FromDate 2010-06-07 and exclusive ToDate 2026-07-14, ending on July 13. Automatic tester warmup begins trading June 10. Keep M30, tester Model1 (M1 OHLC), one MES lot, RR1, the original enabled trade windows, early-close calendar, flatten/fallback, spread/execution settings and disabled trailing stop. This uses generated tester quotes, rather than exchange tick replay.

Freeze the scripts, copied EA/includes/INIs, this protocol, prior raw and complete audited reference ledgers/reports/cache, the ES source CSV and source calendar in `Reports/es_width_filter_20261011/`. Source CSV is `F:\DATABENTO\ES_16_YEARS\MT5_ES_continuous_2010-2026_ohlcv-1m.csv`. Retain input/output hashes, complete MT5 HTML orders/deals, original raw outputs, complete observer outputs, actual symbol metadata and every validation result. Check frozen inputs before execution and interpretation.

## Validation gates

- Each baseline arm must reproduce its prior ES raw ledger byte for byte and its complete audited reference positions in count, identity, entry/exit times, profit and requested risk. Preserve raw files and reference history.
- All four jobs must reconcile complete positions against MT5 HTML orders/deals and tester counts, net profit, gross profit and gross loss. Use original order requested entry minus original SL for requested risk, preserving actual fill minus SL separately.
- Require zero observer errors, zero first-observation lag for every entry, zero active positions at completion, and matching observer/history/tester totals. Missing positions or excursions must not pass as complete paths.
- Verify actual `_Point`, native tick and $5-per-price-point metadata. Verify every filtered entry order's original recorded signal range is at least 12.50 points, including pending orders filled later. Do not validate width using the eventual entry's preceding candle.
- Any failed gate blocks interpretation of the affected comparison; do not replace it with a post-hoc width subset or assumed outcomes.

## Outcomes, periods and costs

Primary results use all complete EA trades for each of the four arms. Report 2010-15, 2016-19, 2020-26, the full span, every calendar year and the frozen entry-session groups: 01:00-16:30, 16:30-20:00 and 20:00-23:30 in the source clock (America/Chicago plus eight hours), not Tallinn civil time. Disclose any entries outside those groups separately.

For each arm report trade count and retention, mean gross R, mean net R, fixed-lot net dollars, gross/net profit factor, closed-trade net-dollar maximum drawdown, net dollars divided by that drawdown, and mean signal width/requested dollar risk. Use requested/signal risk times $5 per price point as the financial R denominator, matching prior expectancy studies. Distinguish mean R, which weights trades equally, from dollars and profit factor, which give wider-risk trades more weight. Drawdown uses cumulative net closed-trade profits including an initial zero; if also displaying MT5 floating equity drawdown, label it separately. Report a zero drawdown denominator explicitly rather than inventing a ratio.

Base cost convention is $1.05 per contract round trip, deducted once from each complete trade. Show two fixed additional-friction sensitivities: one native tick ($1.25 extra, total $2.30), and two native ticks ($2.50 extra, total $3.55), each applied once per round trip. These are arithmetic sensitivity assumptions, not estimates of real commissions, spread or slippage; do not alter execution or double-charge an extra tick on both entry and exit.

Secondary sensitivity excludes entries on the known ES source-hole dates 2020-02-28 and 2020-06-30 and trades crossing a source-calendar date, using the same exclusions in every arm. Preserve and enumerate their full-sample contribution. Do not make these exclusions primary or introduce outcome-driven exclusions.

Separately describe turnover: the baseline ledger's width-at-least-50 subset, its omitted trades, full-rerun entries shared with baseline, and entries newly available in the filtered run. Use original arming metadata and report exact identity/time matching, widths and counts. The subset is a descriptive counterfactual only; the full rerun supplies the primary performance result.

## Paired uncertainty and interpretation

Use 1000 paired resamples of complete source-calendar ENTRY days jointly across all four arms within each period, retaining zero-trade dates. Fixed seed 20261011 with deterministic period offsets. Recompute sampled mean R as total sampled R divided by sampled trades, rather than averaging daily means. Report paired 95% percentile intervals for filtered-minus-baseline changes in gross/net R and fixed-lot net dollars. Point profit factor, drawdown and net-dollar/drawdown comparisons are descriptive unless a separately disclosed uncertainty method is used. Whole-day resampling does not account fully for successive-day dependence or exploratory selection.

Call the RTL filter a useful historical candidate only if BOTH mean net R and fixed-lot net dollars improve against its baseline in BOTH modern eras (2016-19 and 2020-26), with positive filtered mean net R in both. Disclose intervals, yearly consistency, retained trade counts, risk distribution and additional-friction results alongside that assessment; do not hide an era, year or cost scenario that weakens it. The control is explanatory context, not a replacement for the RTL candidate comparison. Gross improvement alone, better expectancy with worse fixed-lot dollars, or improvement confined to one modern era does not meet this screen.

This is a retrospective test on already examined 2016-26 data, not a fresh holdout or confirmatory significance gate. No parameter selection, live-profitability claim or automatic strategy adoption follows from this result.
