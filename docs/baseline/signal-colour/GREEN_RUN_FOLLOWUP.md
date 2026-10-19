# GG green-run cap follow-up

2026-10-20. Follow-up to the [GG run-cap study](RESULTS.md#gg-run-cap-and-the-combined-equity-curve-2026-10-13), prompted by a `MaxGreenRun=1` MT5 test showing lower drawdown in 2021–24.

## Protocol

- Standalone `GG_runband` EA with the renamed `MinGreenRun` / `MaxGreenRun` inputs. Same MNQ continuous symbol, M30, 1-minute OHLC, 1 contract, RR 1, windows, flatten and early-close calendar as the earlier study. `MinGreenRun=1`; sweep `MaxGreenRun=0` (off) through 7. Single test from 2016-01-01 to 2026-10-15, sliced by entry year. The last trade enters 2026-10-01.
- Cost convention: MT5 trade profit minus $1.05 per trade; profit factor and drawdown calculated on that net ledger. Drawdown is trade by trade. The combined RTL + GG comparison sums two independent accounts by exit day and measures daily-close drawdown.
- Preserve the earlier decision rule: select on 2016–19 gross PF, with caps within 0.005 tied in favour of the larger cap (off ranks largest); require the frozen winner to improve both net PF and net drawdown against off in 2020–26. Inspect cap 1 separately because it was suggested after seeing 2021–24.
- Eight output ledgers, MT5 reports, INIs and hashes: `Reports/gg_green_cap_review_20261020/`. Run `venv/Scripts/python.exe python/analyze_gg_green_cap_review.py` to reconcile ledgers with MT5 and print period tables.

All eight ledgers reconcile with their MT5 stats. Their trades through 2026-07-13 match the 2026-10-13 study **exactly** for each cap, confirming that the input rename did not change the strategy. The only newly observed period is July–October 2026; the earlier 2020–26 record is not a fresh holdout.

## GG results

| MaxGreenRun | 2016–19 gross PF | 2020–26 trades | 2020–26 net $ | 2020–26 net DD $ | 2020–26 net PF | 2020–26 net $ / DD |
|---|---:|---:|---:|---:|---:|---:|
| 0 (off) | 1.142 | 11,182 | 39,444 | 5,316 | 1.083 | 7.42 |
| 1 | **1.152** | 9,485 | 29,669 | 5,071 | 1.072 | 5.85 |
| 2 | 1.128 | 10,195 | 32,742 | 5,790 | 1.075 | 5.65 |
| 3 | 1.146 | 10,566 | 34,311 | 5,675 | 1.076 | 6.05 |
| 4 | 1.150 | 10,850 | 38,025 | 5,641 | 1.082 | 6.74 |
| 5 | 1.150 | 11,008 | 36,193 | 5,632 | 1.077 | 6.43 |
| 6 | 1.144 | 11,087 | 37,928 | 5,632 | 1.080 | 6.73 |
| 7 | 1.142 | 11,123 | 38,879 | 5,270 | 1.082 | 7.38 |

The original selection rule picks cap 5 because caps 1, 4 and 5 are within 0.005 gross PF. Cap 5 fails the test: net PF 1.077 versus 1.083 off, drawdown $5,632 versus $5,316, and net profit $36,193 versus $39,444. Cap 1 also fails as an exploratory choice: net profit falls $9,775 (24.8%) while drawdown falls only $245 (4.6%); net PF and profit per drawdown both worsen. Cap 7's $46 drawdown reduction (0.9%) is too small to justify its lower net profit and PF.

### Why cap 1 looked attractive in 2021–24

| Period | Setting | Trades | Net $ | Net DD $ | Net PF | Net $ / DD |
|---|---|---:|---:|---:|---:|---:|
| 2021–24 | Off | 6,733 | 20,128 | 4,995 | 1.082 | 4.03 |
| 2021–24 | Cap 1 | 5,705 | 15,203 | 3,817 | 1.072 | 3.98 |
| 2021–24 | Cap 2 | 6,104 | 18,087 | 4,147 | 1.081 | 4.36 |
| 2021–24 | Cap 3 | 6,371 | 19,261 | 4,403 | 1.083 | 4.37 |
| 2025–26 | Off | 2,830 | 10,516 | 5,316 | 1.061 | 1.98 |
| 2025–26 | Cap 1 | 2,394 | 8,131 | 5,071 | 1.055 | 1.60 |
| 2026 | Off | 1,214 | 6,345 | 4,202 | 1.072 | 1.51 |
| 2026 | Cap 1 | 1,031 | 5,325 | 4,591 | 1.070 | 1.16 |

In 2021–24 cap 1 lowers drawdown 23.6%, but it also lowers profit 24.5%, leaving profit per drawdown slightly worse. Caps 2 and 3 look more efficient in that slice, but neither survives the full 2020–26 test. In 2026 alone, cap 1 has *higher* drawdown.

The newly appended period, entries from 2026-07-14 to 2026-10-01, has 368 off trades and 317 cap-1 trades. Net profit is +$214 off versus -$357 at cap 1. This short addition gives no support for cap 1.

## RTL + GG portfolio check

Using the existing no-cap RTL ledger from `Reports/maxredrun_extended_20261013/` and the new GG ledgers, two separate accounts summed by exit day:

| Period | GG setting | Combined net $ | Combined daily-close DD $ | Net $ / DD |
|---|---|---:|---:|---:|
| 2020–26 | Off | 77,978 | 9,141 | 8.53 |
| 2020–26 | Cap 1 | 68,203 | 10,156 | 6.72 |
| 2021–24 | Off | 38,445 | 7,977 | 4.82 |
| 2021–24 | Cap 1 | 33,520 | 6,625 | 5.06 |
| 2025–26 | Off | 27,331 | 9,141 | 2.99 |
| 2025–26 | Cap 1 | 24,947 | 10,156 | 2.46 |

The 2021–24 combined drawdown reduction does not persist: in 2020–26 cap 1 increases combined drawdown by $1,015 (11.1%) and reduces combined profit by $9,775 (12.5%). As in the earlier study, this assumes two separate accounts and does not model margin or overlapping positions in one account.

## Decision

**Keep GG `MaxGreenRun=0` as the baseline.** The green cap remains an optional research input, but no tested value has a stable improvement that supports adoption. Cap 1's drawdown benefit is confined to the selected 2021–24 window and comes with comparable lost profit there; later and combined results are worse.