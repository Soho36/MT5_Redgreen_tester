# Review of the whipsaw follow-ups: forecast test and MT5 overlays

Written 2026-11-12 at the user's request, after both follow-ups were committed
(5d2062f, 3a030b0). It checks [the MT5 overlays](RESULTS.md) and
[the forecast test](../whipsaw-followup/RESULTS.md) and adds the attribution
check they left open. Same reused history, so everything here is descriptive.
Every check was written down in `python/review_whipsaw_native.py` before its
result was looked at; all rows are in [review_checks.csv](review_checks.csv).

**In short**

1. **The work holds up.** Every published figure was rebuilt from the raw files
   with separate code and is equal.
2. **Next-session trades do look better, but it is not shown.** 35-40% of
   their dollars is simply more money at risk on a volatile day. The rest
   ("better trades") has an interval from about -$5k to +$15k, rests on five
   sessions, and is much weaker on ES, YM and RTY.
3. **It is not specific to whipsaw days.** The days with the highest plain
   volatility forecast are followed by sessions just as large and just as
   profitable.
4. **No tested way of using it beats trading normally.** An extra contract buys
   profit with at least as much drawdown; 2R, days 2-3 and shorts show nothing.

One MNQ, $1.05 per round trip, 2016 to September 2026, 174 next sessions.

## 1. Do the numbers hold? Yes

- Trades and net dollars of all eight native runs: parsed reports equal the
  EA's own ledgers and the published table.
- The 174 next sessions and 403 sessions of days 1-3 were rebuilt from the
  frozen event study; the selected runs equal the control's trades there.
- Every equity drawdown (controls and all overlays, three periods) was rebuilt
  sample by sample from the raw native equity files: equal to the cent.
- All 18 month-resampling intervals reproduce.
- A full 2R simulation of every session gives the native 2R arm's dollars on
  the next sessions exactly.

## 2. Is there an edge in next-session trades?

| Per trade | RTL next | RTL other | GG next | GG other |
|---|---|---|---|---|
| Trades | 1,037 | 15,631 | 1,043 | 16,526 |
| Planned risk | $91 | $56 | $100 | $59 |
| Gross R (before costs) | +0.122 | +0.072 | +0.110 | +0.066 |
| Costs in R | 0.029 | 0.052 | 0.027 | 0.048 |
| Net R | +0.093 | +0.020 | +0.083 | +0.019 |
| Winning trades | 45.1% | 42.7% | 45.6% | 43.2% |
| Net per session | $47 | $13 | $49 | $13 |

Two different things are mixed in that table.

- **More money at work.** The candles are bigger after a whipsaw day, so one
  contract already risks 1.65 times the usual dollars per trade. Nothing has to
  be done to get this.
- **Better trades.** Against trades of the same year and the same planned risk,
  next-session trades earned +0.07 R more for RTL (95% interval -0.01 to +0.15)
  and +0.05 R for GG (-0.02 to +0.12). Positive, and each interval reaches zero.

In dollars: of RTL's $8,195 on next sessions, $3,171 is what equally risky
trades normally earn and $5,024 is "better trades" (-$5,541 to +$14,846). GG:
$8,450 = $2,901 + $5,548 (-$4,390 to +$16,229).

Why the "better trades" part is not established:

- **Few sessions carry it.** The five best of 174 sessions hold 79% of RTL's
  and 63% of GG's next-session profit. RTL made 57% of it in 2026 alone.
  Positive years: RTL 8 of 11, GG 6 of 11. In 2020 RTL lost $1,661 on next
  sessions while GG made $2,405.
- **Shuffle test.** Give the whipsaw label to other days of the same year and
  size at random: 13% of shuffles earn as much as the real next sessions for
  RTL, 19% for GG. (Random placements that leave the whipsaw days out are
  beaten 97-99% of the time, but that comparison is unfair: the few extreme
  sessions can then never land in a draw.)
- **Other instruments.** The same comparison on the saved RTL and GG runs, with
  each instrument's own whipsaw days: ES +0.03 / +0.01 R, YM -0.03 / +0.01,
  RTY +0.07 / +0.03. Five of six positive, every interval includes zero,
  average +0.02.
- **Noise.** One next session swings by about $380 (standard deviation) around
  a $47 average. A forward log could confirm the market effect in a year or
  two, but a $30 difference per session in strategy results would need decades.

## 3. It is the volatility, not the whipsaw

In each year take as many days as there were whipsaw days, but choose them by
the follow-up's volatility-only forecast (fitted on earlier years):

| 174 days chosen by | Next move | A full range or more | RTL on the sessions after | GG on the sessions after |
|---|---|---|---|---|
| Whipsaw flag | 0.93 | 36% | $8,195 | $8,450 |
| Highest volatility forecast | 0.89 | 35% | $11,872 | $8,074 |

Half of the days are the same (88). The days are ranked inside each finished
year, so this is a description and not a tradable rule. The forecast test's verdict is right:
the flag is a visible sign of a very volatile day and adds nothing that minute
volatility does not already say. That test could not have passed anyway for an
effect of the size the regressions leave (+0.15), which is why both results can
be true together.

## 4. Can it be used?

- **Extra contract on next sessions.** RTL: the same profit from simply trading
  the normal strategy larger would have cost $7,079 of drawdown, the overlay
  cost $7,721. GG: $6,728 against $6,483. One worse, one slightly better. Per
  dollar of drawdown the overlay sits in the middle of other placements (better
  than 48% of shuffles for RTL, 72% for GG). And the largest single-trade risk
  and the worst swing inside one session of the whole period are on next
  sessions for both strategies (for GG the worst session too): a second
  contract doubles them, from about $2,400 to $4,800 inside one session.
- **2R on next sessions.** 2R minus 1R per session: RTL +$13 (-$19 to +$45),
  GG -$3 (-$26 to +$22); on all other sessions about -$1. Nothing to follow up.
- **Days 2 and 3.** Movement fades (0.93, 0.87, 0.81) and direction does not
  carry: day 2 has day 1's direction in 43% of cases, all three agree in 22%;
  for all days the figures are 48% and 25%.
- **Shorts.** Saved RTL-short and GG-short runs: gross R on next sessions 0.00
  and -0.07; no better than their other trades.

## What I would do with it

1. **Trade the session after a whipsaw day as normal.** Do not skip it and do
   not cut size out of frustration: it has been an above-average session
   (58% / 56% of them positive against 54% / 52%).
2. **Treat the flag as a risk warning.** With one contract the dollar swings
   are already about 1.6 times normal: the worst 5% of next sessions lose more
   than $560-620, against $330-360 on other days.
3. **No extra contract, no 2R, no three-day rule** on this evidence. If more
   profit is wanted and more risk can be carried, more size on every day does
   the same job without a rule.
4. **If more research is wanted, ask the general question once:** does the
   quality of RTL and GG trades per unit of risk rise with expected volatility?
   That uses all 2,774 sessions instead of 174, can be split into train and
   test years, and can be repeated on ES, YM and RTY.

## Notes on the two write-ups

- The interval table in RESULTS.md answers "did these sessions make money",
  not "did they make more than other sessions". Its one positive pooled row
  (RTL days 1-3) should not be read as support for a three-day rule.
- "RTL 2R is worth further checking": with the all-session comparison above I
  would close it.
- The forecast test is sound (training strictly earlier, fixed penalty).

Code: `python/review_whipsaw_native.py`, tests `python/test_review_whipsaw_native.py`.
Nothing in the two studies was changed. No settings changed.
