# RTL price structure: daily chop and M30 overlap/wicks

2026-10-24. Exploratory historical study. Current uncapped RTL only.
[Frozen protocol](PROTOCOL.md) | [Original research plan](../rtl-market-regimes/PLAN.md)

**No skip rule is supported by the tested definitions.** M30 low efficiency plus
high overlap is profitable in both eras. Adding persistent wicks does not produce
a consistently losing subset. Daily structure is weaker and offers a modest
historical profit/drawdown tradeoff, but sensitivity and uncertainty do not support
adopting a filter. No strategy defaults or live trading settings were changed.

## 1. Completed structure and fixed calibration

Study population: **16,668 trades**, 6,167 in 2016-19 and 10,501 in
2020-September 2026. Baseline net dollars are **$4,416.65 / $38,399.95**, after
$1.05 per completed trade, one MNQ-valued contract, original stop and 1R bar-close
exit. Baseline mean net R is -0.01434 / +0.04759. Different initial dollar risks
explain why average per-trade R and total dollars can have different signs.

Twenty completed daily sessions are the main structural window; twenty completed
M30 candles separately address the user's intraday example. Ten and forty are
fixed sensitivity checks. All cutoffs use valid price windows available **before
2016**, with equal weight per price window and no calibration to trade outcomes.

| Twenty-bar measure | D1 cutoff | M30 cutoff |
|---|---:|---:|
| Low efficiency: absolute net close change / sum of absolute close changes | <= 0.12215 | <= 0.13514 |
| High overlap: mean adjacent shared-range / combined-span ratio | >= 0.46261 | >= 0.45625 |
| High wick: mean of 1 - absolute body / full range | >= 0.56350 | >= 0.56440 |

Daily labels use only earlier source dates. M30 labels include the completed
signal candle and freeze at actual buy-stop **submission**, not eventual fill.
This matters: some orders wait hours to fill. Windows span observed bars across
session gaps. Daily bars aggregate the research session (Chicago + 8h clock,
01:00 onward), which can differ from a broker's displayed D1 bars.

The supplied screenshot is dated October 22-23, beyond the saved source endpoint.
It motivates the structure hypothesis; these results do not classify its exact
candles. The incomplete October 1 session and its forced tester exit are excluded.

## 2. Four efficiency/overlap groups

All rows use the fixed twenty-bar definition. R is net return divided by planned
initial dollar risk, averaged per trade. Dollar results are one-contract totals.

| Timeframe | Group | Trades 2016-19 / recent | Net $ 2016-19 | Net $ recent | Net R/trade 2016-19 / recent |
|---|---|---:|---:|---:|---:|
| D1 | Low efficiency, high overlap | 476 / 975 | -19.80 | 1,213.75 | -0.0492 / +0.0045 |
| D1 | Low efficiency, other overlap | 1,219 / 2,017 | -436.45 | 7,619.65 | -0.0040 / +0.0365 |
| D1 | Other efficiency, high overlap | 1,110 / 1,661 | 1,214.00 | 2,809.45 | -0.0336 / +0.0504 |
| D1 | Other efficiency, other overlap | 3,362 / 5,848 | 3,658.90 | 26,757.10 | -0.0068 / +0.0578 |
| M30 | Low efficiency, high overlap | 748 / 1,214 | 1,070.60 | 9,089.30 | +0.0547 / +0.0998 |
| M30 | Low efficiency, other overlap | 1,165 / 1,920 | 803.25 | 3,795.00 | +0.0012 / +0.0055 |
| M30 | Other efficiency, high overlap | 1,474 / 2,556 | 1,460.80 | 11,036.70 | -0.0121 / +0.0861 |
| M30 | Other efficiency, other overlap | 2,780 / 4,811 | 1,082.00 | 14,478.95 | -0.0406 / +0.0308 |

Daily low-efficiency/high-overlap observations have lower mean R than their
complement in both eras, but both adjusted 97.5% difference intervals include
zero: [-0.1392, +0.0790] and [-0.1553, +0.0652] R. Its early dollar loss is just
$19.80, and its recent dollar result is positive.

The corresponding M30 group has higher observed mean R than its complement in
both eras. Its adjusted difference intervals also include zero: [-0.0296,
+0.1887] and [-0.0339, +0.1520] R. That is not proof of superiority, but it
provides no basis for avoiding the group.

