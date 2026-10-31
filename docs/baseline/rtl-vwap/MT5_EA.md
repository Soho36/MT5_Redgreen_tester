# RTL VWAP gate in MT5: EA, indicator and stock data

Prepared 2026-10-28 at the user's request. These are tools for looking at the far-below VWAP rule
in MT5, on NQ or on the ten stocks, and for a possible forward paper test. They change no research
verdict. The rule [did not transfer](CROSS_RESULTS.md) to ES, YM or RTY and is
[not supported](STOCK_RESULTS.md) on stocks, so it is not adopted for live trading.

## What there is

| Item | What it does |
|---|---|
| [RR_GG_r_MFE_buy-stop-entry_vwap.cs](../../../mt5/experts/RR_GG_r_MFE_buy-stop-entry_vwap.cs) with [rtl_session_vwap.mqh](../../../mt5/experts/rtl_session_vwap.mqh), [stock_early_closes.mqh](../../../mt5/experts/stock_early_closes.mqh), [early_closes.mqh](../../../mt5/experts/early_closes.mqh) | The RTL runband EA plus the VWAP gate, any symbol. Compiled in MT5 as `Experts\CodexResearch\RR_GG_r_MFE_buy-stop-entry_vwap` |
| [RTL_Session_VWAP.mq5](../../../mt5/indicators/RTL_Session_VWAP.mq5) | Draws session VWAP, the gate line and the candles the gate would skip, on any M30 chart. Compiled as `Indicators\CodexResearch\RTL_Session_VWAP` |
| `F:\DATABENTO\STOCKS\MT5\MT5_<STOCK>_2018-2026_ohlcv-1m.csv` | The ten stocks' 1-minute bars for MT5 import (written by [export_stock_mt5.py](../../../python/export_stock_mt5.py); `manifest.json` lists rows, splits, early closes and checks) |
| `rtl_vwap_features_<STOCK>.csv` | VWAP label files for tester runs, next to the CSVs and copied to MT5's `Common\Files`. NQ's is the replay's `rtl_vwap_replay_20261026_features.csv`, already in `Common\Files` |

## The one thing to know: the tester's minute volume is not real

In the Strategy Tester ("1 minute OHLC"), MT5 does not hand the EA the stored minute bars. It makes
its own ticks from them and rebuilds the minutes from those ticks, and every rebuilt minute gets
the same volume. A VWAP computed inside the tester is therefore a plain average of minute prices,
not a volume-weighted one. On NQ the two typically differ by about 2.5 points, enough to change
many decisions. With the same settings, the computed-in-tester run made 19,974 trades and $54,939,
while the real VWAP gives 20,721 trades and $65,645.50 (the verified [replay](REPLAY_RESULTS.md)).

So:

- **Tester (history):** set `VwapLabelFile` to the symbol's label file. The EA then reads the
  study's labels, computed from the real volume.
- **Live or demo chart:** leave `VwapLabelFile` empty. The EA computes VWAP from the broker's
  minute bars, which carry the real volume.

The same holds for the indicator: on a normal chart it computes from stored bars (real volume); in
the tester's visual mode, set its `LabelFile`.

## How the gate works

At each red M30 candle that passes the EA's usual rules, the old pending buy stop is cancelled as
always. Then the gate compares that candle's close with **VWAP minus A20**:

- **VWAP**: from the session's start to the candle's close, the average of each minute's typical
  price (high + low + close) / 3, weighted by its volume. The session is one date on the session
  clock: for NQ, Chicago + 8 h, so the CME day from 01:00; for the stocks, the New York date from
  04:00.
- **A20**: the average true range of the last 20 completed M30 candles.

Close strictly below VWAP minus A20: no new buy stop for this candle. Otherwise, or when the value
is unknown (first candle of a session, missing minutes, fewer than 21 candles), the order is placed
as usual. Open positions are never touched. This is the rule of the [study](RESULTS.md),
unchanged. With `UseVwapGate=false` the EA trades exactly like the runband EA.

## New EA inputs

| Input | Default | Meaning |
|---|---|---|
| SignalCandle | Red (RTL) | Red = RTL, Green = GG. `MinRedRun`/`MaxRedRun` then count runs of that colour (GG baseline: 1 and 0) |
| UseVwapGate | true | Gate on or off |
| VwapFilterLine | Orange cutoff (0) | Orange = compare signal close with VWAP + VwapFarBelowZ × A20; Blue (1) = compare with VWAP itself. Works for RTL and GG |
| VwapFarBelowZ | -1.0 | Gate line = VWAP + this × A20. The research value; do not tune it on history |
| VwapLabelFile | "" | Empty: compute VWAP from minute bars (live/demo). Tester: the label file's name in `Common\Files` |
| VwapAnchorMinute | 0 | VWAP start in minutes after the session date's midnight. 0 = whole session; 570 = 09:30 for stocks (regular hours only) |
| VwapVolume | Auto | Auto = real volume when the minutes have it, else tick volume |
| LogVwapDecisions | false | Writes every candidate's VWAP, A20, z and decision to `Common\Files\vwap_decisions_<tag>.csv` |
| EarlyCloseSet | CME | Which early-close list `UseEarlyCloseCalendar` uses: CME (futures) or US stocks (13:00 closes, flatten 12:30) |
| NotionalPerTrade | 0 | 0 = trade `Lots`. Above 0 = shares worth this much at the buy-stop price, rounded down to the volume step |

