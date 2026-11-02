# Additional flatten-before-open arm

Added at the user's request while the original eight jobs were running, 2026-11-01.
Preserve the [original plan](EXCLUDE_16_PROTOCOL.md) and its frozen jobs. Add four
jobs: RTL/GG x VWAP OFF/ON, all with the 16:00-17:00 entry window excluded and a
forced flatten/cancellation at the first available quote at or after 16:00 each
source date. 16:00 is 30 minutes before the 16:30 cash open on this session clock.
If data are missing at that time, flatten on the next available quote and disclose
any late boundary. Entries resume normally at 17:00.

Use a separately named tester-only EA derived from the original experiment copy.
Only add the one daily flatten operation before normal strategy processing. A
pending order can still trigger on the boundary quote before EA cancellation;
the resulting position is immediately flattened. Record every flatten event and
its pre-action position/order counts. No automatic close at 17:00 or exit change
outside this daily operation. Compare against matched original-control and
entry-exclusion-only jobs with the same equity observer and external costs.

Publish all three window policies. User requested generic intraday DD; no firm-
specific trailing threshold or breach simulation. Verify forced events and trades
carrying across 16:00, plus normal native/VWAP/equity checks from the original plan.
Save added jobs separately under `Reports/rtl_gg_exclude16_flatten_20261101/`.
