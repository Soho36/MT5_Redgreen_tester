# RTL profits within flagged episodes

2026-10-24. Descriptive follow-up to [price structure](RESULTS.md), under the
[frozen episode protocol](EPISODE_PROTOCOL.md). RTL only; no strategy changes.

The M30 flags mix costly failed moves with profitable upward excursions, but a
post-hoc control (section 5) shows unflagged trades split the same way: for a
long 1R trade, contained paths lose and upper escapes win almost by definition.
Most winning trades enter while the original flag is still active, so waiting
for a flag to clear would miss most of these profits. Trades that finish after
the episode clears are profitable, but a winning move itself tends to clear the
flag (section 2), so this is not evidence for a restart rule. Episode age, the
only timing measure known at submission, does not repeat between eras. This
attribution supports no timing hypothesis.

## Scope and interpretation

Use the same uncapped RTL M30/RR1 ledger, one MNQ-valued contract ($2/point), $1.05
per-trade costs, and 16,668 eligible trades in 2016-19 / 2020-September 2026.
The incomplete October 1 tester trade remains excluded. The four existing flags
and their pre-2016 thresholds are unchanged: daily low efficiency/high overlap,
M30 low efficiency/high overlap, M30 high overlap/high wick fraction, and the
M30 intersection of all three. Flags overlap; their profits cannot be added.

The primary lookback is 20 completed observations. Fixed 10/40 neighbors are
reported without selecting a winner. A flagged episode is a consecutive run of
true feature observations, including observations without trades. It is not a
claim that the underlying market regime begins or ends at that boundary.

Each trade is labelled at actual order submission. Its range is the high and low
of the last n completed candles, frozen then. The recorded tester bid/exit
envelope is reconstructed from saved MFE/MAE and actual fill, including realized
gross exit. Extrema have no timestamps: an excursion above the range is not proof
of a sustained breakout, nor does it establish whether crossing occurred before
or after a flag cleared. Touching a boundary remains inside. Fill/exit prices and
flag states are reported separately.

## 1. Where the net dollars came from

Primary M30 high-overlap/high-wick flag, 20 bars:

| Realized trade envelope | Trades, 2016-19 | Net $, 2016-19 | Trades, 2020-Sep 2026 | Net $, 2020-Sep 2026 |
|---|---:|---:|---:|---:|
| Stayed inside the frozen range | 816 | -4,906.80 | 1,334 | -26,777.20 |
| Exceeded its upper boundary only | 389 | +6,041.55 | 732 | +37,677.40 |
| All flagged trades | 1,205 | +1,134.75 | 2,066 | +10,900.20 |

The recent contained group still has $31,080.55 of winning-trade dollars, against
$57,857.75 of losses. The upper-excursion group has $53,220.55 of winning dollars,
against $15,543.15 of losses. Thus 63.1% of winning dollars come from upper
excursions; containment does not mean every trade loses. Mean net R per trade is
-0.3000 versus +0.8435, respectively. In 2016-19 those means are -0.3804 / +0.6888.

The same net signs hold in all 18 M30 flag/window/era combinations: contained
negative, upper-excursion positive. The broad wick and main chop flags remain
net profitable in both eras at every tested window. The strict triple flag is
negative at 10 bars in 2016-19 and positive in its other five combinations.

This split is partly mechanical. In the recent broad-wick/20 group, 36.3% of all
trades have less than 1R of room from requested entry to the old range high;
among trades that eventually exceed that high, 75.3% have less than 1R of room.
For those entries, reaching the planned 1R profit threshold requires exceeding
the old high, subject to actual fill differences. Sorting by the later excursion
therefore sorts partly by realized success. It cannot be turned into a live
"take only the trades that escape" filter. Section 5 shows unflagged trades
with the same signs in every M30 combination, so the split is not chop-specific.

