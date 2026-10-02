# Q8: breach and reclaim of a known low

2026-10-03 · [Frozen protocol](BREACH_RECLAIM_PROTOCOL.md) ·
[Analysis](../python/analyze_breach_reclaim.py) ·
[Full comparison tables](../Reports/breach_reclaim_20261003/report.md).

## Answer

**There is evidence for a narrower version of the hypothesis: a current-session
low reclaim is followed more often by an additional +0.5R advance at 90 minutes.
It does not consistently predict a higher average price return or a better RTL
profit factor across both periods. No filter qualifies.**

The study includes **35,632 qualifying order attempts**, including those that
never filled, and the **14,968 original filled baseline trades**. This avoids
answering the price-response question only with signals that already went far
enough upward to trigger the buy stop.

Current-session lows are the primary source. Previous-session and previous-week
lows are reported separately. No EA changes or new MT5 runs were made.

## Exact comparison

A fresh breach opens above the known low, trades at least one tick below it,
and then either **closes above it (reclaimed)** or **closes below it
(unrecovered)**. Signals opening at/below the level, exact close at the level,
touch without breach, and no contact are separate groups.

All levels existed before the signal opened. The signal cannot create its own
reference low. Roll exclusions and session definitions are unchanged from Q6/Q7.
The current-session low includes only earlier completed bars in that session.

For subsequent price response, R is the original signal range. The primary
event is **a close at least 0.5R above the signal close after three subsequent
M30 bars**, not merely touching that price and not the reclaim already observed.
Incomplete windows, gaps, early closes and delayed submissions are excluded
from that horizon's comparison. No within-bar ordering is assumed.

## Price response, including unfilled attempts

| Current-session low | 2016-19 reclaimed | 2016-19 unrecovered | 2020-26 reclaimed | 2020-26 unrecovered |
|---|---:|---:|---:|---:|
| Complete 90-minute windows | 1,012 | 1,967 | 2,000 | 3,433 |
| Endpoint at least +0.5R | **35.7%** | **29.6%** | **31.5%** | **28.4%** |
| Endpoint above signal close at all | 57.4% | 56.5% | 52.5% | 54.6% |
| Mean endpoint return | +0.118R | +0.047R | -0.001R | +0.018R |
| Median endpoint return | +0.173R | +0.118R | +0.082R | +0.082R |
| Mean maximum upward excursion | +0.950R | +0.772R | +0.852R | +0.740R |
| Mean maximum downward excursion | -0.906R | -0.805R | -0.939R | -0.791R |

Reclaim minus unrecovered, with descriptive 95% calendar-month block intervals:

| Metric | 2016-19 difference [interval] | 2020-26 difference [interval] |
|---|---:|---:|
| Probability of >= +0.5R endpoint | **+6.1 pp [+2.7, +9.6]** | **+3.1 pp [+0.3, +5.8]** |
| Mean endpoint return | +0.071R [-0.021, +0.162] | -0.020R [-0.088, +0.053] |

Thus the positive finding concerns a **particular size of upward response**.
It is not a higher probability of any positive close in both periods, and does
not imply better average return. Reclaim cases also have larger average
downward excursions. Their distribution is different in both directions;
more +0.5R outcomes alone cannot establish a trading advantage.

The intervals are exploratory and unadjusted for multiple comparisons. All
history was previously inspected, and the current-session follow-up was motivated
by the prior screen. These are associations, not new out-of-sample confirmation.

## Filled RTL trades

The buy stop remains at the signal high, stop at the signal low, with the
original 1R bar-close-qualified exit, session rules and one contract. Net
figures include $1.05 commission per round trip, with $2/point.

| Period | Group | Trades | Net $ | Net PF | Avg net R | Net win rate |
|---|---|---:|---:|---:|---:|---:|
| 2016-19 | Reclaimed current-session low | 506 | +229 | **1.031** | +0.066 | 44.9% |
| 2016-19 | Unrecovered breach | 604 | +2,221 | **1.260** | +0.059 | 48.5% |
| 2020-26 | Reclaimed current-session low | 930 | +10,380 | **1.280** | +0.091 | 47.0% |
| 2020-26 | Unrecovered breach | 1,020 | -2,508 | **0.955** | -0.007 | 43.4% |

Recent reclaim trades are stronger, but the earlier dollar PF ranking reverses.
Mean net R favors reclaim by only +0.007R in 2016-19 (interval -0.156 to +0.161)
and by +0.098R in 2020-26 (+0.004 to +0.190). Dollar-weighted PF and average
trade R need not rank groups alike.

