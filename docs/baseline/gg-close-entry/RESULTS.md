# GG entry at the green close

From 2016 through September 2026, entering as soon as a green M30 candle closed earned $10,924.25 after costs, compared with $42,951.05 for the high breakout. Close entry took 7,266 more trades and increased maximum daily-close drawdown by $2,021.40. It earned less in each of the three historical periods.

| Period | High trades | Close trades | High net | Close net | High daily drawdown | Close daily drawdown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| June 2010–2015 | 8,935 | 12,719 | −$5,108.25 | −$15,741.95 | $5,833.10 | $15,941.00 |
| 2016–2019 | 6,388 | 8,933 | $3,635.60 | −$2,450.65 | $1,560.70 | $4,710.20 |
| 2020–Sep 2026 | 11,181 | 15,902 | $39,315.45 | $13,374.90 | $4,881.60 | $6,042.35 |
| 2016–Sep 2026 | 17,569 | 24,835 | $42,951.05 | $10,924.25 | $4,881.60 | $6,903.00 |
| June 2010–Sep 2026 | 26,504 | 37,554 | $37,842.80 | −$4,817.70 | $6,183.85 | $22,701.15 |

In the 2016–September 2026 sample, net win rate fell from 43.30% to 38.85% and net profit factor fell from 1.078 to 1.016. Of the $32,026.80 net shortfall, $24,397.50 came from lower trading profit before the fixed round-trip charge and $7,629.30 from the extra trades at $1.05 each.

## Execution and verification

Both native MT5 runs used the archived ungated NQ M30 settings, the 1-minute OHLC tester model and one MNQ-equivalent contract ($2 per point). After an eligible green candle closed, the close variant bought at the next available ask. Its stop stayed at the signal low. The existing exit waited for a completed M30 candle to reach at least one initial risk above the actual fill, subject to the original session flatten.

All 37,554 market buys through September filled at the next bar's opening bid plus one tick. The median fill was 0.25 points above the green candle's printed close. Exactly 7,294 fills equaled that printed close. Drawdown is the largest peak-to-trough decline in cumulative after-cost P&L at daily closes, grouped by order submission session.

The high-entry ledger matched the archived GG ledger byte for byte. Both reports reconciled to native trade counts and gross profit and loss. Every in-sample entry matched a green signal and its low stop. The close-entry check also matched the fill minute and ask price to the next observed M30 bar. [Study protocol](PROTOCOL.md) · [Tester preparation](../../../python/prepare_gg_close_entry.py) · [Analysis and verification](../../../python/analyze_gg_close_entry.py) · [Exact metrics](../../../Reports/gg_close_entry_20261125/comparison.csv)
