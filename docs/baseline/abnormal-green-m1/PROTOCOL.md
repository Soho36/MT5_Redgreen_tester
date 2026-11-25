# Abnormally large green M1 breakout

Frozen 2026-11-24 before inspecting outcomes. Exploratory Python OHLC screen on
extended continuous NQ, June 2010 through November 13, 2026. One MNQ, $2/point,
$1.05 round-trip cost. No live/default changes.

- Green: close > open. Size: high minus low, including wicks.
- Signal range >= 10 times the arithmetic mean of the preceding 20 completed
  M1 ranges, both colours, including zero ranges. Exclude the signal itself;
  require a positive mean. Export all detected signals, including exclusions.
- Trading requires all 21 bars to be consecutive minutes within one research
  session, and an available next minute. No news/calendar selection filter.
- After close, arm a buy stop at the high, SL one 0.25-point tick below the low.
  At a next open already at/above the high, enter at that worse opening price.
  Otherwise fill at the high on its next touch.
- User confirmed immediate intrabar TP at actual entry + (actual entry - SL).
  Pending persists until filled, replaced by a newer eligible abnormal green
  signal, or session cutoff. Ordinary candles do not replace it. A low touch
  before entry does not cancel it.
- One position. Signals completed while holding are logged busy, not queued.
  No re-entry from a consumed signal. At a minute open, handle cutoff, then
  arm the completed signal if flat, then process price; existing pending can
  be replaced before its open-price fill. This is the screen's explicit order.
- Cancel pending and flatten at 23:30 / existing early-close cutoff, at first
  available open. Missing cutoff uses first subsequent open, flagged as a gap.
  Mark any final open position at the final close, explicitly labelled.
- Gap stops fill at the worse open; targets at target without gap improvement.
  OHLC is the trigger/valuation price; no separately simulated bid/ask spread.
  Add $1 and $2 per completed trade as cost/execution stresses. This is not a
  native MT5 run or verification of real execution during news.
- Primary path O-L-H-C for rising minutes, O-H-L-C for falling, project doji
  convention. Also replay all-low-first and all-high-first paths; sensitivities,
  not formal upper/lower bounds. Track entry/SL and SL/TP same-minute overlap.
- Keep 10x if >=100 eligible signals since 2016. Only if fewer, also run 7.5x,
  then 5x if still needed. Sample-size decision only, never profit selection.

Report full scan counts/exclusions, eras 2010-15, 2016-19, 2020-Sep2026,
Oct-Nov2026 tail and pooled, annual metrics, fills, net win rate, PF, dollars,
mean net R, closed-trade and marked OHLC-path equity DD, execution stress,
pending age and ambiguity. Save signal/trade ledgers, source hashes and tests.
Price alone does not identify news causes. Historical samples are exploratory.
