# Corrected flatten arm: 16:30, entries disabled 16:00-17:00

User correction recorded 2026-11-01 before any flatten-arm native run. Flatten at
the first available quote at or after **16:30**, the cash open on the source clock.
New entries remain disabled from 16:00 inclusive to 17:00 exclusive. The prepared
16:00-flatten version was compiled but never run; preserve its unused artifacts.
This document supersedes the timing in EXCLUDE_16_FLATTEN_AMENDMENT.md.

Run four additional native jobs: RTL/GG x orange VWAP OFF/ON, with the same entry
exclusion and passive equity observer as the original eight-job study. Close open
positions and cancel pending orders once per date at 16:30, before normal EA tick
processing. Existing positions can continue normally from 16:00 to 16:30. Boundary
fills can occur before the EA processes the first quote; flatten handles any
resulting position. Record actual event timestamps and report delayed first quotes.

All other definitions, periods, costs, verification and reporting requirements in
EXCLUDE_16_PROTOCOL.md apply. Evidence:
`Reports/rtl_gg_exclude16_flatten1630_20261101/`. No live chart or default change.
