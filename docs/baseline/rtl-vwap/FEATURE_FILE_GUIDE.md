# Brief guide: create an MT5 VWAP/A20 feature file

**Changing VWAP - A20 to VWAP, or to VWAP + A20, does not require a new file.**
The file stores VWAP and A20 separately; the EA applies the offset and side.
Create a new file when the symbol, source history, clock or coverage changes.

Run these commands from `I:\PycharmProjects\MT5_Redgreen_tester`.

## 1. Generate labels from your M1 history

Use a sorted, tab-separated MT5 M1 CSV with `<DATE>`, `<TIME>`, `<OPEN>`,
`<HIGH>`, `<LOW>`, `<CLOSE>` and positive real `<VOL>`. Use dates `YYYY.MM.DD` and times `HH:MM:SS`,
in the same session/server clock as the custom symbol. This exporter uses
one date per session and performs no timezone conversion. Include at least
21 completed M30 bars before the intended test start for A20 warm-up.

For the existing NQ history through September 2026:

```powershell
.\venv\Scripts\python.exe python\export_vwap_labels.py `
  --minutes "F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv" `
  --end-before 2026-10-01 `
  --output "Reports\vwap_labels\NQ_from_M1.csv"
```

`--end-before` keeps only labels **available strictly before** that date.
Use the day after your final complete session, excluding an incomplete final
session. A partial final M30 slot is marked unknown. The tool computes:
M1 HLC3 weighted by real volume, cumulative per session; arithmetic mean of
20 completed M30 true ranges; availability at the M30 close.

If you already have this project's full-session feature table, the quicker
route produces the same labels without rereading M1 history:

```powershell
.\venv\Scripts\python.exe python\export_vwap_labels.py `
  --features "Reports\rtl_vwap_20261025\features_full_hlc3.csv" `
  --output "Reports\vwap_labels\NQ_from_features.csv"
```

Both routes were checked against all 191,781 rows of the historical NQ file.
The output is tab-separated despite its `.csv` extension. A companion
`.metadata.json` records coverage, row counts and file hashes. Existing
outputs are preserved: choose a fresh filename for each new export.

## 2. Copy it to MT5 Common Files

```powershell
Copy-Item ".\Reports\vwap_labels\NQ_from_M1.csv" `
  "$env:APPDATA\MetaQuotes\Terminal\Common\Files\NQ_from_M1.csv"
```

The existing study file is already there as
`rtl_vwap_replay_20261026_features.csv`; you can use it directly for the same
NQ symbol/history. Do not reuse NQ labels for a different symbol or price
adjustment. Never generate the volume weights from Strategy Tester bars:
the tester's generated minute volume is synthetic.

## 3. Select the file and condition in the tester

Load the supplied upper preset for the full strategy settings
(`UseOutsideFilter=false`, no run cap, RR=1). Set
`VwapLabelFile=NQ_from_M1.csv` (filename only), `UseVwapGate=true`, and
use the matching M30 symbol/history and dates. Warm-up/unknown labels do not
allow shorts. For the separate `CodexShortVwapUpper\RTL_short_vwap_upper` EA:

| Experiment | VwapFilterLine | VwapFarBelowZ | ShortVwapSide |
|---|---|---:|---|
| Below lower orange | Orange | -1 | Below line |
| Below blue VWAP | Blue | -1 (ignored for blue) | Below line |
| Above upper orange | Orange | +1 | Above line |

**+1 alone is insufficient:** select **Above line** for the upper-band test.
The actual sell stop remains at the green candle's low. To draw the upper
orange line with `RTL_Session_VWAP`, also set the indicator's `FarBelowZ=+1`
and its matching `LabelFile`. The offset field's
legacy name is retained for compatibility. This research EA is tester-only.
Matching presets are in `Reports\rtl_short_vwap_upper_20261101\`; choose a
fresh `RunTag` for manual runs.

The default volume column is `<VOL>`. `--volume-column '<TICKVOL>'` is an
explicit tick-volume alternative, producing a different study when tick and
real volume differ. The tested NQ example uses real volume.
