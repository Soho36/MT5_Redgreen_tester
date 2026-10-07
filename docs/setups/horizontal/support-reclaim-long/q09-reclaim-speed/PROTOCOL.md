# Q9: recovery speed and the two-sided explanation

Frozen 2026-10-03 before calculating speed-conditioned outcomes. User requested
fast/slow recovery comparisons at similar depth and volatility, and asked whether
the Q8 +0.5R excess is mostly two-sided. This is a Python price-path diagnostic;
there is no new EA, execution rule, or simulated trade PnL.

## Population, data and timing

- Reuse Q8's 35,632 logged baseline order attempts and 14,968 fills, with its
  original periods, signal definitions, full-session maps and roll exclusions.
  Current-session low is primary; previous-session/week are secondary, not
  replacement winners. Older swing levels remain a separate future extension.
- Q8 classifications and outcomes remain frozen. Verify all unique signal OHLC
  and available Q8 forward endpoints/excursions against the minute source.
  Verify upstream input/code/protocol hashes before reusing artifacts.
- Time zero remains the **M30 signal close**. Speed is a property of the already
  completed signal, not permission to enter earlier using its eventual shape.
  Returns are measured at 30/90/180 minutes after time zero; 90 minutes is primary.
- Use raw continuous minute OHLC and the existing contract ledger. Require every
  minute of the signal for speed, and every expected future minute for ordered
  barrier outcomes. Preserve missing-data and session-end exclusions explicitly.
  Existing Q8 endpoint outcomes remain usable when their M30 window is valid,
  even if a missing minute makes first-touch ordering unavailable.

## Speed and volatility definitions

For fresh breaches (signal opens above L and its low is below L):

- First breach minute = first minute with low < L. First recovery minute = first
  minute at/after that breach with close > L.
- **Recovery-delay proxy** = elapsed minutes from breach-minute open to the
  recovery-minute close. Same-minute recovery is recorded as 1 minute, not zero
  seconds. It is an upper bound at one-minute resolution, not exact tick latency.
- Primary speed comparison is among Q8 **final-close reclaimed** signals:
  **fast <=2 minutes**, **middle 3-5**, **slow >=6**. Middle is reported separately.
  Sensitivities: fast <=1 or <=3 versus the same slow >=6; no searched cutoff.
- Also export breach minute within the M30 bar, count of below-level minute
  closes after breach, fraction of those closes below, number of subsequent
  above-to-below close crossings, depth, reclaim strength and a five-minute
  pre-breach downward approach velocity. Missing approach history stays missing.
  An early transient recovery that finishes below is not a Q8 final reclaim.
- Lagged volatility A = simple mean of the preceding 14 M30 true ranges, excluding
  the signal. True range uses previous close from the same contract; the first
  contract bar uses high-low. Require 14 prior bars from that contract, so roll
  gaps do not become volatility. This is a defined scale, not MQL's ATR smoothing.
- Save depth/A, depth/tick, signal range/A, and reclaim strength/A. Future response
  is reported both in original signal R and in lagged A.

## Two-sided response

For the Q8 reclaim versus unrecovered comparison, and fast versus slow reclaims:

- Endpoint probabilities at >=+0.5R and <=-0.5R; directional balance is their
  difference, and total tail probability is their sum. Also report mean return,
  mean absolute return and positive-return frequency.
- Repeat endpoint quantities at +/-0.5A to check signal-range normalization.
- Within each complete minute path, report upward hit, downward hit, both-hit,
  upward-only, downward-only and neither probabilities at symmetric +/-0.5R.
  Repeat the path labels in A. These are touches from signal close, not fills.
- Classify first hit as up, down, neither or ambiguous. If both thresholds first
  occur in the same minute, the minute open can establish the first side only
  when it is already at/beyond a threshold; otherwise retain ambiguity. Never
  infer favorable ordering from that minute's close or an assumed OHLC path.
- A larger up-tail probability accompanied by a comparable/larger down-tail
  increase and no stable improvement in balance/mean supports a two-sided
  interpretation. Report the actual differences and uncertainty rather than
  impose a post-hoc numerical definition of 'mostly'. No causal claim.

## Similar-depth/volatility comparisons

Show raw and matched results. Matching uses only information known at M30 close,
within each source, period and calendar year. Compare (a) fast versus slow final
reclaims, primary; (b) final reclaim versus unrecovered fresh breaches, secondary.

Deterministic one-to-one matching without replacement: eligible pairs differ
by at most a factor of 2 in each of depth/A, A, and signal range/A; by at most
5 minutes in breach-minute position; and by at most 2 hours in session clock
time. Rank pairs by sum of squared differences divided by those calipers, then
greedily take the smallest, breaking ties by original event order. Retain pair
IDs, counts, unmatched losses and covariate balance. No relaxing calipers after
outcomes are seen. Conditioning on signal-range geometry is possible here
because the entire M30 signal is already known at the study's decision time.

The primary matched sample has valid 90-minute endpoints and complete signal
minute paths, with nonmissing lagged A. Other horizons retain only pairs for
which both endpoints are available. Show raw response counts/exclusions too.
Sparse = fewer than 100 matched pairs per period. All returned estimates remain
exploratory; matching does not remove unobserved differences.

## Reporting and decision

Export all groups, yearly summaries, source-specific and common-source raw
comparisons, pair lists and balance, speed sensitivities, and explicit data
coverage. For primary contrasts report differences in upper/lower probability,
directional balance, mean signed/absolute return, and both-hit probability.
Use 2,000 common calendar-month block resamples (seed 20261003) for differences,
with matching held fixed and months with no group observations retained.
Intervals are descriptive, unadjusted for multiple comparisons or selection.

Speed is a candidate for a separate causal minute-entry experiment only if:
matched fast versus slow has >=100 pairs in each period; both the mean A return
and A endpoint directional balance differences have 95% intervals above zero
in both periods at 90 minutes; their signs persist at 30/180 minutes and at the
two predefined fast cutoffs with >=100 pairs per period. If this fails, retain
any frequency/volatility pattern without labeling it a robust directional edge.

An MT5 EA would be a subsequent implementation test of explicit causal entry,
stop, exit, cancellation and position rules. Python can also simulate those if
execution is modeled, but raw event probabilities do not establish trade PnL.
An EA on the same minute OHLC cannot recover unknown intraminute ordering or
prove actual fills. No additional generated-tick runs are part of this study.
