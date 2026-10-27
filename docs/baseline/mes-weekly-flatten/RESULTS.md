# RTL on weekly MES candles, flattened every session

2026-10-27, exploratory. [Protocol](PROTOCOL.md) fixed before any MES weekly result. Same
setup and controls as the [NQ weekly study](../rtl-weekly-flatten/RESULTS.md) and its
[controls](../rtl-weekly-flatten/CONTROL_RESULTS.md), on ES at $5 per point (one MES).

**Finding:** weekly candles do give ES the resolution its M30 candles lack, and weekly RTL
on MES makes money where M30 RTL loses: +$3,429 / +$12,614 (2016-19 / 2020-26) against
-$4,653 / -$9,086 on M30. But the buy stop is not the reason. A plain weekly long on ES
does as well per trade (RTL minus plain long -0.07 / +0.02 R, intervals across zero) and
earns more ($7,281 / $22,767). RTL's long sessions beat only 21% / 57% of random
placements. So it is the same picture as NQ: on weekly bars RTL mostly harvests the
index's upward drift, and the M30 buy-stop edge does not reappear at the weekly scale on
either instrument. Weekly bars therefore cannot show whether resolution was ES's M30
problem. ES weekly RTL lost in 2010-15 (-$777) and its 2020-26 profit is concentrated
(the five best trades are 84% of it).

## Resolution

Median signal-candle range in ticks (0.25 points):

| | ES M30 | NQ M30 | ES W1 | NQ W1 |
|---|---:|---:|---:|---:|
| 2016-19 | 10 | 30 | 185 | 715 |
| 2020-26 | 25 | 115 | 673 | 3,056 |

The NQ resolution study found the M30 buy-stop gain near zero at about 15 steps per
candle and +0.06 to +0.09 R from about 30. Weekly ES candles are far beyond that, so a
missing gain here is not a resolution limit.

## 2016-19

| Variant | Trades | Sessions per trade | Win % | Gross R | Net R per trade (95% interval) | Net $ | Net PF | Max DD $ | Worst day $ | Median risk $ |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| **MES W1 flatten** | 20 | 33.5 | 60.0 | +0.438 | +0.356 (-0.147 to +0.849) | 3,429 | 2.45 | 1,847 | -527 | 231 |
| MES W1 flatten raw | 20 | 33.3 | 60.0 | +0.469 | +0.388 (-0.100 to +0.865) | 3,499 | 2.51 | 1,867 | -527 | 232 |
| MES W1 hold | 20 | 34.0 | 60.0 | +0.354 | +0.349 (-0.144 to +0.832) | 3,195 | 2.25 | 2,025 | -574 | 231 |
| MES W1 hold MT5-style | 20 | 34.0 | 60.0 | +0.365 | +0.361 (-0.135 to +0.859) | 3,182 | 2.25 | 2,066 | -574 | 231 |
| MES M30 baseline | 6,286 | 1.0 | 39.7 | -0.040 | -0.142 (-0.172 to -0.112) | -4,653 | 0.92 | 5,328 | -292 | 12 |
| Plain long | 38 | 23.5 | 60.5 | +0.509 | +0.436 (+0.064 to +0.796) | 7,281 | 2.62 | 1,556 | -617 | 236 |
| Red week, market entry | 63 | 5.9 | 38.1 | +0.571 | +0.499 (-0.145 to +1.309) | 3,712 | 1.98 | 1,059 | -455 | 87 |
| NQ RTL W1 flatten (reference) | 25 | 24.2 | 56.0 | +0.288 | +0.234 (-0.201 to +0.666) | 4,563 | 2.10 | 2,461 | -516 | 357 |

## 2020-26 (through 2026-09-30)

| Variant | Trades | Sessions per trade | Win % | Gross R | Net R per trade (95% interval) | Net $ | Net PF | Max DD $ | Worst day $ | Median risk $ |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| **MES W1 flatten** | 45 | 21.3 | 57.8 | +0.302 | +0.276 (-0.043 to +0.594) | 12,614 | 1.79 | 4,197 | -925 | 841 |
| MES W1 flatten raw | 50 | 19.5 | 54.0 | +0.205 | +0.181 (-0.121 to +0.483) | 10,199 | 1.54 | 3,868 | -925 | 805 |
| MES W1 hold | 45 | 21.9 | 57.8 | +0.272 | +0.270 (-0.045 to +0.582) | 11,623 | 1.69 | 4,717 | -911 | 841 |
| MES W1 hold MT5-style | 50 | 20.0 | 54.0 | +0.225 | +0.224 (-0.085 to +0.526) | 11,894 | 1.63 | 4,484 | -815 | 805 |
| MES M30 baseline | 10,803 | 1.0 | 40.8 | -0.006 | -0.048 (-0.071 to -0.024) | -9,086 | 0.96 | 10,215 | -1,251 | 31 |
| Plain long | 82 | 17.7 | 54.9 | +0.281 | +0.260 (+0.025 to +0.503) | 22,767 | 1.86 | 5,529 | -1,369 | 718 |
| Red week, market entry | 122 | 4.3 | 30.3 | +0.337 | +0.310 (-0.165 to +0.873) | 8,102 | 1.46 | 3,387 | -1,403 | 173 |
| NQ RTL W1 flatten (reference) | 44 | 21.7 | 61.4 | +0.392 | +0.377 (+0.043 to +0.707) | 27,199 | 2.06 | 7,637 | -3,098 | 1,528 |