The corresponding mean MAE is -0.698/-0.697R (reclaim/unrecovered) earlier and
-0.686/-0.718R recently; mean MFE is 1.097/1.023R and 1.012/0.936R. Medians and
yearly values are retained in `trade_groups.csv`.

About 49.0% versus 30.0% of earlier reclaim/unrecovered attempts match a filled
baseline trade, and 45.5% versus 28.9% recently. These are different selected
populations from the all-attempt price response. A failed fill, canceled/replaced
order or later entry must not be silently treated as an executed trade at the
signal close. The logger records order attempts before broker acceptance.

## Robustness and years

The current-session +0.5R probability advantage at 90 minutes is present in
**9 of 11 yearly slices** (including partial 2026); 2024 and 2025 are exceptions.
The mean endpoint-return advantage is present in only 5 of 11. Filled-trade PF
favors reclaim in 8 of 11 years, but not in the pooled earlier period.

| Sensitivity | 2016-19 probability difference | 2020-26 probability difference | 2016-19 mean-R difference | 2020-26 mean-R difference |
|---|---:|---:|---:|---:|
| 30 minutes, >=1 tick | +4.6 pp | +3.7 pp | +0.029 | -0.004 |
| 90 minutes, >=1 tick (primary) | +6.1 pp | +3.1 pp | +0.071 | -0.020 |
| 180 minutes, >=1 tick | +2.4 pp | +1.0 pp | +0.015 | -0.059 |
| 90 minutes, >=2 ticks | +5.9 pp | +3.1 pp | +0.061 | -0.020 |
| 90 minutes, >=4 ticks | +5.9 pp | +3.1 pp | +0.062 | -0.016 |

The probability finding is not solely a one-tick breach artifact, but the mean
return pattern remains mixed. On the common sample eligible for all three level
sources, the primary probability differences are +5.9 pp [+2.1, +9.7] and
+2.3 pp [-0.7, +5.4]; the recent interval then includes zero. Mean differences
are +0.055R and -0.046R. All predefined candidate gates fail; no source or cutoff
was selected after viewing the results.

## Other low sources

- **Previous-session low:** at 90 minutes, +0.5R response rates favor reclaim
  33.0% versus 26.3% earlier and 29.9% versus 27.4% recently; both difference
  intervals include zero. Filled-trade PF flips from 1.565 versus 1.307 to
  0.815 versus 0.994. Reclaim trade counts are only 111 / 195.
- **Previous-week low:** response rates are lower after reclaim in both periods
  (23.9% versus 34.5%, and 25.8% versus 30.0%). Samples are sparse: only 71 / 124
  reclaimed attempts with complete horizons and 23 / 55 filled reclaim trades.
  These do not establish a general rule about weekly levels.

Every no-contact, touch, exact-close, already-below and unavailable group is
preserved in the tables. The `all_fresh_breaches` aggregate overlaps reclaim
and is descriptive, not an independent control. Depth is saved continuously in
ticks/R and summarized in the fixed 1, 2-4, 5-8 and >8 tick bins.

## Verification and limits

- Rebuilt 191,786 M30 bars; exact agreement with the independently built Q6/Q7
  reference. All 3,053,472 candle values in original trade snapshots match.
- Fixed-1R logged trade history matches the 14,968 original baseline trades;
  counts and PnL reconcile with tester stats, with zero export/close errors.
- Audited all **106,896** attempt/source classifications and all **44,904**
  filled-trade/source level rows against the earlier study.
- Independently checked **803** forward windows, including excluded cases.
  All disjoint group counts and trade profit sums reconcile.
- Five Q8 unit tests cover equality, pre-existing breaches, signal/future
  exclusion, horizon endpoints, missing bars, early closes and delayed submission.
  The five shared level-map tests also pass.
- Input/dependency/protocol hashes are saved in `provenance.json`; independent
  checks are saved in `verification.json`. Results are reproducible with:

```powershell
.\venv\Scripts\python.exe python\analyze_breach_reclaim.py
.\venv\Scripts\python.exe python\verify_breach_reclaim.py
.\venv\Scripts\python.exe -m unittest discover -s python -p test_breach_reclaim.py -v
```

This measures further movement after selected RTL signals, not all market
reversals. The measured price response does not identify stop orders, prove
their exhaustion, or establish that the reference levels have a causal effect.
Signal size, close location and time of day may contribute to group differences.
Trade outcomes retain the accepted OHLC execution limitation. No hypothetical
filtered strategy PnL or drawdown is claimed from removing existing trades.
