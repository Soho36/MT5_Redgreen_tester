# Break-even stop after +1R

2026-10-10 · Exploratory (user request) · [Protocol](PROTOCOL.md), fixed before the runs ·
Runs: `Reports/breakeven_20261010/` · Analysis: `python/analyze_breakeven_study.py` · [Baseline studies](../README.md)

## Summary

- **Question:** baseline unchanged, but once price reaches +1R the stop moves to the entry price. The exit is
  still the bar close at ≥ 1R. Does it help?
- **No. Rejected by the pre-set rule.** It is worse than the baseline on net $ and on average net R in both
  deciding periods: net $6,485 → $5,404 (2016–19) and $37,981 → $33,727 (2020–26).
- **The loss is small against noise.** The week-resampled intervals for the difference include zero in both
  periods. The fair reading is "no benefit", not "clearly harmful". Still, it is better in only 3 of 11 years
  on net $ and 2 of 11 on average R.
- **It lowers drawdown a little** (−5% / −11%), but gives up about as much profit or more (−17% / −11%). That
  is no better than trading a smaller size.
- **Why it doesn't help:** about half of all trades touch +1R, and a third of those fall back to the entry
  before any bar closes at ≥ 1R. Left alone (the baseline), 60% of them end as full losses and 39% recover to
  a profit of about +1.6R on average. Together that is worth about zero (+0.01 / +0.04 R). The break-even
  stop replaces a hold that is worth about zero with an exit at exactly zero. There is nothing to gain.
- **The tester is the best case for this rule.** Every break-even stop filled exactly at the entry price.
  A live stop would slip, so the real result would be slightly worse.
- **The bar-close exit and the original stop stay.** No other trigger levels will be tried in response to
  this result (protocol).

## Results

After $1.05 costs. DD = largest drop of the closed-trade balance inside the period.

| Period | Run | Trades | Win % | Net $ | Net PF | Net DD $ | Avg R before costs | Avg net R |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2016–19 | Baseline | 5,697 | 43.6 | **6,485** | **1.106** | 1,435 | **+0.093** | **−0.004** |
| 2016–19 | Break-even | 6,023 | 36.9 | 5,404 | 1.096 | **1,358** | +0.089 | −0.009 |
| 2020–26 | Baseline | 9,271 | 43.1 | **37,981** | **1.107** | 4,847 | **+0.085** | **+0.060** |
| 2020–26 | Break-even | 9,742 | 36.7 | 33,727 | 1.106 | **4,294** | +0.078 | +0.053 |
| 2010–15 (context) | Baseline | 8,459 | 40.2 | −7,027 | 0.860 | 8,190 | +0.005 | −0.185 |
| 2010–15 (context) | Break-even | 8,898 | 33.2 | −8,510 | 0.818 | 9,079 | −0.006 | −0.196 |

The win rate falls because 16–17% of all trades now end at the entry price. Each of those still pays the
$1.05 cost.

Break-even minus baseline, with 95% intervals from resampling weeks:

| Period | Net $ | Avg net R |
|---|---|---|
| 2016–19 | −1,081 [−2,754, +460] | −0.005 [−0.021, +0.010] |
| 2020–26 | −4,254 [−13,899, +3,954] | −0.007 [−0.018, +0.005] |
| 2010–15 (context) | −1,483 [−2,963, −287] | −0.011 [−0.022, +0.001] |

**Decision rule** (beat the baseline on net $ and average net R in both 2016–19 and 2020–26): fails all
four comparisons. **Rejected.**

## What happens to the trades

The same trade has the same entry time in both runs, so the two ledgers can be compared trade by trade.

| | 2016–19 | 2020–26 |
|---|---:|---:|
| Trades in both runs | 5,631 | 9,203 |
| …that touch +1R (stop moved to entry) | 2,793 (49.6%) | 4,595 (49.9%) |
| …and then exit at the entry price ("cut") | 927 (33.2% of those) | 1,504 (32.7%) |
| Baseline result of the cut trades: full loss | 548 (59%) | 895 (60%) |
| Baseline result of the cut trades: profit | 364 (39%), avg +1.55R | 581 (39%), avg +1.65R |
| Baseline result of the cut trades: mean R before costs | +0.013 | +0.038 |
| Baseline result of the cut trades: total $ | +710 | +5,572 |
| New trades (taken because the position was free earlier) | 392 | 539 |
| New trades: net $ / mean net R | −596 / −0.085 | +2,419 / +0.056 |
| Baseline trades no longer taken | 66 | 68 |
| Baseline trades no longer taken: net $ | −225 | +1,101 |

Every other shared trade is identical in both runs. The total change adds up exactly from these three parts:

- 2016–19: −710 (cut trades) − 596 (new trades) + 225 (trades no longer taken) = **−1,081**
- 2020–26: −5,572 (cut trades) + 2,419 (new trades) − 1,101 (trades no longer taken) = **−4,254**

Reading it:

- The cut trades are the whole point of the rule, and they are where it loses. A trade that touched +1R and
  came back to the entry is not a bad trade in the baseline. Six in ten go on to the full stop, but the four
  in ten that recover earn about 1.6R each, slightly more than the stops lose.
- The new trades are ordinary RTL trades, no better than the average one. They add costs in 2016–19 and
  some profit in 2020–26, not enough to pay for the cut trades.

## More on the cut trades

Descriptive, added on 2026-10-10 after the result (user question). Baseline results, R before costs,
2016–26 pooled. The two periods agree; per-period figures are in the script output.

