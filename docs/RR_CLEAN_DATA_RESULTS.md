# RR on clean data: 1.0 vs 2.0 / 2.5 / 3.0

2026-10-01 · Runs: `Reports/rr_clean_20261001/` · Analysis: `python/analyze_rr_clean_study.py`
Symbol: `MNQcontDTBNT20102026_2` (rebuilt data without the pre-2016 tail bars)

## Protocol (fixed before running)

**Question:** is 2.5R's advantage over 1.0R a broad region or a single lucky point?

**Setup:** current runband EA (calendar on, fallback on, `MaxRedRun = 3`, trail off, 1 contract),
RR 1.0 / 2.0 / 2.5 / 3.0, in 2016-01-01 → 2020-01-01 and 2020-01-02 → 2026-07-14 (8 runs).
All four RR values are rerun on the final symbol so the comparison is like for like.

**Decision rule:** adopt **2.5R** as the new baseline if **2.0, 2.5 and 3.0 all beat 1.0**
on net $ **and** net PF in **both** periods. If any of them fails, keep 1.0R and record
the result. No other RR values will be tried in response to the results.

## Summary

- **Decision rule not met → RR stays 1.0.** The single failing cell is 2.0R in 2020–26:
  $38,366 vs $38,444 for 1.0R. That's $78, effectively a tie.
- **2016–19:** every higher RR clearly beats 1.0 (+$2.0–3.0k, +30–45%), with higher PF.
- **2020–26:** dollars are flat across 1.0–3.0 (within $2.1k, inside noise). PF and
  average R are higher for all of 2.0–3.0. Drawdown moves both ways.
- **Reading:** across 1–3R, higher RR is never meaningfully worse and is better in the earlier
  period and in R terms. But in the main recent period it doesn't add dollars beyond noise.
  The rule was set to avoid adopting an unproven change, and it did its job.

## Results (net of $1/trade; DD = net closed-balance drawdown; no trade crosses a date)

| Period | RR | Trades | Net $ | Net PF | Net DD $ | Net / DD | Avg net R |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2016–19 | 1.0 | 5,697 | 6,770 | 1.111 | 1,427 | 4.74 | +0.001 |
| 2016–19 | 2.0 | 4,781 | 8,763 | 1.146 | 1,552 | 5.65 | +0.026 |
| 2016–19 | 2.5 | 4,511 | 8,802 | 1.149 | 1,538 | 5.73 | +0.021 |
| 2016–19 | 3.0 | 4,283 | 9,781 | 1.171 | 1,329 | 7.36 | +0.042 |
| 2020–26 | 1.0 | 9,271 | **38,444** | 1.108 | 4,837 | 7.95 | +0.061 |
| 2020–26 | 2.0 | 7,762 | **38,366** | 1.111 | 5,046 | 7.60 | +0.075 |
| 2020–26 | 2.5 | 7,327 | 40,536 | 1.119 | 4,530 | 8.95 | +0.092 |
| 2020–26 | 3.0 | 7,044 | 39,558 | 1.118 | 5,599 | 7.07 | +0.085 |

## An argument that doesn't depend on these results

Higher RR trades about 20% less (7,300 vs 9,300 trades in 2020–26). Each trade pays commission
and, live, slippage that the tester doesn't model. At the real $1.05 cost plus one tick of
slippage, the earlier sizing analysis already favoured 2.5R. If you choose to override the
rule, this is the reason to cite, not the backtest dollars.

## Verification

- All 8 runs reconcile trade counts and gross PnL with MT5 stats; no trade crosses a date.
- The first attempt failed safely: the INI named `MNQcontDTBNT20102026(2)`, but the symbol is
  `MNQcontDTBNT20102026_2`. The tester refused to start and the runner stopped. Rerun with the
  correct name.

```powershell
.\venv\Scripts\python.exe python\prepare_rr_clean_study.py
.\python\run_exit_study.ps1 -StudyDir Reports\rr_clean_20261001 -ExpertName RTL_runband_cal -InstallFolder ClaudeEarlyClose
.\venv\Scripts\python.exe python\analyze_rr_clean_study.py
```
