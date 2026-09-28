# RTL (Red-Green Breakout) on MNQ: entry-filter research results

Status as of 2026-09-29. The feature discovery and post-hoc tables are
**in-sample**. Actual MT5 reruns and a frozen location check on 2010–2019 are
now recorded under [MT5 confirmation](#mt5-confirmation-2026-09-29).
**The reruns do not support adopting 0.15 as the default.** Earlier years were
unused for location discovery but were used to select the red-run cap, so this
is a holdout for the added location rule, not for the entire strategy.

## The strategy being filtered

- Signal: the last closed candle is **red**.
- Entry: buy stop at the red candle's high (`h1`). Stop loss at its low (`l1`).
  Risk = candle range.
- Exit: close at bar close once price reaches `entry + RiskReward × risk`
  (RR = 1.0 in all tests), or flatten at 23:30.
- **R-multiple** = profit ÷ (candle_range × $2/point). It's the trade result in
  units of its own risk. We judge filters on R, PF and total $, **never on
  avg $/trade**, because avg $ rises when bigger candles give bigger bets (see
  drop % below).
- **Commission matters:** about $1 per round-turn at 1 lot cuts PF from about
  1.13 to 1.08 on the long history, roughly 40% of the edge. The strategy is
  thin, so a filter must remove *bad* trades, not just *fewer* trades.

## Research rule that has held up so far

> Filters that require **more** of something before entry (more reds, bigger
> drop) don't help. What works is finding a **subset of trades that is
> net-losing or breakeven**, consistently in both halves of the history, and
> excluding it.

## Findings

### 1. Filters that did NOT help (2010–2026 data, about 21k trades)

| Filter | Result |
|---|---|
| Min red-candle count (`RedCandleSequence`) | Requiring more reds degrades results steadily. Best at 1. Only thins trades. |
| Drop magnitude (% fall before entry) | corr(drop %, R) ≈ 0.00. Bigger drops earn more $ only because the candle, and so the bet, is bigger. No edge in R. |

### 2. Red-run cap (`MaxRedRun`): first real improvement (2010–2026)

`red_run` = number of consecutive red candles ending at the signal. A green
candle stops the count, and the signal itself counts as 1.

- Runs 6–7 were genuine net losers (avgR −0.32 / −0.12, PF 0.77 / 0.56). Runs
  1–2 were the best.
- Gross results by `MaxRedRun`, confirmed by both the Python post-hoc sweep and
  MT5 optimization:
  **5** = max profit (52.8k, DD 7.80% vs 9.10%), **4** = balanced
  (52.1k, PF 1.15, DD 7.45%), **2** = best risk-adjusted (47.1k, DD 5.12%).

### 3. Bar-feature scan (2020-01 to 2026-07, 10,022 trades, net of $1 commission)

Tools: `RR_r_MFE_buy-stop-entry_features.cs` logs the raw OHLC of the last 30
bars at order placement. `analyze_features.py` tests 10 bar-only features
(no indicators), **each one on its own**. It checked that every logged snapshot
lines up with its trade (100% match).

Baseline for this period: **net 37,504, PF 1.09** (1st half 1.06 / 2nd half
1.12), avgR +0.047, max DD 6,174.

- **No single feature produced a bucket that loses money in both halves.**
  The largest deviation was |z| 2.6, which is within chance for about 45 buckets.
- **But one theme runs through several correlated features:**
  `location`, `trend_eff`, `room`, `sweep` and `red_run` all say that
  **falling-knife signals** (closing at the bottom of the recent range, after a
  downtrend, far below recent highs) trade at about **breakeven**, while
  **shallow pullbacks** trade best. `location` and `trend_eff` have Spearman
  correlation +0.82, so they are essentially the same measurement.
- **Red-run is weaker in this period.** In 2020+ alone the old "runs 6–7 lose"
  result is faint: run 6 PF 0.59 in the 1st half but 1.03 in the 2nd, and only
  179 trades. Treat `MaxRedRun` as possibly period-dependent.

#### What `location` is

`location = (close of signal − 20-bar low) / (20-bar high − 20-bar low)`, over
the last 20 bars including the signal. 0 means the signal closed at the 20-bar
low (falling knife). 1 means it closed at the 20-bar high (a small dip in an
uptrend).

#### Location in 10% slices (net PF)

| location | all trades | inside `red_run ≤ 2` |
|---|---|---|
| 0.0 – 0.1 | **0.98** | **0.98** |
| 0.1 – 0.2 | **1.01** | **1.04** |
| 0.2 – 0.3 | 1.18 | 1.20 |
| 0.3 – 0.4 | 1.12 | 1.10 |
| 0.4 – 0.5 | 1.11 | 1.15 |
| 0.5 – 0.6 | 1.24 | 1.36 |
| 0.6 – 0.7 | 1.16 | 1.22 |
| 0.7 – 0.8 | 1.05 | 1.13 |
| 0.8 – 0.9 | 1.23 | 1.23 |
| 0.9 – 1.0 | 1.19 | 1.18 |

**The weakness is only in the bottom 20%.** Above 0.2 there is no slope, and
every slice is profitable. A signal at 23% is *not* worse than one in the middle.

#### Location on top of `red_run ≤ 2`

Only 47% of the bottom-of-range trades (`location < 0.13`) are already
removed by `red_run ≤ 2`, so the two filters are **not redundant**.

| Keep only (net, $1 commission) | Trades | Net $ | PF | PF 1st / 2nd | Max DD | Net / DD |
|---|---|---|---|---|---|---|
| baseline | 10,022 | 37,504 | 1.09 | 1.06 / 1.12 | 6,174 | 6.1 |
| `location ≥ 0.13` | 8,025 | 38,910 | 1.13 | 1.11 / 1.15 | 5,084 | 7.7 |
| `red_run ≤ 2` | 7,263 | 38,376 | 1.14 | 1.13 / 1.15 | 4,601 | 8.3 |
| `red_run ≤ 2` + `location ≥ 0.10` | 6,481 | 39,080 | 1.17 | 1.17 / 1.16 | 3,138 | 12.4 |
| `red_run ≤ 2` + `location ≥ 0.15` | 6,026 | 38,604 | 1.18 | 1.17 / 1.19 | 3,466 | 11.1 |
| `red_run ≤ 2` + `location ≥ 0.20` | 5,639 | 37,525 | 1.19 | 1.18 / 1.20 | 3,326 | 11.3 |

**Original post-hoc candidate: `MaxRedRun = 2` + `MinLocation ≈ 0.15`.** It keeps net
profit flat (or slightly up) and roughly **halves max drawdown** versus baseline.
Results for t = 0.10–0.20 are nearly identical, so the result doesn't depend on
the exact number. 0.15 sits in the middle of that range rather than being the
single best row. **Superseded by the actual MT5 results below:** the apparent
plateau in these subsets does not carry over to the full strategy.

### Other features: no usable signal in 2020–2026

`rel_size` (signal range vs recent average), `close_loc` (where the signal
closed within its own candle), `vol_regime`, `bar2` (inside/outside bar vs
previous) and `fill_delay` (bars until the stop filled) showed no stable
losing group. `bar2 = inside` looked good (PF 1.24) but was unstable across
halves (1.04 / 1.43).

## MT5 confirmation (2026-09-29)

Tested the base EA and the runband EA on `MNQcontDATABENTOcurr6`, M30,
2020-01-02 through 2026-07-14, using the saved feature-run settings:
1-minute OHLC modelling, RR 1, 1 lot, zero execution delay, $500,000 starting
deposit, entries from 01:00 through 23:30, flatten at 23:30, range filter off.
These are actual strategy reruns, not subsets of the baseline trade list.

**Costs and drawdown:** MT5 ran with zero native commission. The figures below
deduct the same modeled $1 round-turn per completed trade used in the research.
DD is the maximum **closed-trade balance drawdown after that deduction**, not
MT5 floating equity DD. Gross MT5 equity DD is retained in `summary.json`.
This confirms the research's cost model; it does not validate broker charges,
real-tick fills, or additional slippage.

| Actual MT5 strategy | Trades | Net $ | Net PF | PF 1st / 2nd | Net balance DD | Net / DD |
|---|---:|---:|---:|---:|---:|---:|
| Base / runband filters off | 10,022 | 37,504.50 | 1.093 | 1.058 / 1.123 | 6,174.00 | 6.07 |
| `MaxRedRun=2`, `MinLocation=0` | 8,224 | 42,652.50 | 1.138 | 1.139 / 1.136 | 3,660.50 | 11.65 |
| `MaxRedRun=2`, `MinLocation=0.10` | 7,668 | 43,108.50 | 1.155 | 1.176 / 1.138 | 3,219.00 | 13.39 |
| `MaxRedRun=2`, `MinLocation=0.15` | 7,277 | 39,798.50 | 1.154 | 1.166 / 1.143 | 3,626.00 | 10.98 |
| `MaxRedRun=2`, `MinLocation=0.20` | 6,901 | 40,335.00 | 1.168 | 1.180 / 1.158 | 3,640.00 | 11.08 |

The chronological split is fixed at the median entry time of the original
baseline for every recent case, rather than changing it for each filter.

**Interpretation:** red-run alone performs materially better than its post-hoc
subset (8,224 actual trades versus 7,263 retained baseline trades). Rejecting
signals changes subsequent position availability and pending orders. The old
claim that this difference should be only about 0.6% is not applicable here.
Against actual red-run alone, 0.10 adds $456 (+1.1%) and reduces balance DD
12.1%; most of its PF gain is in the first half. At 0.15, profit falls $2,854
(-6.7%) and balance DD improves only 0.9%. At 0.20, profit falls 5.4% and DD
improves only 0.6%. The location idea remains testable, but 0.15 is not confirmed.

### Earlier-history check with the fixed 0.15 threshold

Requested dates: 2010-01-02 through 2020-01-01; actual trades start in June
2010 because that is where the available custom history begins. Same settings
and $1/trade model; `MaxRedRun=2` in both runs. No threshold search on this period.

| Rule | Trades | Net $ | Net PF | Net balance DD |
|---|---:|---:|---:|---:|
| No location filter | 12,656 | 461.00 | 1.005 | 6,258.50 |
| `MinLocation=0.15` | 11,212 | -50.00 | 0.999 | 5,698.00 |

The added 0.15 rule does not improve net expectancy here. Both results are
around breakeven after the assumed commission; neither supports a robust
historical net edge in this period. A smaller drawdown with fewer trades is
insufficient evidence by itself. This is an incremental location holdout;
red-run was previously studied on these years.

### Implementation and verification

The runband source already contained `MinLocation=0` (off),
`LocationLookback=20`, the signal-inclusive formula, cancellation on a rejected
red signal, and per-trade location logging. Validation hardened that implementation:

- Require the full closed-bar window and skip signals with unavailable location
  when the filter is enabled. Validate threshold [0,1] and lookback >= 1.
- Log location to 10 decimal places and include filter inputs in tester stats.
- Write the header for a new UTF-16 CSV even when its BOM occupies two bytes.
- Flush a tracked close in `OnTester` so a close without a subsequent tick is
  exported. This recovered one $10 trade in the earlier red-run-only run.

Compiled with MetaEditor: **0 errors, 0 warnings**. Checks in
`verify_location_validation.py` confirm:

- Filters off reproduce all 10,022 base trades, including MAE/MFE, exactly.
- All 10,022 exported location values match the original 20-bar OHLC snapshots
  (maximum difference 5e-11, from CSV rounding).
- Trade counts and gross PnL reconcile to MT5 for all eight cases.
- Every filtered trade satisfies its red-run and location inputs.

Artifacts are in `Reports/location_validation_20260929/`: the compiled EA,
compiler logs, tester INIs, original CSVs, reports, and `summary.json`/`summary.csv`.
The tested expert is installed in the AMP terminal's
`MQL5/Experts/CodexLocationValidation/RTL_runband_location.ex5`.

```powershell
.\venv\Scripts\python.exe verify_location_validation.py Reports/location_validation_20260929
```

## Caveats

1. **Discovery numbers are in-sample.** The 0.15 cutoff and `MaxRedRun = 2`
   were both selected with knowledge of the recent data they are scored on.
   The earlier-period check holds out location only, as explained above.
2. **Post-hoc vs strategy reruns:** the discovery table removes trades after
   the fact. A filtered-out signal can let different orders trigger. The actual
   MT5 runs above demonstrate that the difference can be substantial.
3. **Max DD is a single path statistic.** It is noisy; compare PF across both
   halves first.
4. **Commission** is modelled as a flat $1 per trade.

## Next steps

1. **Completed:** MT5 baseline parity, red-run-only, and thresholds 0.10,
   0.15, 0.20; the costs are modeled in Python, not configured in the tester.
2. **Completed:** frozen 0.15 check on 2010–2019. It failed to improve net PF
   or profit. Keep `MinLocation=0` as the default.
3. If pursuing 0.10, label it a new candidate selected using the recent MT5
   results. Validate it on fresh chronological data with realistic execution
   and costs; do not present these reruns as out-of-sample confirmation.
4. Later: walk-forward, then exit/trade-management research using MAE/MFE.

## How to reproduce

```
# 1. MT5: run RR_r_MFE_buy-stop-entry_features.cs (writes features_<windows>_<RR>.csv to Common\Files)
# 2. Feature scan (auto-finds the newest features_*.csv):
.\venv\Scripts\python.exe analyze_features.py --commission 1
.\venv\Scripts\python.exe analyze_features.py --feature location --commission 1
.\venv\Scripts\python.exe analyze_features.py --list
# 3. Red-run analysis on a runband CSV:
.\venv\Scripts\python.exe analyze_runlength.py trade_stats_rr_1.0.csv --commission 1
```
