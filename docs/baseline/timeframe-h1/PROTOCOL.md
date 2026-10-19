# Matched H1 / M30 protocol

Fixed before inspecting the results, 2026-10-15. User request: RTL and GG,
H1 versus M30, RR 0.5 and 1, no MaxRedRun filter.

Eight runs use the dedicated current RTL/GG runband sources, one contract,
MNQcontDTBNT20102026_2, 1-minute OHLC, full 2010-06-07 through available data
ending 2026-10-01 (tester ToDate 2026-10-15). MaxRedRun=0, MinRedRun=1,
MinLocation=0, range/trailing filters disabled. Existing entry windows,
flatten fallback and early-close calendar stay enabled. Costs $1.05/trade.
Primary comparisons: 2016-19 and 2020-26; 2010-15 reference only.

H1 would skip the 23:30 cutoff because the original EA gates flatten on new
bars. Research copies check the same calendar cutoff on ticks for periods
longer than M30, leaving signals and RR exits on the selected chart period.
M30 follows the unchanged code path. No installed production sources change.

Verify all ledgers against MT5 counts/profit and flags, hashes and no overnight
positions. Verify M30 RR=1 against existing uncapped RTL/GG ledgers. Report
net dollars, PF, closed-trade DD, average R, trade frequency, risk and holding
time; annual differences and descriptive paired exit-day bootstrap intervals.
No selection/adoption rule: the report is exploratory.
