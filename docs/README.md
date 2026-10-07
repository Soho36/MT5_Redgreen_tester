# Research docs

**Start with [STATUS.md](STATUS.md)** (where the project stands) and
[JOURNAL.md](JOURNAL.md) (what was done, day by day). This page is the map.

Every study has its own folder: `PROTOCOL.md` (frozen before any outcome),
`RESULTS.md` (the answer) and `img/` when it has charts. Generated tables,
ledgers and MT5 reports stay in `Reports/`. Studies are numbered Q1, Q2, ...
in the order they were run.

## Setups (price patterns at levels and trendlines)

Grouped as in the user's sketch ([photo](reference/setup_map_sketch.jpg)).
"Limit" marks setups drawn with a resting limit order.

### Horizontal levels ([index](setups/horizontal/README.md))

| Setup | Direction | Studies | Status |
|---|---|---|---|
| [Resistance breakout](setups/horizontal/resistance-breakout-long/README.md) | Long | Q18, Q19 | **Passes both stages** (Q18), broadly spread (Q19). Nothing adopted; next step is forward/demo evidence |
| [Support bounce](setups/horizontal/support-bounce-long/README.md) | Long | Q6/Q7, Q10-Q13 | No filter. Q11 slightly better but N = 3 disagrees. The limit variant from the sketch is not tested |
| [Support reclaim](setups/horizontal/support-reclaim-long/README.md) (failed breakdown) | Long | Q8, Q9, Q25 | No. Q25 buy stop at the broken level: PF > 1 but mean R < 0 |
| [Support breakdown](setups/horizontal/support-breakdown-short/README.md) | Short | Q23 | No (fails stage 1); short-side level research stopped |
| [Resistance bounce (limit)](setups/horizontal/resistance-bounce-short-placeholder/README.md) (placeholder) | Short | - | Not tested yet |

### Trendlines ([index](setups/trendlines/README.md))

| Setup | Direction | Studies | Status |
|---|---|---|---|
| [Uptrend bounce](setups/trendlines/uptrend-bounce-long/README.md) (rising line) | Long | Q14, Q20 (limit) | No. RTL signals at the line are worse (Q14); a buy limit on the line loses (Q20) |
| [Uptrend breakdown](setups/trendlines/uptrend-breakdown/README.md) | Short (Q21), long at the break (Q22) | Q21, Q22 | No. The short loses (Q21); buying the breakdown candle is worse than other RTL signals (Q22) |
| [Downtrend breakout](setups/trendlines/downtrend-breakout-long/README.md) (falling line) | Long | Q15, Q16, Q17 | Passed attribution (Q15, Q16) but not traded alone (Q17) |
| [Downtrend bounce](setups/trendlines/downtrend-bounce-short-placeholder/README.md) (placeholder) | Short | - | Not tested yet |
| [Downtrend bounce (limit)](setups/trendlines/downtrend-bounce-long-placeholder/README.md) (placeholder) | Long | - | Not tested yet |
| [Uptrend bounce (limit)](setups/trendlines/uptrend-bounce-short-placeholder/README.md) (placeholder) | Short | - | Not tested yet |

## The RTL strategy itself ([baseline/](baseline/README.md))

Entry filters, exits, RR, sessions and order mechanics of the base strategy
(red candle, buy stop at its high): Q1-Q5, time of day, MaxRedRun, RR, exit
threshold, trailing stop, flatten fallback, early-close calendar, averaging,
limit-only entry, trend-conditioned RR, Q24 trade streaks, the baseline on MES (unseen instrument).

## Reference

- [Data build](reference/DATA_BUILD.md): the continuous NQ and ES one-minute series.
- [Exit and data review](reference/EXIT_AND_DATA_REVIEW.md).
- [Research questions](reference/RESEARCH_QUESTIONS.md) (checklist and inbox)
  and [early research results](reference/RESEARCH_RESULTS.md).
- [figures/](figures/): shared explainers and charts.
- [moved_files.json](reference/moved_files.json): old path to new path for every
  file moved on 2026-10-07 (code comments in `mt5/` and run folders in
  `Reports/` still name the old paths).
- [protocol_hashes.json](reference/protocol_hashes.json): the two protocol
  versions whose recorded hashes are checked via git history (see
  `protocol_matches` in `python/analyze_price_levels.py`).

**Numbering note:** the support-reclaim study was called Q24 until
2026-10-07. Trade streaks had already taken Q24, so support reclaim is Q25 in
the docs; its code, run folders and commit messages keep "Q24".
