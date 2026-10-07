# Q10: support-interaction RTL signals versus every other signal

**Amended during the study at the user's request: the active experiment uses
fixed -1R SL / +1R TP. The original-exit screen below is retained as an interim
diagnostic; its results do not answer the amended experiment. See the amendment
at the end of this document.**

Specified 2026-10-03 before computing Q10 subset/complement results. All history
and earlier subgroup results have already been examined; this remains exploratory.
User prioritizes the complete M30 strategy population, not matched breaches or
M1 speed. No new price-response threshold or entry/exit rule is introduced.

## Baseline and population accounting

- Keep all enabled entry windows, MaxRedRun=3, MinLocation=0, range filter off,
  one contract, buy stop at the red M30 high, original protective stop at its
  low, and existing pending-order replacement/cancellation rules.
- The profit exit is the original **bar-close-qualified market exit at >=1R**,
  with session/calendar flattening. It is not a fixed TP on first touch.
  Analyze actual logged trades, with $2/point and $1.05 round-trip commission.
- Retain the Q8 periods: 2016-01-01 to 2020-01-01 and 2020-01-02 to 2026-07-14,
  exclusive ends. Use all 35,632 baseline order attempts and 14,968 fills.
  Reconcile every fill with the full MT5 ledger and verify upstream hashes.
- Also enumerate **all potential red signals before position availability**
  from the saved M30 reference: last closed candle red, red run 1–3, positive
  range, next available bar in an enabled window and before that day's calendar
  flatten cutoff. The EA uses the preceding available candle, including after
  a closure/gap; do not silently require a same-session signal. Period selection
  uses that next decision bar. Report baseline-attempt and no-attempt counts.
  This census has no invented outcomes for candles skipped by the baseline.
- The attempt log is written before OrderSend: filled/attempts is an observed
  conversion rate, not a broker-accepted-order fill probability. A no-attempt
  potential signal is not an unfilled order. No change removes the red-run cap.

## Known support and fixed classifications

Current-session low is primary. Previous-session and previous-calendar-week
lows are separate secondary sources, using the unchanged Q6/Q8 map frozen
before the signal opens. Preserve contract-roll and missing-history exclusions.
Older confirmed swing levels remain a later study, not a data-selected map.

For valid level L and signal O/H/S/C, **fresh support interaction** is O > L and
S <= L. Keep the Q8 mutually exclusive groups:

1. No contact (S > L, O > L).
2. Touch only (S = L, O > L).
3. Breach and reclaim (S < L, O > L, C > L).
4. Breach and close below (S < L, O > L, C < L): the user's specific example.
5. Breach and exact close (S < L, O > L, C = L).
6. Opened at/below L: separate from a fresh downward interaction.
7. Unavailable level, retaining the reason.

The primary candidate combines groups 2–5. The primary complement is **every
other baseline signal**, including already-below and unavailable-level cases;
call it "every other signal", not "proven no interaction". Also show an
eligible-level-only complement and no-contact-only group to expose coverage
effects. No-contact-only is not substituted for the broad primary complement.

Compare each of the two motivated subtypes (reclaim and close below) with its
own full complement as secondary contrasts. Report touch and exact close
separately without selecting thresholds. A no-touch sensitivity (groups 3–5)
is descriptive. No geometric matching or M1 speed selection in this study.

## Outcomes and opportunity

For each source, period, calendar year and group report potential signals,
attempts, fills, no-attempt potentials, unfilled attempts, observed conversion,
trade and signal shares, net dollars/PF, average/median net R, net win rate,
R quantiles, net win/loss sums, and average signal range. Reconcile partitions
and net sums exactly. All-baseline results are identical across sources.

Attach ledger exit reason and target-qualified time: report SL, target-qualified
non-SL and other/session exits, and actual net-R bands. Do not turn all outcomes
into exactly -1R/+1R or call an unfilled attempt a stopped trade.

Report selected-trade closed-equity maximum drawdown only as historical
attribution. Report each group's additive signed net contribution during the
**full baseline's** largest closed-equity peak-to-trough interval. Neither is
the equity drawdown of a new filtered strategy. Removing trades changes future
position/order availability; potential signals skipped originally may become
tradable. A chronological full rerun is required for filtered PnL/drawdown.

Primary uncertainty: candidate minus full complement in average net R and net
PF, using 2,000 common calendar-month block resamples, seed 20261003, including
empty months. Confidence intervals are descriptive and unadjusted. Compare
with the all-baseline point estimates too; it overlaps the candidate.

## Follow-up rule

For each predeclared candidate (fresh interaction, reclaim, close below), a
current-session candidate merits a separate full MT5 filter experiment if:
candidate and complement each have >=200 fills in both periods; candidate PF
>1 and both PF and average net R exceed the complement in both periods; and
average-R superiority occurs in >=7 of the 11 yearly slices (requiring >=10
fills in each group for a year to count). Report intervals, retention and dollar
opportunity even if it qualifies; this screen alone never adopts a filter.

Report the same rule for the two secondary sources as exploratory comparisons;
do not silently replace the primary source with a sparse apparent winner. If
no candidate qualifies, conclude that this screen does not justify restricting
RTL to the tested support candles. A different level definition is a new test.

Save scripts, protocol, tables, event membership, ledger mappings and provenance.
Verify the geometry, whole-population partitions, census/attempt inclusion,
outcome reconciliation, drawdown attribution and uncertainty calculations.

## Amendment: fixed 1R stop and 1R profit, before fixed-TP outcomes

The user explicitly requested fixed -1R/+1R for this experiment. Run a separate
research EA on the rebuilt symbol with the original all-windows settings,
one-position/pending-order behavior and session safety. The only trading change
is attaching TP = signal high + (signal high - signal low), and disabling the
bar-close profit exit. SL stays at the signal low; buy stop at its high.
Use one-minute OHLC as previously authorized. Planned risk is the signal range;
report any entry gap/slippage rather than force every realized result to +/-1R.
Commission remains $1.05 and session exits remain possible.

The old saved fixed-TP study used another symbol and is not a valid substitute.
Generate new attempt and trade ledgers: fixed TP changes position availability,
so Q8's 35,632/14,968 counts are no longer the active outcome population.
The potential-signal census and all support definitions stay fixed. Preserve
the original-exit interim exports separately; no candidate is selected from
them. Reconcile the new run with tester report and stats, verify attached TP/SL,
and retain the same subset/complement metrics and follow-up gates above.

This is an all-signals fixed-TP reference run. A subsequent support-only strategy
would still require its own full run if a candidate qualifies. Do not mix the
original-exit baseline's results with the fixed-TP candidate's results.
