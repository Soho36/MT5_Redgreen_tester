# RTL weekly signal gate: switching off on weekly sells cuts profit by half or more

2026-10-25. Exploratory test of the user's weekly gate. [Frozen protocol](PROTOCOL.md) |
[Crystal ball](../rtl-downtrend-oracle/RESULTS.md) | [Warning rules](../rtl-warning-rules/RESULTS.md)

**The weekly gate makes RTL clearly worse in every version and era.** It is off
33-45% of the time and cuts net profit by 52-85%. In 7 of 8 version/era cases
the trades it skips are better than the ones it keeps; in 2020-26 with the
primary definition, +0.061 R versus +0.037 R per trade. Random time off of the same pattern does at least as well in
70-99.5% of placements. Not promising under the fixed rule. No strategy defaults
or live settings changed.

## The gate

Weekly bars are built from the M30 data (Monday to Friday, research session),
roll-adjusted like the earlier studies.
- **Sell:** last week was green, and this week trades below last week's low.
- **Buy:** last week was red, and this week trades above last week's high
  (RTL's own entry, on weekly bars).

A sell switches new M30 RTL trades off and a buy switches them back on, from the
close of the M30 bar where the level breaks (primary: "touch"). Sensitivities:
the same signals applied from the next week's start; a stricter version needing
the week to close beyond the level; and unadjusted prices. Open positions are
unaffected. The user's own weekly MT5 run was not repeated here: whether weekly
RTL makes money is a different question from whether weekly sells mark bad
times for M30 RTL.

## Results

| Version | Era | Profit change | Time off | Off periods / median weeks | Skipped trades, mean R | Kept trades, mean R |
|---|---|---:|---:|---|---:|---:|
| Touch (primary) | 2016-19 | -85% | 34% | 21 / 2 | +0.007 | -0.025 |
| Touch (primary) | 2020-26 | -57% | 44% | 29 / 3 | +0.061 | +0.037 |
| Week-close timing | 2016-19 | -54% | 33% | 20 / 2 | -0.009 | -0.017 |
| Week-close timing | 2020-26 | -62% | 43% | 30 / 3 | +0.057 | +0.041 |
| Close-confirmed | 2016-19 | -52% | 36% | 10 / 4.5 | +0.009 | -0.027 |
| Close-confirmed | 2020-26 | -75% | 40% | 16 / 7 | +0.070 | +0.032 |
| Touch, unadjusted | 2016-19 | -85% | 34% | 21 / 2 | +0.007 | -0.025 |
| Touch, unadjusted | 2020-26 | -53% | 45% | 27 / 4 | +0.050 | +0.046 |

All trades average -0.014 R / +0.048 R. With the primary gate, 2016-19 net
profit falls from $4,417 to $650 and 2020-26 from $38,400 to $16,548. It is not a
risk reduction either: 2016-19 daily-close drawdown rises ($2,376 versus
$2,143), and in 2020-26 it is worse than simply trading smaller at the same
exposure ($3,435 versus $3,224).

![RTL with and without the weekly gate](../../../Reports/rtl_weekly_gate_20261025/gate.png)

## Why it fails

- **Weekly sells mark good times for RTL, not bad ones.** RTL buys above red M30
  candles, so it profits from pullbacks that bounce. Weekly sell periods are full
  of such pullbacks, with high volatility and large dollar wins. The shaded
  periods in the figure include several of RTL's strongest stretches, such as
  late 2018 and February to August 2026.
- **Both signals are late.** A sell needs a green week followed by a break of its
  low, so it comes after a fall has started; consecutive red weeks never trigger
  it. In early 2020 the gate missed the first crash week. It switched off on
  March 9 and back on on March 26, near the low. A buy needs price to clear a red
  week's high, so it comes after the rebound is under way. The
  [crystal-ball study](../rtl-downtrend-oracle/RESULTS.md) showed that late
  stops and late resumes are the costly combination.

## In context

None of the direction-based switches tested so far has helped RTL: daily trend
groups, the live zigzag, the warning-based rules, and now the weekly gate. The pattern is consistent: periods that look bearish on a higher
timeframe contain many of RTL's best trades, because it is a buy-the-dip entry.

## Limits

Ledger omission by submission time, not an MT5 replay; a real gate could also
cancel pending orders. Weekly bars use the research session, which can differ
from a broker's weekly candles. All history has been used before; exploratory.

## Verification and reproducibility

Protocol SHA256 (CRLF-normalized):
`28fccc0ca54af3621c295828f1272976728633d2e24024a7e764a668e704d2f6`, checked before
and after. **Independent verification: PASS** (9 of 9): weekly bars, signals and
gate states by explicit loops; roll adjustment by backward factor accumulation;
submission-bar mapping and trade labels; ledger partitions and drawdowns; every
circular shift by prefix sums over gate-off runs (no FFT); and the decision.
**All 9 focused tests pass**: first-touch timing, doji weeks, repeated signals,
both delayed versions, roll adjustment, submission mapping, the shift formula and
causality.

- `python/analyze_rtl_weekly_gate.py`, `python/verify_rtl_weekly_gate.py`,
  `python/test_rtl_weekly_gate.py`, `python/report_rtl_weekly_gate.py`.
- Outputs: `Reports/rtl_weekly_gate_20261025/`;
  [calculated tables](../../../Reports/rtl_weekly_gate_20261025/report_tables.md).
