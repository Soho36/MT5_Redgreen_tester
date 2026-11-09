# Selling the last half hour of a weak NQ day

The weak-day short lost **$1,804.00** on 1,170 trades from January 2016 through September 2026. Selling one minute later on exactly the same days produced **+$238.50**, or $0.20 per trade. Both entry timings lost money from May 2020 onward, the period after the motivating paper's NQ sample ended. The results do not support this short as a standalone strategy.

## Trade and benchmark

At the first futures price in the 3:30 p.m. New York minute, compare NQ with the same contract's last price in the preceding cash session's final regular minute. A price strictly below that mark selects a weak day. The primary simulation sells on the next modeled quote. The second simulation uses the observed 3:31 minute open. Both cover at the 4:00 minute open, using one MNQ's $2 per point and $1.05 per round trip. Positions have a time exit and remain exposed to intratrade losses until then. The benchmark shorts every eligible day using the same fills. [Frozen protocol](PROTOCOL.md)

| Period | Weak trades | Next quote, net | Net per trade | Net PF | Max daily-close drawdown | 3:31 open, net | Every day, next quote net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2016–19 | 416 | +$464.70 | +$1.12 | 1.103 | $696.60 | +$546.20 | −$293.05 |
| 2020–Sep 2026 | 754 | −$2,268.70 | −$3.01 | 0.933 | $7,385.90 | −$307.70 | −$2,587.80 |
| Both periods | 1,170 | **−$1,804.00** | −$1.54 | 0.953 | $7,385.90 | **+$238.50** | −$2,880.85 |
| May 4, 2020–Sep 2026 | 718 | −$2,879.90 | −$4.01 | 0.909 | $7,385.90 | −$926.90 | −$1,559.65 |

The final row overlaps the 2020–26 period. Over the full sample, the weak-day rule took 44% of eligible sessions. The next-quote fill lost $1.54 per weak trade, compared with $1.09 across all days and $0.73 on the remaining days. The early profit came from 2018, which earned $1,040.85 while each of the other three early years lost money. Weak days lost money in each year from 2023 through September 2026 under both entry timings. [Annual figures](../../../Reports/mnq_weak_close_20261106/annual.csv) · [All period and control metrics](../../../Reports/mnq_weak_close_20261106/summaries.csv)

## Timing and costs

| Pooled weak-day results | Next modeled quote | 3:31 minute open |
|---|---:|---:|
| Gross P&L | −$575.50 | +$1,467.00 |
| Net after $1.05 per trade | −$1,804.00 | +$238.50 |
| Net with another $1 per trade | −$2,974.00 | −$931.50 |
| Net with another $2 per trade | −$4,144.00 | −$2,101.50 |
| Net win rate | 48.2% | 48.7% |
| Maximum daily-close drawdown | $7,385.90 | $5,401.50 |

Waiting until the next minute improved pooled net by $2,042.50. Actual fills immediately after the signal cannot be recovered from one-minute OHLC. The second entry timing uses an observed trade price, with historical bid/ask spread and market impact covered only by the cost sensitivities. Four-week block-bootstrap 95% intervals for pooled mean net ranged from −$7.13 to +$3.86 per trade at the next modeled quote and −$5.02 to +$5.26 at 3:31. Both intervals for the improvement in mean net versus the every-day benchmark also cross zero. [Intervals](../../../Reports/mnq_weak_close_20261106/intervals.csv)

## Coverage and verification

The study identified 2,701 scheduled U.S. equity sessions. It excluded 21 early closes and 43 changes of front contract between reference and signal day. The required prices existed for all 2,637 remaining sessions. Twenty-one trades or control observations used a prior early-close session's 12:59 close as their reference. The sample includes 1,170 weak days and 1,467 other eligible days.

The independent verifier rebuilt the exchange schedule, applied the New York–Chicago time-zone conversion to the source clock, read the source futures prices and volumes, and checked all eligibility decisions, entries and exits. It recalculated 24 period rows and 66 annual rows, including transaction costs and daily-close drawdown. [Verification](../../../Reports/mnq_weak_close_20261106/independent_verification.json) · [Session ledger](../../../Reports/mnq_weak_close_20261106/sessions.csv) · [Analysis script](../../../python/analyze_mnq_weak_close.py) · [Verifier](../../../python/verify_mnq_weak_close.py)
