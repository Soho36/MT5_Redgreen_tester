# Equity accounting verification note

Recorded during verification, 2026-11-01. The passive observer's callback counter
under-counted completed deals when deal metadata were not available to that callback.
The saved account **balance and equity observations are independent of that counter**;
the counter does not affect orders, fills or exits. Control ledgers match their
original native runs.

Do not use the observer counter for external costs. Reconstruct completed-trade
counts from authoritative native report exit timestamps, checked against ledger
counts/profit and final account balance. Charge $1.05 for each exit at or before
the observation timestamp. Record the original counter discrepancy in verification,
rather than treating that counter check as passed.

Timestamp resolution is one second: samples just before/after a closure can share
the timestamp. Also compute DD with costs charged strictly before the observation
timestamp and report the difference as cost-timing sensitivity. This does not
remove the larger 1-minute-OHLC generated-tick path limitation. No source equity
prices, strategy outcomes or native ledgers are altered.
