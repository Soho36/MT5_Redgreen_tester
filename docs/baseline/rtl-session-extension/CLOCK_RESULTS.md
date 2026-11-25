# Unusual rallies by time of day and realized RTL session profit

Skipping the next RTL setup when the market had made an unusually large rise for that time of day and the strategy was already profitable reduced net profit in both periods. It increased maximum closed-trade drawdown in both. The next trade after that combination averaged +0.017R in 2016–19 and +0.116R in 2020–July 2026.

## How the rally was measured

The primary rule requires a positive move from the exchange session open that ranks at or above the 90th percentile of returns observed at that same minute over the previous 60 trading sessions. A previous day contributes even if the strategy never traded that day. Reference prices and current prices are minute opens. Missing same-minute observations are omitted. All 14,968 baseline submissions had sufficient reference history for both the primary measure and volatility sensitivity. [Study protocol](CLOCK_PROTOCOL.md)

For example, a 0.999% rise by 11:30 on September 21, 2021 exceeded every available same-minute return in the reference window. A 0.997% rise by 20:00 on April 16, 2020 ranked at only the 67th percentile. Times use the dataset's exchange-session clock. These two observations illustrate the score. The comparisons below use all qualifying trades.

## Does realized P&L distinguish the next trade?

| Period | Rally rank | Prior session net | Trades | Sessions | Next win rate | Mean net R | Total net dollars |
|---|---|---|---:|---:|---:|---:|---:|
| 2016–19 | Outside top-decile rally | Flat or negative | 3,301 | 1,023 | 44.2% | +0.008 | +4,965 |
| 2016–19 | Outside top-decile rally | Positive | 1,893 | 738 | 42.0% | −0.034 | +1,155 |
| 2016–19 | Top-decile rally | Flat or negative | 80 | 61 | 45.0% | +0.087 | −38 |
| 2016–19 | Top-decile rally | Positive | 423 | 208 | 43.0% | +0.017 | +402 |
| 2020–July 2026 | Outside top-decile rally | Flat or negative | 5,333 | 1,670 | 43.8% | +0.068 | +20,919 |
| 2020–July 2026 | Outside top-decile rally | Positive | 3,104 | 1,249 | 41.5% | +0.035 | +8,314 |
| 2020–July 2026 | Top-decile rally | Flat or negative | 153 | 116 | 41.8% | +0.046 | +1,649 |
| 2020–July 2026 | Top-decile rally | Positive | 681 | 315 | 43.9% | +0.116 | +7,098 |

R expresses each trade's net return in units of its initial risk. Dollar risk varies with the signal candle, so dollar totals and average R can differ in sign. Sessions may appear in multiple rows.

Among unusual rallies the green-minus-flat/negative difference in next-trade mean R was −0.070R earlier (95% calendar-week interval −0.443 to +0.249) and +0.070R recently (−0.152 to +0.279). First trades enter the flat group. A second comparison required a prior closed trade and compared groups sharing similar rank, clock time and prior trade count. It retained 342 of 462 eligible earlier trades and 656 of 761 recent trades. The respective differences were −0.035R (−0.875 to +0.548) and +0.179R (−0.086 to +0.476). Neither comparison established a repeatable sign for the incremental P&L effect. These exploratory intervals allow for trades clustering within a week.

## What happened when entries were skipped?

Change in total net profit relative to capped RTL, one MNQ and $1.05 per completed trade. The strategy checks the rule at each new order opportunity, can resume after a pullback, and tracks its own realized P&L.

| Entry skip condition | 2016–19 | 2020–July 13, 2026 |
|---|---:|---:|
| Positive realized P&L alone | −$2,004 | −$22,193 |
| Top 10% rally alone | −$392 | −$8,437 |
| Top 10% rally and positive realized P&L | −$691 | −$7,087 |
| Top 10% rally and realized P&L ≥+1 cumulative net R | −$452 | −$4,976 |
| Top 20% rally and positive realized P&L | −$68 | −$9,499 |
| Top 5% rally and positive realized P&L | −$269 | −$4,105 |
| Top 10% among volatility-matched sessions and positive P&L | −$359 | −$9,283 |

The primary combined rule took net profit from $6,485 to $5,794 earlier and $37,981 to $30,894 recently. Maximum closed-trade drawdown increased from $1,435 to $1,492 and from $4,847 to $5,007. Profit improved in 2019 and 2022, and declined in the other nine calendar years including partial 2026. The earlier replay omitted 438 baseline fills and added 26 newly available trades. The recent replay omitted 707 and added 27. This explains why the change in profit differs from the sum of the highlighted baseline trades.

The volatility sensitivity ranks today's rise against the 60 sessions most similar in volatility experienced up to that exact minute out of the previous 120 sessions. Its results also oppose skipping. The evidence addresses the value of the next **RTL long setup** on previously studied OHLC history. It does not measure whether price later reverses independently of that trade.

## Reproduction

Run `venv/Scripts/python.exe python/rtl_clock_extension.py` then `venv/Scripts/python.exe python/verify_rtl_clock_extension.py` from the project root. Scores at 120 decisions were independently rebuilt from prior-day minute slices. The unrestricted path matched all native Q24 trade submission, entry and exit minutes and net outcomes. A separate minute-by-minute replay matched every taken trade's timestamps and dollars for the primary rally-only (13,700), green-P&L (13,876) and +1R (14,028) policies. Filtered paths use simulated fills.

[All replay results](../../../Reports/rtl_clock_extension_20261124/policies.csv) · [All next-trade cells](../../../Reports/rtl_clock_extension_20261124/cells.csv) · [Matched comparisons](../../../Reports/rtl_clock_extension_20261124/contrasts.csv) · [Yearly changes](../../../Reports/rtl_clock_extension_20261124/annual.csv)

