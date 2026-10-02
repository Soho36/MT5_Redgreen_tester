# Q5: does the signal candle's shape matter?

2026-10-02 · Data: `Reports/entry_shape_20261002/` (same runs as Q3/Q4) · Analysis: `python/analyze_q5_candle_shape.py`
Symbol: `MNQcontDTBNT20102026_2` · Baseline: RR 1.0, `MaxRedRun = 3`, calendar on, 1 contract
Question source: user, 2026-10-02 (Inbox in [RESEARCH_QUESTIONS.md](RESEARCH_QUESTIONS.md))

## Protocol (fixed before running; definitions agreed with the user)

**Idea:** the signal candle is always red, but its shape differs: a full body, a doji, a
shooting star or a hammer. Does the shape affect how the buy stop over its high works out?

**Measures** (signal bar = bar 1, as a share of its range `high − low`):
- body = (open − close) / range
- upper wick = (high − open) / range
- lower wick = (close − low) / range

**Shapes**, checked in this order (first match wins):

| Shape | Rule |
|---|---|
| Doji | body ≤ 10% |
| Hammer | lower wick ≥ 60%, upper wick ≤ 15% |
| Shooting star | upper wick ≥ 60%, lower wick ≤ 15% |
| Full body (marubozu) | body ≥ 80% |
| Other | everything else |

**Related earlier work:** `close_loc` (2026-09-29, old data) found no effect, but looked only
at where the close sits within the range.

**Decision rule:** a shape is a candidate filter only if its **net PF < 1 in both periods**
with at least 200 trades in each. Rarer shapes are reported but can't qualify. A candidate
then needs its own full MT5 test. Otherwise: no filter, finding recorded. No other thresholds
will be tried in response to the results.

## Summary

- **Answer: no.** No shape loses money in both periods, so **no filter**. Q5 is closed.
- **Two shapes lose in one period each, in opposite periods:**
  - **Doji:** loses in 2016–19 (PF 0.889, −$693), but is one of the best groups in 2020–26
    (PF 1.161, +$6.5k).
  - **Full body:** fine in 2016–19 (PF 1.071), loses in 2020–26 (PF 0.938, −$1.8k).

  Excluding either would have helped in one period and hurt in the other.
- **Hammer** is mildly profitable in both periods (PF 1.069 / 1.091). **Shooting star** is rare
  (2% of signals, under 200 trades per period) and can't qualify.
- About 72% of signal candles are "other" (no pronounced shape), with the same results as the
  overall baseline.

## Results (net of $1.05/trade)

| Shape | 2016–19 n | Share | Net $ | PF | Avg R | 2020–26 n | Share | Net $ | PF | Avg R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Doji | 558 | 9.8% | −693 | 0.889 | −0.017 | 1,187 | 12.8% | 6,489 | 1.161 | +0.139 |
| Hammer | 450 | 7.9% | 318 | 1.069 | −0.004 | 716 | 7.7% | 2,335 | 1.091 | +0.021 |
| Shooting star | 129 | 2.3% | 349 | 1.326 | +0.201 | 192 | 2.1% | 198 | 1.031 | −0.032 |
| Full body | 430 | 7.5% | 342 | 1.071 | −0.025 | 539 | 5.8% | −1,823 | 0.938 | −0.032 |
| Other | 4,130 | 72.5% | 6,168 | 1.138 | −0.007 | 6,637 | 71.6% | 30,782 | 1.121 | +0.060 |

## Verification

Same data as Q3/Q4: two 51-bar snapshot runs that reproduce the baseline trades in every field.
The script checks that every signal bar is red with a positive range.

```powershell
.\venv\Scripts\python.exe python\analyze_q5_candle_shape.py
```
