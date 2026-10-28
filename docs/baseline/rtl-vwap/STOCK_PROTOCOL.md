# RTL far-below VWAP rule on Nasdaq-100 stocks

Frozen 2026-10-28, before any stock VWAP label or RTL outcome was computed. The user proposed
this test after the [cross-instrument test](CROSS_RESULTS.md) failed (ES, YM and RTY: 0 of 3;
NQ 2010-15 failed too), and chose a session that includes the pre-market. Only NVDA has been
downloaded so far, and its file was inspected for structure only (hours covered, record count,
hash). Confirmatory in intent. The result is read together with the earlier failures, not
instead of them. No strategy, default or live change follows from this test alone.

## Question

NQ is built from these stocks. If "far below VWAP" really marks weak RTL signals, and the effect
lives in Nasdaq names (which would explain why ES, YM and RTY did not show it), it should appear
in the large Nasdaq-100 stocks:

1. Far-below signals earn less net R than other signals with similar planned risk.
2. Skipping them cuts drawdown more than skipping as many trades chosen without VWAP.

**This is the last historical instrument test of this rule.** Whatever the result, no further
instruments, sessions, thresholds or anchors will be tried on history: testing one market after
another until one passes would bring back the luck problem.

## Stocks and data

Ten large, long-standing Nasdaq-100 companies, chosen by size and data history before any stock
result, including the user's examples NVDA, TSLA and MSFT:

**AAPL, MSFT, NVDA, AMZN, GOOGL, META, AVGO, TSLA, COST, NFLX.**

All ten are Nasdaq-listed index members from May 2018 to September 2026. They are also among the
biggest winners of that period, which favours a long-only strategy. The test compares far-below
signals with other signals of the same stock, so this mostly affects the background.

- **Source:** Databento `XNAS.ITCH`, schema `ohlcv-1m`, raw symbols, 2018-05-01 to 2026-10-27
  (end exclusive), as already downloaded for NVDA. Meta: raw symbol `FB` from 2018-05-01 to
  2022-06-08 and `META` from 2022-06-09; before that date the ticker META belonged to a
  different security.
- **Volume:** bars come from trades on Nasdaq's own exchange only, so volume is Nasdaq-venue
  volume, not all venues. The VWAP here is the Nasdaq-exchange VWAP, an approximation.
- **Time:** timestamps convert from UTC to New York time; a session is one New York date.
  Minutes from 16:00 on (after-hours) are dropped.
- **Splits:** earlier prices are divided by the split ratio and volumes multiplied by it. This
  leaves intraday VWAP unchanged and keeps A20 and multi-day levels continuous. Split dates and
  ratios come from the companies' announcements, and each must show in the data as an overnight
  price ratio within 5% of the ratio. Any other overnight move beyond 30% is investigated before
  labels. The list goes into the source audit.
- **Early closes:** the days Nasdaq's regular session ends at 13:00 New York time, from the
  exchange's published calendar, recorded in the source audit before labels. On those days the
  session ends at 13:00.

## RTL on stocks

The NQ EA's order logic, unchanged except for the session, fills, size and cost:

