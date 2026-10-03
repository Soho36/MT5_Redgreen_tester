# Q9: recovery speed and the two-sided explanation

**Archived research direction, 2026-10-03.** The user redirected the work to
broad M30 support interaction and actual trade outcomes. These results remain
historical evidence. [Archive note](SPEED_RESEARCH_ARCHIVE.md) ·
[Current direction](README.md).

2026-10-03 · [Frozen protocol](../RECLAIM_SPEED_PROTOCOL.md) ·
[Analysis](../../python/analyze_reclaim_speed.py) ·
[Full tables](../../Reports/levels/reclaim_speed_20261003/report.md).

## Answer

**A quick recovery does not establish a reliable upward advantage after the M30
signal closes. The earlier +0.5R association is substantially two-sided in the
recent period, and its interpretation changes when the signal range is replaced
with volatility measured before the signal. No speed filter or earlier-entry
strategy is adopted.**

This is a diagnostic within the existing RTL signal population. It does not
rule out a short-lived bounce immediately after recovery, or an effect in a
different population of support interactions. Those need a causal minute-entry
study, not selection by the eventual M30 signal.

## What speed means here

Reuse Q8's 35,632 logged order attempts, including unfilled attempts. Current-
session low is primary; previous-session/week lows remain separate comparisons.
Each reference level was known before the signal opened, with the existing
session and contract-roll exclusions.

For signals that breach from above and finish above the low, measure the delay
from the first below-level minute's open to the first minute close above the
level. **Fast = 1–2 minutes; middle = 3–5; slow = 6 or more.** A same-minute
recovery is an upper-bound proxy of one minute, not an exact duration. An early
recovery may subsequently fail and recover again; this is first recovery speed,
not sustained recovery. Below-level close counts and recrossings are exported.
Approach speed is exported but was not selected as an outcome-conditioned rule.

All responses start at the completed M30 signal close, at fixed 30/90/180-minute
horizons. R is the signal range. A is the simple average of the preceding 14
M30 true ranges, excluding the signal and resetting history at contract rolls.
It is not the EA's trade risk or a fitted indicator setting.

## Fast versus slow at comparable depth and volatility

One-to-one matching without replacement, within each period and calendar year:
depth/A, A and signal range/A within a factor of two; breach position within
five minutes; time of day within two hours. All matching information is known
at the M30 close. Calipers were not relaxed after looking at results.

| Current-session low, 90 minutes | 2016–19 fast | 2016–19 slow | 2020–26 fast | 2020–26 slow |
|---|---:|---:|---:|---:|
| Matched events | 130 | 130 | 218 | 218 |
| Endpoint >= +0.5R | 34.6% | 36.2% | 28.4% | 32.6% |
| Endpoint <= -0.5R | 27.7% | 26.9% | 27.5% | 29.4% |
| Mean endpoint R | +0.103 | +0.044 | +0.027 | +0.049 |
| Mean endpoint A | +0.129 | +0.041 | +0.073 | -0.006 |
| A endpoint directional balance | +10.8 pp | +13.1 pp | +1.8 pp | +7.3 pp |

Directional balance = P(endpoint >= +0.5A) minus P(endpoint <= -0.5A).
Fast minus slow, with descriptive 95% calendar-month block intervals:

| Difference | 2016–19 | 2020–26 |
|---|---:|---:|
| Mean A return | +0.089 [-0.215, +0.402] | +0.079 [-0.197, +0.360] |
| A directional balance | -2.3 pp [-19.9, +15.8] | -5.5 pp [-19.4, +9.0] |
| +0.5R endpoint probability | -1.5 pp [-11.1, +8.3] | -4.1 pp [-12.8, +4.7] |

The estimates are imprecise. Positive mean-A differences alone do not establish
an edge, particularly when the directional-balance estimates go the other way.
The result is insufficient evidence for the proposed advantage, not proof of
equivalence or of a negative speed effect.

Before matching, complete/valid-A fast/slow groups contain 554/166 earlier and
1,370/275 recent events. Raw fast recoveries are substantially shallower and
occur later within the M30 signal. Matching reduces log-depth standardized
differences from -1.27/-1.33 to -0.25/-0.22; residual imbalance remains. Other
matched covariates have absolute standardized differences <=0.12. This is an
observational comparison on a limited overlap population, not randomization.

## Does the +0.5R excess mostly represent two-sided movement?

The original full endpoint cohorts reproduce exactly:

| Reclaim minus unrecovered, current-session low | 2016–19 | 2020–26 |
|---|---:|---:|
| Extra >= +0.5R endpoints | +6.1 pp | +3.1 pp |
| Extra <= -0.5R endpoints | +1.7 pp | +3.9 pp |
| Mean endpoint R difference | +0.071R | -0.020R |

**Yes for the recent R-normalized result; less completely for the earlier
period.** Recently, the lower tail increases more than the upper tail. Earlier,
the upper-tail increase is larger, but mean-return uncertainty still includes
zero. Neither case supports inferring a target-win rate from the upper tail.

There is also genuinely two-sided *path movement*: on complete future minute
paths, both +0.5R and -0.5R are reached within 90 minutes in **25.7% of reclaim
cases versus 19.3% of unrecovered breaches**, in each period after rounding.
These are different complete-path samples: 837/1,615 earlier and 1,986/3,395
recently. Around 47% of reclaim paths reach the upper threshold first and 47%
reach the lower one first. Same-minute ambiguity is retained separately.
These are barrier touches from the signal close, not executable fill outcomes.

### A substantial part is the choice of denominator

