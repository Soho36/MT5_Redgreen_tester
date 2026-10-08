# Why ES differs from NQ

2026-10-08 · Exploratory, no gate · [Baseline studies](../README.md)

**2026-10-09 follow-up:** [Fixed grids and every origin](../granularity/RESULTS.md) confirms strong NQ resolution sensitivity. The original causal attribution below remains exploratory. The follow-up also found omitted fast-stop control trades in the EA CSV logger: native NQ controls are audit-corrected there, and on 2026-10-09 the MT5 figures below (NQ, ES and yearly-coarse NQ) were audit-corrected too ([audit_signal_colour_ledgers.py](../../../python/audit_signal_colour_ledgers.py)); control figures moved by at most 0.005 R and no conclusion changed. Full ES attribution remains open.

## Summary

- **Question (user):** RTL fails on MES. Is that because ES candles span fewer ticks, or because ES moves
  differently (more mean-reverting)?
- **Mostly tick granularity.** Right after price touches the previous M30 high, NQ follows through and ES
  falls back. Rounding NQ prices to an ES-like grid removes about half of that difference in 2016–26, and
  all of it in 2010–15.
- **The rest is concentrated in tiny candles.** Under 8 ticks, ES breakouts fail even more often than the
  coarsened NQ (−0.15 vs −0.10 R). A guess, not tested: ES's very deep order book at each price makes the
  previous high hold more often.
- **ES is not generally more mean-reverting at the 30-minute scale.** Autocorrelation and variance ratios
  of M30 returns are close to 1 on both. NQ is only slightly more trending (2016–19 VR8 1.06 vs 0.99).
