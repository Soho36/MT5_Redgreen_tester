# Standalone buy-limit entry — 2026-10-02

**Result: mixed periods; keep as a research variant, without changing the
baseline.** All three offsets make money in 2020–2026 but lose after costs in
2016–2019. The primary 90% offset earns $7,021 recently with $1,118 closed-trade
drawdown; earlier it loses $2,951. Its recent net/DD remains below the buy-stop
control despite the much smaller dollar drawdown.

## What was tested

Found the earlier implementation in `mt5/archive/RR_r_MFE_limit-entry.cs`.
This screen follows its trigger: a qualifying red M30 candle arms a setup;
after ask reaches the candle high, place one buy limit. **No buy-stop order or
initial position is opened by the limit variants.**

Entry = high − offset × candle range. Thus 90% means 10% of the range above
the candle low. Stop remains the low; the target remains the original
high + full candle range, checked at bar close. For example, H=100, L=90 gives
limit=91, stop=90, target threshold=110. Tick rounding and existing session /
red-run rules are retained. Full definitions: [protocol](PROTOCOL.md).

Per the user's request, all eight runs use **1-minute OHLC**. No generated-tick
tests were run for this standalone experiment. One MNQ-priced contract,
MaxRedRun=3, original bar-close target, early-close calendar and session flatten.
Costs below deduct $1.05 per completed contract. Dates: 2016-01-01 to 2020-01-01,
then 2020-01-02 to 2026-07-14, on `MNQcontDTBNT20102026_2`.

## Raw results after costs

DD is maximum drawdown of the closed-trade net balance, not intratrade equity.

| Period | Entry | Trades | Net $ | PF | DD $ | Net/DD | Win rate |
|---|---|---:|---:|---:|---:|---:|---:|
| 2016–2019 | Buy-stop control | 5,697 | 6,485.15 | 1.106 | 1,435.30 | 4.52 | 43.4% |
| 2016–2019 | Limit 80% | 3,553 | −3,058.15 | 0.769 | 3,076.90 | −0.99 | 8.8% |
| 2016–2019 | **Limit 90%** | 3,181 | **−2,950.55** | **0.633** | **3,035.20** | **−0.97** | **5.1%** |
| 2016–2019 | Limit 95% | 2,990 | −2,565.00 | 0.550 | 2,664.20 | −0.96 | 3.4% |
| 2020–2026 | Buy-stop control | 9,271 | 37,980.95 | 1.107 | 4,847.40 | 7.84 | 43.0% |
| 2020–2026 | Limit 80% | 5,213 | 5,131.35 | 1.090 | 2,114.30 | 2.43 | 10.1% |
| 2020–2026 | **Limit 90%** | 4,623 | **7,021.35** | **1.242** | **1,117.65** | **6.28** | **6.3%** |
| 2020–2026 | Limit 95% | 4,331 | 5,993.45 | 1.363 | 1,007.40 | 5.95 | 4.3% |

The intended payoff shape appears: many small losses and rare large winners.
For 90%, only 5.1% / 6.3% of trades win after costs. The earlier period earns
just $389.50 gross across 3,181 trades; $3,340.05 of commission turns that into
a $2,950.55 net loss. All three offsets lose in **each** year from 2016 to 2019.

## Annual net dollars

2026 is partial through the July endpoint. These years have already been
examined in prior research; the recent period is not untouched validation data.

| Year | Limit 80% | Limit 90% | Limit 95% |
|---|---:|---:|---:|
| 2016 | −1,194.20 | −802.25 | −614.45 |
| 2017 | −950.70 | −730.80 | −818.35 |
| 2018 | −129.40 | −514.75 | −351.25 |
| 2019 | −783.85 | −902.75 | −780.95 |
| 2020 | −898.45 | −219.95 | 41.60 |
| 2021 | 285.60 | 795.25 | −22.40 |
| 2022 | 1,698.35 | 3,546.30 | 3,870.05 |
| 2023 | 898.90 | 940.15 | 1,254.65 |
| 2024 | 1,467.50 | 393.00 | −142.70 |
| 2025 | 3,284.40 | 1,788.20 | 692.35 |
| 2026 | −1,604.95 | −221.60 | 299.90 |

