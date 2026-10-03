# Price-level research

Updated 2026-10-03. This folder contains all level-study result documents;
generated tables, ledgers and MT5 reports are grouped under `Reports/levels/`.

## Current direction: any red candle interacting with support

The user clarified that the first question is broad: **are qualifying red M30
candles that interact with a known support level better signals than every
other qualifying red candle?** Keep all enabled time windows and the baseline
red-run cap. For this experiment use entry at the signal high, fixed -1R SL at
its low, fixed +1R TP, and the existing session-end flattening.

For a valid level L known before the candle opened, the broad interaction is:

`close < open` and `candle_low <= L <= candle_high`.

Touching with a wick counts. Opening below or exactly at the level does not
exclude a candle whose range reaches it. Closing above, below or exactly at the
level does not change qualification. A candle wholly above or below the level
has no observed contact. No speed, reclaim, close-below, penetration-depth or
proximity-band requirement is part of this primary rule.

Compare the aggregate with **all other qualifying red signals**, retaining
unavailable-level cases explicitly, and report all-signals results for context.
Keep current-session, previous-session and previous-week sources separate.
Specific candle structures can be investigated later; they are descriptive
labels, not separate entry requirements or current filter candidates.

**Scope correction:** the completed Q10 study used the narrower *fresh*
interaction definition (open > L and low <= L). Its aggregate already combined
touches, reclaims and closes below, but excluded candles opening at/below L.
Those historical numbers are preserved unchanged. The broader range-overlap
comparison above is the next research step and has **not yet been calculated**.
The frozen Q10 protocol/scripts reproduce the earlier definition; do not silently
rewrite that historical experiment or present it as the broader test.

## Results and status

| Study | Status | Outputs |
|---|---|---|
| [Q6/Q7: proximity and overhead room](PRICE_LEVELS_RESULTS.md) | Historical context; no filter | `Reports/levels/price_levels_20261003/` |
| [Q8: breach and reclaim](BREACH_RECLAIM_RESULTS.md) | Historical context; price-response branch superseded as primary evidence | `Reports/levels/breach_reclaim_20261003/` |
| [Q9: recovery speed](RECLAIM_SPEED_RESULTS.md) | **Archived research direction** | `Reports/levels/reclaim_speed_20261003/` |
| [Q10: fixed 1R trade comparison](SUPPORT_INTERACTION_RESULTS.md) | Completed under the fresh-interaction definition; broad follow-up pending | `Reports/levels/support_interaction_fixed1r_20261003/` |

The Q10 MT5 source, binary, configuration, reports and logs are in
`Reports/levels/support_fixed1r_20261003/`. The superseded original-exit interim
screen is in `Reports/levels/support_interaction_20261003/`.

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
