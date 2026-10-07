# Signal colour and a no-pattern control (MNQ, control also on MES)

2026-10-08 · Exploratory, no pre-set gate · [Baseline studies](../README.md)

## Summary

- **Question:** is the RTL edge the red candle, any buy stop over the previous bar, or just being long NQ
  while it rises?
- **Not drift.** The control has no pattern: it buys at market at every bar open, with the same stop
  distance and exit. It earns about nothing before costs: +0.011 / +0.009 R (2016–19 / 2020–26), with
  intervals that include zero. It loses after costs.
- **Colour matters little.** Green (the user's GG) gives +0.073 / +0.066 R against red's +0.093 / +0.085.
  The intervals overlap. Red is slightly better and MaxRedRun 3 helps it a little. The edge is the
  **buy stop over a previous M30 high**, not the red candle.
- **Running RTL and GG together** doubles net profit and roughly doubles drawdown. Daily correlation is
  +0.62, so this is about twice the size, not diversification. This matches the user's experience.
- **Meaning for forward testing:** the thing to watch is whether buy-stop entries keep beating plain long
  entries on NQ. Here they beat them by about 0.06–0.08 R in 2016–26.

## Setup

- EA: the baseline runband EA with one added input, `SignalMode`. 0 = red (baseline), 1 = green,
  2 = any non-doji candle, 3 = control (market buy at each bar open while flat, stop one previous-candle
  range below). Edits are in `python/prepare_signal_colour.py`. Flatten, early-close calendar, windows and
  exit are unchanged.
- MNQ `MNQcontDTBNT20102026_2`, M30, 1-minute OHLC, 2010-06-07 → 2026-07-14, $1.05 costs, R = profit ÷
  (candle range × $2).
- Checks: mode 0 with cap 3 reproduces the baseline ledger byte for byte. The standalone
  `mt5/experts/GG_r_MFE_buy-stop-entry_runband.cs` (the RTL EA with only the colour flipped; `MinRedRun` /
  `MaxRedRun` keep their names and count green bars) reproduces the green cap-3 run byte for byte.

## Results

Mean R before costs, with 95% intervals from resampling days:

| Run | 2010–15 | 2016–19 | 2020–26 |
|---|---|---|---|
| Red, cap 3 (baseline) | +0.005 [−0.021, +0.031] | +0.093 [+0.059, +0.129] | +0.085 [+0.059, +0.112] |
| Green, cap 3 | +0.019 [−0.007, +0.045] | +0.073 [+0.043, +0.105] | +0.066 [+0.042, +0.091] |
| Red, no cap | +0.006 | +0.081 | +0.071 |
| Green, no cap | +0.022 | +0.071 | +0.070 |
| Any candle | +0.013 | +0.057 | +0.061 |
| Control: market buy, no pattern | −0.034 [−0.056, −0.013] | +0.011 [−0.015, +0.037] | +0.009 [−0.011, +0.029] |

After costs:

| Run | PF 2016–19 | PF 2020–26 | Net $ 2020–26 | Max DD $ 2020–26 | Trades (all) |
|---|---|---|---|---|---|
| Red, cap 3 | 1.106 | 1.107 | 37,981 | 4,847 | 23,427 |
| Green, cap 3 | 1.051 | 1.084 | 35,626 | 5,675 | 24,852 |
| Any candle | 1.027 | 1.078 | 40,928 | 5,803 | 32,960 |
| Control | 0.954 | 1.008 | 6,112 | 11,261 | 35,800 |

RTL + GG (cap 3) as two accounts, summed by exit day:

| Period | RTL net / DD | GG net / DD | Both net / DD |
|---|---|---|---|
| 2016–19 | 6,485 / 1,412 | 3,701 / 1,619 | 10,186 / 3,032 |
| 2020–26 | 37,981 / 4,352 | 35,626 / 4,881 | 73,607 / 8,517 |

- **By year:** every buy-stop variant follows the same path. All lose 2010–17 after costs and all are positive
  2018–26. The control is negative or near zero in almost every year.
- **2010–15:** buy-stop entries already beat the control by about 0.04–0.05 R before costs. But candles
  were small, so costs were 0.19 R per trade (0.03 R in 2020–26) and outweighed it.
- "Any candle" is below both red and green. One mechanical difference: in red or green mode a resting order
  survives opposite-colour bars, so some entries are at an older high. In "any" mode the order always
  moves to the latest bar. Why this matters is not tested.

## MES: same control (2026-10-08)

The user asked for the same market-buy control on MES. Red cap 3 was rerun with the same EA and
reproduces the [MES baseline](../mes-unseen-instrument/RESULTS.md) byte for byte.

Mean R before costs. The middle column is the gain over the control: red minus control, with a 95%
interval from resampling days jointly.

| | Control (plain long) | Gain over control | = Red baseline |
|---|---|---|---|
| MNQ 2010–15 | −0.034 | +0.039 [+0.014, +0.062] | +0.005 |
| MNQ 2016–19 | +0.011 | +0.083 [+0.054, +0.112] | +0.093 |
| MNQ 2020–26 | +0.009 | +0.075 [+0.053, +0.099] | +0.085 |
| MES 2010–15 | −0.142 | +0.025 [+0.003, +0.047] | −0.118 |
| MES 2016–19 | −0.081 | +0.042 [+0.014, +0.068] | −0.039 |
| MES 2020–26 | −0.037 | +0.039 [+0.019, +0.060] | +0.002 |

- **The buy-stop gain exists on ES too.** In every period it is positive with an interval above zero, about
  half the NQ size (+0.04 vs +0.08 R). This comparison was decided on MNQ before the MES control was run.
  MES itself had already been seen in the baseline test, so this is supporting evidence, not a clean
  confirmation.
- **The instruments differ in the plain-long control.** On NQ a long entered at the bar open with this stop
  and exit breaks even before costs (2016–26). On ES it loses −0.04 to −0.08 R. That fits ES being more
  mean-reverting intraday than NQ, but this is not tested here. So the buy-stop gain only shows up as
  profit where the plain long is not negative.
- **Correction to the MNQ summary above:** "not drift" holds in that the plain long earns ~0 on NQ. But
  the plain long is exactly where NQ and ES differ, so the market's character (drift, trend vs reversion)
  does decide whether the strategy pays.

## Reproduce

```powershell
.\venv\Scripts\python.exe python\prepare_signal_colour.py
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\signal_colour_20261008 RTL_signal
.\venv\Scripts\python.exe python\analyze_signal_colour.py
# MES control
.\venv\Scripts\python.exe python\prepare_signal_colour.py mes
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\signal_colour_20261008_mes RTL_signal
.\venv\Scripts\python.exe python\analyze_signal_colour.py mes
```
