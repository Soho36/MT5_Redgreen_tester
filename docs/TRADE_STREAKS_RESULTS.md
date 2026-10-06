# Q24: trade-result streaks — 2026-10-07

**No predictive or daily-stop rule passes the frozen screen.** Five same-session wins are too rare to assess; three losses do not make the next win more likely. Stops after losses can reduce historical drawdown, but yearly benefits are inconsistent. No EA or sizing change.

[Protocol](TRADE_STREAKS_PROTOCOL.md). Current RTL baseline, 14,968 trades (5,697 earlier; 9,271 recent), one contract, net of $1.05 per trade. 2026 ends July 13. One-minute OHLC; all history previously examined.

## Next trade after a known result sequence

These are **exact preceding streaks**, known at actual order submission. Daily state resets at the synthetic session boundary. The last trade that establishes the streak is excluded from the next-trade result. Zero net breaks a streak.

| Period | Trades | Win rate | Mean net R | Net dollars |
| --- | --- | --- | --- | --- |
| 2016–19 | 5697 | 43.4% | -0.004 | $6,485.15 |
| 2020–Jul 2026 | 9271 | 43.0% | +0.060 | $37,980.95 |

**Within the session (primary)**

| Period | Preceding streak | Next trades | Win rate | Mean R | R vs others | 95% week interval |
| --- | --- | --- | --- | --- | --- | --- |
| 2016–19 | 5 wins | 2 | 100.0% | +0.354 | +0.358 | [+0.081, +0.637] |
| 2016–19 | 3 losses | 313 | 41.9% | -0.077 | -0.077 | [-0.223, +0.079] |
| 2020–Jul 2026 | 5 wins | 13 | 53.8% | +0.318 | +0.258 | [-0.357, +0.885] |
| 2020–Jul 2026 | 3 losses | 504 | 41.1% | +0.001 | -0.062 | [-0.169, +0.046] |

**Across consecutive trades, including different sessions (secondary)**

| Period | Preceding streak | Next trades | Win rate | Mean R | R vs others | 95% week interval |
| --- | --- | --- | --- | --- | --- | --- |
| 2016–19 | 5 wins | 41 | 41.5% | -0.144 | -0.141 | [-0.513, +0.265] |
| 2016–19 | 3 losses | 442 | 44.3% | -0.024 | -0.022 | [-0.139, +0.101] |
| 2020–Jul 2026 | 5 wins | 77 | 37.7% | -0.042 | -0.103 | [-0.370, +0.176] |
| 2020–Jul 2026 | 3 losses | 716 | 42.5% | +0.018 | -0.046 | [-0.139, +0.047] |

After three same-session losses, next-trade win rates are 41.9% / 41.1%, versus baseline 43.4% / 43.0%. Mean-R differences are negative in both periods, but both cluster intervals include zero. This supports neither a winner-is-due rule nor a reliable next-trade skip rule.

Only 2 / 13 trades occur after exactly five same-session wins. There are 10 / 21 sessions reaching five wins, but most have no subsequent trade. A positive earlier R interval based on two trades is sparse-sample evidence and fails the minimum-count gate. Across sessions, five-win next trades have negative mean R, but only 41 / 77 observations and intervals spanning zero.

![Exact streak outcomes](../Reports/trade_streaks_20261007/streaks.png)

Plot points require n >=20; all counts, including smaller groups, are retained in `conditional.csv`. Wilson intervals are descriptive; the lower plot uses calendar-week cluster intervals for mean R versus other next trades.

## Streaks versus shuffled sequences

2,000 shuffles within month and separately within session, recomputing streaks after each shuffle. Daily shuffles retain exactly the outcomes and dollars/R available on each trading day. Holm adjustment covers all exact-bin tests in both scopes within each period/metric/null.

Longest same-session win streaks: **6 / 7**; loss streaks: **11 / 8**. Across sessions: wins **8 / 10**, losses **14 / 17**. Longest cross-session streaks lie inside the monthly-shuffle 95% reference ranges. The earlier within-session 11-loss streak is unusual under monthly shuffling, but ordinary under daily shuffling: a bad day explains it without a sequence effect.

There is some earlier-period excess alternation: 3,418 daily runs versus 3,307–3,413 in the daily-shuffle 95% range; recent 5,472 versus 5,370–5,505 is ordinary. This does not establish predictable profitable entries.

One isolated recent group survives the adjusted permutation screen: next trade after four same-session wins, 37 observations, mean +0.657R. The earlier counterpart has 26 trades and mean -0.180R. It fails replication and sample-size gates. No exact group passes all requirements.

`streak_runs.csv` lists every observed maximal run, dollars/R and timestamps; `streak_frequency.csv` gives its length distribution. `ended_by` distinguishes an opposite result, zero, session end and period end; boundary-ended runs must not be called reversals.

## Stop for the remainder of the session