## Interpretation and approximation

This is not an extraction of the earlier averaging leg. The standalone strategy
can accept new setups while the buy-stop strategy would still be holding a
position. Also, its trigger observes a quote at the signal high, whereas the
averaging version requires an actual initial fill and uses that fill's risk.
That changes trade selection and can explain why recent standalone results
are positive while the averaging add-on was negative. It does not establish
which particular difference caused the gain.

With an additional $1 cost per trade, recent net becomes −$81.65 / $2,398.35 /
$1,662.45 for 80% / 90% / 95%. Earlier results all remain negative. This is
a simple cost stress, not a simulation of queue position or order slippage.

At 90%, 1,195 of 3,181 earlier trades (37.6%) and 1,285 of 4,623 recent trades
(27.8%) open and close within the same minute. OHLC therefore leaves material
fill/stop-ordering uncertainty exactly where this approach trades. These are
the requested raw results, with that approximation accepted; finer testing is
not an automatic next step.

Average net R measured against the actual limit-entry-to-stop risk is
−1.035 / +0.216 for the primary variant. Small stops magnify commissions and
gap losses in this metric. Against full signal-candle risk, those averages are
−0.148 / +0.021. No equal-dollar-risk sizing was applied.

MT5 gross equity drawdown for 90% is $504.50 / $1,230.00. It excludes the
externally deducted commission, so it must not replace net balance DD above.

## Verification and files

- Compilation: zero errors, zero warnings. Existing eight Python tests pass.
- All eight CSV exports reconcile to MT5 trade counts and gross PnL, and to
  every paired entry/exit deal in the complete HTML reports. No recovery needed.
- Both controls reproduce the previous OHLC baseline's trade times, PnL,
  excursions and signal features. Every variant buy order is a buy limit.
- One contract per trade, no averaging, no cross-date trades. Signal levels,
  limit rounding, trigger/entry sequence and original target are checked.
- Zero order rejections or cancellation errors. One invalid-level setup is
  skipped in each earlier variant; none in recent variants.

`python/prepare_limit_only_study.py` creates a tester-only EA from the baseline;
`mt5/experts/limit_only_research.mqh` supplies the standalone entry logic.
`Reports/limit_only_20261002/RTL_limit_only.mq5` and `.ex5` are the generated
source and compiled EA. The same folder holds the frozen manifest, INIs,
logs, reports, CSVs and `results.json`.

`WaitForHigh=false` is implemented for immediate placement and the preparer
has a separate `--immediate` output folder. **Immediate placement has not been
backtested in this study.** The production baseline and archived EA are unchanged.

## Follow-up 2026-10-02: 80% offset with RR 2 → rejected

The user ran 80% with `RiskReward=2` on 2020–26 (5,115 trades, $14,213.50 gross). A
control run in `Reports/limit80_rr2_20261002/` reproduces it exactly; the same settings
were then run on 2016–19.

| Period | Trades | Gross $ | Net $ ($1.05/trade) | Net PF | Net DD $ | Losing years |
|---|---:|---:|---:|---:|---:|---|
| 2020–26 | 5,115 | 14,214 | 8,843 | 1.155 | 2,069 | 2 of 7 |
| 2016–19 | 3,478 | 541 | **−3,111** | **0.765** | 3,225 | **4 of 4** |

Also checked on the 2020–26 run:
- **Fills are realistic.** Every fill came after the market traded at least one tick *below*
  the limit, so a real resting order would have filled. Median stop is 18 ticks; commission
  is 12% of risk. Only 14% of trades open and close in the same minute, none of them winners.
- **Concentrated:** the top 20 of 5,115 trades make $12.9k gross, more than the whole net.
  With $1 extra slippage per trade, net is $3.7k.
- **Not a diversifier:** daily P&L correlates +0.34 with the buy-stop baseline. Running both
  lowers net/DD from 8.73 (baseline alone) to 7.77.

**Decision: rejected.** It loses in every 2016–19 year, like every other limit variant, and
in 2020–26 it is weaker than the baseline and doesn't help alongside it.

To reproduce the saved audit:

```powershell
.\venv\Scripts\python.exe python\analyze_limit_only_study.py
```