### Fixed neighboring windows and rolls

| Timeframe | Window | Candidate net $ 2016-19 | Candidate net $ recent |
|---|---:|---:|---:|
| D1 | 10 | 157.35 | 6,080.15 |
| D1 | 20 | -19.80 | 1,213.75 |
| D1 | 40 | -215.65 | 4,417.15 |
| M30 | 10 | 577.75 | 9,607.50 |
| M30 | 20 | 1,070.60 | 9,089.30 |
| M30 | 40 | 485.95 | 3,895.35 |

After excluding twenty-bar histories touching a contract switch, the M30
candidate remains positive: **$1,090.25 / $8,997.85**. The daily candidate becomes
negative in both eras (-$451.75 / -$690.15), but the early subset has only **22
active weeks**, below the frozen coverage requirement. The recent ten/forty-bar
daily candidates remain positive after roll exclusion. Daily roll-clean coverage
is about 67-68% of baseline trades at n=20 and only 36% at n=40, so that sensitivity
substantially changes the sample. The comparison baseline is restricted to the
same eligible observations.

Annual signs vary. The twenty-day candidate loses in 2016, 2019, 2020 and 2023
among the ten complete evaluation years, and in partial 2026. The M30 candidate
loses only in 2017 and 2021 among those full years. No robust negative-edge
follow-up passes the protocol's requirements.

## 3. Persistent wick diagnostic

The eight efficiency/overlap/wick cells for each timeframe and era are preserved
in the calculated tables. Two M30 subsets directly address the user's example:

| M30 twenty-bar subset | Trades 2016-19 / recent | Net $ 2016-19 | Net $ recent | Net R/trade 2016-19 / recent |
|---|---:|---:|---:|---:|
| High overlap + high wick, regardless of efficiency | 1,205 / 2,066 | 1,134.75 | 10,900.20 | -0.0352 / +0.1051 |
| Low efficiency + high overlap + high wick | 369 / 637 | 297.55 | 1,985.15 | +0.0137 / +0.0611 |

The broader wick/overlap subset remains positive in dollars at n=10 and n=40 in
both eras. The triple condition loses $239.85 in early n=10, but makes $4,926.65
recently; its n=40 results are +$8.65 / +$4,154.00. Neither consistently identifies
negative dollar expectancy. After roll exclusion, the n=20 wick/overlap subset
earns $1,149.50 / $10,667.85.

For the recent broad wick/overlap subset, the nominal 95% difference interval
versus its complement is **[+0.0012, +0.1424] R**. It is exploratory and not
adjusted for the full diagnostic family; it does not justify increasing exposure.
It also provides no evidence for skipping that subset.

The broad wick/overlap subset's mean initial risk is $19.63 / $70.15, with mean
commission burden 0.1039 / 0.0259 R. Its early negative mean net R coexists with
positive dollars; those are different weighting schemes, not a calculation error.

**Scope of the wick definition:** high wick means a twenty-candle average above
56.44%, not that nearly every candle has a tiny body. Within the broad selected
subset, average wick fraction is about 61%; the average fraction of candles with
at least 80% wick is roughly 28% across selected, overlapping trade windows.
These results do not exhaustively test every extreme
visually recognizable cluster. Wicks measure retracement; actual repeated failed
breakouts were not measured in this study.

## 4. Losses avoided, gains missed and comparable exposure

The following are **ledger-omission diagnostics**, not full strategy replays.
They retain the original trades that pass the label; a working gate could change
later order availability. Drawdown is realized equity, not intratrade equity.

| Recent-period scenario | Net $ | Closed-trade DD $ | Daily-close DD $ |
|---|---:|---:|---:|
| All RTL | 38,399.95 | 5,781.15 | 5,781.15 |
| Omit D1 low efficiency + high overlap | 37,186.20 | 5,146.30 | 4,951.55 |
| Static baseline at same D1 retained holding exposure | 34,924.59 | 5,257.93 | 5,257.93 |
| Omit M30 low efficiency + high overlap | 29,310.65 | 6,262.20 | 5,785.10 |
| Static baseline at same M30 retained holding exposure | 34,235.05 | 5,154.12 | 5,154.12 |
| Omit M30 high overlap + high wick | 27,499.75 | 5,953.80 | 5,575.30 |
| Static baseline at same wick/overlap retained holding exposure | 31,265.92 | 4,707.11 | 4,707.11 |
| Omit M30 triple condition | 36,414.80 | 5,781.25 | 5,385.80 |
| Static baseline at same triple-condition retained holding exposure | 36,301.26 | 5,465.19 | 5,465.19 |

