# Research journal

What we did, day by day, and what each step answered. Newest day last.
For the current state of the strategy, see [STATUS.md](STATUS.md).

## Where we are now (updated 2026-10-01)

- **Strategy:** buy stop over the last red M30 candle, stop at its low, bar-close exit at ≥ 1R,
  `MaxRedRun = 3`, flatten at 23:30 with the fallback fix. 2020–26: net $37.4k, PF 1.105.
- **Entry and exit tweaks are largely exhausted;** most ideas failed. Only the red-run cap survived.
- **Data rebuilt** (`MNQcontDTBNT20102026`) and **early-close calendar** added: the strategy is
  now strictly intraday. On clean data 2.5R beats 1R in both periods.
- **Next:** (1) decide RR; (2) confirm `MaxRedRun` on the rebuilt data; (3) time-of-day blocks.
  Re-import the cleaned CSV before using pre-2016 dates.

---

## 2026-09-28: Can preceding bars improve entries?

- Built `RR_r_MFE_buy-stop-entry_features.cs` (logs the last 30 bars per trade) and
  `analyze_features.py` (10 bar-only features, judged one at a time).

## 2026-09-29: Entry filters

- **Feature scan (2020–26):** no feature isolates a losing group. One theme stood out:
  "falling-knife" signals near the 20-bar low trade at about breakeven.
- **Location + red-run** looked good after the fact (DD halved). → Built the runband EA from
  the buy-stop base (`MaxRedRun`, `MinLocation`).
- **MT5 confirmation:** location **not confirmed**; all profit differences are within noise.
- **2010–19 baseline:** 2010–14 has **no edge** even before costs. 2015 onwards looks like today.
- **MaxRedRun train/test:** chosen on 2015–19 by a pre-set rule (→ 3), then frozen on
  2020–26: PF up in 6/7 years, DD −17%, profit flat. **Adopted** (small effect).

## 2026-09-30: Project tidy-up, more entry questions, exits

- Project reorganized into `mt5/`, `python/`, `docs/`, `data/`.
- **Q1 interrupted decline / Q2 recovery after a new low:** periods disagree. **No filter.**
- **First-touch +1R exit (estimate):** worse than the bar-close exit. The overshoot beyond
  1R (about +0.6R on ~70% of winners) is valuable.
- **Data review:** pre-2019 data is NQ-based; the clock is Chicago + 8 h; roll contracts were
  picked with same-day volume; the NQ/MNQ join and any price adjustment are unverified.
- **Exit thresholds 0.75–2R + fixed TP (MT5):** fixed TP is worse. **Found a bug:** positions
  were held for days when the 23:30 bar was missing.
- **RR grid 0.5–5:** a noisy curve. Gains above 1R mostly came from those multi-day holds.

## 2026-10-01: Flatten fix and "capture the wick"

- **Flatten fallback** (new `FlattenFallback` input): the cause was early-close days and
  DST-mismatch weeks. Multi-day holds are gone; the baseline barely changes.
  **RR stays 1.0:** in dollars the best RR differs by period; average R prefers higher RR.
- Added the one-page [STATUS.md](STATUS.md) and summary boxes on the long docs.
- **Resting limit above the target (estimate):** winners give back about 0.3–0.4R, but every
  limit level is worse because it caps the big runners. **Rejected.**
- **Trailing stop after +1R at 0.25 / 0.5 / 1.0R (MT5):** worse in 2015–19, mixed in
  2020–26. **Rejected.** The bar-close exit stays.

## 2026-10-01 (later): Sizing, overnight trades, data rebuild

- **Sizing (real cost $1.05/contract):** fixed-$200-risk sizing capped at 5 contracts beats
  1 contract in 2020–26 but not in 2015–19 (small candles multiply commission). Sizing
  **doesn't change** the RR answer. Keep 1 contract for research.
- **Why ~70–95 overnight trades remain:** a bar-time dump showed the data clock shifts one hour
  in US/EU DST-mismatch weeks (55–60% of them); the rest are holiday early closes.
  Data before 2016 also had a different session shape.
- **Rebuilt the data** from the Databento source ([DATA_BUILD.md](DATA_BUILD.md)): consistent
  clock, rolls without hindsight. Confirmed the old file was shifted 1 h in mismatch weeks.
  Dropped the pre-2016 post-16:00-Chicago tail bars. Imported as `MNQcontDTBNT20102026`.
- **Early-close calendar** ([results](EARLY_CLOSE_CALENDAR_RESULTS.md)): on the new data all
  remaining overnight holds started on early-close days. A data-derived calendar (262 sessions,
  matching the published schedule) makes every run flat at session end. Profit is unchanged.
  On clean data **2.5R beats 1R in both periods** (net $, PF, avg R).

---

*Add a dated section after each working session: the question, the answer, and a link to the
study doc. Keep each step to one or two lines.*
