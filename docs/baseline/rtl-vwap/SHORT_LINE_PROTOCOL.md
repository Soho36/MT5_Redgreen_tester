# RTL short: blue VWAP versus orange VWAP - A20

2026-10-31. User-requested follow-up to [the orange-line test](SHORT_RESULTS.md).
Freeze before inspecting new blue-line outcomes. This is reused history,
not untouched out-of-sample testing. No threshold search.

Add VwapFilterLine to the existing RTL_short_vwap EA:
- 0 = Orange cutoff, close < VWAP + VwapFarBelowZ * A20 (default Z=-1).
- 1 = Blue session VWAP, close < VWAP.

The switch changes eligibility only. The signal stays a green completed M30
candle, with a sell stop at its low and stop at its high. No order is placed
at the VWAP price itself. Both drawn lines retain their existing definitions.
Keep equality and unknown/stale labels ineligible, cancellation before the
gate, existing pending-order/position management, no run cap, 1R bar-close
exit, session windows, early closes and flatten/fallback unchanged. A20
availability remains part of the shared known-label rule, even in blue mode.

Use native MT5, 1-minute OHLC, one MNQ ($2/point), $1.05 per completed trade,
the same symbol/history and frozen real-volume causal label file. Every input
is written explicitly. Tester-only EA guard stays enabled.

First run orange with the switch EA. It must reproduce the original ON
ledger byte for byte and the native totals before running blue. Verify every
blue and orange candidate decision and every original sell-stop order against
the label file, reconcile reports and ledgers, and preserve frozen hashes.

Primary periods: 2016-19 and 2020 through September 2026 by submission session.
2010-15 and pooled 2016-26 are descriptive. Compare unfiltered short, original
orange gate, and blue gate on trades, net dollars, gross/net mean R, net PF,
daily-close and closed-trade DD, annual results, and extra $1/$2 costs. Include
four-week block-bootstrap intervals as uncertainty diagnostics. Show summed
gated RTL-long + each short leg descriptively, one MNQ per independent leg,
without netting; this is not a switching or netting-account execution test.

Positive net dollars in both primary eras is a minimal screen. Assess cost
robustness, per-R expectancy and drawdown alongside it. No automatic live
adoption or baseline change.
