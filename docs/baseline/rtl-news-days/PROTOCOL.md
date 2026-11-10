# RTL: exclude scheduled major US news days

Frozen 2026-11-10 before inspecting news-conditioned strategy outcomes.

The user's broader definition is Investing.com's three-star monetary-policy,
inflation and labour-market news. Initially cover only CPI, Employment Situation
(payrolls/unemployment/wages as one release), and scheduled FOMC decisions.
This is not the entire three-star calendar. No sentiment, actual/forecast values,
speeches, minutes or emergency announcements.

Use official BLS and Fed archives; save source snapshots, URLs, hashes and CSV.
Parse publication dates, not reference months; FOMC decision day, not both days.
Audit missing/duplicate releases, shutdown delays and unscheduled meetings.
Archives are not complete point-in-time schedules: flag unresolved advance
knowledge and report sensitivity excluding affected years.

RTL M30 RR=1, MaxRedRun=0, MinLocation=0, original entry windows, VWAP off,
one contract at $2/point, $1.05 round-trip cost, existing daily/early-close flatten.
Compare control, skip CPI, skip payrolls, skip scheduled FOMC, skip their union.
No production changes or post-result event-set optimization.

Skip the whole research session dated with the announcement's US date. Research
clock is Chicago+8 (New York+7); these releases have the same research date.
Block submissions/pending fills. Verify flat session boundaries; explicitly
model any carried exposure. Continue bars/bookkeeping on skipped sessions.

Primary: 2016-19, 2020-September 2026, pooled 2016-September 2026.
2010-15 and annual tables secondary; exclude incomplete October 1 onward.
Historical exploratory comparison, not untouched out-of-sample confirmation.

Report sessions, removed sessions/trades, net profit, PF, average net trade/R,
daily-close DD, sampled intraday equity DD and net/equity-DD. Screen using the
verified native baseline ledger and equity path. Reconstruct whole-session
exclusion only after proving flat boundaries and session independence. Validate
promising filters with a full replay and matched disabled control; distinguish
reconstructed screening from independent replay confirmation.

10,000 random session exclusions, seed 20261110, preserve counts within each
year/weekday, including zero-trade sessions. Compare profit and DD with random
exclusion. Use 10,000 paired calendar-week bootstrap draws for filter-minus-control
daily P&L uncertainty. Four prespecified filters, not selection-adjusted proof.
Keep costs/session calendar fixed and examine annual concentration.

Evidence: Reports/rtl_news_days_20261110/. Calendar: data/calendars/.
Scripts: python/. Results and compact tables alongside this protocol.
