# Project status

Updated 2026-10-06. **Start here.** Each study below links to the full evidence.
For the day-by-day history, see [JOURNAL.md](JOURNAL.md).

**Trendline research (2026-10-04):** Q14 asked the Q11/Q12 questions for rising
trendlines (consecutive higher swing lows, one week). Signals at intact trendline
support do **worse** than every other signal in both periods (PF 1.029/0.950 vs
1.114/1.124); broad contact is worse too. No filter ([results](trendlines/TRENDLINE_SUPPORT_RESULTS.md),
[index](trendlines/README.md)). **Q15 falling resistance lines pass the gate** ([results](trendlines/TRENDLINE_RESISTANCE_RESULTS.md)):
red signals pressing into an intact falling line from below, PF 1.325/1.332 vs 1.088/1.090,
avg R +0.093/+0.110 vs -0.012/+0.056, 412/693 fills, 8/11 years; sensitivities and broad agree.
Caveats: R intervals include zero, 2023-25 flat, partial 2026 large, gap is in entries below
the line (not true breaks). [Q16 audit](trendlines/RESISTANCE_CONCENTRATION_RESULTS.md): broadly spread
(887 lines, max 5 fills per line), survives every year/week deletion and trimming. Next: user chose a
stand-alone candidate-only EA (whole frozen group primary; entry-below-line as a label).
**[Q17](trendlines/STANDALONE_RESULTS.md): traded alone, the candidates do not survive** the frozen rule: PF 1.242/1.238
but mean R +0.039/+0.050 vs baseline -0.004/+0.060, 4/11 years. The ~40% of trades freed from
baseline blocking are break-even. Shared trades are identical to the baseline. No filter or sizing.

**Horizontal breakouts (Q18) pass both stages** ([results](levels/BREAKOUT_RESULTS.md)): red signals
whose buy stop sits at an intact one-week swing-high level, approached from below. Traded alone
(candidate-only EA, gate verified on all 52,070 signals): 1,083/1,685 trades, PF 1.164/1.204, mean R
+0.062/+0.110 vs baseline -0.004/+0.060, 8/11 years; recent interval excludes zero; freed trades
hold up. Caveats: 2016-19 weak (+$1.7k), 2010-15 negative (worse than baseline 5/6 years), OHLC
only (generated ticks not a stop criterion, user 2026-10-05). Nothing adopted. Manual-run EA:
`mt5/experts/RR_r_MFE_buy-stop-entry_breakout.cs`. [Q19 audit](levels/BREAKOUT_CONCENTRATION_RESULTS.md):
broadly spread (max 5 trades per level), survives every year/week deletion; paired mean-R difference vs
RTL +0.066/+0.050, intervals just include zero per period, exclude it pooled. Next: forward/demo evidence.

**[Q20](trendlines/TRENDLINE_LIMIT_RESULTS.md) (2026-10-05): a buy limit resting on the Q14 rising line fails.**
Stop 0.5 x ATR, baseline 1R exit, any candle colour: PF 0.773/0.969, mean R -0.238/-0.023 (1,484/2,370 trades);
45% stopped in the fill bar (price goes through the line); trade-through and stop 0.25/1.0 x A sensitivities lose too;
beats the regime-matched random-distance control in 2/9 years. 9 MT5 runs replayed in Python with 0 mismatches.
Nothing adopted.

**[Q21](trendlines/BREAKDOWN_SHORT_RESULTS.md) (2026-10-06): shorting the break of the Q14 rising line fails.**
Red M30 candle closing below a live line -> sell stop at its low, stop at its high, next bar only, 1R bar-close exit
(first short-side study). PF 0.893/0.916, mean R -0.081/-0.025 (558/928 trades); loses before costs too; 51% stops vs
32% targets. Beats "any red bar in the same regime" (C1) in mean R but 6/11 years, bootstrap includes zero; S1 (deeper
break) also loses; every red-candle short loses on NQ (C2 PF 0.84/0.97). 4 MT5 runs replayed, 0 mismatches. Nothing adopted.
Exploratory 2R target (user request, plan fixed first): also fails, PF 0.916/0.891, mean R -0.050/-0.041. Red-candle
shorts lose in bear regimes too (descriptive).

