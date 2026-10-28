# RTL: unfavorable-period research plan

Saved 2026-10-23 from the proposal discussed on 2026-10-22. User instruction:
start with **RTL only**, save the proposal as a plan, and work through it point by point.

## Objective and scope

Latest cross-study interpretation: [drawdown synthesis](SYNTHESIS.md), saved
2026-10-25 at the user's request. This qualifies the earlier broad claims that
all filtering is exhausted and retains the modest risk-reduction evidence.

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

## Price-structure follow-up: 2026-10-24

User authorized the four points proposed in conversation, with an additional M30
wick/overlap example. This is a new hypothesis; the first study's null result and
frozen protocol remain unchanged. [Price-structure protocol](../rtl-price-structure/PROTOCOL.md).

- [x] **1. Measure completed daily structure:** 20 sessions, efficiency and overlap;
  10/40 as fixed robustness checks. Separately measure the user's M30 example
  with 20 completed candles and the same fixed neighboring windows.
- [x] **2. Compare four efficiency/overlap groups:** cutoffs calibrated solely on
  pre-2016 price windows, then held fixed for 2016-19 and 2020-September 2026.
- [x] **3. Diagnose persistent wick fraction:** preserve small-body/long-wick
  overlap as an explicit M30 subset, without selecting another optimized gate.
- [x] **4. Assess actual RTL outcomes:** dollars, R, losses avoided, gains missed,
  realized drawdowns, static reduced exposure and limited random-placement controls.

Status: all four points complete and independently verified; 12 focused tests pass.
[Results](../rtl-price-structure/RESULTS.md): M30 low-efficiency/high-overlap and
high-wick/high-overlap subsets make positive dollars in both eras. Daily structure
offers a modest historical profit/drawdown tradeoff but no robust negative-edge
candidate; sensitivity and placement controls do not establish an adoption case.
No filter adopted. No full gated-strategy replay or fresh forward validation is
claimed. An extreme wick-persistence definition would be a separate hypothesis;
the completed study's cutoffs were not retuned around its results.

## Profit location within flagged episodes: 2026-10-24

User authorized finding where the retained profits arise and asked about the
twenty-candle setting and agreement among MA lengths 5-200.
[Frozen attribution protocol](../rtl-price-structure/EPISODE_PROTOCOL.md).

- [x] Form episodes from consecutive flagged price observations, including bars
  without trades; distinguish retrospective episode phase from causal episode age.
- [x] Locate each trade's logged excursion relative to its frozen pre-submission
  range; separate contained paths, upper/lower escapes and exit locations.
- [x] Check whether pending orders fill in the original episode, after its flag
  clears, or in a later episode; compare n=10/20/40 and both historical eras.
- [x] Independently verify and report contribution of winners and losers, counts,
  average returns and episode coverage. No new threshold or trading gate implied.

Completed and independently verified: [episode results](../rtl-price-structure/EPISODE_RESULTS.md).
All 23,569 overlapping attribution rows, 678 summaries and 24 era reconciliations
match; 16 focused tests pass. All 18 M30 flag/window/era combinations have
negative contained-path dollars and positive upper-excursion dollars. Most
winning dollars enter before the original flag clears; some upper excursions
also close profitably before clearance. Retrospective late-episode strength does
not establish a causal waiting rule. Twenty is not the sole source of the failed
blanket omission result. No filter or EA change adopted.

Separate next hypothesis: multi-horizon MA slope agreement. The protocol records
the exact SMA slope identity and the weighting problem in a dense step-5 grid.
Up/down/mixed labels, flat-slope handling and transition costs would need their
own frozen test; no MA outcomes or settings are selected during this attribution.

## MA agreement follow-up: authorized 2026-10-24, resumed 2026-10-25

The user authorized the separate MA test. [Frozen protocol](../rtl-ma-agreement/PROTOCOL.md)
uses completed M30 slopes at 5/10/20/40/80/160/200, a pre-2016 flat-slope band,
five-of-seven primary agreement, and four fixed sensitivity variants. Short/long
conflicts remain separate descriptors, including when the overall state is clear.

- [x] Freeze definitions, calibration, sensitivity variants, omission policies,
  transition attribution and uncertainty before conditional MA results.
- [x] Build and verify completed-price votes, causal states and actual-submission
  labels; preserve all 16,668 eligible RTL trades and baseline economics.
- [x] Compare states and fixed skip policies, dollars/R, costs, drawdowns, annual
  and roll sensitivity, same-holding controls and circular-placement controls.
- [x] Locate profits missed before up-consensus returns and describe causal age
  after reentry, separating future attribution from live information.
- [x] Independently verify all outputs, render results, and decide whether any
  primary policy warrants a separately specified full replay. No automatic adoption.

