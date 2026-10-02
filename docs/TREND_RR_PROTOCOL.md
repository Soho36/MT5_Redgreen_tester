# RTL trend-conditioned RR — frozen 2026-10-02

User supplied the trend-conditioned RR proposal and then clarified: use the
existing RTL baseline tested so far. Accordingly this is RTL only, keeping
the M30-close-qualified **market exit**, MaxRedRun=3, all existing valid windows,
one MNQ-priced contract, low-of-signal stop, calendar and session flattening.
No GG, sell-limit exit, partial exit, breakeven change or new entry filter.
No live/paper forward test. Historical expanding annual walk-forward is included.

Six bull/neutral/bear mappings are frozen: fixed 1/1/1; mild 1.25/1/.75;
strong 1.5/1/.75; bull-only 1.5/1/1; bear-only 1/1/.75;
reversed .75/1/1.5. Bull requires previous completed daily close > SMA200
and SMAfast > SMA200; bear requires both comparisons <; otherwise neutral.
Fast periods are 50 (primary), 40 and 60 (sensitivity only). MAs include only
completed daily closes, including the previous day, on the existing unadjusted
continuous series and its established session clock. No current-day data.

Each trade freezes the entry day's regime and RR until exit. Initial entry
and risk remain the actual buy-stop fill and initial protective stop.
Target qualification stays `completed M30 close >= entry + risk * assigned RR`.
No intrabar target touch exit. Entry timing can change after exits change, so
every adaptive mapping is rerun in MT5 rather than reshuffling baseline trades.

Use one-minute OHLC only. Data starts 2010-06-07; before 200 previous daily
bars exist, preserve entries at 1R and label them `warmup`, not neutral. Include
these shared baseline trades in the initial available 2010–2014 training period;
do not count warmup toward the 75-trades-per-regime requirement. Full test years
are 2015–2025. Also report the usual baseline periods, 2016–2019 and 2020 through
2026-07-14; partial 2026 is excluded only from annual walk-forward scoring.
Earlier market hours differ; retain the
existing early-close calendar rather than silently dropping those years.

For each test year, select baseline/mild/strong using all earlier available
years' net profit / maximum closed-trade dollar drawdown. Require at least 75
trades in bull, neutral and bear for an adaptive candidate; otherwise it is
ineligible. Baseline is the fallback. Resolve exact ties in baseline, mild,
strong order. Freeze the chosen mapping for the whole next year. Independently
repeat the selector for each MA sensitivity; never select between MA lengths.
Only test-year trades enter stitched results. Prior exploration means these
years are chronological holdouts for the selector, not globally untouched data.

Commission is $1.05 per completed contract, matching our baseline comparisons.
Slippage has not been measured: show explicitly assumed additional $1 and $2
per trade cost stresses alongside the primary commission-only result. This
allowance does not change fill timing or pretend to validate queue execution.
Freeze selection under the baseline cost, then stress the same selections.

Assess: stitched net/DD >= 1.10 times fixed baseline; net >= 90% baseline;
DD no larger; annual net/DD improvement in >=60% of test years (also report
annual net improvements); both neighboring lengths improve net/DD; primary
net/DD exceeds reversed by >=10% (a declared interpretation of "clearly");
improvement survives removing 2020–2021 and, separately, the single largest
positive contribution year; extra-$2 stress still improves net/DD. Do not tune
these definitions after results. Bear-only is diagnostic, never selectable.

Report trade count, net, average trade, PF, balance DD and duration, profitable
months/years including zero-trade calendar periods, worst month/quarter/year,
regime results and signed share of net profit, target qualification/exit rate,
holding duration and gross profit / summed positive MFE. Include MAE/MFE in R,
signal and entry details, source contract, session window, weekday and costs in
enriched trades; retain every accepted setup and each M30 target check. Sell-
limit submission/fill rates and RR/GG simultaneous failure rates are not
applicable to the user's RTL-only market-exit scope.

Audit trade counts/PnL against MT5; independently rebuild lagged daily labels
from the minute source; verify all target checks and assigned RRs; compare
overlapping baseline history with established controls; ensure no cross-date
positions. Unit-test leakage prevention, mapping and chronological selection.
