# RTL warning-based skip rules: frozen protocol

2026-10-25. Written before any RTL outcome of these rules was calculated. The
[warning statistics](../rtl-pullback-stats/RESULTS.md) found bounce warnings
reliable and pullback warnings weak; their fixed rule allowed an RTL test for 5%
drops. The user also asked for a live-zigzag stop with a bounce-warning resume.
Both are causal rules: decided at a session's close, applied from the next session.

## 1. Data, unchanged

The 16,668 verified RTL trades (6,167 in 2016-19, 10,501 in 2020-September
2026), one MNQ-valued contract, $1.05 cost, each trade in its submission
session. Roll-adjusted research-session daily closes (raw closes as
sensitivity), live zigzag and features exactly as in the
[crystal-ball](../rtl-downtrend-oracle/PROTOCOL.md) and
[warning-statistics](../rtl-pullback-stats/PROTOCOL.md) protocols. Signal
cutoffs are that study's saved pre-2016 values (cutoffs.csv), per series.

- Pullback warning: 5-session rise R_5 at or above its 90th-percentile cutoff.
- Bounce warning: R_5 at or below its 10th-percentile cutoff. Primary because it
  mirrors the stop signal; the other five bounce predictors (rise_10, rise_20,
  zscore_5/10/20) are reported as sensitivities.

## 2. Rules

Rule A (fixed rule, 5% drops): trading by default. At a close with a pullback
warning while trading, stop from the next session. While stopped, resume from
the next session after a close with a bounce warning, or after M skipped
sessions with none. M = 20 (about the 90th percentile of 5% falls) is primary;
M = 10 and 40 are sensitivities. Signals of the other kind are ignored while in
a state.

Rule B (live-zigzag stop, bounce resume), x = 2%, 3%, 5%: the live zigzag stops
from the session after a fall of x is confirmed (as in the crystal-ball study).
Resume from the session after the first close, on or after that confirmation,
with a bounce warning, or after the zigzag's own rebound confirmation if that
comes first. A bounce warning on the confirmation close means no sessions are
skipped. After resuming, the next stop needs the next zigzag confirmation.
Comparison: the plain live zigzag at the same x.

## 3. Outcomes and controls (as in the crystal-ball study)

Per rule, series and era: stops, skipped sessions and share, skipped trades;
retained and skipped net dollars and mean net R; gain versus baseline in dollars
and %; losses avoided and profits missed; daily-close and closed-trade drawdown;
static holding-time control; all circular shifts of the era skip mask. Stop
periods are listed with start, end, length and resume reason. Ledger omission,
not an MT5 replay.

## 4. Decision, fixed in advance

A rule is promising if, on roll-adjusted closes, in BOTH eras: retained net
dollars above baseline, retained mean net R above baseline, and retained net
dollars above the 97.5th shift percentile. A promising rule must also keep a
positive dollar gain in both eras under raw closes and, for Rule A, at M = 10
and 40; otherwise it is labelled fragile. Drawdown claims also need to beat the
static control. Primary rules: Rule A (rise_5 bounce, M = 20) and Rule B at each
x with the rise_5 bounce. Four primary rules are compared, so one narrow pass is
weak evidence. A promising rule would still need a full MT5 replay (skipping can
free order opportunities) and fresh data before any live use.

## Verification

Hash this protocol (CRLF-normalized) before outcomes and check it after.
Independent verifier: separately written state machines for both rules, the
first verifier's zigzag, explicit masks, ledger partitions, drawdowns, every
circular shift and the decision. Tests: Rule A timeout and resume, ignored
signals within a state, Rule B same-close bounce (no skip), zigzag fallback,
censored final fall, causality (future closes cannot change past decisions).
Save RESULTS.md, a figure and tables; update plan/status/journal.
