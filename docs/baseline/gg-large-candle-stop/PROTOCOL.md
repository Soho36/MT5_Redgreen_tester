# GG: midpoint stops on unusually large session candles

Frozen 2026-11-09 before results. Exploratory user-requested research.

## Question and rule

Does reducing the stop distance on a conspicuously large green GG signal improve
the full strategy? The screenshot motivates the hypothesis, not a fitted
threshold or an identified historical trade.

- Existing unfiltered, uncapped GG M30 on MNQcontDTBNT20102026_2, one contract,
  $2/point. Signal size is high minus low, including wicks.
- Reference is the median range of all earlier completed M30 candles in the same
  full trading session, both colours, excluding the signal and future bars.
  Existing research clock: 01:00 through midnight on one calendar date, not
  only the US cash session. Require five earlier bars and a positive median.
  Include zero-range prior bars. Do not tighten prior-session signals.
- Trigger: range >= 3.0 times median. Predeclared neighbours: >= 2.5 and >= 3.5.
  These are lower bounds, not equality or a band excluding still larger candles.
- Triggered stop = (high + low)/2, nearest tradable tick, ties upward, at least
  one tick below entry. Other stops remain at low.
- Entry stays at the signal high, exactly as in GG; no added entry offset.
- Per the user's answer, the profit-exit threshold moves closer too: RR=1 using
  entry minus new stop, same candle-close exit, not resting intrabar TP.
- Same session flattening, early closes, pending orders and other inputs.
  No size increase, VWAP gate, time exclusion, or live-default change.

## Runs and checks

Four full native MT5 one-minute-OHLC runs: disabled control and three triggers.
Freeze protocol/source/INI hashes. Disabled control must reproduce saved GG.
Independently reconstruct every decision from raw minute bars aggregated to M30,
check filled-order levels, native report and ledger economics. Sample native
equity; full-run gross DD must match MT5. Deduct $1.05 per completed position.

Report 2016-19, 2020-September 2026, pooled 2016-September 2026, secondary 2010-15,
and annual results. October source tail is audited but excluded from primary
tables. Report net dollars, average net R using actual risk, PF, win rate,
equity DD, worst-session DD, affected fills and risk distances. Add $1 and $2
cost stress. Full replay captures changed subsequent opportunities. No edits
to old trade results; R normalization is not a tested sizing strategy.

## Interpretation fixed in advance

Primary is net dollars relative to native equity DD at one contract; net R is
secondary. Promising requires improved net/DD in both main eras without lower
profit in either, with the same direction at neighbouring triggers. Otherwise
report the trade-off or failure, not the best threshold. Historically reused
samples are not untouched out of sample. OHLC is the agreed screening model;
no generated-tick expansion. No automatic adoption or claim about real fills.

