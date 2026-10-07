# Research journal

What we did, day by day, and what each step answered. Newest day last.
For the current state of the strategy, see [STATUS.md](STATUS.md).

## Where we are now (updated 2026-10-01)

- **Strategy:** buy stop over the last red M30 candle, stop at its low, bar-close exit at ≥ 1R,
  `MaxRedRun = 3`, flatten at 23:30 with the fallback fix. 2020–26: net $37.4k, PF 1.105.
- **Entry and exit tweaks are largely exhausted;** most ideas failed. Only the red-run cap survived.
- **Data rebuilt** (`MNQcontDTBNT20102026`) and **early-close calendar** added: the strategy is
  now strictly intraday. On clean data 2.5R beats 1R in both periods.
- **RR = 1.0, decided** after the clean-data check (pre-set rule not met). Use symbol
  `MNQcontDTBNT20102026_2`.
- **`MaxRedRun` confirmed on clean data;** cap 3 kept as the balanced choice (cap 1 = safest).
- **Limit-order entry rejected** and **time of day checked** (no change), 2026-10-02.
- **Q1–Q5 answered (no filter).** **Next:** execution realism (live/demo fills and slippage)
  and the live sizing decision; new ideas go into the Inbox.

---

## 2026-09-28: Can preceding bars improve entries?

- Built `RR_r_MFE_buy-stop-entry_features.cs` (logs the last 30 bars per trade) and
  `analyze_features.py` (10 bar-only features, judged one at a time).

## 2026-09-29: Entry filters

- **Feature scan (2020–26):** no feature isolates a losing group. One theme stood out:
  "falling-knife" signals near the 20-bar low trade at about breakeven.
- **Location + red-run** looked good after the fact (DD halved). → Built the runband EA from
  the buy-stop base (`MaxRedRun`, `MinLocation`).
- **MT5 confirmation:** location **not confirmed**; all profit differences are within noise.
- **2010–19 baseline:** 2010–14 has **no edge** even before costs. 2015 onwards looks like today.
- **MaxRedRun train/test:** chosen on 2015–19 by a pre-set rule (→ 3), then frozen on
  2020–26: PF up in 6/7 years, DD −17%, profit flat. **Adopted** (small effect).

## 2026-09-30: Project tidy-up, more entry questions, exits

- Project reorganized into `mt5/`, `python/`, `docs/`, `data/`.
- **Q1 interrupted decline / Q2 recovery after a new low:** periods disagree. **No filter.**
- **First-touch +1R exit (estimate):** worse than the bar-close exit. The overshoot beyond
  1R (about +0.6R on ~70% of winners) is valuable.
- **Data review:** pre-2019 data is NQ-based; the clock is Chicago + 8 h; roll contracts were
  picked with same-day volume; the NQ/MNQ join and any price adjustment are unverified.
- **Exit thresholds 0.75–2R + fixed TP (MT5):** fixed TP is worse. **Found a bug:** positions
  were held for days when the 23:30 bar was missing.
- **RR grid 0.5–5:** a noisy curve. Gains above 1R mostly came from those multi-day holds.

## 2026-10-01: Flatten fix and "capture the wick"

- **Flatten fallback** (new `FlattenFallback` input): the cause was early-close days and
  DST-mismatch weeks. Multi-day holds are gone; the baseline barely changes.
  **RR stays 1.0:** in dollars the best RR differs by period; average R prefers higher RR.
- Added the one-page [STATUS.md](STATUS.md) and summary boxes on the long docs.
- **Resting limit above the target (estimate):** winners give back about 0.3–0.4R, but every
  limit level is worse because it caps the big runners. **Rejected.**
- **Trailing stop after +1R at 0.25 / 0.5 / 1.0R (MT5):** worse in 2015–19, mixed in
  2020–26. **Rejected.** The bar-close exit stays.

## 2026-10-01 (later): Sizing, overnight trades, data rebuild

- **Sizing (real cost $1.05/contract):** fixed-$200-risk sizing capped at 5 contracts beats
  1 contract in 2020–26 but not in 2015–19 (small candles multiply commission). Sizing
  **doesn't change** the RR answer. Keep 1 contract for research.
- **Why ~70–95 overnight trades remain:** a bar-time dump showed the data clock shifts one hour
  in US/EU DST-mismatch weeks (55–60% of them); the rest are holiday early closes.
  Data before 2016 also had a different session shape.
- **Rebuilt the data** from the Databento source ([DATA_BUILD.md](reference/DATA_BUILD.md)): consistent
  clock, rolls without hindsight. Confirmed the old file was shifted 1 h in mismatch weeks.
  Dropped the pre-2016 post-16:00-Chicago tail bars. Imported as `MNQcontDTBNT20102026`.