Every baseline trade is one of three kinds:

| Kind | Share of trades | Full stop | Profit | Mean R |
|---|---:|---:|---:|---:|
| Never touches +1R | 50% | 87.5% | 7% | −0.87 |
| Touches +1R and never comes back to the entry | 33% | 0% | 100% | +1.55 |
| Touches +1R, then comes back to the entry (cut) | 16% | 59% | 39% | +0.03 |

The break-even stop changes nothing in the first two kinds. Its whole effect is on the third: one trade in six.
What the baseline does with those 2,431 trades:

| Baseline result | Trades | Share | Total R |
|---|---:|---:|---:|
| Full stop (−1R) | 1,443 | 59% | −1,443 |
| Between −1R and 0 | 43 | 2% | −12 |
| Between 0 and +1R | 96 | 4% | +58 |
| +1R to +1.5R | 470 | 19% | +574 |
| +1.5R to +2R | 197 | 8% | +340 |
| +2R to +3R | 118 | 5% | +281 |
| Above +3R | 64 | 3% | +272 |
| **All** | 2,431 | | **+70** |

- **A fair bet.** The stops lose 1,443R and the recoveries earn 1,525R: +0.03R per trade. At the winners'
  average of +1.6R, about 38.3% of these trades must recover for the hold to be worth zero. 38.9% do
  (2016–19: 39.3% against 39.2% needed; 2020–26: 38.6% against 37.7%).
- **The winners' average rests on a few large ones.** 182 trades (7.5%) end above +2R and bring more than a
  third of the group's winnings. The break-even stop removes those too. Once a trade recovers, it wins as
  much as a trade that never came back (+1.6R against +1.55R).
- **Recoveries don't bounce off the entry price.** 56% of the trades that recover first make a new low
  after coming back, typically around −0.6R.
- **Little time is freed.** Median times: 31 minutes from entry to the +1R touch, 20 more to come back to
  the entry, and the baseline then holds on for 38 minutes (23 to the stop, 59 to a winning exit). That is
  why only 931 new trades appear for 2,431 cut ones, each paying a new $1.05.
- **Not predictable from the high.** How far the trade ran above +1R before coming back does not sort the
  two outcomes the same way in both periods.

Reading (interpretation): once price is back at the entry, the push that triggered the buy stop is used up.
What is left is a plain long with a 1R stop. The [no-pattern control](../signal-colour/RESULTS.md) (market
buy, same stop and exit) was also worth about zero before costs (+0.009 / +0.007 R).

## By year

| Year | Net $ baseline | Net $ break-even | Change | DD baseline | DD break-even |
|---|---:|---:|---:|---:|---:|
| 2016 | −472 | −846 | −374 | 1,176 | 1,303 |
| 2017 | 967 | 1,076 | **+109** | 370 | **314** |
| 2018 | 1,944 | 1,562 | −382 | 1,435 | **1,334** |
| 2019 | 4,046 | 3,612 | −433 | 1,163 | 1,220 |
| 2020 | 4,558 | 5,807 | **+1,249** | 2,967 | **2,237** |
| 2021 | 1,018 | −478 | −1,496 | 3,525 | **3,270** |
| 2022 | 4,429 | 4,405 | −25 | 3,601 | **2,688** |
| 2023 | 5,113 | 6,074 | **+961** | 2,160 | **1,829** |
| 2024 | 9,280 | 8,576 | −704 | 2,153 | 2,519 |
| 2025 | 4,684 | 2,081 | −2,603 | 3,979 | 4,294 |
| 2026 (to July) | 8,899 | 7,263 | −1,636 | 4,847 | **3,978** |

Net $ better in 3 of 11 years, average net R better in 2 of 11, drawdown lower in 7 of 11.

## How this fits earlier results

- The [1.0R trailing stop](../trailing-stop/RESULTS.md) also starts at the entry price when +1R is reached
  and was rejected. A fixed break-even stop is the mildest form of that idea, and it fails the same way.
- None of the attempts to protect or bank the first +1R (fixed take-profit, resting limit, trailing stop,
  break-even stop) has beaten simply waiting for the bar close in both periods. The trades that wobble
  after touching +1R are part of what pays.
- This was one planned run on data that has all been seen before. A negative result on a single planned
  try is solid. Trying 0.5R, 1.5R or "entry + a few ticks" next and keeping the best one would not be:
  with enough variants one of them looks good by chance.

## Verification

- Compiled with 0 errors, 0 warnings. With the input off, the control ledger is **byte-identical** to the
  saved baseline (`Reports/instrument_baseline_20261008`, 23,427 trades).
- Both ledgers match MT5's own order/deal report: 0 missing trades, totals equal.
- 12,074 stops moved to entry, 0 failed modifications. The stop-move flag agrees with the separately logged
  tick-level MFE on all 24,663 trades (moved ⇔ MFE ≥ 1R).
- All 3,873 shared trades that differ from the control are break-even exits at exactly $0. All 4,115
  break-even exits (including those in new trades) filled exactly at the entry price.
- Intrabar order: 51 of 4,115 break-even exits (1.2%) happen in the same minute as the stop move, so the
  tester's assumed order of prices inside a minute matters little here. 74 exits happen on a price jump
  that also passes the original stop; the tester fills them at the entry price, which favours the rule.

```powershell
.\venv\Scripts\python.exe python\prepare_breakeven_study.py
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\breakeven_20261010 RTL_breakeven
.\venv\Scripts\python.exe python\analyze_breakeven_study.py
```
