# RTL (Red-Green Breakout) on MNQ: entry-filter research results

> **Summary** (added 2026-10-01; [project status](../STATUS.md))
> - Of all the entry filters tried (min red count, drop %, location, 10 bar
>   features), only the **red-run cap** survived. `MaxRedRun = 3` was chosen on
>   2015–19 and passed a frozen 2020–26 test, but the effect is small (PF/DD, not profit).
> - Location looked good after the fact but failed in full MT5 runs. Differences
>   were within noise.
> - 2010–2014 has no edge before costs. 2015 onwards resembles today.
> - This file is the chronological log of those studies. Later work is linked from STATUS.

Update 2026-09-30: the [first interrupted-decline and low-recovery study](../baseline/q01-q02-preceding-candles/RESULTS.md)
is complete at N=5,10,20,50 on actual cap-3 trades. Neither new filter was
adopted: recent-period associations failed to establish consistent support
in the earlier period. Remaining questions are tracked in
[RESEARCH_QUESTIONS.md](RESEARCH_QUESTIONS.md).

Historical status as of 2026-09-29. The feature discovery and post-hoc tables are
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

### Independent re-check and noise level (2026-09-29)

Re-running `verify_location_validation.py` passed all checks and reproduced
every number in the tables above.

**How big is noise?** The per-trade net std is about $116. Comparing two runs
through the trades that differ between them (trades removed + new trades):

| Change | Removed | New | Net change | ≈1 s.e. | z |
|---|---:|---:|---:|---:|---:|
| off → `MaxRedRun=2` | 2,858 | 1,060 | +$5,148 | $7,268 | +0.7 |
| `MaxRedRun=2` → + `MinLocation=0.10` | 870 | 314 | +$456 | $3,995 | +0.1 |
| `MaxRedRun=2` → + `MinLocation=0.15` | 1,398 | 451 | −$2,854 | $4,993 | −0.6 |

- **None of the net-profit differences are distinguishable from noise.** The
  ranking of 0.10 / 0.15 / 0.20 by profit is noise. Location as a filter is
  not supported: keep `MinLocation = 0`.
- **For `MaxRedRun = 2`, the evidence is the risk profile, not profit:** PF
  1.09 → 1.14 with **both halves improving** (1.06 → 1.14, 1.12 → 1.14), and
  balance DD 6.2k → 3.7k with 18% fewer trades.
- **The live filter changes trades a lot:** `MaxRedRun = 2` removed 2,858
  baseline trades but created 1,060 new ones. Signals that were skipped left the
  position free for later ones. Post-hoc subset tables can't predict this, so
  always confirm filters as real MT5 runs.
- **2010–2019 with `MaxRedRun = 2` is breakeven after commission** (PF 1.005;
  first half 0.83). There is no filters-off MT5 run for 2010–2019 with these
  settings. The old `trade_stats_rr_1.0.csv` used different settings (its 2020+
  part has 8,251 trades, not 10,022), so it can't serve as the baseline. That
  run (`early_off`) was done next; see the following section.

### 2010–2019 baseline (`early_off`) and the two regimes (2026-09-29)

MT5 run `early_off`: the same INI as `early_red2_loc0` with `MaxRedRun=0`, same
EA build. 15,077 trades, gross 13,995.5, gross PF 1.122. The CSV reconciles
with MT5 stats. Files are in `Reports/location_validation_20260929/`.

| Period | Rule | Trades | Gross $ | Gross PF | Gross avgR | Net $ | Net PF | Net DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2010–2014 | off | 7,411 | 893 | 1.024 | +0.000 | −6,518 | 0.843 | 6,826 |
| 2010–2014 | red ≤ 2 | 6,244 | 524 | 1.017 | −0.005 | −5,720 | 0.831 | 6,016 |
| 2015–2019 | off | 7,666 | 13,102 | 1.168 | +0.080 | 5,436 | 1.066 | 2,122 |
| 2015–2019 | red ≤ 2 | 6,412 | 12,594 | 1.203 | +0.096 | 6,182 | 1.094 | 1,636 |
| 2020–2026 | off | 10,022 | 47,526 | 1.120 | +0.071 | 37,504 | 1.093 | 6,174 |
| 2020–2026 | red ≤ 2 | 8,224 | 50,876 | 1.167 | +0.095 | 42,652 | 1.138 | 3,660 |

- **2010–2014: the strategy has no edge even before costs** (gross avgR 0.000),
  with or without the cap. This is a different regime. Optimizing filters
  there would be fitting noise.
- **From 2015 on, the gross edge is similar to today** (avgR +0.08 vs +0.07).
  `MaxRedRun=2` improves gross PF and net DD in both 2015–2019 and 2020–2026.
- **By year (gross PF):** the cap is better in 10 of 17 years, and in 8 of 12
  from 2015 on. That's a consistent tilt but not a strong one; single years are
  noisy.
- **Commission is distorted in early years.** Average risk per trade was only
  $7–15 in 2010–2017, so $1 commission cost 0.12–0.22R per trade. In 2020+ it's
  0.01–0.03R. MNQ only launched in 2019, so early-period net $ is hypothetical.
  **Compare regimes on gross R / gross PF**, and apply commission only where
  it's realistic.
- **Not out-of-sample for red-run:** `MaxRedRun` was originally chosen on
  2010–2026 data, so both periods had been seen. A clean test needs the value
  chosen on one period only (train) and then frozen for the next (test). See
  Next steps.

