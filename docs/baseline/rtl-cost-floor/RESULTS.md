# RTL cost floor: results (2026-11-19, exploratory, native MT5)

[Protocol](PROTOCOL.md), fixed before the runs. Skip a signal when $1.05 would be more than 20% / 10% / 5% of its
risk, i.e. red candle range below 2.625 / 5.25 / 10.5 NQ points. Four native runs, 2010-06-07 to 2026-10-01 data,
one MNQ, costs charged afterwards. Run folder `Reports/rtl_cost_floor_20261119/`; scripts
`python/prepare_rtl_cost_floor.py`, `python/analyze_rtl_cost_floor.py`.

**Checks.** The control output is byte-identical to the 2026-11-16 RTL baseline (sha256 88c0d614...). Smallest kept
candle in each arm is exactly the threshold (0.25 / 2.75 / 5.25 / 10.5 pts); the tester log shows the filter enabled
with the intended minimum.

## At $1.05 per trade

| Era | Control net / closed DD | floor20 | **floor10 (main)** | floor05 |
|---|---|---|---|---|
| 2010-15 | -$7,496 / $8,254 | -$4,064 / $4,932 | **-$950 / $1,992** | +$320 / $786 |
| 2016-19 | $4,417 / $2,176 | $4,927 / $2,176 | **$5,646 / $2,208** | $4,540 / $2,085 |
| 2020-Sep 2026 | $38,534 / $5,781 | $38,346 / $5,781 | **$38,315 / $5,781** | $37,029 / $5,781 |
| Pooled | $35,454 / $8,803 | $39,210 / $5,781 | **$43,012 / $5,781** | $41,889 / $5,781 |
| Trades (pooled) | 25,833 | 21,734 | 17,285 | 12,138 |

Mean net R (2010-15 / 2016-19 / 2020-26): control -0.181 / -0.014 / +0.048; floor10 -0.033 / +0.041 / +0.046.

- **2010-15:** the floor turns a heavy loss into about break-even and cuts closed DD by three quarters. Still no real
  edge there: floor10 gross +0.029 R per trade.
- **2016-19:** floor10 net +$1,229, DD +$32 (flat). By the strict pre-set reading (net up, DD not up) this era is a
  hair short; in practice unchanged DD.
- **2020-26:** floor10 removes 80 trades, -$219, same DD. As planned, it barely touches recent years.
- The neighbours agree in direction: more floor = better 2010-15, but floor05 starts to cost 2020-26 money (-$1,505).
- Orders freed by skipped ones: 281 trades worth +$13 pooled (floor10). The effect is the removed trades, not
  changed timing.
- The removed small candles were also weaker **before** costs: gross R rises from +0.006 to +0.029 in 2010-15.

## At $0.50 per MNQ-equivalent (closer to full-NQ commissions before 2019)

floor10: 2010-15 -$2,456 -> +$632 (DD $3,620 -> $991); 2016-19 $7,809 -> $7,840 (DD $2,073 -> $2,105);
2020-26 $44,310 -> $44,048. The early-era gain shrinks but stays.

## Reading

- The cost floor does what the ledger said: it removes trades that lose through costs. It mostly matters in
  2010-15, a little in 2016-19, and not at all now (median risk ~50 points in 2026; a 5.25-point M30 candle
  is rare).
- It explains **why 2010-15 looked so bad** (small candles paying 20%+ of their risk in costs) but it does not create
  an edge there.
- As a live rule it is cheap insurance for a return to very low volatility, not a profit source today.
  Chosen after seeing the ledger split; exploratory. No baseline change.

## Follow-up: is MES today where NQ was in 2010-15? (2026-11-19, ledger only)

User question. Cap-0 RTL ledgers from the cross study (`Reports/rtl_vwap_cross_20261027/trades_ES.csv`, MES $5/pt,
$1.05); script `python/analyze_mes_cost_vs_ticks.py`. Skips are ledger omissions.

- **Costs: no.** MES since 2020 has median signal candles of 18-36 ticks and pays 0.03-0.06 R per trade, like NQ in
  2018-19, not NQ 2010-15 (12-16 ticks, 0.13-0.23 R). MES 2010-17 (6-10 ticks, 0.11-0.15 R) did look like early NQ.
- **The real MES problem is no gross edge:** -0.005 R per trade in 2020-26 before costs, against NQ +0.04 to +0.12
  at the same tick counts in 2018-19.
- **Ticks matter on both:** gross R by signal size, all years: NQ -0.02 under 8 ticks, +0.01-0.02 at 8-16, +0.04-0.08
  above 16; MES -0.19 / -0.06 / -0.02 under 16 ticks, but only +0.01-0.04 above. Small candles lose before costs on both
  (the [granularity finding](../nq-vs-es/RESULTS.md)); above that NQ has an edge and MES barely does.
- **Floors on MES:** a 10% cost floor (>= 2.25 pts) leaves 2020-26 at -$7,642. The tick-equal floor (>= 21 ticks,
  5.25 pts) gives +$418 / +$1,710 / -$2,325 (2010-15 / 2016-19 / 2020-26), net R +0.001 / +0.021 / -0.005: break-even,
  not an edge. Matches the native 50-tick ES test of 2026-10-11 ([results](../es-minimum-width/RESULTS.md)).
- Reading: the floor rescued early NQ because NQ's gross edge was there once candles were big enough. MES lacks it.
  No MES change.
