# Break-even stop after +1R: protocol

2026-10-10 · Exploratory (user request) · Fixed before any run · [Baseline studies](../README.md)

## Question

Everything in the RTL baseline stays the same. Once price reaches +1R, move the stop loss to the entry
price (break-even). The exit is still the bar-close exit at ≥ 1R. Does that improve the baseline?

## Rule tested

Baseline unchanged: red M30 candle, buy stop at its high, stop at its low, market exit after the first
bar that closes ≥ entry + 1.0R, flatten at 23:30 with fallback and early-close calendar, `MaxRedRun = 3`,
1 contract.

One addition, checked on every tick (`BreakevenAtR = 1.0`):

- The first time bid ≥ entry + 1.0 × R, the stop is moved **once** to the entry price.
- It does not trail after that. `BreakevenAtR = 0` switches it off (the baseline).

Which trades can change: only those that touch +1R inside a bar, do **not** close a bar at ≥ +1R, and
then fall back to the entry price. The baseline keeps holding them; they end as a full loss, a later
≥ 1R close, or a session flatten. The variant exits them at about zero. Exiting earlier also frees the
position, so some new trades appear and a few baseline trades disappear.

## Runs

Two full MT5 runs on `MNQcontDTBNT20102026_2`, M30, 1-minute OHLC, 2010-06-07 → 2026-07-14:

| Run | `BreakevenAtR` |
|---|---|
| Control | 0 |
| Break-even | 1.0 |

The EA is the baseline runband EA with text edits from `python/prepare_breakeven_study.py`. The control
must reproduce the saved baseline ledger (`Reports/instrument_baseline_20261008`) field by field. Both
ledgers are audited against MT5's own order/deal report.

## Measures

- Costs $1.05 per trade. R = profit ÷ (candle range × $2).
- Periods: **2016–19** and **2020–26** decide. 2010–15 is shown for context only (different market hours).

## Decision rule

Same rule as the [trailing-stop study](../trailing-stop/RESULTS.md): the break-even stop becomes a
candidate only if it beats the control on **both** net $ **and** average net R in **both** deciding
periods. Otherwise it is recorded as rejected. No other trigger level (0.5R, 1.5R …) or stop offset
(entry + x) will be tried in response to the results.

Reported without a gate: PF, drawdown, yearly count, a paired breakdown of the trades that changed,
a week-resampled interval for the difference, and how many break-even exits happen in the same minute
as the stop move.

## Why this is exploratory

All of NQ 2010–26 has already been looked at, and this is one more exit variant on the same data
(after the fixed TP, the resting limit, three trailing distances and the RR grid). The more variants
are tried on one sample, the more likely one looks good by chance. So a pass would be a lead to check
on forward data, not a rule change.

Prior evidence, stated before running: the 1.0R trailing stop also starts at the entry price when +1R
is reached (then keeps trailing). It was rejected. A fixed break-even stop is the mildest form of that
idea, so a large gain is not expected.

## Known limitation

The tester's 1-minute OHLC model has four prices per minute in an assumed order. A break-even exit in
the same minute as the +1R touch depends on that assumed order. Stops also fill without slippage in the
tester; a live break-even stop can slip below the entry price.
