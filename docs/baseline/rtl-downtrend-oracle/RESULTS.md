# RTL downtrend crystal ball: perfect timing helps, late timing does not

2026-10-24. Exploratory historical study proposed by the user. Current uncapped RTL
only. [Frozen protocol](PROTOCOL.md) | [Earlier regime studies](../rtl-market-regimes/PLAN.md)

**A perfect crystal ball would have raised RTL's net profit by 36-202%. Almost all
of that gain depends on being on time.** One session late cuts it by half or more; two to three
sessions late it is gone for 2-3% drops; only the larger drops in 2020-26 tolerate
more delay, and not in 2016-19. A real detector (the same zigzag without
hindsight) reacts 2-21 sessions late and cuts profit by 10-82% at every size, in
both eras. By the rule fixed before the run, **further research on downtrend
filters for RTL is not worthwhile.** No strategy defaults or live settings changed.

## The idea

Skip RTL while the market is falling and resume when the fall ends, using
hindsight to find the exact peak and trough. No real indicator can beat that, so
it is a ceiling for every downtrend filter. The same signals are then made
deliberately late, to see how quickly the benefit decays. The delay at which it
disappears is how fast a real detector would need to be.

## Definitions

- **Trades:** the 16,668 verified RTL trades, 6,167 in 2016-19 and 10,501 in
  2020-September 2026; one MNQ-valued contract, $1.05 per trade. Baseline net
  profit $4,416.65 / $38,399.95.
- **Downtrend:** a zigzag on research-session daily closes. A fall of at least x
  from a closing peak, ending at the lowest close before a rebound of at least x.
  Sizes 2%, 3%, 5%, 10%, fixed in advance (20% was dropped as too rare).
