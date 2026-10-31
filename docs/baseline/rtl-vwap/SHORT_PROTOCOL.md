# RTL short below the unchanged VWAP cutoff

2026-10-31. User-requested exploratory test on previously examined NQ history.
Frozen before new outcomes. No threshold search.

Use the project RTL-short baseline: green M30 signal, sell stop at its low,
stop at its high, 1R bar-close exit, no run cap, unchanged session windows,
23:30 flatten with fallback and the existing early-close calendar. One MNQ,
$2/point, $1.05 round-turn cost. MT5 1-minute OHLC.

Blue stays session HLC3 VWAP; orange stays VWAP minus arithmetic A20 (20
completed M30 true ranges). New shorts qualify only when the completed
signal close is strictly below orange, the known condition blocking longs.
Equality and unknown/stale labels do not qualify. Cancel an old pending order
on a replacement green signal before applying the gate; opposite-colour bars
and existing positions keep baseline management. This gates submission, not
later fills; a resting order can fill after price recovers.

Replay OFF and ON in native MT5 using the existing causal real-volume label
file (tester volume is synthetic). OFF must reproduce the saved
ymbase_20261023_rtl_short_nq ledger and native totals before ON runs. Verify
all gated decisions and actual short orders against labels and native reports.
Preserve input hashes. Use a separate portable tester, with no account copied.

Primary reporting: 2016-19 and 2020 through September 2026; 2010-15 and pooled
2016-26 descriptive. Exclude submission sessions from October 1 2026 onward.
Report trades, net dollars, gross/net mean R, net PF, daily-close and
closed-trade drawdowns, annual results and +$1/+ $2 cost stress. Compare
unfiltered shorts, qualifying baseline shorts (ledger subset), and full
replay. Illustrate independently replayed gated RTL-long plus gated RTL-short
at one contract per leg, summing without netting opposite positions; this is
not a tested single-account execution model.

The question is whether the rejected-long region produces profitable shorts.
Losing less than unfiltered shorts is insufficient: assess positive net
returns in both primary eras. No live deployment or baseline change.

## Environment resolution before gated outcomes

The active terminal initially locked the 2026 HCC history. Windows capture
failed and the existing account-free portable tester cannot run. The user
then reported accidentally closing MT5 and asked to retry. With no terminal
running, launch the existing native tester with the dedicated EA and frozen
configs. Do not stop a user's existing terminal. Native OFF must reproduce
the reference byte for byte before ON. Both native arms are the final evidence;
the abandoned mirrored simulator's baseline did not pass and supplies no
outcome evidence. Add a tester-only EA guard. Lines and threshold unchanged.
