# Five completed daily closes as a direction filter for M30 RTL

**Keep unfiltered RTL.** From 2020 through September 2026, the daily gate reduced net profit by $20,377.50 (53.1%) and maximum closed-trade drawdown by $64.60 (1.1%). The earlier M30 slope gate earned $6,212.90 more than the daily gate in that period with $1,667.15 less drawdown.

## Native MT5 comparison

Each cell shows **after-cost net profit / maximum closed-trade drawdown**. Results use one MNQ-equivalent on continuous NQ history, $2 per point and $1.05 per completed trade. Each period starts at zero for drawdown measurement. Period assignment uses order submission time.

| Period | Unfiltered M30 RTL | Five-close D1 gate | Seven-close M30 gate |
|---|---:|---:|---:|
| Jun 2010–2015 | −$7,496.20 / $8,254.05 | −$5,813.90 / $5,859.95 | −$5,873.85 / $6,371.80 |
| 2016–2019 | $4,416.65 / $2,175.90 | $1,155.00 / $1,127.45 | $3,624.30 / $784.75 |
| 2020–Sep 2026 | $38,399.95 / $5,781.15 | $18,022.45 / $5,716.55 | $24,235.35 / $4,049.40 |
| 2016–Sep 2026 | $42,816.60 / $5,781.15 | $19,177.45 / $5,716.55 | $27,859.65 / $4,049.40 |
| Full period | $35,320.40 / $8,802.95 | $13,363.55 / $6,981.85 | $21,985.80 / $6,371.80 |

The daily gate reduced losses in 2010–15. In 2016–19 it gave up 74% of net profit for a 48% drawdown reduction. In the recent period, its net profit per dollar of drawdown fell to 3.15 from 6.64 for unfiltered RTL. The M30 gate earned more with less drawdown than the daily gate in both periods since 2016.

## Which M30 trades did the daily gate exclude?

| Period | Trades kept | Net from trades kept | Baseline trades excluded | Net from excluded trades |
|---|---:|---:|---:|---:|
| Jun 2010–2015 | 5,458 | −$5,813.90 | 3,706 | −$1,682.30 |
| 2016–2019 | 3,730 | $1,155.00 | 2,437 | $3,261.65 |
| 2020–Sep 2026 | 5,991 | $18,022.45 | 4,510 | $20,377.50 |

In the recent period all 4,510 excluded trades occurred on falling-slope days. They averaged $4.52 net per trade versus $3.01 for the trades on rising-slope days. Across the entire native replay, every retained trade matched its baseline counterpart in submission, entry, exit and profit. With the daily gate fixed throughout each trading date, skipping orders produced zero additional fills in this sample. The early excluded group includes 15 trades during the five-close warm-up and six trades at exactly zero slope.

## Construction and verification

The tester stayed on M30 using the existing M1 OHLC model. Each candidate new M30 buy stop required a positive ordinary least-squares slope over five completed native D1 closes. The gate uses the symbol's MT5 session dates, skips non-trading days and rolls across week boundaries. The forming D1 candle never enters the calculation. Order replacement, trading windows, stops, exits and flattening follow baseline RTL.

The control reproduced all 25,833 archived trade rows byte for byte. Reported statistics exclude the partial October 1 endpoint, leaving 25,832 baseline trades and 15,179 daily-gated trades through September. Rebuilding D1 closes from the final M30 close of each observed date verified the most recent completed daily bar, slope and eligibility for every candidate decision (60,193 control and 71,679 gated). Native deals, ledgers, dates, levels and price-based profits reconciled. This was one fixed rule evaluated on previously studied history.

[Protocol](PROTOCOL.md) · [Earlier M30 experiment](../rtl-regression-slope/RESULTS.md) · [Study setup](../../../python/prepare_rtl_daily_regression.py) · [Verification](../../../python/analyze_rtl_daily_regression.py) · [Summary CSV](../../../Reports/rtl_daily_regression_slope_20261125/summary.csv) · [Attribution CSV](../../../Reports/rtl_daily_regression_slope_20261125/attribution.csv)