- **Early-close calendar** ([results](baseline/early-close-calendar/RESULTS.md)): on the new data all
  remaining overnight holds started on early-close days. A data-derived calendar (262 sessions,
  matching the published schedule) makes every run flat at session end. Profit is unchanged.
  On clean data **2.5R beats 1R in both periods** (net $, PF, avg R).
- **RR 1.0 / 2.0 / 2.5 / 3.0 on `MNQcontDTBNT20102026_2`** ([results](baseline/rr-clean-data/RESULTS.md)):
  higher RR clearly better in 2016–19 and in R terms, flat in 2020–26 dollars. The rule
  required all of 2.0–3.0 to beat 1.0 in both periods; it failed by $78 (2.0R, 2020–26).
  **Decided: RR stays 1.0.**
- **MaxRedRun train/test on clean data** ([results](baseline/maxredrun/RESULTS.md)): 2016–19 training
  picked cap 1 (cap 3 second). Frozen on 2020–26, cap 1 vs off: PF 1.098 → 1.134, DD −30%,
  but −23% profit. Cap 3 = balanced (DD −16%, profit −2%). The cap is confirmed; its value is
  a risk/profit choice.

---

## 2026-10-02: One averaging entry near the protective stop

- [Averaging study](baseline/averaging-entry/RESULTS.md): one equal-sized add at 5/10/20% R
  above the original stop, original bar-close target kept. All worse in the OHLC
  model; 10% also worse with generated ticks in both periods. **Keep it off.**
- The added leg loses in every year. Twelve valid MT5 runs reconcile; a stop-before-
  limit execution case required basket accounting across two position identifiers.
- **Execution review is now first priority:** finer generated ticks reduce the
  matched baseline net from $6,485 to $612 / $37,981 to $19,435 at $1.05 per contract.
  No strategy default changed. Neither model uses historical trade ticks.
- Preserved invalid diagnostics, repaired 40 missing control-export rows strictly
  from its complete MT5 report, fixed runner log-rotation handling, and restored
  temporary MT5 storage redirections after the final run.

## 2026-10-02 (later): Standalone buy-limit entries, OHLC only

- User prefers one-minute OHLC for raw screening; no further generated-tick
  testing planned. Found the archived limit-only EA and reproduced its
  high-trigger behavior while retaining current session handling.
- [Standalone screen](baseline/limit-only/RESULTS.md): 80/90/95% offsets all profitable
  in 2020–26, all lose in every year of 2016–19. Primary 90%: −$2,951 / +$7,021
  net, DD $3,035 / $1,118. No adoption; keep the separate research variant.
- Eight MT5 runs reconcile to full reports; both controls match the historical
  OHLC baseline. Limit runs contain no buy-stop orders. Immediate placement is
  implemented as an option but was not backtested.
