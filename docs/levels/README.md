# Price-level research

Updated 2026-10-04. This folder contains all level-study result documents;
generated tables, ledgers and MT5 reports are grouped under `Reports/levels/`.

## Current direction: intact one-week M30 swing-low support (Q11)

Decided with the user on 2026-10-04; frozen in the
[Q11 protocol](../LEVEL_VISIT_PROTOCOL.md) before any Q11 outcome was computed.

- **Exit:** the original RTL exit (>=1R qualified at bar close). The fixed-TP
  experiment is secondary context only; compare like with like.
- **Levels:** confirmed M30 **swing lows** (lowest of 5 bars on each side, known
  only once the 5th bar after closes) whose pivot is in a rolling **one-week**
  window (current session + 5 previous sessions). Two weeks and N = 3 are
  reported alongside, not chosen afterwards. Pivots within D of each other merge
  into one level at the lowest member. Session/week extremes are not used.
- **Support = approached from above.** D = 0.5 x ATR(14, M30, before the signal).
  Price must have closed at least 1 x ATR above the level after the pivot, then
  come back into L +/- D. Shallow undercuts (false breakdowns) still count until
  a close more than D below the level breaks it. The signal may open and close
  below the level and candle shape does not matter, but its low may undercut the
  level by at most D (amended before outcomes; deeper = separate slice-through group).
- **Comparison:** support-revisit signals versus every other qualifying red
  signal, with slice-through, broken-level, not-departed, no-contact and unavailable groups
  reported separately. Same follow-up rule as Q10.

Every report must name its level source explicitly (current session, previous
session, previous week, or one/two-week M30 swing lows).

**Superseded proposal (2026-10-03):** a broad "range overlaps any session/week
low" definition with fixed TP. It was never computed. It mixed candles testing
support from above with candles rejected at a broken level from below, which
the visit rule now separates.

## Results and status

| Study | Status | Outputs |
|---|---|---|
| [Q6/Q7: proximity and overhead room](PRICE_LEVELS_RESULTS.md) | Historical context; no filter | `Reports/levels/price_levels_20261003/` |
| [Q8: breach and reclaim](BREACH_RECLAIM_RESULTS.md) | Historical context; price-response branch superseded as primary evidence | `Reports/levels/breach_reclaim_20261003/` |
| [Q9: recovery speed](RECLAIM_SPEED_RESULTS.md) | **Archived research direction** | `Reports/levels/reclaim_speed_20261003/` |
| [Q10: support interaction](SUPPORT_INTERACTION_RESULTS.md) | Complete; original exit is the primary result, fixed TP secondary. Previous-week lead fails only the sample rule | `Reports/levels/support_interaction_20261003/` (primary), `..._fixed1r_20261003/` |
| [Q11: one-week swing-low support](../LEVEL_VISIT_PROTOCOL.md) | **Protocol frozen 2026-10-04; not yet run** | `Reports/levels/level_visit_20261004/` (planned) |

The Q10 MT5 source, binary, configuration, reports and logs are in
`Reports/levels/support_fixed1r_20261003/`. The original-exit screen, now
Q10's primary result, is in `Reports/levels/support_interaction_20261003/`.

Read the [speed archive note](SPEED_RESEARCH_ARCHIVE.md) for why the research
changed direction. Protocols retain their original `docs/` paths and contents
to preserve frozen definitions and hashes; each result links to its protocol.

## Relocation and audit history

All six generated report directories were moved on 2026-10-03. Numerical CSVs,
decisions, tester outputs and binaries were preserved. Scripts and result links
now use `Reports/levels/`; the fixed-TP run manifest points to its relocated INI.

`Reports/levels/_relocation_20261003/` retains the 77-file pre-move inventory,
original provenance/verification/manifest files and dependency snapshots.
Current provenance records identify the relocation and refresh working-tree
hashes for path-only code changes; they are not new historical research results.
The legacy original-exit screen's protocol had already been superseded by the
fixed-TP amendment; that pre-existing mismatch is recorded explicitly.

Generated `Reports/` files remain local and Git-ignored. Result documents,
protocols, analysis/generation scripts and tests are versioned. No old study or
source data was deleted, and no production trading rule changed during cleanup.
