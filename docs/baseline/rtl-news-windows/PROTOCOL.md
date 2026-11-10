# RTL: thirty minutes before and after scheduled major news

Frozen 2026-11-10 before inspecting intraday-filter outcomes. Follow-up to
the committed [whole-day study](../rtl-news-days/RESULTS.md), user authorized
both proposed rules. No optimization of the thirty-minute width.

Same original uncapped RTL M30, RR=1, VWAP off, all entry windows, one contract,
$2/point, $1.05 per closed trade, normal/early-close daily flatten. Same history
and reporting periods: primary 2016-19, 2020-Sep2026, pooled; secondary 2010-15
and annual. Exclude October 1, 2026 and later from published outcomes.

Keep the initial CPI / Employment Situation / scheduled FOMC decision scope.
Add the associated scheduled FOMC press-conference start as a distinct timestamp
on its actual historical dates. Use official statement release times, historical
conference listings and official timing notices. No unscheduled meetings,
sentiment, actual/forecast data, speeches or minutes. Preserve source snapshots,
extraction methods, discrepancies and provenance. Archived dates are not complete
point-in-time schedules; retain the 2013/2025/2026 year-removal sensitivity.

Block [event time - 30 minutes, event time + 30 minutes): inclusive start,
exclusive end. Merge overlapping/touching windows. New York time maps to the
research clock by adding seven hours (Chicago+8); retain UTC with proper US DST
for audit, but do not apply European DST. Conferences are treated by START time;
this does not guarantee avoidance of their entire duration. Older separated
statement/conference windows retain the intervening tradable gap.

Three new native MT5 runs:
1. Disabled control, byte-identical to the old original RTL ledger.
2. Entry exclusion: cancel pending orders on the first quote at/after window
   start; block submissions throughout it. Existing positions use normal exits.
3. Flat window: same, plus close all positions at the first eligible quote and
   enforce flatness on subsequent quotes during the window.

Keep the existing native whole-day-union run as a fourth benchmark. Replay full
strategy state, not delete historical trades. Continue bars and bookkeeping.
On reopening, the ordinary M30 new-bar logic resumes; no special mid-bar entry
or candle-content filter. A signal candle may include news-window prices.

Broker pending/SL processing can precede OnTick on the boundary quote. Record
boundary fills and forced exits, cancellation/flatten success, delayed actions,
and any remaining window exposure. Never label entry-only as no-exposure.
Flatness is after the first available EA callback, not retroactively before
that quote. Windows are checked every quote, including old 15-minute boundaries.

Report native net profit, trades, PF, average net trade and R, daily DD, sampled
intraday equity DD, net/equity-DD, and additional $1/trade cost sensitivity.
Compare era/year stability and whole-day versus narrow-window tradeoffs.
Use paired calendar-week bootstrap for net changes (10,000 draws, seed 20261110).
Do not reuse whole-day random-exclusion percentiles for intraday interventions;
random intraday controls would require separate full state replays.

Verify native report/ledger/stats economics, exact control, no window submissions,
every logged window action against the frozen schedule, no flat-mode surviving
exposure, and gross-equity DD against MT5. Independently replay minute OHLC paths
to verify changed fills/exits and subsequent strategy state. Add focused tests
for merged intervals, old quarter-hour boundaries, fees and event clock mapping.
No production setting changes or automatic commit. Evidence:
Reports/rtl_news_windows_20261110/; portable calendar/snapshots: data/calendars/.
