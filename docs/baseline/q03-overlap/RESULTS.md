# Q3: were the bars before the signal overlapping or moving steadily?

2026-10-02 · Runs: `Reports/entry_shape_20261002/` · Analysis: `python/analyze_q3_overlap.py`
Symbol: `MNQcontDTBNT20102026_2` · Baseline: RR 1.0, `MaxRedRun = 3`, calendar on, 1 contract
Question source: [RESEARCH_QUESTIONS.md](../../reference/RESEARCH_QUESTIONS.md) Q3

## Protocol (fixed before running)

**Idea:** bars that keep crossing the same prices (chop) differ from a staircase, even when
the net move and range are similar. Does the trade's outcome depend on which one came before
the signal?

**Data:** the baseline rerun on 2016–19 and 2020–26 with `SnapshotBars = 51` (signal + 50
preceding bars). These runs must reproduce the baseline trades.

**Window:** the N bars before the signal, bars 2 … N+1. The signal bar is excluded.
N ∈ {5, 10, 20}.

**Overlap (main measure):** for each pair of neighbouring bars in the window,
`overlap / union`, where
- `overlap = max(0, min(high₁, high₂) − max(low₁, low₂))`
- `union = max(high₁, high₂) − min(low₁, low₂)`

`OVL_N` is the mean over the N−1 pairs: 0 = no shared prices (staircase), 1 = identical bars.
A pair with `union = 0` (two identical flat bars) counts as 1.

**Direction:** `close[2] − open[N+1]` over the window: *down* if < 0, otherwise *up*.

**Groups:** overlap terciles, with cut points taken from the 2016–19 trades only and applied
unchanged to 2020–26, crossed with direction: 3 × 2 = 6 groups per N. Prime suspect: the
**low-overlap down** group (a steady decline before a long entry).

**Is it new information?** Spearman correlation of `OVL_N` with `trend_eff` (net move ÷ sum of
ranges, same window). If |ρ| > 0.7, Q3 mostly repeats `trend_eff`.

**Decision rule:** a group is a candidate filter only if its **net PF < 1 in both periods**,
with at least 200 trades in each, and the same holds at a neighbouring N. A candidate then
needs its own full MT5 test before anything changes. Otherwise: no filter, finding recorded.
No other definitions will be tried in response to the results.

## Summary

- **Answer: no.** No overlap/direction group loses money in both periods at any N, so
  **no filter**. Q3 is closed.
- **The prime suspect doesn't hold:** "low overlap + down" (a steady decline before a long
  entry) is profitable in both periods at N = 5 and 10 (PF 1.07–1.16). At N = 20 it's
  breakeven in 2016–19 (0.990) and good in 2020–26 (1.149).
- **Overlap is new information, but it doesn't predict anything consistently:** its
  correlation with `trend_eff` is only −0.03 to −0.18, so it measures something different.
  Yet the few weak cells appear in one period only (N = 10 "mid + down": 0.972 in 2020–26
  but 1.041 in 2016–19).
- **One striking cell, not actionable:** N = 5 "high overlap + up" earns $16.2k (PF 1.315)
  in 2020–26, about 40% of the period's profit, but only PF 1.021 in 2016–19. It's one of 36
  cells, inconsistent across periods, and outside the pre-set rule. Noted, not pursued.

## Results (net of $1.05/trade)

| N | Group | 2016–19 n | Net $ | PF | Avg R | 2020–26 n | Net $ | PF | Avg R |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | low overlap, down | 743 | 1,398 | 1.161 | −0.021 | 1,238 | 3,562 | 1.068 | +0.025 |
| 5 | low overlap, up | 1,156 | 1,128 | 1.094 | +0.025 | 1,817 | 4,627 | 1.072 | +0.035 |
| 5 | mid overlap, down | 836 | 1,316 | 1.135 | +0.050 | 1,428 | 2,461 | 1.040 | +0.038 |
| 5 | mid overlap, up | 1,063 | 1,970 | 1.187 | +0.036 | 1,637 | 6,623 | 1.112 | +0.080 |
| 5 | high overlap, down | 1,008 | 488 | 1.042 | −0.062 | 1,684 | 4,540 | 1.069 | +0.032 |
| 5 | high overlap, up | 891 | 185 | 1.021 | −0.062 | 1,467 | 16,170 | 1.315 | +0.151 |
| 10 | low overlap, down | 782 | 925 | 1.097 | −0.048 | 1,324 | 7,706 | 1.136 | +0.020 |
| 10 | low overlap, up | 1,117 | 704 | 1.061 | −0.006 | 1,784 | 5,932 | 1.098 | +0.058 |
| 10 | mid overlap, down | 842 | 427 | 1.041 | −0.034 | 1,421 | −1,756 | 0.972 | −0.015 |
| 10 | mid overlap, up | 1,057 | 2,209 | 1.213 | +0.081 | 1,648 | 11,999 | 1.199 | +0.108 |
| 10 | high overlap, down | 896 | 1,683 | 1.171 | −0.019 | 1,516 | 5,298 | 1.086 | +0.064 |
| 10 | high overlap, up | 1,003 | 538 | 1.055 | −0.019 | 1,578 | 8,803 | 1.162 | +0.108 |
| 20 | low overlap, down | 810 | −109 | 0.990 | −0.077 | 1,397 | 8,771 | 1.149 | +0.059 |
| 20 | low overlap, up | 1,089 | 629 | 1.061 | −0.049 | 1,750 | 5,286 | 1.087 | +0.045 |
| 20 | mid overlap, down | 795 | 3,411 | 1.394 | +0.092 | 1,370 | 4,807 | 1.081 | +0.067 |
| 20 | mid overlap, up | 1,104 | 1,482 | 1.134 | +0.057 | 1,674 | 9,625 | 1.166 | +0.039 |
| 20 | high overlap, down | 842 | 380 | 1.038 | −0.035 | 1,410 | 3,279 | 1.055 | +0.073 |
| 20 | high overlap, up | 1,057 | 692 | 1.066 | −0.014 | 1,670 | 6,211 | 1.105 | +0.081 |

Tercile cut points (from 2016–19): N = 5: 0.379 / 0.477; N = 10: 0.405 / 0.468; N = 20: 0.418 / 0.461.

## Verification

- Both `SnapshotBars = 51` runs reproduce the baseline trades (`Reports/rr_clean_20261001`, RR 1.0)
  in every field (numeric comparison). All 14,968 trades have all 51 bars logged.
- Before the real runs, the analysis code was smoke-tested on the older snapshot data
  (`Reports/preceding_candles_20260930`, old symbol). That printed part of an old-data table;
  the protocol above was already fixed and was not changed.

```powershell
.\venv\Scripts\python.exe python\prepare_entry_shape.py
.\python\run_exit_study.ps1 -StudyDir Reports\entry_shape_20261002 -ExpertName RTL_runband_cal -InstallFolder ClaudeEarlyClose
.\venv\Scripts\python.exe python\analyze_q3_overlap.py
```
