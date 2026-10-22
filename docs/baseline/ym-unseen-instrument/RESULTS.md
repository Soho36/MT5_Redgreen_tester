# Four baselines on YM (Dow), next to NQ and ES

2026-10-23 · Descriptive comparison, no pre-set gate · [Baseline studies](../README.md)

## Summary

- **Question (user):** how do the four baselines (RTL, GG, RTL-short, GG-short) do on Dow futures (YM), an
  instrument none of them was built on?
- **Answer: the long side keeps a small gross edge on YM, smaller than NQ's and too small to survive costs. Both
  shorts lose, as on NQ and ES.** After $1.05 costs, 2020–26: RTL −$2.5k (PF 0.987), GG −$5.7k (0.971),
  RTL-short −$15.8k (0.917), GG-short −$18.7k (0.910). Over 17 years RTL and GG each make money in 4 years,
  RTL-short in 1, GG-short in 0.
- **Before costs YM sits between NQ and ES.** RTL mean R per trade is +0.036 / +0.056 / +0.014 (2010–15 /
  2016–19 / 2020–26), against NQ +0.006 / +0.081 / +0.072 and ES −0.118 / −0.040 / −0.006. The earlier two YM
  intervals are above zero; the recent one includes zero. GG on YM follows: +0.013 / +0.046 / +0.005.
- **Costs weigh more on MYM:** median risk is $22.5 per trade recently (45 Dow points at $0.50), so $1.05 costs
  0.06 R, against 0.02 R on MNQ. That turns a small gross edge into a loss.