```powershell
.\venv\Scripts\python.exe python\verify_location_validation.py Reports/location_validation_20260929
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
4. **Completed:** `early_off` 2010–2019 baseline. 2010–2014 has no gross
   edge; from 2015 on it matches today. `MaxRedRun=2` helps in 2015–2019 and 2020+.
5. **Proposed: a train/test test of `MaxRedRun`.** Choose the value on
   **2015–2019 only**, using gross PF / gross avgR as the criterion, decided
   *before* looking. Then run that frozen value on 2020–2026 and compare it with
   filters off. Skip 2010–2014, which has no edge to filter. Run each value as
   its own MT5 single test with its own `RunTag`: optimization passes share one
   RunTag and would overwrite each other's CSVs. Caveat: we already know `2`
   works in 2020+, so this is an honest parameter test, not a discovery test.
   **Selection rule, fixed before running (2026-09-29):** single MT5 tests on
   2015-01-01 → 2020-01-01 with `MaxRedRun` ∈ {0 (off), 1, …, 7}, all else as
   in `early_off.ini`. Winner = highest **gross PF**. A tie within 0.005 goes
   to the larger `MaxRedRun` (the less restrictive filter). The winner is then
   frozen and run once on 2020–2026, and compared with filters off.

   **Training result (2015–2019, 8 single MT5 tests, in
   `Reports/maxredrun_train_20260929/`; reproduce with
   `evaluate_maxredrun_train.py`):**

   | MaxRedRun | off | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
   |---|---:|---:|---:|---:|---:|---:|---:|---:|
   | Trades | 7,666 | 4,869 | 6,412 | 7,052 | 7,389 | 7,535 | 7,601 | 7,645 |
   | Gross $ | 13,102 | 9,918 | 12,594 | 15,060 | 14,432 | 13,928 | 13,288 | 12,720 |
   | Gross PF | 1.168 | **1.223** | 1.203 | **1.220** | 1.197 | 1.184 | 1.173 | 1.164 |
   | Net DD | 2,122 | 1,261 | 1,636 | 1,382 | 2,023 | 1,998 | 2,014 | 1,980 |

   The filters-off run matches the 2015–2019 part of `early_off` exactly. By
   the fixed rule, the best is 1.223 (cap 1), and cap 3 is within 0.005, so the
   tie goes to the larger cap. **Winner: `MaxRedRun = 3`.** Every cap from 1 to 6
   beats off, but the curve isn't smooth (2 is below both 1 and 3), so caps 1–3
   can't really be told apart.

   **Frozen test, 2020-01-02 → 2026-07-14** (a fresh filters-off run reproduced
   the earlier baseline exactly):

   | Rule | Trades | Gross $ | Gross PF | Gross avgR | Net $ | Net PF | Net DD |
   |---|---:|---:|---:|---:|---:|---:|---:|
   | off | 10,022 | 47,526 | 1.120 | +0.071 | 37,504 | 1.093 | 6,174 |
   | `MaxRedRun=3` (frozen) | 9,147 | 46,438 | 1.132 | +0.084 | 37,291 | 1.105 | 5,134 |
   | *`MaxRedRun=2` (for reference; chosen with 2020+ seen)* | *8,224* | *50,876* | *1.167* | *+0.095* | *42,652* | *1.138* | *3,660* |

   - **Out of sample, the cap helps a little and in the right direction:** gross
     PF is higher in **6 of 7 test years**, avgR +0.071 → +0.084, and net DD is
     17% lower. Net profit is unchanged ($−214, z ≈ 0.0).
   - **In 2020+, cap 2 looks much better than cap 3,** but 2 was picked with
     2020+ data in view, and in 2015–2019 caps 1–3 were indistinguishable. Most of
     cap 2's extra gain in 2020+ should be treated as optimism from having chosen it
     with that period in view, not as evidence that 2 is better than 3.
   - **Conclusion:** capping deep red runs is a real but **small** effect that
     survives a clean out-of-sample test. It mainly improves risk (PF, DD), not
     profit. Any cap in the 2–3 range is defensible; don't expect the in-sample
     2020+ numbers for cap 2 to repeat.
6. Later: walk-forward (e.g. train 3 years → test the next year, rolling), then
   exit/trade-management research using MAE/MFE.

## Project organization

See [the root README](../../README.md) for the current directory layout. MT5 sources
are in `mt5/experts/`, Python tools in `python/`, older strategies in
`mt5/archive/`, and historical CSVs in `data/legacy/`. Paths in command examples
are relative to the project root; `Reports/` remains there.

The next four questions are tracked in [RESEARCH_QUESTIONS.md](RESEARCH_QUESTIONS.md).

## How to reproduce

```
# 1. MT5: run RR_r_MFE_buy-stop-entry_features.cs (writes features_<windows>_<RR>.csv to Common\Files)
# 2. Feature scan (auto-finds the newest features_*.csv):
.\venv\Scripts\python.exe python\analyze_features.py --commission 1
.\venv\Scripts\python.exe python\analyze_features.py --feature location --commission 1
.\venv\Scripts\python.exe python\analyze_features.py --list
# 3. Red-run analysis on a runband CSV:
.\venv\Scripts\python.exe python\analyze_runlength.py data\legacy\trade_stats_rr_1.0.csv --commission 1
```
