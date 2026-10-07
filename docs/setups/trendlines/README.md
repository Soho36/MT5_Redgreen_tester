# Trendlines

Setups at rising and falling trendlines. One folder per setup, one subfolder per study:
[uptrend bounce](uptrend-bounce-long/README.md),
[uptrend breakdown](uptrend-breakdown/README.md),
[downtrend breakout](downtrend-breakout-long/README.md),
placeholders: [downtrend bounce (short)](downtrend-bounce-short-placeholder/README.md),
[downtrend bounce (limit, long)](downtrend-bounce-long-placeholder/README.md),
[uptrend bounce (limit, short)](uptrend-bounce-short-placeholder/README.md). [All docs](../../README.md).

The text and table below are the study log.

Started 2026-10-04. This study is kept separate from the
[horizontal price-level study](../horizontal/README.md) but asks the same
questions: do red RTL signals at rising trendline support do better than
every other signal (Q11-style), and does broad contact with any unbroken
rising line (Q12-style)? It uses the same baseline population, original exit
and follow-up gate. Generated outputs go under `Reports/trendlines/`.

| Study | Status | Outputs |
|---|---|---|
| [Q14: rising trendline support](uptrend-bounce-long/q14-trendline-support/RESULTS.md) ([protocol](uptrend-bounce-long/q14-trendline-support/PROTOCOL.md)) | Complete 2026-10-04: candidates **worse** than every other signal in both periods (PF 1.029/0.950 vs 1.114/1.124); broad contact also worse; no filter | `Reports/trendlines/trendline_support_20261004/` |
| [Q15: falling trendline resistance](downtrend-breakout-long/q15-falling-resistance/RESULTS.md) ([protocol](downtrend-breakout-long/q15-falling-resistance/PROTOCOL.md)) | Complete 2026-10-04: **passes the gate** (PF 1.325/1.332 vs 1.088/1.090; both sensitivities and broad contact agree). Gap carried by entries below the line, weak in 2023-25. Qualifies for a full MT5 run protocol only | `Reports/trendlines/trendline_resistance_20261004/` |
| [Q16: Q15 concentration audit](downtrend-breakout-long/q16-resistance-concentration/RESULTS.md) ([protocol](downtrend-breakout-long/q16-resistance-concentration/PROTOCOL.md)) | Complete 2026-10-04: edge spread over 887 lines / 439 weeks; survives every single year/week deletion and symmetric trimming; week-bootstrap mean R just includes zero | `Reports/trendlines/resistance_concentration_20261004/` |
| [Q17: stand-alone candidate EA](downtrend-breakout-long/q17-standalone/RESULTS.md) ([protocol](downtrend-breakout-long/q17-standalone/PROTOCOL.md)) | Complete 2026-10-04: **does not survive** its own execution. PF 1.24/1.24 but mean R +0.039/+0.050 vs baseline -0.004/+0.060; 4/11 years. Freed trades ~break-even; no filter | `Reports/trendlines/resistance_standalone_20261004/` |
| [Q20: buy limit resting on a rising trendline](uptrend-bounce-long/q20-trendline-limit/RESULTS.md) ([protocol](uptrend-bounce-long/q20-trendline-limit/PROTOCOL.md)) | Complete 2026-10-05: **fails on its own numbers**. PF 0.773/0.969, mean R -0.238/-0.023; 45% of trades stopped in the fill bar; beats the matched control in 2/9 years. No filter, no strategy | `Reports/trendlines/trendline_limit_runs_20261005/` |
| [Q21: short the breakdown of a rising trendline](uptrend-breakdown/q21-breakdown-short/RESULTS.md) ([protocol](uptrend-breakdown/q21-breakdown-short/PROTOCOL.md)) | Complete 2026-10-06: **fails**. PF 0.893/0.916, mean R -0.081/-0.025; loses before costs; beats the any-red-bar control in mean R but only 6/11 years. Every red-candle short loses on NQ. No filter, no strategy | `Reports/trendlines/trendline_breakdown_runs_20261006/` |
| [Q22: RTL longs at or after a rising-line break](uptrend-breakdown/q22-breakdown-rtl/RESULTS.md) ([protocol](uptrend-breakdown/q22-breakdown-rtl/PROTOCOL.md)) | Complete 2026-10-06: **no gate passes**. Buying the breakdown candle's high is worse than every other signal (PF 1.010/0.831 vs 1.111/1.123; 2020-26 interval excludes zero) but S1 disagrees, so no skip filter. 10 bars after a break: no difference | `Reports/trendlines/breakdown_rtl_20261006/` |

The old [`Trendline_rejection.cs`](../../../mt5/Trendline_rejection.cs) EA was
the source of the idea and is not used for testing.