Daily results differ because an intraday trade usually stays inside a multi-day
range. At 20 days, contained trades contribute -$346.80 / -$2,291.90, while all
flagged trades contribute -$19.80 / +$1,213.75. Yet contained trades account for
82.7% / 87.2% of winning dollars. Daily containment turns positive in the recent
era at both 10 and 40 days, so the M30 pattern should not be generalized to daily
structure. Daily outside-range cells have only 18-40 trades at the primary window.

## 2. Entries precede clearance; profitable exits often follow it

Primary broad-wick/20, 2020-September 2026:

| Event and state | Trades | Net $ | Share of winning dollars |
|---|---:|---:|---:|
| Fill: original episode still active | 1,965 | +11,104.75 | 95.0% |
| Fill: unflagged | 97 | -656.35 | 4.5% |
| Fill: a later episode | 4 | +451.80 | 0.6% |
| Exit: original episode still active | 1,259 | -8,996.95 | 46.2% |
| Exit: unflagged | 630 | +17,573.50 | 44.9% |
| Exit: a later episode | 177 | +2,323.65 | 8.9% |

Fill and exit are separate partitions of the same 2,066 trades; do not add the
two blocks. A later episode means the original flag cleared and subsequently
returned. Rounded shares can sum to 100.1%.

The earlier era has the same broad-wick pattern: 94.0% of winning dollars enter
within the original episode. Trades exiting in that episode net -$2,978.65;
those exiting after it clears net +$4,113.40. All three M30 flags have negative
same-episode-exit dollars and positive after-original-episode-exit dollars at
20 bars in both eras.

Thus the retained profit is not explained mainly by pending orders that fill
after the flag has already disappeared. Entries commonly precede clearance.
Clearance is not necessary for profit: among recent broad-wick/20 trades,
389 upper-excursion trades exit within the original episode and earn +$15,713.55.
The other 870 same-episode exits are contained and lose $24,710.50. Their combined
loss does not mean that every trade needs a cleared flag to succeed.
Waiting for clearance may miss part of a successful move, but this attribution
does not quantify a delayed-entry strategy: that needs a new rule and full
replay. Exit-state grouping itself uses future information and is not an entry
decision. It is also partly reverse causation: the flag is computed from the
bars the trade lives through, and a strong upward move makes larger bodies, less
overlap and higher efficiency, which can clear the flag. Longer trades are also
more likely to outlive episodes that usually last one or two bars. Positive
after-clearance exits are expected even if the flag had no effect on outcomes.
Daily fill/exit flags remain in the same episode because both events
are intraday and daily labels update only once per day.

## 3. Late in hindsight is different from old in real time

For episodes with at least three observations, early/middle/late divides the
eventual episode length into thirds. Length-1/2 episodes are kept separate.
These phases are unknowable at submission and cannot be used to select trades.
Because a winning move can clear the flag, "late" partly means "shortly before
a move", so a late-phase gain is expected from hindsight alone.

Broad-wick/20 submission phase:

| Retrospective phase | Trades, 2016-19 | Net $, 2016-19 | Trades, 2020-Sep 2026 | Net $, 2020-Sep 2026 | Recent mean net R |
|---|---:|---:|---:|---:|---:|
| Early | 332 | -1,632.10 | 579 | -5,069.95 | -0.0834 |
| Middle | 355 | -212.75 | 594 | +2,543.30 | +0.0855 |
| Late | 340 | +934.00 | 639 | +12,146.55 | +0.2687 |
| Episode only 1-2 observations | 178 | +2,045.60 | 254 | +1,280.30 | +0.1692 |

There is a historical association with late submissions, not an "only late wins"
result. The primary main M30 chop flag also has early losses and late gains in
both eras, but short episodes supply +$1,254.45 / +$6,082.50. The triple flag's
early net dollars change sign between eras. No universal phase rule follows.

Elapsed episode age is known at submission. For broad-wick/20, net dollars by
age bins 1 / 2-3 / 4-8 / 9+ observations are:

