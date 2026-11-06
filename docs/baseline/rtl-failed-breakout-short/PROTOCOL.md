# RTL red-candle failed-breakout short

2026-11-05. User-requested exploratory experiment; frozen before new outcomes.
The user confirmed that the stop references the original red candle and that
the sell stop becomes active immediately when the next candle breaks its high.

## Rule

- A completed red M30 candle (`close < open`) is the signal. While flat, watch
  only the immediately following M30 candle for a bid strictly above its high.
- At the first such quote, submit a sell stop at the original red candle's low,
  with a protective stop at the original red candle's high. Both use the
  existing RTL short convention of zero extra price offset. A touch of the high
  is insufficient. No close-back-inside requirement is added: the subsequent
  reversal through the sell-stop level is the failed breakout.
- The low may have traded before the high breaks. That earlier low is never a
  fill: only quotes after order submission can fill the sell stop. Do not use
  the finished M30 high to prequalify the whole candle.
- An unarmed watch expires at the next M30 boundary. Once submitted, the order
  retains the existing red-short lifetime: green/doji bars leave it resting;
  a new red signal replaces it, even if the new signal never qualifies. Session
  exclusion and flattening cancel it. Only one order/position at a time; a
  watcher is consumed on its first submission attempt and cannot rearm after a
  stop-out within the same candle. Native broker processing precedes the EA's
  new-bar cancellation, as in the control.

## Frozen comparison

Run native MT5 OFF and ON with a separate tester-only EA. OFF must reproduce
the unfiltered **red-candle short** control from
`Reports/gg_red_outside_short_20261021/ggredshort_20261021_control.ini`
byte for byte, including the trade ledger and matching native totals. A green
signal mirror is not the direct control for this red-signal idea.

Keep MNQ-priced continuous NQ (`MNQcontDTBNT20102026_2`), M30, MT5 one-minute
OHLC, one MNQ ($2/point), $1.05 round-turn cost, no run cap or location/range
filter, no VWAP filter, 1R candle-close exit, 01:00-23:30 windows, 23:30 flatten,
fallback and existing early-close calendar. The 1R exit remains a market close
at the next bar's first quote after a completed close reaches entry minus 1R;
it is not a fixed intrabar take profit. Stop levels remain fixed.

Use the same full native date range as the existing control (2016-01-01 to
2026-10-15; available history includes partial October). Report submission
sessions in 2016-19 and 2020 through September 2026 as primary periods, and
pooled 2016-September 2026 descriptively. Exclude October submissions from all
reported research metrics. Do not optimize offsets, RR, expiry or filters.

Report trades, net dollars, gross/net mean R, net PF, win rate, closed-trade
and daily-close drawdowns, annual results, and another $1/$2 per trade in costs.
Assess whether ON is net profitable in both periods, not just whether it loses
less than the control. Record causal signal/watch/arm events and independently
verify timing and order levels against the minute history and native reports.
Freeze input hashes and reconcile native orders/deals/ledger/stats.

This is previously examined history and synthetic within-minute ordering,
not untouched out-of-sample evidence or a live execution test. No baseline or
live-trading defaults are changed.