- **Session:** 04:00-15:59 New York time, pre-market plus regular hours (the user's choice).
  M30 bars start at 04:00, 04:30, ... 15:30 and are built from the minutes that exist. Orders
  may be placed from the session's first bar.
- **Orders:** at the first minute of each new M30 bar, if the previous completed bar is red
  (close < open) with a positive range: cancel any pending order and place a buy stop at that
  bar's high with the stop at its low, unless the high is at or below the current price
  (rejected). Otherwise a pending order stays. One position at a time. A session's first bar may
  use the previous session's last bar as its signal, as the EA does; its VWAP label is then
  unknown.
- **Exit:** the stop, or at the first minute of the next bar after a completed bar closes at or
  above entry + 1R, where R runs from the actual fill to the stop, as the EA computes it.
- **Cutoff:** 15:30 (12:30 on early-close days), mirroring NQ's 23:30. At the first minute of
  the cutoff bar, close any position at that minute's open and cancel orders; no new orders
  after it. A position still open at the next session's first minute (data ended early) closes
  at that minute's open.
- **Fills, changed from NQ:** MT5's tester fills stops at their level even when price jumps past
  them. Stocks gap overnight and print thinly before the open, so fills here are gap-aware. A buy
  stop fills at its level, or at a minute's open when that open is already above it. A stop-loss
  exits at its level, or at the open when that open is already below it. Within a minute, the
  price path follows the simulator's MT5 1-minute OHLC order.
- **Size and cost:** $10,000 at the requested price per trade (fractional shares), so results
  compare across stocks and years. Planned risk = shares x (requested price - stop); net R = net
  dollars / planned risk. Cost $2 per completed trade (about 1 basis point per side); +$2 and +$4
  stress reported.

## The rule, unchanged

NQ's code, `python/build_rtl_vwap_features.py` (hash below), variant `full_hlc3`, fed with the
stock's session minutes in its input format. VWAP = cumulative minute (H+L+C)/3 x volume /
cumulative volume from the session's first minute, pre-market included. A20 = arithmetic mean of
the last 20 completed M30 true ranges. z = (signal close - VWAP) / A20, from the latest M30
feature available (bar start + 30 min) at or before submission. A feature from an earlier
session, or a missing A20, is unknown, and the trade is kept. **Far below: z < -1.**

## Samples

- **Primary:** all ten stocks, trades submitted 2018-05-01 to 2026-09-30 (the futures tests'
  end). Eras 2018-19 (from May 2018) and 2020-Sep 2026; pooled = both.
- **Portfolio:** the ten stocks' daily dollar results added together, on a calendar of every
  session with data for any of them.
- **Descriptive only, never in the verdict:** each stock alone; the regular-hours version
  (session and VWAP from 09:30, same cutoff); co-movement with NQ (NQ's `full_hlc3` label at the
  same moment; NQ's clock is New York time + 7 hours).

## Source checks, before any label

- Each file is `XNAS.ITCH`, `ohlcv-1m`, with the listed symbol and dates; its SHA-256 is recorded
  at first read (NVDA's is below).
- Minutes: positive volume, valid OHLC, unique ordered timestamps; split and early-close lists
  as above.
- Given NQ's session, cutoffs and MT5 fills, the stock simulator must reproduce all 25,833 MT5
  NQ trades exactly, which shows its order logic is the EA's.
- Every trade's signal bar is red, with high = requested price and low = stop. Positions never
  cross a session except where data ends early, and each such case is explained.

Any failure stops the study until it is resolved and disclosed. No outcome is read before these
pass.

## Measures

As in the [cross-instrument protocol](CROSS_PROTOCOL.md), with stocks in place of instruments:

**A. Risk-matched contrast.** Cells are stock x era x planned-risk decile (equal-count, ties by
submission time). In each cell: mean net R of far-below trades minus that of all other trades,
unknowns included; the weighted mean uses far-below counts as weights. 95% interval: circular
4-calendar-week block bootstrap, 5,000 draws, drawing the same weeks for all stocks so their
joint moves stay together.

**B. Placebos that skip without VWAP,** 2,000 draws each, within each stock:

1. Risk decile: as many random non-far-below trades per stock x era x decile cell as it has
   far-below trades (shortfall reported).
2. Rolled within month: the rule's own skip pattern rolled circularly within each stock-month.
3. Month x risk tertile, and 4. largest risk: descriptive.

Statistics are taken on the portfolio: net dollars, daily-close drawdown and planned risk kept.
"Rule beats" = the share of draws whose drawdown is larger than the rule's (ties count against
the rule).

**C. Descriptive.** Per-stock results; the NQ study's unadjusted contrast and its time x risk
adjustment; annual results; cost stress; the regular-hours version; co-movement with NQ.

Seeds: bootstrap 2026102801, placebos 2026102802; stocks are processed in the listed order.

## Verdict, fixed now

The test **supports** the rule if, on the pooled ten-stock sample:

1. contrast A is below zero and its whole 95% interval lies below zero;
2. the rule's portfolio drawdown beats at least 95% of B1 draws and at least 95% of B2 draws; and
3. in each era, contrast A is below zero and the rule's portfolio drawdown is below the median
   drawdown of B1 and of B2; and contrast A is below zero in at least 7 of the 10 stocks.

A stock with fewer than 200 far-below trades or 30 active weeks is left out of tests 1-3 and
reported. With fewer than 8 stocks left, the result is inconclusive. Otherwise the test
**does not support** the rule.

What follows:

- **Supports:** the effect shows in data it was not found on, in the stocks NQ is made of. Read
  with NQ 2016-26, that points to a Nasdaq-specific effect rather than luck, and would explain the
  ES, YM and RTY result. The rule becomes a candidate for cautious live use on NQ: start small,
  with a forward review rule written before going live.
- **Does not support, or inconclusive:** the VWAP line for RTL closes on history. A forward
  paper test on NQ remains possible.

Limits, stated in advance. These stocks drive NQ and fall on the same days, so this is partly
the same history; the co-movement output measures how much. Volume is Nasdaq-venue only, the
pre-market prints thinly, and there is no spread or slippage model. Gap-aware fills, $10,000
sizing and a stock session make absolute results incomparable with NQ's; the test is relative.
The ten stocks are survivors.

## Outputs and verification

`Reports/rtl_vwap_stocks_20261028/` (gitignored). An independent verifier re-reads the files with
separate code and rebuilds the M30 bars, VWAP, A20 and z. It re-implements the stock RTL rules
separately and must match every trade. It also recomputes every summary, contrast, bootstrap and
placebo draw, and the verdict. Tests: split adjustment, session window and cutoff (including
early closes), gap-aware entry and stop fills, signal-bar check, placebo counts. One chart.
Results go to `STOCK_RESULTS.md` in this folder, with plan, journal and status updated.

## Inputs at freeze (SHA-256)

| File | SHA-256 |
|---|---|
| `F:\DATABENTO\NVDA-XNAS-20261028-NHDY74EDDE.zip` | `07188fceb083489dd18389b42b330b8e8f4d726dcda452d9f802befdb88a1062` |
| its `xnas-itch-20180501-20261026.ohlcv-1m.dbn` (matches Databento's manifest) | `d2486d79131a6e2a06771f7fc98174cad3b8740db3d1386ea9e367c49e40c781` |
| `python/build_rtl_vwap_features.py` | `1dd7adc771100f80570b8ce608f3a11d3fc0a81c4c103536c6de119bbbfc51e4` |

The other nine stocks' files are hashed on arrival, before any label.
