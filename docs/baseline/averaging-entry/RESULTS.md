# One near-stop averaging entry

Study started 2026-10-01; completed 2026-10-02.
[Protocol](PROTOCOL.md). The adopted EA source is unchanged.

**Verdict: keep averaging off.** All three distances worsen the coarse-model
comparison. The primary 10% distance also reduces profit and increases drawdown
in both periods with finer generated ticks. The added leg loses money in every
individual year from 2016 through the partial 2026 sample. Twelve valid full
MT5 runs were checked; invalid prototype outputs are excluded.

The more consequential finding is that the baseline itself is sensitive to
the execution model. Review this before adding more filters or deciding live
sizing. Neither simulation establishes real-tick execution performance.

## Question and implementation

After the normal one-contract buy stop fills, place one additional one-contract
buy limit just above the original protective stop. Keep that stop and the
original bar-close 1R target for the entire basket, as requested by the user.
Cancel an unfilled add on exit or session flatten. Never add more than once.

Primary distance: 10% of the initial fill-to-stop distance above the stop;
neighbours: 5% and 20%, rounded upwards to an exchange tick. With exact fills,
the 10% version has 1.10 times the initial planned price risk. That is a planned
risk calculation, not a guarantee about gap execution or transaction costs.

Use `MNQcontDTBNT20102026_2`, M30, MaxRedRun=3, MinLocation=0, the early-close
calendar and flatten fallback. Compare 2016-01-01 to 2020-01-01 and 2020-01-02
to 2026-07-14. All these data were previously examined; this is exploratory.
Costs below are $1.05 per round-turn contract, including the added contract.
DD means net closed-basket balance drawdown, not intratrade equity drawdown.

## One-minute OHLC comparison

These are full MT5 reruns using the previous studies' Model=1. Both controls
reproduce the prior clean-data RR=1 runs, trade by trade. All original-leg
entries, exits and PnL remain identical when averaging is enabled.

| Period | Add distance above SL | Baskets | Add fills | Net $ | Net PF | Net DD $ | Avg net initial R |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2016–19 | Off | 5,697 | 0 | 6,485.15 | 1.106 | 1,435.30 | −0.0041 |
| 2016–19 | 5% R | 5,697 | 3,094 | −5,012.05 | 0.932 | 6,732.80 | −0.1625 |
| 2016–19 | 10% R | 5,697 | 3,176 | −3,161.65 | 0.958 | 5,394.90 | −0.1423 |
| 2016–19 | 20% R | 5,697 | 3,371 | 1,005.60 | 1.013 | 3,117.55 | −0.1067 |
| 2020–26 | Off | 9,271 | 0 | 37,980.95 | 1.107 | 4,847.40 | +0.0599 |
| 2020–26 | 5% R | 9,271 | 5,095 | −10,235.80 | 0.976 | 18,728.20 | −0.0387 |
| 2020–26 | 10% R | 9,271 | 5,248 | 3,784.05 | 1.009 | 8,705.40 | −0.0109 |
| 2020–26 | 20% R | 9,271 | 5,532 | 19,464.35 | 1.044 | 8,400.85 | +0.0182 |

All three distances fail the predefined screen in both periods. At 10%, the
added contract contributes −$9,646.80 / −$34,196.90. Fractionally rescaling each
basket to the baseline's planned risk produces total net −$2,767.02 / $3,456.12;
this does not rescue the comparison. That normalization reserves the possible
add risk even for baskets in which the limit does not fill.

## Execution ordering matters

On a synthetic tick that crosses both levels, MT5 can execute the original stop
first, then fill the buy limit before the EA has a chance to cancel it. The
research EA immediately closes any such replacement position and assigns its
actual execution and cost to the original basket. At 10%, there are 1,787 such
cases in 2016–19 and 2,396 in 2020–26 in the OHLC model. Treating these as ordinary
one-position baskets originally lost deals; the unreconciled prototype outputs
are preserved in `Reports/averaging_entry_20261001_invalid_v1` and excluded.

