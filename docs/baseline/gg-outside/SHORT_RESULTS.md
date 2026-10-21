# Green outside bar: sell-stop mirror

2026-10-20. Follow-up to [the GG outside-bar long screen](RESULTS.md), prompted by the user's request to sell under the same green outside candle. Exploratory MT5 screen; no short strategy is adopted.

This study uses a **green** outside candle. The user's corrected [red outside-candle short test](RED_SHORT_RESULTS.md) is documented separately.

## Rule and runs

Use exactly the long study's closed green signal and full high/low outside filter. The short EA places a **sell stop at the signal low**, a **stop loss at its high**, and exits after the first M30 bar that closes at or below entry minus 1R. Session windows, flattening, early-close calendar, RR 1, one contract, and one-minute OHLC model are unchanged. A rejected green signal cancels the previous pending sell stop, matching the long filter's pending-order treatment. The optional trailing stop is mirrored for shorts and stays disabled in this study.

The 13 runs use the same MNQ-priced continuous NQ symbol and 2016-01-01 to 2026-10-15 tester settings as the long screen; the last available trade date is 2026-10-01. One run has the outside filter off (green-candle short control), and 12 use the same lookbacks and size thresholds as the long study: n = 1, 3, 5, 10 and (range ratio, each-side overhang fraction) = (1.00, 0), (1.25, 0), (1.25, 0.10). Net results subtract $1.05 per completed trade. Code: [prepare_gg_outside_short.py](../../../python/prepare_gg_outside_short.py); reconciliation: [analyze_gg_outside_short.py](../../../python/analyze_gg_outside_short.py). The saved EA, INIs, ledgers, MT5 reports, logs and output hashes are in `Reports/gg_outside_short_20261020/`.

The short EA is installed as `CodexBaselineResearch\GG_outside_short` for manual MT5 tests. Its `UseOutsideFilter` input defaults to **true**; change the Value column to false only to test the unfiltered short control.

## MT5 results

| Setting (n / range ratio / overhang) | 2016–19 trades | 2016–19 net $ | 2016–19 PF | 2020–26 trades | 2020–26 net $ | 2020–26 PF | 2020–26 DD $ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Green-candle short control | 6,457 | −5,492 | 0.927 | 11,176 | −3,228 | 0.993 | 21,096 |
| 1 / 1.00 / 0 | 580 | −370 | 0.960 | 1,208 | 716 | 1.011 | 4,936 |
| 1 / 1.25 / 0 | 525 | −164 | 0.980 | 1,070 | −3,084 | 0.950 | 5,932 |
| 1 / 1.25 / 0.10 | 418 | 392 | 1.059 | 777 | −3,919 | 0.917 | 5,902 |
| 3 / 1.00 / 0 | 90 | −236 | 0.882 | 190 | 2,530 | 1.169 | 2,047 |
| 3 / 1.25 / 0 | 83 | −431 | 0.771 | 175 | 1,280 | 1.088 | 2,031 |
| 3 / 1.25 / 0.10 | 62 | −93 | 0.929 | 125 | −6 | 0.999 | 2,119 |
| 5 / 1.00 / 0 | 38 | −111 | 0.878 | 94 | 73 | 1.008 | 2,184 |
| 5 / 1.25 / 0 | 37 | −135 | 0.851 | 89 | −490 | 0.947 | 2,184 |
| 5 / 1.25 / 0.10 | 24 | −24 | 0.960 | 65 | −29 | 0.995 | 2,026 |
| 10 / 1.00 / 0 | 12 | 83 | 1.363 | 43 | −476 | 0.907 | 1,830 |
| 10 / 1.25 / 0 | 12 | 83 | 1.363 | 42 | −1,125 | 0.779 | 1,830 |
| 10 / 1.25 / 0.10 | 11 | 97 | 1.452 | 30 | −615 | 0.823 | 1,743 |

The strict n=3 short is the strongest recent cell: +$2,530, PF 1.169 on 190 fills, versus −$2,591 for the matched n=3 GG long. But it lost in 2016–19. In 2020–26 it wins 4 of 7 years; 2022 alone contributes +$2,268, about 90% of the recent total. Excluding 2022 leaves +$262. Requiring 1.25 times the widest prior candle cuts recent profit to +$1,280; also requiring a 10% overhang on each side reduces it to roughly break-even. The n=1 short is near break-even recently and loses earlier. Larger lookbacks have too few fills and mostly lose recently. None gives a stable result across the two periods and neighboring definitions.

## Verification and limits

All 13 short ledgers reconcile trade count and gross profit with MT5's exported totals. The EA compiles with zero errors and warnings. In the MT5 HTML order records, all 45,092 control sell-stop orders and all 1,194 strict-n=3 sell-stop orders have stop losses above entry; neither report has a buy-stop order. The short's bar-close exit buys to cover, and the optional trailing code is reversed consistently.

The full history has been examined in previous project work, so 2020–26 is a comparison period, not a fresh untouched holdout for this newly proposed short. These are one-minute OHLC simulated fills, with the execution-mode sensitivity documented in [project status](../../STATUS.md). The strict n=3 result is a research lead only; it does not justify live short trading or replacing the GG baseline.
