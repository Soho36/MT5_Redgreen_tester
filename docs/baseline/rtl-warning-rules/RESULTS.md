# RTL warning-based skip rules: nothing beats trading every session

2026-10-25. Exploratory RTL test of the [warning statistics](../rtl-pullback-stats/RESULTS.md).
[Frozen protocol](PROTOCOL.md) | [Crystal ball](../rtl-downtrend-oracle/RESULTS.md) |
[Early signals](../rtl-downtrend-oracle/EARLY_RESULTS.md)

**Neither rule improves RTL; all four primary rules are "not promising" under
the fixed rule.** Rule A (stop after a big 5-session rise) sits out 37-47% of
sessions and loses half of 2020-26 profit. Rule B (stop when the live zigzag
confirms a fall, resume at the first bounce warning) repairs most of the plain
zigzag's damage, but still loses at 2% and 3% drops; at 5% it barely skips
anything. No strategy defaults or live settings changed.

## The rules

Both decide at a session's close and act from the next session.

- **Rule A (fixed rule, 5% drops):** stop when the 5-session rise is in the top
  10% of pre-2016 rises (at least +3.1%). Resume after the first close with a
  bounce warning (5-session move at most -2.5%), or after 20 skipped sessions.
- **Rule B (2%, 3%, 5%):** stop after the live zigzag confirms a fall of that
  size. Resume after the first close, from the confirmation on, with a bounce
  warning, or after the zigzag's rebound confirmation if that comes first.

Sensitivities: the other five bounce signals, timeouts of 10 and 40 sessions
(Rule A), and unadjusted closes.

## Results

Change in net profit versus trading every session, roll-adjusted closes:

| Rule | 2016-19 | 2020-26 | Sessions skipped | Stops (2016-19 / 2020-26) | Median stop, sessions | Plain live zigzag |
|---|---:|---:|---:|---:|---:|---:|
| A: pullback stop, bounce resume | +7% | -51% | 37% / 47% | 23 / 63 | 20 / 14 | - |
| B, 2%: zigzag stop, bounce resume | -22% | -15% | 11% / 15% | 44 / 123 | 2 / 2 | -82% / -42% |
| B, 3% | -7% | -17% | 4% / 6% | 25 / 76 | 0 / 0.5 | -63% / -58% |
| B, 5% | +6% | +0% | 0.3% / 0.8% | 12 / 39 | 0 / 0 | -63% / -49% |

None beats 97.5% of the same time off placed at random. Only Rule B at 5% raises
net profit and average R in both eras, by $251 and $76, because it skips almost
nothing. Across all 18 Rule A variants, 2020-26 loses
40-51% under either price series. Rule B at 2% loses in every variant and era.
A few Rule B 5% variants are slightly positive in both eras, but they skip under
5% of sessions, too little to tell apart from trading every session.

![Warning rules versus trading every session](../../../Reports/rtl_warning_rules_20261025/rules.png)

## Why the signals did not turn into profit

- **Rule A stops in rallies that keep going.** The pullback warning is mostly a
  false alarm (statistics study), so most stops land in continuing rallies. 38
  of 86 stops since 2016 ran to the 20-session timeout. Rally sessions are RTL's best
  sessions, so skipping them costs heavily.
- **Rule B skips the wrong part of the fall.** The bounce warning does find lows,
  which is why Rule B loses far less than the plain zigzag: it gets back in near
  the bottom instead of after the rebound. But the costly RTL sessions are the
  first ones after the peak, before any fall can be confirmed. By the time a 2%
  fall is confirmed, the rest of it is short. The sessions Rule B still skips
  were not bad for RTL: +0.046 / +0.005 R per trade, against -0.014 / +0.048 R
  for all trades.
- **At 5% the warning is already on.** When a 5% fall is confirmed, the price has
  usually just fallen at least 2.5% in five sessions. 77-83% of stops are
  cancelled the same day, so Rule B at 5% is close to trading every session.

## A side observation on risk

Rule B at 2% gives a better profit-to-drawdown ratio than trading every session:
2.35 versus 2.06 in 2016-19 and 8.1 versus 6.6 in 2020-26. Recently it earns the
same as simply trading smaller at equal exposure ($32,815 versus $32,751) with a
lower daily-close drawdown ($4,051 versus $4,931). In 2016-19 it earns less than
that control. This is a modest risk-reduction hint, like the daily-chop hint in
the [structure study](../rtl-price-structure/RESULTS.md), not a pass: random time
off of the same shape earned as much in about half or more of the placements.

## What this series of studies shows

Perfect hindsight timing of daily downtrends would help RTL a lot. Real
detectors do not get there: confirming a fall is too late, and the only early
warning available from rises fires mostly in rallies that continue. The bounce
warning is a genuine statistical finding about NQ lows, but RTL's losses sit at
the start of falls, where no signal tested here arrives in time. For RTL on NQ,
daily downtrend filtering looks exhausted.

## Limits

Ledger omission by submission session, not an MT5 replay; skipping can free
order opportunities. Four primary rules and many variants were compared. All
history has been used before; exploratory only.

## Verification and reproducibility

Protocol SHA256 (CRLF-normalized):
`39522fbe9a34172e17c71ca575ed11528cfe09b2f95687d3fc8a50cd25dc8d35`, checked before
and after. **Independent verification: PASS** (7 of 7, all 156 rule/era rows):
separately written event scans for both rules, loop-built features, the first
verifier's zigzag, ledger partitions, drawdowns, every circular shift and the
decision. **All 9 focused tests pass**, including timeouts, same-day
cancellations, the zigzag fallback, the censored final fall and causality.

- `python/analyze_rtl_warning_rules.py`, `python/verify_rtl_warning_rules.py`,
  `python/test_rtl_warning_rules.py`, `python/report_rtl_warning_rules.py`.
- Outputs: `Reports/rtl_warning_rules_20261025/`;
  [calculated tables](../../../Reports/rtl_warning_rules_20261025/report_tables.md).
