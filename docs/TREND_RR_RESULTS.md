# RTL trend-conditioned RR — 2026-10-02

**Keep fixed 1R; the proposed adaptation fails the frozen screen.**
The primary annual selection changes 2015–2025 net/DD by **-1.3%** versus fixed 1R. Net profit is $35,111.05 versus $35,823.00; closed-trade drawdown is $3,950.25 versus $3,979.25.

The user clarified that only the trend concept should be imported. Every run uses our existing RTL buy-stop entry, MaxRedRun=3, candle-low stop, M30-close-qualified market exit and session handling. No GG, new entry filter, sell-limit exit or forward test was added. All tests use 1-minute OHLC.

## Our usual comparison periods

Mappings show bull / neutral / bear RR. Previous completed daily close and SMAfast must both be above SMA200 for bull, both below for bear; all other available combinations are neutral. Each trade keeps its entry-day RR. This table uses 50/200 and $1.05 commission per contract. DD is net balance drawdown.

| Mapping | 2016–2019 net $ | DD $ | Net/DD | 2020–Jul 2026 net $ | DD $ | Net/DD |
|---|---:|---:|---:|---:|---:|---:|
| Fixed 1R | 6,485.15 | 1,435.30 | 4.52 | 37,980.95 | 4,847.40 | 7.84 |
| Mild 1.25 / 1 / 0.75 | 6,470.15 | 1,572.70 | 4.11 | 37,333.40 | 5,089.55 | 7.34 |
| Strong 1.5 / 1 / 0.75 | 6,311.85 | 1,623.70 | 3.89 | 35,272.35 | 5,452.20 | 6.47 |
| Bull-only 1.5 / 1 / 1 | 6,694.20 | 1,486.30 | 4.50 | 35,933.70 | 5,452.20 | 6.59 |
| Bear-only 1 / 1 / 0.75 | 6,102.80 | 1,572.70 | 3.88 | 37,319.60 | 4,847.40 | 7.70 |
| Reversed 0.75 / 1 / 1.5 | 5,980.65 | 1,588.00 | 3.77 | 32,967.00 | 5,395.90 | 6.11 |

## Historical annual selection

Training expands from the available 2010–2014 history. Select only fixed, mild or strong using prior years' net/DD, subject to the 75-trades-per-regime rule, and freeze the choice for the next year. Full test years are 2015–2025; partial 2026 is excluded from this score. The 2015–2025 history was examined in earlier research, so these are chronological selector holdouts, not genuinely untouched validation data.

| Year | Selected mapping | Selected net $ | Fixed net $ | Selected net/DD | Fixed net/DD |
|---|---|---:|---:|---:|---:|
| 2015 | mild | 826.50 | 255.65 | 1.37 | 0.30 |
| 2016 | strong | -657.85 | -471.90 | -0.48 | -0.40 |
| 2017 | baseline | 967.15 | 967.15 | 2.61 | 2.61 |
| 2018 | strong | 1,897.30 | 1,944.05 | 1.17 | 1.35 |
| 2019 | mild | 3,580.50 | 4,045.85 | 3.16 | 3.48 |
| 2020 | strong | 3,891.85 | 4,557.65 | 0.99 | 1.54 |
| 2021 | strong | 2,094.80 | 1,018.00 | 0.73 | 0.29 |
| 2022 | strong | 4,084.25 | 4,429.25 | 1.19 | 1.23 |
| 2023 | strong | 4,031.30 | 5,113.15 | 1.47 | 2.37 |
| 2024 | strong | 8,850.35 | 9,280.45 | 2.87 | 4.31 |
| 2025 | strong | 5,544.90 | 4,683.70 | 1.48 | 1.18 |

Improved annual net/DD: **3/11** years; improved annual net dollars: **3/11**.

## Moving-average and placebo checks

Each MA length has its own prior-years-only selector; MA lengths are never candidates for selection. Diagnostics below are fixed mappings across the same 2015–2025 dates.

| Fast / slow | Annual selection net $ | DD $ | Net/DD | Fixed 1R net/DD | Reversed net/DD | Bear-only net/DD |
|---|---:|---:|---:|---:|---:|---:|
| 40/200 | 35,909.15 | 3,950.25 | 9.09 | 9.00 | 5.73 | 8.71 |
| 50/200 | 35,111.05 | 3,950.25 | 8.89 | 9.00 | 5.82 | 8.74 |
| 60/200 | 34,897.15 | 3,950.25 | 8.83 | 9.00 | 5.87 | 8.59 |

All mapping sensitivities (net/DD, 2015–2025):

| Mapping | 40/200 | 50/200 | 60/200 |
|---|---:|---:|---:|
| Fixed 1R | 9.00 | 9.00 | 9.00 |
| Mild 1.25 / 1 / 0.75 | 9.07 | 9.08 | 8.90 |
| Strong 1.5 / 1 / 0.75 | 9.07 | 9.01 | 8.84 |
| Bull-only 1.5 / 1 / 1 | 9.37 | 9.28 | 9.26 |
| Bear-only 1 / 1 / 0.75 | 8.71 | 8.74 | 8.59 |
| Reversed 0.75 / 1 / 1.5 | 5.73 | 5.82 | 5.87 |

