# GG: size cap on outsized signal candles

Frozen 2026-11-11 before any run. Exploratory, user-requested.

## Question and rule

Does skipping GG signals whose candle is far larger than the session's typical
bar reduce the strategy's risk without costing profit? This is a risk rule
(limit the largest single bets). It is not a claim that such trades can be
predicted to lose.

- Existing unfiltered, uncapped GG M30 on MNQcontDTBNT20102026_2, one contract,
  $2/point, RR 1.
- Signal size and reference exactly as in the 2026-11-09 midpoint-stop study:
  high minus low including wicks, against the median range of all earlier
  completed M30 candles of the same full research session (01:00 to midnight on
  one calendar date), both colours, excluding the signal and later bars. At
  least five earlier bars and a positive median are required; otherwise the
  signal is never capped. A previous session's last candle used as the next
  session's first signal is never capped.
- Cap: range >= k x median rejects the signal. No buy stop is placed and any
  pending buy stop is cancelled, exactly as the EA already treats a green
  signal rejected by its other filters. Still larger candles are capped too
  (a lower bound, not a band).
- Primary k = 5. Fixed neighbours k = 4 and k = 6.
- Everything else unchanged: entry at the signal high, stop at its low, 1R
  candle-close exit, 23:30 and early-close flatten, order handling. No VWAP
  gate, no size change.

## Where 5 comes from

5x was chosen on 2026-11-11 after ledger cuts of this same history
(python/explore_gg_session_filters.py): removing trades of 5x or more left
profit about unchanged and daily DD 7-13% lower. 4x and 6x were written down
with it, before this replay. The replay can refute the idea: freed entries may
lose, and the neighbours may disagree. A pass on reused history is a reason
for a forward trial, not confirmation.

## Runs

Two arms, four native MT5 one-minute-OHLC runs each: cap off (control), 4x, 5x, 6x.

1. Primary arm: all entry windows on (the research baseline).
2. Secondary arm: entries at 16:00 and 16:30 disabled (`W1600W1700=false`),
   the window setting studied on 2026-11-01. Reported next to the primary; it
   cannot rescue a failed primary.

Checks. Frozen protocol, source and INI hashes. The primary control must
reproduce the saved GG ledger byte for byte, and the secondary control the
saved GG exclude16-17 ledger byte for byte. Every logged candidate decision is
rebuilt from raw minute bars aggregated to M30. Every native trade is matched
against an independent minute replay: entry and exit minute, requested, stop,
fill and exit price, submission bar. No accepted order may come from a capped
signal. Ledger and report economics must agree, and sampled gross equity DD
must equal MT5's. $1.05 per completed position, plus $1 and $2 stress.

## Reporting

2016-19, 2020-September 2026, pooled 2016-September 2026, secondary 2010-15,
and annual results. The October source tail is excluded. Net dollars, mean net
R, PF, win rate, sampled equity DD after costs, worst-session DD, largest
initial risk, worst single trade, capped signals, and the split of the profit
change into control trades that disappear and trades that exist only with the cap.

## Interpretation fixed in advance

The cap is supported as a risk rule only if, at 5x on the primary arm, both
main eras show lower sampled equity DD and higher net/equity-DD than the
control, and neither neighbour contradicts it: net/equity-DD at 4x and at 6x
not below the control in either main era. Lower net profit does not by itself
fail a risk rule; it is reported and is the user's to weigh. Anything else is
reported as a trade-off or a failure, without picking the best threshold.
No automatic adoption and no live or default setting change. One-minute OHLC
is the agreed screening model; no claim about real fills.
