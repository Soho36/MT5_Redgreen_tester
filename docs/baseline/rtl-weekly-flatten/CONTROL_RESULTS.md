# Weekly RTL controls: plain long and random timing

2026-10-27, exploratory. [Control protocol](CONTROL_PROTOCOL.md) fixed before any control
result. Follow-up to [RTL on weekly candles, flattened every session](RESULTS.md).

**Finding:** on weekly bars, neither RTL's buy stop nor its timing shows an edge over
simply being long NQ. The plain long (buy at every week's first open while flat, stop one
weekly range below, same weekly-close 1R exit and daily flatten) earns more per trade in
2016-19 (+0.51 vs +0.29 R before costs) and a little less in 2020-26 (+0.30 vs +0.39).
RTL minus plain long is -0.22 / +0.10 R, with intervals wide across zero, and RTL is
higher in 8 of 17 years. RTL's own long periods, moved to random times, earn about the
same in 2016-19 and more in 2020-26 (better than 81% of shifts), short of the 95% bar set
in advance. What weekly RTL does give is less time in the market (55-59% of sessions
against 80-85%) and, in 2020-26, a smaller drawdown ($7.6k against $14.1k for the plain
long, mostly 2022). On M30 the buy stop beats the plain long by about +0.07 R with
intervals above zero; on weekly bars that gain is not visible.

## Controls

All three use the primary weekly setup: flat at every cutoff and bought back at the next
open, roll-adjusted levels, profit in raw prices, $1.05 per daily round turn, one MNQ.

- **Plain long:** the weekly form of the repo's market-buy control (`SignalMode = 3`). At
  the first session of every week while flat, buy at the open (one tick above, as MT5
  fills it); stop = entry - the previous week's range. No candle pattern.
- **Red week, market entry:** RTL's signals and stop (a red week, stop at its low), but buy
  at the next week's first open instead of waiting for the buy stop above the high.
- **Random timing:** RTL's own in-market sessions shifted in time by every circular shift
  of at least 60 sessions inside each era (912 / 1,626 shifts). Each session scores one MNQ
  long from the first open to the flatten, minus $1.05.

## 2016-19

| Variant | Trades | Sessions per trade | Win % | Gross R | Net R per trade (95% interval) | Net $ | Net PF | Max DD $ | Worst day $ | Median risk $ |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| RTL (buy stop) | 25 | 24.2 | 56.0 | +0.288 | +0.234 (-0.192 to +0.656) | 4,563 | 2.10 | 2,461 | -516 | 357 |
| Plain long | 50 | 16.5 | 64.0 | +0.512 | +0.464 (+0.165 to +0.751) | 8,744 | 2.12 | 3,312 | -635 | 364 |
| Red week, market entry | 70 | 4.6 | 38.6 | +0.655 | +0.569 (-0.124 to +1.409) | 5,764 | 2.19 | 1,492 | -516 | 105 |

## 2020-26 (through 2026-09-30)

| Variant | Trades | Sessions per trade | Win % | Gross R | Net R per trade (95% interval) | Net $ | Net PF | Max DD $ | Worst day $ | Median risk $ |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| RTL (buy stop) | 44 | 21.7 | 61.4 | +0.392 | +0.377 (+0.041 to +0.696) | 27,199 | 2.06 | 7,637 | -3,098 | 1,528 |
| Plain long | 74 | 20.0 | 56.8 | +0.295 | +0.282 (+0.016 to +0.546) | 37,568 | 1.80 | 14,108 | -1,857 | 1,379 |
| Red week, market entry | 131 | 4.1 | 30.5 | +0.339 | +0.323 (-0.114 to +0.820) | 14,394 | 1.40 | 4,603 | -1,922 | 375 |

2010-15 (reference): RTL +0.196 R gross / $892, plain long +0.246 / $3,464, red week market
entry +0.057 / $1,005.

## Buy-stop gain

RTL minus control, mean R per trade, independent trade bootstraps (10,000 draws).

