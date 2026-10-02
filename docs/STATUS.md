# Project status

Updated 2026-10-03. **Start here.** Each study below links to the full evidence.
For the day-by-day history, see [JOURNAL.md](JOURNAL.md).

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
- Q8 support-reclaim filter ([results](BREACH_RECLAIM_RESULTS.md),
  [protocol](BREACH_RECLAIM_PROTOCOL.md)): current-session reclaims more often
  precede a +0.5R endpoint after 90 minutes (+6.1 / +3.1 percentage points), but
  mean price return and filled-trade PF do not improve across both periods.
  A post-hoc check shows the recent excess is two-sided dispersion (-0.5R tail
  also rises); only 2016-19 hints at upward bias. No strategy filter adopted.
- Q6/Q7 first price-level screen ([results](PRICE_LEVELS_RESULTS.md),
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
   mostly wider dispersion (both tails), no stable RTL filter. Resistance paths, level history and role reversal
   remain proposed in that checklist.
2. Execution sensitivity remains unresolved; do not equate OHLC screening
   profits with verified fills. Further tick-generation runs are not planned.
3. Sizing: at the real cost ($1.05/contract), "fixed $200 risk, max 5 contracts" beats
   1 contract on net/DD in 2020–26 but not in 2015–19. Sizing does not change the RR
   answer. Keep 1 contract for research; decide live sizing at the end.

## Study index

| Date | Study | Verdict |
|---|---|---|
| 10-03 | [Q8: support breach and reclaim](BREACH_RECLAIM_RESULTS.md) | More +0.5R responses after current-session reclaims; mixed mean return and PF, no filter |
| 10-03 | [Q6/Q7: support proximity and overhead room](PRICE_LEVELS_RESULTS.md) | No filter from previous-session primary or predefined neighbors; current-session/week sources retained separately |
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
