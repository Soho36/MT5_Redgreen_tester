# The YM experiments on RTY (Russell 2000)

2026-10-23 · Descriptive comparison, no pre-set gate · [Baseline studies](../README.md) ·
Same method as [YM](../ym-unseen-instrument/RESULTS.md)

## Summary

- **Question (user):** repeat the YM experiments on Russell 2000 futures (RTY): the four baselines, the plain-long
  control and RTL on H1.
- **Answer: RTY behaves like YM.** A small long gross edge, too small for costs on M30; both shorts lose. Same-window
  comparison (2018–26), RTL gross R per trade: NQ +0.079, YM +0.029, **RTY +0.024**, ES −0.004. Net 2020–26: RTL
  −$3.5k (PF 0.978), GG −$11.2k (0.934), RTL-short −$12.8k, GG-short −$11.1k. RTL makes money in 2 of 10 years
  (2020, 2021), GG in 1.
- **Buy stop versus plain long:** the gain transfers again, +0.050 / +0.040 R (2018–19 / 2020–26, intervals above
  zero). A plain long on RTY loses a little (−0.031 / −0.015), like YM.
- **Ticks per candle:** M2K pays $0.50 per 0.1 tick, the same as MNQ and MYM. RTY's median M30 candle spans 34 ticks
  (NQ 94 in the same window), so commission costs 0.083 R per trade. Gross R does not rise with ticks.
- **H1:** helps again by halving the trades: 2020–26 net +$3.1k (PF 1.029) against −$3.5k on M30; 2018–26 +$2.3k,
  positive in 4 of 10 years, most of it in 2025–26.
- **Across the four instruments (2018–26):** the buy-stop gain is +0.037 to +0.042 R on ES, YM and RTY and +0.066 on
  NQ. The plain long is +0.013 on NQ and −0.013 to −0.041 on the others. NQ stands out on both: a somewhat larger gain
  and a market that did not punish a plain long.

## Setup

