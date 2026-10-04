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
| [Q15: falling trendline resistance](RESISTANCE_PROTOCOL.md) | **Protocol frozen 2026-10-04**: long RTL signals at falling lines through lower swing highs (fill = break from below); run pending | `Reports/trendlines/charts/resistance_*` (examples only) |

The old [`Trendline_rejection.cs`](../../mt5/Trendline_rejection.cs) EA was
the source of the idea and is not used for testing.
