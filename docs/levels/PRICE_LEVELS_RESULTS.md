# Q6/Q7: support proximity and room to resistance

2026-10-03. [Frozen protocol](../PRICE_LEVELS_PROTOCOL.md) ·
[Analysis](../../python/analyze_price_levels.py) ·
[Full generated tables](../../Reports/levels/price_levels_20261003/report.md).

## Finding

**No filter qualifies in this first screen. Keep the RTL entry rules unchanged.**

- **Q6, proximity to support:** previous-session near-support trades have a
  higher dollar profit factor in 2016-19 but a lower one in 2020-26. The earlier
  near group has only 187 trades, below the preset 200-trade minimum. Far-support
  trades remain profitable in both periods. This is inconclusive about a small
  proximity effect, not proof that support levels never matter.
- **Q7, room to resistance:** previous-session resistance within 1R does not
  identify a losing group. Its PF is 1.110 / 1.196 across the two periods, versus
  1.103 / 1.097 with more than 1R of room. Neither neighboring cutoff qualifies.
- Current-session and previous-week highs also fail to support avoiding nearby
  resistance. Current-session limited-room trades perform better on both PF and
  average R in both periods. This is a secondary, reverse-direction observation;
  it is not a newly selected filter or an established independent effect.
- Repeating comparisons on the identical 12,938 trades eligible for all three
  sources does not change the no-filter decision. No full filtered-strategy MT5
  rerun was triggered by the frozen rule.

## What was measured

The reference map is frozen **before the signal bar opens**. Current-session
levels use earlier completed bars, previous-session levels use the last completed
trading session, and previous-week levels use the last completed calendar
trading week. All are full-session extremes in the rebuilt symbol's clock.

Let R be signal high minus signal low. Support distance is
`(signal low - reference low) / R`; overhead room is
`(reference high - planned entry) / R`, where planned entry is signal high.
Negative distances and exact overhead contact are separate groups. Historical
extremes are reference prices, not automatically active/unbroken support or
resistance. No pivot clustering, role reversal, age optimization, or combined
level map was used.

The strategy stays MaxRedRun=3, MinLocation=0, fixed one contract, RR=1,
bar-close-qualified exit, calendar/fallback flattening and original entry windows.
Costs are **$1.05 per round trip**, with $2/point. Outcomes use the existing
one-minute OHLC runs on `MNQcontDTBNT20102026_2`; no new fills were simulated.

## Previous session: primary comparison

| Question / group | 2016-19 trades | Net $ | Net PF | Avg net R | 2020-26 trades | Net $ | Net PF | Avg net R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Support near: 0-0.5R below signal low | 187 | 443 | 1.165 | +0.044 | 311 | 1,482 | 1.077 | +0.083 |
| Support far: >0.5R below signal low | 4,632 | 1,870 | 1.041 | -0.028 | 7,379 | 29,558 | 1.119 | +0.062 |
| Resistance above entry: >0 to 1R | 546 | 695 | 1.110 | +0.005 | 847 | 7,309 | 1.196 | +0.083 |
| Resistance above entry: >1R | 3,890 | 4,404 | 1.103 | -0.013 | 6,480 | 24,510 | 1.097 | +0.060 |

Dollar PF and average R weight trades differently; a positive dollar result can
coexist with negative average R. Dollar PF was the preselected screening metric.
The groups above are not the whole population: signal lows below the reference
low, and planned entries at/above the reference high, are reported separately
in the complete tables rather than being relabeled far support or unlimited room.

Month-block bootstrap intervals for the primary differences in average net R:

| Contrast | 2016-19 difference [95% interval] | 2020-26 difference [95% interval] |
|---|---:|---:|
| Far minus near support | -0.073 [-0.274, +0.121] | -0.021 [-0.164, +0.117] |
| Limited minus more room | +0.018 [-0.073, +0.117] | +0.023 [-0.075, +0.119] |

All four intervals include zero. They are descriptive and unadjusted for
multiple comparisons; they do not establish equivalence between groups.

## Other horizons, kept separate

