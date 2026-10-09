# Project status

Updated 2026-10-09. **Start here.** All study docs are mapped by setup type in [README.md](README.md). Each study below links to the full evidence.
For the day-by-day history, see [JOURNAL.md](JOURNAL.md).

**ES data for unseen-instrument tests (2026-10-08):** continuous ES 1-minute file built with the NQ rules
(`F:\DATABENTO\ES_16_YEARS\MT5_ES_continuous_2010-2026_ohlcv-1m.csv`, 2010-06-07 → 2026-10-07), input checks clean
([DATA_BUILD](reference/DATA_BUILD.md#es-build-2026-10-08)). Do not use the old ES conversion: 3 days hold spread prices.
Two ES-only data holes (2020-02-28, 2020-06-30). Imported as `MEScontDTBNT20102026`.

**[Baseline on MES](baseline/mes-unseen-instrument/RESULTS.md) (2026-10-08): the RTL edge does not transfer.** Unchanged
baseline EA and settings: MES mean R before costs −0.039 / +0.002 (2016–19 / 2020–26) vs MNQ +0.093 / +0.085, 95%
intervals apart. PF net 0.930 / 0.979; 15/17 years lose. Costs in R are the same on both, so the gap is the
signal itself (win rate 2–4 points lower). Treat MNQ results as unconfirmed on independent data.

**[Signal colour + control](baseline/signal-colour/RESULTS.md) (2026-10-08, exploratory): the edge is the buy stop, not the
colour or drift.** On MNQ a market-buy control with the same stop and exit earns ~0 R before costs (+0.009 / +0.007, audited). Green
signals nearly match red (+0.073 / +0.066 vs +0.093 / +0.085 R). RTL + GG together = ~2x net and ~2x DD. GG EA:
`mt5/experts/GG_r_MFE_buy-stop-entry_runband.cs`. **Same control on MES:** the buy stop beats the plain long there too,
by +0.029 / +0.044 / +0.042 R (2010–15 / 2016–19 / 2020–26, audited, all intervals above 0), about half the NQ gain. But the
MES plain long itself loses −0.15 / −0.08 / −0.04 R (NQ ≈ 0), so RTL fails there. The market's background decides.

**[Why ES differs](baseline/nq-vs-es/RESULTS.md) (2026-10-08, exploratory): mostly tick granularity.** After a touch of
the previous M30 high, NQ follows through and ES falls back. NQ rounded to an ES-like grid loses half (2016–26) to all
(2010–15) of that difference; the rest sits in tiny ES candles. **MT5 on the coarse symbol** (`MNQcoarseDTBNT20102026`):
RTL mean R before costs −0.123 / +0.020 / +0.041 (2010–15 / 2016–19 / 2020–26) vs NQ +0.005 / +0.093 / +0.085. The edge needs
candles spanning many ticks; ES also has a negative plain long that granularity doesn't explain.

**[NQ fixed-grid resolution](baseline/granularity/RESULTS.md) (2026-10-09, exploratory):** all 30 runs, every grid origin:
wider price grids progressively reduce RTL minus control (2020–26 +0.078 → +0.004 R). Ordered by steps per candle, the
NQ periods line up on roughly one curve (near 0 at ~15 steps, +0.06 to +0.09 R from ~30), so 2010–15's weak edge looks
mostly like low resolution. No cutoff or filter adopted. Logger fix: market-entry controls omit fast stops; all
2026-10-08 ledgers re-audited (≤ 0.005 R change).

**[Complete paths: NQ / coarse NQ / ES](baseline/path-interaction/RESULTS.md) (2026-10-09, exploratory): ES line closed.** ES
doesn't lose at the bar-close exit (touch-to-close retention equal in 2020–26). It reaches +1R slightly less and extends less,
in both RTL and the plain long. Its plain-long gap vs coarse NQ sits mostly in candles under ~24 steps (hypothesis: real
tick noise near tight stops). No rule change. Next: MNQ forward test, logging slippage and candle size in ticks.

**[Q24 trade-result streaks](baseline/q24-trade-streaks/RESULTS.md) (2026-10-07): no predictive or daily-stop gate passes.**
Current RTL ledger, 14,968 trades, $1.05 costs: after three same-session losses the next-trade win rate
is 41.9%/41.1% (baseline 43.4%/43.0%); mean-R difference intervals include zero. Five-win daily
streaks have only 2/13 next trades. Session stops after 3–5 losses reduce drawdown but improve
dollars in only 5–6/11 years; retain as a risk trade-off, no adoption. Sequence tests and independent
replay of all states/20 policies pass. [Protocol](baseline/q24-trade-streaks/PROTOCOL.md).

**Trendline research (2026-10-04):** Q14 asked the Q11/Q12 questions for rising
trendlines (consecutive higher swing lows, one week). Signals at intact trendline
support do **worse** than every other signal in both periods (PF 1.029/0.950 vs
1.114/1.124); broad contact is worse too. No filter ([results](setups/trendlines/uptrend-bounce-long/q14-trendline-support/RESULTS.md),
[index](setups/trendlines/README.md)). **Q15 falling resistance lines pass the gate** ([results](setups/trendlines/downtrend-breakout-long/q15-falling-resistance/RESULTS.md)):
red signals pressing into an intact falling line from below, PF 1.325/1.332 vs 1.088/1.090,
avg R +0.093/+0.110 vs -0.012/+0.056, 412/693 fills, 8/11 years; sensitivities and broad agree.
Caveats: R intervals include zero, 2023-25 flat, partial 2026 large, gap is in entries below
the line (not true breaks). [Q16 audit](setups/trendlines/downtrend-breakout-long/q16-resistance-concentration/RESULTS.md): broadly spread
(887 lines, max 5 fills per line), survives every year/week deletion and trimming. Next: user chose a
stand-alone candidate-only EA (whole frozen group primary; entry-below-line as a label).
**[Q17](setups/trendlines/downtrend-breakout-long/q17-standalone/RESULTS.md): traded alone, the candidates do not survive** the frozen rule: PF 1.242/1.238
but mean R +0.039/+0.050 vs baseline -0.004/+0.060, 4/11 years. The ~40% of trades freed from
baseline blocking are break-even. Shared trades are identical to the baseline. No filter or sizing.

**Horizontal breakouts (Q18) pass both stages** ([results](setups/horizontal/resistance-breakout-long/q18-breakout/RESULTS.md)): red signals
whose buy stop sits at an intact one-week swing-high level, approached from below. Traded alone
(candidate-only EA, gate verified on all 52,070 signals): 1,083/1,685 trades, PF 1.164/1.204, mean R
+0.062/+0.110 vs baseline -0.004/+0.060, 8/11 years; recent interval excludes zero; freed trades
hold up. Caveats: 2016-19 weak (+$1.7k), 2010-15 negative (worse than baseline 5/6 years), OHLC
only (generated ticks not a stop criterion, user 2026-10-05). Nothing adopted. Manual-run EA:
`mt5/experts/RR_r_MFE_buy-stop-entry_breakout.cs`. [Q19 audit](setups/horizontal/resistance-breakout-long/q19-breakout-concentration/RESULTS.md):
broadly spread (max 5 trades per level), survives every year/week deletion; paired mean-R difference vs
RTL +0.066/+0.050, intervals just include zero per period, exclude it pooled. Next: forward/demo evidence.

**[Q20](setups/trendlines/uptrend-bounce-long/q20-trendline-limit/RESULTS.md) (2026-10-05): a buy limit resting on the Q14 rising line fails.**
Stop 0.5 x ATR, baseline 1R exit, any candle colour: PF 0.773/0.969, mean R -0.238/-0.023 (1,484/2,370 trades);
45% stopped in the fill bar (price goes through the line); trade-through and stop 0.25/1.0 x A sensitivities lose too;
beats the regime-matched random-distance control in 2/9 years. 9 MT5 runs replayed in Python with 0 mismatches.
Nothing adopted.

**[Q21](setups/trendlines/uptrend-breakdown/q21-breakdown-short/RESULTS.md) (2026-10-06): shorting the break of the Q14 rising line fails.**
Red M30 candle closing below a live line -> sell stop at its low, stop at its high, next bar only, 1R bar-close exit
(first short-side study). PF 0.893/0.916, mean R -0.081/-0.025 (558/928 trades); loses before costs too; 51% stops vs
32% targets. Beats "any red bar in the same regime" (C1) in mean R but 6/11 years, bootstrap includes zero; S1 (deeper
break) also loses; every red-candle short loses on NQ (C2 PF 0.84/0.97). 4 MT5 runs replayed, 0 mismatches. Nothing adopted.
Exploratory 2R target (user request, plan fixed first): also fails, PF 0.916/0.891, mean R -0.050/-0.041. Red-candle
shorts lose in bear regimes too (descriptive).

**[Q22](setups/trendlines/uptrend-breakdown/q22-breakdown-rtl/RESULTS.md) (2026-10-06): RTL longs at or after a rising-line break - no gate passes.**
RTL buys on the red breakdown candle are worse than every other signal (PF 1.010/0.831 vs 1.111/1.123, avg R -0.070/-0.069
vs -0.002/+0.065, 7/11 years; 2020-26 interval excludes zero), but the S1 (deeper break) sensitivity disagrees, so no skip
filter. Signals in the 10 bars after a break: no difference. With Q21: the break bar pays in neither direction.
**[Q23](setups/horizontal/support-breakdown-short/q23-support-breakdown/RESULTS.md) (2026-10-07): the Q18 mirror short fails stage 1; short-side level research stops.**
Green signal's sell stop at an intact swing-low level approached from above: better than other green signals (7/11 years)
but PF 0.992/1.038, N = 3 disagrees. The short mirror baseline (stage 0 MT5 run) loses in every period, PF 0.750/0.916/0.974,
confirming the user's manual test. Every short tried in Q21-Q23 loses on NQ.

**[Q25](setups/horizontal/support-reclaim-long/q25-support-reclaim/RESULTS.md) (2026-10-07): buying the reclaim of a broken swing-low level fails.**
Buy stop at the level after a red candle closes below it, stop at its low, 3-bar life: PF 1.042/1.063 but mean R
-0.073/-0.051; worse than the candle-high entry (C1) in 2020-26; 5/11 years. 58% of orders cancelled (low taken first),
a third of fills stopped in the fill bar. Post hoc only: risk >= 1 x ATR positive in both periods. Execution fact: inside a
minute the tester spread is 0.01, so a buy stop fills only when the bid trades at it (14,541 orders replayed, 0 unexplained).
Exploratory follow-up without cancellation on a touch of the low (user's original design): also fails, PF 0.964/1.059,
mean R -0.113/-0.006, below C1 in both periods, 4/11 years; the added low-taken-first trades are mixed (PF 0.855/1.052).

**Level research:** Q13 audited Q12's previous-week-low lead. Its 276 fills
represent 126 weekly events; earlier advantages survive single-year/week
deletions, but recent dollar profit is concentrated in 2025-2026 and the small
recent R advantage is fragile. Trimming/equal-event comparisons stay positive;
cluster intervals include zero. Inconclusive, no filter
([results](setups/horizontal/support-bounce-long/q13-weekly-low/RESULTS.md), [level index](setups/horizontal/README.md)).
Q12's broader swing/session contact comparisons remain inconsistent across periods.
[Speed research is archived](setups/horizontal/support-reclaim-long/q09-reclaim-speed/ARCHIVE.md).

## The strategy (current research baseline)

| | |
|---|---|
| Signal | The last closed M30 candle is red |
| Entry | Buy stop at its high; stop loss at its low; risk = candle range |
| Exit | Market exit after the first bar that closes ≥ entry + **1.0R**; flatten at 23:30 |
| Filter | `MaxRedRun = 3` (skip if more than 3 reds in a row); `MinLocation = 0` (off) |
| Session safety | `FlattenFallback = true` + `UseEarlyCloseCalendar = true`: always flat at session end, including early closes |
| Sizing / costs | 1 contract; $1 per round-turn modelled in Python (real cost $1.05) |
| EA | [`mt5/experts/RR_r_MFE_buy-stop-entry_runband.cs`](../mt5/experts/RR_r_MFE_buy-stop-entry_runband.cs) (+ `early_closes.mqh`) |
| Data | `MNQcontDTBNT20102026`: NQ rebuilt from Databento with a consistent clock ([DATA_BUILD.md](reference/DATA_BUILD.md)), priced as MNQ |

**Execution qualification (2026-10-02):** the figures below use one-minute OHLC
modelling. The [averaging study](baseline/averaging-entry/RESULTS.md) found that changing
to finer generated ticks reduced matched baseline net at $1.05/contract from
$6,485 to $612 (2016–19) and $37,981 to $19,435 (2020–26). Both modes use the
same minute data; neither is real-tick validation. The user accepts one-minute
OHLC for further raw screening to avoid slow generated-tick runs. Keep this
execution sensitivity in mind when interpreting results or considering live
sizing. The research baseline rules stay unchanged.

**Earlier OHLC results** (rebuilt data, calendar on, net of $1 commission, 1 contract):

| Period | RR | Trades | Net $ | Net PF | Net DD $ | Avg net R |
|---|---:|---:|---:|---:|---:|---:|
| 2020-01 → 2026-07 | 1.0 | 9,272 | 38,433 | 1.108 | 4,837 | +0.061 |
| 2020-01 → 2026-07 | 2.5 | 7,328 | 40,524 | 1.119 | 4,530 | +0.092 |
| 2016 → 2019 | 1.0 | 5,699 | 6,816 | 1.111 | 1,427 | +0.004 |
| 2016 → 2019 | 2.5 | 4,514 | 8,858 | 1.150 | 1,538 | +0.025 |

The edge is thin, and all of 2015–2026 has been looked at. No untouched data is left for validation.
Data before 2016 had different market hours (trading until ~16:30 Chicago) and is no longer a reference period.

## Decisions

**Adopted**
- `MaxRedRun = 3`. Chosen on 2015–19 by a pre-set rule, then tested frozen on 2020–26:
  PF up in 6 of 7 years, DD −17%, profit flat. A **small** but real effect.
  **Confirmed on clean data** ([check](baseline/maxredrun/RESULTS.md)): training picked cap 1,
  which tested frozen at PF +0.036 and DD −30% but −23% profit. Cap 3 is the balanced choice
  (DD −16%, profit −2%). The cap value is a risk-vs-profit trade-off. **Decided 2026-10-01:
  keep cap 3**; cap 1 is the conservative alternative.
- `FlattenFallback` fix (bug: positions were held up to 6.5 days).
- Rebuilt data (`MNQcontDTBNT20102026`) and the early-close calendar: no trade crosses
  a session any more. Results match the old data closely, so earlier entry findings stand.
- **RR = 1.0** (2026-10-01). On clean data, 2.0–3.0 didn't beat 1.0 in both periods by the
  pre-set rule ([check](baseline/rr-clean-data/RESULTS.md)). Revisit only with a new reason, e.g.
  measured live slippage.

**Rejected** (evidence kept, don't retest without a new reason)
- Q15-Q17 falling trendline resistance: passed the attribution gate (Q15) and the concentration audit
  (Q16), but traded alone (Q17) mean R +0.039/+0.050 does not beat the baseline -0.004/+0.060 and only
  4/11 years; freed trades break-even. No filter, stand-alone strategy or sizing change.
- Q14 rising trendline support ([results](setups/trendlines/uptrend-bounce-long/q14-trendline-support/RESULTS.md),
  [protocol](setups/trendlines/uptrend-bounce-long/q14-trendline-support/PROTOCOL.md)): candidate/rest PF 1.029/1.114 and
  0.950/1.124, avg R -0.029/-0.038; 5/11 years better; two-week and N=3 checks
  also worse recently. Broad unbroken-line contact also worse in both periods. No filter.
- Q12 broad support-origin contact ([results](setups/horizontal/support-bounce-long/q12-broad-support/RESULTS.md),
  [protocol](setups/horizontal/support-bounce-long/q12-broad-support/PROTOCOL.md)): primary contact/rest PF
  1.137/1.061 earlier, 1.084/1.143 recently; mean R difference +0.028/-0.029,
  5/11 years better. Two weeks and N=3 also reverse. No broad filter supported;
  broad previous-week contact remains a distinct small-sample lead, not ruled out.
- Q11 one-week M30 swing-low support ([results](setups/horizontal/support-bounce-long/q11-level-visit/RESULTS.md),
  [protocol](setups/horizontal/support-bounce-long/q11-level-visit/PROTOCOL.md)): candidate/rest PF 1.201/1.087 and
  1.140/1.099, avg R +0.036 / +0.005 better, 7/11 years; all intervals include
  zero and N = 3 disagrees, so no full rerun. Recently, signals with no level
  nearby (PF 1.191) do better than the candidates. Q10's weekly lead not reproduced.
- Q10 support-interaction screen ([results](setups/horizontal/support-bounce-long/q10-support-interaction/RESULTS.md)).
  **Primary, original exit:** current-session interaction/rest PF 1.179/1.079
  earlier versus 1.086/1.114 recently; previous session flips too. Previous-week
  interactions beat the rest in both periods (PF 1.707/1.451, 9/11 years) but
  with only 72/137 fills, so no candidate qualifies. The fixed 1R SL/TP run is
  secondary context and does not replace the original bar-close exit.
- **Archived direction:** Q9 fast-recovery candidate ([results](setups/horizontal/support-reclaim-long/q09-reclaim-speed/RESULTS.md),
  [protocol](setups/horizontal/support-reclaim-long/q09-reclaim-speed/PROTOCOL.md)): 130/218 matched current-session pairs
  show no reliable upward advantage after the M30 close; all candidate gates
  fail. The Q8 two-sided R effect weakens/reverses in lagged-volatility units,
  consistent with smaller reclaim signal ranges. Intrabar/early-minute entry
  follow-ups are parked, not next steps; no EA change.
- Q8 support-reclaim filter ([results](setups/horizontal/support-reclaim-long/q08-breach-reclaim/RESULTS.md),
  [protocol](setups/horizontal/support-reclaim-long/q08-breach-reclaim/PROTOCOL.md)): current-session reclaims more often
  precede a +0.5R endpoint after 90 minutes (+6.1 / +3.1 percentage points), but
  mean price return and filled-trade PF do not improve across both periods.
  A post-hoc check shows the recent excess is two-sided dispersion (-0.5R tail
  also rises); only 2016-19 hints at upward bias. No strategy filter adopted.
- Q6/Q7 first price-level screen ([results](setups/horizontal/support-bounce-long/q06-q07-price-levels/RESULTS.md),
  [protocol](setups/horizontal/support-bounce-long/q06-q07-price-levels/PROTOCOL.md)): previous-session near-support PF rankings
  disagree and the earlier near group is sparse; resistance within 1R remains
  profitable in both periods at all predefined cutoffs. No filter. Current-session
  and previous-week comparisons also provide no reason to avoid nearby highs.
  Pivot zones, level interaction and role reversal remain separate questions.
- Trend-conditioned target RR on the unchanged RTL baseline
  ([results](baseline/trend-rr/RESULTS.md), [protocol](baseline/trend-rr/PROTOCOL.md)):
  primary mild/strong mappings reduce net/DD in both usual comparison periods;
  historical annual selection also fails the required improvement. Fixed 1R stays.
- Minimum red count, drop size, `location` filter, 10 other bar features.
- Q1 interrupted decline, Q2 recovery after a new low.
- Fixed take-profit at 1R (first touch): worse than the bar-close exit in both periods.
- Resting limit above the target to "capture the wick" (estimate from MFE, 2026-10-01).
  Winners give back 0.38R / 0.32R on average from their best point (2015–19 / 2020–26),
  but a limit at 1.5–4R is worse at every level in both periods (2020–26: $30.7–35.5k
  vs $37.4k). It caps the big runners, which are worth more than the give-back.
- Trailing stop after +1R at 0.25 / 0.5 / 1.0R (full MT5 runs, 2026-10-01): clearly
  worse in 2015–19 at every distance; mixed in 2020–26. Rejected by the pre-set rule.
  The bar-close exit stays.
- Buy-stop-limit entry (an experiment; not used for testing).
- Switching off session blocks (time of day): every block is profitable in both periods, and
  none is consistently weak ([results](baseline/time-of-day/RESULTS.md)). Trade windows unchanged.
- Standalone buy-limit entry near the candle low (offsets 80/90/95%, plus 80% with RR 2):
  loses in every year of 2016–19 at every setting. In 2020–26 it's profitable but weaker than
  the baseline, concentrated in ~20 trades, and positively correlated with it
  ([results](baseline/limit-only/RESULTS.md)).
- One equal-sized averaging limit near the original stop, original target kept
  ([full study](baseline/averaging-entry/RESULTS.md), 2026-10-02): 5/10/20% distances all
  worse in the OHLC model; 10% also worse in both periods with generated ticks.
  The added leg loses money in every year from 2016 through partial 2026.

**Open**
- **Q18 horizontal breakout lead** ([results](setups/horizontal/resistance-breakout-long/q18-breakout/RESULTS.md)): passed attribution and stand-alone
  stages under one-minute OHLC. Q19 audit done (broad, not concentrated). Next: forward/demo evidence; user is making manual MT5 runs.
- **Standalone buy limits** ([results](baseline/limit-only/RESULTS.md)): offsets
  80/90/95% below signal high are profitable in 2020–26 but lose in every
  year of 2016–19. No adoption; retain the separate research EA. Tested the
  archived high-trigger behavior, using one-minute OHLC only.
- **Symbol:** use `MNQcontDTBNT20102026_2` (rebuilt, tail bars dropped) for all new runs.
- **Live sizing:** decide at the end. Real cost is $1.05/contract; slippage is unknown.

## Next steps, in order

1. **Entry-shape questions:** Q1–Q5 all answered, no filter (incl. signal-candle shape).
   New ideas go into the Inbox in [RESEARCH_QUESTIONS.md](reference/RESEARCH_QUESTIONS.md).
   **Price-level context:** Q6/Q7 session/week proximity screen complete, no filter.
   Q8 support reclaim complete: a +0.5R response-frequency association that is
   mostly wider dispersion in signal-R units (both tails), no stable RTL filter.
   Q9 speed is archived. Q10 is complete; its original-exit screen is primary.
   [Q11](setups/horizontal/support-bounce-long/q11-level-visit/RESULTS.md) one-week swing-low support: small, unconfirmed
   edge, no filter. Open inbox ideas: levels approached from below, level history.
   See the [level-study index](setups/horizontal/README.md); no immediate-entry speed work
   is queued. Resistance paths, level history and role reversal remain separate.
2. Execution sensitivity remains unresolved; do not equate OHLC screening
   profits with verified fills. Further tick-generation runs are not planned.
3. Sizing: at the real cost ($1.05/contract), "fixed $200 risk, max 5 contracts" beats
   1 contract on net/DD in 2020–26 but not in 2015–19. Sizing does not change the RR
   answer. Keep 1 contract for research; decide live sizing at the end.

## Study index

| Date | Study | Verdict |
|---|---|---|
| 10-07 | [Q24: trade-result streaks](baseline/q24-trade-streaks/RESULTS.md) | No reliable next-trade prediction; five wins too sparse; loss-based session stops reduce DD but fail yearly consistency; no rule adopted |
| 10-04 | [Q18: horizontal swing-high breakout](setups/horizontal/resistance-breakout-long/q18-breakout/RESULTS.md) | **Passes both stages** (attribution, stand-alone EA); first level lead to survive own execution; OHLC only, weak 2016-19 |
| 10-04 | [Q17: stand-alone falling-resistance EA](setups/trendlines/downtrend-breakout-long/q17-standalone/RESULTS.md) | Does not survive own execution: PF 1.24 but mean R below baseline recently, 4/11 years |
| 10-04 | [Q15: falling trendline resistance](setups/trendlines/downtrend-breakout-long/q15-falling-resistance/RESULTS.md) | **Passes the gate** in both periods with both sensitivities; qualifies for a full MT5 run protocol; 2023-25 flat |
| 10-04 | [Q14: rising trendline support](setups/trendlines/uptrend-bounce-long/q14-trendline-support/RESULTS.md) | Worse than every other signal in both periods; loses money recently; no filter |
| 10-04 | [Q11: one-week swing-low support](setups/horizontal/support-bounce-long/q11-level-visit/RESULTS.md) | Slightly better than the rest in both periods, but small, intervals include zero, N = 3 disagrees; no filter |
| 10-03 | [Q10: support interaction](setups/horizontal/support-bounce-long/q10-support-interaction/RESULTS.md) | Original exit primary: session levels flip between periods; previous-week better in both but too few fills; no filter |
| 10-03 | [Q9: recovery speed](setups/horizontal/support-reclaim-long/q09-reclaim-speed/RESULTS.md) | Archived direction; evidence retained, no speed/early-entry follow-up queued |
| 10-03 | [Q8: support breach and reclaim](setups/horizontal/support-reclaim-long/q08-breach-reclaim/RESULTS.md) | More +0.5R responses after current-session reclaims; mixed mean return and PF, no filter |
| 10-03 | [Q6/Q7: support proximity and overhead room](setups/horizontal/support-bounce-long/q06-q07-price-levels/RESULTS.md) | No filter from previous-session primary or predefined neighbors; current-session/week sources retained separately |
| 10-02 | [RTL trend-conditioned RR](baseline/trend-rr/RESULTS.md) | Primary mappings and annual selection fail to improve on fixed 1R; no forward test |
| 09-28/29 | [Entry filters and bar features](reference/RESEARCH_RESULTS.md) | Only the red-run cap survives; location and other features don't |
| 09-29 | [MaxRedRun train/test](reference/RESEARCH_RESULTS.md#next-steps) | Cap 3 passes out of sample; the effect is small |
| 09-30 | [Preceding candles Q1/Q2](baseline/q01-q02-preceding-candles/RESULTS.md) ([protocol](baseline/q01-q02-preceding-candles/PROTOCOL.md)) | No filter adopted; the periods disagree |
| 09-30 | [Exit estimate and data review](reference/EXIT_AND_DATA_REVIEW.md) | First-touch exit worse; several data caveats |
| 09-30 | [Exit thresholds](baseline/exit-threshold/RESULTS.md) ([protocol](baseline/exit-threshold/PROTOCOL.md)) | Fixed TP worse; RR comparison distorted by the flatten bug |
| 09-30 | [RR 0.5–5.0 grid](baseline/rr-optimization/RESULTS.md) | Noisy curve; RR>1 gains were mostly multi-day holds |
| 10-01 | [Flatten fallback fix](baseline/flatten-fallback/RESULTS.md) | Bug fixed; baseline barely changes; RR still open |
| 10-01 | [Trailing stop after +1R](baseline/trailing-stop/RESULTS.md) | Rejected at all distances; keep the bar-close exit |
| 10-01 | [Data rebuild](reference/DATA_BUILD.md) | Clean NQ series from Databento source; old data was shifted 1 h in DST-mismatch weeks |
| 10-01 | [Early-close calendar](baseline/early-close-calendar/RESULTS.md) | No overnight holds left; on clean data 2.5R beats 1R in both periods |
| 10-01 | [RR 1.0 vs 2.0 / 2.5 / 3.0, clean data](baseline/rr-clean-data/RESULTS.md) | Rule not met by $78 → RR stays 1.0; higher RR never meaningfully worse |
| 10-01 | [MaxRedRun train/test, clean data](baseline/maxredrun/RESULTS.md) | Cap confirmed (PF up, DD down); cap 1 = safest, cap 3 = balanced |
| 10-02 | [Standalone buy-limit entry](baseline/limit-only/RESULTS.md) ([protocol](baseline/limit-only/PROTOCOL.md)) | Rejected: loses every 2016–19 year at every offset (incl. 80% / RR 2) |
| 10-02 | [Time of day](baseline/time-of-day/RESULTS.md) | No block to switch off; every block profitable in both periods |
| 10-02 | [Q3: overlap vs staircase](baseline/q03-overlap/RESULTS.md) | No group loses in both periods; no filter |
| 10-02 | [Q4: pullback vs broader move](baseline/q04-context/RESULTS.md) | All groups profitable in both periods; no filter |
| 10-02 | [Q5: signal-candle shape](baseline/q05-candle-shape/RESULTS.md) | Doji and full body each lose in one period only; no filter |
| 10-02 | [Near-stop averaging entry](baseline/averaging-entry/RESULTS.md) ([protocol](baseline/averaging-entry/PROTOCOL.md)) | Rejected in both models; also exposes material baseline execution sensitivity |
| 10-02 | [Standalone buy-limit entry](baseline/limit-only/RESULTS.md) ([protocol](baseline/limit-only/PROTOCOL.md)) | Positive recently, negative in every earlier year; no adoption; OHLC only |

## How we test

- Fix definitions and the selection rule **before** running. Keep negative results.
- Use one-minute OHLC for raw screening per the user's 2026-10-02 preference;
  document intraminute uncertainty without automatically launching generated ticks.
- Confirm any filter with a **full MT5 rerun**. Removing rows from a CSV misses the
  changed entries (a skipped trade frees the position for another one).
- Report **both** net $ and average net R, and say which one decides.
- Look for broad regions, not the best single grid step. Neighbouring steps differ by ±$4–5k from noise.
