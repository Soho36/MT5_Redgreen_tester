# First one-minute candle of 15:30 news

Completed 2026-11-22. [Frozen protocol](PROTOCOL.md).

**The combined rule does not show a profitable edge after costs.** Three full
native MT5 runs completed: CPI + payrolls, CPI only and payrolls only. All
333 combined trades independently match raw-minute signals, entry quotes and
subsequent exits. The two separate ledgers reproduce the combined ledger exactly.

One MNQ-valued contract ($2/point), $1.05 per round trip. This uses the project's
continuous NQ research history, not a native MNQ feed. Original historical dates;
the packed Forex Tester dataset was not used. DD below is intraday marked-to-market
equity after costs. The complete [summary](summary.csv) also includes annual
results, daily-close DD, mean net R and +$1/trade stress.

| Period | Trades | Gross $ | Net $ | Win rate | PF | Equity DD $ | Net with +$1/trade |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2016-19 | 83 | 125.50 | 38.35 | 71.1% | 1.118 | 164.35 | -44.65 |
| 2020-26 | 151 | -85.50 | -244.05 | 70.9% | 0.942 | 788.85 | -395.05 |
| 2016-26 | 234 | 40.00 | -205.70 | 70.9% | 0.954 | 788.85 | -439.70 |
| 2010-15 | 99 | 64.50 | -39.45 | 51.5% | 0.859 | 70.60 | -138.45 |

Full June 2010–September 2026: 333 trades, gross $104.50, net $-245.15.

The recent win rate is about 71%, but the median planned reward/risk is only
0.256: the remaining wick offers a relatively small target while the opposite
candle extreme is often a distant stop. A high hit rate alone is insufficient.
The 2016–19 net gain is only $38.35 and becomes a loss with another $1 per trade.

## CPI and payroll decomposition

These are the same fixed rule on predeclared subsets, not optimized variants.

| Release | Period | Trades | Net $ | Win rate | PF | Mean net R | Equity DD $ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cpi | 2016-19 | 38 | -3.40 | 68.4% | 0.962 | -0.098 | 81.75 |
| cpi | 2020-26 | 74 | -547.20 | 74.3% | 0.773 | -0.038 | 1,000.20 |
| cpi | 2016-26 | 112 | -550.60 | 72.3% | 0.780 | -0.058 | 1,000.20 |
| payrolls | 2016-19 | 45 | 41.75 | 73.3% | 1.178 | 0.072 | 112.95 |
| payrolls | 2020-26 | 77 | 303.15 | 67.5% | 1.171 | -0.078 | 452.15 |
| payrolls | 2016-26 | 122 | 344.90 | 69.7% | 1.172 | -0.023 | 529.00 |

Payrolls earn positive dollars in the main eras, whereas CPI loses. Payrolls'
recent mean net R is negative despite positive dollar P&L: dollar risk varies
between trades. This small, repeatedly examined historical sample does not
establish a robust payroll-only trading rule. No production change is made.

## Implemented execution rules

- Calendar: scheduled CPI and Employment Situation releases at 15:30 research
  time, equivalent to 08:30 New York. FOMC is not a 15:30 release and is excluded.
- Read the exact completed 15:30–15:31 M1 candle. Green buys, TP at its high and
  SL at its low; red sells, TP at its low and SL at its high.
- Enter once on the first available quote in 15:31. Buy at ask, sell at bid.
  This is an executable next-quote entry, not a retroactive fill at the candle's
  closing price. The entry may differ from that close.
- Skip a doji or a candle closing at its target extreme (zero target distance).
  Also skip if the new entry quote is outside the strict SL–TP bracket or broker
  stop-distance rules reject the levels. Do not move TP/SL to make an order fit.
- If the exact signal/entry minute is absent, do not substitute a later candle.
  One attempt per event session, no retries or re-entry.
- Attached TP/SL operate intrabar. Any survivor closes at the existing daily
  23:30/early-close cutoff. There were 241 TP exits, 91 SL exits, and one
  early-close exit (2021-04-02 at 16:00, net -$44.55).

The combined run observed 387 eligible source sessions:

| Decision | Sessions |
| --- | --- |
| entered | 333 |
| zero_target_wick | 23 |
| invalid_entry_levels | 19 |
| doji | 11 |
| missing_entry_minute | 1 |

There were no broker order rejections. Dates before source history and dates
without any source bars are itemized in [verification](verification.json).
The 400-event calendar includes 13 such unobserved dates; missing data are not
counted as trading opportunities. The one missing entry-minute decision is
separate from dates with no source session at all.

## Model limitations and verification

