# The RTL strategy itself

Studies of the base strategy, not of a price pattern at a level: red M30
candle, buy stop at its high, stop at its low, bar-close exit at 1R, session
flatten. The current rules are in [STATUS.md](../STATUS.md).
[All docs](../README.md).

| Study | Answer |
|---|---|
| [RTL downtrend crystal ball](rtl-downtrend-oracle/RESULTS.md) ([protocol](rtl-downtrend-oracle/PROTOCOL.md)) | Perfect hindsight downtrend skipping adds 36-202% profit, but the gain vanishes 2-3 sessions late for small drops and by 3 sessions in 2016-19 at every size; the live zigzag loses 10-82%. Downtrend filters not worth pursuing. Independently verified |
| [RTL profit location within chop/wick episodes](rtl-price-structure/EPISODE_RESULTS.md) ([protocol](rtl-price-structure/EPISODE_PROTOCOL.md)) | Contained paths lose and upper excursions win, but unflagged trades split the same way (post-hoc control), so this is not chop-specific. Entries commonly precede flag clearance; no timing rule supported. Independently verified; MA agreement remains a separate proposal |
| [RTL daily/M30 price structure](rtl-price-structure/RESULTS.md) ([protocol](rtl-price-structure/PROTOCOL.md)) | No filter: M30 overlap/chop and wick/overlap subsets profitable in both eras. Daily omission has a modest historical risk tradeoff but unstable sensitivity; all four plan points completed and independently verified |
| [RTL unfavorable periods](rtl-market-regimes/RESULTS.md) ([plan](rtl-market-regimes/PLAN.md), [protocol](rtl-market-regimes/PROTOCOL.md)) | Six daily trend x volatility groups all positive in dollars in both eras; no skip candidate. Cost/R and dollar risk vary; smaller groups remain inconclusive |
| [H1 versus M30, RTL and GG](timeframe-h1/RESULTS.md) | No run cap, RR 0.5/1: H1 cuts recent trades 44–47%; RR 0.5 earns more, RR 1 less. GG H1/RR 1 has 50% higher DD; no baseline change |
| [Q1/Q2: preceding candles](q01-q02-preceding-candles/RESULTS.md) ([protocol](q01-q02-preceding-candles/PROTOCOL.md)) | No filter; keep MaxRedRun = 3, MinLocation = 0 |
| [Q3: overlapping vs steady bars](q03-overlap/RESULTS.md) | No filter |
| [Q4: pullback vs broader move](q04-context/RESULTS.md) | No filter |
| [Q5: signal-candle shape](q05-candle-shape/RESULTS.md) | No filter (doji / full body flip between periods) |
| [Time of day](time-of-day/RESULTS.md) | Every session block profitable in both periods; windows unchanged |
| [MaxRedRun on clean data](maxredrun/RESULTS.md) | Cap 1 wins the train/test on PF and DD but costs 23% net; the user kept cap 3. Extended to 2026-10-01 (2026-10-13): cap 3 no longer lowers drawdown and earns 5.7% less than off; **cap dropped, baseline is no cap** |
| [RR 0.5-5.0 optimization review](rr-optimization/RESULTS.md) | 2.5R the best profit/drawdown candidate in that sample |
| [RR on clean data](rr-clean-data/RESULTS.md) | 2.0 / 2.5 / 3.0 do not all beat 1.0; RR stays 1.0 |
| [Exit threshold](exit-threshold/RESULTS.md) ([protocol](exit-threshold/PROTOCOL.md)) | Keep the 1R bar-close exit |
| [Trailing stop after +1R](trailing-stop/RESULTS.md) | Rejected |
| [Break-even stop after +1R](breakeven-stop/RESULTS.md) ([protocol](breakeven-stop/PROTOCOL.md)) | Rejected: worse on net $ and average R in both periods; the trades it cuts are worth about zero in the baseline |
| [Trade paths: what price does between entry and exit](trade-paths/RESULTS.md) | Descriptive. Per 100 trades: 50 never touch +1R (44 stop), 33 touch it and never come back (all win), 16 come back to entry (10 stop, 6 win). Holding is slightly positive at every level; no place to cut or bank early |
| [Flatten fallback](flatten-fallback/RESULTS.md) | Fix adopted: always flat at session end |
| [Early-close calendar](early-close-calendar/RESULTS.md) | Adopted: no cross-date trades |
| [Near-stop averaging entry](averaging-entry/RESULTS.md) ([protocol](averaging-entry/PROTOCOL.md)) | Keep averaging off |
| [Limit-only entry](limit-only/RESULTS.md) ([protocol](limit-only/PROTOCOL.md)) | Rejected |
| [Trend-conditioned RR](trend-rr/RESULTS.md) ([protocol](trend-rr/PROTOCOL.md)) | Keep fixed 1R |
| [Green outside long](gg-outside/RESULTS.md), [green outside short](gg-outside/SHORT_RESULTS.md), [red breakdown versus new-high short](gg-outside/RED_BREAKDOWN_RESULTS.md), [strict red outside short](gg-outside/RED_SHORT_RESULTS.md) | Both red-candle short definitions lose in all 12 settings in both periods; the marked chart does not need a new high. The green-candle short is separate. No rule adopted |
| [Signal colour + no-pattern control](signal-colour/RESULTS.md) | Edge is the buy stop over a previous high, not the colour (green ≈ red). Buy-stop gain over a plain long: NQ +0.08 R, ES +0.04 R; ES fails because its plain long loses. GG run cap (2026-10-13): none passes, GG runs with no cap; RTL + GG equity chart |
| [Why ES differs from NQ](nq-vs-es/RESULTS.md) | Earlier coarsening suggests resolution sensitivity; fixed-grid follow-up below strengthens it. Full ES attribution remains open |
| [NQ resolution: fixed grids and every origin](granularity/RESULTS.md) ([protocol](granularity/PROTOCOL.md)) | All 30 runs complete: wider grids progressively reduce RTL minus control in every era/origin; 2020–26 +0.078 → +0.004 R. Control ledgers audited; no new filter |
| [NQ / coarse NQ / ES: complete paths](path-interaction/RESULTS.md) ([protocol](path-interaction/PROTOCOL.md)) | 180,130 paths: recent broad effective-step comparison finds lower +1R reach / more stop-first on ES, similar post-touch close retention; three-way overlap and tick-size matching limit attribution |
| [ES minimum 50-tick candle width](es-minimum-width/RESULTS.md) ([protocol](es-minimum-width/PROTOCOL.md)) | Full EA reruns: recent RTL gross/net expectancy remains negative; fewer trades lower costs, earlier positive result has only 91 trades. No filter adopted |
| [Tighter stop, scaled target](stop-fraction/RESULTS.md) | Stop at 0.75 / 0.5 x candle with the 1R target scaled: worse net R in 16–17 of 17 years on NQ and YM; NQ 2020–26 $38.4k → $19.3k / $13.7k. Rejected |
| [RTY (Russell 2000): the YM experiments](rty-unseen-instrument/RESULTS.md) | Like YM: RTL gross +0.019 / +0.025 R (2018–19 / 2020–26), lost to costs on M2K; shorts lose; buy-stop gain +0.050 / +0.040 R; H1 2020–26 +$3.1k |
| [YM (Dow): four baselines vs NQ and ES](ym-unseen-instrument/RESULTS.md) | Longs keep a small gross edge (RTL +0.036 / +0.056 / +0.014 R, 2010–15 / 2016–19 / 2020–26), lost to costs on MYM; both shorts lose. Buy-stop gain over a plain long transfers (+0.080 / +0.057 / +0.032 R), YM's plain long slightly negative. Does not confirm NQ in money |
| [MES: unseen instrument](mes-unseen-instrument/RESULTS.md) | No edge on MES even before costs (mean R −0.04 / +0.00 vs MNQ +0.09 / +0.09) |
| [Q24: trade-result streaks](q24-trade-streaks/RESULTS.md) ([protocol](q24-trade-streaks/PROTOCOL.md)) | No predictive or daily-stop rule passes |