Completed 2026-10-25: [results](../rtl-ma-agreement/RESULTS.md). All three policies
remove profitable dollars in both eras under all five definitions; no primary
policy passes the frozen replay screen. Clear-up returns improve recently but
do not repeat early. Skip-down has a modest recent risk tradeoff, with contrary
early evidence and unequal dollar-risk exposure. Future consensus often arrives
during profitable trades, but that is outcome-conditioned attribution, not a
predictive restart rule. All 83,340 labelled rows, 159 summaries, 90 policy rows,
60,000 bootstrap group draws and 12,000 placement draws independently verified;
18 tests pass. No MA filter or EA change adopted; full replay not triggered.

## Downtrend crystal ball: 2026-10-24

User proposed a perfect-foresight downtrend test as a ceiling for all downtrend
filters, with deliberate delays. [Frozen protocol](../rtl-downtrend-oracle/PROTOCOL.md).

- [x] Hindsight zigzag downtrends at 2/3/5/10% on roll-adjusted daily closes;
  raw closes as sensitivity.
- [x] Skip from peak to trough, then 1/2/3/5/10/20 sessions late; live zigzag as
  the no-hindsight counterpart; static and all-shift placement controls.
- [x] Independently verify and apply the fixed decision rule.

Completed: [results](../rtl-downtrend-oracle/RESULTS.md). On-time gains of 36-202%
vanish within 2-3 sessions for small drops and by 3 sessions in 2016-19 at every
size; the live zigzag loses profit everywhere. Downtrend filters are not worth
pursuing further for RTL on NQ. No filter or EA change adopted.

## Crystal ball with early signals: 2026-10-25

User asked whether a pullback-anticipation statistic is worth building.
[Frozen addendum](../rtl-downtrend-oracle/EARLY_PROTOCOL.md).

- [x] Stop and resume 1/2/3/5 sessions early; early stop with on-time resume.
- [x] Same controls; independently verify and apply the fixed decision rule.

Completed: [early results](../rtl-downtrend-oracle/EARLY_RESULTS.md). Being early
costs far less than being late, so the pullback statistic passes the fixed rule.
Next, if pursued: a separately frozen protocol for a stop signal and an early
resume signal, with hit rates against the base rate and false-alarm cost.

## Pullback and bounce warning statistics: 2026-10-25

User's step 2. [Frozen protocol](../rtl-pullback-stats/PROTOCOL.md); price data only.

- [x] Durations of falls and rallies; hindsight "tiredness" by leg age.
- [x] Pullback ("up a lot") and bounce ("down a lot") warnings against zigzag
  turns, with volatility-matched base rates and all-shift controls.
- [x] Independently verify and apply the fixed decision rule.

Completed: [results](../rtl-pullback-stats/RESULTS.md). Bounce warnings pass
everywhere; pullback warnings pass only for 5% drops (5-session rise). Next, if
pursued: a frozen RTL test of signal-based skipping for 5% drops, and possibly a
separately frozen live-zigzag stop with a bounce-warning resume.

## Warning-based skip rules on RTL: 2026-10-25

User-requested RTL test of the warning statistics. [Frozen protocol](../rtl-warning-rules/PROTOCOL.md).

- [x] Rule A: pullback-warning stop, bounce-warning or timeout resume (5% drops).
- [x] Rule B: live-zigzag stop, bounce-warning resume, at 2/3/5%.
- [x] Independently verify and apply the fixed decision rule.

Completed: [results](../rtl-warning-rules/RESULTS.md). No rule is promising;
nothing beats trading every session. Daily downtrend filtering for RTL on NQ is
considered exhausted; no MT5 replay stage triggered.

## Weekly signal gate: 2026-10-25

User proposal after a weekly MT5 run. [Frozen protocol](../rtl-weekly-gate/PROTOCOL.md).

- [x] Weekly bars from M30, roll-adjusted; sell/buy breaks of the prior week.
- [x] Gate new M30 trades at the breaking bar's close; three fixed sensitivities.
- [x] Independently verify and apply the fixed decision rule.

Completed: [results](../rtl-weekly-gate/RESULTS.md). Not promising: every version
cuts profit by 52-85%.

## VWAP and price action: 2026-10-25

User authorized after saving the [drawdown synthesis](SYNTHESIS.md).
[Frozen protocol](../rtl-vwap/PROTOCOL.md), RTL only, existing baseline.

- [x] Freeze four questions: location, distance, reclaim/loss and repeated crossings.
- [x] Build minute-volume VWAP and causal labels; preserve unknown session opens.
- [x] Compare trade outcomes, omission policies, equal exposure and confounds.
- [x] Independently verify, report results and determine whether replay is warranted.

