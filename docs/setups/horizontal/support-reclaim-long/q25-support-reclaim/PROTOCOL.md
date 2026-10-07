# Q25: buy the reclaim of a broken swing-low level

*Numbered Q24 until 2026-10-07; renamed Q25 in the docs because the trade-streaks study had already taken Q24. Code, run folders and commit messages keep "Q24".*

**Frozen 2026-10-07** with the user's design (2026-10-07), before any Q25
count or outcome was computed. All of 2010-2026 and the Q6-Q23 results have
been seen, so this is exploratory.

**The question (the user's proposal).** Use the same swing-low levels as Q11
and Q23, but go **long** on a failed breakdown. A red M30 candle opens at or
above an intact level and closes below it. A **buy stop at the level price**
waits for price to come back; the stop loss is that candle's low. Does this
long make money, and is entering at the level better than the standard RTL
entry (the candle's high) on the same candles?

**Prior evidence, stated up front:**

- RTL buys at the **high** of support-breaking red candles were inconsistent:
  Q8 unrecovered session-low breaches PF 1.260 / 0.955; Q11 slice-throughs
  1.071 / 0.941; Q22 rising-line breakdown candles 1.010 / 0.831.
- [Q9](../q09-reclaim-speed/RESULTS.md) could not rule out a short-lived bounce right
  after a reclaim, and said that would need a causal entry. A buy stop at the
  level is such an entry: it fills only once price is back at the level.
- [Q23](../../support-breakdown-short/q23-support-breakdown/RESULTS.md): shorting the break of the same levels
  was near break-even (PF 0.992 / 1.038). Its losing example is a reclaim.
- [Q20](../../../trendlines/uptrend-bounce-long/q20-trendline-limit/RESULTS.md): limit orders resting at a
  level fill disproportionately on bars that keep going through. A buy stop
  triggers when the ask reaches the level, so it needs no trade-through.

## Levels: the frozen Q11 map, evaluated at the breakdown candle

Nothing is re-parameterized ([`level_visit.py`](../../../../../python/level_visit.py)).
At the open of bar s, from bars before s only:

- **A(s)** = mean of the 14 true ranges before s, same contract; **D = 0.5 x A**.
- **Window:** the session of s plus the 5 previous sessions, one contract.
- **Swing lows:** N = 5, known once pivot + 5 <= s - 1.
- **Levels:** known swing lows merged greedily from the lowest within D;
  **L = the lowest member's low**. A level is identified by that member (its
  defining pivot).
- **Intact:** no close more than D below L after the level's latest member
  (Q11's broken rule); **departed:** a close at least A above L after it.

## The signal

Bar s is a **breakdown** of a level if the level is intact and departed,
**open(s) >= L** and **close(s) < L** (the user's "any close below"; the bar is
red by construction). If s breaks several levels, the **lowest** broken level
is used (the first one price has to reclaim); ties go to the later defining
pivot.

**One signal per level.** A breakdown spends its level whether or not an
order follows. Spending is recorded on every bar, in order, eligible or not
(the Q21 lesson: a level must not come back because A was re-measured).

## The order (fixed)

At the open of **bar t = s + 1**, if the strategy is flat, t opens in an
enabled window (01:00-23:30) before the flatten or early close, and s and t
are in the same contract:

- **R = L - low(s)**. If R < **0.25 x A(s)**, no order (skip "min_risk"; the
  number of skips is reported).
- If the ask at t's open is already at or above L, no order (gap back above
  the level; no chasing).
- Otherwise a **buy stop at L** with **stop loss = low(s)** attached. Prices
  are bar prices, already on the tick.

**Order life: 3 bars** (t, t+1, t+2). It is cancelled at the first of:

- the open of t+3 without a fill;
- **price trades at or below low(s)** before a fill (bid <= low(s) on any
  tick: the setup is broken);
- the window exit, the flatten or the early close;
- a new signal, which replaces it (as RTL replaces its order).

**After a fill:** the baseline exit, a market exit after the first M30 bar
that closes >= entry + 1R, with RiskReward = 1.0 in every regime (the Q20
audit's BullRR/BearRR bug excluded); session flatten and fallback on; one
contract; $1.05 per round trip modelled in Python; net R = net / (2 x R).
Symbol `MNQcontDTBNT20102026_2`, M30, one-minute OHLC, 2010-06-07 to
2026-07-14 in one run.

**Periods:** decision 2016-01-01 to 2020-01-01 and 2020-01-02 to 2026-07-14;
2010-2015 reported separately.

## Controls

- **C1 (decision): the RTL entry on the same candles.** On every bar t where
  the primary places an order: buy stop at **high(s)** instead of L, same stop
  loss low(s), same 3-bar life, same cancellation, same exit. It isolates the
  entry price: is buying the reclaim of the level better than buying above
  the breakdown candle?
- **RTL baseline** (PF 1.106 / 1.107, mean R -0.004 / +0.060): context only.

## Sensitivity (fixed now)

**S1, deeper break:** close(s) < L - D. Everything else is unchanged, with its
own C1.

## Reading rule (fixed now)

The primary **passes** if, in both decision periods:

- >= 200 trades;
- PF > 1 and mean net R > 0;
- mean net R > C1's;
- mean R beats C1 in >= 7 of 11 years (years with >= 10 trades in each);
- S1 also has PF > 1 and mean net R > its C1's.

**Also reported:** min-risk skips and gap skips per period; 2010-2015; the
week-block bootstrap of primary minus C1 (5,000 resamples, seed 20261007);
fills by bar of the order life (1st / 2nd / 3rd); cancellations by reason.

**What a pass means:** buying the reclaim at the level is a better long than
buying the breakdown candle's high, under one-minute OHLC. It adopts nothing;
combination with RTL or Q18 and sizing need their own protocol.

## Reported per run, period and year

Trades, net $, PF, mean / median net R, win %, exit mix, stops in the fill bar,
OHLC-ambiguous fills (the fill minute also reached the stop), closed drawdown,
longest losing run, average R in points and cost as a share of R.

**Descriptive labels (primary, never candidates):** close depth below L in A;
R / A; bar of the order life that filled; level age and merged / single;
time-of-day segment; daily regime (Q10).

## Verification

- **Unit tests** for the signal: fresh break (open >= L, close < L); intact
  and departed; lowest level of several; one signal per level, spending on
  every bar; min risk; gap above; window / roll; S1.
- **Classify-only EA run** (no orders) at the primary and S1 thresholds,
  logging every eligible bar t: bar s, status, level, defining pivot, A, entry,
  stop, R and level counts. A Python implementation on the Q11 functions must
  reproduce every bar: 0 mismatches. The logged bars must be exactly the
  eligible set.
- **Trading runs** replayed against that log: every order matches the
  classification; every cancellation follows the four rules (3-bar expiry and
  the low(s) touch checked against one-minute data); every fill is at or above
  L (C1: high(s)) with stop low(s).
- **Execution audit:** one position at a time; nothing held over the flatten;
  no send or cancel errors; MT5 reconciles with the ledger.
- Hashes of the inputs, code and this protocol.

## Planned files and outputs

`python/support_reclaim.py` and `python/test_support_reclaim.py`;
`mt5/experts/support_reclaim.mqh`; `python/prepare_support_reclaim.py`,
`python/verify_support_reclaim.py`. Outputs:
`Reports/levels/support_reclaim_<date>/`. Results doc:
`docs/setups/horizontal/support-reclaim-long/q25-support-reclaim/RESULTS.md`.

## What was seen while drafting

Only the results quoted above and the Q23 example charts. No Q25 count or
outcome was computed.

## Pre-trade verification (done 2026-10-07, no outcomes)

Run folder: `Reports/levels/support_reclaim_20261007/`. Code:
[`support_reclaim.py`](../../../../../python/support_reclaim.py),
[`support_reclaim.mqh`](../../../../../mt5/experts/support_reclaim.mqh),
[`prepare_support_reclaim.py`](../../../../../python/prepare_support_reclaim.py),
[`verify_support_reclaim.py`](../../../../../python/verify_support_reclaim.py); 9 unit tests in
[`test_support_reclaim.py`](../../../../../python/test_support_reclaim.py) (plus Q11's 12).

**Classify-only runs** (ReclaimMode = 1, no order ever sent), primary
(BreakDepthA = 0) and S1 (0.5): compiled 0 errors / 0 warnings, about 40 s
each, full history 2010-06-10 to 2026-07-13.

- **Eligible bars:** 184,888 logged in each run, exactly the expected set: 0
  extra, 0 missing.
- **Python reproduces every bar: 0 mismatches** in both runs, first time. That
  covers status, bar s, colour, contract, level, defining pivot, latest member,
  members, entry, stop, risk, A and level counts (known pivots, levels, live,
  broken). Orders 4,373 / 4,373 (primary) and 2,917 / 2,917 (S1).

**Counts (no P&L, no R).** "Breakdowns" are bars t whose bar s freshly broke a
live, unspent level (orders + min-risk skips + gap skips).

| Period | Run | Breakdowns | Orders | Min-risk skips | Gap skips | Median R (points) | Median R / A | Median close depth / A |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2010-15 | Primary | 1,677 | 1,451 | 117 (7.0%) | 109 | 4.75 | 0.97 | 0.51 |
| 2016-19 | Primary | 1,198 | 1,094 | 76 (6.3%) | 28 | 9.00 | 0.99 | 0.49 |
| 2020-26 | Primary | 2,006 | 1,828 | 150 (7.5%) | 28 | 30.75 | 0.88 | 0.46 |
| 2010-15 | S1 | 1,015 | 1,013 | 0 | 2 | 6.50 | 1.34 | 0.91 |
| 2016-19 | S1 | 730 | 729 | 0 | 1 | 13.00 | 1.46 | 0.93 |
| 2020-26 | S1 | 1,175 | 1,175 | 0 | 0 | 46.25 | 1.32 | 0.90 |

- The minimum risk removes 6-8% of primary breakdowns and none under S1
  (a close more than 0.5 x A below L already makes R > 0.5 x A).
- At the median, the $1.05 round trip is about 0.06R in 2016-19 and 0.02R in
  2020-26 (arithmetic, not an outcome).
- At t's open the ask sits a median 4.25 / 15.5 points below the level
  (2016-19 / 2020-26), about half the risk: the buy stop needs a real move back.
- Orders exceed the 200-trade floor before fills, cancellations and position
  blocking.

Next: the trading build (3-bar order life, cancel on a touch of low(s), C1 at
high(s)), checked against this log before the trading runs.