- Omitting the M30 main candidate avoids **$44,616.30** of losing-trade dollars
  but misses **$53,705.60** of winning-trade dollars recently. Net profit falls
  about 24%, while closed-trade drawdown increases.
- Omitting the M30 wick/overlap subset avoids **$73,400.90** but misses
  **$84,301.10**, reducing net profit by **$10,900.20**. It also underperforms
  simple exposure scaling on both recent profit and drawdown.
- Daily omission avoids $39,605.90 and misses $40,819.65. It retains about **97%
  of profit** while reducing daily-close drawdown about **14%** and holding
  exposure about 9%. This is a modest historical risk-reduction hint. However,
  early daily-close DD is $2,027.95 versus $1,988.07 for the matched static control,
  and the fixed sensitivities do not establish a stable unfavorable state.

The triple M30 condition has only a small recent profit/daily-DD advantage over
static scaling and worse closed-trade DD; early results are worse than static
scaling. It is not a consistent improvement.

Each omission has 2,000 seeded circular-shift placement controls, preserving
skip count and run lengths in trade order. After matching retained holding
exposure, about 25% of recent daily-control placements earn at least as much
as the actual daily omission, and 24% have drawdown as low. The observed result
is not exceptional within that control. For M30 main omission, about 90% of
placements earn at least as much and 73% have drawdown as low. These are
dependent descriptive comparisons, not p-values or randomized causal evidence.

Static scaling is fractional portfolio arithmetic, not executable one-contract
sizing. Matching holding exposure does not match initial risk exactly; the saved
tables also report retained trade-count and planned-risk fractions.

### Cost stress

With an extra $1 / $2 per trade, the recent M30 main candidate remains positive
at $7,875.30 / $6,661.30. The weaker recent daily candidate falls from $1,213.75
to $238.75 / -$736.25. In the early era the entire baseline loses under either
additional allowance, so that result does not uniquely implicate daily chop.
These are assumed allowances, not measured execution costs.

## Verification and reproducibility

Protocol SHA256: `dcde54820c8f914b64f5e51d801c7b6a34e9d5ead3b0734d92d273cb829e2729`.
**Independent verification: PASS.** Rebuilt all 5,511,965 original minutes into
191,786 M30 OHLC bars and 4,203 daily bars; exact agreement. Reconciled all 25,833
source trades and 16,668 primary trades. Independently checked all six feature
panels, calibration cutoffs, submission-time joins, 584 outcome/coverage rows,
20 bootstrap rows (10,000 paired draws per era), 24 omission portfolios, all
16,000 circular-shift draws and the session curves. All **12 focused tests pass**.
The original source hashes and frozen protocol remain unchanged. See the
[hash-bound verification record](../../../Reports/rtl_price_structure_20261024/independent_verification.json).

Programs:
- `python/analyze_rtl_price_structure.py`: reproducible calculations and provenance.
- `python/verify_rtl_price_structure.py`: independent source/feature/outcome audit.
- `python/test_rtl_price_structure.py`: mathematical and causal boundary tests.
- `python/report_rtl_price_structure.py`: tables and static figure.

Run from the project root with its `venv/Scripts/python.exe`. Outputs are in
`Reports/rtl_price_structure_20261024/`, including feature panels, trade labels,
thresholds, all summary/annual/wick/roll tables, bootstrap intervals, controls,
session curves, and source/output SHA256 manifests.

[Calculated tables](../../../Reports/rtl_price_structure_20261024/report_tables.md)
and [diagnostic figure](../../../Reports/rtl_price_structure_20261024/structure_diagnosis.png).
All history has been used in prior research; chronological splits are not pristine
holdouts. This study retains the existing one-minute OHLC execution qualification.
No live filter is adopted and no complete gated-strategy replay is claimed.