Keep the triggering trade, skip all later trades that session and resume next session. The independent sequential replay verifies these decisions. These are saved-ledger counterfactuals; adoption requires an EA/full MT5 check. Skipping only the next trade would change available entries and is not modelled.

**2016–19**

| Stop after | Trades | Net $ | DD $ | PF | Mean R | Net change $ |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 5697 | 6,485.15 | 1,435.30 | 1.106 | -0.004 | — |
| win 2 | 4525 | 5,660.25 | 1,096.00 | 1.122 | +0.003 | -824.90 |
| win 3 | 5450 | 6,064.50 | 1,576.65 | 1.104 | -0.003 | -420.65 |
| win 4 | 5657 | 6,793.65 | 1,435.30 | 1.112 | -0.003 | +308.50 |
| win 5 | 5695 | 6,468.25 | 1,435.30 | 1.105 | -0.004 | -16.90 |
| win 6 | 5697 | 6,485.15 | 1,435.30 | 1.106 | -0.004 | +0.00 |
| loss 2 | 3830 | 4,505.00 | 748.35 | 1.121 | -0.006 | -1,980.15 |
| loss 3 | 4976 | 7,433.20 | 1,177.70 | 1.145 | +0.004 | +948.05 |
| loss 4 | 5425 | 6,812.75 | 1,256.65 | 1.119 | +0.000 | +327.60 |
| loss 5 | 5587 | 6,748.65 | 1,266.70 | 1.113 | -0.004 | +263.50 |
| loss 6 | 5669 | 6,747.05 | 1,310.25 | 1.111 | -0.003 | +261.90 |

**2020–Jul 2026**

| Stop after | Trades | Net $ | DD $ | PF | Mean R | Net change $ |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 9271 | 37,980.95 | 4,847.40 | 1.107 | +0.060 | — |
| win 2 | 7385 | 30,276.75 | 4,220.45 | 1.112 | +0.064 | -7,704.20 |
| win 3 | 8777 | 37,486.65 | 4,425.90 | 1.113 | +0.063 | -494.30 |
| win 4 | 9191 | 35,503.45 | 4,847.40 | 1.101 | +0.057 | -2,477.50 |
| win 5 | 9250 | 38,141.00 | 4,847.40 | 1.108 | +0.060 | +160.05 |
| win 6 | 9265 | 38,270.75 | 4,847.40 | 1.108 | +0.060 | +289.80 |
| loss 2 | 6190 | 26,930.00 | 3,187.25 | 1.128 | +0.066 | -11,050.95 |
| loss 3 | 8105 | 34,575.75 | 3,944.90 | 1.117 | +0.063 | -3,405.20 |
| loss 4 | 8875 | 37,403.75 | 3,955.55 | 1.112 | +0.060 | -577.20 |
| loss 5 | 9156 | 37,248.20 | 4,215.60 | 1.107 | +0.059 | -732.75 |
| loss 6 | 9245 | 39,097.25 | 4,816.75 | 1.111 | +0.061 | +1,116.30 |

After five wins, stopping changes net by **-$16.90 / +$160.05**, with drawdown unchanged. Recently, 8 of 13 sessions with another trade have a losing remainder, but only 2 give back over half the positive trigger profit. Earlier, neither of the two continuing sessions loses money. Across all trigger sessions, including days with no remainder, the recent giveback rate is 2/21. One memorable giveback is insufficient to set this rule.

Stopping after three losses reduces DD by 18.0% / 18.6%, improves net/DD by 39.7% / 11.9%, but changes profit by +$948 / -$3,405 and benefits only 6/11 years. Four-loss stopping reduces DD by 12.4% / 18.4% and retains 105.1% / 98.5% of profit; dollar benefit appears in only 5/11 years. The similar four/five-loss thresholds are a possible risk-management trade-off to discuss, not a confirmed prediction or an adopted rule. Every stop threshold fails at least one fixed requirement.

## Verification and limits

Seven synthetic sequence tests pass. MT5 trade counts and gross PnL match the stats export; all 14,968 net outcomes match the established Q10 ledger. Every prior result is closed by the next actual submission, with no overlapping/cross-session positions. Independent sequential replay: **14,968 states and 20 policies, zero mismatches**, including dollar totals, omissions, mean R and drawdown. Source/output hashes are saved.

The statistical nulls assume exchangeability within their shuffle groups. Long-streak estimates are especially sparse. These historical comparisons do not demonstrate trend exhaustion, actual tick execution or future profitability. The previously documented OHLC sensitivity still applies.

Reproduce from the project root:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s python -p test_trade_streaks.py -v
.\venv\Scripts\python.exe python\analyze_trade_streaks.py
.\venv\Scripts\python.exe python\verify_trade_streaks.py
.\venv\Scripts\python.exe python\report_trade_streaks.py
```

Evidence: `Reports/trade_streaks_20261007/` (conditional/yearly results, daily stops and remainders, permutation tests, run frequencies, gate checks and provenance).
