# Failed-breakout shorts after a red M30 candle

2026-11-06. Waiting for the next candle to break the red high improved the NQ short in both historical periods. At one MNQ it lost $449.80 in 2016–19 and earned $1,444.75 in 2020–September 2026. Across both periods, $994.95 net on 4,951 trades leaves **$0.20 per trade** after the assumed $1.05 round-trip cost. An extra $1 per trade turns the result into a $3,956.05 loss.

## What traded

The first bid strictly above the completed red candle's high during the immediately following M30 candle arms a sell stop **one tick (0.25 points) below the red low**. The protective stop sits **one tick above the original red high**. A fill requires a subsequent quote at or below the sell stop. An unfilled order can remain through green or doji bars until a new red signal replaces it or the session cutoff cancels it. The existing RTL session rules and close-confirmed 1R exit apply. The matched control places the same buffered order immediately after the red candle closes. [One-tick protocol](ONE_TICK_PROTOCOL.md)

For example, on January 4, 2016, the 09:30 signal candle had a 4,534.75 high and a 4,522.25 low. At 10:00:40 the simulated bid reached 4,535.75, arming a sell stop at 4,522.00 with protection at 4,535.00. The order filled at 10:03:40 and the 1R candle-close exit executed at 10:30 for 4,508.00, $26.95 net. Times are on the research symbol's session clock.

## Matched native MT5 results

One MNQ on continuous NQ history, $2 per point, $1.05 cost per trade. Periods use the order submission session. PF is profit factor after costs. Daily drawdown uses closed profit at each day's end. Trade drawdown uses each individual trade close. R divides each trade's profit by its own initial dollar risk.

| Period | Short entry | Trades | Net | Win rate | Net PF | Gross / net mean R | Daily / trade max drawdown |
|---|---|---:|---:|---:|---:|---:|---:|
| 2016–19 | Immediate control | 6,282 | −$13,447.10 | 37.2% | 0.846 | −0.049 / −0.129 | $14,530 / $14,581 |
| 2016–19 | After high break | 1,706 | −$449.80 | 34.3% | 0.974 | −0.020 / −0.126 | $1,275 / $1,275 |
| 2020–Sep 2026 | Immediate control | 11,177 | −$17,976.35 | 38.4% | 0.964 | −0.004 / −0.027 | $23,790 / $24,004 |
| 2020–Sep 2026 | After high break | 3,245 | +$1,444.75 | 36.2% | 1.013 | +0.048 / +0.018 | $6,154 / $6,175 |
| Both periods | Immediate control | 17,459 | −$31,423.45 | 38.0% | 0.947 | −0.020 / −0.064 | $34,083 / $34,331 |
| Both periods | After high break | 4,951 | **+$994.95** | 35.6% | 1.008 | +0.025 / −0.032 | $6,154 / $6,175 |

The rule took 72% fewer trades. Five of the eleven annual rows were positive, including partial 2026. Net ranged from −$2,997.70 in 2023 to +$2,785.35 in 2025. The recent mean net R was +0.018, with a four-week block-bootstrap 95% interval of −0.041 to +0.075. The small net profit came with substantial uncertainty on previously studied history. [Annual results](../../../Reports/rtl_failed_breakout_buffered_20261106/annual.csv)

| Additional cost per trade | 2016–19 net | 2020–Sep 2026 net | Pooled net |
|---|---:|---:|---:|
| $0 | −$449.80 | +$1,444.75 | +$994.95 |
| $1 | −$2,155.80 | −$1,800.25 | −$3,956.05 |
| $2 | −$3,861.80 | −$5,045.25 | −$8,907.05 |

## When the reversal happened

MT5 watched 51,951 red signals. A qualifying high break armed 16,161 orders. Of the 4,951 fills, **2,147 filled in the same M30 candle that broke the high** and lost $5,239.85 net. The other **2,804 filled in later candles** and earned $6,234.80. These groups describe the trades of the tested order-lifetime rule. An earlier cancellation policy would free subsequent signals and would require a separate replay.

| Fill timing | 2016–19 trades / net | 2020–Sep 2026 trades / net |
|---|---:|---:|
| During the candle that broke the high | 712 / −$1,261.10 | 1,435 / −$3,978.75 |
| On a later candle | 994 / +$811.30 | 1,810 / +$5,423.50 |

## Original RTL price convention

The first pair of runs put the sell stop exactly at the red low and the protective stop exactly at its high. Under that convention, waiting for the high break earned −$761.05 and +$1,633.05 across the two periods, or +$872 pooled with a $5,975.95 daily-close drawdown. The immediate control lost $31,705 pooled. All 18,040 immediate-control trades reproduced the saved red-short ledger byte for byte. Both price conventions gave a small pooled profit that disappeared with another $1 per trade. [Original protocol](PROTOCOL.md)

## Evidence

MT5 generated quotes from one-minute OHLC and reported each sell-stop order and deal. These results depend on its assumed price sequence within each minute. Native trade counts, fills, stop levels and gross P&L agree with the ledgers for all four runs. The one-tick run uses initial risk equal to the red candle's range plus 0.50 points. [One-tick period metrics](../../../Reports/rtl_failed_breakout_buffered_20261106/summaries.csv) · [Equity and daily drawdown](../../../Reports/rtl_failed_breakout_buffered_20261106/equity.png) · [One-tick trades](../../../Reports/rtl_failed_breakout_buffered_20261106/trades_on.csv)

The native generation and reporting scripts are [the one-tick runner](../../../python/run_rtl_failed_breakout_buffered.py) and [the analysis](../../../python/analyze_rtl_failed_breakout_short.py). To reproduce the period metrics from the saved native files, run the analysis with `--one-tick` using the project venv.

The independent audit reconstructed the M30 candles and MT5 quote sequence from the source minutes, including tick volumes for sparse minutes. All 16,161 sell stops in the one-tick variant followed the first strict break in the required candle. All 4,951 fills occurred on the first eligible quote after submission. The audit also checked the levels and disposition of all 24,520 control orders and recalculated six period rows and 22 annual rows. Twelve focused tests cover ordering, expiry and stop placement. [One-tick verification](../../../Reports/rtl_failed_breakout_buffered_20261106/independent_verification.json) · [Original convention verification](../../../Reports/rtl_failed_breakout_short_20261105/independent_verification.json)
