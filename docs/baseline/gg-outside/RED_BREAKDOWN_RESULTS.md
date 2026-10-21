# Red breakdown short: new-high requirement comparison

2026-10-21. The marked chart shows a large **red** candle that breaks recent lows, but its high can remain below a preceding high. This study tests that chart-matching definition alongside the stricter [red outside-bar test](RED_SHORT_RESULTS.md), which also requires a new high. The earlier [green-candle short](SHORT_RESULTS.md) is a different trade.

## Rules and data

The last closed M30 candle is red. Its **full high-to-low range**, including wicks, must be at least r times W, where W is the widest individual candle among the preceding n closed candles. Its low must be below every low in that window, by at least b times W. A strict outside bar additionally has a high above every preceding high, by at least o times W. At b = o = 0, the low must strictly break the prior lows in both versions. The strict version additionally needs a strictly higher high. We tested n = 1, 3, 5, 10 and (r, b) = (1.00, 0), (1.25, 0), (1.25, 0.10). The strict study uses the corresponding (r, o) grid; its 0.10 setting requires that extension on **both** sides.

The GG-style short sells on a stop at the red signal candle's low, with stop loss at its high and the first M30 close at or below entry minus 1R as the target exit. Other order lifetime, session, flattening, and early-close rules match the strict red outside study. The unfiltered control sells below every qualifying red candle. Data: MNQ-priced continuous NQ, M30 signals with one-minute OHLC MT5 execution, one contract, 2016-01-01 through available data ending 2026-10-01. Net dollars subtract $1.05 per completed trade.

[prepare_gg_red_breakdown_short.py](../../../python/prepare_gg_red_breakdown_short.py) generates the isolated EA and 13 MT5 jobs. [analyze_gg_red_breakdown_short.py](../../../python/analyze_gg_red_breakdown_short.py) reconciles the output. The INIs, source, reports, ledgers, logs, and completion hashes are in `Reports/gg_red_breakdown_short_20261021/`. For manual testing, select `CodexBaselineResearch\GG_red_breakdown_short`. Its filter defaults to **on** with n=3, range ratio=1.25, low-break fraction=0. The strict new-high EA is `CodexBaselineResearch\GG_red_outside_short`, also filter-on by default.

## Chart-matching breakdown, without a new-high requirement

| Setting (n / range ratio / low break) | 2016–19 trades | 2016–19 net $ | 2016–19 PF | 2020–26 trades | 2020–26 net $ | 2020–26 PF | 2020–26 DD $ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Red-candle short control | 6,677 | −13,609 | 0.845 | 11,363 | −18,096 | 0.964 | 23,214 |
| 1 / 1.00 / 0 | 3,779 | −5,012 | 0.912 | 6,450 | −8,321 | 0.976 | 13,180 |
| 1 / 1.25 / 0 | 3,078 | −6,249 | 0.875 | 5,217 | −6,599 | 0.977 | 8,945 |
| 1 / 1.25 / 0.10 | 3,036 | −6,306 | 0.872 | 5,135 | −5,736 | 0.980 | 8,056 |
| 3 / 1.00 / 0 | 2,101 | −4,517 | 0.882 | 3,510 | −15,081 | 0.933 | 17,120 |
| 3 / 1.25 / 0 | 1,574 | −3,412 | 0.890 | 2,592 | −6,192 | 0.965 | 8,590 |
| 3 / 1.25 / 0.10 | 1,543 | −3,942 | 0.871 | 2,526 | −6,281 | 0.964 | 9,075 |
| 5 / 1.00 / 0 | 1,545 | −5,396 | 0.831 | 2,524 | −10,468 | 0.941 | 11,814 |
| 5 / 1.25 / 0 | 1,099 | −3,677 | 0.850 | 1,824 | −8,192 | 0.941 | 9,426 |
| 5 / 1.25 / 0.10 | 1,078 | −3,669 | 0.849 | 1,782 | −8,475 | 0.938 | 9,650 |
| 10 / 1.00 / 0 | 861 | −3,630 | 0.836 | 1,483 | −9,522 | 0.924 | 11,453 |
| 10 / 1.25 / 0 | 624 | −2,748 | 0.842 | 1,057 | −3,631 | 0.962 | 6,168 |
| 10 / 1.25 / 0.10 | 604 | −2,484 | 0.852 | 1,025 | −4,603 | 0.951 | 7,177 |

**All 12 breakdown settings lose net dollars in both periods.** The strongest recent profit factor is still below 1 (0.980). A few settings have slightly positive average R when each trade is normalized by its own risk, yet their net dollars are negative; position size is fixed, so those larger-dollar losses matter.

## What changes when a new high is required?

This table holds r = 1.25 and the low-break minimum at zero in both variants. The strict version adds a high above the preceding n highs; it has no additional upper-extension minimum. These are separate full MT5 runs, so differing pending-order histories can also affect trades.

| n | No new high: 2016–19 trades / net $ / PF | New high: 2016–19 trades / net $ / PF | No new high: 2020–26 trades / net $ / PF | New high: 2020–26 trades / net $ / PF |
|---:|---:|---:|---:|---:|
| 1 | 3,078 / −6,249 / 0.875 | 1,202 / −2,773 / 0.863 | 5,217 / −6,599 / 0.977 | 2,350 / −8,049 / 0.942 |
| 3 | 1,574 / −3,412 / 0.890 | 278 / −1,155 / 0.829 | 2,592 / −6,192 / 0.965 | 513 / −10,635 / 0.774 |
| 5 | 1,099 / −3,677 / 0.850 | 132 / −626 / 0.838 | 1,824 / −8,192 / 0.941 | 254 / −7,953 / 0.697 |
| 10 | 624 / −2,748 / 0.842 | 52 / −742 / 0.617 | 1,057 / −3,631 / 0.962 | 111 / −5,741 / 0.582 |

The new-high condition sharply reduces trade count and worsens recent profit factor at every lookback in this comparison. The complete 12-setting new-high grid, including both-side 0.10 overhang, is in [RED_SHORT_RESULTS.md](RED_SHORT_RESULTS.md). Its 12 settings also lose in both periods.

## Verification and decision

The no-new-high control CSV is byte for byte identical to the strict study's red-candle control. All 13 breakdown ledgers reconcile trade counts and gross profit with MT5 totals; every EA run compiled with zero errors and warnings. The generated source compares the closed signal only with preceding closed bars and uses its low for sell-stop entry and high for stop loss. The MT5 HTML orders show 24,725 control and 6,169 n=3/r=1.25 breakdown sell stops, all with stops above entry and no buy stops.

Neither red short filter passes this historical screen, so no rule is adopted. The grid was motivated by visible chart examples and earlier work on these data; it is exploratory rather than an untouched validation. The one-minute OHLC fill model remains a limitation.