- **Buy stop versus plain long ([follow-up below](#plain-long-control-buy-stop-gain-versus-background)):** the
  buy-stop mechanism transfers to YM. It beats a market buy at the bar open by +0.080 / +0.057 / +0.032 R, every
  interval above zero, in 15 of 17 years (NQ +0.041 / +0.072 / +0.064, ES +0.029 / +0.042 / +0.035). YM's plain
  long sits slightly below zero (−0.044 / −0.001 / −0.018), between NQ (about 0 since 2016) and ES (clearly negative).
  Since 2020 YM's gain is half of NQ's and has been about zero in 2025–26.
- **Ticks per candle and H1 ([follow-up below](#ticks-per-candle-and-h1)):** MYM and MNQ both pay $0.50 per tick, so
  commission in R depends only on how many ticks a candle spans. YM's M30 candles span about half as many ticks as
  NQ's, which doubles the commission per trade in R. The edge before costs does not grow with ticks above about 20 on
  any instrument, and at equal ticks YM still earns less than NQ. RTL on H1 (correct session cutoff) helps YM on both
  counts: 2020–26 gross R +0.028 vs +0.014, cost 0.042 vs 0.060 R, net +$6.1k (PF 1.048) vs −$2.5k. Over all years
  it is +$5.4k, positive in 6 of 17 years.
- **Meaning:** YM is the second unseen index future after ES. It does not confirm the NQ result in money: the long
  gross edge is there in 2016–19 but has faded since 2020, which is when NQ earned most of its money. It does
  confirm, for the third time, that buying the break of a previous high beats a plain long.

## Setup

| | |
|---|---|
| Strategies | RTL = `RTL_runband` (red candle, buy stop at its high, stop at its low). GG = `GG_runband` (green candle, buy stop at its high). RTL-short = `GG_outside_short` with `UseOutsideFilter=false` (green candle, sell stop at its low, stop at its high; the RTL mirror). GG-short = `GG_red_outside_short` with `UseOutsideFilter=false` (red candle, sell stop at its low; the GG mirror). The short pair are the unfiltered controls of the [2026-10-20](../gg-outside/SHORT_RESULTS.md) and [2026-10-21](../gg-outside/RED_SHORT_RESULTS.md) screens |
| Common rules | M30, RR 1 bar-close exit, no run cap, flatten 23:30 with fallback, early-close calendar, trade window 01:00–23:30, 1 lot |
| Tester | Model 1 (1-minute OHLC), 2010-06-07 → 2026-10-23; every EA input written into the INI |
| Symbols | NQ `MNQcontDTBNT20102026_2` ($2/pt), ES `MEScontDTBNT20102026_2` ($5/pt), YM `MYMcontDTBNT20102026` ($0.50/pt, priced as MYM). [Data build](../../reference/DATA_BUILD.md#ym-build-2026-10-23) |
| Table | Trades entered before 2026-10-01 (end of the NQ data) on all three |
| Costs | $1.05 per trade on every symbol. R = trade profit ÷ (signal candle range × $/pt) |

**Checks.** All four NQ runs reproduce earlier ledgers: RTL and GG exactly (25,833 / 26,505 trades, the
2026-10-21 server-clock runs); both shorts trade for trade from 2016-01-11 on (the earlier runs started in 2016).
ES had to be re-imported (the old `MEScontDTBNT20102026` no longer holds bars in MT5); RTL on the new symbol gives
the same gross R as the 2026-10-08 [MES study](../mes-unseen-instrument/RESULTS.md) (−0.040 / −0.006 here with no
cap, −0.039 / +0.002 there with cap 3). $/pt read back from the ledgers matches each symbol.

## Results (net of $1.05, gross R with 95% interval)

| Strategy | Period | Inst | Trades | Win % | Gross R | 95% interval | Net R | PF net | Net $ | Max DD $ |
|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|
| RTL | 2010–15 | NQ | 9,164 | 40.3 | +0.006 | −0.021 … +0.032 | −0.181 | 0.865 | −7,496 | 8,254 |
| | | ES | 9,227 | 36.6 | −0.118 | −0.142 … −0.093 | −0.248 | 0.784 | −15,366 | 15,570 |
| | | **YM** | 9,097 | 40.8 | **+0.036** | +0.008 … +0.063 | −0.142 | 0.879 | −6,548 | 6,934 |
| | 2016–19 | NQ | 6,167 | 43.4 | +0.081 | +0.048 … +0.114 | −0.014 | 1.064 | 4,417 | 2,176 |
| | | ES | 6,286 | 39.7 | −0.040 | −0.071 … −0.010 | −0.142 | 0.924 | −4,653 | 5,356 |
| | | **YM** | 6,209 | 42.6 | **+0.056** | +0.023 … +0.089 | −0.070 | 1.013 | 691 | 2,261 |
| | 2020–26 | NQ | 10,501 | 42.8 | +0.072 | +0.046 … +0.097 | +0.048 | 1.090 | 38,400 | 5,781 |
| | | ES | 10,803 | 40.8 | −0.006 | −0.030 … +0.018 | −0.048 | 0.964 | −9,086 | 10,288 |
| | | **YM** | 10,889 | 40.7 | **+0.014** | −0.010 … +0.038 | −0.046 | 0.987 | −2,467 | 5,403 |
| GG | 2010–15 | NQ | 8,935 | 41.5 | +0.022 | −0.005 … +0.048 | −0.149 | 0.910 | −5,108 | 5,836 |
| | | ES | 8,685 | 38.2 | −0.098 | −0.123 … −0.073 | −0.215 | 0.814 | −13,237 | 13,532 |
| | | **YM** | 8,879 | 40.9 | **+0.013** | −0.014 … +0.039 | −0.150 | 0.881 | −6,626 | 6,852 |
| | 2016–19 | NQ | 6,388 | 43.7 | +0.071 | +0.040 … +0.103 | −0.016 | 1.048 | 3,636 | 1,708 |
| | | ES | 6,371 | 38.9 | −0.072 | −0.102 … −0.043 | −0.165 | 0.875 | −8,446 | 8,710 |
| | | **YM** | 6,373 | 42.2 | **+0.046** | +0.014 … +0.077 | −0.072 | 0.979 | −1,158 | 2,944 |
| | 2020–26 | NQ | 11,181 | 43.3 | +0.068 | +0.043 … +0.092 | +0.044 | 1.083 | 39,315 | 5,316 |
| | | ES | 11,169 | 41.5 | +0.003 | −0.020 … +0.026 | −0.037 | 0.970 | −8,297 | 10,407 |
| | | **YM** | 11,198 | 40.9 | **+0.005** | −0.019 … +0.029 | −0.052 | 0.971 | −5,701 | 8,955 |
| RTL-short | 2010–15 | NQ | 9,546 | 36.2 | −0.095 | −0.121 … −0.070 | −0.289 | 0.749 | −14,992 | 15,635 |
| | | ES | 9,252 | 33.6 | −0.209 | −0.233 … −0.185 | −0.341 | 0.663 | −24,681 | 24,769 |
| | | **YM** | 9,300 | 37.2 | **−0.067** | −0.093 … −0.041 | −0.249 | 0.776 | −12,559 | 12,769 |
| | 2016–19 | NQ | 6,457 | 37.7 | −0.019 | −0.052 … +0.014 | −0.117 | 0.927 | −5,492 | 6,872 |
| | | ES | 6,635 | 34.2 | −0.165 | −0.195 … −0.136 | −0.272 | 0.742 | −17,722 | 18,042 |
| | | **YM** | 6,533 | 36.7 | **−0.064** | −0.096 … −0.032 | −0.194 | 0.842 | −9,105 | 9,529 |
| | 2020–26 | NQ | 11,176 | 38.0 | −0.002 | −0.027 … +0.024 | −0.027 | 0.993 | −3,228 | 21,096 |
| | | ES | 11,491 | 36.6 | −0.067 | −0.091 … −0.043 | −0.112 | 0.892 | −29,356 | 32,224 |
| | | **YM** | 11,295 | 38.4 | **−0.016** | −0.040 … +0.009 | −0.078 | 0.917 | −15,807 | 18,446 |
| GG-short | 2010–15 | NQ | 9,494 | 36.5 | −0.099 | −0.124 … −0.074 | −0.278 | 0.747 | −16,299 | 16,376 |
| | | ES | 9,782 | 33.3 | −0.224 | −0.246 … −0.202 | −0.351 | 0.633 | −30,402 | 30,441 |
| | | **YM** | 9,539 | 37.3 | **−0.080** | −0.105 … −0.055 | −0.251 | 0.748 | −15,652 | 15,778 |
| | 2016–19 | NQ | 6,677 | 36.8 | −0.055 | −0.086 … −0.023 | −0.149 | 0.845 | −13,609 | 14,729 |
| | | ES | 6,983 | 34.4 | −0.167 | −0.196 … −0.139 | −0.271 | 0.722 | −21,510 | 22,377 |
| | | **YM** | 6,649 | 37.2 | **−0.063** | −0.093 … −0.032 | −0.188 | 0.831 | −10,455 | 11,274 |
| | 2020–26 | NQ | 11,363 | 38.3 | −0.005 | −0.030 … +0.020 | −0.029 | 0.964 | −18,096 | 23,214 |
| | | ES | 11,737 | 36.9 | −0.070 | −0.093 … −0.047 | −0.113 | 0.879 | −35,926 | 38,544 |
| | | **YM** | 11,550 | 38.1 | **−0.027** | −0.051 … −0.004 | −0.087 | 0.910 | −18,663 | 21,275 |

Dollar figures are not comparable across instruments ($2, $5 and $0.50 per point); compare R.

**YM by year (net $):** RTL is positive in 2018, 2019, 2020 and 2023; GG in 2019, 2020, 2025 and 2026;
RTL-short only in 2020; GG-short in no year. Full table: `Reports/ym_baselines_20261023/ym_years.csv`.
After 2026-10-01 (outside the table) YM adds 104 RTL trades (+$760), 104 GG (+$618), 85 RTL-short (−$36),
104 GG-short (−$348).

**Long and short together:** on all three instruments RTL and GG are correlated +0.53 to +0.57 day by day, the two
shorts +0.58 to +0.59, longs against shorts −0.16 to −0.23. Adding a losing short to a long does not help, as
already seen on NQ ([long + short merge](../../JOURNAL.md#2026-10-07-long--short-baselines-merged-descriptive)).

## Notes and limits

- **Data holes:** YM has no bars for parts of 2020-02-27, 2020-02-28 (from 10:00), 2020-03-16 (4 hours) and the
  end of 2020-06-30 (also missing in ES). 13–18 trades per strategy fall on those days; they move results by at
  most $1.3k and are left in.
- **Resolution:** a YM tick is one Dow point, so the median recent candle spans about 45 ticks (2016–19 about 22),
  against about 115 on NQ and 25 on ES. YM's recent fade happens while its candles span *more* ticks, so tick
  resolution alone does not explain it ([granularity study](../granularity/RESULTS.md) for context).
- One-minute OHLC simulated fills, as in all screening runs.

## Plain-long control: buy-stop gain versus background

Follow-up the same day (user request). The control is the [signal-colour study's](../signal-colour/RESULTS.md)
market buy: at every M30 bar open while flat, buy at market with the stop one previous-candle range below, same RR 1
bar-close exit, flattening and calendar as RTL (saved `RTL_signal` EA, `SignalMode=3`, no cap). Gain = RTL mean gross
R minus control mean gross R; intervals resample whole days jointly. Trades before 2026-10-01.

**Checks.** Market-entry ledgers drop positions stopped on the next tick, so every control and RTL ledger was
rebuilt from the MT5 report ([audit](../../../python/audit_ym_control.py)): controls recover 72 (NQ), 128 (ES) and
75 (YM) trades; RTL ledgers need none; all match the tester totals. The NQ control reproduces the audited 2026-10-08
control trade for trade up to 2026-07-14 (35,872 trades). The same EA in red-candle mode on YM reproduces the RTL
YM ledger exactly (26,299 trades).

| Period | Inst | RTL gross R | Control gross R | Control 95% | **Buy-stop gain** | Gain 95% |
|---|---|---:|---:|---|---:|---|
| 2010–15 | NQ | +0.006 | −0.036 | −0.056 … −0.015 | +0.041 | +0.019 … +0.065 |
| | ES | −0.118 | −0.147 | −0.166 … −0.128 | +0.029 | +0.008 … +0.050 |
| | **YM** | +0.036 | −0.044 | −0.066 … −0.022 | **+0.080** | +0.057 … +0.101 |
| 2016–19 | NQ | +0.081 | +0.009 | −0.017 … +0.034 | +0.072 | +0.045 … +0.100 |
| | ES | −0.040 | −0.083 | −0.106 … −0.060 | +0.042 | +0.016 … +0.067 |
| | **YM** | +0.056 | −0.001 | −0.026 … +0.023 | **+0.057** | +0.031 … +0.084 |
| 2020–26 | NQ | +0.072 | +0.007 | −0.012 … +0.027 | +0.064 | +0.043 … +0.085 |
| | ES | −0.006 | −0.041 | −0.059 … −0.023 | +0.035 | +0.016 … +0.055 |
| | **YM** | +0.014 | −0.018 | −0.038 … +0.001 | **+0.032** | +0.011 … +0.052 |
| all | NQ | +0.050 | −0.007 | −0.020 … +0.006 | +0.057 | +0.044 … +0.071 |
| | ES | −0.053 | −0.087 | −0.099 … −0.076 | +0.034 | +0.021 … +0.047 |
| | **YM** | +0.031 | −0.023 | −0.036 … −0.010 | **+0.054** | +0.042 … +0.067 |

- **The buy stop adds value on all three instruments in every period.** The gain is positive in 17/17 years on NQ
  and ES and 15/17 on YM. The two YM exceptions are 2025 (−0.001) and 2026 to date (−0.009).
- **YM's background is mildly negative,** like a weaker ES: a plain long loses a little before costs in every period.
- **Why recent YM is weak:** RTL +0.014 R = background −0.018 + gain +0.032. Against NQ (+0.007 and +0.064), both
  parts are lower, but most of the gap is in the gain: it fell from +0.057 (2016–19) to +0.032 (2020–26) and has
  been about zero since 2025. On NQ it held up. By year: `Reports/ym_control_20261023/years.csv`.
- **Earlier YM looks better than NQ:** in 2010–15 the YM gain (+0.080) is twice NQ's, which is why RTL had a small
  gross edge on YM in the years it had none on NQ.

## Ticks per candle and H1

Follow-up the same day. The user ran RTL on MYM by hand at M15 / M30 / H1 / H2 (`RTL_signal`, no commission;
gross +$17.5k / +$20.0k / +$23.5k / +$14.3k) and asked whether YM would do better with NQ's candle resolution.
Script: [analyze_ym_h1.py](../../../python/analyze_ym_h1.py).

**Commission is a ticks question.** MNQ and MYM both pay $0.50 per tick, so $1.05 costs the same R at the same
number of ticks per candle (the cost columns below are identical for NQ and YM). Median RTL candle 2016–26:
NQ 74 ticks, YM 35, ES 19. So on M30 YM pays about twice NQ's commission per R.

**The edge before costs is not a ticks question above ~20 ticks.** RTL gross R by signal candle size, 2016–26:

| Ticks per candle | NQ RTL R | YM RTL R | ES RTL R | NQ gain | YM gain | Cost R (NQ = YM) |
|---|---:|---:|---:|---:|---:|---:|
| <10 | −0.087 | +0.017 | −0.104 | +0.096 | +0.177 | 0.33 |
| 10–20 | +0.126 | +0.007 | −0.017 | +0.155 | +0.066 | 0.15 |
| 20–30 | +0.089 | +0.003 | +0.041 | +0.046 | +0.034 | 0.087 |
| 30–45 | +0.090 | +0.027 | +0.009 | +0.073 | +0.024 | 0.058 |
| 45–70 | +0.088 | +0.040 | +0.015 | +0.067 | +0.023 | 0.038 |
| 70–110 | +0.092 | +0.094 | −0.030 | +0.093 | +0.074 | 0.025 |
| 110+ | +0.052 | +0.027 | +0.071 | +0.043 | +0.036 | 0.012 |

Gain = RTL minus plain-long control. On NQ, RTL earns about +0.09 R from 10 ticks up, flat. On YM it is lower than
NQ in every bucket from 10 to 70 ticks, where most YM trades are; only 70–110 matches. Bucket intervals are wide
(gain intervals about ±0.05–0.08), and bucketing mixes candle size with volatility and era, so this is descriptive.
It does not support "YM would match NQ with NQ's resolution": more ticks per candle would cut YM's commission to
NQ's level but would not lift its gross edge to NQ's. This agrees with the [granularity study](../granularity/RESULTS.md),
where NQ's edge stopped improving at about 30 steps per candle.

**RTL on H1, correct session cutoff.** On H1 there is no 23:30 bar, so `RTL_signal` / `RTL_runband` on H1 can hold
positions overnight. These runs use the [H1 study's](../timeframe-h1/RESULTS.md) `RTL_timeframe` (tick-level 23:30
cutoff), same inputs as M30 (`Reports/ym_h1_20261023/`; NQ H1 from the H1 study). At most one overnight exit per run
(a data-hole day). The YM H1 run grosses +$20.4k to 2026-10-22 against the user's +$23.5k; the ~$3.1k difference is
the overnight holds.

| Inst | TF | Period | Trades | Median ticks | Gross R | Cost R | Net R | Net $ | PF net | Max DD $ |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NQ | M30 | 2016–19 | 6,167 | 30 | +0.081 | 0.095 | −0.014 | 4,417 | 1.064 | 2,176 |
| NQ | H1 | 2016–19 | 3,377 | 44 | +0.081 | 0.065 | +0.016 | 4,462 | 1.091 | 1,347 |
| NQ | M30 | 2020–26 | 10,501 | 115 | +0.072 | 0.024 | +0.048 | 38,400 | 1.090 | 5,781 |
| NQ | H1 | 2020–26 | 5,849 | 163 | +0.057 | 0.017 | +0.040 | 28,020 | 1.092 | 4,039 |
| ES | M30 | 2020–26 | 10,803 | 25 | −0.006 | 0.042 | −0.048 | −9,086 | 0.964 | 10,288 |
| ES | H1 | 2020–26 | 5,911 | 36 | +0.004 | 0.029 | −0.025 | 2,312 | 1.013 | 5,564 |
| YM | M30 | 2010–15 | 9,097 | 15 | +0.036 | 0.177 | −0.142 | −6,548 | 0.879 | 6,934 |
| YM | H1 | 2010–15 | 4,960 | 21 | +0.050 | 0.122 | −0.072 | −2,223 | 0.940 | 2,728 |
| YM | M30 | 2016–19 | 6,209 | 22 | +0.056 | 0.126 | −0.070 | 691 | 1.013 | 2,261 |
| YM | H1 | 2016–19 | 3,440 | 31 | +0.054 | 0.087 | −0.033 | 1,482 | 1.041 | 1,728 |
| YM | M30 | 2020–26 | 10,889 | 45 | +0.014 | 0.060 | −0.046 | −2,467 | 0.987 | 5,403 |
| YM | H1 | 2020–26 | 5,923 | 64 | +0.028 | 0.042 | −0.014 | 6,097 | 1.048 | 2,635 |

Mean net R is below zero while net dollars are positive because the larger candles carry more dollars per R and the
smaller ones carry most of the cost. Full table, all periods: `Reports/ym_h1_20261023/m30_vs_h1.csv`.

- **YM H1 beats YM M30 in every period** after costs, with lower drawdown: half the trades means half the commission,
  and recent gross R doubled. On NQ, H1 keeps the gross R in 2016–19 but loses some in 2020–26 (as the H1 study found).
- **Still small:** YM H1 makes +$5.4k over 16 years, positive in 6 of 17 years; 2010–15 loses. 2020–26 +$6.1k is about
  a fifth of NQ M30's +$38.4k at one micro contract each, and 2020 alone gives +$3.5k of it.
- H1 was chosen after seeing the user's hand runs at four timeframes, so H1 being best on YM is a selected result.

## Reproduce

```powershell
.\venv\Scripts\python.exe python\build_continuous.py YM "F:\DATABENTO\YM_16_YEARS" "F:\DATABENTO\YM_16_YEARS\source\glbx-mdp3-20100606-20261021.ohlcv-1m.dbn"
.\venv\Scripts\python.exe python\import_custom_symbol.py "F:\DATABENTO\YM_16_YEARS\MT5_YM_continuous_2010-2026_ohlcv-1m.csv" MYMcontDTBNT20102026 MNQcontDTBNT20102026_2 1.0 0.5 Reports\ym_symbol_20261023
.\venv\Scripts\python.exe python\import_custom_symbol.py "F:\DATABENTO\ES_16_YEARS\MT5_ES_continuous_2010-2026_ohlcv-1m.csv" MEScontDTBNT20102026_2 MNQcontDTBNT20102026_2 0.25 1.25 Reports\es_symbol_20261023
.\venv\Scripts\python.exe python\prepare_ym_baselines.py
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\ym_baselines_20261023 RTL_runband <tags>   # per EA, see manifest.json
.\venv\Scripts\python.exe python\analyze_ym_baselines.py
.\venv\Scripts\python.exe python\prepare_ym_control.py
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\ym_control_20261023 RTL_signal
.\venv\Scripts\python.exe python\audit_ym_control.py
.\venv\Scripts\python.exe python\analyze_ym_control.py
.\venv\Scripts\python.exe python\prepare_ym_h1.py
.\venv\Scripts\python.exe python\run_mt5_job.py Reports\ym_h1_20261023 RTL_timeframe
.\venv\Scripts\python.exe python\analyze_ym_h1.py
```