Outputs go to `Common\Files`: trades `rtlvwap_<tag>_<RR>.csv`, totals `rtlvwap_<tag>_<RR>_stats.csv`
(with the gate's candidate, known and withheld counts). The tester reuses the last value of any input
an INI leaves out, so set them all.

## NQ in the tester

**Filter selection, EA version 1.02 (2026-10-31):** set `UseVwapGate=true`, then choose
`VwapFilterLine`: **Orange cutoff** preserves the original rule; **Blue line** requires
the signal candle to close at or above VWAP. Equality is allowed in both modes.
`VwapFarBelowZ` still positions the orange chart line when Blue is selected, but does
not affect the blue filter. Both lines remain visible. The normal entry rules,
pending-order handling, and unknown-data behavior are unchanged: both modes use the
existing known-VWAP/A20 checks, including the A20 warmup. Gate OFF bypasses either
selection. Journal messages, decision CSVs and tester stats identify the selected line.
The blue mode is an experimental option; previous study results describe Orange only.
Set `VwapFilterLine=0` explicitly in old INIs/presets to preserve the original rule;
MT5 may retain a previously selected input when it is omitted.

**Visual chart, version 1.01 (2026-10-31):** enable Visualization on an M30 test of
`RR_GG_r_MFE_buy-stop-entry_vwap`. The EA automatically adds
`Indicators\CodexResearch\RTL_Session_VWAP` using its own VWAP inputs, including
`VwapLabelFile`. Compile/install the current EA and indicator (version 1.01 or later) together.
Blue is session VWAP; dashed orange is `VWAP + VwapFarBelowZ * A20` (normally
VWAP minus A20). The lines also appear with the gate OFF for comparison.
The EA suppresses the indicator's standalone red-candle marks so they cannot be
mistaken for actual RTL or GG trades; MT5's native trade markers remain.
Label-file values appear on their signal candle only once that candle has closed;
the forming candle stays blank. Computed VWAP can move while the candle forms.
This display does not change entry/exit rules or run during nonvisual tests or
optimization. The EA prints its version in the Journal at startup.

Use the correct label file for historical tests: the displayed lines use the same
source as the gate, including synthetic tester volume if the filename is empty.
If the indicator is missing or cannot be attached, the visual test reports the
error and stops initialization.

The baseline settings (symbol `MNQcontDTBNT20102026_2`, M30, 1 minute OHLC, windows 01:00-23:30,
flatten 23:30, CME early closes), plus `VwapLabelFile=rtl_vwap_replay_20261026_features.csv`. The
labels cover 2010-06-07 to 2026-09-30; after the last label the gate stays off (unknown = allowed).

**GG on NQ** (added 2026-10-30): the same settings and the same label file, plus `SignalCandle=Green
(GG)`, `MinRedRun=1`, `MaxRedRun=0`. The label file has one row per M30 bar, so it serves green
signals as well as red. With the gate off this reproduces the GG baseline run
(`ymbase_20261023_gg_nq`) byte for byte. Prepared INIs: `Reports/gg_vwap_ea_20261030`
([prepare_gg_vwap_ea.py](../../../python/prepare_gg_vwap_ea.py)); results in
[GG_RESULTS.md](GG_RESULTS.md#mt5-replay).

**After a GG run, set `SignalCandle=Red (RTL)` explicitly for RTL.** The tester reuses the last
value of an input missing from an INI, and the INIs written before 2026-10-30 (including
`Reports/rtl_vwap_ea_20261028`) have no `SignalCandle` line: run after a GG run, they would trade
green candles. Check the tester's Inputs tab, or the `signal_candle` column of the stats file.

## The stocks

**Data.** May 2018 to 2026-10-27 (NVDA to 2026-10-26), New York time, 04:00-15:59 (04:00-12:59 on early-close days),
split-adjusted to today's shares (volumes scaled up to match), as in the stock test. Meta starts
2022-06-09 (Databento has no FB history). Labels run to the same end.

**Imported and verified 2026-10-29** in the research AMP MT5 terminal. All ten symbols
are under `Custom\CodexInstruments`, named `AAPL_XNAS`, `MSFT_XNAS`, `NVDA_XNAS`,
`AMZN_XNAS`, `GOOGL_XNAS`, `META_XNAS`, `AVGO_XNAS`, `TSLA_XNAS`, `COST_XNAS`,
and `NFLX_XNAS`. All 11,663,663 M1 bars were read back and checked against the input
timestamps, OHLC prices (within 0.0000001), tick/real volumes and spread. Settings
and the source/label hashes passed. Evidence: `Reports/stock_import_20261029/`.
The companion VWAP label files are verified in `Common\Files`.

Automated import: [import_stock_symbols.py](../../../python/import_stock_symbols.py),
with MT5 closed. Set Digits before Tick size: setting 0.000001 while the symbol
still has the copied two-digit precision rounds the tick size to zero.

**Manual import settings:**

1. View > Symbols (Ctrl+U) > Create Custom Symbol. Copy it from `MNQcontDTBNT20102026_2`, so
   sessions and order settings are the ones the EA already works with. Name it, e.g., `NVDA_XNAS`.
2. Set Digits 6, Contract size 1, Calculation "Exchange Stocks" (margin = position value, not a
   futures margin per share), Tick size 0.000001, Tick value 0.000001, currencies USD, Volume min
   and step 0.01 (fractional shares, as the study's $10,000 per trade; use 1 for whole shares).
3. Bars tab > Import Bars > choose the stock's CSV. The columns are MT5's own export layout.
4. Copy the stock's `rtl_vwap_features_<STOCK>.csv` to `Common\Files` if it is not there.

**EA settings for a stock:** windows W0400W0500 through W1500W1600 on, all others off;
FlattenHourEnd 15, FlattenMinuteEnd 30; FlattenFallback and UseEarlyCloseCalendar true;
EarlyCloseSet US stocks; ServerClock Auto; NotionalPerTrade 10000; VwapLabelFile
`rtl_vwap_features_<STOCK>.csv`.

**MT5 will not match the stock test exactly.** Its tester fills a buy stop at its price even when
the market opens above it, and a stop-loss at its price even when price gaps below. Stocks gap
overnight and in the thin pre-market, so MT5 looks better than the study's gap-aware fills. The
study also charged $2 per trade, and fractional sizes round down to the volume step. The 2026
early closes (Nov 27, Dec 24) come from the published calendar; extend the list for 2027.

## The indicator

Attach it to an M30 chart.

| Display | Meaning |
|---|---|
| Blue line | Session VWAP up to each candle's close |
| Dashed orange line | The gate line, VWAP - A20 |
| Red x above a candle | Red candle closing below the gate line, with the next candle in the same session: the EA places no buy stop at its high. The EA's other rules (windows, flatten, filters) are not drawn |

Values sit on the candle whose close they use; the older `RTL_Study_VWAP` draws them one candle
later, at the decision. The forming candle's values change until it closes. Inputs match the EA's
(`FarBelowZ`, `AnchorMinute`, `VolumeSource`, `ServerClock`, `LabelFile`), plus `MaxBars` = 3000
candles. That needs about 90,000 minutes, under MT5's default limit of 100,000 bars per chart
(Tools > Options > Charts > Max bars in chart); older candles stay empty. On a chart whose minutes
are not loaded yet, the Experts log shows "waiting for the 1-minute history" and the lines appear
a moment later.

## Live or demo (forward test)

On AMP's live symbols (e.g. `MNQZ26`) leave `ServerClock` on Auto: it maps the UTC server time to
the session clock, so the VWAP day is the CME day. Auto volume uses AMP's real minute volume. If a
candidate's minutes are missing, its label is unknown and the order is placed;
`LogVwapDecisions=true` records every decision. A forward paper test would need its own frozen
protocol before it starts.

## How it was checked (2026-10-28)

[verify_rtl_vwap_ea.py](../../../python/verify_rtl_vwap_ea.py) on the runs prepared by
[prepare_rtl_vwap_ea_check.py](../../../python/prepare_rtl_vwap_ea_check.py); evidence in
`Reports/rtl_vwap_ea_20261028/verification.json` (local).

1. **Label file, NQ tester:** identical to the verified replay ON run: the same 66,666 candidates,
   64,817 known, 21,007 orders withheld, byte-identical 20,721 trades, $65,645.50 net.
2. **Computed in the tester:** the session, A20 and known/unknown logic match the study exactly
   (65,747 candidates). VWAP equals the equal-weight average from the second test day on. On the
   first day the minutes before the tester's first tick are stored bars, so the weights mix.
3. **Computed outside the tester** (stored bars, real volume): all 1,003 NQ candles of September
   2026 match the study's VWAP within 0.0000000001, A20 exactly, and all 182 far-below labels.
4. **Indicator, both modes,** same candles: VWAP and gate line within 0.0000000001; 129 of 129 red
   x's where expected.
5. **Indicator on a fresh chart** of a custom symbol whose minutes were not loaded: it waited for
   them and filled itself.
6. **Stock files:** M30 features rebuilt from each exported CSV equal the stock test's (largest
   VWAP difference 0.0000003, TSLA, from rounding prices to 6 decimals; 0 label changes).
7. **Label-file format:** 3 new tests ([test_rtl_vwap_mt5.py](../../../python/test_rtl_vwap_mt5.py));
   all 42 VWAP tests pass.

A first EA run that computed VWAP in the tester is kept in `Reports/rtl_vwap_ea_20261028_firstrun`
with the volume probe that found the synthetic tester volume.