- **MT5 on the coarsened NQ confirms it for the strategy itself** ([below](#mt5-rtl-and-the-control-on-coarsened-nq-2026-10-08)).
  RTL mean R before costs falls from +0.093 / +0.085 to +0.020 / +0.041 (2016–19 / 2020–26), and from +0.005 to
  −0.123 in 2010–15, which is ES's level. Separately, ES's plain long loses with the RTL exit and coarsening does
  not reproduce that.

## Method

Script: [analyze_market_character.py](../../../python/analyze_market_character.py), 1-minute data, no EA, no costs,
2010-06 → 2026-07-14, session 01:00–23:30. For every M30 bar (about 181,000 per instrument):

- **Plain:** a long at the next bar's open, with a target and stop one candle range away (the geometry of the
  market-buy control).
- **Breakout:** if the next bar touches the high, a long at the high, stop at the low, target 1R (RTL
  geometry, any colour; "red" keeps red signal bars only).
- **Score:** which is hit first on 1-minute highs and lows, as expected R = 2p − 1. Same-minute double hits
  count half. Unresolved by 23:30 are left out (about 4–7%).
- **Hold %:** of the target-first cases, the share where that M30 bar also closes at or above the target.
  RTL exits on the bar close, not on the touch.
- **Coarsened NQ** ([build_coarse_nq.py](../../../python/build_coarse_nq.py)): every NQ price rounded to a
  per-year grid. The grid is k × 0.25, where k is the NQ/ES ratio of median M30 range that year: 0.5 in
  2010–16, 0.75 in 2017–19, 1.0 in 2020–23, 1.25 in 2024–25, 1.5 in 2026. NQ candles then span about as
  many steps as ES candles. File: `F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_coarse_2010-2026_ohlcv-1m.csv`.

This is a simplified bet: it exits on the touch and holds a single position. It measures how price behaves,
not the strategy, so its levels differ from the MT5 results. The plain bet is slightly positive on all
three series.

## Results

Breakout minus plain (expected R before costs, all colours / red only):

| Period | NQ | Coarsened NQ | ES |
|---|---|---|---|
| 2010–15 | −0.029 / −0.050 | −0.102 / −0.154 | −0.110 / −0.129 |
| 2016–19 | +0.012 / +0.032 | −0.037 / −0.027 | −0.092 / −0.095 |
| 2020–26 | +0.024 / +0.044 | +0.000 / +0.019 | −0.022 / −0.017 |

By signal-candle size in ticks (grid steps for coarsened NQ), 2016–26, breakout minus plain:

| Steps | NQ | Coarsened NQ | ES | Breakouts: NQ / coarse / ES |
|---|---|---|---|---|
| <8 | −0.012 | −0.096 | −0.147 | 1,179 / 10,387 / 11,515 |
| 8–16 | −0.005 | −0.022 | −0.060 | 4,075 / 16,471 / 17,211 |
| 16–24 | −0.009 | +0.006 | −0.013 | 4,638 / 11,232 / 10,963 |
| 24–32 | +0.002 | −0.008 | −0.025 | 4,110 / 7,069 / 6,735 |
| 32–48 | +0.015 | +0.037 | −0.003 | 7,237 / 7,140 / 7,028 |
| 48–64 | +0.032 | +0.020 | +0.015 | 5,917 / 3,210 / 3,070 |
| 64–128 | +0.021 | +0.023 | +0.015 | 14,805 / 2,910 / 2,910 |

- On real NQ most candles are large in ticks, so breakouts follow through. Coarsened, NQ gets as many small
  candles as ES, and those fail.
- At 16+ steps all three are within a few hundredths of each other (each cell about ±0.02–0.03).
- **Hold %** is 47–51% everywhere. ES is about 1–3 points lower; coarsening does not move NQ there.
- **M30 return structure** (lag-1 autocorrelation / VR8, period means): 2010–15 NQ +0.013 / 0.99, ES +0.005 /
  0.96; 2016–19 NQ +0.009 / 1.06, ES −0.008 / 0.99; 2020–26 NQ −0.003 / 0.99, ES −0.003 / 0.97. Coarsening
  does not change these.

## MT5: RTL and the control on coarsened NQ (2026-10-08)

The user imported the coarse file as `MNQcoarseDTBNT20102026`, with settings copied from
`MNQcontDTBNT20102026_2`. It was run with the same EA and settings as the [signal-colour](../signal-colour/RESULTS.md)
runs (red cap 3 = RTL baseline; market-buy control). Check: 100% of the ledger's candle ranges lie on the yearly grid.

Mean R before costs, audited ledgers (gain = RTL minus control, 95% interval from resampling days):

| | 2010–15 | 2016–19 | 2020–26 |
|---|---|---|---|
| **RTL** NQ | +0.005 | +0.093 | +0.085 |
| **RTL** coarsened NQ | **−0.123** | **+0.020** | **+0.041** |
| **RTL** ES | −0.118 | −0.039 | +0.002 |
| Control NQ | −0.036 | +0.009 | +0.007 |
| Control coarsened NQ | −0.019 | +0.015 | +0.006 |
| Control ES | −0.147 | −0.083 | −0.040 |
| Gain NQ | +0.041 | +0.085 | +0.078 |
| Gain coarsened NQ | −0.103 [−0.127, −0.079] | +0.005 [−0.023, +0.034] | +0.035 [+0.014, +0.058] |
| Gain ES | +0.029 | +0.044 | +0.042 |

After costs, coarsened NQ RTL: PF 0.758 / 1.042 / 1.058, net −$13.3k / +$2.7k / +$21.1k. Real NQ: +$38.0k in 2020–26.

- **Granularity alone removes about half of the RTL edge in 2016–26 and all of it in 2010–15.** There the
  coarsened NQ lands on ES exactly (−0.123 vs −0.118). Its win rate drops to ES levels too (35.9% vs 36.4%
  in 2010–15).
- **It works by removing the buy-stop gain, not the plain long.** On coarsened NQ the plain long stays
  around zero, like real NQ. On ES the plain long itself loses. Granularity does not reproduce that, so
  ES has a second, separate weakness. It shows only with the bar-close exit: in the touch-exit path
  measure, the ES plain long was as good as NQ's.
- **In 2016–26 coarsened NQ still beats ES** by about 0.04–0.06 R. That is about the size of ES's negative
  plain long.

**Meaning for the strategy:** the RTL edge needs candles that span many price steps. That fits NQ having no edge in
2010–15 (small candles) and a clear edge from about 2018 (large candles). If NQ's M30 range in ticks shrinks
again, the edge should shrink with it. *Corrected 2026-10-09:* an earlier version stated a ~30-tick requirement.
The [granularity study](../granularity/RESULTS.md#steps-per-candle-across-periods) shows a gradual decline, not a
cutoff: the gain over the control is near zero at about 14–15 steps per candle and about +0.04 to +0.09 R at 27–29
steps. Read a prediction for another instrument from that curve, stated before its data is used; no threshold is
established.

## Reproduce

```powershell
.\venv\Scripts\python.exe python\build_coarse_nq.py "F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv" "F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_coarse_2010-2026_ohlcv-1m.csv"
.\venv\Scripts\python.exe python\analyze_market_character.py
# MT5 on the imported coarse symbol
.\venv\Scripts\python.exe python\prepare_signal_colour.py nqcoarse
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\signal_colour_20261008_nqcoarse RTL_signal
.\venv\Scripts\python.exe python\analyze_signal_colour.py nqcoarse
```
