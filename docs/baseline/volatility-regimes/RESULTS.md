# Volatility, costs and the weak early years (2026-11-19, descriptive)

User questions after looking at the NQ M30 range history
([plot script](../../../python/plot_m30_range_history.py)):

1. Is RTL weak in 2010-15 because fixed costs are a much bigger share of a small candle?
2. Should the candle-range filter be adaptive instead of fixed points?
3. When candle ranges start to ramp up, does the market fall next, and does halting RTL help?

Data: native RTL baseline ledger (`Reports/rtl_midpoint_20261116/trades_baseline.csv`,
25,833 trades, June 2010 - Sept 2026, one MNQ, $1.05 per trade) and M30 bars built from the
continuous 1-minute file. Script: [`python/analyze_volatility_regimes.py`](../../../python/analyze_volatility_regimes.py);
tables in `Reports/volatility_regimes_20261119/`. Skips are **ledger omissions, not MT5 replays**.

## 1. Costs explain the size of the early loss, not the missing edge

| Era | Trades | Cost per trade in R | Gross R | Net R | Net R at the 2020-26 cost (0.018 R) |
|---|---|---|---|---|---|
| 2010-15 | 9,164 | 0.187 | +0.006 (-0.021 to +0.032) | -0.181 | -0.013 |
| 2016-19 | 6,167 | 0.095 | +0.081 (+0.047 to +0.116) | -0.014 | +0.063 |
| 2020-26 | 10,502 | 0.024 | +0.072 (+0.047 to +0.096) | +0.048 | +0.053 |

- The $1.05 is about 0.19 R per trade in 2010-15 (median risk 3-4 points) against 0.02 R since 2020.
  That turns a flat era into a -0.18 R per trade loss.
- With 2020s-sized costs 2010-15 is still about zero (-0.013 R): **there is no gross edge to save** in
  2010-15 (2016 too: +0.002). Costs are why it loses so much, not why it does not win.
- 2016-19 is different: gross +0.08 R is as good as recent years; costs (0.095 R) eat it. At
  2020s costs 2016-19 would have been clearly profitable. 2017 alone: gross +0.118, net -0.022.
- Caveat: MNQ only exists from May 2019. Before that one would have traded NQ, where commission
  per point of risk is roughly half the MNQ figure, so the early cost drag is somewhat overstated.

## 2. Adaptive size filter: only a minimum helps, and only through costs

Signal risk divided by the median M30 range of the 20 prior sessions, quintiles per era:

- Smallest fifth (risk under ~0.5x typical): net -0.43 R (2010-15), -0.16 R (2016-19), +0.05 R (2020-26).
  Gross R in that quintile is near zero in early eras: the loss is the cost.
- Largest fifth (over ~1.85x typical) is profitable in every era (+0.06 R 2016-19; $13.6k since 2020).
- No consistent gross-R pattern across quintiles. An adaptive **maximum** has no support (agrees with the
  GG size-cap test). An adaptive **minimum** is really a cost filter ("skip when $1.05 > x% of risk"); it
  would have helped 2010-19 but cost $3.8k since 2020 at the quintile cut. Not tested natively.

## 3. Volatility ramp: no reliable down signal, and RTL earns in those sessions

Ramp = median M30 range of the prior 5 sessions / prior 60 sessions, known before the session opens.

- Market after a ramp: next 20 sessions are not consistently lower. Ramp 1.5-2 was weak in 2016-19
  and 2020-26 (+0.5% / -0.4% over 20 sessions vs +1.3-1.9% normally) but strong in 2010-15 (+4.2%);
  ramp > 2 was strong in 2020-26 (+4.4%). Samples are small (38-146 sessions per cell).
- RTL trades in ramp sessions are not worse: since 2020 every bucket is profitable (ramp > 2: +0.060 R).

Halting all sessions above a ramp threshold (ledger omission), vs skipping as many random sessions:

| Era | Halt if ramp > | Sessions skipped | Net base -> halt | DD base -> halt | Random skips: net / DD | DD beats random |
|---|---|---|---|---|---|---|
| 2016-19 | 1.2 | 25% | $4,417 -> $1,973 | $2,176 -> $1,837 | $3,335 / $1,748 | 44% |
| 2016-19 | 1.5 | 13% | $4,417 -> $3,200 | $2,176 -> $1,809 | $3,769 / $1,967 | 68% |
| 2020-26 | 1.2 | 27% | $38,534 -> $23,990 | $5,781 -> $3,834 | $28,430 / $5,279 | 99% |
| 2020-26 | 1.5 | 13% | $38,534 -> $29,760 | $5,781 -> $4,853 | $33,684 / $5,457 | 81% |
| 2020-26 | 2.0 | 4% | $38,534 -> $32,910 | $5,781 -> $5,781 | $36,934 / $5,726 | 34% |

- Halting always costs more profit than random skipping: the skipped high-volatility sessions are
  among the better ones.
- Ramp > 1.2 since 2020 lowers DD more than random skips (99%), but net/DD falls 6.67 -> 6.26; trading
  0.66 contract every day gives the same DD with more profit. 2016-19 shows no DD benefit over random.
- Verdict: you mostly miss profit. Treat a volatility ramp as a sizing/risk warning at most, not a halt.

No settings changed.
