# GG on weekly candles, flattened every session

2026-10-27, exploratory. [Protocol](PROTOCOL.md) fixed before any GG weekly result. Same
setup and controls as the [RTL weekly study](../rtl-weekly-flatten/RESULTS.md) and its
[controls](../rtl-weekly-flatten/CONTROL_RESULTS.md), with a green signal week.

**Finding:** weekly GG is weaker than weekly RTL and weaker than simply being long.
Flattened every session it nets $3,544 (2016-19) and $15,996 (2020-26), +0.33 / +0.18 R
per trade, but with an $18,760 drawdown in 2020-26. 2022 alone lost $12,903: ten stops
in eleven trades, buying breakouts above green weeks during the bear market. The
drawdown ran from November 2021 to January 2023 and was only recovered in May 2026. As
with RTL, flattening barely matters (held: $3,798 / $16,208). Against the controls, GG
earns less per trade than the plain long (-0.13 / -0.10 R), and its long sessions beat only
11% / 27% of random placements. Its 2020-26 drawdown is larger than 98% of them, so on
weekly bars GG's timing looks worse than random. Weekly RTL lost nothing in 2022 (+$807).

## 2016-19

| Variant | Trades | Sessions per trade | Win % | Gross R | Net R per trade (95% interval) | Net $ | Net PF | Max DD $ | Worst day $ | Median risk $ |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| **GG W1 flatten** | 33 | 18.5 | 60.6 | +0.379 | +0.326 (-0.047 to +0.701) | 3,544 | 1.66 | 2,880 | -435 | 336 |
| GG W1 flatten raw | 32 | 19.8 | 56.2 | +0.302 | +0.246 (-0.150 to +0.619) | 3,541 | 1.63 | 2,975 | -435 | 389 |
| GG W1 hold | 33 | 19.1 | 60.6 | +0.341 | +0.337 (-0.038 to +0.705) | 3,798 | 1.68 | 3,141 | -448 | 336 |
| GG W1 hold MT5-style | 32 | 20.3 | 56.2 | +0.272 | +0.268 (-0.133 to +0.665) | 3,954 | 1.69 | 3,203 | -448 | 389 |
| GG M30 baseline | 6,388 | 1.0 | 43.4 | +0.071 | -0.016 (-0.048 to +0.016) | 3,636 | 1.05 | 1,561 | -384 | 16 |
| Plain long | 50 | 16.5 | 64.0 | +0.512 | +0.464 (+0.156 to +0.750) | 8,744 | 2.12 | 3,312 | -635 | 364 |
| Green week, market entry | 42 | 15.6 | 54.8 | +0.283 | +0.235 (-0.104 to +0.568) | 3,998 | 1.63 | 3,461 | -635 | 286 |
| RTL W1 flatten (reference) | 25 | 24.2 | 56.0 | +0.288 | +0.234 (-0.201 to +0.666) | 4,563 | 2.10 | 2,461 | -516 | 357 |

## 2020-26 (through 2026-09-30)

| Variant | Trades | Sessions per trade | Win % | Gross R | Net R per trade (95% interval) | Net $ | Net PF | Max DD $ | Worst day $ | Median risk $ |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| **GG W1 flatten** | 51 | 20.5 | 52.9 | +0.195 | +0.181 (-0.128 to +0.497) | 15,996 | 1.42 | 18,760 | -3,098 | 1,395 |
| GG W1 flatten raw | 57 | 17.7 | 50.9 | +0.121 | +0.109 (-0.190 to +0.405) | 12,988 | 1.31 | 19,180 | -3,098 | 1,395 |
| GG W1 hold | 51 | 21.1 | 52.9 | +0.193 | +0.192 (-0.128 to +0.505) | 16,208 | 1.43 | 17,926 | -3,141 | 1,395 |
| GG W1 hold MT5-style | 57 | 18.2 | 50.9 | +0.167 | +0.166 (-0.135 to +0.478) | 17,920 | 1.43 | 17,854 | -3,140 | 1,395 |
| GG M30 baseline | 11,181 | 1.0 | 43.2 | +0.068 | +0.044 (+0.020 to +0.069) | 39,315 | 1.08 | 4,882 | -2,124 | 60 |
| Plain long | 74 | 20.0 | 56.8 | +0.295 | +0.282 (+0.018 to +0.540) | 37,568 | 1.80 | 14,108 | -1,857 | 1,379 |
| Green week, market entry | 73 | 14.9 | 46.6 | +0.061 | +0.049 (-0.196 to +0.303) | 14,639 | 1.33 | 18,822 | -3,098 | 1,136 |
| RTL W1 flatten (reference) | 44 | 21.7 | 61.4 | +0.392 | +0.377 (+0.043 to +0.707) | 27,199 | 2.06 | 7,637 | -3,098 | 1,528 |

