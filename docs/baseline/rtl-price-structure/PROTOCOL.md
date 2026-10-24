# RTL price structure: frozen exploratory protocol

2026-10-24. Written before this study's conditional outcomes. User authorized the
four-point daily study and supplied an M30 wick/overlap example. Separate follow-up
to the [saved plan](../rtl-market-regimes/PLAN.md). Current uncapped RTL only.

## 1. Data and completed information

Use Reports/rtl_market_regimes_20261023/trades.csv, reconciled to original
timeframe_baseline_20261015 orders/deals and hashes. MaxRedRun=0, MinLocation=0,
original stop, 1R bar-close exit, one MNQ-valued contract ($2/point), $1.05 cost
per completed trade. Extra $1/$2 are cost stress allowances, not measured fills.
R denominator is planned initial risk. No live changes or entry optimization.

Eras: 2016-01-01 through 2019-12-31 and 2020-01-01 through 2026-09-30.
Pre-2016 is calibration/warmup. Exclude the incomplete 2026-10-01 tester session.
Screenshot dates Oct22-23 are beyond this source; it motivates the hypothesis,
but its exact candles cannot be tested here.

M30 OHLC: Reports/trend_rr_20261002/m30_reference.csv. Independently rebuild ALL
OHLC columns from original one-minute data. Source clock is Chicago + 8 hours;
exclude minutes before 01:00, matching the existing reference. Daily OHLC
aggregates observed bars by source date; these are research-session daily bars,
not necessarily a broker's D1 candles. No synthetic bars or M30 session resets.
Daily labels use strictly earlier dates. M30 labels use the last bar with
open time + 30 minutes <= actual buy-stop submission, including the completed
signal bar. Use as-of matching through gaps; never label at eventual fill.

## 2. Fixed measurements and four groups

Primary D1 n=20 completed sessions. Separately study M30 n=20 completed observed
bars for the user's intraday example. For BOTH, n=10/40 are sensitivities only.
- Efficiency E = abs(C[t]-C[t-n]) / sum(abs(C[i]-C[i-1]), i=t-n+1..t).
  Requires n+1 closes. All-zero changes give E=0.
- Pair overlap = max(0,min(H[i],H[i-1])-max(L[i],L[i-1])) /
  (max(H[i],H[i-1])-min(L[i],L[i-1])). Identical zero-span pair = 1.
  O = mean of n-1 internal adjacent pairs among the last n candles.
- Per-bar wick w = 1-abs(C-O)/(H-L); zero-range candle w=0 (no wick).
  W = mean w over n candles. Also record fraction with w>=0.80, descriptive only.
Small bodies and long total wicks are the same feature, not two confirmations.

For each timeframe/window separately, freeze linear E 1/3, O 2/3 and W 2/3
percentiles from ALL valid completed price windows available before 2016-01-01.
Equal weight per observed window, not per trade. Low E means <= cutoff;
high O/W means >= cutoff. Four exhaustive groups: low_eff_high_overlap (the
predeclared candidate), low_eff_other_overlap, other_eff_high_overlap,
other_eff_other_overlap. No later refitting or whole-evaluation quantiles.

## 3. Wick diagnostic and sensitivity

At n=20 split each four-group cell into high/other W, on D1 and M30. These eight
rows are diagnostic, not eight optimized gates. Show mean W and w>=0.80 fraction.
Explicitly report M30 low_eff_high_overlap AND high_wick, plus high_wick AND
high_overlap regardless of E (the direct user hypothesis). Neither is promoted
merely for looking better than the main candidate.

Roll sensitivity excludes observations whose n+1-close history touches a
contract switch, using the original roll schedule. Compare against the baseline
restricted to the SAME observations. Keep thresholds fixed; report coverage.
Actual failed-breakout counts are deferred: wick fraction does not prove failure.

## 4. Outcomes, omission comparisons and interpretation

Four groups, baseline and annual rows: trades, active sessions/weeks, gross/net
mean R, net dollars, PF, risk, costs/R, holding hours, worst day/week, closed-trade
and daily-close drawdown. Use a common full session calendar including zero-PnL
dates. Report dollar losses avoided AND profitable dollars missed by omission.
Subset drawdowns do not add to portfolio drawdown. These are realized-balance,
not intratrade mark-to-market statistics. Include both cost stresses.

For D1/M30 n=20 candidates and the two named M30 wick subsets, show baseline,
omitted ledger, and static baseline scaled to retained holding-time fraction.
Fractional scaling of both PnL/cost is diagnostic, not one-MNQ executable sizing.
Show retained trade-count and planned-risk fractions too. Ledger omission is NOT
a full strategy replay: skipped positions can free new order opportunities.

Placement control: 2,000 seeded circular shifts of each boolean skip mask over
chronologically ordered trades within each era. Preserve exact skip count and
run lengths in trade order, not calendar durations. Show retained PnL, daily DD
and holding-exposure distributions, plus random curves rescaled to candidate
retained holding exposure. This is a limited placement control, not independent
randomized evidence. Seed 20261024; no selecting favorable shifts.

Uncertainty: 10,000 paired circular moving-block bootstrap draws of four calendar
weeks, seed 20261024; preserve whole trades. At n=20 show 95% net-R and
group-minus-complement intervals for four groups and named wick subsets; also
97.5% intervals for the two main D1/M30 candidate contrasts. Fewer than 200
trades or 30 active weeks in either era is sparse/inconclusive. Show annual signs;
2026 is partial. Report all fixed sensitivities, not only a winner.

No automatic adoption. Negative-edge follow-up requires negative net dollars
AND net mean R in BOTH eras, adequate counts/weeks, and same signs at n=10/40
and roll sensitivity. Positive-edge risk-reduction claims instead need explicit
profit/drawdown and equal-exposure comparisons; a smaller DD alone is insufficient.
All reused history is exploratory. A promising gate needs separately frozen
order/restart semantics, complete replay, then fresh data.

## Verification and deliverables

Hash protocol before outcomes; verify unchanged at run end. Save hashes,
thresholds, features, trade labels, summaries, annual/wick tables, sensitivities,
uncertainty and controls. Independently verify OHLC, as-of timing, formulas,
cutoffs, partitions, costs/R, endpoint, summary arithmetic and future invariance.
Focused tests: flat bars, alternating/trending prices, gaps and completion times.
Produce RESULTS.md and a static figure; update plan/status/journal. Preserve
prior studies and strategy defaults.