| | |
|---|---|
| Data | Databento `GLBX.MDP3` `RTY.FUT` 1-minute; CME RTY starts 2017-07-10 (Russell traded on ICE before). [Data build](../../reference/DATA_BUILD.md#rty-build-2026-10-23) |
| Symbol | `M2KcontDTBNT20172026`, $5/pt (M2K), tick 0.1 = $0.50 |
| Runs | Exactly the YM study's EAs and INIs, symbol and dates changed: RTL, GG, RTL-short, GG-short (M30); `RTL_signal` market-buy control and red check; `RTL_timeframe` on H1. Tester 2017-07-10 → 2026-10-23, 1-minute OHLC, 1 lot |
| Windows | 2018–19 and 2020–26 on all four instruments (NQ/ES/YM ledgers from the YM study). 2017 H2 is the thin launch period, shown apart. Trades before 2026-10-01 |
| Costs | $1.05 per trade. R = trade profit ÷ (signal candle range × $/pt) |

**Checks.** Control ledger audited against the MT5 report (83 fast stops recovered, totals match); RTL ledger needs
no recovery; the signal EA in red-candle mode reproduces RTL_runband exactly (14,778 trades). $/pt read back as 5.0
from every ledger. 4 RTL trades fall on the two data-gap days (2020-03-16, 2025-11-28).

## Results (net of $1.05)

| Strategy | Window | Inst | Trades | Gross R | 95% interval | Net R | PF net | Net $ | Max DD $ |
|---|---|---|---:|---:|---|---:|---:|---:|---:|
| RTL | 2018–19 | **RTY** | 3,207 | **+0.019** | −0.026 … +0.065 | −0.110 | 0.914 | −2,179 | 3,061 |
| | | NQ | 3,068 | +0.103 | +0.055 … +0.150 | +0.043 | 1.101 | 4,628 | 2,176 |
| | | ES | 3,133 | +0.004 | −0.040 … +0.047 | −0.073 | 0.977 | −873 | 1,947 |
| | | YM | 3,048 | +0.082 | +0.034 … +0.129 | −0.002 | 1.077 | 2,537 | 827 |
| | 2020–26 | **RTY** | 10,778 | **+0.025** | −0.001 … +0.051 | −0.044 | 0.978 | −3,486 | 6,509 |
| | | NQ | 10,501 | +0.072 | +0.046 … +0.097 | +0.048 | 1.090 | 38,400 | 5,781 |
| | | ES | 10,803 | −0.006 | −0.030 … +0.018 | −0.048 | 0.964 | −9,086 | 10,288 |
| | | YM | 10,889 | +0.014 | −0.010 … +0.038 | −0.046 | 0.987 | −2,467 | 5,403 |
| GG | 2018–19 | **RTY** | 3,178 | **+0.039** | −0.007 … +0.084 | −0.080 | 0.923 | −2,080 | 2,374 |
| | 2020–26 | **RTY** | 10,908 | **+0.003** | −0.021 … +0.027 | −0.061 | 0.934 | −11,248 | 14,004 |
| RTL-short | 2018–19 | **RTY** | 3,361 | **−0.027** | −0.074 … +0.021 | −0.165 | 0.868 | −3,570 | 4,024 |
| | 2020–26 | **RTY** | 11,333 | **−0.011** | −0.036 … +0.013 | −0.082 | 0.922 | −12,810 | 13,427 |
| GG-short | 2018–19 | **RTY** | 3,398 | **−0.021** | −0.066 … +0.024 | −0.152 | 0.810 | −5,732 | 6,216 |
| | 2020–26 | **RTY** | 11,349 | **−0.008** | −0.033 … +0.016 | −0.075 | 0.936 | −11,055 | 13,038 |

GG and the shorts on NQ/ES/YM in the same windows: `Reports/rty_baselines_20261023/summary.csv` (GG 2020–26 gross R:
NQ +0.068, ES +0.003, YM +0.005; shorts negative or about zero everywhere). 2017 H2 (thin launch months, ~700 trades
each) loses net on all four. RTY net $ by year: RTL positive in 2020 (+$431) and 2021 (+$315) only; GG in 2020 only;
the shorts in no year.

## Plain-long control

| Window | Inst | RTL gross R | Plain long R | Buy-stop gain | Gain 95% |
|---|---|---:|---:|---:|---|
| 2018–19 | **RTY** | +0.019 | −0.031 | **+0.050** | +0.013 … +0.088 |
| | NQ | +0.103 | +0.031 | +0.072 | +0.033 … +0.109 |
| | ES | +0.004 | −0.041 | +0.044 | +0.008 … +0.080 |
| | YM | +0.082 | +0.005 | +0.077 | +0.038 … +0.114 |
| 2020–26 | **RTY** | +0.025 | −0.015 | **+0.040** | +0.020 … +0.062 |
| | NQ | +0.072 | +0.007 | +0.064 | +0.044 … +0.085 |
| | ES | −0.006 | −0.041 | +0.035 | +0.016 … +0.055 |
| | YM | +0.014 | −0.018 | +0.032 | +0.012 … +0.052 |
| 2018–26 | **RTY** | +0.024 | −0.019 | **+0.042** | +0.024 … +0.060 |
| | NQ | +0.079 | +0.013 | +0.066 | +0.048 … +0.084 |
| | ES | −0.004 | −0.041 | +0.037 | +0.020 … +0.055 |
| | YM | +0.029 | −0.013 | +0.042 | +0.024 … +0.059 |

## Ticks per candle and H1

RTY RTL by signal candle size, 2018–26 (median 34 ticks): gross R +0.021 / +0.040 / +0.032 / +0.030 / +0.020 / +0.040
for 10–20 / 20–30 / 30–45 / 45–70 / 70–110 / 110+ ticks, against a cost of 0.149 / 0.088 / 0.058 / 0.039 / 0.025 /
0.014 R. Flat above 10 ticks, and below NQ's ~+0.09 at every size, as on YM. Table: `ticks_buckets.csv`.

| Inst | TF | Window | Trades | Median ticks | Gross R | Cost R | Net $ | PF net |
|---|---|---|---:|---:|---:|---:|---:|---:|
| **RTY** | M30 | 2020–26 | 10,778 | 39 | +0.025 | 0.069 | −3,486 | 0.978 |
| **RTY** | H1 | 2020–26 | 5,950 | 56 | +0.024 | 0.047 | 3,088 | 1.029 |
| **RTY** | M30 | 2018–26 | 13,985 | 34 | +0.024 | 0.083 | −5,666 | 0.969 |
| **RTY** | H1 | 2018–26 | 7,646 | 49 | +0.029 | 0.056 | 2,322 | 1.019 |
| YM | H1 | 2018–26 | 7,625 | 58 | +0.042 | 0.046 | 8,812 | 1.059 |
| ES | H1 | 2018–26 | 7,640 | 31 | +0.017 | 0.035 | 4,534 | 1.022 |
| NQ | M30 | 2018–26 | 13,569 | 94 | +0.079 | 0.032 | 43,028 | 1.091 |
| NQ | H1 | 2018–26 | 7,526 | 134 | +0.068 | 0.022 | 32,058 | 1.095 |

On RTY, H1 keeps the gross R and halves the commission. RTY H1 by year: 2020 +$1.6k, 2025 +$2.4k, 2026 +$1.5k,
2024 about 0; 2017–19 and 2021–23 lose. No overnight exits in any H1 run. H1 was chosen on YM after the user's hand
runs, so it is not an independent choice here either. Full table: `m30_vs_h1.csv`.

## Reproduce

```powershell
.\venv\Scripts\python.exe python\build_continuous.py RTY "F:\DATABENTO\RTY_16_YEARS" "F:\DATABENTO\RTY_16_YEARS\source\glbx-mdp3-20100606-20261021.ohlcv-1m.dbn"
.\venv\Scripts\python.exe python\import_custom_symbol.py "F:\DATABENTO\RTY_16_YEARS\MT5_RTY_continuous_2017-2026_ohlcv-1m.csv" M2KcontDTBNT20172026 MNQcontDTBNT20102026_2 0.1 0.5 Reports\rty_symbol_20261023
.\venv\Scripts\python.exe python\prepare_rty_baselines.py
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\rty_baselines_20261023 <EA> <tag>   # per job, see manifest.json
.\venv\Scripts\python.exe python\analyze_rty_baselines.py
```
