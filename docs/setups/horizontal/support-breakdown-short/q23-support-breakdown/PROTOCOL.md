# Q23: do green signals that break horizontal swing-low support make a short?

**Frozen 2026-10-06** at the user's request ("we draw levels with the same
rules as Q18, but now for the short side"), before any Q23 count or outcome
was computed. All of 2010-2026 and the Q6-Q22 results have been seen, so this
is exploratory.

**The question.** The exact short-side mirror of
[Q18](../../resistance-breakout-long/q18-breakout/RESULTS.md), the only level definition that passed both of its
stages. A **green** M30 signal places a **sell stop at its low** (stop loss at
its high). The candidate is a green signal whose sell stop sits at an intact
horizontal **swing-low support** level, approached from above, so that a fill
breaks the level. Is that a better short than every other green signal, and
does it hold up traded alone?

**The mirror, item by item:**

| Q18 (long) | Q23 (short) |
|---|---|
| Red signal candle, red run 1-3 | Green signal candle (close > open), green run 1-3 |
| Buy stop at the high, stop at the low | Sell stop at the low, stop at the high |
| Exit after the first close >= entry + 1R | Exit after the first close <= entry - 1R |
| Swing highs, merged from the highest; L = highest member | Swing lows, merged from the lowest; L = lowest member |
| Broken = close > L + D; departed = close <= L - A | Broken = close < L - D; departed = close >= L + A |
| Candidate: contacts an intact, departed level and high <= L + D | Candidate: contacts an intact, departed level and low >= L - D |

**Prior evidence, stated up front:**

- **No short has worked here.** In Q21, shorting the low of red candles lost
  in every variant: any red bar (C2) PF 0.840 / 0.969 at 1R, and it lost in
  bear regimes too. NQ drifts up.
- **The user tried the mirror baseline by hand** (green candle, sell stop at
  its low) and found it "very choppy and unstable". Here it is only the
  population, not a candidate.
- **Q18** passed both stages for longs, but its 2016-19 evidence was weak and
  2010-15 went the other way.
- **[Q11](../../support-bounce-long/q11-level-visit/RESULTS.md)** used the same swing-low levels for the
  long side: red RTL signals revisiting intact support from above did slightly
  *better* than the rest (PF +0.11 / +0.04), but N = 3 disagreed, so it was not
  taken further. Q23 uses the same level map for the opposite trade: selling
  the break instead of buying the hold.

Expectations are low.

## Stage 0: the short mirror baseline (new MT5 run, the population)

No short-side census exists, so one MT5 run of the mirror baseline provides
the signals, attempts and fills, as Q10's run did for RTL.

**EA.** The Q10 research parent with the Q21 short-side patches (direction
flag, mirrored bar-close exit, direction-aware ledger and qualified flag, the
window exit cancelling every order; RiskReward = 1.0 sets the target in every
regime). Its red-candle entry is replaced by the mirror:

- the last closed M30 candle is green (close > open);
- its green run (consecutive green candles ending at it) is 1-3, the mirror of
  MaxRedRun = 3; a run above 3 cancels the pending sell stop, as the parent's
  rejection does;
- the pending sell stop is replaced: sell stop at the low, stop loss at the
  high; risk = range > 0;
- a red or doji candle leaves the pending order alone (as a green one does in
  the parent); MinLocation and the candle-range filter stay off;
- same windows (01:00-23:30), flatten, early closes, fallback, one contract,
  one position, $1.05 per round trip modelled in Python;
- symbol `MNQcontDTBNT20102026_2`, M30, one-minute OHLC, 2010-06-07 to
  2026-07-14 in one run.