Completed 2026-10-26: [results](../rtl-vwap/RESULTS.md), 13 tests and full
independent reconstruction pass. Far-below full-session VWAP signals provide a
risk-reduction lead across both eras, despite failing the negative-dollar screen
early. A [concrete replay proposal](../rtl-vwap/REPLAY_PROPOSAL.md) is saved;
not executed or adopted. Recent drawdown duration worsens and cash-anchor results
are weaker. Other tested VWAP relationships do not justify a filter.

## Full VWAP strategy replay: completed 2026-10-27

User authorized the full replay and commit. [Frozen protocol](../rtl-vwap/REPLAY_PROTOCOL.md).

- [x] Freeze the single far-below rule and original pending-order maintenance.
- [x] Reproduce all 25,833 baseline trades exactly before enabling the gate.
- [x] Replay skipped orders and subsequent opportunities through the full engine.
- [x] Reconcile candidate/order histories, attribution, equal-exposure controls,
  annual/cost results and sampled open-equity risk independently.
- [x] Save results, chart, executable workflow and verification; no live adoption.

[Results](../rtl-vwap/REPLAY_RESULTS.md): net $4,417 -> $4,721 early and
$38,400 -> $45,725 recently; daily-close DD $2,143 -> $986 and $5,781 -> $3,158.
Both beat same-holding and same-planned-risk baseline scaling. New trades add
$887/$729; recent daily DD duration grows 283 -> 328 days, and extra $1/trade
makes early filtered net -$303. All raw outputs/economics independently verified;
22 VWAP tests pass. Keep the unchanged rule for prospective validation rather
than more tuning on the same history. No production RTL change.

## VWAP rule on ES, YM and RTY: frozen 2026-10-27

User asked for this after the evaluation's placebo checks (see the journal).
[Frozen protocol](../rtl-vwap/CROSS_PROTOCOL.md), SHA-256
`39a0884b7d746de14902e8a87833c4903da0965e331b47e7ead3b277cf912886`. No ES/YM/RTY
VWAP label or outcome computed before freezing.

- [x] Freeze the unchanged rule, samples, placebos, seeds and the verdict.
- [x] Parse and reconcile the existing ES/YM/RTY/NQ RTL runs; NQ reproduces the VWAP panel.
- [x] Build features with the unchanged NQ code; label trades; signal-bar check.
- [x] Risk-matched contrast, placebos, descriptive outputs; apply the fixed verdict.
- [x] Independently verify; results, chart, plan, journal and status.

Completed 2026-10-27: [results](../rtl-vwap/CROSS_RESULTS.md). **Does not transfer: 0 of 3
confirm.** Risk-matched contrasts -0.013 / -0.026 / -0.028 R on ES / YM / RTY (NQ -0.091), every
interval across zero; the rule's DD beats only 87% / 15% / 89% of same-month placebos (95%
needed). NQ 2010-15 fails too. Per protocol: no rescue on these data; the rule stays a forward
candidate only. No production RTL change.

## VWAP rule on Nasdaq-100 stocks: frozen 2026-10-28

User's proposal after the cross-instrument result: new data, not a rescue on the futures data,
and read together with those failures. [Frozen protocol](../rtl-vwap/STOCK_PROTOCOL.md), SHA-256
`a12a4172b7d326e4e86d2537ddd0101c93849ccbe22daee11120211c5bfb4e38`. The last historical instrument
test of this rule. Only NVDA's file structure was inspected before freezing.

- [x] Freeze ten stocks, data, session with pre-market, gap-aware fills, tests and verdict.
- [x] Download the other nine stocks (XNAS.ITCH ohlcv-1m, 2018-05-01 to 2026-10-27; FB then META).
  No FB history was available, so Meta enters from 2022-06-09 (disclosed, before any outcome).
- [x] Source checks: hashes, splits, early closes; simulator reproduces the 25,833 NQ trades.
- [x] Simulate RTL per stock, label, run contrast, placebos and the fixed verdict.
- [x] Independently verify; results, chart, plan, journal and status.

Completed 2026-10-28: [results](../rtl-vwap/STOCK_RESULTS.md). **Does not support: tests 1 and 2
pass, test 3 fails.** Matched on risk, far-below trades earn 0.058 R less (interval -0.089 to
-0.028), in both eras and 8 of 10 stocks, and also away from NQ's sell-offs. The portfolio
drawdown falls $37,345 to $19,270, beating 100% / 99% of placebos, but in 2018-19 the rule was no
better than random skipping. Per protocol, the VWAP line for RTL closes on history; a forward
paper test on NQ remains possible. No production RTL change.
