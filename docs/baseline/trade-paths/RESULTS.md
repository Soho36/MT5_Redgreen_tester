# Baseline trade paths: what price does between entry and exit

2026-10-10 · Descriptive, no rule tested, no gate · Runs: `Reports/trade_paths_20261010/` ·
Analysis: `python/analyze_trade_paths.py` · [Baseline studies](../README.md)

## Summary

The pure baseline (no break-even stop, nothing changed), followed quote by quote from entry to exit.
2016–26, 14,968 trades, R before costs. Out of every 100 trades:

- **50 never touch +1R.** 44 are stopped. 6 are still open at the session end and are closed there, 3.5 with
  a small profit and 2.7 with a small loss.
- **50 touch +1R.**
  - 33 never come back to the entry price. All of them win: 23.5 exit at the close of the bar that touched
    +1R, 9 at a later bar close.
  - 16 come back to the entry price. 10 of those go on to the stop, 6 recover and exit with a profit.
- **Losers often looked fine first.** Of the stopped trades, 45% had been above +0.5R and 18% had touched +1R.
- **Winners need room.** 60% of the winners were below −0.25R at some point, 35% below −0.5R, and 15% came
  within a quarter of the candle from the stop.
- **No shortcut on the way.** At every level, up or down, holding on was worth slightly more on average than
  getting out there (mostly +0.03 to +0.09R). Back at the entry price, a trade is worth about the same
  whatever it did before. That fits the fixed take-profit, the trailing stop and the break-even stop all failing.

## How to read this

- **R** = the signal candle's range (entry minus stop), measured from the fill price. +1R is the exit
  threshold, −1R is the stop.
- **Quotes** are the tester's prices in the 1-minute OHLC model, four per minute. A level counts as reached
  when a quote is at or beyond it. That is how the tester triggers an order resting at that level.
