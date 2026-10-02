# Q3: were the bars before the signal overlapping or moving steadily?

2026-10-02 · Runs: `Reports/entry_shape_20261002/` · Analysis: `python/analyze_q3_overlap.py`
Symbol: `MNQcontDTBNT20102026_2` · Baseline: RR 1.0, `MaxRedRun = 3`, calendar on, 1 contract
Question source: [RESEARCH_QUESTIONS.md](RESEARCH_QUESTIONS.md) Q3

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

## Results

*Pending.*