| Era | Age 1 | Age 2-3 | Age 4-8 | Age 9+ |
|---|---:|---:|---:|---:|
| 2016-19 | +1,159.80 | +93.55 | -216.60 | +98.00 |
| 2020-Sep 2026 | -1,919.20 | -1,268.40 | +8,417.85 | +5,669.95 |

The age pattern does not repeat cleanly. Waiting a fixed number of observations
is not supported simply by the retrospective early/late pattern. Some dollar
and mean-R signs also differ because dollar risk per trade varies; all means,
counts and coverage are retained in the calculated tables.

At 20 bars the recent broad-wick inventory contains 3,251 episodes, of which
1,312 contain eligible trades and 1,939 contain none. Median length across all
episodes is two observed bars, versus seven among episodes with trades. For the
main M30 chop flag, 4,078 episodes include 1,086 with trades; 67.1% last just one
or two observations. A 20-bar lookback does not mean a flag stays on for 20 bars.
Threshold crossings can produce brief episodes within broader visual congestion.
A future regime flag would need hysteresis (separate on/off levels) or a minimum
duration before its episodes could be read as regimes.

## 4. Sensitivity to the twenty-candle choice

Broad M30 wick/overlap, with each window's previously frozen calibration:

| Lookback | Trades, 2016-19 / recent | Net $, 2016-19 | Net $, recent | Recent contained net $ | Recent winning dollars entering in original episode |
|---|---:|---:|---:|---:|---:|
| 10 | 979 / 1,753 | +551.55 | +13,729.85 | -26,819.80 | 91.1% |
| 20 | 1,205 / 2,066 | +1,134.75 | +10,900.20 | -26,777.20 | 95.0% |
| 40 | 1,376 / 2,391 | +1,147.70 | +11,910.45 | -19,634.60 | 95.6% |

Yes, window length matters: it changes which submissions are flagged, episode
boundaries, and the reference range. The recent contained share of winning
dollars rises from 22.4% to 36.9% to 54.4%, partly because a longer range makes
containment easier. These are not identical trades with only a different timer.
Nevertheless, all three versions sacrifice positive net dollars if their
selected historical trades are omitted. Twenty is not the sole cause of that
failure. No best window is selected from these outcomes.

For the main M30 chop flag, recent net dollars are +$9,607.50 / +$9,089.30 /
+$3,895.35 at 10/20/40. Daily values are +$6,080.15 / +$1,213.75 / +$4,417.15;
earlier daily net changes sign across windows. All four flags and both eras
appear in [calculated tables](../../../Reports/rtl_flagged_episodes_20261024/report_tables.md).

## 5. Control added after results: unflagged trades

Not part of the frozen protocol; added after reviewing sections 1-3. The same
as-of join, frozen n-candle range and path groups are applied to every valid
trade, flagged or not. Flagged rows reproduce section 1 exactly. Twenty bars:

| Flag | Era | Trades, flagged / unflagged | Above range only, flagged / unflagged | Contained net R, flagged / unflagged | Above-range net R, flagged / unflagged |
|---|---|---:|---:|---:|---:|
| Broad wick | 2016-19 | 1,205 / 4,962 | 32.3% / 29.3% | -0.380 / -0.332 | +0.689 / +0.767 |
| Broad wick | 2020-Sep 2026 | 2,066 / 8,435 | 35.4% / 29.0% | -0.300 / -0.241 | +0.844 / +0.706 |
| Main chop | 2016-19 | 748 / 5,419 | 35.4% / 29.2% | -0.343 / -0.341 | +0.780 / +0.746 |
| Main chop | 2020-Sep 2026 | 1,214 / 9,287 | 37.2% / 29.4% | -0.385 / -0.237 | +0.918 / +0.708 |

