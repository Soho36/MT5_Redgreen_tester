# Trendline research

Started 2026-10-04. This study is kept separate from the
[horizontal price-level study](../levels/README.md) but asks the same
questions: do red RTL signals at rising trendline support do better than
every other signal (Q11-style), and does broad contact with any unbroken
rising line (Q12-style)? It uses the same baseline population, original exit
and follow-up gate. Generated outputs go under `Reports/trendlines/`.

| Study | Status | Outputs |
|---|---|---|
| [Q14: rising trendline support](TRENDLINE_SUPPORT_RESULTS.md) ([protocol](TRENDLINE_PROTOCOL.md)) | Complete 2026-10-04: candidates **worse** than every other signal in both periods (PF 1.029/0.950 vs 1.114/1.124); broad contact also worse; no filter | `Reports/trendlines/trendline_support_20261004/` |
| [Q15: falling trendline resistance](TRENDLINE_RESISTANCE_RESULTS.md) ([protocol](RESISTANCE_PROTOCOL.md)) | Complete 2026-10-04: **passes the gate** (PF 1.325/1.332 vs 1.088/1.090; both sensitivities and broad contact agree). Gap carried by entries below the line, weak in 2023-25. Qualifies for a full MT5 run protocol only | `Reports/trendlines/trendline_resistance_20261004/` |

The old [`Trendline_rejection.cs`](../../mt5/Trendline_rejection.cs) EA was
the source of the idea and is not used for testing.