2010-15 (reference): MES W1 flatten -0.01 R gross, -$777 (40 trades); plain long +0.25 R,
+$3,273; MES M30 -$15,366.

## Controls

| RTL minus | Era | Gross R (95% interval) | Net R (95% interval) |
|---|---|---|---|
| Plain long | 2016-19 | -0.071 (-0.691 to +0.551) | -0.081 (-0.699 to +0.545) |
| Plain long | 2020-26 | +0.020 (-0.373 to +0.405) | +0.016 (-0.375 to +0.409) |
| Red week, market entry | 2016-19 | -0.133 (-1.074 to +0.701) | -0.143 (-1.072 to +0.684) |
| Red week, market entry | 2020-26 | -0.035 (-0.665 to +0.530) | -0.034 (-0.657 to +0.538) |

| Random timing (RTL's sessions long from the open) | 2016-19 | 2020-26 |
|---|---:|---:|
| Sessions long | 651 | 915 |
| RTL pattern $ | 3,379 | 10,724 |
| Shifted patterns: median / 95th $ | 4,323 / 6,918 | 9,880 / 17,601 |
| Shifts below RTL | 21% | 57% |
| RTL pattern DD $ (shifts' median) | 1,739 (2,128) | 4,882 (5,126) |
| Shifts with a larger DD | 66% | 55% |

- None of the reading rules is met. RTL has the higher gross R than the plain long in 7
  of 17 years. For comparison, on M30 the ES buy stop beat its plain long by +0.04 R in
  both eras ([YM control study](../ym-unseen-instrument/RESULTS.md)).
- Counting every held session (the look-ahead version) gives 60% / 99% of shifts below
  RTL: once more the breakout fill days carry the score.
- **Why ES weekly is positive while ES M30 loses:** the weekly plain long is positive on
  ES (+$7,281 / +$22,767), unlike the M30 plain long. At a weekly stop (median $231 / $841
  per MES), $1.05 per round turn is almost free, and holding for weeks collects ES's drift
  instead of intraday noise. With +$2 per round turn, weekly RTL keeps $2,091 / $10,694;
  M30 falls to -$17,225 / -$30,692.

## Flattening

As on NQ: all 105 trades are shared between flattened and held, 3 end differently, and
the change per trade is -0.01 / +0.01 / +0.01 R (2010-15 / 2016-19 / 2020-26). Two
breakouts filled at a reopen; three trades opened below their stop while flat. The ES
data holes (2020-02-28, 2020-06-30) fall outside RTL positions. One session closed at its
last bar instead of the cutoff: 2018-07-04, where the ES data ends at 19:59 and the
calendar's cutoff is 20:00.

## Caveats

Exploratory, and ES was already used for M30 tests (unseen for weekly bars only). Samples
are small (20-50 trades per era) and every interval is wide. 2025: RTL weekly +$29 against
the plain long's +$6,976. Raw levels give 5 more 2020-26 trades and $2,415 less.

## Verification and reproduction

- **ES M30:** the simulator reproduces all 26,342 trades of the MT5 ES M30 RTL ledger
  (YM/ES baselines, 2026-10-23): same entry and exit minute and profit.
- **MES W1:** a fresh MT5 tester run of the same frozen RTL source on
  `MEScontDTBNT20102026_2`, W1, flatten and windows off, is reproduced trade by trade by
  `MES W1 hold MT5-style`: all 95 trades, entry and exit minute and profit to the cent.
- **Tick order on flat minutes, found while checking ES:** 18 tiny-candle ES trades first
  failed to match. All were stopped inside a minute whose close equals its open. MT5
  orders such a minute by the last minute that moved: high first after a rise, low first
  after a fall (2,952 of 2,952 such fills across NQ RTL, NQ GG and ES). With that rule all
  78,680 MT5 M30 trades (NQ RTL, NQ GG, ES RTL) match exactly, NQ's two earlier same-minute
  timing differences included. Rerunning the NQ RTL, control and GG weekly studies changes
  no number; 28 timestamps move by seconds within their minute.
- The NQ weekly ledger is unchanged; 15 unit tests pass.

Study: `python/analyze_mes_weekly_flatten.py` (about 3 minutes; first run builds
`minutes_es.npz`). MT5 job: `python/prepare_mes_weekly_flatten.py`, then
`python/run_mt5_job.py Reports/mes_weekly_flatten_20261027 RTL_weekly_hold_mes`. Ledgers,
`summary.csv`, `yearly.csv`, `control_gains.csv`, `paired_flat_hold.csv`, `results.json`
and the MT5 run are in `Reports/mes_weekly_flatten_20261027/`.
