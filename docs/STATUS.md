# Project status

Updated 2026-10-26. **Start here.** All study docs are mapped by setup type in [README.md](README.md). Each study below links to the full evidence.
For the day-by-day history, see [JOURNAL.md](JOURNAL.md).

**[RTL session VWAP](baseline/rtl-vwap/RESULTS.md) (2026-10-26, exploratory): far-below signals warrant a risk-management replay; no filter adopted.** Four fixed questions, 16,668 trades, full-session HLC3 VWAP plus close-price/cash-anchor sensitivities. Skipping close < VWAP - A20 changes net/DD from $4,417/$2,143 to $3,939/$932 early, and $38,400/$5,781 to $43,435/$3,084 recently. Both beat same-holding static exposure; close-price and roll-clean patterns agree. Strict negative-edge screen fails because skipped early dollars are positive. Recent DD duration worsens 283 -> 392 days, cash-anchor evidence is weaker, and retained planned risk is only 61% versus 72% holding. Repeated crossings remain profitable; reclaims are too rare. All raw features/trades/economics/controls independently verified; 13 tests pass. [Full replay proposal](baseline/rtl-vwap/REPLAY_PROPOSAL.md) saved, not executed.

**[Drawdown research synthesis](baseline/rtl-market-regimes/SYNTHESIS.md) (2026-10-25):** accepting manageable drawdowns currently has stronger support than the tested timing filters. This is not proof all filters are exhausted or recovery is guaranteed. Preserve the warning-rule risk hint, distinguish exposure reduction from prediction, and assess account-level survivability and forward execution before deployment. Baseline unchanged.