| Source / group | 2016-19 trades | Net $ | Net PF | Avg net R | 2020-26 trades | Net $ | Net PF | Avg net R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Current session: near support | 805 | 102 | 1.011 | -0.087 | 1,309 | 3,821 | 1.068 | +0.093 |
| Current session: far support | 3,576 | 3,040 | 1.088 | -0.014 | 5,770 | 29,273 | 1.150 | +0.066 |
| Current session: room >0 to 1R | 2,094 | 3,354 | 1.147 | +0.047 | 3,297 | 21,209 | 1.165 | +0.078 |
| Current session: room >1R | 3,051 | 2,106 | 1.063 | -0.043 | 5,024 | 13,571 | 1.071 | +0.049 |
| Previous week: near support | 61 | 467 | 1.437 | +0.114 | 105 | 280 | 1.038 | +0.043 |
| Previous week: far support | 4,562 | 2,289 | 1.051 | -0.018 | 6,769 | 28,159 | 1.122 | +0.068 |
| Previous week: room >0 to 1R | 209 | 555 | 1.235 | +0.150 | 291 | 2,948 | 1.235 | +0.048 |
| Previous week: room >1R | 3,443 | 7,436 | 1.183 | +0.018 | 5,614 | 25,149 | 1.109 | +0.059 |

The weekly near-support samples are too small for the preset minimum. These
tables use each source's eligible sample; use the generated common-population
tables for comparisons between sources. On that common sample, current-session
limited-room versus more-room PF remains 1.198 versus 1.061 in 2016-19 and
1.205 versus 1.061 in 2020-26. Its recent-period mean-R difference interval still
includes zero. Distances are also related to candle size and session time, so
this is not evidence of an independent causal resistance effect.

## Year and threshold checks

Previous-session resistance within 1R is profitable in **10 of 11 calendar-year
slices**, including partial 2026; 2022 is the exception (PF 0.795, -$1,584).
The near-support group loses in 6 of 11 years and profits in 5, with only 30-68
trades per year. The annual detail is retained in `annual_contrasts.csv`.

| Previous-session comparison | 2016-19 group PF / comparison PF | 2020-26 group PF / comparison PF |
|---|---:|---:|
| Support far >0.25R / near 0-0.25R | 1.043 / 1.261 | 1.114 / 1.157 |
| Support far >0.50R / near 0-0.50R | 1.041 / 1.165 | 1.119 / 1.077 |
| Support far >0.75R / near 0-0.75R | 1.044 / 1.089 | 1.107 / 1.191 |
| Room >0 to 0.5R / >0.5R | 1.110 / 1.103 | 1.008 / 1.118 |
| Room >0 to 1.0R / >1.0R | 1.110 / 1.103 | 1.196 / 1.097 |
| Room >0 to 1.5R / >1.5R | 1.155 / 1.090 | 1.298 / 1.064 |

All hypothesized weak groups remain profitable in both periods at all predefined
cutoffs. Exact equality with the current-session high loses in both periods,
but with only 71 / 35 trades and outside the primary contrasts; it does not
qualify for a filter. No extra thresholds were searched after seeing results.

## Coverage, age and verification

- Original baseline: **5,697 / 9,271 trades**; net **$6,485.15 / $37,980.95**.
  Counts, gross profit and original trade fields reconcile with saved tester
  statistics and the saved RR=1 baseline.
- Rebuilt **191,786 M30 bars** from the minute source. All **3,053,472** exported
  OHLC values (51 candles per trade) match that reference exactly.
- Previous-session usable trades: **5,606 / 9,129**; 91 / 142 excluded at rolls.
  Current-session usable trades: **5,549 / 9,068**; 148 / 203 had no preceding
  bar in the same session. Previous-week usable trades: **5,237 / 8,009**;
  460 / 1,262 excluded because the reference window crossed contracts.
- Common sample: **5,104 / 7,834** trades. Primary gates fail there too.
- **1,191 independent direct-window checks** verify extremes, first-attainment
  timestamps, source boundaries, roll exclusions and signed distances.
- **5 unit tests pass**, covering signal/future exclusion, equal retests,
  weekends/holidays, calendar weeks, contract rolls and exact distance boundaries.
- Formation age was recorded, not optimized: previous-session highs/lows are
  typically about 22-25 hours old; current-session extrema about 2.5-4 hours;
  previous-week extrema about 151-173 hours. These are per-trade medians and
  include elapsed weekend time. Trading-session ages are also exported.

This is an exploratory association screen on previously inspected data. The
accepted OHLC execution sensitivity remains unresolved. The no-filter decision
does not settle pivot zones, rejection/reclaim behavior, or level role reversal.

## Reproduce

```powershell
.\venv\Scripts\python.exe python\analyze_price_levels.py
.\venv\Scripts\python.exe -m unittest discover -s python -p test_price_levels.py -v
```

Outputs are in `Reports/levels/price_levels_20261003/`: `features.csv`, `groups.csv`,
`annual_contrasts.csv`, `contrasts.json`, `coverage.csv`, `ages.csv`,
`decisions.json`, `m30_reference.csv`, `provenance.json`, and `report.md`.
The provenance file records input, analysis-script and protocol hashes.
