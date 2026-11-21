# RTL weekly-anchored VWAP screen

Completed 2026-11-20; [protocol](WEEKLY_ANCHOR_PROTOCOL.md) recorded before
outcomes. RTL M30, same original full-session minute HLC3 NQ volume and MNQ
valuation. Weekly VWAP resets each Monday source-date week, accumulates across
daily sessions, and continues to use the original arithmetic 20-M30-bar true
range. Skip when completed close is strictly below weekly VWAP minus A20;
first signal of a new week with only prior-week data is unknown and retained.

This is an exploratory **baseline-ledger omission**, not an MT5 replay. A real
gate alters order maintenance and may enable subsequent trades. NQ history and
other filters have already been examined repeatedly. Weekly VWAP can span a
contract roll in the continuous source and mix contract price levels; 1,297
eligible baseline trades occur in weeks containing a roll and 343 are flagged.
No parameter optimization or production change.

All numbers use one MNQ-valued contract and $1.05 per round trip. Maximum
drawdown is based on daily closes, starting at zero in each era. Session filter
is the prior ledger-omission comparison, not the separate full replay.

| Period | Policy | Trades kept | Net $ | Daily max DD $ | Longest daily DD, calendar days |
|---|---|---:|---:|---:|---:|
| 2010-15 | Baseline | 9,164 | -7,496.20 | 8,254.05 | 2,024 |
| 2010-15 | Weekly VWAP | 6,074 | -6,136.20 | 6,817.30 | 2,024 |
| 2010-15 | Session VWAP | 6,781 | -6,031.05 | 7,019.45 | 2,025 |
| 2016-19 | Baseline | 6,167 | 4,416.65 | 2,143.15 | 906 |
| 2016-19 | Weekly VWAP | 4,216 | 2,065.20 | 1,696.75 | 1,078 |
| 2016-19 | Session VWAP | 4,547 | 3,938.65 | 931.95 | 641 |
| 2020-Sep 2026 | Baseline | 10,501 | 38,399.95 | 5,781.15 | 283 |
| 2020-Sep 2026 | Weekly VWAP | 6,905 | 42,647.75 | 3,782.40 | 349 |
| 2020-Sep 2026 | Session VWAP | 7,615 | 43,435.25 | 3,084.05 | 392 |

The weekly rule skips 1,951 early and 3,596 recent trades, compared with
1,620 and 2,886 for the session rule. Weekly-skipped trades earn +$2,351.45
in 2016-19 and -$4,247.80 in 2020-26. Over 2016-26, 2,997 trades are flagged
by both, 2,550 by weekly only and 1,509 by session only. First-week unknowns
kept: 40 / 36 / 66 for the three eras; session unknowns 189 / 173 / 380.

In 2016-19, a baseline scaled to the weekly rule's holding-time fraction has
net $2,866.83 and DD $1,391.11; scaling to planned-risk fraction gives $2,465.11
and $1,196.18. Both beat the weekly omission's $2,065.20 / $1,696.75. In the
recent period same-holding is $25,054.46 / $3,771.97 and same-risk is
$21,588.08 / $3,250.11: weekly improves profit but not drawdown against either
scaling. Fractional-contract scaling is an analytical comparison, not a
one-contract implementation. 2010-15 scaling also beats weekly on both metrics.

Weekly beats baseline net in 2016, 2018, 2021, 2022 and partial 2026; it loses
profit in 2017, 2019, 2020 and 2023-25. The early 2010-15 years improve except
partial 2010. Weekly DD duration is longer in both 2016-19 and 2020-26.

Verification: 191,781 weekly VWAP observations cross-checked using an independent
scalar accumulation; all 16,668 available session-VWAP labels match the
previous verified panel. Two tests cover Monday reset, strict equality, prior-day
availability and missing A20. Results, annual breakdown, trade labels, input and
output hashes: `Reports/rtl_weekly_vwap_20261120/`. Reproduce with
`python/analyze_rtl_weekly_vwap.py`; tests `python/test_rtl_weekly_vwap.py`.
