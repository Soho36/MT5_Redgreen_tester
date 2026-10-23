# Data rebuild: continuous NQ and ES 1-minute series

2026-10-01 (NQ), 2026-10-08 (ES) · Script: `python/build_continuous.py` (was `build_nq_continuous.py`)
· Output: `F:\DATABENTO\MNQ_16_YEARS\`, `F:\DATABENTO\ES_16_YEARS\`

The NQ part comes first; the ES build (same rules, unseen-instrument data) is [below](#es-build-2026-10-08).

## Summary

- **Why:** the current MT5 symbol (`MNQcontDATABENTOcurr6`) has an inconsistent clock.
  Since 2015 the session shifts one hour earlier in the US/EU daylight-saving mismatch
  weeks (no 23:30 bar, so flatten failed). Before 2015 it has a different session shape.
  Rolls also used same-day volume (hindsight).
- **Rebuilt from source:** Databento `GLBX.MDP3`, `NQ.FUT` (all NQ contracts), OHLCV-1m,
  2010-06-06 → 2026-09-30.
- **Result:** from 2016 on, every normal session is **01:00–23:59** all year, with no
  DST shift. Early closes end at 19:59 / 20:14 (12:00 / 12:15 Chicago).
- **Next:** import as a new MT5 custom symbol (keep the old one), then rerun the key
  tests on it.

## Conventions

| | |
|---|---|
| Contracts | NQ outrights only; calendar spreads dropped. Keyed by `instrument_id`, because one-digit-year names (`NQM0`) repeat every decade |
| Clock | America/Chicago + 8 h for all years (normal session 01:00–23:59 on one date) |
| Roll | Each date trades the contract with the highest volume on the **previous** date, never rolling back to an earlier expiry. 67 contract periods; every roll falls in Mar/Jun/Sep/Dec on the 7th–19th |
| Prices | Raw, not adjusted. Positions are flat at session end, so roll gaps fall between sessions |
| Format | MT5 bar import, tab-separated `<DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>`; spread 1 as before |

## Output

- `MT5_NQ_continuous_2010-2026_ohlcv-1m.csv`: 5,511,965 bars, 4,203 dates,
  2010-06-07 01:00 → 2026-10-01 02:59. Imported into MT5 as custom symbol
  `MNQcontDTBNT20102026`.
- `MT5_NQ_continuous_2010-2026_rolls.csv`: roll date, `instrument_id`, contract name,
  first date the contract appears.

## Checks

- **Compared with the old converted CSV** (`MT5_databento-ohlcv-1m.csv`): 90.4% of common
  minutes are identical. The 426 differing days are explained:
  - 277 days in DST-mismatch weeks: the **old file is shifted by exactly 1 hour** there
    (100% identical after shifting). The new file is correct.
  - 69 days near rolls: the deliberate one-day-later roll (previous-day volume).
  - 80 days with identical prices and only volume different (2× in the new download).
    The EA doesn't use volume.
- No zero prices; no bars with high < low.

## Known quirks (real market structure, not build errors)

- **Before 2016, NQ traded until about 16:15–16:30 Chicago** (00:00–00:30 in this clock).
  Those thin bars (median volume 7 vs 86) landed on the *next* date and created "Saturday"
  fragments. **Dropped** (21,050 rows across all contracts, plus 35 sporadic 00:xx bars in
  2018), so every session starts at 01:00 and there are no weekend dates.
- In 2010–2012, 123 sessions end at 23:14: NQ then halted at 15:15 Chicago.

## Reproduce

```powershell
.\venv\Scripts\pip.exe install databento   # once
.\venv\Scripts\python.exe python\build_continuous.py NQ "F:\DATABENTO\MNQ_16_YEARS" "F:\DATABENTO\MNQ_16_YEARS\NQ_20100606-20261001\glbx-mdp3-20100606-20260930.ohlcv-1m.dbn"
```

## ES build (2026-10-08)

- **Why:** an instrument the strategy was never tuned on (unseen data). Built with exactly the NQ
  rules above; the refactored script reproduces the NQ files byte for byte.
- **Source:** Databento `GLBX.MDP3`, `ES.FUT`, OHLCV-1m, two CSV downloads:
  `ES_full.ohlcv-1m.csv` (2010-06-06 → 2026-04-16) and `glbx-mdp3-20260417-20261006.ohlcv-1m.csv`
  (2026-04-17 → 2026-10-06, UTC).
- **Input checks (both files):** no duplicate (minute, contract) rows, timestamps sorted, no zero
  prices, no OHLC inconsistencies, all prices on the 0.25 tick, no zero-volume bars, each
  `instrument_id` has one name. The files join seamlessly (last bar 2026-04-16 23:59 UTC, first
  2026-04-17 00:00 UTC, no overlap; ESM6/ESU6/ESZ6/ESH7 keep the same `instrument_id` in both).
  No calendar gap longer than a weekend/holiday (but see the two intraday holes below).
- **Output:** `MT5_ES_continuous_2010-2026_ohlcv-1m.csv`: 5,685,512 bars, 4,207 dates,
  2010-06-07 01:00 → 2026-10-07 02:59 (the last session is partial, as in the NQ file).
  29,079 post-close tail rows dropped. `MT5_ES_continuous_2010-2026_rolls.csv`: 67 contract
  periods, all in Mar/Jun/Sep/Dec on the 11th–18th.
- **Output checks:** Monday–Friday dates only; since 2016, 2,779/2,781 sessions start at 01:00
  and 2,682 end at 23:59 (the rest are early closes 19:59/20:14 and holidays). Session dates
  equal the NQ file's (ES has 4 more at the end because its download is newer).
- **Intraday holes (found 2026-10-08, after the first check):** the Databento ES source stops mid-session on
  **2020-02-28** (no bars after 15:59 UTC, 17:58 in this clock) and **2020-06-30** (after 14:10 UTC, 17:10),
  for all contracts. NQ has both days complete. These are the only ES-only holes: every session was compared
  with NQ (end time and bar count), and the other long internal gaps appear in both (2012-07-03, 2019-02-27,
  2025-11-28 CME outage). Re-download those two days if Databento has them; the RTL baseline has 8 trades
  there (net −$480).
- **Early-close calendar:** `mt5/experts/early_closes.mqh` (built from NQ) fits ES too. ES has the same CME
  schedule. Apart from the two holes, the only differences are 3 sessions whose last bar is one minute off
  (19:59 vs 20:00).
- **Compared with the old ES conversion** (`MT5_v_converted.csv`, to 2026-04-17): 98.5% of
  common minutes identical (the old file already used this clock). The 67 differing days:
  - 64 are the session before a roll (the old file rolled on same-day volume).
  - **3 days in the old file hold calendar-spread prices instead of ES** (2017-03-13 ≈ −3.2,
    2017-12-11 ≈ 2.9, 2019-06-17 ≈ 4.2 instead of 2,368 / 2,655 / 2,895). Any test on an MT5
    symbol built from the old file is wrong on those days. The new file contains outrights only.

```powershell
.\venv\Scripts\python.exe python\build_continuous.py ES "F:\DATABENTO\ES_16_YEARS" "F:\DATABENTO\ES_16_YEARS\ES_full.ohlcv-1m.csv" "F:\DATABENTO\ES_16_YEARS\glbx-mdp3-20260417-20261006.ohlcv-1m.csv"
```

## YM build (2026-10-23)

- **Why:** a second unseen instrument (Dow futures) for the four baselines ([results](../baseline/ym-unseen-instrument/RESULTS.md)).
  Built with exactly the NQ/ES rules above.
- **Source:** Databento `GLBX.MDP3`, `YM.FUT` (parent), OHLCV-1m, one DBN file
  `glbx-mdp3-20100606-20261021.ohlcv-1m.dbn` (job GLBX-20261022-65U97KVMGQ), unpacked to
  `F:\DATABENTO\YM_16_YEARS\source\`.
- **Input checks:** 257,534 spread rows dropped; outrights have no duplicate (minute, contract) rows, sorted
  timestamps, no zero prices, no OHLC inconsistencies, every price on the 1.0 tick, no zero-volume bars, one name per
  `instrument_id`. Last bar 2026-10-21 23:59 UTC.
- **Output:** `MT5_YM_continuous_2010-2026_ohlcv-1m.csv`: 5,502,688 bars, 4,223 dates,
  2010-06-07 01:00 → 2026-10-22 02:59 (last session partial). 17,087 post-close tail rows dropped. 67 contract
  periods, all in Mar/Jun/Sep/Dec.
- **Output checks:** Monday–Friday only; since 2016, 2,789/2,792 sessions start at 01:00 and 2,694 end at 23:59
  (the rest are the usual early closes). Session dates match NQ apart from five 2014 dates the NQ file lacks
  (2014-06-12/13, 2014-09-23/24/25, 2014-12-31 present in YM only; 2014-10-03 in NQ only) and the newer end.
- **Intraday holes (compared with NQ):** 2020-02-27 (two gaps of 98 and 190 min), 2020-02-28 (nothing before 10:00),
  2020-03-16 (227 min) and 2020-06-30 (no bars after 17:10, the same hole as ES). Other long gaps also occur in NQ.
  YM has fewer bars per session than NQ on some days (minutes with no trade), mainly around rolls.
- **MT5:** imported 2026-10-23 as `MYMcontDTBNT20102026` by `python/import_custom_symbol.py`: settings copied from
  `MNQcontDTBNT20102026_2`, then tick size 1.0 and tick value $0.50 (MYM). The script reads every year back from MT5
  and checks bar counts, first/last bar and price sums against the CSV (`Reports/ym_symbol_20261023/`).
- **ES re-import (same day):** the old `MEScontDTBNT20102026` no longer has bars in MT5, so the ES file was imported
  again as `MEScontDTBNT20102026_2` (tick 0.25, $1.25, i.e. $5/pt as before) with the same checks
  (`Reports/es_symbol_20261023/`). The old symbol was left untouched.

```powershell
.\venv\Scripts\python.exe python\build_continuous.py YM "F:\DATABENTO\YM_16_YEARS" "F:\DATABENTO\YM_16_YEARS\source\glbx-mdp3-20100606-20261021.ohlcv-1m.dbn"
```

## RTY build (2026-10-23)

- **Why:** a third unseen instrument (Russell 2000) for the same experiments as YM
  ([results](../baseline/rty-unseen-instrument/RESULTS.md)). Same rules as NQ/ES/YM.
- **Source:** Databento `GLBX.MDP3`, `RTY.FUT` (parent), OHLCV-1m, `glbx-mdp3-20100606-20261021.ohlcv-1m.dbn`
  (job GLBX-20261022-G4K3WHA8KV), unpacked to `F:\DATABENTO\RTY_16_YEARS\source\`. **CME RTY starts 2017-07-09**
  (Russell futures traded on ICE before), so there is no 2010–16.
- **Input checks:** 215,575 spread rows dropped; outrights clean (no duplicates, sorted, no zero prices, no OHLC
  inconsistencies, every price on the 0.1 tick, no zero volume, one name per `instrument_id`).
- **Output:** `MT5_RTY_continuous_2017-2026_ohlcv-1m.csv`: 3,077,561 bars, 2,401 dates, 2017-07-10 01:01 →
  2026-10-22 02:59; 49 tail rows dropped; 38 contract periods.
- **Output checks:** Monday–Friday only; 2,377/2,401 sessions start at 01:00, 2,294 end at 23:59 (the rest are early
  closes or a last minute without a trade); no session ends early against NQ. The launch months 2017-07 → 2017-09 are
  thin (about 50 intraday gaps of 1–6 hours); after that the long gaps are 2019-02-27, 2020-03-09/16/17/18, 2020-04-17
  and the 2025-11-28 CME outage. RTY has fewer bars per session than NQ on many days (minutes without a trade).
- **MT5:** `M2KcontDTBNT20172026` (settings from `MNQcontDTBNT20102026_2`, tick 0.1, tick value $0.50 = M2K $5/pt),
  imported and verified per year by `python/import_custom_symbol.py` (`Reports/rty_symbol_20261023/`).

```powershell
.\venv\Scripts\python.exe python\build_continuous.py RTY "F:\DATABENTO\RTY_16_YEARS" "F:\DATABENTO\RTY_16_YEARS\source\glbx-mdp3-20100606-20261021.ohlcv-1m.dbn"
```

