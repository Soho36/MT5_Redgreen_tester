# Far-below VWAP rule on GG, NQ (exploratory)

Frozen 2026-10-30, before any VWAP label or labelled outcome was computed for GG trades. The user
asked whether the unchanged rule also marks weak GG signals on NQ. **Exploratory:** GG trades the
same NQ sessions the rule was found on (daily correlation with RTL about +0.6; in a trade together
71% of the time), so this is not independent evidence. Agreed in advance: a pass does **not**
upgrade the rule; a fail counts against it (it would look specific to red signal candles). No
strategy, default or live change follows.

## Question

Does the rule that held for RTL on NQ 2016-26 also hold for GG there?

1. Far-below GG signals earn less net R than other GG signals with similar planned risk.
2. Skipping them cuts daily-close drawdown more than skipping as many GG trades chosen without VWAP.

## Sample and source

The existing GG run on NQ, no new MT5 run: `ymbase_20261023_gg_nq` in `Reports/ym_baselines_20261023`
(report, ledger, stats, INI, completion record). Settings: green M30 candle (close > open), buy stop
at its high, stop at its low, RR 1 bar-close exit, `MinGreenRun=1`, `MaxGreenRun=0`, `MinLocation=0`,
flatten with fallback, early-close calendar, 01:00-23:30 window, 1 lot, Model 1, symbol
`MNQcontDTBNT20102026_2`, $2 per point. Cost $1.05 per trade; planned risk = (requested price -
original stop) x $2; net R = net dollars / planned risk; periods by submission session; trades
submitted before 2026-10-01.

| Sample | Role | Periods |
|---|---|---|
| NQ GG 2016-Sep 2026 | primary | eras 2016-19 and 2020-Sep 2026; pooled |
| NQ GG 2010-15 | secondary | same statistics; never changes the verdict |

**VWAP features are not rebuilt.** The labels use the cross test's frozen NQ features
(`Reports/rtl_vwap_cross_20261027/features_NQ.csv`, variant `full_hlc3`, built by
`build_rtl_vwap_features.py` and matched there to the original study) and its NQ session calendar.
The rule is unchanged: z = (signal close - VWAP) / A20 from the latest feature available at or before
submission; **far below: z < -1**; a feature from an earlier session or a missing A20 is unknown and
the trade is kept.

## Source checks, before any outcome

- Report, ledger, stats, INI settings and completion hashes reconcile as in the cross test.
- Published GG NQ counts and net (Reports/ym_baselines_20261023/summary.csv): 6,388 / +$3,635.60
  (2016-19), 11,181 / +$39,315.45 (2020-26), 8,935 / -$5,108.25 (2010-15).
- Date-crossing orders and positions are explained by sessions whose data end early.
- Every labelled bar is the GG signal bar: high = requested price, low = original stop, close > open;
  more than 0.1% unexplained mismatches stops the study.
- Pipeline check: labelling the cross test's NQ RTL trades with the same loaded features reproduces
  that test's saved labels and z exactly.

## Measures and verdict

Exactly the cross test's (CROSS_PROTOCOL.md, "Measures" and "Verdict"), on one instrument:
baseline and rule summaries (ledger omission, not a replay); A. risk-decile contrast with a 4-week
circular block bootstrap (5,000 draws); B. placebos B1 risk decile and B2 rolled within month
(2,000 draws each), plus B3 and B4 as descriptive. Seeds: bootstrap 202610300, placebos 202610310,
primary sample first, then secondary.

**Consistent with RTL** if, on the pooled primary sample: (1) contrast A is below zero with its whole
95% interval below zero; (2) the rule's daily-close DD beats at least 95% of B1 draws and of B2
draws; (3) in each era, contrast A is below zero and the rule's DD is below the median DD of B1 and
of B2. Fewer than 200 far-below trades or 30 active far-below weeks in an era: inconclusive.
Otherwise **not consistent**. One verdict; the secondary sample is descriptive.

Descriptive only, never the verdict: how many GG signals are far below; annual rows; the roll-clean
subset; and the combined RTL + GG account (daily sum of both ledgers, cross-test RTL labels):
net and daily-close DD with no gate, gate on RTL only, and gate on both.

## Outputs and verification

`Reports/gg_vwap_20261030/` (gitignored): audit, labelled trades, summaries, contrast and bootstrap
draws, placebo masks and draws, verdict, provenance. A separate script re-parses the report,
rebuilds VWAP, A20 and z from the raw NQ minutes with the cross test's independent code, and
recomputes the summaries, contrast, every bootstrap and placebo draw, the verdict and the combined
account. Results go to `GG_RESULTS.md` in this folder; journal and status updated.

## Inputs at freeze (SHA-256)

| File | SHA-256 |
|---|---|
| `Reports/ym_baselines_20261023/ymbase_20261023_gg_nq.htm` | `031d4f2cff7cdfe07b8704ffd3277517684756c64f1ce3bb536442611da9600d` |
| `Reports/ym_baselines_20261023/runband_ymbase_20261023_gg_nq_1.00.csv` | `091a3eeb2dae54698df78fb6860939593564c123681646efe822fd0e9333b459` |
| `Reports/ym_baselines_20261023/runband_ymbase_20261023_gg_nq_1.00_stats.csv` | `6dea87bb5cdf704ad529af25e1e6eef0f4f6a91e98332ae5dbf60a3344d9be4c` |
| `Reports/rtl_vwap_cross_20261027/features_NQ.csv` | `d88bbd10f82df2b6bb428b418b5cbbdb3c13f8baea3fa2d6ae491656d3bc92d6` |
| `Reports/rtl_vwap_cross_20261027/trades_NQ.csv` | `1c8537e0eca9de7a0470e9e6a9668687d3a09c0387c664b182c6d0f6f7ddaf3e` |
| `Reports/rtl_vwap_cross_20261027/calendars.csv` | `64be3ff61751cc8237c82f5c4adad9e70e73f698d59715195c5e8586b0866141` |
| `F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv` | `df3390928189f0d12c2140c3994671998151d8cb7289189b6f8a8ad83ff74e6a` |
| `F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_rolls.csv` | `7421df167e9bcdcdd21a310395f388e041d50de4ed42d987095c5596109be49d` |