- **Roll gaps** are removed from the closes (the jump from the old contract's last
  close to the new contract's first open). Unadjusted closes are a sensitivity.
- **Crystal ball, d sessions late:** skip trades submitted from session peak+1+d
  through trough+d. **Live zigzag:** skip from the session after the fall reaches
  x through the session in which the rebound reaches x. It uses no future data.
- **Controls:** the same skip pattern placed at every other point in the era
  (all circular shifts), and the baseline scaled down to the same holding time.

| Drop size | Downtrends, 2016-19 / 2020-26 | Median length, sessions | Sessions inside downtrends, 2016-19 / 2020-26 |
|---|---:|---:|---:|
| 2% | 44 / 123 | 4 | 26% / 40% |
| 3% | 24 / 76 | 9 / 6 | 22% / 36% |
| 5% | 11 / 39 | 15 | 20% / 32% |
| 10% | 3 / 12 | 21 / 48.5 | 14% / 33% |

A fixed percentage means different things in calm and volatile years: 2017 had
seven 2% downtrends, 2022 had 29. The early 10% result rests on three events.

## 1. The ceiling and how fast it decays

Change in net profit versus trading every session, roll-adjusted closes:

| Era | Drop | On time | 1 late | 2 late | 3 late | 5 late | 10 late | 20 late | Live zigzag |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2016-19 | 2% | +202% | +56% | -7% | -35% | -93% | -64% | -36% | -82% |
| 2016-19 | 3% | +152% | +71% | +15% | -10% | -64% | -69% | -38% | -63% |
| 2016-19 | 5% | +92% | +43% | +17% | -5% | -40% | -54% | -5% | -63% |
| 2016-19 | 10% | +36% | +17% | +3% | -1% | -6% | -5% | -19% | -10% |
| 2020-26 | 2% | +172% | +50% | -9% | -26% | -39% | -23% | -25% | -42% |
| 2020-26 | 3% | +134% | +46% | +7% | -15% | -25% | -25% | -41% | -58% |
| 2020-26 | 5% | +97% | +46% | +28% | +5% | -8% | -23% | -35% | -49% |
| 2020-26 | 10% | +39% | +18% | +16% | +8% | +1% | -7% | -23% | -29% |

![Change in net profit by crystal-ball delay](../../../Reports/rtl_downtrend_oracle_20261024/decay.png)

On time, the 2% crystal ball would have turned the recent $38,400 into $104,294,
by skipping trades that averaged -0.13 R (-0.19 R in 2016-19). On-time skips beat
every shifted placement of the same pattern. For 2% drops, drawdown also fell well
below the scaled-down control: $1,528 versus $3,611 recently, $584 versus $1,610
earlier.

Break-even delay, the first tested delay at which skipping no longer adds profit:

| Drop | 2016-19 | 2020-26 | No better than random time off from |
|---|---:|---:|---|
| 2% | 2 | 2 | 2 / 3 sessions |
| 3% | 3 | 3 | 2 / 3 sessions |
| 5% | 3 | 5 | 2 / 5 sessions |
| 10% | 3 | 10 | 1 / 10 sessions |

Only the 5% and 10% drops in 2020-26 stay helpful at three sessions late, and
they fail in 2016-19. Nothing passes the fixed test (three or more sessions late,
better than baseline and than 97.5% of shifted placements, in both eras).

## 2. The live zigzag: what a real detector gets

| Drop | Stop lag / resume lag, median sessions | Profit change 2016-19 / 2020-26 | Skipped trades, mean net R | Shifted placements doing at least as well |
|---|---|---:|---:|---:|
| 2% | 2 / 2-3 | -82% / -42% | +0.050 / +0.034 | 99% / 64% |
| 3% | 3-3.5 / 3 | -63% / -58% | +0.034 / +0.062 | 97% / 96% |
| 5% | 6-8 / 4-6 | -63% / -49% | +0.052 / +0.068 | 99.6% / 96% |
| 10% | 17.5-21 / 10.5-13 | -10% / -29% | +0.028 / +0.054 | 40% / 85% |

All trades average -0.014 R / +0.048 R. The live zigzag skips trades that are
better than average in seven of eight cases, and is usually worse than placing
the same time off at random. Its drawdown beats simply trading smaller in only
two of eight cases: 5% drops in 2020-26, with far less profit ($19,606 versus
$28,332), and 10% drops in 2016-19, which rest on three downtrends. For 3% drops
in 2020-26 it is $5,296 versus $3,902 for the scaled control.

## 3. Why lateness hurts this much

By definition, the hindsight downtrend contains only the falling part, so the
long trades skipped on time are handicapped by the falling price. A late signal
moves the skipped window forward: it keeps some of the falling trades and
removes sessions just after the low, which are roughly average for RTL rather
than bad. At 5-10 sessions late, skipped trades average -0.008 to +0.039 R. Short
downtrends (median 4-15 sessions at 2-5%) are mostly over before any detector
could confirm them; a confirmation that needs the price to fall x already
arrives near the bottom, and resuming after an x rebound misses the bounce.

## Sensitivity and limits

- **Unadjusted closes:** same decision. Gains and break-even delays are similar;
  the 10% recent crystal ball stays positive through 10 sessions late (+3.5%),
  but 2016-19 still fails from 3 sessions.
- **Ledger omission, not an MT5 replay.** Skipping by submission session ignores
  any order that a freed position might have allowed.
- **Scope:** daily downtrends of 2-10%. Other kinds of filter (execution costs,
  intraday structure already studied, others) are not covered by this ceiling.
- All history has been used in earlier studies; results are exploratory.

## Verification and reproducibility

Protocol SHA256 (CRLF-normalized):
`a39d490acc8897adf206da557c1786d07adfeef1fb209ba3d6e5d3c73afa2ffa`, checked before
and after the run. **Independent verification: PASS** (12 of 12 checks): input
hashes, a separately written vectorized zigzag reproduces all pivots for both
series, explicit session-range masks, return-based roll adjustment, all 128
rule/era ledger partitions and drawdowns, every circular shift by direct loop,
and the protocol decision. **All 10 focused tests pass.** They cover pivots,
exact thresholds, ties, the censored final leg, delay boundaries, roll
adjustment, the shift control and that the live rule ignores future closes.

- `python/analyze_rtl_downtrend_oracle.py`: calculations and provenance.
- `python/verify_rtl_downtrend_oracle.py`: independent verifier.
- `python/test_rtl_downtrend_oracle.py`: focused tests.
- `python/report_rtl_downtrend_oracle.py`: figure and tables.

Outputs in `Reports/rtl_downtrend_oracle_20261024/`: segments, masks, rule
outcomes and controls, yearly counts, lags, decision, provenance, verification.
[Calculated tables](../../../Reports/rtl_downtrend_oracle_20261024/report_tables.md).
