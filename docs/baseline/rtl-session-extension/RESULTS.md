# RTL after a session rally and realized gains

The +2% rally combined with positive realized session P&L offered little basis for skipping the next RTL setup. All 15 earlier trades on such rallies already had positive session P&L. In the recent period, 106 of the 119 trades were in profit for the session before submission. The comparison group had only 13 trades in nine sessions. Adding a requirement for two consecutive winners reduced replay profit in both periods.

This exploratory follow-up uses Q24's 14,968 capped RTL trades through July 13, 2026, one MNQ and $1.05 per closed trade. Extension uses the first bid of the submission bar versus the session's first traded open, typically 01:00 on the dataset clock. The trigger can switch off on a pullback. P&L uses closed trades, including costs. A win streak counts consecutive profitable trades, and +1R of session P&L sums each prior trade's realized return divided by its own initial risk. [Protocol](PROTOCOL.md)

## What happened on the next baseline trade?

| Period | Rise since open | Prior session P&L | Trades | Sessions | Win rate | Mean net R | Total net |
|---|---|---|---:|---:|---:|---:|---:|
| 2016–19 | Below 2% | Flat or negative | 3,381 | 1,031 | 44.2% | +0.010 | $4,928 |
| 2016–19 | Below 2% | Positive | 2,301 | 793 | 42.2% | −0.026 | $1,266 |
| 2016–19 | At least 2% | Flat or negative | 0 | 0 | — | — | — |
| 2016–19 | At least 2% | Positive | 15 | 15 | 46.7% | +0.207 | $291 |
| 2020–July 2026 | Below 2% | Flat or negative | 5,473 | 1,688 | 43.8% | +0.067 | $22,531 |
| 2020–July 2026 | Below 2% | Positive | 3,679 | 1,314 | 41.8% | +0.051 | $15,093 |
| 2020–July 2026 | At least 2% | Flat or negative | 13 | 9 | 46.2% | +0.088 | $37 |
| 2020–July 2026 | At least 2% | Positive | 106 | 62 | 44.3% | −0.006 | $320 |

Among recent extended trades, positive prior P&L corresponds to a −0.094R difference relative to flat or negative P&L. The exploratory 95% week-bootstrap interval spans −0.72R to +0.40R. Comparing within submission hours represented on both sides changes the estimate to +0.16R, with only 59 trades in those hours. The earlier period has no corresponding comparison. Positive total dollars can coincide with negative mean R because the dollar risk per trade varies with candle size.

## Change in net dollars when the strategy actually skips orders

| Skip condition | 2016–19 | 2020–July 2026 |
|---|---:|---:|
| Rise ≥2% alone | −$291 | −$270 |
| Positive session P&L alone | −$2,004 | −$22,193 |
| Two consecutive wins alone | −$825 | −$7,704 |
| Rise ≥2% and positive session P&L | −$291 | +$179 |
| Rise ≥2% and session P&L ≥+1R | −$291 | −$174 |
| Rise ≥2% and at least two consecutive wins | −$342 | −$824 |
| Rise ≥1% and positive session P&L | −$976 | −$3,809 |
| Rise ≥3% and positive session P&L | −$255 | +$518 |

The +2% and positive P&L rule changed closed-trade maximum drawdown from $1,435 to $1,382 earlier and from $4,847 to $4,851 recently. Its recent +$179 was under 0.5% of baseline profit. It helped in six of eleven calendar years including partial 2026. The earlier +3% comparison contains just two baseline trades. These results leave open the broader question of exhaustion after a move unusually large for the prevailing volatility.

Each replay recalculates states from trades actually taken and cancels an older pending stop on each rejected red signal. A P&L-only skip once positive lasts the remainder of the session because there are no more realized trades to change that state. The extension combination can resume when price retreats. Changed opportunities explain why removing 106 recent positive-P&L trades from the baseline does not reproduce the strategy result.

## Verification and reproduction

The unrestricted Python one-minute OHLC replay matches all 14,968 native Q24 fills by submission, entry and exit minute, net dollars, risk-normalized returns and preceding win counts. A second implementation checks the primary +2% rules through the project's minute-by-minute EA engine, including path-specific state reconstruction. All trade timestamps and dollar returns matched for extension alone (14,835 trades), green P&L (14,845), +1R (14,852) and two wins (14,896). Filtered results are simulated, with the native MT5 ledger as the control.

From the project root run `venv/Scripts/python.exe python/rtl_session_extension.py`, then `venv/Scripts/python.exe python/verify_rtl_session_extension.py`. [All skip-rule results](../../../Reports/rtl_session_extension_20261124/policies.csv) · [All next-trade comparisons](../../../Reports/rtl_session_extension_20261124/cells.csv) · [Uncertainty and hourly comparisons](../../../Reports/rtl_session_extension_20261124/contrasts.csv) · [Annual changes](../../../Reports/rtl_session_extension_20261124/annual.csv)

