# Exclude 16:00-17:00: RTL and GG, with and without VWAP

Recorded before new outcomes, 2026-11-01. Full native MT5 replay on the same NQ
history. User requested generic intraday drawdown, without account-specific rules.

Run eight jobs: RTL/GG x orange VWAP gate OFF/ON x original windows/exclude only
16:00-17:00. VWAP gate uses signal **close**, z < -1 (VWAP - A20); equality and
unknown keep. No blue-price, slope, open-price or additional filter. Otherwise
retain the existing full-window baseline settings, source and real-volume labels.

The only window input changed is `W1600W1700=false`; all other enabled windows
remain enabled. Source clock is Chicago+8, seven hours ahead of New York: the
excluded hour is 09:00-10:00 New York, containing the 09:30 cash open. It blocks
submissions at 16:00 and 16:30, then resumes at 17:00. Existing positions are managed
normally. Existing pending-order cancellation semantics are unchanged, including
possible fills on the first tick of the excluded bar before cancellation. This
does not guarantee zero open exposure or zero fills during the excluded hour.

Control ledgers must match the corresponding saved native baseline and VWAP runs
byte for byte. Separate tester-only EA with a passive before/after-tick and trade-
transaction equity observer; no chart attachment or live strategy change. Capture
changed account balance/equity and cumulative closed trades. All jobs use the same
observer so the intraday comparison is consistent. Model is 1-minute OHLC with
generated ticks; open-equity DD is model-dependent, not actual-tick proof.

Report 2016-19, 2020-Sep 2026, pooled 2016-Sep 2026; 2010-15 secondary; annual.
Use one contract, $2/point, $1.05/trade external cost, charged at closure for the
equity observer. Report count, net, mean gross/net R, profit factor, daily-close DD
(submission-session attribution, as before), sampled open-equity peak-to-trough DD
(continuous running high, reset only at analysis-era start), and worst within-session
equity peak-to-trough DD (high resets each source date). No capped/floored trailing
threshold, firm breach-rate or combined-account intraday claim.

Compare each exclusion run with its matched all-window control; no optimization of
the hour. Verify every native trade and economics, submission-hour exclusion,
VWAP candidate decisions/filled eligibility, control identity, and equity observer
closed counts/end balances. Recompute sampled DD from saved observations with an
independent algorithm and reconcile net costs to native ledgers. Report fills and
positions carrying exposure during the excluded hour explicitly.

Evidence: `Reports/rtl_gg_exclude16_20261101/`. Publish `EXCLUDE_16_RESULTS.md`,
summary chart, reproducible preparation and verification code. Historical exploratory
study; no adoption verdict or automatic production-setting change.