Reclaim signal ranges average 16.3 versus 20.2 points earlier, and 50.2 versus
67.5 recently. Half of a smaller signal range is an easier threshold to reach
in either direction. The fixed pre-signal volatility scale gives a different
picture on all Q8 endpoints with valid A:

| 90-minute outcomes in A | 2016–19 reclaim | 2016–19 unrecovered | 2020–26 reclaim | 2020–26 unrecovered |
|---|---:|---:|---:|---:|
| Valid endpoints | 1,008 | 1,958 | 1,989 | 3,414 |
| Endpoint >= +0.5A | 37.7% | 36.3% | 33.3% | 35.4% |
| Endpoint <= -0.5A | 27.5% | 29.3% | 29.4% | 29.4% |
| Mean absolute endpoint A | 1.159 | 1.254 | 1.103 | 1.205 |
| Both +/-0.5A touched, complete paths only | 38.1% | 41.4% | 33.7% | 38.2% |

Thus reclaims do **not** simply predict more volatility in comparable units.
The excess of large R moves is consistent with smaller signal ranges, as well
as differences between the populations. It is not evidence that stop orders
were consumed, and the normalization comparison does not prove a sole cause.

The complete-signal, valid-A pool also shows the recent result clearly:
reclaim minus unrecovered has +3.0 pp upper-R endpoints [0.3, 5.8], +3.8 pp
lower-R endpoints [1.4, 6.1], and -0.8 pp R directional balance [-5.2, 3.8].
In A, its upper-tail difference is -2.0 pp [-4.5, 0.5], lower-tail difference
-0.1 pp [-2.4, 2.4], and mean absolute movement difference -0.101A
[-0.171, -0.028]. These intervals use that pool, not the full table above.

Matching reclaim to unrecovered breaches leaves 572 pairs earlier and 1,224
recently. Their +0.5R probability differences become -2.4/-0.8 pp; both
intervals include zero. Mean-A differences are -0.011/+0.049, also with
intervals including zero. Neither normalization nor matching uncovers a
consistent directional benefit.

## Sensitivities and distant levels

- Fast <=1 and <=3 minutes versus the same slow group both have negative
  matched 90-minute A-balance differences in each period. No cutoff qualifies.
- At 30 minutes the matched mean-A differences are +0.028/-0.030; at 180 they
  are +0.377/+0.165. Direction and horizon do not satisfy the predefined
  consistency rule. No alternative horizon was adopted after inspection.
- Previous-session lows yield only **10/22** primary matched speed pairs;
  previous-week lows only **2/2**. These cannot support a conclusion about
  distant major levels. Older confirmed swing levels remain untested.
- All three frozen candidate gates fail. This does not justify promoting
  speed to an RTL filter or claiming an earlier-entry edge.

## Python versus an MT5 EA

Python answers this event-study question without a new EA: it can reconstruct
known levels, classify minute paths, compare symmetric outcomes and audit
sampling differences. It can also simulate explicit trading rules, with a
chronological event loop for orders, fills, stops, exits, costs and position
availability. Removing rows from the old trade CSV is not that simulation.

For an immediate reclaim-entry experiment, start a **new causal event cohort**
at a completed-minute reclaim; do not condition entry on the eventual M30 red
candle, final reclaim, completed range or future low. Freeze the level map,
entry timing, protective stop, target/time exit, cancellation and repeated-
crossing rules. Evaluate gains and losses after costs, including failed and
unfilled attempts. This would answer a different question from Q9.

An MT5 EA is useful for validating that full execution model in the intended
platform and, if warranted, forward testing it. The project requires a full
MT5 rerun before adopting an RTL change. However, an EA tested on the same M1
OHLC does not supply historical tick order, seconds spent below a level or real
fills. No new EA or generated-tick run was needed for Q9.

## Verification and limitations

- Verified 19 upstream input/code/protocol hashes before analysis.
- Reconstructed 125,316 M30 bars from 3,712,172 source minutes, exactly matching
  the saved Q8 reference over this interval.
- Checked all 35,632 unique signal OHLC and 100,206 available forward
  endpoints and excursion windows against source minutes.
- 33,703 signals have every expected minute; 1,929 do not. Speed is unavailable
  for incomplete signals. At the primary reclaim horizon this excludes 96/1,012
  earlier and 5/2,000 recent signals. Ordered paths require complete future
  minutes separately. Selection due to missing data remains a limitation.
- Lagged volatility needs 14 prior same-contract bars. A zero lagged scale
  observed during a flat stretch is explicitly unavailable for A normalization;
  the corresponding R outcomes remain. No division by zero is retained.
- Eight unit tests cover minute timing, equal-price cases, transient recoveries,
  ambiguous barrier order, invalid scale outputs, lag/roll behavior and matching.
  Independent checks verify 3,263 saved pairs, 446 signal paths, 300 future
  paths, all response partitions, and exact preservation of Q8 input columns.
  Ten Q9 dependency hashes pass. Results are saved in `verification.json`
  alongside the report.
- All historical data have already been inspected. Month-block intervals use
  2,000 common calendar-month resamples, fixed matching, and no multiple-test
  adjustment. Matches may cross months; the blocks preserve calendar dependence
  rather than resampling matched pairs as independent observations.
- No PnL, fill assumption, causal liquidity mechanism, sub-minute speed effect,
  or result for all support interactions is established by this study.

Reproduce with the project venv:

```powershell
.\venv\Scripts\python.exe python\analyze_reclaim_speed.py
.\venv\Scripts\python.exe python\verify_reclaim_speed.py
.\venv\Scripts\python.exe -m unittest discover -s python -p test_reclaim_speed.py -v
```
