# Full-bodied abnormal green candles

2026-11-24 follow-up to the [initial 10x screen](RESULTS.md).
**Primary definition fixed before results: body >=80% of high-low range**;
upper and lower wicks together <=20%. 70% and 90% are descriptive neighbours,
not a selection of the best historical cutoff. [Protocol](WICK_PROTOCOL.md).

## How many of the original 446?

| Minimum body % | Of original 446 | Share % |
|---|---|---|
| 70 | 243 | 54.5 |
| 80 | 170 | 38.1 |
| 90 | 92 | 20.6 |
| 100 | 21 | 4.7 |

Exactly wickless means open=low and close=high. The main 80% gate retains 170
original candles and excludes 276 (61.9%). This measures total wick fraction,
not only the upper wick; both limits are known when the signal candle closes.

## Full replay results

All original entry, stop, immediate 1R TP, pending lifetime, cutoff and cost
rules retained. A rejected signal does not replace an existing qualifying pending
order. Full-history one MNQ, $1.05/trade, June 2010-November 13, 2026:

| Filter | Trades | Net $ | Win % | PF | Path DD $ | Net extra $2/trade |
|---|---|---|---|---|---|---|
| control | 446 | 972.20 | 54.3 | 1.054 | 2,424.90 | 80.20 |
| body70 | 246 | 1,890.20 | 56.1 | 1.221 | 1,541.90 | 1,398.20 |
| body80 | 171 | 56.95 | 56.7 | 1.009 | 2,314.45 | -285.05 |
| body90 | 93 | -876.65 | 55.9 | 0.766 | 2,052.55 | -1,062.65 |

The primary 80% rule yields **$56.95** on **171 trades**,
with **$2,314.45** marked path drawdown. Removing its largest
winning trade leaves **$-391.50**. The net figures for
70/80/90% are exploratory neighbours on reused history, not unseen confirmation.

### Net dollars by period

| period | control | body70 | body80 | body90 |
|---|---|---|---|---|
| 2010-15 | -251.15 | -136.25 | -85.15 | -100.10 |
| 2016-19 | 314.45 | 246.00 | 274.65 | 201.85 |
| 2020-Sep2026 | 1,114.55 | 1,940.50 | -132.55 | -978.40 |
| Oct-Nov2026 | -205.65 | -160.05 | 0.00 | 0.00 |
| 2016-Nov2026 | 1,223.35 | 2,026.45 | 142.10 | -776.55 |
| all | 972.20 | 1,890.20 | 56.95 | -876.65 |

### Why replay instead of just deleting ledger rows?

| filter | shared | new | removed | changed_shared |
|---|---|---|---|---|
| control | 446 | 0 | 0 | 0 |
| body70 | 243 | 3 | 203 | 0 |
| body80 | 170 | 1 | 276 | 0 |
| body90 | 92 | 1 | 354 | 0 |

Shared counts signal IDs present in both runs; new counts previously untraded
signals that now fill; removed counts baseline signals no longer filled.
Changed shared compares entry time, exit time and net. Detailed candle shapes
and a ledger-only subset calculation are saved, separately from replay outcomes.

### 80% OHLC path sensitivities

| Path | Trades | Net $ | Path DD $ |
|---|---|---|---|
| directional | 171 | 56.95 | 2,314.45 |
| low_first | 171 | 56.95 | 2,314.45 |
| high_first | 171 | 56.95 | 2,314.45 |

Python OHLC screen, not native MT5. Spread is not separately simulated;
$1/$2 extra per-trade costs are stresses, not real execution modeling. Path
sensitivities do not bound every possible intraminute price ordering.

### Annual net dollars

| period | control | body70 | body80 | body90 |
|---|---|---|---|---|
| 2010 | -63.65 | -7.80 | -7.80 | -28.15 |
| 2011 | -207.00 | -81.25 | -69.45 | -49.35 |
| 2012 | -176.10 | -89.65 | -84.55 | -71.85 |
| 2013 | 42.35 | -10.25 | 26.05 | 32.20 |
| 2014 | -113.95 | -30.05 | 16.15 | 17.75 |
| 2015 | 267.20 | 82.75 | 34.45 | -0.70 |
| 2016 | -162.60 | -91.05 | -55.35 | -15.70 |
| 2017 | 35.55 | 25.80 | 47.05 | 42.70 |
| 2018 | -108.65 | 63.20 | 48.60 | 157.75 |
| 2019 | 550.15 | 248.05 | 234.35 | 17.10 |
| 2020 | -173.35 | -10.05 | -68.35 | 70.85 |
| 2021 | -63.95 | 315.30 | 126.05 | -70.20 |
| 2022 | 347.95 | -126.35 | -70.65 | 452.50 |
| 2023 | 1,222.80 | 941.05 | 721.85 | 462.10 |
| 2024 | 403.90 | 1,243.40 | 1,279.65 | 59.95 |
| 2025 | 815.80 | 377.70 | -917.15 | -1,358.30 |
| 2026 | -1,644.25 | -960.60 | -1,203.95 | -595.30 |

## Reproduction and evidence

```powershell
.\venv\Scripts\python.exe -m unittest discover -s python -p "test_abnormal_green_m1*.py" -v
.\venv\Scripts\python.exe python\abnormal_green_m1_wicks.py
```

All three unfiltered controls match original ledgers exactly. Shape values and
gates checked against raw OHLC; independent cumulative-sum signal detection,
first-entry/exit and full marked-DD verification passes for all 12 runs.
Original study outputs preserved. Full new outputs and hashes:
`Reports/abnormal_green_m1_20261124/wick_filter/`. The
`original_446_candle_shapes.csv` file contains each candle's body/upper/lower-wick
fractions. Subfolders `body70`, `body80`, `body90` contain trade and decision
ledgers and individual manifests. Compact tables and checks sit beside this report.
No production settings changed.
