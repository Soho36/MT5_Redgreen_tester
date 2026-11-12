# Native whipsaw replays and trading overlays

Specified 2026-11-12 before new native outcomes. Exploratory reused history.
The original ledger subsets and volatility-forecast results are already known.
No live changes. The user's intended use is an overlay on normal trading,
not necessarily skipping other sessions. Bounded and expanding examples have
been visually accepted as one family; the frozen primary rule remains broader.

## Fixed tests

Original NQ M30 event: three swings of 0.75 preceding-session ATR20. Reproduce
243 historical events, including 174 in 2016-September 2026. Verify old input
hashes. Eight native runs: RTL/GG each with control, day 1 at 1R, union of days
1-3 at 1R, and day 1 at 2R. 2R is one fixed secondary test, not optimization.
Keep all other inputs, one-MNQ size, early closes, flattening and Model=1.
2R retains the original bar-close exit mechanism; it is not a resting TP.

The gate uses the current submission session, not the previous signal candle's
date. Every permitted session follows a completed event session. Historical
bars, position management and flattening continue on disabled sessions.
Overlapping event windows are deduplicated; exposure never stacks above two
contracts in the sizing scenario. Days mean the original study's kept sessions.

Controls must reproduce published primary trades. Selected 1R runs must
reproduce the corresponding control subset (times, fills, exits and economics).
Native 2R replay is essential because altered exits can change later entries.
Preserve every run, input hash and output hash. Verify flat session boundaries.

## Overlay interpretation

Keep normal baseline trades. Evaluate one extra contract on day 1 and on
days 1-3 (two total). Separately replace baseline day-1 trades with native
day-1 2R trades, keeping normal trades on other sessions. With verified flat
boundaries, combine native session equity envelopes to compute intraday DD.
These sizing overlays assume identical fills and linear per-contract costs;
they are not fresh two-contract native runs or a liquidity-impact model.
Use $1.05 per round trip per contract and extra $2 cost sensitivity.

Report both eras and pooled: net dollars, R/trade, profit factor, intraday
equity DD, worst session, risk, concentration and extra-cost sensitivity.
Separate overlay profit from added risk. Compare incremental session PnL and
R using whole-month bootstrap intervals, 5,000 draws, seed 20261112.
Do not treat more dollars from more exposure as proof of improved selection.
Volatility-matched allocation remains a necessary attribution check; these
unconditional overlay intervals do not establish that advantage.

Measure following days 1, 2 and 3 separately. The old three-day aggregate was
not a test of multiple individually trending sessions. Deduplicate sessions
within each horizon; do not add horizon profits because they can overlap.
Disclose how many day-2/3 sessions are also day 1 after a newer whipsaw.
Report market movement and strategy economics separately; these are long-only
strategies and cannot automatically exploit a large downward move.

No winner is adopted live. Thresholds, targets and horizons stay fixed after
results. Native replay checks implementation on the same history; prospective
confirmation remains outstanding.
