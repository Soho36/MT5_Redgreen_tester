# RTL downtrend crystal ball, early signals: frozen addendum

2026-10-25. Written before any early-timing outcome was calculated. Addendum to
the [frozen protocol](PROTOCOL.md); everything not stated here is unchanged
(trades, daily closes, roll adjustment, zigzag, sizes, eras, metrics, controls).
The user asked whether "up N% over n sessions, so a pullback is likely soon" is
worth building. A predictor like that acts before the turn, so this sets the
ceiling for being early, as the first study did for being late.

## Rules (P = peak session, T = trough session, positions in the session list)

- Early by e sessions, e = 1, 2, 3, 5: skip sessions P+1-e through T-e. Both stop
  and resume come e sessions too soon.
- Early stop, on-time resume, e = 1, 2, 3, 5: skip sessions P+1-e through T.
  This assumes the end of each drop is still known perfectly, so it is the most
  favourable case for an early warning.
- Reference: the on-time crystal ball (P+1 through T), recomputed here.
Windows are clipped at the first session. Overlapping windows (a rally shorter
than e) are merged; a session is skipped once.

## Outcomes and controls

Same as the first study: retained and skipped trades, net dollars, mean net R,
gain versus baseline in dollars and %, drawdowns, static holding-time control
and all circular shifts of the era skip mask. Both series (roll-adjusted primary,
raw sensitivity), both eras.

## Decision, fixed in advance

A pullback-anticipation statistic (the user's step 2) is worth building only if,
for some size, an early rule with e >= 2 (either kind) keeps retained net
dollars above baseline AND above the 97.5th shift percentile in BOTH eras on the
roll-adjusted series. A probabilistic "pullback soon" signal cannot plausibly
place the peak within one session. Passing is necessary, not sufficient: a real
predictor errs both early and late, and late was already shown to fail.
Otherwise step 2 is not worth building for RTL on NQ.

## Verification

Hash this addendum (CRLF-normalized) before outcomes and check it after.
Independent verifier reuses the first study's separately written zigzag,
rebuilds the early masks from explicit session ranges, and recomputes ledger
partitions, drawdowns, every circular shift and the decision. Tests: clipping at
the first session, merged overlaps, e=0 equals the on-time rule.
