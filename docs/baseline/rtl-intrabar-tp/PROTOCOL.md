# RTL MNQ: candle-close 1R plus resting 2R take profit

Frozen 2026-10-27 before computing outcomes. User-requested exploratory experiment.
"1/2" is interpreted as risk:reward 1:2 (+2R); the parameter remains configurable.

Compare the unchanged M30 RTL baseline (completed candle close >= +1R, exit at
next bar's first bid) with the same strategy plus an attached sell take profit
at entry + 2 x initial entry-to-stop risk. The first exit wins. All other entry,
stop, order replacement, window, session flatten/fallback and early-close rules
stay the same. No VWAP filter, no red-run cap, one MNQ, $2 per point.

Use the existing raw continuous NQ minute history and MT5 1-minute OHLC ordering.
A touched limit fills at its specified level, including overshoots; no filling at
the candle high. Stop/target ordering follows the generated minute path, including
entry minutes; pre-entry prices cannot close a later position. A broker TP at the
first tick of a chart bar precedes the EA callback. Rounding, if needed, is upward
to a valid tick. At 2R the MNQ quarter-point grid already gives valid levels.

Replay the full strategy so changed exits affect new entries. First reproduce the
saved baseline trade by trade: entry/exit minute, requested price, fill, stop,
exit price. Additional simulator trades before MT5's first trade are excluded.
Primary periods: 2016-19 and 2020 through 2026-09-30 (exclude incomplete October).
2010-15 is a reference only. Cost = $1.05 per completed round turn, also report
+$1 and +$2 cost stress, annual results, exit counts, holding time, gross/net R,
net profit, PF and net closed-trade and daily-close drawdown. Neither is floating
equity drawdown. No parameter search or automatic baseline adoption.

Add synthetic checks for entry-minute touch, a wick touching 2R then reversing,
close-confirmed 1R before 2R, stops and flattening, and no TP when disabled.
Prepare a separate tester-only EA from the hashed frozen RTL_timeframe source;
retain ManageOpenPosition unchanged and attach TP to the pending buy stop.
Compile and compare its trades with the simulator if a historical tester is
available without interrupting the user's running session. Record limitations.
