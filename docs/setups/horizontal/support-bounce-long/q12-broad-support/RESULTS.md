# Q12: every red candle contacting support-origin levels

2026-10-04 · [Protocol](PROTOCOL.md) ·
[Analysis](../../../../../python/analyze_broad_support.py) ·
[Eligibility code](../../../../../python/broad_support.py) ·
[Full tables](../../../../../Reports/levels/broad_support_20261004/report.md)

**Broad contact does not consistently identify better RTL trades.** Rolling
swing-low contacts beat the remaining signals in 2016-2019 but underperform in
2020-2026, across all three fixed swing settings. No broad filter is supported.
Previous-week-low contact remains a separate, small-sample lead; this study
does not establish that support levels in general are useful or useless.

## What changed

At the user's request, every known swing-low level remains eligible throughout
its rolling window regardless of previous breaks. A red signal qualifies when
its range overlaps the level's zone. No prior departure, approach-from-above,
maximum penetration, or open/close-side requirement. This includes Q11's intact
revisits, deep slices, previously broken contacts and not-departed contacts.
Q11's historical classifications and findings are preserved, not rewritten.

Primary source: confirmed M30 swing lows, N=5, current session plus five prior
sessions, merged as in Q11, zone +/-0.5 of lagged ATR(14). Two weeks/N=5 and one
week/N=3 are fixed sensitivities. Zones can include near misses of the exact
price. Age, causal confirmation and contract-roll exclusions still apply;
merging/zone width still use the signal's lagged ATR. Removing the broken state
does not make the map permanently static.

The secondary session/week definitions instead require literal range contact:
signal low <= known low <= signal high. They include opens at/below the level,
but exclude candles lying entirely below it. Each source is reported separately.

Outcomes use the original RTL exit (bar-close-qualified >=1R, not fixed TP),
$1.05 round-trip cost and the existing signal/order/position rules. All 52,070
qualifying red signals are classified, including unsubmitted and unfilled ones;
actual returns exist for the baseline's 14,968 fills. MaxRedRun=3 and the existing
enabled session windows still define the population.

## Primary rolling swing-low comparison

| Period | Group | Potential signals | Attempts | Fills | Fill/attempt | Net $ | PF | Mean net R |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2016-2019 | Contact | 10,232 | 7,306 | 2,995 | 41.0% | 4,953.25 | 1.137 | +0.009 |
| 2016-2019 | Every other | 9,392 | 6,116 | 2,702 | 44.2% | 1,531.90 | 1.061 | -0.019 |
| 2020-2026 | Contact | 17,118 | 12,225 | 4,929 | 40.3% | 18,112.05 | 1.084 | +0.046 |
| 2020-2026 | Every other | 15,328 | 9,985 | 4,342 | 43.5% | 19,868.90 | 1.143 | +0.076 |

Contact covers 52-53% of potential signals and filled trades. This is no longer
the small, restrictive Q11 subset. Win rates are 44.3% vs 42.4% earlier and
43.1% vs 42.9% recently; a slightly higher win rate does not imply higher PF or R.

| Setting | Period | PF difference [95% interval] | Mean R difference [95% interval] |
|---|---|---:|---:|
| One week, N=5 | 2016-2019 | +0.076 [-0.062, +0.224] | +0.028 [-0.039, +0.096] |
| One week, N=5 | 2020-2026 | -0.059 [-0.188, +0.078] | -0.029 [-0.074, +0.018] |
| Two weeks, N=5 | 2016-2019 | +0.106 [-0.036, +0.245] | +0.015 [-0.048, +0.078] |
| Two weeks, N=5 | 2020-2026 | -0.056 [-0.192, +0.086] | -0.024 [-0.075, +0.031] |
| One week, N=3 | 2016-2019 | +0.116 [-0.053, +0.270] | +0.037 [-0.038, +0.112] |
| One week, N=3 | 2020-2026 | -0.019 [-0.156, +0.112] | -0.023 [-0.073, +0.028] |