- **Follow-up, 80% / RR 2** (user's 2020–26 run: $8.8k net): fills are realistic and stops
  reasonable, but it's concentrated in ~20 trades and positively correlated with the baseline.
  On 2016–19 the same settings lose −$3.1k (4 of 4 years). **Limit entry rejected.**
- **Time of day** ([results](baseline/time-of-day/RESULTS.md)): five session blocks by order-placement
  time. Every block is profitable in both periods and none is consistently weak, so **no
  window change**. The edge is spread across the session.
- **Q3, overlap vs staircase** ([results](baseline/q03-overlap/RESULTS.md)): did the bars before the
  signal keep crossing the same prices, or move steadily? No overlap/direction group loses
  in both periods at N = 5/10/20, so **no filter**.
- **Q4, pullback vs broader move** ([results](baseline/q04-context/RESULTS.md)): older × recent direction
  groups at (5, 20), (3, 10) and (10, 40) are all profitable in both periods. "Pullback in an
  advance" is not better. **No filter.** With Q1–Q4 done, pre-entry bar shape looks exhausted.
- **Q5, signal-candle shape** ([results](baseline/q05-candle-shape/RESULTS.md)), the user's new question:
  doji / hammer / shooting star / full body / other. No shape loses in both periods. Doji loses
  in 2016–19 but is strong in 2020–26; full body is the reverse. **No filter.**

## 2026-10-02: Trend-conditioned targets on baseline RTL

- User clarified: import only the trend idea, retaining our RTL entry, stop,
  filters and bar-close-qualified market exit. No GG, sell-limit exit or forward test.
- [Study](baseline/trend-rr/RESULTS.md): six bull/neutral/bear mappings with previous-day
  50/200 MAs and 40/200, 60/200 checks. Primary mild/strong mappings reduce
  net/DD in both usual periods; annual historical selection also fails the
  required improvement. Keep fixed 1R.
- All 16 OHLC runs passed the audit, including 1,257,870 target checks. Annual
  selection net/DD: 8.89 versus fixed 9.00 (−1.3%); only 3/11 years improve.
  Neighboring MA results change sign. Higher assumed costs favor lower turnover,
  but slippage remains unmeasured. Baseline source and defaults are unchanged.

## 2026-10-03: Price-level context (Q6/Q7)

- [First screen](setups/horizontal/support-bounce-long/q06-q07-price-levels/RESULTS.md): previous-session support proximity and
  overhead room, with current-session/week comparisons. No filter qualifies;
  nearby resistance groups profit in both periods, while near-support samples
  are sparse and PF rankings disagree. No full filtered-strategy rerun triggered.
- Reused 14,968 matching baseline trades; verified 3,053,472 candle values,
  1,191 independent level windows and 5 timing/roll unit tests. No EA changes.

## 2026-10-03: Support breach and reclaim (Q8)

- [Study](setups/horizontal/support-reclaim-long/q08-breach-reclaim/RESULTS.md): current-session reclaims increase the
  90-minute +0.5R response rate by 6.1 / 3.1 pp, including unfilled signals.
  Mean forward return and trade PF do not improve in both periods; no filter.
- Audited 35,632 attempts, 14,968 baseline fills and 803 independent forward
  windows. Deeper breaches preserve the probability association; resistance
  approach/breach paths remain a separate proposed study.
- [Post-hoc dispersion check](setups/horizontal/support-reclaim-long/q08-breach-reclaim/RESULTS.md#post-hoc-check-direction-or-dispersion):
  reclaims also hit -0.5R more often (+3.9 pp recently), so the 2020-26 excess is
  wider outcomes, not upward bias; smaller signal ranges inflate R. Next study:
  report both tails and a lagged-ATR normalization.

## 2026-10-03: Recovery speed and symmetric outcomes (Q9)

- [Study](setups/horizontal/support-reclaim-long/q09-reclaim-speed/RESULTS.md): fast <=2 versus slow >=6 minutes gives no
  reliable post-M30 advantage in 130/218 matched current-session pairs. No
  candidate qualifies; immediate reclaim entries remain a different experiment.
- Both half-R barriers are reached more often after reclaim (25.7% vs 19.3%),
  but the excess reverses in lagged-volatility units. Smaller signal ranges are
  a substantial normalization issue; no general volatility or liquidity claim.
- Rebuilt minute paths and checked every available Q8 forward window. Python
  suffices for this diagnostic; no EA changes or additional MT5 runs.

## 2026-10-03: Support candles versus the entire red-signal population (Q10)

- User moved the focus from speed to actual M30 strategy outcomes and specified
  fixed -1R SL/+1R TP for this experiment. A new isolated MT5 reference run gives
  16,395 fills from 38,853 attempts; all 52,070 potential signals are accounted for.
- [Results](setups/horizontal/support-bounce-long/q10-support-interaction/RESULTS.md): current-session interaction/rest PF
  1.226/1.000 earlier, 1.079/1.084 recently. Weekly interactions improve both
  periods but only 79/146 trades. No candidate qualifies; production unchanged.
- Audited 51,104 report deals and 58,965 order brackets over full history;
  subset/complement attribution and costs reconcile. Preserve the original-exit
  interim screen separately; its outcomes are not mixed into this experiment.

## 2026-10-03: Archive speed direction and organize level research

- At the user's request, [archive Q9 and the intrabar/early-entry proposals](setups/horizontal/support-reclaim-long/q09-reclaim-speed/ARCHIVE.md)
  in place. Preserve Q8/Q9 evidence and frozen protocols; this is a change in
  research direction, not a claim that all speed effects are disproven.
- [Active definition](setups/horizontal/README.md): any qualifying red M30 candle with
  low <= known support <= high, regardless of open/close side. The completed
  fresh-interaction Q10 screen is narrower; broad follow-up remains pending.
- Move all six level-output directories under `Reports/levels/` and result
  documents under `docs/levels/`; preserve old metadata/dependency snapshots
  and a relocation inventory. Update code paths and links; no numerical
  results, production rules or source data changed during organization.
- Validation after relocation: 21 focused tests, Q8/Q9/fixed-1R saved-output
  verifiers, 77-file inventory reconciliation and 130 local links all pass.

## 2026-10-04: Original exit restored; Q11 one-week swing-low support specified

- Q10's [original-exit screen](setups/horizontal/support-bounce-long/q10-support-interaction/RESULTS.md) is now the
  primary result; fixed TP is secondary. Previous-week interactions beat the
  rest in both periods (PF 1.707/1.451) but with only 72/137 fills.
- Froze the [Q11 protocol](setups/horizontal/support-bounce-long/q11-level-visit/PROTOCOL.md): confirmed M30 swing lows
  (N = 5) from a rolling one-week window, merged within 0.5 x ATR; support = revisit
  from above after a 1 x ATR departure, undercuts allowed until a close more than
  0.5 x ATR below. Two weeks and N = 3 reported alongside. Not run.
- Built the Q11 level code, 12 unit tests and [example charts](setups/horizontal/README.md)
  (`python/plot_level_visit_example.py`). The charts showed candles slicing far
  through levels counted as support, so the protocol was amended before any
  outcome: the signal low may undercut by at most 0.5 x ATR. Level contacts
  from below go to a separate inbox question.

## 2026-10-04: Q11 run, one-week swing-low support

- [Results](setups/horizontal/support-bounce-long/q11-level-visit/RESULTS.md): candidates beat every other signal
  in both periods (PF 1.201/1.087, 1.140/1.099) but by little; all intervals
  include zero and N = 3 disagrees, so no full rerun and no filter. Recently,
  signals with no level nearby do better than candidates.
- 52,070 signals classified under three settings; 1,323 sampled signals
  re-derived independently with no mismatch; partitions reconcile.

## 2026-10-04: Q12 broad support-origin contact, no broken-level retirement

- User requested the broad question and keeping levels eligible despite earlier
  breaks. [Protocol](setups/horizontal/support-bounce-long/q12-broad-support/PROTOCOL.md): contact only; no departure,
  depth or open/close-side restriction; original exit and fixed Q11 map settings.
- [Results](setups/horizontal/support-bounce-long/q12-broad-support/RESULTS.md): rolling swing-low contact/rest PF
  1.137/1.061 earlier and 1.084/1.143 recently, 5/11 years better. Both sensitivities
  reverse too. Broad session contact also reverses; weekly contact remains an
  uncertain lead with 101/175 fills. No filter or new MT5 run.
- New runner fails on missing/changed inputs, checks 312,420 signal/definition
  rows, reconciles 12 partitions and preserves all Q10/Q11 files. Eight tests pass.

## 2026-10-04: Q13 previous-week-low concentration audit

- Committed broad-support Q12 as `7d99d5e`. [Q13](setups/horizontal/support-bounce-long/q13-weekly-low/RESULTS.md)
  counts 126 filled weekly events behind 276 trades. Earlier advantages survive
  single-year/week deletions; recent profit is concentrated in 2025-2026 and
  its average-R advantage flips after removing the largest trade.
- Symmetric trimming/equal-event weighting remain positive, but weekly cluster
  intervals include zero. No new filter, subgroup search or MT5 run; seven tests
  and upstream hashes pass. Code, protocol, ledgers and results saved separately.

## 2026-10-04: PWL yearly view against other RTL

- Committed Q13 as `e7f454c`. [Yearly view](setups/horizontal/support-bounce-long/q13-weekly-low/YEAR_VIEW.md) adds
  other-RTL means beside PWL: recent relative returns alternate, with 2023
  already stronger than 2025/2026 and 69/175 contacts in negative 2022/2024.
- Dollars and R have different risk weights; 2025's strong trade result is
  carried by 4/12 positive weekly events. All 11 comparisons and 126 event
  sums reproduce from saved trades; causal regime explanation remains open.

## 2026-10-04: Q14 rising trendline support, draft protocol

- New separate study, [docs/trendlines/](setups/trendlines/README.md); same questions,
  population, exit and gate as Q11/Q12. The old `Trendline_rejection.cs` EA is
  the idea source only (per-bar touch counting, today's ATR for old bars).
- [Draft protocol](setups/trendlines/uptrend-bounce-long/q14-trendline-support/PROTOCOL.md): lines through consecutive
  higher N=5 swing lows in one week, >=10 bars apart, rising >=0.02 x A per bar;
  candidate = revisit of an unbroken, departed line from above (low >= V - D).
- Example charts led to the consecutive-lows and slope-floor rules (all pairs
  gave a fan of ~3 lines per contact and near-flat lines). Counts only: about
  9.5% of signals are candidates in both periods. Code + 12 tests; no outcomes.

## 2026-10-04: Q14 run, rising trendline support

- User approved the draft; froze it (`5cc52ef`) before outcomes. [Results](setups/trendlines/uptrend-bounce-long/q14-trendline-support/RESULTS.md):
  candidates do worse than every other signal in both periods (PF 1.029/0.950
  vs 1.114/1.124, 565/821 fills); broad unbroken-line contact also worse. No filter.
- Two-week and N=3 agree recently. Only "anchors >46 bars apart" is better in
  both periods (one of 23 label cells, post hoc). It is not a lead under the frozen rule.
- Consistency check caught a mixed broken/not-departed grouping bug before any
  outcome; fixed to the frozen text, test added. 1,323 signals re-derived
  independently with 0 mismatches; 12 partitions reconcile.

## 2026-10-04: Q15 falling trendline resistance, draft protocol

- Committed Q14 as `839d79b`. [Q15 draft](setups/trendlines/downtrend-breakout-long/q15-falling-resistance/PROTOCOL.md): Q14's
  frozen definitions mirrored to consecutive lower swing highs; candidate = red
  signal pressing into an intact falling line from below, so a fill breaks it.
- Code reuses the Q14 classifier via price negation; 7 tests build falling
  scenarios directly. Counts only: ~9% of signals are candidates in both periods.

## 2026-10-04: Q15 run, falling trendline resistance passes the gate

- Froze the draft as approved (`e916e40`). [Results](setups/trendlines/downtrend-breakout-long/q15-falling-resistance/RESULTS.md):
  candidates PF 1.325/1.332 vs 1.088/1.090, avg R +0.093/+0.110 vs -0.012/+0.056,
  412/693 fills, 8/11 years; two weeks, N=3 and broad contact all pass too.
- Caveats: avg-R intervals include zero; 2023-25 show no advantage; partial
  2026 is half of recent net. The gap sits in entries *below* the line, not breaks.
- 1,323 signals re-derived on raw highs (no mirror): 0 mismatches; no look-ahead.
  Next: a separate protocol for a full MT5 filter run, with the user.

## 2026-10-04: Q16 concentration audit of Q15

- Committed Q15 as `d47c00a`. User chose a stand-alone, candidate-only EA next
  (whole frozen group primary, entry-below-line a label), after a Q13-style audit.
- [Q16](setups/trendlines/downtrend-breakout-long/q16-resistance-concentration/RESULTS.md): 1,105 trades on 887 lines (max 5
  per line), 439 weeks; every year/week deletion keeps both differences positive;
  trimming leaves +0.10/+0.05R. Week-bootstrap mean R just includes zero. Top 10-20
  winners removed one-sidedly erase it. Unlike Q13, not concentrated.

## 2026-10-04: Q17 stand-alone EA built, draft protocol

- Committed Q16 as `14c0007`. [Q17 draft](setups/trendlines/downtrend-breakout-long/q17-standalone/PROTOCOL.md): baseline research EA +
  `mt5/experts/resistance_gate.mqh`; non-candidates rejected like a MaxRedRun rejection.
- Compiled 0/0. Classify-only MT5 run (no orders) reproduces Q15 on all 52,070 signals:
  0 group mismatches, 4,580/4,580 candidates, identical anchors. Trading run awaits freeze.

## 2026-10-04: Q17 stand-alone run, falling resistance does not survive

- Froze Q17 (`a30fe42`) and ran the candidate-only EA (27 s). [Results](setups/trendlines/downtrend-breakout-long/q17-standalone/RESULTS.md):
  669/1,001 trades, PF 1.242/1.238, mean R +0.039/+0.050 vs baseline -0.004/+0.060; 4/11 years.
  Fails the frozen rule. No filter, sizing or stand-alone strategy.
- Shared trades identical to the baseline (405/678), so execution is not the cause: the
  264/323 freed trades (taken while the baseline was busy) are break-even and dilute Q15's edge.

## 2026-10-04: Q18 horizontal breakout, draft protocol

- Committed Q17 as `64a6193`. User asked about horizontal breakouts; chose (a) fill = break as
  primary. [Draft](setups/horizontal/resistance-breakout-long/q18-breakout/PROTOCOL.md): Q11 machinery mirrored to swing highs; stage 1 Q11
  gate, stage 2 stand-alone EA with the Q17 rule; stopping rule for level/line research.
- Counts only: ~16.5% of signals are breakout tests in both periods; 42% have entry at/above L.
  Charts led to renaming the broken group (it also holds falls back through old levels).

## 2026-10-04: Q18 horizontal breakout passes both stages

- Froze Q18 (`4de937a`). Stage 1: candidates PF 1.198/1.192 vs 1.093/1.095, mean R +0.049/+0.121
  vs -0.012/+0.051, 8/11 years; sensitivities agree; raw-high re-derivation 0 mismatches.
- Stage 2: MQL5 level gate matched stage 1 on all 52,070 signals, then traded alone:
  1,083/1,685 trades, PF 1.164/1.204, mean R +0.062/+0.110 vs baseline -0.004/+0.060, 8/11
  years; freed trades hold up (unlike Q17). [Results](setups/horizontal/resistance-breakout-long/q18-breakout/RESULTS.md).
- Caveats: 2016-19 weak, 2010-15 negative, OHLC only. Nothing adopted; next is the user's call.

## 2026-10-05: breakout EA for manual runs, RiskReward fix, Q19 audit

- Saved the exact Q18 stage-2 EA as `mt5/experts/RR_r_MFE_buy-stop-entry_breakout.cs` (one file, tested
  defaults); a defaults-only run reproduces stage 2 trade by trade. User found RiskReward had no effect:
  the research parent took its target from BullRR/BearRR. Fixed in the .cs (RR 1 unchanged, RR 2 differs).
- [Q19](setups/horizontal/resistance-breakout-long/q19-breakout-concentration/RESULTS.md): breakout trades spread over ~2,250 levels / 524 weeks;
  every year/week deletion keeps the advantage; trimming shrinks it (half earlier). Paired difference vs
  RTL +0.066/+0.050R, week intervals just include zero per period, exclude pooled. Not concentrated.

## 2026-10-05: Q20 trendline buy-limit, draft protocol

- User proposed resting a buy limit on the rising (Q14) line, any candle colour; stop chosen 0.5 x ATR below.
  [Draft](setups/trendlines/uptrend-bounce-long/q20-trendline-limit/PROTOCOL.md): lines re-evaluated each M30 open, order re-priced per bar,
  one trade per departure episode, baseline 1R bar-close exit. Decision control C1: same bars, random-distance limit.
- Sensitivities: trade-through fill (1 tick below), stops 0.25 / 1.0 x A. Frozen as drafted, nothing run.

## 2026-10-05: Q20 frozen, classify-only run verified

- Froze Q20 as drafted (`4c86411`). Built `trendline_limit.py` / `trendline_limit.mqh`; the classify-only EA run
  (no orders) matches Python on all 184,888 eligible bars: 0 mismatches (after one pre-outcome fix for the first
  day of history). [Verification](setups/trendlines/uptrend-bounce-long/q20-trendline-limit/PROTOCOL.md#pre-trade-verification-done-2026-10-05-no-outcomes).
- Counts only: orders on ~56% of bars, ~9% of those can fill; tester spread means a 1-tick bid trade-through
  is already needed; cost ~0.13R in 2016-19. SVG charts of the per-bar order steps added.

## 2026-10-05: Q20 trading runs, the trendline buy limit fails

- Built the trading modes (primary, C1, C2; trade-through and stop 0.25/1.0 x A) and the C1 delta table; 10 MT5 runs
  (classify repeat byte-identical). Every run replayed bar by bar in Python: 0 mismatches; fills and ledgers audited.
- [Results](setups/trendlines/uptrend-bounce-long/q20-trendline-limit/RESULTS.md): PF 0.773/0.969, mean R -0.238/-0.023; fails PF > 1 and mean R > 0
  in both periods before the control matters; 2/9 years beat C1. 45% of trades stop out in the fill bar.
- Caveat on the frozen control: one global episode, so C1 placed no order in 2022 (price never closed 1 x A above the
  last fill). Fill-bar colour/depth labels are outcomes, not filters.

## 2026-10-06: Q21 trendline breakdown short, protocol frozen

- User proposed shorting the break of the Q14 rising lines: a red M30 candle closing below a live line, sell stop at
  its low, stop at its high, next bar only, 1R bar-close exit. First short-side study (mirror of GG, not of RTL).
- [Protocol](setups/trendlines/uptrend-breakdown/q21-breakdown-short/PROTOCOL.md) frozen before any count: one signal per line (first close below
  after departure spends it); decision control C1 = any red bar in the same armed-line regime; S1 = close > D below.

## 2026-10-06: Q21 classify-only runs verified

- Built `trendline_breakdown.py` / `.mqh`; classify-only EA (primary and S1) matches Python on all 184,888 eligible
  bars, 0 mismatches. [Verification](setups/trendlines/uptrend-breakdown/q21-breakdown-short/PROTOCOL.md#pre-trade-verification-done-2026-10-06-no-outcomes).
- Pre-outcome fix: "live" was judged from scratch each bar, so a growing A revived 52 / 202 already-broken lines.
  Breaks are now recorded on every bar and stay spent (one signal per line, as the protocol says).
- Counts only: ~950 / ~1,570 orders (2016-19 / 2020-26); R ~1.7 x A, cost ~0.04R / 0.01R. PC hung once on a
  verifier memory bug (per-bar copies of the spent set), fixed.

## 2026-10-06: Q21 trading runs, the breakdown short fails

- Built the short side into the research EA (direction flag, mirrored bar-close exit, direction-aware ledger) plus
  primary / S1 / C1 / C2 modes; classify regression byte-identical; 4 runs replayed against the verified log, 0 mismatches.
- [Results](setups/trendlines/uptrend-breakdown/q21-breakdown-short/RESULTS.md): PF 0.893/0.916, mean R -0.081/-0.025; gross negative before costs;
  better than C1 (any red bar in the regime) in mean R but 6/11 years, interval includes zero. No label works in both periods.

## 2026-10-06: Q21 exploratory 2R target

- User asked for a 2R target; plan fixed and committed before running (exploratory, same rule, C1 at 2R).
  [Result](setups/trendlines/uptrend-breakdown/q21-breakdown-short/RESULTS.md#2r-result-2026-10-06-also-fails-no-better-than-1r): PF 0.916/0.891,
  mean R -0.050/-0.041, gross negative; only 18-19% reach 2R. Descriptive regime split: red-candle shorts lose in
  bear regimes too.

## 2026-10-06: Q22 protocol frozen (RTL longs after a rising-line break)

- After Q21, user chose to use the break on the long side. Prior evidence (Q14 broken-line contact, Q21 no follow-through)
  points to "better" rather than "worse", so the user chose a two-sided gate: skip filter if worse, failed-breakdown long if better.
- [Protocol](setups/trendlines/uptrend-breakdown/q22-breakdown-rtl/PROTOCOL.md): group A = red signal candle breaks a live line, B = break in the 10 bars
  before; Q10 census attribution, no new MT5 run; sensitivity S1. Future separate study noted: Q18-mirror swing-low breakdown short.

## 2026-10-06: Q22 results, no gate passes

- [Results](setups/trendlines/uptrend-breakdown/q22-breakdown-rtl/RESULTS.md): against the prior evidence, RTL buys on the red breakdown candle are worse
  than every other signal in both periods (PF 1.010/0.831), 7/11 years, 2020-26 interval excludes zero; the skip-filter gate
  fails only on S1. 10-bar post-break group: no difference. Break events = verified Q21 log on 170,256 bars, 0 mismatches.

## 2026-10-06: Q23 protocol frozen (Q18 mirror short)

- User asked for the short mirror of Q18 with the same level rules. [Protocol](setups/horizontal/support-breakdown-short/q23-support-breakdown/PROTOCOL.md):
  green signal, sell stop at its low at an intact swing-low level approached from above; frozen Q11 classifier as is.
- No short census exists, so stage 0 is a new MT5 run of the short mirror baseline (green run 1-3, mirrored exit).

## 2026-10-07: Q23 results, the Q18 mirror short fails stage 1

- Stage 0 MT5 run of the short mirror baseline (green candle, sell stop at its low): 24,111 trades, all checks pass;
  it loses in every period (PF 0.750/0.916/0.974). Stage 1 with the frozen Q11 classifier as is (1,440 independent
  re-derivations, 0 mismatches): candidate PF 0.992/1.038, better than the rest 7/11 years, N = 3 disagrees.
- [Results](setups/horizontal/support-breakdown-short/q23-support-breakdown/RESULTS.md): fails; no stand-alone run; stopping rule ends short-side level research.

## 2026-10-07: Q24 trade-result streaks

- [Q24](baseline/q24-trade-streaks/RESULTS.md): 14,968 current RTL trades; within-session and cross-session streaks, next-trade R/win rates, week intervals and 2,000 month/day shuffles. No predictive gate passes; five daily wins have only 2/13 next trades.
- Session stops after 3–5 losses reduce DD but help dollars in only 5–6/11 years; no rule adopted. Seven tests and independent replay of every state/20 policies pass, zero mismatches.

## 2026-10-07: Q25 protocol frozen (buy the reclaim of a broken swing-low level)

- After the Q23 charts, user proposed going long off the same levels: buy stop at the level after a red candle breaks
  and closes below it, stop at that candle's low. User set a 3-bar order life and a 0.25 x ATR minimum risk (skips reported).
- [Protocol](setups/horizontal/support-reclaim-long/q25-support-reclaim/PROTOCOL.md): decision control C1 = same candles with the RTL entry (buy stop at the high).

## 2026-10-07: Q25 classify-only runs verified

- Built `support_reclaim.py` / `.mqh` on the Q11 level functions; classify-only EA (primary and S1) matches Python on all
  184,888 eligible bars, 0 mismatches, first time. [Verification](setups/horizontal/support-reclaim-long/q25-support-reclaim/PROTOCOL.md#pre-trade-verification-done-2026-10-07-no-outcomes).
- Counts only: 1,094 / 1,828 orders (2016-19 / 2020-26); min-risk skips 6-8% of breakdowns (none under S1); cost ~0.06R / 0.02R.

## 2026-10-07: Q25 trading runs, the reclaim buy stop fails

- Trading build (3-bar life, tick-level cancel on a touch of the candle low, C1 at the candle high); classify regression
  byte-identical; 4 runs replayed (0 mismatches) and every order's life replayed on M1 data (0 unexplained).
- Execution fact: intrabar spread is 0.01 (source file), so buy stops fill only when the bid reaches them.
- [Results](setups/horizontal/support-reclaim-long/q25-support-reclaim/RESULTS.md): PF 1.042/1.063, mean R -0.073/-0.051, fails mean R > 0 and C1 in 2020-26;
  5/11 years. Small-risk trades drive the losses; risk >= 1 x ATR positive in both periods (post hoc, not a lead).

## 2026-10-07: Q25 follow-up without cancellation on the low

- User: taking out the signal candle's low does not invalidate the setup (cancel-on-touch was my addition). Plan fixed and
  committed first (exploratory); same EA with CancelOnLow = false; all runs verified incl. M1 order-life replay.
- [Result](setups/horizontal/support-reclaim-long/q25-support-reclaim/RESULTS.md#no-cancellation-result-2026-10-07-also-fails-the-added-trades-are-mixed):
  fails (PF 0.964/1.059, R -0.113/-0.006, below C1). Q25 trades reappear unchanged; the added trades are mixed
  (PF 0.855 / 1.052). Q25 closed.

## 2026-10-07: long + short baselines merged (descriptive)

- User asked whether the Q23 short mirror baseline (green candle, sell stop at its low) smooths the RTL long
  baseline. Both runs have identical tester settings (2010-06 to 2026-07, 1R, run cap 3); ledgers summed by exit day,
  $1.05 costs. [Script](../python/merge_long_short.py), [chart](figures/long_short_equity.png).
- No: daily correlation -0.39, but shorts lose in 13/17 years, including the long's losing years 2010-14 and 2016.
  Short P&L is positive in only 7/32 losing long quarters. Net $37,439 -> $8,009, max DD $8,186 -> $24,617.
  The one hedge year is 2022 (+$9,620), given back in 2023 (-$12,206). Merging also assumes a hedging account:
  14,916/23,427 long trades overlap a short in time.

## 2026-10-07: docs reorganised by setup type

- At the user's request (hand sketch of setups, [photo](reference/setup_map_sketch.jpg)), docs/ now has one folder per
  setup under `setups/horizontal/` and `setups/trendlines/`, one subfolder per study (PROTOCOL.md, RESULTS.md, img/),
  `baseline/` for the RTL strategy studies, `reference/`, and placeholders for untested setups. Map: [README](README.md).
- 80 files moved with git mv; every relative link rewritten and checked; doc paths in python/ updated
  (old -> new in [moved_files.json](reference/moved_files.json)). Support reclaim renumbered Q24 -> Q25 (trade streaks
  already had Q24). Protocol hash checks now accept the recorded version from git history (`protocol_matches`).

## 2026-10-08: ES 1-minute data for unseen-instrument tests

- User downloaded ES (Databento, 2010-06 → 2026-10-06, two CSVs). Both files pass every check and join without
  gap or overlap. Built `MT5_ES_continuous_2010-2026_ohlcv-1m.csv` with the NQ rules (script generalised to
  `python/build_continuous.py`; NQ output reproduced byte for byte). Details: [DATA_BUILD.md](reference/DATA_BUILD.md#es-build-2026-10-08).
- The old ES conversion (`MT5_v_converted.csv`) has calendar-spread prices on 3 days (2017-03-13, 2017-12-11,
  2019-06-17). Next: user imports the new file as an MT5 custom symbol.

## 2026-10-08: RTL baseline on MES (unseen instrument)

- User created `MEScontDTBNT20102026` and asked for the baseline on it, compared with MNQ. Same EA (runband, RR 1,
  cap 3) and tester settings; the MNQ rerun reproduces the existing baseline ledger exactly.
  [Results](baseline/mes-unseen-instrument/RESULTS.md).
- **No edge on MES even before costs:** mean R −0.039 / +0.002 (2016–19 / 2020–26) vs MNQ +0.093 / +0.085, intervals
  apart; win rate 2–4 points lower; net loss in 15/17 years. The MNQ edge does not transfer to ES.
- Found two ES source-data holes (2020-02-28, 2020-06-30 stop mid-session); noted in DATA_BUILD. Negligible here.

## 2026-10-08: signal colour (GG) and a no-pattern control

- Question: is the edge the red candle, or just being long NQ? User suggested GG (buy over green). One EA, `SignalMode`
  red / green / any / market-buy control. [Results](baseline/signal-colour/RESULTS.md).
- Not drift: the control earns +0.011 / +0.009 R before costs (intervals include 0). Green ≈ red (+0.073 / +0.066 vs
  +0.093 / +0.085 R, overlapping). The edge is the buy stop over a previous M30 high. RTL + GG = ~2x net and ~2x DD
  (corr +0.62). New EA `mt5/experts/GG_r_MFE_buy-stop-entry_runband.cs` (RTL with the colour flipped, verified).

*Add a dated section after each working session: the question, the answer, and a link to the
study doc. Keep each step to one or two lines.*
