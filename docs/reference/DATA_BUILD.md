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
  No calendar gap longer than a weekend/holiday.
- **Output:** `MT5_ES_continuous_2010-2026_ohlcv-1m.csv`: 5,685,512 bars, 4,207 dates,
  2010-06-07 01:00 → 2026-10-07 02:59 (the last session is partial, as in the NQ file).
  29,079 post-close tail rows dropped. `MT5_ES_continuous_2010-2026_rolls.csv`: 67 contract
  periods, all in Mar/Jun/Sep/Dec on the 11th–18th.
- **Output checks:** Monday–Friday dates only; since 2016, 2,779/2,781 sessions start at 01:00
  and 2,682 end at 23:59 (the rest are early closes 19:59/20:14 and holidays). Session dates
  equal the NQ file's (ES has 4 more at the end because its download is newer).
- **Compared with the old ES conversion** (`MT5_v_converted.csv`, to 2026-04-17): 98.5% of
  common minutes identical (the old file already used this clock). The 67 differing days:
  - 64 are the session before a roll (the old file rolled on same-day volume).
  - **3 days in the old file hold calendar-spread prices instead of ES** (2017-03-13 ≈ −3.2,
    2017-12-11 ≈ 2.9, 2019-06-17 ≈ 4.2 instead of 2,368 / 2,655 / 2,895). Any test on an MT5
    symbol built from the old file is wrong on those days. The new file contains outrights only.

```powershell
.\venv\Scripts\python.exe python\build_continuous.py ES "F:\DATABENTO\ES_16_YEARS" "F:\DATABENTO\ES_16_YEARS\ES_full.ohlcv-1m.csv" "F:\DATABENTO\ES_16_YEARS\glbx-mdp3-20260417-20261006.ohlcv-1m.csv"
```