| RTL minus | Era | Gross R (95% interval) | Net R (95% interval) |
|---|---|---|---|
| Plain long | 2016-19 | -0.224 (-0.751 to +0.322) | -0.230 (-0.752 to +0.287) |
| Plain long | 2020-26 | +0.096 (-0.335 to +0.515) | +0.095 (-0.335 to +0.514) |
| Red week, market entry | 2016-19 | -0.367 (-1.299 to +0.460) | -0.335 (-1.273 to +0.476) |
| Red week, market entry | 2020-26 | +0.052 (-0.554 to +0.611) | +0.054 (-0.547 to +0.598) |

The fixed reading needs a positive gain in both eras and a 2020-26 interval above zero:
neither control comparison meets it. By year, RTL has the higher gross R in 8 of 17 years
against the plain long and 11 of 17 against the red-week market entry. The red-week
market entry buys lower (at the week open, under the red high), so its risk is about a
quarter of RTL's and it is stopped more often (win 31-39%). Its R per trade is similar or
higher, but its dollars are smaller.

## Random timing

| Pattern | Era | Sessions long | RTL pattern $ | Shifts: median / 95th $ | Shifts below RTL | RTL DD $ | Shifts' median DD $ | Shifts with higher DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| As fixed | 2016-19 | 605 | 7,065 | 4,621 / 7,794 | 89.6% | 1,571 | 2,449 | 92.4% |
| As fixed | 2020-26 | 955 | 44,950 | 19,572 / 36,277 | 99.4% | 5,850 | 9,987 | 97.9% |
| **From the open** | 2016-19 | 580 | 4,562 | 4,428 / 7,567 | 52.2% | 2,066 | 2,393 | 63.9% |
| **From the open** | 2020-26 | 911 | 27,808 | 18,773 / 35,040 | 80.9% | 6,846 | 9,871 | 91.1% |

- **Read the "from the open" rows.** The protocol scored every session RTL held, including
  the day each buy stop filled. That day is in RTL's pattern because price broke out during
  it, so scoring it from the open looks ahead: the 69 fill days carry $2,503 / $17,142 of
  full-session profit. I noticed this after seeing the result. The correction keeps only
  sessions RTL was long from the first bar; those were decided at the previous close.
  Neither version meets the 95%-in-both-eras reading.
- **Corrected,** RTL's long periods earn what random periods of the same shape earn in
  2016-19, and more in 2020-26 (81% of shifts below). Their drawdown is smaller than 91% of
  shifts in 2020-26 but only 64% in 2016-19: a risk hint, not an established effect.
- RTL's real ledger ($4,263 / $27,255 by exit day) is below its whole-session pattern,
  because it enters at the breakout level and stops out inside sessions.

## Caveats

Exploratory; all data seen before. Weekly samples are small (25-131 trades per era), so
every interval is wide: this is "no visible edge", not "proof of none". The plain long's
higher dollars come with more time in the market and a deep 2022 loss (-$6,360 that year
against RTL +$807). The random-timing correction was made after seeing the result and is
disclosed above. Costs, fills and flattening are as in the main study.

## Verification and reproduction

- **MT5 W1 check of the market-entry path:** a fresh MT5 tester run of the frozen
  signal-colour EA (`SignalMode = 3`, flatten and windows off) is reproduced by the
  simulator (held, raw levels, MT5 fills): 165 of 166 trades exact (entry and exit minute,
  profit to the cent). The first MT5 trade opens on the tester's start tick (Tuesday
  2012-05-08); the simulator, which starts in 2010, opened the same trade at that week's
  Monday open, with the same -$255.50. MT5 fills a market buy one tick (0.25) above the
  open; the controls use that.
- After adding the controls, the simulator still reproduces the primary RTL ledger exactly.
- Every random-timing shift total is recomputed two more ways (FFT circular correlation
  and direct indexing). 12 unit tests pass, including both market-entry controls.

Study: `python/analyze_rtl_weekly_control.py` (about 90 s; uses the weekly-flatten minute
cache). MT5 job: `python/prepare_rtl_weekly_control.py`, then
`python/run_mt5_job.py Reports/rtl_weekly_control_20261027 RTL_weekly_control`. Ledgers,
`control_summary.csv`, `control_gains.csv`, `control_yearly.csv`, `control_results.json`
and the MT5 run are in `Reports/rtl_weekly_control_20261027/`.
