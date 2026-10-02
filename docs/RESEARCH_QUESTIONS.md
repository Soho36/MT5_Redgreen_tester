# Preceding-candle research checklist

Created 2026-09-30. These are hypotheses, not promised improvements. Investigate
one at a time, retain negative findings, and link each completed study here.
Research baseline: `MaxRedRun=3`, `MinLocation=0`, original entry/exit rules.

## Q1. Can a small green interruption hide a continuing decline?

- [x] Complete first diagnostic study: [results](PRECEDING_CANDLES_RESULTS.md).
  Recent N=10–20 weakness did not replicate in 2015–2019; no filter adopted.
- Question: does a short consecutive red run still perform poorly when the
  surrounding bars show a longer interrupted decline?
- Measure red-bar share and downward close-to-close share among N preceding
  bars, alongside the existing consecutive red-run count.
- Example: six reds, one small green, then two reds passes the run cap.
- First study uses the explicit density proxy in the
  [protocol](PRECEDING_CANDLES_PROTOCOL.md); it does not yet distinguish the
  body size of the interrupting green bar.
- Follow-up only if justified: distinguish a small green interruption from a
  substantial recovery, using a definition fixed before examining outcomes.

## Q2. Did price recover after breaking an earlier low?

- [x] Complete first diagnostic study: [results](PRECEDING_CANDLES_RESULTS.md).
  PF rankings reverse across periods; no recovery requirement adopted.
- Separate no new low, new low with no recovery, and new low with the signal
  closing back above the preceding N-bar low.
- The old `sweep` feature detects the breach only; it never required recovery.
- All information is known when the signal closes. Do not use what happens
  after order placement to classify the entry.
- Definitions and equality cases: [protocol](PRECEDING_CANDLES_PROTOCOL.md).

## Q3. Were preceding bars overlapping or progressing steadily?

- [x] Answered 2026-10-02: [Q3 results](Q3_OVERLAP_RESULTS.md). No overlap/direction group
  loses in both periods at N = 5/10/20; no filter. Overlap is barely correlated with
  `trend_eff` (new information), but it doesn't predict outcomes consistently.
- Measure adjacent high-low range overlap alongside net price movement.
- Motivation: repeatedly crossing the same prices differs from a rising or
  falling staircase, even with similar final location and overall range.
- Before starting: define the normalization, treatment of zero-range bars,
  and whether the signal participates. Avoid duplicating `trend_eff` without
  demonstrating additional information.

## Q4. Is the immediate pullback opposed to the broader move?

- [x] Answered 2026-10-02: [Q4 results](Q4_CONTEXT_RESULTS.md). All 4 older/recent direction
  groups are profitable in both periods at (5, 20), (3, 10) and (10, 40); no filter.
- Compare the direction of the recent few bars with an older, non-overlapping
  context window.
- Motivation: a recent decline after an advance differs from a decline inside
  a longer decline; a single aggregate trend measure can hide that distinction.
- Before starting: fix both window lengths and the direction definition.

## Inbox: new questions

Write any new idea here as soon as it comes up: one line, no analysis needed. When we pick
it up, it gets a number, a fixed protocol before looking at outcomes, and a results doc.

| Added | Question | Status |
|---|---|---|
| 2026-10-02 | Does the **signal candle's shape** matter: full body (marubozu), doji, shooting star (long upper wick), hammer (long lower wick)? Related: `close_loc` (09-29) found no effect, but it looked only at where the close sits, not at the full shape. | Queued after Q4 |

## Shared lookback questions

- [x] Compare N = 5, 10, 20, 50 for Q1/Q2 using consistent definitions and the same trades.
- N preceding bars means bars 2 through N+1; bar 1 is the completed signal.
  Existing `location_N` is different: it includes the signal in N bars.
- On M30, these are 2.5, 5, 10, 25 hours of bar time, not necessarily elapsed
  time across market closures. Session-boundary variants are separate tests.
- Log at least 51 bars. Extra recorded bars must not silently change a feature.
- Confirm a proposed filter with a full MT5 rerun before claiming a strategy
  improvement; excluding CSV rows changes neither order nor position availability.
- Previously examined 2015–2026 data remain exploratory, even with a frozen
  chronological split. Fresh-data or prospective validation is a separate stage.