**Q22 (2026-10-06, frozen, not run): RTL longs at or after a rising-line break** ([protocol](trendlines/BREAKDOWN_RTL_PROTOCOL.md)).
Two-sided gate on existing baseline fills (worse -> skip filter, better -> failed-breakdown long).
**Queued as a separate study (user, 2026-10-06):** Q18 mirror short - sell stop at an intact one-week swing-low level
approached from above. The RTL mirror (green candle, sell stop at its low) was tried manually by the user: choppy, unstable.

**Level research:** Q13 audited Q12's previous-week-low lead. Its 276 fills
represent 126 weekly events; earlier advantages survive single-year/week
deletions, but recent dollar profit is concentrated in 2025-2026 and the small
recent R advantage is fragile. Trimming/equal-event comparisons stay positive;
cluster intervals include zero. Inconclusive, no filter
([results](levels/WEEKLY_LOW_ROBUSTNESS_RESULTS.md), [level index](levels/README.md)).
Q12's broader swing/session contact comparisons remain inconsistent across periods.
[Speed research is archived](levels/SPEED_RESEARCH_ARCHIVE.md).

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
| Data | `MNQcontDTBNT20102026`: NQ rebuilt from Databento with a consistent clock ([DATA_BUILD.md](DATA_BUILD.md)), priced as MNQ |

**Execution qualification (2026-10-02):** the figures below use one-minute OHLC
modelling. The [averaging study](AVERAGING_ENTRY_RESULTS.md) found that changing
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
  **Confirmed on clean data** ([check](MAXREDRUN_CLEAN_RESULTS.md)): training picked cap 1,
  which tested frozen at PF +0.036 and DD −30% but −23% profit. Cap 3 is the balanced choice
  (DD −16%, profit −2%). The cap value is a risk-vs-profit trade-off. **Decided 2026-10-01:
  keep cap 3**; cap 1 is the conservative alternative.
- `FlattenFallback` fix (bug: positions were held up to 6.5 days).
- Rebuilt data (`MNQcontDTBNT20102026`) and the early-close calendar: no trade crosses
  a session any more. Results match the old data closely, so earlier entry findings stand.
- **RR = 1.0** (2026-10-01). On clean data, 2.0–3.0 didn't beat 1.0 in both periods by the
  pre-set rule ([check](RR_CLEAN_DATA_RESULTS.md)). Revisit only with a new reason, e.g.
  measured live slippage.

