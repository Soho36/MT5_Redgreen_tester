# GG replay using the green candle’s open

On the 2016–September 2026 sample, the open gate earned $6,855.25 less than the close gate and increased maximum daily-close drawdown by $642.35. Ungated GG had the highest net profit and smallest drawdown of the three over this period.

Both native MT5 runs evaluated the completed M30 green candle against its session VWAP minus A20. The open variant blocked a new buy stop when the candle opened strictly below that cutoff. The close variant used the close. Equality and unavailable labels allowed entry. Both variants used the original GG buy stop at the signal high, the frozen session features and the October GG tester settings. Net results include $1.05 per round trip for one MNQ-equivalent contract. Drawdown is measured from daily closes grouped by order submission session.

| Sample | Ungated net / drawdown | Close gate net / drawdown | Open gate net / drawdown |
| --- | ---: | ---: | ---: |
| 2010–2015 | −$5,108 / $5,833 | −$4,513 / $5,567 | −$4,858 / $5,746 |
| 2016–2019 | $3,636 / $1,561 | $4,741 / $1,773 | $4,716 / $1,775 |
| 2020–Sep 2026 | $39,315 / $4,882 | $36,659 / $5,360 | $29,830 / $6,002 |
| 2016–Sep 2026 | $42,951 / $4,882 | $41,401 / $5,360 | $34,545 / $6,002 |
| Full, Jun 2010–Sep 2026 | $37,843 / $6,184 | $36,888 / $5,877 | $29,688 / $6,597 |

The 2016–September 2026 trade counts were 17,569 ungated, 15,938 close and 14,993 open. The two gates were within $26 net of each other in 2016–2019. From 2020 onward the open gate gave up $6,829.70 relative to the close gate. In January–September 2026 alone the open gate drew down $6,002, compared with $4,504 for close and $3,881 ungated.

The [baseline-trade omission study](GG_OPEN_RESULTS.md) estimated $37,356 net and $4,456 drawdown for the open rule over the primary sample. Once MT5 replayed the order sequence, the open rule produced 14,993 trades compared with 12,986 in the omission study. Skipping an order can leave GG free to take a later signal. The smaller drawdown in the omission study disappeared in the replay.

## Verification

The close-control trade ledger matched the archived close run byte for byte. The decision audit matched the recorded opens, closes, available cutoffs and block flags to the frozen features through September. All 22,697 eligible open-run fills joined to allowed decision bars and matched their signal highs and lows. Each tester run had one additional candidate beyond the feature history, excluded from performance reporting.

The [replay script](../../../python/replay_gg_open_vwap.py) prepares and runs both variants from the archived October EA. The [verifier](../../../python/verify_gg_open_replay.py) produces the exact-dollar comparison and decision audit in `Reports/gg_open_replay_20261124/`.
