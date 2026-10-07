# Time of day: does the session block matter?

2026-10-02 · Runs: `Reports/time_of_day_20261002/` · Analysis: `python/analyze_time_of_day.py`
Symbol: `MNQcontDTBNT20102026_2` · Baseline: RR 1.0, `MaxRedRun = 3`, calendar on, 1 contract

## Protocol (fixed before running)

**Question:** do some parts of the session lose money consistently, so that the EA's
existing trade-window inputs should switch them off?

**Data:** the baseline rerun on 2016–19 and 2020–26 with `SnapshotBars = 1`, which logs each
trade's signal-bar time. These runs must reproduce the baseline trades field by field.

**Blocks**, by the time the buy stop is **placed** (signal bar open + 30 min). The data clock
is Chicago + 8 h:

| Block | Data clock | Chicago |
|---|---|---|
| Asia | 01:00–09:00 | 17:00–01:00 |
| Europe | 09:00–16:00 | 01:00–08:00 |
| US open | 16:00–18:00 | 08:00–10:00 (8:30 data releases and cash open) |
| US midday | 18:00–21:00 | 10:00–13:00 |
| US afternoon | 21:00–23:30 | 13:00–15:30 |

Boundaries fall on the EA's hourly window slots, so any block can be switched off exactly.
Fill time is reported separately: a placed order can fill in a later block.

**Decision rule:** a block is a candidate to switch off only if its **net PF < 1 in both
periods**. A candidate is then confirmed with full MT5 runs with that block's windows off.
It is adopted only if net $ and net PF beat the baseline in both periods. If no block
qualifies, the windows stay as they are. No other block definitions will be tried in
response to the results.

## Summary

- **No block qualifies → trade windows unchanged.** Every block is profitable in both
  periods (net PF 1.00–1.37). The edge is spread across the whole session.
- **No block is consistent across periods either.** US afternoon is the best block in
  2016–19 (PF 1.37) and flat in 2020–26 (PF 1.00). US open is weak in 2016–19 and strong in
  2020–26. Every block has losing years. These look like noise, not structure.
- **Placement vs fill:** 6.7% of orders fill in a later block than they were placed; the
  conclusions are the same either way.

## Results (net of $1.05/trade; by placement block)

| Block | 2016–19 trades | Net $ | Net PF | Avg R | 2020–26 trades | Net $ | Net PF | Avg R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Asia | 2,018 | 3,207 | 1.214 | −0.017 | 3,178 | 11,865 | 1.142 | +0.068 |
| Europe | 1,754 | 1,094 | 1.060 | −0.027 | 2,913 | 10,752 | 1.099 | +0.076 |
| US open | 674 | 434 | 1.037 | +0.014 | 1,027 | 8,957 | 1.137 | +0.085 |
| US midday | 720 | 188 | 1.016 | +0.005 | 1,132 | 4,570 | 1.076 | +0.018 |
| US afternoon | 386 | 1,426 | 1.370 | +0.104 | 715 | 28 | 1.001 | +0.005 |
| Session open* | 145 | 137 | 1.125 | +0.027 | 306 | 1,810 | 1.263 | +0.028 |

\* Orders placed at 01:00 from the previous session's last bar (signal at 23:30). This
group wasn't in the block definitions; it's reported for completeness and is profitable too.

**Net $ by year and placement block:**

| Block | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Asia | 391 | −42 | 932 | 1,927 | 3,146 | 709 | 1,053 | −642 | 1,777 | 4,159 | 1,663 |
| Europe | −341 | 267 | 552 | 616 | −204 | 2,114 | 319 | 788 | 3,917 | −804 | 4,622 |
| US open | −44 | 230 | −472 | 721 | 17 | 1,456 | 727 | 1,968 | 3,736 | 1,771 | −719 |
| US midday | −833 | 254 | 383 | 384 | 1,045 | −2,215 | 1,701 | 2,581 | 762 | −1,306 | 2,002 |
| US afternoon | 353 | 246 | 478 | 350 | 899 | −859 | 598 | 94 | −1,159 | 360 | 95 |

By fill block, US open in 2016–19 is the only cell below PF 1 (0.975), and it's strong in
2020–26 (1.139), so the rule isn't met that way either.

## Verification

- Both `SnapshotBars = 1` runs reproduce the baseline trades (`Reports/rr_clean_20261001`,
  RR 1.0) in every field. Only the number formatting differs: the snapshot export writes fixed
  decimals.
- CSV trade counts and gross PnL reconcile with MT5 stats.

```powershell
.\venv\Scripts\python.exe python\prepare_time_of_day.py
.\python\run_exit_study.ps1 -StudyDir Reports\time_of_day_20261002 -ExpertName RTL_runband_cal -InstallFolder ClaudeEarlyClose
.\venv\Scripts\python.exe python\analyze_time_of_day.py
```