**Census (Python, the mirror of Q10's):** every green M30 bar with green run
1-3, range > 0, and a submission bar (the next bar) opening at or after 01:00
and before the flatten cutoff. Attempts are the signals the EA logged; fills
are the ledger's trades. Periods are split by submission time: 2016-01-01 to
2020-01-01 and 2020-01-02 to 2026-07-14; 2010-2015 is reported separately.

**Stage-0 checks (before any classification is compared with outcomes):**

- every logged attempt is a census signal with the same green run and
  submission bar;
- every trade is a short from a logged attempt, filled at or below the signal
  low, with stop = signal high and RiskReward 1.0;
- one position at a time, every trade exits its session, MT5 trade count and
  net match the ledger, and there are 0 export or close errors.

## Stage 1: attribution screen (Q18's gate, unchanged)

**Classifier:** the frozen Q11 classifier
([`level_visit.classify`](../../../../../python/level_visit.py), with its pre-outcome
no-deep-slice amendment), applied **as is** to the green signal bars. Nothing
is re-parameterized. A = mean of the 14 true ranges before the signal (same
contract), D = 0.5 x A; swing lows N = 5, known once bar i+5 has closed; a
one-week window (signal session + 5 previous); contact = low <= L + D and
high >= L - D.

**Groups (Q11 order and implementation, named for the short side):**

1. **Unavailable:** roll, missing history, invalid A.
2. **Breakdown test (primary candidate)** = Q11 "support revisit": contacts an
   intact, departed level and low >= L - D. The sell stop at the signal low
   sits within D of the level, so a fill trades at or through it.
3. **Poke-through** = Q11 "slice-through": the low is already more than D
   below L.
4. **Broken-downward contact** = Q11 "broken contact".
5. **Not-departed contact.**
6. **No contact.**

**Rule.** The primary candidate (one week, N = 5) passes stage 1 only if all
hold:

- candidate and complement (every other green signal) each have >= 200 fills
  in both periods;
- candidate PF > 1;
- candidate PF and average net R exceed the complement in both periods;
- average R is better in >= 7 of 11 years (>= 10 fills per group);
- the two-week N = 5 and one-week N = 3 sensitivities point the same way in
  both periods.

Contrasts use 2,000 calendar-month block resamples (seed 20261004) as
descriptive 95% intervals. Partitions must reconcile with the stage-0 run
exactly.

**Descriptive labels (never candidates), inside group 2:** entry at or below L
versus above L (a fill is a strict break only at or below); (L - low) / A in
bins; opens below L; level age; merged versus single member; false
breakdowns since the level formed (closes below L). Broad contact (groups 2-5)
is context only. Also the daily regime at the signal (Q10 bull / bear /
neutral).

## Stage 2: stand-alone run (only if stage 1 passes)

Built as in Q18: the stage-0 EA plus an MQL5 gate implementing this level
definition (the mirror of [`level_gate.mqh`](../../../../../mt5/experts/level_gate.mqh)
to lows). A non-candidate is rejected like a run rejection.

- **Gate check:** a classify-only run must reproduce the stage-1 Python
  classification for every census signal before any trading run.
- **Reading rule (Q17's, unchanged).** Survives if, in both periods:
  stand-alone PF > 1; mean net R > 0; mean net R > the stage-0 mirror
  baseline's; mean R beats the mirror baseline's in >= 7 of 11 years (years
  with >= 10 trades). Also report trade identity with stage 0, freed and
  displaced trades, the week bootstrap and the entry-at-or-below-L label.

## Stopping rule (agreed before outcomes)

If the primary fails stage 1 or stage 2, **short-side level research stops.**
No other N, window, zone, confluence or role-reversal candidate is opened
without a new external reason agreed with the user. A pass at both stages
adopts nothing by itself: combining with RTL (opposite direction, one position)
and sizing would each need their own protocol.

## Verification and outputs

- **Unit tests** for the census mirror: green run counting, doji handling,
  window and cutoff boundaries, period split. The Q11 classifier keeps its own
  tests (`test_level_visit.py`).
- **Independent re-derivation** of a random sample of green signals on raw
  lows with plain loops (`verify_level_visit.direct`, which does not import
  the study code): 0 mismatches required.
- Stage-0 checks above; exact partition reconciliation; hashes of the EA,
  inputs, code and this protocol.
- Code: `python/prepare_support_breakdown.py` (EA and jobs),
  `python/analyze_support_breakdown.py` (census, checks, stage 1), tests in
  `python/test_support_breakdown.py`; MQL entry `mt5/experts/short_mirror.mqh`.
- Outputs: `Reports/levels/support_breakdown_<date>/`. Results doc:
  `docs/setups/horizontal/support-breakdown-short/q23-support-breakdown/RESULTS.md`.
- Execution: one-minute OHLC with the tester's one-tick spread; generated
  ticks are not a criterion (the user's 2026-10-05 decision).

## What was seen while drafting

Nothing beyond the Q11, Q18 and Q21 results quoted above and the user's
qualitative manual test. No green-signal count or outcome has been computed.
Counts may be shown before outcomes are compared.
