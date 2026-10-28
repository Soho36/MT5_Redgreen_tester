# RTL MNQ: +1R candle-close exit plus +2R resting take profit

Completed 2026-10-27 under the [frozen protocol](PROTOCOL.md). Exploratory,
user-requested test. **The added +2R take profit makes this version worse on
net profit in both primary periods. Keep the existing candle-close baseline.**
"1/2" was interpreted as risk:reward 1:2 (+2R).

## What was tested

Same M30 RTL: red candle, buy stop at its high, original stop at its low,
no red-run cap, no VWAP filter, one MNQ ($2 per point), flatten at 23:30 with
fallback and early-close calendar. Keep the original exit: a completed candle
closing at >= +1R closes the position at the next bar's first bid. Add an attached
take profit at entry + 2 x initial risk. Whichever exit occurs first closes the
whole position. This is a resting sell limit for the long, with the existing
candle-close check still active. Changing the 1R check itself was not tested.

Both arms were fully rerun in MT5 on `MNQcontDTBNT20102026_2`, M30, 1-minute
OHLC. Changed exit availability feeds back into entries. Tester coverage:
2010-06-07 to 2026-10-15; tables exclude October and end-of-data liquidation.
$1.05 cost per completed round turn is deducted in analysis. History is reused;
this is an exploratory comparison, not a new out-of-sample confirmation.

## Native MT5 results

| Period | Exit | Trades | Net $ | Net closed-trade DD $ | Net PF | Mean net R | TP exits |
|---|---|---:|---:|---:|---:|---:|---:|
| 2016-19 | Original 1R close | 6,167 | 4,416.65 | 2,175.90 | 1.064 | -0.0143 | 0 |
| 2016-19 | 1R close + 2R TP | 6,182 | 3,535.40 | 1,793.40 | 1.051 | -0.0223 | 811 |
| 2020-Sep 2026 | Original 1R close | 10,501 | 38,399.95 | 5,781.15 | 1.090 | +0.0476 | 0 |
| 2020-Sep 2026 | 1R close + 2R TP | 10,510 | 32,429.00 | 5,798.65 | 1.077 | +0.0334 | 1,226 |

Net profit falls **20.0% / 15.5%**. Earlier closed-trade DD falls 17.6%, but
recent DD rises 0.3%. Net/DD declines 2.03 -> 1.97 and 6.64 -> 5.59.
Daily-close DD: $2,143.15 -> $1,753.65 and $5,781.15 -> $5,798.65.
These are net balance drawdowns, not floating-equity drawdowns.

The win rate increases from 43.17% -> 44.13% and 42.71% -> 43.51%, while mean
gross R falls 0.0807 -> 0.0728 and 0.0715 -> 0.0574. The outcome is therefore
not explained by commissions alone. Mean holding time falls only about 2 minutes:
103.13 -> 100.69 and 101.16 -> 99.14. There are only 15 / 9 net additional trades.
The hybrid earns less in 6 of the 7 recent calendar years; 2020 is the exception.
Across all 17 years it improves 6. Reference 2010-15 net is essentially unchanged:
-$7,496.20 -> -$7,495.95.

## Why taking the spike did not help overall

On the 1,226 shared recent entries where the hybrid TP exits, 582 improve their
result by $23,626 combined, while 630 lose $29,153.50 relative to the baseline
(14 unchanged). The net change on these shared entries is **-$5,527.50**.
Taking reversals helps, but capping the larger candle-close winners costs more.
Changed entry availability accounts for the remaining -$443.45, for a total
-$5,970.95. Early shared-entry change is -$1,074; changed availability offsets
$192.75, leaving -$881.25. These paired attributions describe the full replay;
they do not substitute for it.

With an additional $1 / $2 per trade, early baseline net is -$1,750 / -$7,917,
hybrid -$2,647 / -$8,829; recent baseline $27,899 / $17,398, hybrid $21,919 /
$11,409. The ranking remains the same.

## Verification and artifacts

- New tester-only EA `RTL_intrabar_tp` compiles with **0 errors, 0 warnings**.
  `RiskReward=1` retains the close check; `IntrabarTakeProfitR=2` adds the TP;
  `IntrabarTakeProfitR=0` disables it. Installed separately under
  `MQL5/Experts/CodexExitResearch/RTL_intrabar_tp.ex5` for historical testing.
  The original EA/source and default baseline were not changed.
- Disabled-TP native run reproduces all **25,833** original trades exactly,
  including tickets, submission/entry/exit times and all execution prices/profits.
- Minute simulator agrees with all **25,833 baseline and 25,872 hybrid trades**:
  submission/entry/exit minute, requested price, fill, original stop, exit price
  and dollars. Final tables use native MT5 fills and timestamps.
- Native comparison found and fixed two simulation details: submissions on sparse
  bar openings use the actual first quote time; an attached TP is executable on
  the generated quote after its pending buy-stop fill. The preliminary same-quote
  TP estimate was superseded. The 1-minute OHLC model cannot establish real tick
  ordering inside a minute. No parameters were selected from these corrections.
- 11 hybrid tests and 15 existing engine tests pass, including next-quote TP
  activation, wick reversals, close-confirmed exits, stops and session flattening.

Saved outputs: `Reports/rtl_intrabar_tp_20261027/`. Start with
`summary_native.csv`, `yearly_native.csv`, `attribution_native.csv`,
`native_baseline.csv`, `native_tp2r.csv`, and `verification.json`.
The folder also preserves both native HTML reports, INIs, compiled EA, source,
compiler logs, completion hashes, simulator tables and correction provenance.

Reproduce from the project root using the project venv:

```powershell
& .\venv\Scripts\python.exe python\analyze_rtl_intrabar_tp.py
& .\venv\Scripts\python.exe python\verify_rtl_intrabar_tp.py
& .\venv\Scripts\python.exe -m unittest discover -s python -p test_rtl_intrabar_tp.py -v
```

`prepare_rtl_intrabar_tp.py` creates the isolated source/configs on a clean run
folder. `run_rtl_intrabar_tp.py compile` compiles them; `run <frozen_tag>` runs
one historical tester arm and refuses to launch if a terminal is already running.
The original installed account context is used for the historical tester, with
live trading disabled; no preexisting terminal was interrupted.
