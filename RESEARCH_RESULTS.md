# RTL (Red-Green Breakout) on MNQ: entry-filter research results

Status as of 2026-09-29. **Everything below is in-sample.** No filter has been
validated out-of-sample yet (see [Next steps](#next-steps)).

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

**Current best candidate: `MaxRedRun = 2` + `MinLocation ≈ 0.15`.** It keeps net
profit flat (or slightly up) and roughly **halves max drawdown** versus baseline.
Results for t = 0.10–0.20 are nearly identical, so the result doesn't depend on
the exact number. 0.15 sits in the middle of that range rather than being the
single best row.

### Other features: no usable signal in 2020–2026

`rel_size` (signal range vs recent average), `close_loc` (where the signal
closed within its own candle), `vol_regime`, `bar2` (inside/outside bar vs
previous) and `fill_delay` (bars until the stop filled) showed no stable
losing group. `bar2 = inside` looked good (PF 1.24) but was unstable across
halves (1.04 / 1.43).

## Caveats

1. **All numbers are in-sample.** The 0.15 cutoff and `MaxRedRun = 2` were
   both read off the same 2020–2026 data they are scored on.
2. **Post-hoc vs live:** the table removes trades after the fact. In MT5 a
   filtered-out signal can let a *different* order trigger instead, so live
   results will differ slightly. For `MaxRedRun` the two differed by about 0.6%.
3. **Max DD is a single path statistic.** It is noisy; compare PF across both
   halves first.
4. **Commission** is modelled as a flat $1 per trade.

## Next steps

1. **Confirm in MT5** with `RR_r_MFE_buy-stop-entry_runband.cs`: the backtest
   EA `RR_r_MFE_buy-stop-entry.cs` plus `MinRedRun` / `MaxRedRun`,
   `MinLocation` (0 = off) and `LocationLookback` (20). With all filters off it
   trades exactly like the base EA, so the first check is that a run with
   filters off reproduces the base result. Then run `MaxRedRun = 2` with
   `MinLocation` ∈ {0, 0.10, 0.15, 0.20}, with commission set in the tester.
   Output: `runband_<windows>_<RR>.csv` in Common\Files, with `red_run` and
   `location` columns.
2. **Out-of-sample test on 2010–2019.** None of these years were used for the
   location analysis. If `red_run ≤ 2` + `location ≥ 0.15` also improves
   PF and DD there, that's the first real confirmation.
3. Later: walk-forward, then exit/trade-management research using the MAE/MFE
   columns.

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
