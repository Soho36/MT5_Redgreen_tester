# Seven-close regression slope for RTL

**Keep unfiltered RTL as the default.** From 2020 through September 2026, requiring an upward slope cut maximum closed-trade drawdown by $1,732 and after-cost profit by $14,165. Net profit per dollar of drawdown fell from 6.64 to 5.98. In 2016–19 the trade-off was more favorable, with 64% less drawdown for 18% less profit.

## Native MT5 replay

One MNQ-equivalent contract on continuous NQ history, $2 per index point, $1.05 per completed trade. Each row starts drawdown measurement from zero at the beginning of the period. Drawdown uses the after-cost balance at each exit. Periods are assigned by order submission. The early years use NQ history with MNQ-equivalent sizing and modeled costs.

| Period | Baseline trades | Up-slope trades | Baseline net | Up-slope net | Baseline max DD | Up-slope max DD |
|---|---:|---:|---:|---:|---:|---:|
| Jun 2010–2015 | 9,164 | 4,807 | −$7,496.20 | −$5,873.85 | $8,254.05 | $6,371.80 |
| 2016–2019 | 6,167 | 3,484 | $4,416.65 | $3,624.30 | $2,175.90 | $784.75 |
| 2020–Sep 2026 | 10,501 | 5,753 | $38,399.95 | $24,235.35 | $5,781.15 | $4,049.40 |
| 2016–Sep 2026 | 16,668 | 9,237 | $42,816.60 | $27,859.65 | $5,781.15 | $4,049.40 |
| Full period | 25,832 | 14,044 | $35,320.40 | $21,985.80 | $8,802.95 | $6,371.80 |

The recent after-cost profit factor improved from 1.090 to 1.124. Allowing fewer setups improved profit per dollar of gross trade losses, while reducing total earnings. In 2010–15, both strategies lost money. Filtering lowered total losses, while profit factor deteriorated from 0.865 to 0.786.

## Where the recent profit went

Matched by the submission time of the filled buy stop, 4,255 trades were identical in both runs and earned $22,325.25. From that common set:

| 2020–Sep 2026 trade group | Trades | After-cost net |
|---|---:|---:|
| Baseline trades with a flat or falling slope | 6,140 | +$15,258.00 |
| Other baseline trades displaced by changed order or position availability, despite a rising slope | 106 | +$816.70 |
| Newly filled trades in the filtered replay | 1,498 | +$1,910.10 |

The baseline adds the first two groups to the shared trades. The filtered replay adds the third. That accounts for the entire $14,164.60 difference. In 2016–19 the 3,590 flat-or-falling baseline trades also made money (+$1,610). The profitability of the excluded group reverses in 2010–15 (−$2,881.70).

## Implementation and checks

The native MT5 Strategy Tester used M1 OHLC modeling and the established M30 RTL configuration. At each eligible red-candle submission, the EA took the seven most recent completed M30 closes across session boundaries. The sign of the fitted line is the sign of their weighted sum with weights −3 through +3, oldest first. Exact zero blocks. The EA evaluates the filter immediately after normal red-signal cancellation and before submitting the replacement. Existing orders can fill between signals and positions follow RTL's existing exit logic.

The replay with the filter off reproduced all 25,833 archived ledger rows byte for byte. The reported periods end on September 30, so one October 1 baseline fill is excluded ($133.95 net). A second calculation on the frozen M30 price series verified all 60,193 baseline and 75,239 filtered candidate decisions in the reported periods. The filtered path blocked 44,472 candidate submissions, including 130 exactly flat. Every reported fill matched an allowed source signal, with buy-stop and stop-loss levels equal to its high and low. Both native reports reconciled to their ledgers and price-based P&L. All shared trades had identical entry/exit timestamps and economics.

This was a single prespecified rule on previously studied history. [Protocol](PROTOCOL.md) · [Preparation](../../../python/prepare_rtl_regression_slope.py) · [Verification and attribution](../../../python/analyze_rtl_regression_slope.py) · [Results CSV](../../../Reports/rtl_regression_slope_20261125/summary.csv) · [Trade attribution CSV](../../../Reports/rtl_regression_slope_20261125/attribution.csv)
