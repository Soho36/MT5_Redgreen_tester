# RTL weekly signal gate: frozen protocol

2026-10-25. Written before any outcome was calculated. The user ran RTL on
weekly MNQ bars in MT5 (results not in this repository) and proposed: stop new
M30 RTL trades when the weekly chart gives a sell signal, resume when it gives a
buy signal. Expectation from the earlier studies: signals that confirm a fall
or a rebound tend to arrive late, which was costly; weekly levels have not been
tested, so this is measured, not assumed.

## 1. Data

The 16,668 verified RTL trades (6,167 in 2016-19, 10,501 in 2020-September 2026),
one MNQ-valued contract, $1.05 cost. Weekly bars are built from the verified M30
reference (Reports/trend_rr_20261002/m30_reference.csv, research session from
01:00 on the Chicago + 8 hour clock), source dates through 2026-09-30. A week is
Monday to Friday by source date; open = first M30 open, high/low = extremes,
close = last M30 close. Green: close > open; red: close < open; otherwise doji.

Roll gaps: M30 prices before each contract switch are ratio back-adjusted so the
move from the last bar before the switch date to the first bar on it is zero,
the same adjustment as the crystal-ball daily closes. Raw prices are a sensitivity.

## 2. Gate (primary: intraweek touch)

For each completed week W and the following week W+1:
- Sell signal: W is green and an M30 bar in W+1 has a low below W's low.
- Buy signal: W is red and an M30 bar in W+1 has a high above W's high.
- Only the first such bar counts. The signal takes effect at that bar's close.

The gate starts enabled in 2010. A sell signal disables it and a buy signal
enables it; a signal that matches the current state changes nothing. An RTL
trade is skipped if the gate is disabled after the close of the last M30 bar
completed at its submission time. RTL submits at M30 bar closes, so this uses no
information the strategy could not have had. Open positions are not affected.

Sensitivities (fixed):
- Week-close timing: the same signals, applied from the start of week W+2.
- Close-confirmed: sell if W is green and W+1 closes below W's low; buy if W is
  red and W+1 closes above W's high; applied from the start of week W+2.
- Raw (unadjusted) prices with the primary definition.

## 3. Outcomes and controls

Per variant and era: gate-off periods (count, length in weeks), share of M30
bars and of trades skipped; retained and skipped net dollars and mean net R;
gain versus baseline in dollars and %; losses avoided and profits missed;
daily-close and closed-trade drawdown; static holding-time control.
Placement control: all circular shifts of the era's per-M30-bar gate-off mask
(net dollars by exact circular correlation); share of shifts at least as good,
and the 97.5th percentile. Ledger omission by submission time, not an MT5
replay: a real gate could also cancel pending orders and free new ones.

## 4. Decision, fixed in advance

The gate is promising if, with the primary definition on adjusted prices, in
BOTH eras: retained net dollars above baseline, retained mean net R above
baseline, and retained net dollars above the 97.5th shift percentile. It is
robust only if the dollar gain also stays positive in both eras under all three
sensitivities; otherwise a pass is labelled fragile. Drawdown claims also need
to beat the static control. A promising gate would still need an MT5 replay and
fresh data before live use.

## Verification

Hash this protocol (CRLF-normalized) before outcomes and check it after.
Independent verifier: weekly bars, colours, signal bars and times, gate states
with separately written loops; trade labels, ledger partitions, drawdowns, all
circular shifts by direct summation, and the decision. Tests: first-touch
timing, doji weeks, repeated signals in the same state, week-close and
close-confirmed timing, roll adjustment, causality (future prices cannot change
past gate states).