- **Before costs.** Costs are $1.05 per trade whatever the path, so they don't change any comparison here.
- Tables show 2016–26 pooled. The two periods agree closely; where it matters both are shown.
- This describes what happened. It tests no rule. See [what it does not say](#what-this-does-not-say).

## 1. How trades end

| Ending | Share | Mean R | Total R | Median time in trade |
|---|---:|---:|---:|---:|
| Stopped at the original stop | 53.7% | −1.00 | −8,037 | 47 min |
| Exit after a bar closes at ≥ +1R | 38.6% | +1.59 | +9,199 | 83 min |
| Closed at the session end | 7.7% | +0.14 | +157 | 140 min |
| **All** | 100% | **+0.088** | +1,319 | |

The shares are the same in both periods (stopped 53.5% / 53.8%, bar-close exits 38.4% / 38.7%).

## 2. The path tree

Trades per 100. "Back at entry" means a quote at or below the entry price after the +1R touch.

| Path | 2016–26 | 2016–19 | 2020–26 | Mean R |
|---|---:|---:|---:|---:|
| **Never touches +1R** | **50.2** | 50.5 | 50.1 | −0.87 |
| → stopped | 44.0 | 43.8 | 44.1 | −1.00 |
| → session end, with a profit | 3.5 | 4.1 | 3.2 | +0.35 |
| → session end, with a loss | 2.7 | 2.6 | 2.8 | −0.31 |
| **Touches +1R** | **49.8** | 49.5 | 49.9 | +1.05 |
| → never back at entry | 33.4 | 33.0 | 33.6 | +1.55 |
| → → the touch bar closes ≥ +1R: exit | 23.5 | 23.2 | 23.6 | +1.58 |
| → → a later bar closes ≥ +1R: exit | 9.2 | 9.1 | 9.2 | +1.54 |
| → → session end | 0.7 | 0.7 | 0.8 | +0.72 |
| → back at entry | 16.4 | 16.5 | 16.3 | +0.03 |
| → → stopped | 9.7 | 9.7 | 9.7 | −1.00 |
| → → a bar closes ≥ +1R: exit | 5.9 | 6.1 | 5.9 | +1.70 |
| → → session end | 0.7 | 0.7 | 0.8 | +0.16 |

- **Where the profit in "never touches +1R" comes from:** the session flatten. These trades were still open
  at 23:30 (or at an early close) and were closed at market. Nearly all (903 of 936) exit at 23:30, the rest
  at early-close times. The ones in profit were entered late in the session (17:00 server time or later)
  and average +0.35R.
- A trade that touches +1R and is never back at the entry price always wins.
- Nearly half of the +1R touches (24 of 50) are finished by the close of the same bar.
- The +1R touch comes a median 40 minutes after entry. 27% of touches happen inside the entry's own M30 bar.

## 3. Stopped trades: how far they got first

The highest point each stopped trade reached before it was stopped (8,037 trades).

| Highest point | Share | Running total |
|---|---:|---:|
| Under +0.1R | 15.9% | 15.9% |
| +0.1R to +0.25R | 17.0% | 32.9% |
| +0.25R to +0.5R | 22.0% | 54.9% |
| +0.5R to +0.75R | 16.2% | 71.0% |
| +0.75R to +1R | 10.9% | 81.9% |
| +1R to +1.5R | 12.8% | 94.7% |
| +1.5R to +2R | 3.6% | 98.4% |
| +2R or more | 1.7% | 100% |

- A third of the losers never got a quarter of the candle into profit. 22% are stopped inside the entry's
  own M30 bar.
- But 45% had been above +0.5R, and 18% had touched +1R without a bar closing there.

## 4. Winning exits: how deep they went, and what they made

The lowest point of each trade that exited after a bar close at ≥ +1R (5,774 trades).

| Lowest point | Share | Running total | Mean final R |
|---|---:|---:|---:|
| Never below the entry price | 12.4% | 12.4% | +1.83 |
| Down to −0.25R | 27.4% | 39.8% | +1.51 |
| −0.25R to −0.5R | 25.0% | 64.8% | +1.54 |
| −0.5R to −0.75R | 20.0% | 84.8% | +1.56 |
| −0.75R to the stop | 15.2% | 100% | +1.68 |

How deep a winner went says nothing about how much it then made.

| Final result | Share of winners | Share of all winnings |
|---|---:|---:|
| Under +1R (next open below the close) | 2.2% | 1.3% |
| +1R to +1.25R | 38.5% | 26.9% |
| +1.25R to +1.5R | 21.4% | 18.2% |
| +1.5R to +2R | 20.7% | 22.1% |
| +2R to +3R | 12.1% | 18.0% |
| +3R to +5R | 4.1% | 9.3% |
| +5R or more | 1.0% | 4.3% |

- Winners average +1.59R (median +1.34R) although the threshold is +1R: the exit waits for the bar close.
  Trades above +2R are 17% of the winners and bring almost a third of the winnings.
- Winners give back 0.34R on average (median 0.23R) between their best point and the exit.

## 5. Level map: once price is at a level, what follows

The first time a trade is quoted at a level. "Holding from there" = mean final R minus the level: what
staying in was worth compared with getting out exactly at that level. ± is a rough 95% range.

| Level | Trades that get there | Then stopped | Then end in profit | Mean final R | Holding from there | 2016–19 | 2020–26 |
|---|---:|---:|---:|---:|---:|---:|---:|
| −0.75R | 61% | 88% | 11% | −0.72 | +0.03 ± 0.02 | +0.04 | +0.03 |
| −0.5R | 71% | 76% | 22% | −0.45 | +0.05 ± 0.02 | +0.07 | +0.04 |
| −0.25R | 83% | 65% | 32% | −0.20 | +0.05 ± 0.02 | +0.07 | +0.04 |
| Entry (all trades) | 100% | 54% | 43% | +0.09 | +0.09 ± 0.02 | +0.09 | +0.08 |
| +0.25R | 81% | 44% | 53% | +0.33 | +0.08 ± 0.02 | +0.09 | +0.07 |
| +0.5R | 68% | 36% | 62% | +0.57 | +0.07 ± 0.03 | +0.08 | +0.07 |
| +0.75R | 57% | 27% | 72% | +0.82 | +0.07 ± 0.03 | +0.09 | +0.06 |
| +1R | 50% | 20% | 80% | +1.05 | +0.05 ± 0.03 | +0.06 | +0.05 |
| +1.5R | 27% | 10% | 90% | +1.55 | +0.05 ± 0.04 | +0.07 | +0.04 |
| +2R | 13% | 7% | 93% | +2.11 | +0.11 ± 0.06 | +0.06 | +0.15 |
| +3R | 4% | 4% | 96% | +3.20 | +0.20 ± 0.14 | +0.11 | +0.27 |

- **Most trades go against you first.** 71% are at −0.5R at some point and 61% at −0.75R, yet only 54% stop.
- **A deep trade is usually lost, but not worth cutting.** At −0.5R, 76% go on to the stop. The other 24%
  recover enough that the average final result (−0.45R) is still slightly better than taking −0.5R.
- **Holding is positive at every level, in both periods.** The numbers are small (mostly +0.03 to +0.09R)
  and close to the +0.09R a new trade is worth. No level stands out as the place to cut or to take profit.
- The +1R row is the fixed take-profit: touching +1R is worth +1.05R on average if held, against +1.00R if
  taken there.

## 6. Back at the entry price: does it matter where the trade has been?

Trades that first went to a level and were later quoted back at the entry price. Mean final R is what
holding from the entry price was then worth.

| First went… | Trades | Share of those that got there | Then stopped | Then profit | Mean final R | 2016–19 | 2020–26 |
|---|---:|---:|---:|---:|---:|---:|---:|
| up to +0.25R | 9,797 | 81% | 55% | 42% | +0.05 ± 0.03 | +0.07 | +0.03 |
| up to +0.5R | 6,484 | 64% | 56% | 41% | +0.04 ± 0.03 | +0.08 | +0.02 |
| up to +0.75R | 4,049 | 47% | 57% | 40% | +0.03 ± 0.04 | +0.05 | +0.02 |
| up to +1R | 2,452 | 33% | 59% | 39% | +0.03 ± 0.06 | +0.02 | +0.04 |
| up to +1.5R | 652 | 16% | 65% | 35% | −0.04 ± 0.11 | −0.19 | +0.04 |
| up to +2R | 193 | 10% | 69% | 31% | −0.07 ± 0.21 | −0.34 | +0.11 |
| down to −0.25R | 9,268 | 75% | 54% | 43% | +0.06 ± 0.03 | +0.08 | +0.05 |
| down to −0.5R | 5,425 | 51% | 54% | 42% | +0.07 ± 0.04 | +0.09 | +0.05 |
| down to −0.75R | 2,358 | 26% | 55% | 41% | +0.07 ± 0.06 | +0.10 | +0.06 |

- Back at the entry price, a trade looks like a new one: 54–59% then stop, about 40% then profit, worth
  about +0.03 to +0.07R. A new trade: 54% stop, 43% profit, +0.09R. Where it has been makes little difference.
- The "+1R" row is the break-even stop's group ([study](../breakeven-stop/RESULTS.md)).
- The +1.5R and +2R rows are few trades, and they change sign between the periods. That is noise.
- A third of the trades that touch +1R come back to the entry price. Even after +2R, one in ten does.

## 7. The first move

Which side is reached first.

| First move | Share of trades | Then stopped | Then profit | Mean final R | Holding from there |
|---|---:|---:|---:|---:|---:|
| +0.25R before −0.25R | 52% | 45% | 53% | +0.33 | +0.08 ± 0.03 |
| −0.25R before +0.25R | 47% | 64% | 33% | −0.18 | +0.07 ± 0.03 |
| +0.5R before −0.5R | 52% | 36% | 62% | +0.57 | +0.07 ± 0.03 |
| −0.5R before +0.5R | 47% | 75% | 22% | −0.44 | +0.06 ± 0.03 |
| +0.75R before −0.75R | 51% | 27% | 72% | +0.82 | +0.07 ± 0.03 |
| −0.75R before +0.75R | 46% | 87% | 11% | −0.72 | +0.03 ± 0.02 |

- The first move is close to a coin flip, tilted a little upward (52 against 47).
- It tells a lot about how the trade will end. It tells little about what is left to gain from that
  point: holding is worth a similar small amount after a good start as after a bad one.

## What this says

- The edge is small and spread along the whole path. It is not concentrated at one point where a rule could
  collect it early or protect it.
- Wherever the trade is, and however it got there, what is left is a small positive expectation. That is
  consistent with all the rejected exit changes: [fixed take-profit](../exit-threshold/RESULTS.md),
  [trailing stop](../trailing-stop/RESULTS.md), [break-even stop](../breakeven-stop/RESULTS.md).
- The profit comes from letting winners run to the bar close (mean +1.59R, a fifth of winners above +2R)
  against stops that cost exactly 1R.

## What this does not say

- It is a description of 2016–26, the same data as every other study here. A rule built from the
  best-looking cell of these tables would be fitted to this sample and would need new data (the MNQ forward
  test) before it means anything.
- "Holding from there" compares with an exit at exactly the level, without slippage, and without the new
  trades an earlier exit would allow. The break-even study showed those side effects are real.
- Quotes are the tester's four prices per minute (the minute's open, high, low and close), not real ticks.
  A level touched in reality is still touched here. Only the order of the high and the low inside one
  minute is assumed.
- The ± ranges treat trades as independent. They are a rough guide, not a test.

## Verification

- The run's ledger is byte-identical to the saved baseline (23,427 trades). The tick log is passive.
- One path per ledger trade, in order (8.4 million quotes). Fill minus stop equals the logged candle range
  on every trade. The first quote is the entry tick. Every non-stop exit is the last quote. No exit is
  beyond the stop price.
- Path highs and lows reproduce the ledger's MFE and MAE on all 23,427 trades.
- Against the separate break-even run: the same +1R touches, and "touched +1R, later back at entry" is
  exactly the 3,873 trades that run cut (plus one trade that ended at the entry price on its own exit).

```powershell
.\venv\Scripts\python.exe python\prepare_trade_paths.py
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\trade_paths_20261010 RTL_paths
.\venv\Scripts\python.exe python\analyze_trade_paths.py
```
