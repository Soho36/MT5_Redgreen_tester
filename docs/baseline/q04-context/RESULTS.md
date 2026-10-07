# Q4: is the recent pullback against the broader move?

2026-10-02 · Data: `Reports/entry_shape_20261002/` (same runs as Q3) · Analysis: `python/analyze_q4_context.py`
Symbol: `MNQcontDTBNT20102026_2` · Baseline: RR 1.0, `MaxRedRun = 3`, calendar on, 1 contract
Question source: [RESEARCH_QUESTIONS.md](../../reference/RESEARCH_QUESTIONS.md) Q4

## Protocol (fixed before running)

**Idea:** a short dip after an advance (pullback in an uptrend) may behave differently from
a dip inside a longer decline. One overall trend number can hide that difference.

**Data:** the two 51-bar snapshot runs from Q3, which reproduce the baseline trades exactly.

**Windows** (bar 1 = signal, excluded; the two windows don't overlap):
- **Recent:** the R bars before the signal, bars 2 … R+1.
- **Older:** the L bars before that, bars R+2 … R+L+1.

Settings (R, L): **(5, 20) is primary**; (3, 10) and (10, 40) are its neighbours.

**Direction** of each window = sign of its net move, `close(newest bar) − open(oldest bar)`:
*down* if < 0, otherwise *up*.

**Groups:** older direction × recent direction = 4 groups:

| Older | Recent | Meaning |
|---|---|---|
| up | down | **pullback in an advance** |
| down | down | **decline inside a decline** (prime suspect) |
| up | up | rally continuing |
| down | up | bounce inside a decline |

**Decision rule:** a group is a candidate filter only if its **net PF < 1 in both periods**,
with at least 200 trades in each, at the primary setting **and** at least one neighbour.
A candidate then needs its own full MT5 test. Otherwise: no filter, finding recorded.
No other windows or definitions will be tried in response to the results.

## Summary

- **Answer: no.** All 4 groups are profitable in **both** periods at **all three** window
  settings (net PF 1.002–1.226). **No filter.** Q4 is closed.
- **The intuitive story doesn't hold:** "pullback in an advance" is not better. At the primary
  setting it's the *weaker* half (PF 1.077 / 1.042), while "decline inside a decline", the prime
  suspect, is fine (1.140 / 1.076).
- **No consistent ranking:** the order of the groups changes from setting to setting and period
  to period. For example, "bounce in decline" is the best group at (5, 20) and (10, 40) but the
  weakest in 2020–26 at (3, 10). That's noise around one shared positive edge.

## Results (net of $1.05/trade)

| Setting (recent, older) | Group | 2016–19 n | Net $ | PF | Avg R | 2020–26 n | Net $ | PF | Avg R |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **(5, 20) primary** | pullback in advance | 1,462 | 1,249 | 1.077 | −0.007 | 2,403 | 4,048 | 1.042 | +0.019 |
| | decline in decline | 1,125 | 1,954 | 1.140 | −0.023 | 1,947 | 6,514 | 1.076 | +0.048 |
| | rally continuing | 1,750 | 448 | 1.026 | −0.032 | 2,693 | 15,088 | 1.170 | +0.099 |
| | bounce in decline | 1,360 | 2,834 | 1.199 | +0.050 | 2,228 | 12,331 | 1.143 | +0.067 |
| (3, 10) | pullback in advance | 1,409 | 1,449 | 1.097 | −0.051 | 2,262 | 11,469 | 1.135 | +0.077 |
| | decline in decline | 1,259 | 1,890 | 1.121 | +0.018 | 2,140 | 12,536 | 1.138 | +0.063 |
| | rally continuing | 1,712 | 766 | 1.046 | +0.031 | 2,721 | 11,760 | 1.129 | +0.069 |
| | bounce in decline | 1,317 | 2,380 | 1.166 | −0.021 | 2,148 | 2,215 | 1.025 | +0.026 |
| (10, 40) | pullback in advance | 1,497 | 28 | 1.002 | −0.067 | 2,360 | 6,018 | 1.067 | +0.008 |
| | decline in decline | 1,023 | 3,007 | 1.226 | +0.016 | 1,901 | 5,229 | 1.058 | +0.044 |
| | rally continuing | 1,796 | 529 | 1.033 | −0.024 | 2,753 | 8,417 | 1.095 | +0.076 |
| | bounce in decline | 1,381 | 2,921 | 1.190 | +0.075 | 2,257 | 18,316 | 1.211 | +0.108 |

## What Q1–Q4 add up to

All four preceding-candle questions are answered with the same result: no shape of the bars
before the signal reliably separates good trades from bad. Together with the earlier 10-feature
scan, this suggests the pre-entry bar pattern is genuinely exhausted as a filter source. The
only survivor is the red-run cap.

## Verification

Same data as Q3: two 51-bar snapshot runs that reproduce the baseline trades in every field.

```powershell
.\venv\Scripts\python.exe python\analyze_q4_context.py
```
