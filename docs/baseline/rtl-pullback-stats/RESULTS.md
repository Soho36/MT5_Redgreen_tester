# Pullback and bounce warnings: "down a lot" finds lows, "up a lot" barely finds peaks

2026-10-25. Exploratory price statistics, step 2 of the user's idea.
[Frozen protocol](PROTOCOL.md) | [Early-signal crystal ball](../rtl-downtrend-oracle/EARLY_RESULTS.md)

**The bounce warning works as a statistic; the pullback warning mostly does not.**
After an unusually large fall over 5, 10 or 20 sessions, the low of a 2-5% drop
comes within two sessions 21-53% of the time: 1.8-4.9x the volatility-matched
base rate, every predictor, size and era, and under every sensitivity. After an
unusually large rise, the peak comes within two sessions only 6-38% of the time,
with 17-84% outright false alarms; it passes the fixed test only for 5% drops
with the 5-session rise. **Rallies do not get tired:** the older a rally, the
less likely its peak is near. By the fixed rule, an RTL test is worth designing
for 5% drops only. No RTL trades were used here; nothing about the strategy changed.

## How to read the numbers

- **Turns** come from the hindsight zigzag of the crystal-ball study (2%, 3%, 5%
  drops on roll-adjusted daily closes). They are the truth being predicted.
- **Signals** are known at each session's close. Pullback warning: the rise over
  n = 5, 10 or 20 sessions is in the top 10% of all such rises before 2016.
  Bounce warning: the move is in the bottom 10%. Each comes as a plain % move and
  as a move scaled by the last 20 sessions' volatility (6 + 6 predictors).
- **A hit** is a turn within 2 sessions: the early-signal study showed two
  sessions early still pays.
- **Base rates** say how often a turn is that close anyway. The volatility-matched
  base compares like with like, because busy markets have more of everything.
- **Shifted signals** slide each signal series through the era. Signals bunch
  together in a few episodes, so many signal days can be one event. Beating 97.5%
  of shifts guards against that.
- Fixed pass test: at least 30 signals, 1.25x both base rates, above 97.5% of
  shifts, in BOTH 2016-19 and 2020-September 2026.

## 1. How long drops and rallies last (sessions, median and 10th-90th percentile)

| Drop size | Falls, 2016-19 | Falls, 2020-26 | Rallies, 2016-19 | Rallies, 2020-26 |
|---|---|---|---|---|
| 2% | 4 (2-11) | 4 (2-13) | 10 (2-41) | 5 (1-20) |
| 3% | 9 (3-16) | 6 (2-20) | 18 (4-86) | 7 (1-41) |
| 5% | 15 (9-21) | 15 (4-21) | 66 (8-145) | 11 (3-86) |

Falls are short and fairly regular; rallies vary enormously. 2020-26 is much
choppier than 2016-19 at every size.

## 2. Pullback warning: "up a lot, so a peak is near"

Volatility-scaled and plain rises both find peaks somewhat more often than the
base rate (volatility-matched lift 1.1-4x), but:
- Hit rates stay low: 6-38% of signals have a peak within 2 sessions.
- Many are false alarms (no peak within 10 sessions): 17-84%.
- In 2016-19 most fail the shift test. Strong rallies come in a few clusters, so
  63-109 signal days are only a handful of independent events.
- Only the 5-session rise for 5% drops passes in both eras (hit rate 9.9% /
  13.3% versus 3.2% / 6.9% base). One pass out of six predictors is weak evidence.

**Rallies do not get tired** (hindsight ages, so this is a description, not a
signal). Chance that the peak comes within 2 sessions, by sessions since the low:

| Drop | Era | 1-2 | 3-5 | 6-10 | 11-20 | 21+ |
|---|---|---:|---:|---:|---:|---:|
| 2% | 2016-19 | 26% | 24% | 15% | 14% | 12% |
| 2% | 2020-26 | 39% | 35% | 26% | 29% | 22% |
| 3% | 2016-19 | 8% | 16% | 13% | 12% | 6% |
| 3% | 2020-26 | 27% | 29% | 20% | 16% | 12% |
| 5% | 2016-19 | 0% | 6% | 7% | 4% | 4% |
| 5% | 2020-26 | 21% | 21% | 17% | 5% | 7% |