**Rejected** (evidence kept, don't retest without a new reason)
- Q15-Q17 falling trendline resistance: passed the attribution gate (Q15) and the concentration audit
  (Q16), but traded alone (Q17) mean R +0.039/+0.050 does not beat the baseline -0.004/+0.060 and only
  4/11 years; freed trades break-even. No filter, stand-alone strategy or sizing change.
- Q14 rising trendline support ([results](trendlines/TRENDLINE_SUPPORT_RESULTS.md),
  [protocol](trendlines/TRENDLINE_PROTOCOL.md)): candidate/rest PF 1.029/1.114 and
  0.950/1.124, avg R -0.029/-0.038; 5/11 years better; two-week and N=3 checks
  also worse recently. Broad unbroken-line contact also worse in both periods. No filter.
- Q12 broad support-origin contact ([results](levels/BROAD_SUPPORT_RESULTS.md),
  [protocol](levels/BROAD_SUPPORT_PROTOCOL.md)): primary contact/rest PF
  1.137/1.061 earlier, 1.084/1.143 recently; mean R difference +0.028/-0.029,
  5/11 years better. Two weeks and N=3 also reverse. No broad filter supported;
  broad previous-week contact remains a distinct small-sample lead, not ruled out.
- Q11 one-week M30 swing-low support ([results](levels/LEVEL_VISIT_RESULTS.md),
  [protocol](LEVEL_VISIT_PROTOCOL.md)): candidate/rest PF 1.201/1.087 and
  1.140/1.099, avg R +0.036 / +0.005 better, 7/11 years; all intervals include
  zero and N = 3 disagrees, so no full rerun. Recently, signals with no level
  nearby (PF 1.191) do better than the candidates. Q10's weekly lead not reproduced.
- Q10 support-interaction screen ([results](levels/SUPPORT_INTERACTION_RESULTS.md)).
  **Primary, original exit:** current-session interaction/rest PF 1.179/1.079
  earlier versus 1.086/1.114 recently; previous session flips too. Previous-week
  interactions beat the rest in both periods (PF 1.707/1.451, 9/11 years) but
  with only 72/137 fills, so no candidate qualifies. The fixed 1R SL/TP run is
  secondary context and does not replace the original bar-close exit.
- **Archived direction:** Q9 fast-recovery candidate ([results](levels/RECLAIM_SPEED_RESULTS.md),
  [protocol](RECLAIM_SPEED_PROTOCOL.md)): 130/218 matched current-session pairs
  show no reliable upward advantage after the M30 close; all candidate gates
  fail. The Q8 two-sided R effect weakens/reverses in lagged-volatility units,
  consistent with smaller reclaim signal ranges. Intrabar/early-minute entry
  follow-ups are parked, not next steps; no EA change.
- Q8 support-reclaim filter ([results](levels/BREACH_RECLAIM_RESULTS.md),
  [protocol](BREACH_RECLAIM_PROTOCOL.md)): current-session reclaims more often
  precede a +0.5R endpoint after 90 minutes (+6.1 / +3.1 percentage points), but
  mean price return and filled-trade PF do not improve across both periods.
  A post-hoc check shows the recent excess is two-sided dispersion (-0.5R tail
  also rises); only 2016-19 hints at upward bias. No strategy filter adopted.
- Q6/Q7 first price-level screen ([results](levels/PRICE_LEVELS_RESULTS.md),
  [protocol](PRICE_LEVELS_PROTOCOL.md)): previous-session near-support PF rankings
  disagree and the earlier near group is sparse; resistance within 1R remains
  profitable in both periods at all predefined cutoffs. No filter. Current-session
  and previous-week comparisons also provide no reason to avoid nearby highs.
  Pivot zones, level interaction and role reversal remain separate questions.
- Trend-conditioned target RR on the unchanged RTL baseline
  ([results](TREND_RR_RESULTS.md), [protocol](TREND_RR_PROTOCOL.md)):
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
  none is consistently weak ([results](TIME_OF_DAY_RESULTS.md)). Trade windows unchanged.
- Standalone buy-limit entry near the candle low (offsets 80/90/95%, plus 80% with RR 2):
  loses in every year of 2016–19 at every setting. In 2020–26 it's profitable but weaker than
  the baseline, concentrated in ~20 trades, and positively correlated with it
  ([results](LIMIT_ONLY_RESULTS.md)).
- One equal-sized averaging limit near the original stop, original target kept
  ([full study](AVERAGING_ENTRY_RESULTS.md), 2026-10-02): 5/10/20% distances all
  worse in the OHLC model; 10% also worse in both periods with generated ticks.
  The added leg loses money in every year from 2016 through partial 2026.

**Open**
- **Q18 horizontal breakout lead** ([results](levels/BREAKOUT_RESULTS.md)): passed attribution and stand-alone
  stages under one-minute OHLC. Q19 audit done (broad, not concentrated). Next: forward/demo evidence; user is making manual MT5 runs.
- **Standalone buy limits** ([results](LIMIT_ONLY_RESULTS.md)): offsets
  80/90/95% below signal high are profitable in 2020–26 but lose in every
  year of 2016–19. No adoption; retain the separate research EA. Tested the
  archived high-trigger behavior, using one-minute OHLC only.
- **Symbol:** use `MNQcontDTBNT20102026_2` (rebuilt, tail bars dropped) for all new runs.
- **Live sizing:** decide at the end. Real cost is $1.05/contract; slippage is unknown.

## Next steps, in order

1. **Entry-shape questions:** Q1–Q5 all answered, no filter (incl. signal-candle shape).
   New ideas go into the Inbox in [RESEARCH_QUESTIONS.md](RESEARCH_QUESTIONS.md).
   **Price-level context:** Q6/Q7 session/week proximity screen complete, no filter.
   Q8 support reclaim complete: a +0.5R response-frequency association that is
   mostly wider dispersion in signal-R units (both tails), no stable RTL filter.
   Q9 speed is archived. Q10 is complete; its original-exit screen is primary.
   [Q11](levels/LEVEL_VISIT_RESULTS.md) one-week swing-low support: small, unconfirmed
   edge, no filter. Open inbox ideas: levels approached from below, level history.
   See the [level-study index](levels/README.md); no immediate-entry speed work
   is queued. Resistance paths, level history and role reversal remain separate.
2. Execution sensitivity remains unresolved; do not equate OHLC screening
   profits with verified fills. Further tick-generation runs are not planned.
3. Sizing: at the real cost ($1.05/contract), "fixed $200 risk, max 5 contracts" beats
   1 contract on net/DD in 2020–26 but not in 2015–19. Sizing does not change the RR
   answer. Keep 1 contract for research; decide live sizing at the end.

## Study index

| Date | Study | Verdict |
|---|---|---|
| 10-04 | [Q18: horizontal swing-high breakout](levels/BREAKOUT_RESULTS.md) | **Passes both stages** (attribution, stand-alone EA); first level lead to survive own execution; OHLC only, weak 2016-19 |
| 10-04 | [Q17: stand-alone falling-resistance EA](trendlines/STANDALONE_RESULTS.md) | Does not survive own execution: PF 1.24 but mean R below baseline recently, 4/11 years |
| 10-04 | [Q15: falling trendline resistance](trendlines/TRENDLINE_RESISTANCE_RESULTS.md) | **Passes the gate** in both periods with both sensitivities; qualifies for a full MT5 run protocol; 2023-25 flat |
| 10-04 | [Q14: rising trendline support](trendlines/TRENDLINE_SUPPORT_RESULTS.md) | Worse than every other signal in both periods; loses money recently; no filter |
| 10-04 | [Q11: one-week swing-low support](levels/LEVEL_VISIT_RESULTS.md) | Slightly better than the rest in both periods, but small, intervals include zero, N = 3 disagrees; no filter |
| 10-03 | [Q10: support interaction](levels/SUPPORT_INTERACTION_RESULTS.md) | Original exit primary: session levels flip between periods; previous-week better in both but too few fills; no filter |
| 10-03 | [Q9: recovery speed](levels/RECLAIM_SPEED_RESULTS.md) | Archived direction; evidence retained, no speed/early-entry follow-up queued |
| 10-03 | [Q8: support breach and reclaim](levels/BREACH_RECLAIM_RESULTS.md) | More +0.5R responses after current-session reclaims; mixed mean return and PF, no filter |
| 10-03 | [Q6/Q7: support proximity and overhead room](levels/PRICE_LEVELS_RESULTS.md) | No filter from previous-session primary or predefined neighbors; current-session/week sources retained separately |
| 10-02 | [RTL trend-conditioned RR](TREND_RR_RESULTS.md) | Primary mappings and annual selection fail to improve on fixed 1R; no forward test |
| 09-28/29 | [Entry filters and bar features](RESEARCH_RESULTS.md) | Only the red-run cap survives; location and other features don't |
| 09-29 | [MaxRedRun train/test](RESEARCH_RESULTS.md#next-steps) | Cap 3 passes out of sample; the effect is small |
| 09-30 | [Preceding candles Q1/Q2](PRECEDING_CANDLES_RESULTS.md) ([protocol](PRECEDING_CANDLES_PROTOCOL.md)) | No filter adopted; the periods disagree |
| 09-30 | [Exit estimate and data review](EXIT_AND_DATA_REVIEW.md) | First-touch exit worse; several data caveats |
| 09-30 | [Exit thresholds](EXIT_THRESHOLD_RESULTS.md) ([protocol](EXIT_THRESHOLD_PROTOCOL.md)) | Fixed TP worse; RR comparison distorted by the flatten bug |
| 09-30 | [RR 0.5–5.0 grid](RR_OPTIMIZATION_REVIEW.md) | Noisy curve; RR>1 gains were mostly multi-day holds |
| 10-01 | [Flatten fallback fix](FLATTEN_FALLBACK_RESULTS.md) | Bug fixed; baseline barely changes; RR still open |
| 10-01 | [Trailing stop after +1R](TRAILING_STOP_RESULTS.md) | Rejected at all distances; keep the bar-close exit |
| 10-01 | [Data rebuild](DATA_BUILD.md) | Clean NQ series from Databento source; old data was shifted 1 h in DST-mismatch weeks |
| 10-01 | [Early-close calendar](EARLY_CLOSE_CALENDAR_RESULTS.md) | No overnight holds left; on clean data 2.5R beats 1R in both periods |
| 10-01 | [RR 1.0 vs 2.0 / 2.5 / 3.0, clean data](RR_CLEAN_DATA_RESULTS.md) | Rule not met by $78 → RR stays 1.0; higher RR never meaningfully worse |
| 10-01 | [MaxRedRun train/test, clean data](MAXREDRUN_CLEAN_RESULTS.md) | Cap confirmed (PF up, DD down); cap 1 = safest, cap 3 = balanced |
| 10-02 | [Standalone buy-limit entry](LIMIT_ONLY_RESULTS.md) ([protocol](LIMIT_ONLY_PROTOCOL.md)) | Rejected: loses every 2016–19 year at every offset (incl. 80% / RR 2) |
| 10-02 | [Time of day](TIME_OF_DAY_RESULTS.md) | No block to switch off; every block profitable in both periods |
| 10-02 | [Q3: overlap vs staircase](Q3_OVERLAP_RESULTS.md) | No group loses in both periods; no filter |
| 10-02 | [Q4: pullback vs broader move](Q4_CONTEXT_RESULTS.md) | All groups profitable in both periods; no filter |
| 10-02 | [Q5: signal-candle shape](Q5_CANDLE_SHAPE_RESULTS.md) | Doji and full body each lose in one period only; no filter |
| 10-02 | [Near-stop averaging entry](AVERAGING_ENTRY_RESULTS.md) ([protocol](AVERAGING_ENTRY_PROTOCOL.md)) | Rejected in both models; also exposes material baseline execution sensitivity |
| 10-02 | [Standalone buy-limit entry](LIMIT_ONLY_RESULTS.md) ([protocol](LIMIT_ONLY_PROTOCOL.md)) | Positive recently, negative in every earlier year; no adoption; OHLC only |

## How we test

- Fix definitions and the selection rule **before** running. Keep negative results.
- Use one-minute OHLC for raw screening per the user's 2026-10-02 preference;
  document intraminute uncertainty without automatically launching generated ticks.
- Confirm any filter with a **full MT5 rerun**. Removing rows from a CSV misses the
  changed entries (a skipped trade frees the position for another one).
- Report **both** net $ and average net R, and say which one decides.
- Look for broad regions, not the best single grid step. Neighbouring steps differ by ±$4–5k from noise.