All runs use MT5's generated one-minute OHLC ticks, not real news ticks.
Observed entry spread is 0.25 points. This exchange-mode symbol triggers attached
stops/targets on the Last-price OHLC path, including short positions. Native
tester exits fill at their specified levels; this is a tester convention, not a
guarantee of live stop/limit execution. [MT5 explains exchange stop triggering](https://www.metatrader5.com/en/terminal/help/trading/general_concept).
News latency, variable spreads, slippage and queue priority are not reproduced.

Two trades over full history have an execution-minute range containing both
TP and SL. Generated-tick ordering resolves them in the tester, but M1 OHLC
alone cannot prove real intraminute ordering. Neither occurs in 2020–26.
Five focused tests cover direction, dojis, zero target wick, next-quote gaps and
broker minimum distances. All native decisions match raw source candles; all
entries match quote side, exits match an independent forward minute-path replay,
and native gross equity DD reconciles. Daily compression reproduces full costed
equity paths. Subset union exactly matches the combined run.

## Long versus short trades

Post-hoc descriptive split of the verified native trades; no new rule or
parameter selection. One trade maximum per session makes this an exact ledger
decomposition. Longs follow green news candles, shorts follow red ones.
Both directions include the same $1.05 round-trip cost.

| Period | Direction | Trades | Net $ | Win rate | PF | Average net $ | Mean net R |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2010-15 | Long | 48 | -44.40 | 56.2% | 0.732 | -0.93 | -0.148 |
| 2010-15 | Short | 51 | 4.95 | 47.1% | 1.043 | 0.10 | -0.418 |
| 2016-19 | Long | 47 | 160.65 | 80.9% | 2.880 | 3.42 | 0.091 |
| 2016-19 | Short | 36 | -122.30 | 58.3% | 0.489 | -3.40 | -0.132 |
| 2020-26 | Long | 84 | 940.80 | 76.2% | 1.558 | 11.20 | 0.019 |
| 2020-26 | Short | 67 | -1,184.85 | 64.2% | 0.526 | -17.68 | -0.155 |
| full | Long | 179 | 1,057.05 | 72.1% | 1.545 | 5.91 | -0.007 |
| full | Short | 154 | -1,302.20 | 57.1% | 0.543 | -8.46 | -0.237 |

**Longs outperform shorts in both main eras.** Since 2020, longs earn $940.80
while shorts lose $1,184.85, explaining the combined loss. Early longs earn
$160.65 versus shorts losing $122.30. Across full history, longs earn $1,057.05
and shorts lose $1,302.20. However, full-history mean net R for longs is still
slightly negative (-0.0066), so positive dollars are not uniform risk-adjusted
expectancy across eras. This post-hoc split motivates a hypothesis; it does not
validate a newly selected long-only strategy.

Recent release-specific split (2020–September 2026):

| Release | Direction | Trades | Net $ | Win rate | PF | Mean net R |
| --- | --- | --- | --- | --- | --- | --- |
| cpi | Long | 44 | 250.30 | 79.5% | 1.235 | -0.019 |
| cpi | Short | 30 | -797.50 | 66.7% | 0.408 | -0.065 |
| payrolls | Long | 40 | 690.50 | 72.5% | 2.107 | 0.062 |
| payrolls | Short | 37 | -387.35 | 62.2% | 0.664 | -0.228 |

The full [direction summary](direction_summary.csv) includes all eras, both
release subsets, reward/risk, +$1/trade stress and **closed-trade** drawdown for
each side. That drawdown is not the intraday equity DD in the main table.
Counts and profits of the two sides reconcile to each combined ledger in every
period. Differences are descriptive; no formal significance or forward-data
confirmation is claimed.

## EA and reproduction

EA: `mt5/experts/News_first_minute_research.mq5`.
Installed for the tester as `CodexResearch\News_first_minute_research`.
Use the original custom symbol `MNQcontDTBNT20102026_2`, M1, 1-minute OHLC model.
Inputs: `NewsMask=3` both, `1` CPI, `2` payrolls; `RunTag` labels output files.
The EA intentionally refuses live use and other symbols/clocks.

The complete source/includes, compiled EX5 and three tester INIs are packaged
in `Reports/news_first_minute_20261122/News_first_minute_EA.zip`. That folder
also holds native HTML reports, decisions, deals, equity paths and completion hashes.
The generated calendar include comes from the frozen timestamp CSV. Preparation
is performed by the runner; existing completed runs are preserved.

```powershell
& .\venv\Scripts\python.exe python/run_news_first_minute.py
& .\venv\Scripts\python.exe python/analyze_news_first_minute.py
& .\venv\Scripts\python.exe python/report_news_first_minute.py
& .\venv\Scripts\python.exe -m unittest discover -s python -p test_news_first_minute.py -v
```

Calendar scope and source end date match the preceding
news study; this experiment does not add October/November 2026 releases.