## Costs and concentration

Slippage is unmeasured. The primary comparison retains our $1.05 commission assumption. The following are additional cost allowances, not validated execution simulations; selections stay frozen.

| Extra cost / trade | Selected net $ | Fixed net $ | Selected net/DD | Fixed net/DD |
|---|---:|---:|---:|---:|
| $1.00 | 20,192.05 | 20,133.00 | 4.94 | 4.19 |
| $2.00 | 5,273.05 | 4,443.00 | 0.49 | 0.43 |

The selected strategy makes 771 fewer trades than fixed 1R in these test years. Charging more per trade therefore helps its relative result: the cost-stress advantage is real within that assumption, but it does not establish the actual execution cost. At the known commission assumption the primary screen still fails.

Excluding 2020, 2021: selected net/DD 7.76, fixed 7.60.

Excluding 2021: selected net/DD 8.36, fixed 8.75.

## Regime results for the selected strategy

These are attributed subsets: their drawdowns do not sum to portfolio drawdown. Profit shares are signed shares of total net profit.

| Regime | Trades | Net $ | Share of total net | DD $ | PF |
|---|---:|---:|---:|---:|---:|
| bull | 10,889 | 19,875.05 | 56.6% | 3,093.45 | 1.078 |
| neutral | 1,804 | 9,827.30 | 28.0% | 2,862.45 | 1.173 |
| bear | 2,226 | 5,408.70 | 15.4% | 3,426.35 | 1.077 |

Fixed-1R bear subset: net $6,459.10, DD $3,600.65.

## Other selected-strategy metrics (2015–2025)

| Metric | Annual selection | Fixed 1R |
|---|---:|---:|
| Trades | 14919 | 15690 |
| Average net trade $ | 2.35 | 2.28 |
| Profit factor | 1.092 | 1.094 |
| Profitable months | 67.4% | 69.7% |
| Profitable years | 90.9% | 90.9% |
| Worst month $ | -1562.85 | -1715.00 |
| Worst quarter $ | -2627.45 | -2386.05 |
| Worst year $ | -657.85 | -471.90 |
| Longest balance drawdown, calendar days | 716.0 | 638.2 |
| Average holding time, minutes | 112.3 | 99.8 |
| Trades qualifying for target exit | 34.0% | 37.8% |
| Qualified exits completed | 100.0% | 100.0% |
| Gross realized / sum positive MFE | 6.8% | 7.2% |
| Average net R | 0.0263 | 0.0222 |
| Average MAE R | -0.7338 | -0.7138 |
| Average MFE R | 1.1762 | 1.0998 |

## Frozen decision gates

| Gate | Result |
|---|---|
| ratio gain 10 percent | FAIL |
| net retained 90 percent | PASS |
| dd not increased | PASS |
| improved 60 percent years | FAIL |
| beats reversed 10 percent | PASS |
| survives without 2020 2021 | PASS |
| survives without best year | FAIL |
| survives extra 2 cost | PASS |
| both neighbor lengths beneficial | FAIL |

The protocol defines “clearly beats reversed” as at least 10% better net/DD and annual improvement as higher annual net/DD; annual net-dollar improvement is also shown. See the [frozen protocol](TREND_RR_PROTOCOL.md) for all definitions.

## Validation and limits

All 16 MT5 runs reconcile to tester trade counts and gross PnL. The independent minute-source audit checks each signal OHLC, prior-day MA label, frozen trade RR and all **1,257,870** M30 target checks. No cross-date trades or trend export/target-close errors were found. The fixed control reproduces both established comparison periods, including trade times, profits, excursions and signal features. Compilation has zero errors/warnings; 12 Python tests pass.

The source begins in June 2010; 200 prior daily closes first exist on 2011-03-15. Earlier entries remain at 1R with an explicit warmup label, without treating unknown trend as neutral. Before-2016 market hours differ; the existing early-close calendar is retained. Raw continuous prices include roll gaps, matching the baseline's rollover construction.

One-minute OHLC cannot establish actual intraminute ordering or slippage. Drawdowns in tables use completed trades, not marked-to-market equity; per-run MT5 gross equity DD is retained in the audit JSON. Sell-limit fill rates and RR/GG simultaneous failures are inapplicable to this RTL-only market-exit study. No live strategy defaults were changed.

## Files

- `Reports/trend_rr_20261002/`: source/compiled EA, includes, INIs, manifests, reports, logs, raw/enriched trades, every accepted setup, every target check, independent daily/M30 references, stitched annual trades and `results.json` (including all monthly/yearly and regime metrics).
- `python/prepare_trend_rr_study.py`, `trend_regimes.py`, `trend_rr_metrics.py`, `analyze_trend_rr_study.py`, `report_trend_rr_study.py`, `test_trend_rr.py`.
- `mt5/experts/trend_rr_research.mqh`: tester-only daily regime assignment and audit logging.

```powershell
.\venv\Scripts\python.exe python\analyze_trend_rr_study.py
.\venv\Scripts\python.exe python\report_trend_rr_study.py
```
