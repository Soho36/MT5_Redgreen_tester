# RTL far-below VWAP rule on ES, YM and RTY

Frozen 2026-10-27, before any VWAP feature, label or outcome was computed for ES, YM or RTY.
The user asked for this test after the [evaluation](../../JOURNAL.md#2026-10-27-evaluation-of-the-vwap-study)
of the NQ [study](RESULTS.md) and [full replay](REPLAY_RESULTS.md): the unchanged rule on other index
futures, with the evaluation's placebo controls. Confirmatory in intent. No strategy, default or live
change follows from this test alone.

## Question

On NQ, skipping new RTL signals whose completed close is more than one A20 below full-session VWAP
about halved daily-close drawdown in both eras. Placebos that skipped as many trades without VWAP did
not. If "far below VWAP" really marks weak RTL signals, other index futures should show the same,
even where RTL loses money overall:

1. Far-below signals earn less net R than other signals with similar planned risk.
2. Skipping them cuts drawdown more than skipping as many trades chosen without VWAP.

Profit is reported but does not enter the verdict: on NQ, drawdown was the robust part.

## Samples and sources

No new MT5 runs. Each instrument uses its existing RTL run, with the NQ baseline's settings: red M30
candle (close < open), buy stop at its high, stop at its low, RR 1 bar-close exit, `MaxRedRun=0`,
`MinLocation=0`, flatten with fallback, early-close calendar, 01:00-23:30 window, 1 lot, Model 1
(1-minute OHLC). Minute data are the Databento continuous files the custom symbols were imported
from; volume is the full-size contract's actual traded volume.

| | MT5 run tag (report, ledger, stats) | Symbol, $/point | Minute file in `F:\DATABENTO\` |
|---|---|---|---|
| ES | `ymbase_20261023_rtl_es`, `Reports/ym_baselines_20261023` | `MEScontDTBNT20102026_2`, $5 | `ES_16_YEARS\MT5_ES_continuous_2010-2026_ohlcv-1m.csv` |
| YM | `ymbase_20261023_rtl_ym`, same folder | `MYMcontDTBNT20102026`, $0.50 | `YM_16_YEARS\MT5_YM_continuous_2010-2026_ohlcv-1m.csv` |
| RTY | `rtybase_20261023_rtl`, `Reports/rty_baselines_20261023` | `M2KcontDTBNT20172026`, $5 | `RTY_16_YEARS\MT5_RTY_continuous_2017-2026_ohlcv-1m.csv` |
| NQ | `ymbase_20261023_rtl_nq`, `Reports/ym_baselines_20261023` | `MNQcontDTBNT20102026_2`, $2 | `MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv` |

Roll files sit beside each minute file. Only trades submitted before 2026-10-01. Cost $1.05 per
completed trade. Planned risk = (requested price - original stop) x $/point; net R = net dollars /
planned risk. Periods are assigned by submission session.

| Sample | Role | Periods |
|---|---|---|
| ES, YM | primary | eras 2016-19 and 2020-Sep 2026; pooled 2016-Sep 2026 |
| RTY | primary | eras 2018-19 and 2020-Sep 2026; pooled 2018-Sep 2026 |
| NQ 2016-Sep 2026 | reference, already seen | pipeline check; reported for comparison |
| NQ, ES, YM 2010-15; RTY 2017-07 to 2017-12 | secondary | same statistics; never change the verdict |

RTY starts in 2018 as in the [RTY study](../rty-unseen-instrument/RESULTS.md): CME RTY began
2017-07-10 and its first months are thin. NQ 2010-15 has never been analysed for this rule, but the
full-replay MT5 report spans 2010-26, so it is not strictly blind. Before 2016 some sessions have a
different shape ([data build](../../reference/DATA_BUILD.md)); VWAP still resets per source date.
Data holes (ES's two, RTY's 2020-03-16 and 2025-11-28) stay as they are: no synthetic minutes or bars.

## Source checks, before any label

- Parse each MT5 report (buy-stop orders; buy-in and sell-out deals, volume 1, zero commission and
  swap). Reconcile it with its runband ledger and stats file: one trade per ledger row, entry and
  exit times, profit, candle range = requested price - original stop, whole-run report totals.
- Reproduce the published counts and net dollars: ES 6,286 / -$4,652.80 (2016-19) and 10,803 /
  -$9,085.65 (2020-26); YM 6,209 / +$690.55 and 10,889 / -$2,466.95; RTY 3,207 / -$2,179.35
  (2018-19) and 10,778 / -$3,486.40.
- Minute data: positive volume equal to tick volume, unique ordered timestamps, valid OHLC, every
  minute at or after 01:00.
- Every trade's labelled signal bar (M30, rebuilt from minutes) must have high = requested price,
  low = original stop and close < open. On NQ all 16,668 eligible trades match. Mismatches are
  explained before any outcome is computed; more than 0.1% unexplained stops the study.
- NQ reference: the new code on the NQ run must reproduce the VWAP study's `full_hlc3` panel trade
  for trade (matched by submission and entry time): labels, z, economics, and its omission result
  of net $3,938.65 / $43,435.25 and daily-close DD $931.95 / $3,084.05 (2016-19 / 2020-26).

Any failure stops the study until it is resolved and disclosed. No outcome is read before these pass.

## The rule, unchanged

Use the NQ code, imported unchanged from `python/build_rtl_vwap_features.py` (hash below), variant
`full_hlc3`. VWAP = cumulative minute (H+L+C)/3 x volume / cumulative volume, from the first minute
of each source session (Chicago + 8 h; one session per source date). Each date trades one contract,
so VWAP never mixes contracts. A20 = arithmetic mean of the last 20 completed M30 true ranges.
z = (signal close - VWAP) / A20, from the latest M30 feature whose available_at (bar start + 30 min)
is at or before submission. **Far below: z < -1.** A feature from an earlier session, or a missing
A20, is unknown, and the trade is kept. Nothing else is tested: no other threshold, anchor, price,
window, volume source or exit.

## Measures

For every sample, baseline (all trades) and rule (far-below trades removed from the ledger; this is
not a replay, so orders freed by skipped trades are not modelled): trades, net $, net mean R, PF,
planned risk and holding time kept, daily-close max DD on the full session calendar (flat days
included, starting from zero at the sample start), closed-trade DD, longest daily DD, worst session
and week, +$1 and +$2 cost stress.

**A. Risk-matched contrast.** Within each era, sort trades by planned risk (ties by submission time)
and cut them into 10 equal-count deciles (sizes differ by at most one). In each decile: mean net R of
far-below trades minus mean net R of all other trades, unknowns included. Report every difference,
how many are negative, and the weighted mean (weights = far-below trades per decile; pooled samples
combine both eras' deciles). 95% interval: circular 4-calendar-week block bootstrap over the
sample's calendar weeks, empty weeks kept, 5,000 draws; each draw recomputes every decile difference
and weight, leaving out (and counting) deciles that lack either group.

**B. Placebos that skip without VWAP.** 2,000 draws each, on the pooled sample. Every cell lies
within one era, so era results use the same draws restricted to each era. Placebos may skip
unknown trades; the rule never does.

1. Risk decile: in each decile, skip as many non-far-below trades as it has far-below trades, chosen
   at random. If there are too few, skip them all and report the shortfall.
2. Rolled within month: in submission order, roll the actual skip pattern circularly within each
   calendar month by a random offset. This keeps each month's count and the runs of consecutive skips.
3. Month x risk tertile (descriptive): as 1, within calendar-month x risk-tertile cells; tertiles
   are cut like the deciles.
4. Largest risk (descriptive, deterministic): in each era, skip as many trades as the rule skips
   there, choosing the largest planned risks.

Report net $, daily-close DD and planned risk kept. "Rule beats" = the share of draws whose DD is
above the rule's DD (ties count against the rule); the same for net $.

**C. Descriptive only.** The NQ study's unadjusted far-below contrast and its time-block x
risk-tertile adjustment; the baseline scaled to the rule's holding time; annual results; the
roll-clean subset (no roll in the 21 bars behind A20); co-movement with NQ: NQ's `full_hlc3` label at
the same submission time, the share of far-below trades on which NQ was also far below, and contrast
A restricted to trades on which NQ was not far below.

Seeds: bootstrap 202610270 + k, placebos 202610280 + k; k = 0 NQ, 1 ES, 2 YM, 3 RTY. Each generator
serves its instrument's primary (or reference) sample first, then its secondary sample.

## Verdict, fixed now

An instrument **confirms** the NQ result if, on its pooled primary sample:

1. contrast A is below zero and its whole 95% interval lies below zero;
2. the rule's daily-close DD beats at least 95% of draws of placebo B1 and at least 95% of B2; and
3. in each era, contrast A is below zero and the rule's DD is below the median DD of B1 and of B2.

An instrument with fewer than 200 far-below trades or 30 active weeks in an era is inconclusive,
which counts as not confirming. Overall: **transfers** if at least two of ES, YM and RTY confirm;
**partial** if one; **does not transfer** if none. This is one test with one verdict: the secondary
samples (tests 1-2; test 3 needs two eras) and the descriptive outputs are not extra chances to pass.

What follows:

- Transfers: the drawdown rule has support beyond NQ's history. Next: a forward shadow test of the
  unchanged rule on NQ, including a check that the live volume source gives the same labels. Still
  no live change from history alone, and no claim about profit.
- Partial or does not transfer: treat the NQ result as possibly specific to NQ's history. No rescue:
  no other thresholds, anchors, instruments or periods on these data. The rule stays a forward
  candidate only.

Limits, stated in advance. RTL loses money on ES, YM and RTY, so confirming means the signal
transfers, not that RTL should trade them. On a losing sample, drawdown mostly reflects the total
loss, so test 2 there largely repeats the dollar contrast; test 1 does not depend on it. Index
futures fall on the same days, so these instruments are not independent of NQ; the co-movement
diagnostic shows how much each adds.

## Outputs and verification

`Reports/rtl_vwap_cross_20261027/` (gitignored): parsed trades and source audits, features, labelled
trades, summaries, contrast and bootstrap draws, placebo draws, the verdict table, and provenance
with hashes. An independent script rebuilds the trades from the reports and VWAP/A20/z for every
labelled trade from raw minutes with separate code, recomputes every summary, contrast and the
verdict, and checks the placebo invariants. Tests: session reset gives unknown, availability
boundary, signal-bar check, placebo counts. One compact chart. Results go to `CROSS_RESULTS.md` in
this folder, with plan, journal and status updated.

## Inputs at freeze (SHA-256)

| File | SHA-256 |
|---|---|
| `F:\DATABENTO\ES_16_YEARS\MT5_ES_continuous_2010-2026_ohlcv-1m.csv` | `433cd1ee3f0f3c8b9d644849b75290927a80e8e5d5ff869e6781a53c5ee966a5` |
| `F:\DATABENTO\ES_16_YEARS\MT5_ES_continuous_2010-2026_rolls.csv` | `7fdadb910fc8797bcb3a8d591ecd5e264df783bac78e50552bfff10e72432b56` |
| `F:\DATABENTO\YM_16_YEARS\MT5_YM_continuous_2010-2026_ohlcv-1m.csv` | `bc9f4ceb85c32ad856faeb5f1bda31d02006c98d9bbb5c941d1969388fb5cea5` |
| `F:\DATABENTO\YM_16_YEARS\MT5_YM_continuous_2010-2026_rolls.csv` | `a43f1072b26a45f6d835e3f0d10833875ca6515ed318d12db4cdec60831c34db` |
| `F:\DATABENTO\RTY_16_YEARS\MT5_RTY_continuous_2017-2026_ohlcv-1m.csv` | `0d039c8cda8311ee4e26937a2d5512652654466853c56fe91781a59ac39d349c` |
| `F:\DATABENTO\RTY_16_YEARS\MT5_RTY_continuous_2017-2026_rolls.csv` | `6bbf3e99ac7389417eef24a332660c66f2bb15a999a8d0ab3609d5f919597943` |
| `F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv` | `df3390928189f0d12c2140c3994671998151d8cb7289189b6f8a8ad83ff74e6a` |
| `F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_rolls.csv` | `7421df167e9bcdcdd21a310395f388e041d50de4ed42d987095c5596109be49d` |
| `Reports/ym_baselines_20261023/ymbase_20261023_rtl_es.htm` | `1e30301889f3bc164f186d8149672cb945e57a7d2a72afdb8b737e88d6174e81` |
| `Reports/ym_baselines_20261023/runband_ymbase_20261023_rtl_es_1.00.csv` | `78df4a367427fa81a6831ce6cb3d12c453cfb8dacc573f9e46c9d006ef96c0b3` |
| `Reports/ym_baselines_20261023/runband_ymbase_20261023_rtl_es_1.00_stats.csv` | `4470e5846fc9fdabe61697bc59907d71b30d009ce1899d8ede71568176728393` |
| `Reports/ym_baselines_20261023/ymbase_20261023_rtl_ym.htm` | `741c3ec4810088c4f6f491d77cb34e950c7bf5d721f7a0b80558d429823578f0` |
| `Reports/ym_baselines_20261023/runband_ymbase_20261023_rtl_ym_1.00.csv` | `012e8c1213ce1fa09a77ccdca30910df5398b6cbfa8b82889736b74b59a88416` |
| `Reports/ym_baselines_20261023/runband_ymbase_20261023_rtl_ym_1.00_stats.csv` | `b5c132502832f422c7d79cf7e444167936a381919a88b8eed653c7d2d4445148` |
| `Reports/rty_baselines_20261023/rtybase_20261023_rtl.htm` | `3da4d2f36bde2c21f19a087a0686d4d999a2730be7f45ef2d38820c27286c580` |
| `Reports/rty_baselines_20261023/runband_rtybase_20261023_rtl_1.00.csv` | `fe0aeee980857bb96613dac6a29f5726ef68c4ba108f98909b4632a9497d9479` |
| `Reports/rty_baselines_20261023/runband_rtybase_20261023_rtl_1.00_stats.csv` | `13e1df0e1b4ad1e84a63b2028646a8294635fd5905c250b8065f0d5eae1201d1` |
| `Reports/ym_baselines_20261023/ymbase_20261023_rtl_nq.htm` | `6b724f98866f81d8493f4a317bd841d6fe16633761ca0004e1c31f8ff8cd48c2` |
| `Reports/ym_baselines_20261023/runband_ymbase_20261023_rtl_nq_1.00.csv` | `88c0d6144b1ce8ecc937a8f5333188240bc41b6cf241cef2e3778dde7bd752e5` |
| `Reports/ym_baselines_20261023/runband_ymbase_20261023_rtl_nq_1.00_stats.csv` | `a9be3898eb2d75fee95df2a94452682ee8941e1fce5964d6d76f6ff713723ee2` |
| `Reports/rtl_vwap_20261025/trades.csv` (NQ reference panel) | `1a3fbb6b4303ec6c72d2b2c85c9d9db1303ec66fd398a9ff5ea1c2af8ea91365` |
| `python/build_rtl_vwap_features.py` | `1dd7adc771100f80570b8ce608f3a11d3fc0a81c4c103536c6de119bbbfc51e4` |
