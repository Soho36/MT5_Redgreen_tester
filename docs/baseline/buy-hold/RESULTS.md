# One-contract hold, with and without rollover exits

2026-11-08. User-requested descriptive benchmark. One long MNQ-sized contract
($2 per NQ point), no stop, no take-profit, no session flatten, no compounding.
Full dataset: **2010-06-07 01:00:00 to 2026-10-01 02:59:59**, in the dataset's
Chicago + 8 hour clock. Includes the final partial session.

| Variant | Completed positions | MT5 profit before commission | Modeled commission | Net profit | MT5 equity drawdown | Equity drawdown after modeled commission |
|---|---:|---:|---:|---:|---:|---:|
| Hold the raw continuous series | 1 | $57,974.00 | $1.05 | **$57,972.95** | $12,565.50 | $12,565.50 |
| Close/reopen at every rollover | 67 | $50,389.50 | $70.35 | **$50,319.15** | $12,804.00 | $12,808.20 |

Costs are the project's $1.05 per completed contract position, applied after the
native replay. MT5 itself charged zero commission and swap. Native entry spread
is included: every buy filled 0.25 points ($0.50) above the source opening bid;
sells filled at the source closing bid. No additional slippage is modeled.
Commission-adjusted equity allocates $0.525 on each entry and exit.
Both maximum equity drawdowns end at 2022-10-13 16:33 in the dataset clock.
The $500,000 tester deposit prevents margin constraints from changing this fixed-size benchmark;
these dollar results are not account-percentage returns.

## Exact rules and interpretation

- Raw hold: one buy at 1,832.00 on the first source quote, one tester-end sale
  at 30,819.00. The simple bid-to-bid calculation is
  (30,819.00 - 1,831.75) x $2 = $57,974.50, before the $0.50 entry spread.
- Rollover version: use all 67 contract periods in the saved roll schedule.
  Close on the last available quote of the old contract, reopen one contract on
  the first available quote of the next contract. Stay long across every other
  overnight/weekend gap. There are 66 switches and never more than one contract.
- The continuous file is unadjusted. Its $7,551.50 summed roll-boundary jumps
  contribute to the raw hold but not the close/reopen version. Another $33.00 of
  entry spreads and $69.30 of commission explain the **$7,653.80** net difference.
- Closing/reopening across adjacent source sessions is a boundary-roll model,
  not a simultaneous calendar-spread fill. It excludes the market move during
  the old-close/new-open interval too. Measuring simultaneous rolls would need
  both expiries' prices at the same time. Results use historical NQ prices with
  MNQ-sized economics, including dates before the micro contract existed.

## Native MT5 replay and checks

Both variants ran in Strategy Tester, M1 chart, one-minute OHLC model, no
optimization, remote agents, cloud, or live trading. The dedicated EAs reject
execution outside Strategy Tester. The roll schedule is embedded in the roll EA;
its exits use the modeled final quote, including sparse-minute :01/:30 closes.

MT5 initially skipped the first dataset day to obtain history. That diagnostic
run is preserved in `Reports/buy_hold_20261108/` but is **not** used above.
A separate `MNQ_BuyHold_20261108` custom symbol clones the research symbol and
adds 1,380 flat warm-up minutes on June 4, before the tested period. Every one of
the original 5,511,965 bars was read back and compared, including timestamps,
OHLC, both volumes, and spreads. All original bars are unchanged. Both final
runs open exactly at 2010-06-07 01:00:00.

`python/verify_buy_hold.py` independently derives the segment boundaries from
the original CSV and roll schedule, then checks all entry/exit times and prices,
position volumes and directions, profits, costs and the complete minute equity
path. Both native equity drawdowns match, and every fill passes.

Evidence under `Reports/buy_hold_20261108/exact_start/`:

- `buyhold_exact_20261108_hold.htm` and `buyhold_exact_20261108_roll.htm`: native reports.
- Matching `_deals.csv` and `_stats.csv`: native fill/statistics exports.
- `verification.json`: independent audit and final numbers.
- `expected_roll_trades.csv`: 67 source-price segments before spread and fees.
- `clone_verification.tsv`, `prepared.json`: source readback and frozen input hashes.
- `BuyHoldExact20261108_hold.mq5` and `BuyHoldExact20261108_roll.mq5`: exact replay sources.

Preparation and native runners: `python/run_buy_hold.py` (initial diagnostic),
`python/run_buy_hold_rolls.py` (exact-start clone and final hold/roll jobs).
Completed runs are preserved; recheck with:

```powershell
.\venv\Scripts\python.exe python\verify_buy_hold.py
```

No strategy baseline changed.


[Matched RTL/GG baseline comparison](COMPARISON.md): full-history profit trails
buy-and-hold with rollovers but DD is lower; since 2020, both baselines outperform
that benchmark in net dollars as well as equity DD.


## Daily session flatten/reopen extension (2026-11-09)

A third native benchmark reopens one long at every session start and closes at
the standard 23:30 cutoff (earlier on calendar early closes). Full dataset:
4,203 positions, $51,508.00 gross, $47,094.85 net after $1.05 per position, and
$13,266.05 cost-adjusted equity DD. Since 2020: $35,965.20 net with the same DD.
All fills and native gross DD ($13,023.50) verified. This does not improve profit
or drawdown over holding through sessions with rollovers. The [full comparison](COMPARISON.md)
includes it alongside RTL/GG and both VWAP variants.

Native report: `Reports/buy_hold_20261108/session_flat/buyhold_session_20261108.htm`.