2010-15 (reference): GG W1 flatten +0.35 R gross, +$1,654 (44 trades); GG M30 -$5,108.

## Flattening

Same picture as RTL: 128 of 128 GG trades are shared between the flattened and held
versions, and 3 end differently. Change per trade: -0.08 / -0.01 / -0.01 R (2010-15 /
2016-19 / 2020-26), mostly commission on about 20 daily round turns. Three trades opened
below their stop at a session open and ended while flat. 11 orders were rejected
because the next week opened above the green week's high (a green week often closes
near its high).

## Controls

| GG minus | Era | Gross R (95% interval) | Net R (95% interval) |
|---|---|---|---|
| Plain long | 2016-19 | -0.132 (-0.610 to +0.338) | -0.139 (-0.612 to +0.327) |
| Plain long | 2020-26 | -0.100 (-0.504 to +0.312) | -0.101 (-0.507 to +0.313) |
| Green week, market entry | 2016-19 | +0.097 (-0.415 to +0.594) | +0.090 (-0.417 to +0.589) |
| Green week, market entry | 2020-26 | +0.134 (-0.269 to +0.544) | +0.132 (-0.279 to +0.539) |

| Random timing (GG's sessions long from the open) | 2016-19 | 2020-26 |
|---|---:|---:|
| Sessions long | 600 | 999 |
| GG pattern $ | 2,147 | 15,504 |
| Shifted patterns: median / 95th $ | 4,768 / 7,469 | 21,359 / 35,827 |
| Shifts below GG | 11% | 27% |
| GG pattern DD $ (shifts' median) | 2,792 (2,449) | 18,172 (10,219) |
| Shifts with a larger DD | 34% | 2% |

- **Plain long:** GG earns less per trade in both eras and has the higher gross R in only
  6 of 17 years. It does not meet the reading rule.
- **Buy stop vs market entry on green weeks:** buying above the green week's high is a bit
  better than buying at the next open (+0.10 / +0.13 R; 10 of 17 years), but the intervals
  cross zero.
- **Random timing:** GG's long periods earn less than most random placements of the same
  shape, and in 2020-26 its drawdown is larger than 98% of them. Counting every held
  session (the look-ahead version) moves this to 41% / 76% of shifts below GG, still short
  of 95%.

## Together and next to M30

- **RTL and GG weekly together** (one contract each, by exit day): daily correlation 0.62 /
  0.70, both long in 39-41% of sessions. 2020-26 net $43,308 with DD $23,313 (worst day
  -$6,195), against the plain long's $37,568 with DD $14,108. 2016-19: $6,416, DD $4,488.
- **GG weekly next to GG M30:** 2020-26 together $55,368 with DD $17,239, against GG M30
  alone $39,315 with DD $4,882.

## Caveats

Exploratory, all data seen. Samples are small (32-57 GG trades per era) and every interval
is wide. GG's weakness is concentrated in 2022; without that year, its 2020-26 trades net
about $28.9k against RTL's $26.4k. Roll adjustment matters (raw levels give 6 more 2020-26 trades and
$3,008 less). Costs, fills and flattening are as in the RTL weekly study.

## Verification and reproduction

- **GG M30:** the simulator with a green signal reproduces all 26,505 trades of the MT5 GG
  M30 ledger (frozen 2026-10-15 run): same entry and exit minute and profit. 17 extra
  simulated trades fall before MT5 starts trading.
- **GG W1:** a fresh MT5 tester run of the frozen GG source on W1 (flatten and trade
  windows off) is reproduced trade by trade by `GG W1 hold MT5-style`: all 119 trades,
  entry and exit minute and profit to the cent; 14 simulated trades fall before MT5's
  June 2012 start.
- The RTL weekly ledger and the plain-long control are unchanged after the colour switch
  was added. Random-timing shift totals are checked by FFT. 13 unit tests pass, including
  a GG-specific one.

Study: `python/analyze_gg_weekly_flatten.py` (about 2 minutes; uses the RTL weekly minute
cache). MT5 job: `python/prepare_gg_weekly_flatten.py`, then
`python/run_mt5_job.py Reports/gg_weekly_flatten_20261027 GG_weekly_hold`. Ledgers,
`summary.csv`, `yearly.csv`, `control_gains.csv`, `paired_flat_hold.csv`, `results.json`
and the MT5 run are in `Reports/gg_weekly_flatten_20261027/`.
