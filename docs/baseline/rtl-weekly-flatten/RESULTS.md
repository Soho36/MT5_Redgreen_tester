# RTL on weekly candles, flattened every session

2026-10-27, exploratory. [Protocol](PROTOCOL.md) fixed before any weekly result.

**Finding:** flattening at every session close and reopening at the next open changes
weekly RTL very little. On the same roll-adjusted levels, 2016-19 net is $4,563
flattened versus $5,043 held; 2020-26 is $27,199 versus $23,826, and that recent gain
comes from one lucky trade. So an MT5 W1 run that holds overnight is a fair guide to
the flattened version. Per trade, weekly RTL looks far better than M30 (+0.23 / +0.38 R
versus -0.01 / +0.05 R) and barely notices costs. But it trades about 6 times a year,
risks a median $1,528 per MNQ contract in 2020-26 (up to about $3,100), and earned less
than M30 in 2020-26 with a larger drawdown. **The [controls](CONTROL_RESULTS.md) find no
edge beyond being long NQ:** a plain weekly long earns as much per trade, and RTL's timing
does not beat random timing by the bar set in advance.

## Setup

- Weekly bar = Monday-Friday sessions. A red week arms a buy stop at its high for the
  next week, stop at its low; exit after a week closes at or above entry + 1R. Same rules
  as the M30 EA, on W1 bars (no red-run cap, no filters).
- **Flatten:** positions are live from the session open (01:00 on the Chicago + 8 h
  clock) to 23:30 or the early-close time. At the cutoff the position is closed; at the
  next open it is bought back with the same stop and target. A pending buy stop is
  suspended while flat, and fills at the next open if price is already above it.
- Profit in raw prices; signal levels roll-adjusted (raw levels as a sensitivity).
  $1.05 per round turn, and every daily piece is a round turn. One MNQ, $2 per point.
- Built in a Python 1-minute simulator that reproduces MT5 exactly (see Verification).
- Eras by first-fill date; 2020-26 runs to 2026-09-30. Intervals: trade bootstrap of mean
  net R. DD: daily equity at one contract (flat every night, so closed = marked; held
  trades are marked at each session close).

## 2016-19

| Variant | Trades | Sessions per trade | Win % | Net R per trade (95% interval) | Net $ | Net PF | Max DD $ | Worst day $ | Median risk $ |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| **W1 flatten** | 25 | 24.2 | 56.0 | +0.234 (-0.201 to +0.666) | 4,563 | 2.10 | 2,461 | -516 | 357 |
| W1 flatten raw | 26 | 22.6 | 57.7 | +0.226 (-0.186 to +0.624) | 4,206 | 2.01 | 2,491 | -516 | 356 |
| W1 hold | 25 | 24.8 | 56.0 | +0.271 (-0.191 to +0.725) | 5,043 | 2.20 | 2,436 | -545 | 357 |
| W1 hold MT5-style | 26 | 23.2 | 57.7 | +0.290 (-0.132 to +0.711) | 5,106 | 2.21 | 2,435 | -546 | 356 |
| M30 baseline | 6,167 | 1.0 | 43.2 | -0.014 (-0.048 to +0.019) | 4,417 | 1.06 | 2,143 | -454 | 15 |

## 2020-26 (through 2026-09-30)

| Variant | Trades | Sessions per trade | Win % | Net R per trade (95% interval) | Net $ | Net PF | Max DD $ | Worst day $ | Median risk $ |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| **W1 flatten** | 44 | 21.7 | 61.4 | +0.377 (+0.043 to +0.707) | 27,199 | 2.06 | 7,637 | -3,098 | 1,528 |
| W1 flatten raw | 44 | 21.9 | 63.6 | +0.366 (+0.022 to +0.706) | 24,121 | 1.86 | 6,342 | -3,098 | 1,526 |
| W1 hold | 45 | 21.6 | 60.0 | +0.356 (+0.024 to +0.677) | 23,826 | 1.79 | 9,626 | -3,141 | 1,538 |
| W1 hold MT5-style | 45 | 21.9 | 62.2 | +0.406 (+0.075 to +0.723) | 25,985 | 1.91 | 7,041 | -3,140 | 1,538 |
| M30 baseline | 10,501 | 1.0 | 42.7 | +0.048 (+0.023 to +0.072) | 38,400 | 1.09 | 5,781 | -2,218 | 58 |

W1 hold = held through nights and weekends on adjusted levels, +$1.05 per roll crossed.
W1 hold MT5-style = what the MT5 tester shows on W1: raw levels, stops and entries
always filled at their level, even across a weekend gap. 2010-15 (reference, older
session hours): W1 flatten +$892 (+0.09 R, 34 trades); M30 -$7,496.

## What flattening changes

