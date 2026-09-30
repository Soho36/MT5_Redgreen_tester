# RR 0.5-5.0 optimization review

2026-09-30. The supplied XML/PNG used **MinRedRun=3, MaxRedRun=0**: at least
three reds, without an upper cap. The user confirmed this was accidental and
requested a corrected repeat with **MinRedRun=1, MaxRedRun=3**. Do not use the
first optimization to choose an exit for the cap-3 baseline.

The mistaken run is preserved as separate evidence in
`Reports/rr_optimization_20260930/`, including all 46 matched trade/stats pairs,
the saved tester inputs, summary/yearly tables and hashes. Its 138,826 trade
rows reconcile with XML counts, profits, PF and native balance drawdown.

For that minimum-3 population only, the net-profit winner was 4.6R ($25,204
after modeled $1/trade), while 3.1R had the largest net profit / closed-balance
DD ratio ($24,440 / $3,310 = 7.38). These are exploratory results for a different
entry rule, not the current candidate selection. Original supplied files remain
unchanged.

## Corrected repeat

Repeat the user's complete 0.5-5.0 grid in 0.1 steps, same expert, custom symbol,
2020.01.02-2026.07.14 period, M30/M1 OHLC model, one contract, existing windows
and flatten setting. Change only the mistaken red-run inputs; use a unique
export/report tag. Disable live trading and remote/cloud agents. Save the full
tester configuration and require all 46 trade/stat pairs and a matching 1R
baseline before interpreting the curve. Evidence directory:
`Reports/rr_cap3_corrected_20260930/`.

Python analyzes native MT5 trade paths, with $1 commission per completed trade,
profit, PF, signal-range-normalized R, closed-balance DD and yearly stability.
Keep native gross floating-equity DD distinct from net closed-balance DD.
Look for broad useful regions rather than treating the best decimal as an
established optimum. All this history has been viewed; no untouched holdout
is claimed.

## Current scope

The user explicitly limits this project to the technical trading strategy.
No Apex/account-lifecycle tests are planned. MT5 generates complete entry/exit
paths; Python verifies and compares them. Shortened/holiday session-close
handling remains a separate sensitivity and does not block this repeat.
Its materiality should be measured if tested, not presumed in either direction.

## Corrected results: completed

The fresh optimization completed all 46 passes. All **338,204 trade rows**
reconcile with XML/stat counts, profits, PF and gross balance DD. The 1R pass
reproduces every original field of the earlier 9,147-trade cap-3 baseline.
The complete grid has no missing RR values; the tester log confirms completion.

All figures below are after modeled $1 round-trip commission. DD is net
closed-balance drawdown, not floating-equity drawdown.

| RR | Trades | Net profit $ | Net PF | Net DD $ | Net/DD | Average net R |
|---|---:|---:|---:|---:|---:|---:|
| 1.0 | 9,147 | 37,291.0 | 1.105 | 5,134.5 | 7.26 | +0.0601 |
| 1.1 | 8,909 | 42,362.5 | 1.119 | 4,502.5 | 9.41 | +0.0652 |
| 1.5 | 8,202 | 38,983.5 | 1.110 | 5,797.5 | 6.72 | +0.0691 |
| 2.0 | 7,569 | 39,958.0 | 1.116 | 5,234.5 | 7.63 | +0.0762 |
| 2.4 | 7,191 | 42,136.0 | 1.125 | 4,841.5 | 8.70 | +0.0933 |
| 2.5 | 7,103 | 43,701.0 | 1.130 | 4,530.0 | 9.65 | +0.0977 |
| 2.6 | 7,037 | 42,511.5 | 1.127 | 4,856.5 | 8.75 | +0.0933 |
| 2.7 | 6,966 | 44,387.0 | 1.133 | 5,107.0 | 8.69 | +0.0962 |
| 3.0 | 6,817 | 39,925.0 | 1.120 | 5,615.5 | 7.11 | +0.0854 |
| 3.5 | 6,527 | 45,396.5 | 1.141 | 5,921.5 | 7.67 | +0.1018 |
| 4.6 | 6,110 | 35,319.5 | 1.114 | 7,181.5 | 4.92 | +0.0904 |
| 5.0 | 5,989 | 38,724.5 | 1.127 | 6,999.0 | 5.53 | +0.0935 |

**2.5R is the most useful profit/drawdown candidate in this sample.** It raises
net profit 17.2% versus 1R and reduces net closed DD 11.8%. The surrounding
2.3-2.9 region also exceeds 1R on net profit / closed DD, so the interest is
broader than its exact local maximum. This does not validate the exact decimal.

**3.5R earns the most**, and has the largest average net R. Compared with 2.5R,
it adds only $1,695.50 (3.9%) of net profit while increasing net closed DD by
$1,391.50 (30.7%). Neighboring 3.4-3.7 settings also earn relatively high profit,
but with larger DD than the 2.4-2.6 region. Above approximately 4.4R the curve
deteriorates. The mistaken minimum-3 run's 4.6R winner does not transfer.

**1.1R is a worthwhile nearby control**, with similar profit/DD to 2.5R and
the best native gross recovery factor. Its sharp local improvement does not
extend to 1.0 or 1.2, so do not adopt it merely because of the best-looking
single step. The net closed-DD ranking and native gross floating-DD recovery
ranking differ; both are retained. Gross floating-equity DD is $4,943.50 at
1R, $4,316 at 1.1R, $4,643 at 2.5R and $5,739.50 at 3.5R.

### Chronology within this already-seen history

| RR | Net $ in 2020-22 | Net $ in 2023-July 2026 |
|---|---:|---:|
| 1.0 | 9,993.5 | 27,297.5 |
| 1.1 | 9,595.0 | 32,767.5 |
| 2.5 | 9,361.0 | 34,340.0 |
| 2.6 | 10,213.0 | 32,298.5 |
| 3.5 | 11,226.5 | 34,170.0 |

1.1R and 2.5R's profit gains are concentrated in the later block. 2.5R beats
1R in four of seven calendar-year buckets (2026 partial), not every year.
All five displayed variants have positive net dollars in each year; that is
not the same as consistent superiority to the baseline. These subdivisions
are descriptive, not an untouched validation set.

Cross-date outcomes remain in the tests as requested. At 2.5R they contribute
$9,381 versus $1,962.50 at 1R. The $7,418.50 difference exceeds the total
$6,410 profit gain; same-date aggregate profit falls $1,008.50. This remains
a technical sensitivity to record, without blocking the current analysis or
claiming a causal no-overnight counterfactual. At 1.1R only $888.50 of the
$5,071.50 profit gain is in the cross-date category.

### Research decision

Retain 1R as the unchanged baseline; carry **1.1R, the 2.4-2.6R neighborhood,
and 3.5R** as distinct candidates for a fixed subsequent comparison on other
periods and execution-cost sensitivity. Do not run a still finer grid on the
same dates. The wider curve improves our understanding: more waiting can help,
but profit and drawdown eventually worsen, and the choice depends on the entry
population. The technical focus is native strategy results; no account-policy
simulation is needed for this next step.

The corrected XML is also saved beside the original as
`mt5/optimizations/rr-cap3-05-5-0.1.xml`. No strategy default was changed.

```powershell
.\python\run_rr_optimization.ps1
.\venv\Scripts\python.exe python\analyze_rr_optimization.py --corrected
```