In all 18 M30 flag/window/era combinations, unflagged contained trades also lose
(-0.15 to -0.44 R per trade) and unflagged above-range trades also win (+0.65 to
+0.85 R). The section 1 split describes RTL trades generally, not a failure that
belongs to chop. Flagged trades escape above their range somewhat more often at
10 and 20 bars, not consistently at 40; their narrower ranges leave less room
(36-38% versus 30-32% under 1R at 20 bars). Within each path group, flagged results
are usually more extreme: contained trades lose more, escapes earn more.

This control has no separate independent verifier. It reconciles every flagged
path-group count and net-dollar total to the verified attribution. Program:
`python/control_rtl_flagged_paths.py`; output:
`Reports/rtl_flagged_paths_control_20261024/path_control.csv`, all four flags,
three windows, both eras.

## MA agreement: a separate proposed study

The user's idea can describe directional agreement across horizons. It cannot
remove the delay inherent in averages of past prices. For a simple MA's
one-observation slope, the exact identity is:

`SMA_L(t) - SMA_L(t-1) = (C[t] - C[t-L]) / L`.

Thus slope-sign agreement is agreement among returns over different horizons,
not independent confirmations. A 5,10,...,200 grid gives 31 of its 40 votes to
lengths of at least 50 bars. A fixed spread such as 5,10,20,40,80,160,200, or equal
weight per horizon band, would avoid accidentally putting most weight on the
slower horizons. These are proposals, not tested settings. The
[StockCharts MA definition](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential)
provides the SMA formula and explains the greater lag of longer averages.

A separate protocol should distinguish clear up, clear down and mixed/flat,
define slope strength/deadbands in advance, and keep short-down/long-up pullbacks
distinct from short-up/long-down recoveries. A clear downtrend has different
implications for this long-only strategy than a clear uptrend; "clear direction"
alone is not sufficient. Mixed horizons may identify congestion, but can also
identify the start of a profitable turn or an ordinary RTL pullback.

The next useful comparison would measure gains retained and missed around those
transitions, alongside loss reduction, both eras and fixed sensitivities. It
should use only completed information available at submission, then replay a
surviving rule with explicit restart and pending-order treatment. No MA test or
new MA threshold was selected during this attribution.

## Verification and artifacts

The original price-structure data/thresholds and baseline economics reconcile
exactly. This attribution produces 23,569 rows across 12 overlapping
flag/window specifications, 24 era reconciliations, 678 summary rows, 68,203
full-history episodes and 47,663 era-episode rows. Episode inventories include
zero-trade runs. These are not 23,569 independent trades.

Independent verification **passed** for all rows above after literal episode/range
reconstruction, raw trade joins, extrema conversion, partition totals and
provenance checks. All sixteen focused tests **passed**. They cover boundaries,
invalid gaps, censoring, strict range touches, no zero-clamping of excursions,
zero-trade episodes and future-data perturbations.

- [Audit and provenance](../../../Reports/rtl_flagged_episodes_20261024/provenance.json)
- [Independent verification](../../../Reports/rtl_flagged_episodes_20261024/independent_verification.json)
- [Full calculated tables](../../../Reports/rtl_flagged_episodes_20261024/report_tables.md)
- [Winning-dollar attribution chart](../../../Reports/rtl_flagged_episodes_20261024/profit_location.png)
- [Analyzer](../../../python/analyze_rtl_flagged_episodes.py), [independent verifier](../../../python/verify_rtl_flagged_episodes.py), [tests](../../../python/test_rtl_flagged_episodes.py), [report generator](../../../python/report_rtl_flagged_episodes.py)
- [Unflagged path control](../../../python/control_rtl_flagged_paths.py) (post-hoc, section 5)

The figure separates winning dollars from losses; it is not a net-return chart.
All results remain descriptive on repeatedly inspected historical data, using
modelled tester execution. The broad wick flag is an average condition, not an
exhaustive test of the user's extreme visual example. No trading filter, EA
change, causal proof, fresh forward validation or delayed-entry replay is claimed.
