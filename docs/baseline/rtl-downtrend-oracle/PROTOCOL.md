# RTL downtrend crystal ball: frozen protocol

2026-10-24. Written before any downtrend outcome was calculated. The user proposed
a perfect-foresight test: skip RTL while a hindsight downtrend runs, resume when
it ends, then make the same signals deliberately late. It sets a ceiling for
downtrend avoidance; it is not a tradable rule. Current uncapped RTL only.

## 1. Data

Trades: Reports/rtl_price_structure_20261024/trades.csv, primary rows only
(16,668: 6,167 in 2016-19, 10,501 in 2020-September 2026). One MNQ-valued contract,
$1.05 cost, planned initial risk as R. Hashes must match that study's provenance.
Each trade belongs to its submission `session` (research-session source date).

Daily bars: the verified D1 panel Reports/rtl_price_structure_20261024/
features_d1_20.csv (OHLC only), research-session closes (Chicago + 8h clock,
01:00 onward), from the first bar in 2010 through 2026-09-30. The incomplete
2026-10-01 session is excluded. Sessions are observed daily bars; no synthetic days.

Roll gaps: switch sessions come from the original rolls file (first date of each
new symbol). Primary series removes each roll gap by ratio back-adjustment: the
return from the previous session close to the switch session open is set to zero;
all other returns are unchanged. Raw unadjusted closes are a fixed sensitivity.
Reason: the next contract usually trades up to about 1% higher, comparable to the
smaller drop sizes.

## 2. Downtrends (zigzag on daily closes)

Sizes x = 2%, 3%, 5%, 10%, fixed. 20% is excluded as too rare (about four events
since 2016); below 2% a daily "downtrend" is often one or two sessions, close to
knowing each trade's direction in advance.

State machine over closes c, starting undecided at the first bar:
- Undecided: track the highest and lowest close so far. A close <= high*(1-x)
  confirms a decline from that high; a close >= low*(1+x) confirms a rise.
- Falling: a close <= the running low moves the low (ties move it later).
  A close >= low*(1+x) confirms the trough at the running low.
- Rising: a close >= the running high moves the high (ties move it later).
  A close <= high*(1-x) confirms the peak at the running high.
A downtrend runs from a peak session P to the following trough session T. If the
data ends while falling, T is the running low (tentative, flagged right-censored).

## 3. Rules compared

Crystal ball with delay d sessions, d = 0, 1, 2, 3, 5, 10, 20: skip trades
submitted in sessions P+1+d through T+d (positions in the observed session list).
d=0 stops right after the peak close and resumes right after the trough close.
Delay shifts stop and resume equally.

Live zigzag (causal counterpart, same x): skip from the session after a decline is
confirmed through the session in which the rise is confirmed; resume the next
session. This is the crystal ball with variable delay: the time to fall x and the
time to rebound x. Report its stop and resume lags (sessions after P and T).

## 4. Outcomes per size, series, rule and era

Trades and sessions skipped, share of era sessions skipped; retained and skipped
net dollars, mean net R; gain = retained minus baseline net dollars (also as % of
baseline); retained daily-close and closed-trade drawdown; losses avoided and
profits missed. Common era session calendar including zero-PnL sessions.
Ledger omission only, not an MT5 replay. Per year: downtrend count and share of
sessions inside downtrends at each size.

Controls, per era:
- Static: baseline scaled to the rule's retained holding-time fraction.
- Placement: ALL circular shifts of the rule's session skip mask over the era's
  session calendar (exhaustive, no random seed). Report the share of shifts whose
  retained net dollars are at least the rule's, the 2.5/50/97.5 percentiles, and
  drawdown shares. Shifts keep the same pattern of time off; they are dependent
  descriptive comparisons, not p-values.

## 5. Interpretation, fixed in advance

A. Ceiling: at d=0, does skipping raise net dollars and mean net R in both eras,
and beat the 97.5th percentile of shifts? Report the size of the gain.
B. Decay: per size and era, the break-even delay is the smallest tested d at which
retained net dollars <= baseline; the random-equivalent delay is the smallest d at
which retained net dollars are not above the 97.5th shift percentile.
C. Decision: further downtrend-filter research is worthwhile only if some size,
at d=3 or later, keeps retained net dollars above baseline AND above the 97.5th
shift percentile in BOTH eras, or if the live zigzag does so for some size.
Three sessions is about the fastest a daily-close detector can confirm a
multi-day move. Otherwise downtrend avoidance is not worth pursuing for RTL on NQ.
A drawdown claim also requires beating the static control.
Raw-close results are reported; a conclusion that holds only on one series is
labelled fragile. Scope: daily downtrend avoidance at 2-10%; this does not test
other filter families. All history has been used before; results are exploratory.

## Verification and deliverables

Hash this protocol before outcomes; verify unchanged at the end. Independent
verifier: second zigzag implementation and pivot property checks, roll
adjustment, skip masks, trade/dollar partitions reconcile to baseline, shift
controls recomputed directly. Tests: synthetic pivots, exact-threshold and tie
cases, tentative final leg, delay boundaries, live-rule causality (future closes
cannot change past decisions), roll adjustment preserves other returns.
Save RESULTS.md, a figure, tables and provenance; update plan/status/journal.
No strategy defaults or live settings change.
