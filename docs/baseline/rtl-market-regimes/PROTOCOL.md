# RTL daily trend x volatility: frozen first-stage protocol

2026-10-23. Frozen before calculating six-group outcomes. RTL only.
[Full plan](PLAN.md). Descriptive historical screen, not an adopted gate.

## Baseline and provenance

Saved run: Reports/timeframe_baseline_20261015/
runband_tf_20261015_rtl_m30_rr1p0_1.00.csv, matching MT5 HTML, stats, INI, manifest
and completion hashes. MaxRedRun=0, MinLocation=0, one MNQ-valued contract
($2/price point), original stop, 1R bar-close exit, flatten fallback and early-close
calendar. Reconcile whole-run count/gross PnL and 2016-19 / 2020+ slices to saved
uncapped baselines. No GG. No entry/exit optimization. Hash protocol, inputs, outputs.

Primary eras: **2016-01-01 <= session < 2020-01-01** and
**2020-01-01 <= session < 2026-10-01**. Show annual rows; 2026 is partial.
The source ends 2026-10-01 02:59. Its final trade has an 'end of test' liquidation:
exclude the incomplete date from primary inference, show separately to reconcile
published totals. Pre-2016 supplies indicator warmup only.

Clock: Chicago + 8 hours. Session is source calendar date with minutes before
01:00 excluded, as in trend_regimes.py. No weekend/holiday forward filling.
Recover actual buy-stop submission, planned entry and stop from MT5 orders linked
by ledger ticket. Labels freeze at submission, not fill/exit. Audit no cross-date
orders or positions. Daily closes may be rebuilt from saved M30 reference, with
independent reconciliation to daily_reference.csv and original minute source.

## Fixed labels

For submission session d, every price below is from a date strictly before d.

**Trend:** previous close AND previous SMA50 strictly above previous SMA200 = bull;
both strictly below = bear; otherwise neutral. Require 200 prior sessions.
Use the established raw continuous closes, not roll-adjusted spot prices.

**Volatility:** r_t = log(C_t / C_(t-1)); s_t = sample SD (ddof=1) of 20 session
returns ending t. At d compare s_(d-1) with the linear 75th percentile of the
**252 values s_(d-253) ... s_(d-2)**. Elevated iff strictly greater; ties normal.
Full warmup required. Never use whole-sample quantiles. Six groups:
bull/neutral/bear x normal/elevated. No group is presumed bad.

**Predeclared sensitivities, never winner selection:**
1. 70th and 80th volatility percentiles, one at a time; other definitions fixed.
2. Roll-robust volatility: omit each contract-switch date's return; same 20-session
   SD window, at least 15 non-roll returns; same lagged 252-value 75th percentile.
   Keep established raw-price trend. Report label changes and sign stability.
3. Include final partial session only for endpoint reconciliation, not inference.

## Metrics and uncertainty

Base cost $1.05/completed trade. Extra $1 and $2/trade are cost stress allowances,
not measured slippage. R uses planned initial risk = (order entry - original stop)
x $2; verify against candle_range. Save fill price/risk separately if available.
Never treat realized fill slippage as known at submission.

For each group/era and annual rows: trades, active sessions/weeks, gross/net mean R,
net dollars, dollar PF, planned risk mean/median, commission/R, holding exposure,
worst day/week, mean worst 5% session outcomes, closed-trade and daily-close DD,
and daily-close DD duration. Daily measures use the same eligible-session calendar
including zero group-PnL dates. These are balance/daily-close, not intratrade MTM,
statistics. Group-subset drawdowns do not sum to portfolio DD.

Use 10,000 paired moving-block bootstrap draws of four consecutive calendar weeks,
circular wrapping, seed 20261023; preserve trades inside sampled weeks. Report 95%
intervals for group mean net R and difference from complement, plus 99.1667%
intervals (Bonferroni six-group family within each era). These are exploratory
uncertainty estimates, not untouched validation. Report invalid/degenerate draws.

Show dollars and R: negative mean R with positive dollars does not justify blanket
skipping in a one-contract strategy. Cost stress and planned risk clarify this.

## Fixed candidate screen and next stage

An **exploratory skip candidate** must meet all:
- At least 200 trades and 30 distinct active weeks in EACH primary era.
- Negative net dollars AND mean net R in both eras at base cost.
- Mean net R below its complement in both eras.
- At least five full years with >=30 group trades; at least 60% of those years
  have negative net dollars. Partial 2026 is excluded from this annual gate.
- Both eras retain negative group dollars and mean net R for EACH sensitivity:
  70th percentile, 80th percentile, roll-robust. Sparse variants are inconclusive
  (same >=200 trades / >=30 weeks requirement).

Report confidence intervals regardless of screening outcome. This is a screen,
not a statistical proof or live adoption gate. Do not optimize cutoffs, trend
lengths, group combinations or additional indicators after seeing outcomes.
If no group qualifies, plan steps 6-8 are **not triggered**. Record the null
result and discuss any separate risk-management hypothesis explicitly.

If any qualify, choose at most one using 2016-19 lowest mean net R (ties lexical),
acknowledging the both-era screen already used later history. Freeze pending-order,
position and restart policy before simulation. Compare chronological results,
profit retained, missed winners, static reduction and random block skipping,
then full MT5 replay. Ledger omission is not executable gating because order
availability changes. Fresh forward evidence is still required.

## Verification

Recompute daily labels independently from past arrays; test future perturbations
cannot change past labels. Audit order joins, known-at-submission timestamps,
no overlapping/cross-date positions, totals, cost/R arithmetic, exact partition,
roll dates and endpoint. Verify summary arithmetic independently of analysis code.
