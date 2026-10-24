# Pullback and bounce warning statistics: frozen protocol

2026-10-25. Written before any statistic below was calculated. Step 2 of the
user's idea: "if MNQ is up N% over n sessions, a pullback is more likely soon",
plus how long drops and rallies last. The [early-signal crystal ball](../rtl-downtrend-oracle/EARLY_RESULTS.md)
showed an early warning has room, but the resume matters more than the stop, so
a mirror "down N%, bounce soon" signal is tested too. Price data only; no RTL
trade outcomes are used here.

## 1. Data and truth

Roll-adjusted research-session daily closes c, 2010 through 2026-09-30, exactly
as in the [crystal-ball protocol](../rtl-downtrend-oracle/PROTOCOL.md); raw closes
are a sensitivity. Truth is that study's hindsight zigzag at drop sizes x = 2%,
3%, 5% (10% is too rare). Peaks P and troughs T are session positions.

- Stop target at session t: a peak lies in [t, t+k]. Stopping after t's close
  is then on time or at most k sessions early.
- Resume target at session t: a trough lies in [t, t+k].
- k = 2 primary (two early passed at every size); k = 1 and 3 reported.
- Evaluation ends k sessions before the last confirmed pivot of each size,
  since later targets are unknown. Eras 2016-19 and 2020-September 2026.

## 2. Signals, known at t's close

- Rise R_n = c[t]/c[t-n] - 1, n = 5, 10, 20 sessions.
- Volatility-scaled Z_n = ln(c[t]/c[t-n]) / (s_t * sqrt(n)), where s_t is the
  sample standard deviation of the last 20 daily log returns ending at t.
- Stop signal: R_n (or Z_n) at or above its 90th percentile. Resume signal: at or
  below its 10th percentile. Percentiles use all valid sessions before 2016 only;
  80th/20th are a sensitivity. Six stop and six resume predictors in total.

## 3. Statistics per size, predictor, direction, k and era

- Signal sessions; hits; hit rate P(target | signal).
- Base rate P(target) over all evaluation sessions.
- Volatility-matched base: s_t terciles fixed from pre-2016 sessions; the
  expected hit rate is the era's per-tercile base rate averaged over the signal
  sessions. Volatile periods have more drops and larger moves, so a plain rise
  could look predictive only because the market is busy.
- Lifts: hit rate / base and hit rate / volatility-matched base.
- Placement control: all circular shifts of the era's signal series over its
  evaluation sessions; share of shifts with a hit rate at least the signal's,
  and the 97.5th percentile. Signals cluster, so this is the honest comparison.
- Timing of each signal: hit (turn within k); early by k+1 to 10 sessions;
  late (stop signal inside a falling leg P+1..T, resume signal inside a rising
  leg T+1..next P); otherwise a false alarm.

## 4. Durations and "tiredness" (descriptive)

Per size and era: lengths of falling legs (P to T) and rising legs (T to next P)
in sessions, percentiles 10/25/50/75/90. Hindsight hazard: for sessions inside a
leg, by age since the leg began (1-2, 3-5, 6-10, 11-20, 21+), the share whose
turn comes within k = 2 sessions. A rising hazard means legs get "tired". Leg age
uses hindsight pivots, so it is descriptive, not a signal.

## 5. Decision, fixed in advance

A predictor passes if, on roll-adjusted closes at k = 2 and the 90th/10th
cutoff, in BOTH eras: at least 30 signal sessions, hit rate at least 1.25 x the
volatility-matched base AND at least 1.25 x the plain base, AND above the 97.5th
shift percentile. An RTL test of signal-based skipping is worth designing for a
drop size only if at least one stop predictor AND at least one resume predictor
pass for that size. Twelve predictors x three sizes are compared, so a single
pass is weak evidence; agreement across n, families or sizes counts for more.
Raw-close and sensitivity results are reported; a pass on one series only is
labelled fragile. Exploratory: all history has been used before.

## Verification and deliverables

Hash this protocol (CRLF-normalized) before calculating and check it after.
Independent verifier recomputes features, cutoffs, targets, rates, volatility
matching, every circular shift, timing classes, hazards and the decision with
separately written code. Tests: target window boundaries and end-of-data
exclusion, causality (future closes cannot change features or signals at t),
cutoffs from pre-2016 only, volatility-matched arithmetic, hazard ages.
Save RESULTS.md, a figure and tables; update plan/status/journal.
