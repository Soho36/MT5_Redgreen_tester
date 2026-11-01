# RTL blue VWAP slope: full MT5 replay

Recorded 2026-11-01 after the descriptive [slope-only results](SLOPE_RESULTS.md).
User requested a full replay. This is exploratory reuse of known NQ history.

Run two native M30/1-minute-OHLC historical jobs with identical RTL baseline
settings: slope gate OFF, then ON. OFF must reproduce the previous RTL baseline
trade ledger byte for byte and native totals. ON permits a new buy stop only when
the completed signal candle's blue session VWAP exceeds the preceding M30-close
VWAP, exactly 30 minutes earlier in the same session. Missing, flat or falling
slope blocks. No orange or price-above-blue condition. Original cancellation of
the old buy stop occurs before the gate; fills and exits follow the normal EA.
Slope is not rechecked at fill. Later signals freed by skipped orders may trade.

Use the frozen real-volume features already independently verified by the slope
study, with availability at signal close and no comparison across resets/gaps.
Export all bar labels, including unavailable ones. Fail on label/chart mismatch.
Tester-only research EA has its own name; existing strategy files remain intact.
All inputs are explicitly set. No live chart attachment or trading.

Use original history through the baseline run's end so OFF can reproduce the whole
ledger. Report only submission sessions before 2026-10-01: 2016-19, 2020-Sep 2026,
pooled 2016-Sep 2026, with 2010-15 secondary. One contract, $2/point, $1.05/trade.
Compare baseline, omission and replay: count, net, mean gross/net R, daily-close DD,
net/DD, annual results. Use the same frozen submission-session calendar.

Check every native candidate decision against independently rebuilt slope labels;
verify every replay trade's source signal is rising, source OHLC matches entry/SL,
native ledger/report/stats reconcile, and baseline/omission match the descriptive
study. Independently reconstruct replay profit from fills/exits and verify daily DD.
Preserve hashes, configs, sources, reports and logs in
`Reports/rtl_vwap_slope_replay_20261101/`. No optimization or adoption decision.