**[RTL M30 MA agreement](baseline/rtl-ma-agreement/RESULTS.md) (2026-10-25, exploratory): no filter adopted.** Seven SMA lengths, five-of-seven primary agreement, pre-2016 flat bands and four fixed sensitivities. Primary up/down/mixed net $: -901/+2,744/+2,574 early; +13,051/+9,611/+15,738 recent. Skip mixed, skip down and only-up all reduce profit in both eras under every variant. Recent skip-down lowers profit 25% and daily-close DD 32.5%; its modest same-holding advantage does not repeat early and does not equalize dollar risk. Many profitable trades are already open when up-consensus returns; the future-timing split does not establish a live entry rule. Independently verified all 83,340 labelled rows, 159 summaries, 90 policy rows, bootstrap/placement outputs; 18 tests pass. [Plan](baseline/rtl-market-regimes/PLAN.md#ma-agreement-follow-up-authorized-2026-10-24-resumed-2026-10-25) complete; no full replay triggered.

**[RTL weekly signal gate](baseline/rtl-weekly-gate/RESULTS.md) (2026-10-25, exploratory): switching off on weekly sells cuts profit by 52-85%.** User's idea: stop new M30 RTL trades when a week breaks below a green prior week's low, resume when a week breaks above a red prior week's high. Off 33-45% of the time; primary (intraweek touch): $4,417 -> $650 (2016-19), $38,400 -> $16,548 (2020-26). Every sensitivity (week-close timing, close-confirmed, unadjusted prices) loses 52-85%. Skipped trades are better than kept ones in 7 of 8 cases (2020-26: +0.061 vs +0.037 R); no drawdown benefit. Weekly sell periods hold many of RTL's best dip-buying stretches, and both signals arrive late. Verifier 9/9, 9 tests pass. [Protocol](baseline/rtl-weekly-gate/PROTOCOL.md). No gate adopted.

**[RTL warning-based skip rules](baseline/rtl-warning-rules/RESULTS.md) (2026-10-25, exploratory): nothing beats trading every session; daily downtrend filtering looks exhausted for RTL on NQ.** Rule A (stop after a top-10% 5-session rise, resume on a bounce warning or after 20 sessions): +7% / -51% (2016-19 / 2020-26), sitting out 37-47% of sessions; all 18 variants lose 40-51% recently. Rule B (live-zigzag stop, bounce-warning resume): repairs most of the plain zigzag's damage (2%: -22% / -15% versus -82% / -42%) but still loses at 2-3%; at 5% it barely skips (+6% / +0%). No primary rule beats random time off; all "not promising". Rule B at 2% has a better profit-to-drawdown ratio (risk hint only). Verifier 7/7, 9 tests pass. [Protocol](baseline/rtl-warning-rules/PROTOCOL.md). No gate adopted.

**[Pullback and bounce warnings](baseline/rtl-pullback-stats/RESULTS.md) (2026-10-25, price statistics): "down a lot" finds lows, "up a lot" barely finds peaks.** Signals = top/bottom 10% of 5/10/20-session moves (plain and volatility-scaled, cutoffs from pre-2016); a hit = a 2/3/5% zigzag turn within 2 sessions. Bounce warnings: low within 2 sessions 21-53% of the time, 1.8-4.9x the volatility-matched base, all predictors/sizes/eras/sensitivities; still 1.25-2.1x versus simply knowing a fall is confirmed (post-hoc). Pullback warnings: 6-38% hits, 17-84% false alarms; only the 5-session rise for 5% drops passes. Rallies do not get tired: older rallies are less likely to end soon. Fixed rule: RTL test worth designing for 5% drops only. Verifier 10/10, 7 tests pass. [Protocol](baseline/rtl-pullback-stats/PROTOCOL.md). No gate adopted.

**[RTL downtrend crystal ball, early signals](baseline/rtl-downtrend-oracle/EARLY_RESULTS.md) (2026-10-25, exploratory): early costs far less than late; a pullback statistic is worth building.** Stop and resume both two sessions early still add +20% to +59% at every size and era (two late: -9% to +28%); with the resume exactly at the low, stopping up to five sessions early adds +8% to +130%. Fixed rule passes; raw closes agree. Caveats: the resume matters more than the stop (late resumes give up the rebound, the costliest window in dollars); in 2020-26 the early advantage is mostly in dollars, not R per trade; false alarms are not in the ceiling. Independent verification 7/7, 15 tests pass. [Addendum](baseline/rtl-downtrend-oracle/EARLY_PROTOCOL.md). No gate adopted.

**[RTL downtrend crystal ball](baseline/rtl-downtrend-oracle/RESULTS.md) (2026-10-24, exploratory): late, confirmation-based downtrend filters not worth pursuing (early warnings: see the addendum above).** Hindsight zigzag downtrends of 2/3/5/10% on daily closes; skip RTL from peak to trough, then the same signals 1-20 sessions late. On time, net profit would rise 36-202% (2016-19 / 2020-September 2026). One session late cuts the gain by half or more; break-even is 2-3 sessions late for 2-3% drops and fails by 3 sessions in 2016-19 at every size. The live zigzag (no hindsight) reacts 2-21 sessions late and cuts profit 10-82% at every size and era, usually worse than random time off. Fixed decision rule: no size passes at 3+ sessions late in both eras; raw closes agree. Independent verification 12/12, 10 tests pass. [Protocol](baseline/rtl-downtrend-oracle/PROTOCOL.md). No gate adopted.

**[RTL profits within flagged episodes](baseline/rtl-price-structure/EPISODE_RESULTS.md) (2026-10-24, descriptive): blanket chop avoidance removes useful upward moves.** Broad M30 wick/overlap, 20 bars, 2020-September 2026: contained trades net -$26,777; upper excursions +$37,677; total +$10,900. Those path signs repeat across all 18 M30 flag/window/era combinations, and a post-hoc control shows unflagged trades split the same way, so the split describes RTL trades generally, not chop. About 95% of recent winning dollars enter while the original wick flag remains active, so waiting for it to clear would miss most of them. After-clearance exits and late-in-hindsight submissions look better, but a winning move itself tends to clear the flag; causal episode age does not repeat between eras. No timing rule is supported. All 23,569 overlapping attribution rows, episode inventories and 678 summaries independently verified; 16 tests pass. [Plan](baseline/rtl-market-regimes/PLAN.md#profit-location-within-flagged-episodes-2026-10-24) completed for this attribution; MA agreement saved as a separate, untested proposal. No gate adopted.

**[RTL daily/M30 price structure](baseline/rtl-price-structure/RESULTS.md) (2026-10-24, exploratory): no filter adopted.** All four points of the [follow-up plan](baseline/rtl-market-regimes/PLAN.md#price-structure-follow-up-2026-10-24) complete. Fixed pre-2016 cutoffs, 20 bars with 10/40 sensitivities. M30 low-efficiency/high-overlap earns $1,071 / $9,089; high-wick/high-overlap earns $1,135 / $10,900 in 2016-19 / 2020-September 2026. Skipping these sacrifices profit; recent closed-trade drawdown rises. Daily omission retains 97% of recent profit and cuts daily-close DD 14%, but sensitivity/uncertainty and placement controls do not establish a stable filter. All 16,668 study trades, six feature panels, 584 outcome/coverage rows, bootstrap and placement controls independently verified; 12 tests pass. Tested wick dominance is a rolling average, not an exhaustive test of extreme visual patterns.

**[RTL daily trend x volatility](baseline/rtl-market-regimes/RESULTS.md) (2026-10-23, exploratory): no skip condition qualifies.** [Saved plan](baseline/rtl-market-regimes/PLAN.md), steps 1-5 complete. All six primary groups make positive net dollars in 2016-19 and 2020-September 2026; four smaller groups lack independent-week coverage. Mean planned risk rises $21.72 -> $78.95, while mean commission/R falls 0.095 -> 0.024. All 25,833 source trades and 16,668 primary trades independently verified; 16 tests pass. The incomplete Oct1 end-of-test trade is excluded. No gate adopted; conditional replay stages not triggered.

**[Tighter stop with a scaled target](baseline/stop-fraction/RESULTS.md) (2026-10-23, exploratory): rejected.** Stop at entry − 0.75 / 0.5 × candle, 1R target scaled with it, on NQ and YM (k = 1 reproduces the baseline). Gross R the same or lower (NQ 2020–26 +0.072 → +0.052 / +0.064), costs per R up, win rate 43% → 40% / 36%; net R per dollar risked worse in 16–17 of 17 years on both. NQ 2020–26 at one contract $38.4k → $19.3k / $13.7k.

**[The YM experiments on RTY (Russell 2000)](baseline/rty-unseen-instrument/RESULTS.md) (2026-10-23, descriptive): RTY behaves like YM.** CME RTY exists from 2017-07 only; symbol `M2KcontDTBNT20172026` ($0.50 per 0.1 tick, as MNQ/MYM). RTL gross R 2018–19 / 2020–26: RTY +0.019 / +0.025 (NQ +0.103 / +0.072, YM +0.082 / +0.014, ES +0.004 / −0.006). Net 2020–26: RTL −$3.5k, GG −$11.2k, both shorts about −$11–13k. Buy-stop gain over a plain long +0.050 / +0.040 R (intervals above 0); plain long −0.031 / −0.015. RTL H1 2020–26 +$3.1k PF 1.029. Across NQ/ES/YM/RTY (2018–26) the buy-stop gain is +0.04 R on the three others and +0.07 on NQ; only NQ's plain long is not negative.

**[Four baselines on YM (Dow)](baseline/ym-unseen-instrument/RESULTS.md) (2026-10-23, descriptive): a second unseen instrument does not confirm NQ.** Same EAs and settings on NQ, ES (re-imported as `MEScontDTBNT20102026_2`) and YM (`MYMcontDTBNT20102026`, $0.50/pt). Gross R per trade, RTL 2010–15 / 2016–19 / 2020–26: YM +0.036 / +0.056 / +0.014, NQ +0.006 / +0.081 / +0.072, ES −0.118 / −0.040 / −0.006; GG on YM +0.013 / +0.046 / +0.005. After $1.05 (0.06 R on MYM) 2020–26 loses: RTL −$2.5k PF 0.987, GG −$5.7k PF 0.971. RTL-short and GG-short lose on all three instruments in every period (YM 2020–26 −$15.8k / −$18.7k). **Plain-long control (audited):** the buy stop beats a market buy on YM by +0.080 / +0.057 / +0.032 R (intervals above 0, 15/17 years; NQ +0.041 / +0.072 / +0.064, ES +0.029 / +0.042 / +0.035); YM's plain long is slightly negative (−0.044 / −0.001 / −0.018). Recent YM weakness is mostly a smaller gain, about zero in 2025–26. **Ticks / H1:** MYM and MNQ pay the same $0.50 per tick, so commission in R is set by ticks per candle (YM M30 ~35 vs NQ ~74); gross edge does not grow with ticks above ~20 and is lower than NQ's at equal ticks. RTL H1 (correct cutoff) on YM: 2020–26 gross +0.028 R, net +$6.1k PF 1.048 (M30 −$2.5k); all years +$5.4k, 6/17 years positive. Selected after the user's hand runs.

**[MT5 versus prop fills tool and server clock](JOURNAL.md#2026-10-21-mt5-backtest-versus-prop-fills-tool) (2026-10-21, tooling):** `python/compare_mt5_nt8.py` pairs MT5 tester trades with prop fills from NT8's database (both clocks UTC). AMP's live `MNQZ26` runs on UTC, the research symbols on Chicago + 8 h, so both runband EAs got `ServerClock` (Auto: custom symbol = session clock, broker symbol = UTC with US-DST shift). Research ledgers reproduce exactly; on `MNQZ26` the EAs now flatten at 20:30 UTC.

**[Red breakdown versus new-high outside short](baseline/gg-outside/RED_BREAKDOWN_RESULTS.md) (2026-10-21, exploratory):** the marked red candle needs a new n-bar low and enlarged full range; a new high is optional. All 12 no-new-high settings lose net dollars in 2016–19 and 2020–26. At n=3/r=1.25, recent net/PF is −$6,192/0.965 without the new high versus −$10,635/0.774 with it. Both isolated MT5 EAs are available for manual tests; no short rule adopted.

**[Red outside-bar short correction](baseline/gg-outside/RED_SHORT_RESULTS.md) (2026-10-21, exploratory):** the signal is a *red* outside M30 candle; sell stop at its low, stop at its high. All 12 filtered settings lose net money in 2016–19 and 2020–26. Strict n=3: −$1,099 / −$10,252, PF 0.839 / 0.787; the earlier positive short screen used a *green* outside candle. No red-short rule adopted. `GG_red_outside_short` is available for manual MT5 tests with the filter enabled by default.

**[GG outside-bar short mirror](baseline/gg-outside/SHORT_RESULTS.md) (2026-10-20, exploratory):** 12 short-side MT5 filters plus a green-candle short control. Strict n=3 sells below the outside low: 2020–26 +$2,530, PF 1.169 on 190 fills, but 2016–19 −$236, PF 0.882; 2022 accounts for 90% of recent profit and nearby size settings weaken. No short rule adopted. The manually testable `GG_outside_short` EA has `UseOutsideFilter=true` by default.

**[GG full-range outside-bar screen](baseline/gg-outside/RESULTS.md) (2026-10-20, exploratory):** 12 GG-only filtered MT5 runs over n=1/3/5/10 and three size settings. The filter-off control reproduces all 17,570 GG trades. Strict n=1 stays profitable but lowers 2020–26 PF to 1.058 from 1.083; all n=3 settings lose in 2020–26. No GG filter adopted.

**[H1 versus M30, RTL and GG](baseline/timeframe-h1/RESULTS.md) (2026-10-15, exploratory):** eight matched uncapped MT5 runs at RR 0.5/1. H1 cuts recent trades 44–47%. At RR 0.5, H1 earns more in both eras, but recent DD rises 10% (RTL) / 42% (GG). At RR 1, recent net falls 27% / 50%; GG DD rises 50%. M30/RR 1 still earns more recent dollars than either H1 variant. H1 research copies enforce the existing half-hour session cutoff on ticks; all ledger/session audits pass. No baseline change.

**[MaxRedRun on the test extended to 2026-10-01](baseline/maxredrun/RESULTS.md#extended-test-to-2026-10-01-2026-10-13)
(2026-10-13): the red-run cap is dropped. The baseline is now `MaxRedRun = 0` (no cap), user decision.** The original
test stopped at 2026-07-14 although the symbol holds data to 2026-10-01. Extended (net of $1.05): off $38,534, PF 1.091,
DD 5,781; cap 3 $36,322, PF 1.097, DD 5,980; cap 1 (the frozen winner) $29,830, PF 1.125, DD 4,036, still passing. Cap 3
minus off is −$2,212 with an interval of −11,006 to +6,678, so in dollars the two cannot be told apart; per trade the
cap still adds +0.012 R. It helped in 2020–23 and cost money in 2024–26. The 58 new days alone decide nothing.
**Every study dated before 2026-10-13 used cap 3 as its baseline.** They are not rerun: the cap moves results by a few
percent. New studies use no cap.

**[ES minimum 50-tick candle width](baseline/es-minimum-width/RESULTS.md) (2026-10-11, exploratory): does not pass.**
Four full EA reruns use the built-in filter (MinCandleRange = 1250 quote points = 12.5 price points). Recent RTL gross
R falls +0.0018 -> -0.0207, net R improves slightly -0.0418 -> -0.0322 as costs fall; the improvement interval spans zero.
2016-19 is positive but has only 91 trades. Recent trades fall 9,623 -> 1,479; changed order lifetimes alter the entries.
Both baselines reproduce earlier ledgers; 69,422 complete paths audited. No filter adopted and no causal ES attribution.

**[Break-even stop after +1R](baseline/breakeven-stop/RESULTS.md) (2026-10-10, exploratory): rejected.** Baseline unchanged,
stop moved to the entry price once price touches +1R: net $6,485 → $5,404 / $37,981 → $33,727 (2016–19 / 2020–26), average
net R −0.004 → −0.009 / +0.060 → +0.053; 3/11 years better. Differences are within noise, DD is 5–11% lower. The trades it
cuts (touched +1R, came back to entry) are worth about zero in the baseline: 60% stop out, 39% recover to about +1.6R.

**[Baseline trade paths](baseline/trade-paths/RESULTS.md) (2026-10-10, descriptive):** every baseline trade followed quote by
quote. Per 100 trades (2016–26, both periods alike): 50 never touch +1R (44 stop, 6 closed at session end); 33 touch +1R and
never come back to entry (all win); 16 come back to entry (10 stop, 6 win). 45% of losers had been above +0.5R; 60% of winners
had been below −0.25R. At every level from −0.75R to +3R, holding on was worth slightly more than getting out there (mostly
+0.03 to +0.09R), and a trade back at entry is worth about the same whatever it did before. No rule tested; nothing to adopt.

**ES data for unseen-instrument tests (2026-10-08):** continuous ES 1-minute file built with the NQ rules
(`F:\DATABENTO\ES_16_YEARS\MT5_ES_continuous_2010-2026_ohlcv-1m.csv`, 2010-06-07 → 2026-10-07), input checks clean
([DATA_BUILD](reference/DATA_BUILD.md#es-build-2026-10-08)). Do not use the old ES conversion: 3 days hold spread prices.
Two ES-only data holes (2020-02-28, 2020-06-30). Imported as `MEScontDTBNT20102026`.

**[Baseline on MES](baseline/mes-unseen-instrument/RESULTS.md) (2026-10-08): the RTL edge does not transfer.** Unchanged
baseline EA and settings: MES mean R before costs −0.039 / +0.002 (2016–19 / 2020–26) vs MNQ +0.093 / +0.085, 95%
intervals apart. PF net 0.930 / 0.979; 15/17 years lose. The gap already exists before costs; its mechanism remains
unresolved (win rate 2–4 points lower). Treat MNQ results as unconfirmed on independent data.

**[Signal colour + control](baseline/signal-colour/RESULTS.md) (2026-10-08, exploratory): the edge is the buy stop, not the
colour or drift.** On MNQ a market-buy control with the same stop and exit earns ~0 R before costs (+0.009 / +0.007, audited). Green
signals nearly match red (no cap on either: +0.071 / +0.070 vs +0.081 / +0.071 R). RTL + GG together = ~2x net and ~2x DD
([equity chart](figures/rtl_gg_equity.png)). **GG run cap (2026-10-13): none passes, GG runs with no cap.** The RTL
train/test rule applied to green picks cap 5, which is worse than off on 2020–26 (net PF 1.082 vs 1.088, net $36.2k vs
$39.2k); the earlier GG figures used RTL's cap 3 untested. Both with no cap (the baseline since 2026-10-13), 2020–26:
$78.1k net, $9.1k DD on daily closes. At equal size the mix is only slightly smoother (daily swings 9% smaller,
worst month $2.2k vs $3.6k / $2.9k; inside the noise, nothing in 2016–19). In one account it needs two contracts 71% of
the time; split across several one-contract accounts it costs nothing. GG EA:
`mt5/experts/GG_r_MFE_buy-stop-entry_runband.cs`. **Same control on MES:** the buy stop beats the plain long there too,
by +0.029 / +0.044 / +0.042 R (2010–15 / 2016–19 / 2020–26, audited, all intervals above 0), about half the NQ gain. But the
MES plain long itself loses −0.15 / −0.08 / −0.04 R (NQ ≈ 0), so RTL fails there. The market's background decides.

**[Why ES differs](baseline/nq-vs-es/RESULTS.md) (2026-10-08, exploratory): resolution sensitivity, attribution open.**
Artificially coarsened NQ loses RTL performance: MT5 gross R -0.123 / +0.020 / +0.041 (2010-15 / 2016-19 / 2020-26)
versus native NQ +0.005 / +0.093 / +0.085. Coarsening changes signals, entries, stops and targets together. This establishes
sensitivity to the data grid; it does not establish that fewer candle ticks primarily cause ES's weakness. ES's negative
plain-long control remains a separate difference.

**[NQ fixed-grid resolution](baseline/granularity/RESULTS.md) (2026-10-09, exploratory):** all 30 runs, every grid origin:
wider price grids progressively reduce RTL minus control (2020-26 +0.078 -> +0.004 R). Ordered by steps per candle, the
NQ periods line up on roughly one curve (near 0 at ~15 steps, +0.06 to +0.09 R from ~30). This descriptive alignment
strengthens the resolution hypothesis without isolating its mechanism. No cutoff or filter adopted. Logger fix:
market-entry controls omit fast stops; all 2026-10-08 ledgers re-audited (<= 0.005 R change).

**[Complete paths: NQ / coarse NQ / ES](baseline/path-interaction/RESULTS.md) (2026-10-09, exploratory):** recent broad
effective-step comparisons find lower ES +1R reach and more stop-first paths, with similar close retention after +1R.
The plain-long gap versus coarse NQ is concentrated in smaller candles in that comparison. Three-instrument overlap is
limited and native-tick matching changes the population and several conclusions; these are associations, not a resolved
ES mechanism. The subsequent full minimum-width test above does not produce positive recent ES RTL expectancy.

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
| Filter | None since 2026-10-13: `MaxRedRun = 0` (no cap; it was 3 until then), `MinLocation = 0` (off) |
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

**Current baseline, no cap** (one-minute OHLC, calendar on, net of $1.05, 1 contract, RR 1.0):

| Period | Trades | Net $ | Net PF | Net DD $ | Avg net R |
|---|---:|---:|---:|---:|---:|
| 2020-01-02 → 2026-10-01 | 10,502 | 38,534 | 1.091 | 5,781 | +0.048 |
| 2020-01-02 → 2026-07-13 | 10,165 | 38,890 | 1.097 | 5,781 | +0.047 |
| 2016-01-01 → 2019-12-31 | 6,167 | 4,417 | 1.064 | 2,176 | −0.014 |

**Earlier OHLC results with `MaxRedRun = 3`** (rebuilt data, calendar on, net of $1 commission, 1 contract):

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
- **No red-run cap (`MaxRedRun = 0`), decided 2026-10-13.** History: cap 3 was chosen on 2015–19 by a pre-set
  rule and tested frozen on 2020–26 (PF up in 6 of 7 years, DD −17%, profit flat). On clean data
  ([check](baseline/maxredrun/RESULTS.md)) training picked cap 1 (PF +0.036, DD −30%, profit −23%) and the user
  kept cap 3 as the balanced choice (DD −16%, profit −2%) on 2026-10-01. On the test extended to 2026-10-01, cap 3
  no longer lowers drawdown (5,980 vs 5,781 for off) and earns 5.7% less, so the user dropped it. Cap 1 still
  passes and stays the conservative alternative. Per trade the cap still adds about +0.012 R, so look at it
  again if sizing ever moves from a fixed contract count to a fixed dollar risk.
- `FlattenFallback` fix (bug: positions were held up to 6.5 days).
- Rebuilt data (`MNQcontDTBNT20102026`) and the early-close calendar: no trade crosses
  a session any more. Results match the old data closely, so earlier entry findings stand.
- **RR = 1.0** (2026-10-01). On clean data, 2.0–3.0 didn't beat 1.0 in both periods by the
  pre-set rule ([check](baseline/rr-clean-data/RESULTS.md)). Revisit only with a new reason, e.g.
  measured live slippage.

**Rejected** (evidence kept, don't retest without a new reason)
- ES minimum 50-tick candle width ([results](baseline/es-minimum-width/RESULTS.md), 2026-10-11): full rerun remains
  negative before and after costs in 2020-26; earlier positive sample has only 91 trades. No ES filter adopted.
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
- Break-even stop: stop moved to the entry price once price touches +1R, bar-close exit kept
  ([results](baseline/breakeven-stop/RESULTS.md), 2026-10-10). Worse on net $ and average net R in both
  periods (within noise); DD 5–11% lower for 11–17% less profit. Don't retry other trigger levels.
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
| 10-13 | [MaxRedRun, test extended to 2026-10-01](baseline/maxredrun/RESULTS.md#extended-test-to-2026-10-01-2026-10-13) | Cap 3 no longer lowers drawdown and earns 5.7% less; cap dropped, baseline is no cap |
| 10-13 | [GG run cap and RTL + GG equity](baseline/signal-colour/RESULTS.md#gg-run-cap-and-the-combined-equity-curve-2026-10-13) | No cap passes for GG; red and green earn about the same; together = twice the size |
| 10-11 | [ES minimum candle width](baseline/es-minimum-width/RESULTS.md) ([protocol](baseline/es-minimum-width/PROTOCOL.md)) | 50-tick rule fails: recent RTL gross/net negative, paired net improvement uncertain; earlier 91 trades; no adoption |
| 10-10 | [Baseline trade paths](baseline/trade-paths/RESULTS.md) | Descriptive: path tree, where losers and winners had been, level map. Holding is slightly positive at every level; no early cut or take-profit point |
| 10-10 | [Break-even stop after +1R](baseline/breakeven-stop/RESULTS.md) ([protocol](baseline/breakeven-stop/PROTOCOL.md)) | Rejected: worse on net $ and average R in both periods; cut trades are worth about zero in the baseline |
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