This is too execution-sensitive to judge solely from the coarse model. A
focused off/10% check therefore uses Model=0, Every tick generated from the same
minute bars. It is still **not historical trade-tick or order-book validation**.
MetaQuotes describes the [generated-tick models](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation)
and [transaction event ordering](https://www.mql5.com/en/docs/event_handlers/ontradetransaction).

## Finer generated-tick comparison

| Period | Version | Baskets | Add fills | Net $ | Net PF | Net DD $ | Avg net initial R |
|---|---|---:|---:|---:|---:|---:|---:|
| 2016–19 | Off | 5,560 | 0 | 611.50 | 1.009 | 2,805.65 | −0.0621 |
| 2016–19 | 10% R | 5,560 | 3,191 | −5,414.55 | 0.928 | 7,255.40 | −0.1463 |
| 2020–26 | Off | 9,179 | 0 | 19,435.05 | 1.052 | 5,957.55 | +0.0215 |
| 2020–26 | 10% R | 9,179 | 5,265 | 9,770.80 | 1.023 | 8,282.55 | +0.0008 |

For 2016–19, the add contributes −$6,026.05, loses money in every individual
year, and has 134 profitable adds out of 3,191 fills. There are 553 stop-before-add
cases, fewer than in the coarse model but still material. Equal-planned-risk
net is −$4,784.36. The result also remains negative at $1 commission per contract.

For 2020–26, the add contributes −$9,664.25. Only 262 of 5,265 adds finish
profitable after costs (5.0%, versus 4.2% in 2016–19). There are 253 stop-before-add
cases. Equal-planned-risk net is $8,910.50, versus $19,435.05 for the control.
The extra contract loses money even **before** commission in both periods:
−$2,675.50 / −$4,136.00. Costs worsen an already negative contribution.

| Year | Added leg net $, generated ticks |
|---|---:|
| 2016 | −1,331.10 |
| 2017 | −1,095.80 |
| 2018 | −2,237.45 |
| 2019 | −1,361.70 |
| 2020 | −2,423.20 |
| 2021 | −1,561.25 |
| 2022 | −1,317.15 |
| 2023 | −1,337.75 |
| 2024 | −721.50 |
| 2025 | −579.60 |
| 2026 through July 13 | −1,723.80 |

Cost sensitivity in the finer model:

| Period | Control, $1/contract | 10% add, $1/contract | Control, $2.05/contract | 10% add, $2.05/contract |
|---|---:|---:|---:|---:|
| 2016–19 | 889.50 | −4,977.00 | −4,948.50 | −14,165.55 |
| 2020–26 | 19,894.00 | 10,493.00 | 10,256.05 | −4,673.20 |

$2.05 is the $1.05 commission plus a flat extra $1 round-trip execution-cost
stress per contract, not an estimated live slippage distribution.

MT5's **gross intratrade equity DD**, before the Python commission adjustment,
also increases. Off → 10%: OHLC $1,288.50 → $1,858.00 / $4,646.00 → $6,971.00;
generated ticks $1,771.00 → $2,323.00 / $5,142.00 → $6,566.00 (earlier/recent).
These figures have a different cost basis from the net closed-basket DD table.

The baseline itself changes materially with the simulation mode: net profit
falls from $6,485 to $612 in 2016–19 and from $37,981 to $19,435 in 2020–26.
Generated ticks can fill the original buy stop above its requested level and
change intraminute ordering; the EA then locks its risk and target to the actual
fill. Previous OHLC results should therefore be labelled with their modelling
assumption. This finding merits an execution review before further filters or
live sizing decisions; it is not proof that generated ticks reproduce reality.

## Validation and operational evidence

- Compiler: 0 errors, 0 warnings. Research variant refuses non-tester use and
  hedging accounts; baseline strategy source and defaults remain unchanged.
- All twelve valid runs reconcile basket volumes and per-leg PnL to MT5 totals. MT5's
  trade count is compared with exit deals because one basket can contain a
  stopped parent and a separately closed replacement add.
- Every original leg and its entry/exit schedule matches its control in the
  same model. No cross-date baskets, rejected adds, skipped adds or cancellation
  errors occur. A coarse control is never compared against a finer averaging run.
- Eight Python tests pass, including independent arithmetic for commissions,
  planned-risk normalization with an unfilled add, and losses exceeding planned
  risk. The runner's log fence was checked for append and truncate/regrow cases.
- The recent finer control completed successfully, but its custom CSV lacked
  40 contiguous rows. Its full MT5 HTML report contains all 9,179 trades. The
  recovery script checks every surviving row against the report, restores the
  missing price/time/PnL facts, and reconciles exactly to $29,073 gross. Unknown
  excursions and signal features are left blank. Original CSV and a list of
  recovered tickets are retained; recovered rows are explicitly marked.
- A rotated tester log also hid that run's completion from the batch runner.
  Terminal launch/completion evidence and the report are preserved. The runner
  now detects truncated-and-regrown logs and checks the terminal exit code.
- Generating ticks exhausted C: disk space on the first attempt. The test uses
  temporary directory junctions to the project drive for tick cache and, on the
  final run, common exports. Existing MT5 folders were preserved and restored
  after the run. This did not change the custom symbol or its history. The final
  run's original CSV reconciles without any report-based repair.

## Files and reproduction

- `mt5/experts/averaging_research.mqh`: optional one-add logic and basket export.
- `python/prepare_averaging_study.py`: derives a tester-only EA from the current
  baseline, copies includes, and freezes the jobs; `--generated-ticks` prepares
  the focused sensitivity. Refuses to overwrite completed study directories.
- `python/analyze_averaging_study.py`: reconciliation, costs, yearly breakdown,
  equal-planned-risk comparison and the predefined screen.
- `python/recover_averaging_control.py`: strict report-based repair for an off
  control only; never estimates missing excursions or alters trading outcomes.
- `Reports/averaging_entry_20261001/` and `Reports/averaging_entry_20261001_ticks/`:
  source snapshots, compiled EA, INIs, manifests, reports, CSVs and audit records.

```powershell
.\venv\Scripts\python.exe python\analyze_averaging_study.py
.\venv\Scripts\python.exe python\analyze_averaging_study.py Reports\averaging_entry_20261001_ticks
.\venv\Scripts\python.exe -m unittest discover -s python -p "test_*.py" -v
```
