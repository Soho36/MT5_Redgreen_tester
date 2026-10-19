# RTL and GG: H1 versus M30

**Finding:** H1 has roughly 44–47% fewer recent trades and larger risk per contract. At RR 0.5 it earns more than M30 at RR 0.5 in both eras; at RR 1 it earns less recently. Recent GG H1/RR 1 also has 50% higher drawdown. M30/RR 1 still earns more recent dollars than either H1 variant for each strategy. No baseline change is adopted.

2026-10-15. Eight matched MT5 Strategy Tester runs, `MaxRedRun=0` on both strategies, RR 0.5 and 1.0.

MNQ-priced continuous NQ (`MNQcontDTBNT20102026_2`), one contract, one-minute OHLC modelling, data through **2026-10-01**. Same 01:00–23:30 entry window, early-close calendar, no candle-range/location/trailing filter. Costs are **$1.05 per completed trade**. RR is a **bar-close threshold**, so winners can exceed the chosen RR.

H1 signals, pending-order decisions and target exits use hourly bars. The original EA checks flattening only at a new chart bar; H1 skips 23:30. Isolated research copies therefore check the existing cutoff on ticks for H1. M30 execution is unchanged. All eight runs have zero cross-date positions.

## 2016-19

| Strategy | RR | TF | Trades | Win % | Net $ | Net PF | Net DD $ | Avg net R |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| RTL | 0.5 | M30 | 7,191 | 52.0 | 771 | 1.012 | 2,317 | -0.040 |
| RTL | 0.5 | H1 | 3,737 | 51.7 | 3,543 | 1.077 | 1,231 | -0.000 |
| RTL | 1 | M30 | 6,167 | 43.4 | 4,417 | 1.064 | 2,176 | -0.014 |
| RTL | 1 | H1 | 3,377 | 43.5 | 4,462 | 1.091 | 1,347 | +0.016 |
| GG | 0.5 | M30 | 7,644 | 52.3 | 56 | 1.001 | 2,806 | -0.044 |
| GG | 0.5 | H1 | 4,250 | 53.5 | 5,719 | 1.108 | 1,578 | +0.019 |
| GG | 1 | M30 | 6,388 | 43.7 | 3,636 | 1.048 | 1,708 | -0.016 |
| GG | 1 | H1 | 3,700 | 44.9 | 5,877 | 1.106 | 1,466 | +0.032 |

## 2020-26 (through October 1, 2026)

| Strategy | RR | TF | Trades | Win % | Net $ | Net PF | Net DD $ | Avg net R |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| RTL | 0.5 | M30 | 12,182 | 51.8 | 26,414 | 1.065 | 4,537 | +0.022 |
| RTL | 0.5 | H1 | 6,505 | 51.6 | 33,447 | 1.117 | 5,009 | +0.044 |
| RTL | 1 | M30 | 10,502 | 42.8 | 38,534 | 1.091 | 5,781 | +0.048 |
| RTL | 1 | H1 | 5,849 | 42.5 | 28,020 | 1.092 | 4,039 | +0.040 |
| GG | 0.5 | M30 | 13,670 | 52.1 | 19,929 | 1.041 | 5,056 | +0.019 |
| GG | 0.5 | H1 | 7,344 | 52.7 | 26,343 | 1.077 | 7,162 | +0.039 |
| GG | 1 | M30 | 11,182 | 43.3 | 39,444 | 1.083 | 5,316 | +0.044 |
| GG | 1 | H1 | 6,321 | 43.5 | 19,717 | 1.055 | 7,990 | +0.033 |

## What changes on H1

- **RTL, RR 0.5:** recent net changes by $+7,033; trades -46.6%, net PF 1.065 → 1.117, DD +10.4%. Median signal range 28.0 → 40.2 points; median hold 44 → 81 minutes. H1 earns more in 9/11 years (2016–2026; 2026 partial). Paired exit-day bootstrap 95% interval for recent net difference: $-11,792 to $+25,401.
- **RTL, RR 1:** recent net changes by $-10,514; trades -44.3%, net PF 1.091 → 1.092, DD -30.1%. Median signal range 28.8 → 40.8 points; median hold 64 → 113 minutes. H1 earns more in 4/11 years (2016–2026; 2026 partial). Paired exit-day bootstrap 95% interval for recent net difference: $-28,935 to $+7,523.
- **GG, RR 0.5:** recent net changes by $+6,414; trades -46.3%, net PF 1.041 → 1.077, DD +41.6%. Median signal range 29.8 → 42.8 points; median hold 51 → 96 minutes. H1 earns more in 8/11 years (2016–2026; 2026 partial). Paired exit-day bootstrap 95% interval for recent net difference: $-13,748 to $+26,742.
- **GG, RR 1:** recent net changes by $-19,727; trades -43.5%, net PF 1.083 → 1.055, DD +50.3%. Median signal range 30.0 → 43.5 points; median hold 71 → 138 minutes. H1 earns more in 4/11 years (2016–2026; 2026 partial). Paired exit-day bootstrap 95% interval for recent net difference: $-38,906 to $-1,742.

Larger H1 candles change signal frequency and dollar risk per contract; hourly target checks also change realised exits. This is a comparison of whole strategies, not an isolated entry-signal test. Net DD is calculated from closed-trade equity, not intratrade drawdown. The day bootstrap is descriptive and does not model longer serial dependence. The 2010–15 era has different session hours and is retained only in the generated tables. All periods have already been examined; these runs do not establish untouched out-of-sample or live execution performance.

## Verification and reproduction

Both research EAs compiled with zero errors and warnings. All eight CSV ledgers reconcile exactly to MT5 trade counts and gross profit; RR/cap/calendar flags and output hashes pass. M30 RR 1 reproduces the existing uncapped RTL 2020–26 ledger and GG ledger through July 13, 2026.

Inputs, frozen sources, compiled EAs, manifests, completion hashes, HTML tester reports, logs, `audit.json`, `summary.csv`, `yearly.csv`, and paired differences are saved in `Reports/timeframe_baseline_20261015/`.

Preparation: `python/prepare_timeframe_baseline.py`. Execute each expert’s tags with `python/run_mt5_job.py Reports/timeframe_baseline_20261015 RTL_timeframe <RTL tags>` and similarly `GG_timeframe <GG tags>`; existing completed jobs are preserved. Analysis: `venv/Scripts/python.exe python/analyze_timeframe_baseline.py`.