The longer a rally has run, the less likely it is about to end. "It has gone up
for a long time, so a pullback is due" is the opposite of what happened.

## 3. Bounce warning: "down a lot, so a low is near"

| Drop | Low within 2 sessions, 2016-19 / 2020-26 | Volatility-matched base | Lift | Low 3-10 sessions away | Already past the low |
|---|---|---|---|---|---|
| 2% | 37-50% / 41-53% | 15-20% / 22-24% | 1.8-3.4x | 19-35% | 10-38% |
| 3% | 28-43% / 36-43% | 9-13% / 14-16% | 2.1-4.1x | 22-38% | 11-45% |
| 5% | 21-27% / 28-35% | 5-7% / 8-10% | 2.8-4.9x | 21-39% | 16-38% |

All six bounce predictors pass at every size in both eras, on both series, at
k = 1, 2, 3 and at the 80th/20th cutoffs. The 5-session versions are the
timeliest; 20-session falls are more often flagged after the low has passed.

**Is it just "we are in a fall"?** Check after the run, not in the protocol: a
bounce warning can only fire after a fall, and lows can only be near during a
fall. Compared with simply knowing a fall is underway (the live zigzag has
confirmed it), the 5-session warning still helps:

| Drop | Low within 2 sessions, any confirmed-fall day | With the 5-session warning |
|---|---|---|
| 2% | 36% / 41% | 52% / 51% |
| 3% | 25% / 30% | 45% / 44% |
| 5% | 16% / 22% | 34% / 39% |

A lift of 1.25-2.1x over that stricter base. Smaller than the headline lift, but
real in both eras.

![Warning signals and rally age](../../../Reports/rtl_pullback_stats_20261025/warnings.png)

## 4. Decision and what it means for RTL

**Fixed rule:** an RTL test is worth designing for a drop size only if a stop and
a resume predictor both pass. That holds for 5% drops only (stop: 5-session rise;
resume: all six); unadjusted closes agree.

Reading this with the earlier studies:
- The information sits on the resume side, which the early-signal study found
  matters more: a late resume gives up the rebound, the costliest window.
- The stop side is weak. Waiting for a rally to "look stretched" mostly produces
  false alarms, and a stop that fires in a continuing rally skips some of RTL's
  best sessions.
- One natural combination is outside this protocol's rule: stop on the live
  zigzag's confirmation (late, but a late stop cost less than a late resume) and
  resume on the bounce warning. Testing it would need its own frozen protocol.

## Limits

Price statistics only: a good hit rate does not yet mean better RTL results.
Turns are hindsight pivots. Twelve predictors x three sizes were compared;
agreement across predictors, eras and series is what makes the bounce result
credible, while the single 5% stop pass may be chance. Section 3's
confirmed-fall comparison was chosen after seeing the results. All history has
been used before.

## Verification and reproducibility

Protocol SHA256 (CRLF-normalized):
`e8322dd0e12e3bfe1485d2c0231e610fa3ea6e04ccb155039ebd6d87120e3461`, checked before
and after. **Independent verification: PASS** (10 of 10, all 864 statistic
rows): features by explicit loops, cutoffs by hand-written interpolation,
targets from session sets, rates, volatility matching, every circular shift by
np.roll, timing classes, leg lengths, hazards and the decision, using the
crystal-ball verifier's separately written zigzag. **All 7 focused tests pass.**

- `python/analyze_rtl_pullback_stats.py`, `python/verify_rtl_pullback_stats.py`,
  `python/test_rtl_pullback_stats.py`, `python/report_rtl_pullback_stats.py`.
- Outputs: `Reports/rtl_pullback_stats_20261025/`;
  [calculated tables](../../../Reports/rtl_pullback_stats_20261025/report_tables.md).
