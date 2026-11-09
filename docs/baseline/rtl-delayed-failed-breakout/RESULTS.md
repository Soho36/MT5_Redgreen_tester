# Waiting for the breakout candle to close before shorting NQ

Completed November 7, 2026. On one MNQ, the delayed short earned **$6,410.95 net across 2,901 trades** from January 2016 through September 2026. The existing rule that places the sell stop immediately on the high break earned $994.95. Waiting one bar without requiring a high break lost $3,988.35. All figures include $1.05 per round trip.

## The rule tested

After a completed red M30 candle, watch the immediately following candle. Its first bid strictly above the red high starts the setup. If a later bid in that candle reaches one tick below the red low, abandon the setup. Otherwise, on the first quote of the next scheduled M30 candle, place a sell stop one tick below the original red low and a protective stop one tick above the original red high. A newly completed red candle takes priority, a session cutoff cancels the setup, and an opening bid already at or below the entry disqualifies it. An accepted order follows the standard RTL replacement, 1R candle-close exit and session flatten rules. One tick is 0.25 index points.

The immediate control uses the same prices and exits and places its order when the high first breaks. The plain-delay control waits for the close and watches for a low touch from the start of the candle. It discards setups whose low is touched before a later high break, which the delayed high-break rule can still accept. Each strategy was replayed separately, so its fills can change the signals available afterward. [Frozen protocol](PROTOCOL.md)

## Native MT5 results

| Period | Rule | Trades | Net dollars | Net PF | Daily-close max drawdown | Mean net R |
|---|---|---:|---:|---:|---:|---:|
| 2016–19 | Immediate high break | 1,706 | −$449.80 | 0.974 | $1,275.10 | −0.126 |
| 2016–19 | Delayed high break | 1,019 | +$1,050.05 | 1.105 | $1,072.05 | −0.084 |
| 2016–19 | Plain delay | 1,445 | −$648.25 | 0.963 | $2,309.70 | −0.115 |
| 2020–Sep 2026 | Immediate high break | 3,245 | +$1,444.75 | 1.013 | $6,154.35 | +0.018 |
| 2020–Sep 2026 | Delayed high break | 1,882 | +$5,360.90 | 1.083 | $3,379.70 | +0.067 |
| 2020–Sep 2026 | Plain delay | 2,302 | −$3,340.10 | 0.966 | $6,139.20 | +0.010 |
| Both periods | Immediate high break | 4,951 | +$994.95 | 1.008 | $6,154.35 | −0.032 |
| Both periods | **Delayed high break** | **2,901** | **+$6,410.95** | **1.086** | **$3,379.70** | **+0.014** |
| Both periods | Plain delay | 3,747 | −$3,988.35 | 0.965 | $6,139.20 | −0.038 |

The delayed rule won 36.8% of trades. Its best calendar year was 2025 (+$3,238.15), about half the pooled profit. January–September 2026 lost $1,427.30. Fixed one-contract P&L was positive in both primary periods, but results per unit of initial risk were weaker. The pooled mean net return was +0.014R per trade, with a four-week block-bootstrap 95% interval of −0.052R to +0.080R. Drawdowns above are based on closed P&L at the end of each day. [Period metrics](../../../Reports/rtl_delayed_failed_breakout_20261106/summaries.csv) · [Annual results](../../../Reports/rtl_delayed_failed_breakout_20261106/annual.csv) · [Equity chart](../../../Reports/rtl_delayed_failed_breakout_20261106/equity.png)

| Additional cost per delayed trade | 2016–19 net | 2020–Sep 2026 net | Pooled net |
|---|---:|---:|---:|
| $0 | +$1,050.05 | +$5,360.90 | +$6,410.95 |
| $1 | +$31.05 | +$3,478.90 | +$3,509.95 |
| $2 | −$987.95 | +$1,596.90 | +$608.95 |

## What the fresh replay established

The earlier study had identified 2,804 later fills earning $6,234.80. The delayed rule reproduced **2,797** of those fills with exactly the same entries and exits, worth $6,113.15. Seven old fills worth $121.65 disappeared. The fresh replay added 104 fills worth $297.80. Together these changes added $176.15 to the previously observed later-fill result. The experiment established that the timing rule could capture most of the subgroup on this history. Its profitability on fresh prices remains the main open question. [Original timing split](../rtl-failed-breakout-short/RESULTS.md) · [Matched-trade attribution](../../../Reports/rtl_delayed_failed_breakout_20261106/attribution.csv)

## Verification

The native immediate run reproduced the earlier trade and event files byte for byte, and all native statistics agreed. Each arm's tickets, actual risk, fills, realized P&L and trade totals reconcile across the MT5 deal report, CSV ledger and tester totals. Separate arithmetic checked period and annual metrics. An independent audit rebuilt the full set of eligible red signals from raw minute prices, session cutoffs and native position times. The delayed arm saw 54,535 eligible red signals, 16,768 qualifying high breaks, 13,425 submitted sell stops and 2,901 fills. All watches, disqualifications, next-bar submissions and first eligible fill quotes matched, as did the 15,340 orders of the plain-delay control. The project uses MT5's generated one-minute OHLC sequence, so actual historical ordering and live execution costs remain uncertain. [Native control check](../../../Reports/rtl_delayed_failed_breakout_20261106/baseline_validation.json) · [Independent chronology](../../../Reports/rtl_delayed_failed_breakout_20261106/independent_chronology.json)

Reproduce with the project venv. The [native runner](../../../python/run_rtl_delayed_failed_breakout.py) accepts `prepare`, `compile`, `immediate`, `delayed` and `plain` in order and preserves completed jobs. The [analysis](../../../python/analyze_rtl_delayed_failed_breakout.py) and [verifier](../../../python/verify_rtl_delayed_failed_breakout.py) read the saved jobs.
