# Project status

Updated 2026-10-01. **Start here.** One page. Each study below links to the full evidence.
For the day-by-day history, see [JOURNAL.md](JOURNAL.md).

## The strategy (current research baseline)

| | |
|---|---|
| Signal | The last closed M30 candle is red |
| Entry | Buy stop at its high; stop loss at its low; risk = candle range |
| Exit | Market exit after the first bar that closes ≥ entry + **1.0R**; flatten at 23:30 |
| Filter | `MaxRedRun = 3` (skip if more than 3 reds in a row); `MinLocation = 0` (off) |
| Session safety | `FlattenFallback = true` (flatten even when the 23:30 bar is missing) |
| Sizing / costs | 1 contract; $1 per round-turn modelled in Python |
| EA | [`mt5/experts/RR_r_MFE_buy-stop-entry_runband.cs`](../mt5/experts/RR_r_MFE_buy-stop-entry_runband.cs) |
| Data | Custom MNQ-sized series; NQ-based before MNQ existed (2019). See the data caveats below |

**Where it stands** (net of commission, 1 contract):

| Period | Trades | Net $ | Net PF | Net DD $ | Avg net R |
|---|---:|---:|---:|---:|---:|
| 2020-01 → 2026-07 | 9,258 | 37,419 | 1.105 | 5,134 | +0.060 |
| 2015 → 2019 | 7,194 | 7,172 | 1.098 | 1,434 | −0.012 |
| 2010 → 2014 | — | ≈ breakeven before costs | | | |

The edge is thin, and all of 2015–2026 has been looked at. No untouched data is left for validation.

## Decisions

**Adopted**
- `MaxRedRun = 3`. Chosen on 2015–19 by a pre-set rule, then tested frozen on 2020–26:
  PF up in 6 of 7 years, DD −17%, profit flat. A **small** but real effect.
- `FlattenFallback` fix (bug: positions were held up to 6.5 days).

**Rejected** (evidence kept, don't retest without a new reason)
- Minimum red count, drop size, `location` filter, 10 other bar features.
- Q1 interrupted decline, Q2 recovery after a new low.
- Fixed take-profit at 1R (first touch): worse than the bar-close exit in both periods.
- Resting limit above the target to "capture the wick" (estimate from MFE, 2026-10-01).
  Winners give back 0.38R / 0.32R on average from their best point (2015–19 / 2020–26),
  but a limit at 1.5–4R is worse at every level in both periods (2020–26: $30.7–35.5k
  vs $37.4k). It caps the big runners, which are worth more than the give-back.
- Trailing stop after +1R at 0.25 / 0.5 / 1.0R (full MT5 runs, 2026-10-01): clearly
  worse in 2015–19 at every distance; mixed in 2020–26. Rejected by the pre-set rule.
  The bar-close exit stays.
- Buy-stop-limit entry (an experiment; not used for testing).

**Open**
- **RR:** 1.0 stays for now. Dollars favour ~1R in 2020–26 but 2–2.5R in 2015–19.
  Average R favours higher RR in both. This depends on the sizing decision.
- **Sizing policy:** fixed contracts or fixed risk per trade. *This is the user's decision.*
- **Early-close days:** about 70–95 trades still hold one overnight gap.
- **Data provenance:** NQ/MNQ join date, any price adjustment, roll-contract choice.

## Next steps, in order

1. Decide the sizing policy. It picks the primary metric and settles RR.
2. Flatten before known early closes (session calendar), then rerun 1R vs 2.5R.
3. Pin down data provenance (join, adjustment, roll dates).
4. Time-of-day diagnostic: a few broad session blocks, signal time vs fill time.
5. Lower priority: Q3/Q4 entry-shape questions ([checklist](RESEARCH_QUESTIONS.md)).

## Study index

| Date | Study | Verdict |
|---|---|---|
| 09-28/29 | [Entry filters and bar features](RESEARCH_RESULTS.md) | Only the red-run cap survives; location and other features don't |
| 09-29 | [MaxRedRun train/test](RESEARCH_RESULTS.md#next-steps) | Cap 3 passes out of sample; the effect is small |
| 09-30 | [Preceding candles Q1/Q2](PRECEDING_CANDLES_RESULTS.md) ([protocol](PRECEDING_CANDLES_PROTOCOL.md)) | No filter adopted; the periods disagree |
| 09-30 | [Exit estimate and data review](EXIT_AND_DATA_REVIEW.md) | First-touch exit worse; several data caveats |
| 09-30 | [Exit thresholds](EXIT_THRESHOLD_RESULTS.md) ([protocol](EXIT_THRESHOLD_PROTOCOL.md)) | Fixed TP worse; RR comparison distorted by the flatten bug |
| 09-30 | [RR 0.5–5.0 grid](RR_OPTIMIZATION_REVIEW.md) | Noisy curve; RR>1 gains were mostly multi-day holds |
| 10-01 | [Flatten fallback fix](FLATTEN_FALLBACK_RESULTS.md) | Bug fixed; baseline barely changes; RR still open |
| 10-01 | [Trailing stop after +1R](TRAILING_STOP_RESULTS.md) | Rejected at all distances; keep the bar-close exit |

## How we test

- Fix definitions and the selection rule **before** running. Keep negative results.
- Confirm any filter with a **full MT5 rerun**. Removing rows from a CSV misses the
  changed entries (a skipped trade frees the position for another one).
- Report **both** net $ and average net R, and say which one decides.
- Look for broad regions, not the best single grid step. Neighbouring steps differ by ±$4–5k from noise.