- **The same trades.** 103 of 104 signals trade in both versions, and 101 end the same
  way. Two breakouts happened while flat (both before 2016) and filled at the next open;
  no order was ever rejected.
- **Small cost per trade, mostly commission.** A trade is held about 22 sessions, so it
  pays about 22 round turns. Average change per shared trade: -0.08 / -0.04 / +0.04 R
  (2010-15 / 2016-19 / 2020-26). Commission: -0.10 / -0.05 / -0.01 R (it shrinks as the
  weekly stop grows in dollars). Missed overnight moves: +0.03 / +0.01 / +0.06 R. Each
  trade moves by a median 0.09-0.18 R either way.
- **The recent gain is one trade.** Held, the August 2024 trade was stopped at 23:32 on
  6 September 2024, two minutes after the flatten time. Flattened, it was out at 23:30,
  never hit its stop in live hours, and reached its target: +$3,208 instead of -$2,664.
  Leaving out the two trades that ended differently, flattening cost -0.01 R per trade
  in 2020-26 too.
- **One gap below the stop while flat** (March 2025): the trade ended at the next open
  without a further loss piece, -$1,814 instead of -$2,105 held.

## Weekly versus M30

- **Per contract:** 2016-19 about the same ($4,563 vs $4,417); 2020-26 less ($27,199 vs
  $38,400) with a larger drawdown ($7,637 vs $5,781) and a worse single day (-$3,098 vs
  -$2,218). Net profit to max DD: 1.9 / 3.6 weekly, 2.1 / 6.6 M30.
- **Per trade:** much better in R, and robust to costs. With +$2 per round turn the
  weekly version keeps $3,351 / $25,293; M30 falls to -$7,917 / +$17,398.
- **Few trades:** 25 and 44. The 2016-19 interval includes zero; in 2020-26 its lower end
  is +0.04 R. The five best trades are 67% of 2020-26 profit. Positive in 10 of 11 years
  2016-2026 (2018 -$886); M30 also 10 of 11.
- **Size:** a weekly stop is a whole week's range. Median risk per MNQ is $357 (2016-19)
  and $1,528 (2020-26), up to about $3,100 in 2026; one MNQ is the smallest size.
- **Time in the market:** 59% / 55% of sessions. Simply buying every session open and
  selling at the flatten earned $8,031 / $36,615 with DD $3,198 / $12,428 (same costs).
  Weekly RTL took 57% / 74% of that profit with 77% / 61% of the drawdown. That is
  about what its time in the market alone would give. The follow-up [controls](CONTROL_RESULTS.md)
  confirm it: no visible gain from the buy stop or from RTL's timing on weekly bars.
- **Together with M30** (one contract each, by exit day): daily correlation 0.39 / 0.32.
  2020-26 net $65,655, DD $9,430 (profit to DD 7.0 against M30 alone 6.6); 2016-19 $8,679,
  DD $4,067. A slight smoothing, descriptive only.

## Caveats

All periods were seen before; this is a descriptive comparison, not a confirmation. The
weekly sample is small and its profit is concentrated. The roll adjustment matters in
single years (2024: +$5,069 adjusted vs +$1,214 raw levels). Entries and stops fill at
their level inside a session (or at a worse 1-minute open); session-open reopen fills
use the first 1-minute open, with no extra slippage beyond the stress costs. A one-MNQ
weekly stop of $1,500-3,000 matters for any account loss limit.

## Verification and reproduction

- **M30 check:** the simulator in M30 mode, with the EA's own flatten logic, reproduces
  all 25,833 trades of the MT5 M30 RTL ledger: identical order levels, stops, fill and
  exit prices; exit minute identical in 25,831 (two same-minute timing differences).
  18 extra simulated trades fall in the first three days, before MT5 starts trading.
- **W1 check:** a fresh MT5 tester run on W1 (frozen 2026-10-15 RTL source, flatten and
  trade windows off) reproduced trade by trade by `W1 hold MT5-style`: all 92 trades,
  entry and exit minutes and profit to the cent. MT5 starts trading only in June 2012
  (it needs about 100 weekly bars of history); 12 earlier simulated trades are extra.
- **Independent check:** `verify_rtl_weekly_flatten.py` rebuilds weekly bars, roll
  factors and cutoffs separately and steps session by session; it reproduces all 103
  primary trades and 2,291 daily pieces exactly. 9 unit tests of the flatten/reopen
  rules pass.

Simulator: `python/rtl_weekly_engine.py`. Study: `python/analyze_rtl_weekly_flatten.py`
(about 90 s). MT5 job: `python/prepare_rtl_weekly_flatten.py`, then
`python/run_mt5_job.py Reports/rtl_weekly_flatten_20261027 RTL_weekly_hold`. Trades,
daily pieces, summary, yearly, pairing, `audit.json`, `extras.json` and the MT5 run are in
`Reports/rtl_weekly_flatten_20261027/`.