Differences are contact minus every other; 2,000 paired calendar-month
resamples. All these intervals include zero. Primary average R beats the rest
in 5/11 years (sensitivities 4/11 and 5/11), below the specified 7/11 gate.

Excluding unavailable signals from the comparator does not rescue the result:
available no-contact PF is 1.097 / 1.191 and mean R -0.016 / +0.088. Contact's
mean-R difference becomes +0.025 / -0.042, also uncertain. Thus the period
reversal is not caused solely by putting roll exclusions in the complement.

During the recent baseline's largest closed-equity drawdown, contact trades
contribute -$4,660.95 of -$4,847.40, despite being 53% of fills. Earlier they
contribute -$733.70 of -$1,435.30. This is attribution within the existing trade
sequence, not an estimate of a contact-only strategy's drawdown.

## Session and calendar-week lows: separate context

These use exact price contact rather than the swing-low ATR zones.

| Level source | Contact fills, earlier / recent | PF contact/rest, earlier | PF contact/rest, recent | Mean R difference, earlier / recent |
|---|---:|---:|---:|---:|
| Current session low | 1,227 / 2,018 | 1.172 / 1.081 | 1.083 / 1.115 | +0.095 / -0.024 |
| Previous session low | 307 / 523 | 1.351 / 1.084 | 0.965 / 1.122 | +0.140 / -0.034 |
| Previous week low | 101 / 175 | 1.261 / 1.101 | 1.386 / 1.098 | +0.203 / +0.014 |

Current/previous-session comparisons also reverse between periods. The previous
week remains positive on both point estimates, with mean R better in 8/11 years,
but fewer than 200 contact fills in either period. Its mean-R difference interval
is [+0.009, +0.393] earlier and [-0.153, +0.210] recently; both PF difference
intervals span zero. These are exploratory, unadjusted comparisons.

Broadening Q10's previous-week definition adds 29 / 38 fills opening at or below
the level. Those added trades have average R -0.072 / -0.125. Overall weekly
PF falls from Q10's 1.707 / 1.451 to 1.261 / 1.386, and the recent mean-R
advantage shrinks from about +0.069 to +0.014. These are overlapping populations,
not independent replications; the added subgroup is descriptive, not a new
rule to exclude it. A calendar-week extreme remains a different hypothesis
from the much larger set of rolling swing lows.

## Interpretation and decision

Keeping historically broken levels eligible is a valid way to test the user's
broad idea without assuming a particular rejection pattern. It substantially
increases coverage, but does not produce a stable long-trade advantage. This
study measures trading outcomes; it does not measure whether levels attract
more price activity or prove that stop orders cause the behavior seen on charts.

The primary and both sensitivities fail the specified follow-up rule. Preserve
the evidence and leave RTL unchanged. No new shape/depth/break filter is selected
from the breakdown. The weekly-extreme observation remains inconclusive.

This answers the broad selection question for these defined levels and the
existing RTL fills. A filtered strategy could alter subsequent pending orders
and position availability; these subset totals are not a complete backtest of
that strategy. No untouched data remains, and the existing minute-OHLC execution
limitation still applies. No new MT5 run was needed for this screen.

## Verification and reproducibility

- All 19 upstream manifest entries matched; missing/changed inputs now stop
  this new runner rather than merely lowering a match counter.
- Independently recomputed all 156,210 swing signal/settings from M30 prices;
  every result matched the union of Q11's four contact categories.
- Rebuilt all three session/week maps; levels and availability matched Q10 for
  another 156,210 signal/source rows.
- All 12 definition/period partitions reconcile to 52,070 unique potential
  signals, 35,632 attempts and 14,968 fills, with net $6,485.15 / $37,980.95.
- Eight focused tests cover unrestricted contact, both zone boundaries,
  confirmation, future-data invariance, expiry, roll/ATR exclusions, exact
  contact and failed input verification.
- Generated ledgers, tables, yearly metrics, contrasts, verification and input/
  output hashes: `Reports/levels/broad_support_20261004/`. Generated reports remain
  local and Git-ignored; code, protocol, tests and this results document are versioned.
