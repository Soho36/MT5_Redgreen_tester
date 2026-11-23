# Manual MT5 tests

Select `CodexResearch\News_first_minute_research` in Strategy Tester, symbol
`MNQcontDTBNT20102026_2`, period M1, and the 1-minute OHLC model used in the study.
The EA is tester-only and expects the original research clock.

In **Inputs**, select **TradeDirection**:

| Value | Selection | Behavior |
|---|---|---|
| 0 | Both longs and shorts | Default; original behavior |
| 1 | Longs only | Green news candles can enter; red candles are skipped |
| 2 | Shorts only | Red news candles can enter; green candles are skipped |

The switch filters entries; it never reverses a signal. TP, SL, sizing, calendar
and session exits stay unchanged. Excluded signals appear as `direction_disabled`
in the decision log.

`NewsMask` independently selects releases: 3 = CPI and payrolls, 1 = CPI only,
2 = payrolls only. Use a different `RunTag` for each manual test if you want to
keep all exported logs. The native report is gross of the study's external
$1.05 round-trip fee.

Compile/install the current version with `python/install_news_first_minute.py`.
Add `--verify` to run three 2024 native checks against the original study's
corresponding trades; checks refuse to interrupt an existing terminal or
overwrite prior verification outputs. The original study runner intentionally
uses its frozen source and should not be used to install this newer version.

Updated package: `Reports/news_first_minute_direction_20261122/News_first_minute_EA.zip`.
