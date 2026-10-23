# RTL: unfavorable-period research plan

Saved 2026-10-23 from the proposal discussed on 2026-10-22. User instruction:
start with **RTL only**, save the proposal as a plan, and work through it point by point.

## Objective and scope

Find observable conditions in which reducing or skipping RTL long exposure improves
the result after costs while preserving profitable opportunities. Distinguish a
negative entry expectancy from positive expectancy accompanied by larger dollar risk.
Keep the current uncapped M30 RTL entry, 1R bar-close exit, session handling, and
one-contract baseline unchanged during diagnosis. GG is deferred. Short hedging
is a later, separate question. We cannot expect to predict every losing period.

## Why this research

The matched market-buy control earned roughly zero gross R while buy-stop entries
did better. Upward drift alone is insufficient to explain RTL. The older fixed-1R
daily-bear subset was profitable; falling markets are not automatically unfavorable.
Recent-candle direction, session blocks and trade-result streaks did not establish
a reliable skip rule. See [signal/control](../signal-colour/RESULTS.md),
[daily trend](../trend-rr/RESULTS.md), [recent direction](../q04-context/RESULTS.md),
[streaks](../q24-trade-streaks/RESULTS.md), [session blocks](../time-of-day/RESULTS.md).

## Ordered work and progress

- [x] **1. Save the proposal as this plan; restrict the initial study to RTL.**
- [x] **2. Freeze the experiment before viewing its outcomes.**
  [PROTOCOL.md](PROTOCOL.md): three lagged daily trends times two trailing volatility
  states, a separate cost/risk diagnostic, and explicit data boundaries.
- [x] **3. Reconcile the current baseline and label every eligible trade.**
  Check source hashes, MT5 totals, submission timestamps, no future information,
  session boundaries, rollover effects and the incomplete final data session.
- [x] **4. Produce the six-group diagnosis.**
  For each era and year: counts, gross/net R, dollars, initial risk, costs,
  worst days/weeks, drawdown and uncertainty. Separate weak edge from larger risk.
- [x] **5. Decide whether any condition is repeatably unfavorable.**
  Apply the frozen screen. Do not redesign groups around one historical drawdown.
  If none qualifies, record that answer instead of inventing a gate to continue.
- [ ] **6. If a condition qualifies, freeze one gate and its restart rule.**
  Define pending-order/open-position treatment. Evaluate chronologically; report
  losses avoided, gains missed, rebound capture and drawdown duration.
- [ ] **7. Compare with equally reduced exposure.**
  Static risk reduction and matched random/block skipping distinguish predictive
  value from merely trading less. Fractional contracts are a diagnostic, not an
  executable one-MNQ sizing rule.
- [ ] **8. Rerun the complete strategy for a surviving gate.**
  Ledger filtering misses new orders freed by skipped positions. Reconcile the
  full replay/MT5 run, costs and open-equity risk.
- [ ] **9. Freeze and observe on genuinely fresh forward data.**
  Historical splits remain exploratory because this history has been examined.
  Another historical test cannot supply future observations.

## Further hypotheses, kept separate

- Intraday choppiness / failed continuation through previous highs after the initial
  study. Do not stack extra indicators on weak initial evidence.
- Cost burden relative to the planned stop: small gross edges may disappear after
  costs. A gate must use information available before submission.
- A short hedge may lose alone yet help the portfolio. Compare synchronized daily
  RTL equity (including flat days), reduced/filtered RTL, and RTL plus hedge after
  costs. Measure payoff in RTL's worst periods. Opposite direction alone is not
  sufficient. Deferred during this RTL-only diagnostic.

## Safeguards and completion standard

Use completed information, past-only thresholds, a small fixed set of definitions,
and period-clustered uncertainty. Report R and dollars because one contract does
not maintain constant dollar risk. Preserve the one-minute OHLC qualification;
slippage is not measured here. This study changes no live defaults or accounts.

Record completed steps here and in [RESULTS.md](RESULTS.md). Mark conditional steps
not triggered when preceding evidence fails, rather than passed.
Research context: [Statistical Overfitting and Backtest Performance](https://sdm.lbl.gov/oapapers/ssrn-id2507040-bailey.pdf).


## First study completed: 2026-10-23

Steps 1-5 complete; [results](RESULTS.md) independently verified. All six primary
groups have positive net dollars in both eras; none qualifies. Four smaller groups
also have insufficient independent-week coverage. No skip rule is adopted.

- Steps 6-8: **not triggered**, because the frozen screen produced no candidate.
- Step 9: pending a surviving rule and genuinely future observations; not completed
  by this historical study.
- RTL-only scope retained. The cost/risk diagnostic and intraday-choppiness ideas
  remain separate possible follow-ups; no new thresholds were selected here.
