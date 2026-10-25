# RTL MA-agreement study

Completed 2026-10-25 under the [protocol frozen on October 24](PROTOCOL.md).
RTL only, M30. Independently verified; all 18 focused tests pass.

**No tested MA filter is adopted.** Mixed and downward agreement both contain
positive net dollars in both eras. Every one of the three omission policies
reduces profit in both eras across all five frozen definitions. Clear-up
agreement has better recent returns per trade, but that advantage does not repeat
in 2016-19. Waiting for up-consensus excludes trades whose profitable move is
already under way; the timing association does not establish a better entry rule.

## What was tested

The primary definition uses completed M30 closing-price SMAs at lengths
5,10,20,40,80,160,200, with equal votes. Up/down requires at least five of seven
slopes pointing that way. Everything else is mixed, including flat slopes.
These are M30 lengths, not daily MAs. Slopes are measured over one observation,
not by price being above/below the MA or by MA ordering.

Very small slopes count as flat. Each length's cutoff is the pre-2016 20th
percentile of its absolute slope divided by the arithmetic mean of the last
20 true ranges. Calibration uses 64,702 common-valid price observations and no
trade outcomes. The SMA identity is exact:

`SMA_L(t)-SMA_L(t-1) = (C[t]-C[t-L])/L`.

Thus these are correlated views of the same prices, not independent votes. Four
fixed sensitivities test four-of-seven, six-of-seven, no flat band, and a dense
5,10,...,200 grid requiring 29 of 40 votes. No winner was selected after seeing
outcomes. The dense grid gives 31 votes to lengths of at least 50.

Labels use only the latest completed observation at actual order submission.
The unchanged baseline is uncapped RTL M30/RR1, original stop, bar-close profit
exit, session flatten, one MNQ-valued contract ($2/point), $1.05 per-trade costs.
All 16,668 eligible trades remain: 6,167 in 2016-19 and 10,501 in January 2020
through September 2026. The incomplete October 1 tester trade stays excluded.

## 1. State outcomes

| Submission state | Trades, 2016-19 | Net $, 2016-19 | Mean net R | Trades, 2020-Sep 2026 | Net $, 2020-Sep 2026 | Mean net R |
|---|---:|---:|---:|---:|---:|---:|
| Up | 1,623 | -900.65 | -0.0577 | 2,600 | +13,051.00 | +0.0917 |
| Down | 1,395 | +2,743.75 | +0.0547 | 2,707 | +9,611.15 | +0.0349 |
| Mixed | 3,149 | +2,573.55 | -0.0225 | 5,194 | +15,737.80 | +0.0321 |
| All | 6,167 | +4,416.65 | -0.0143 | 10,501 | +38,399.95 | +0.0476 |

The direction of the averages is not the same as RTL's subsequent profitability.
In particular, downward agreement does not identify a losing long-trade group.
Mixed direction supplies 41.0% of recent net dollars; removing it removes a
substantial part of the existing ledger's profit.

Dollars and average R can disagree because trade size is fixed at one contract,
not at constant dollar risk. Mean initial risk for up/down/mixed is
$14.43/$33.89/$20.08 in 2016-19 and $55.53/$111.25/$73.84 recently. Down-state
trades have about twice the planned dollar risk of up-state trades. A filter's
risk effects therefore cannot be interpreted solely as directional prediction.

All primary state cells exceed the 200-trade/30-week coverage minimum. Their
active weeks are 195/184/209 early and 324/327/353 recent, respectively.

## 2. Omission costs and drawdown

Policies suppress new submissions only: skip mixed, skip down, or take only up.
Already accepted orders and open positions are left alone. These figures filter
the existing ledger; they do not replay orders freed by skipped positions or
enter at a later confirmation price.

| Policy | Net $, 2016-19 | Daily-close DD $, 2016-19 | Net $, 2020-Sep 2026 | Daily-close DD $, 2020-Sep 2026 |
|---|---:|---:|---:|---:|
| Baseline | 4,416.65 | 2,143.15 | 38,399.95 | 5,781.15 |
| Skip mixed | 1,843.10 | 2,037.70 | 22,662.15 | 5,541.25 |
| Skip down | 1,672.90 | 1,871.25 | 28,788.80 | 3,903.35 |
| Only up | -900.65 | 1,106.50 | 13,051.00 | 3,459.90 |

Skipping mixed sacrifices 41% of recent profit for only a 4% reduction in
daily-close drawdown. It retains 50.5% of holding exposure. The entire baseline
scaled to that exposure earns $19,380.92 with $2,917.82 drawdown: less profit
than the filter, but substantially less drawdown too. There is no simple
profit-and-risk improvement.

Skipping down has the most credible recent risk tradeoff of the three primary
policies: profit falls 25%, drawdown 32.5%. At the same 72.9% holding exposure,
the static comparator earns $27,985.30 with $4,213.21 drawdown, versus the filter's
$28,788.80/$3,903.35. That modest advantage does not repeat early: the filter
earns $1,672.90 with $1,871.25 drawdown, versus static $3,265.23/$1,584.43.
The recent filter retains only 63.7% of summed planned dollar risk despite
retaining 72.9% of holding time, so this comparator does not isolate directional
information from changes in dollar-risk exposure.

Only-up keeps 23.3% of recent holding exposure and 34.0% of profit. Its higher
recent mean R does not mean better risk control at equivalent exposure: the
static comparator has $8,966.27 profit and $1,349.88 drawdown, versus only-up's
$13,051.00/$3,459.90. Only-up loses money in the earlier era.

For recent only-up, skipped trades contain $377,157.40 of winning dollars and
$351,808.45 of losses. The gains missed exceed the losses avoided by $25,348.95.
These large opposing totals explain why an apparently sensible exclusion can
reduce net profit. Fractional sizing is a diagnostic comparator, not an
executable one-contract recommendation. It matches holding exposure, not all
features of dollar-risk or volatility exposure. Drawdowns here are realized
closed-trade/daily-close measures, not marked-to-market intratrade risk.

## 3. Where the missed profits occur relative to confirmation

For each primary non-up submission, a non-up spell continues through any
down/mixed switches and ends at the first up observation. Invalid observations
or the study endpoint censor a spell. These endpoints are retrospective. The
next table partitions the trades only-up would omit; outcomes are complete
baseline-trade outcomes, not PnL earned before or after confirmation separately.

| When up-consensus first returns | Trades, 2016-19 | Net $, 2016-19 | Trades, 2020-Sep 2026 | Net $, 2020-Sep 2026 |
|---|---:|---:|---:|---:|
| By the order's fill | 105 | +99.25 | 131 | +1,686.45 |
| While the trade is open | 1,102 | +18,998.90 | 1,759 | +104,058.55 |
| After the trade has exited | 3,337 | -13,780.85 | 6,010 | -80,301.00 |
| No observed return before censoring | 0 | 0.00 | 1 | -95.05 |
| All non-up submissions | 4,544 | +5,317.30 | 7,901 | +25,348.95 |

This shows why entry timing deserves attention: the profitable aggregate
contribution comes largely from trades already open when consensus becomes up.
In that recent group, confirmation occurs a median of two observed bars after
the completed submission observation; the median close-to-close advance is
1.34 times the mean true range known then. It does not tell us how much of the
$104,058.55 was earned before confirmation, or what a delayed-entry strategy
could earn.

The relationship is also endogenous: rising prices both improve a long trade
and help turn the MA slopes up. The split is not evidence that we can identify
successful transitions in advance. Trades that finish before consensus returns
still supply 60.4% of the omitted winning dollars, despite losing on net; those
open at confirmation supply 37.6%, and by-fill confirmation 2.0%. A profitable
trade does not require consensus to turn up during its lifetime.

Causal age after reentry supplies no stable shortcut. For up episodes beginning
after mixed, first-observation submissions net -$151.70 early versus +$1,513.75
recently (74/115 trades); ages 2-3 net -$400.80/+$3,180.55. Older ages also fail
to give a uniformly repeating pattern. Direct down-to-up reentry cells are tiny
(two early and eleven recent eligible trades); do not infer a rule from them.

## 4. Conflicting horizons, robustness and uncertainty

Short direction uses 5/10/20, long uses 80/160/200, each needing two agreeing
votes. The nine contexts are saved for every primary row, even if its overall
state is up or down. A short-down/long-up pullback can coexist with overall up.

| Context | Trades, early / recent | Net $, 2016-19 | Net $, 2020-Sep 2026 |
|---|---:|---:|---:|
| Short down / long up | 1,192 / 1,859 | -948.60 | +1,412.55 |
| Short up / long down | 393 / 786 | +43.85 | +4,934.70 |
| Both down | 1,114 / 2,212 | +2,683.80 | +6,364.40 |
| Both up | 1,296 / 1,985 | -180.30 | +13,076.75 |

Disagreement is not uniformly unfavorable. Every one of the nine contexts has
positive recent net dollars, while several early signs differ. These descriptive
subgroups do not justify selecting a new combination after the test.

All 30 variant/policy/era omission cells remove positive net dollars. The primary
up group's early dollar loss is not robust in sign: four-of-seven, six-of-seven
and zero-band versions are slightly profitable then, although their mean net R
is negative. Six-of-seven up is attractive recently ($11,249.25, +0.1366 mean R,
$1,070 drawdown) but earns only $114.95 with -0.0069 mean R early. It is a
sensitivity result, not a promoted setting. The dense grid does not repair the
cross-era inconsistency.

Removing all trades whose 201-observation feature window includes a contract
switch preserves the main primary signs. Roll-clean down nets +$3,053.25/
+$11,414.40; mixed +$2,458.75/+$16,255.45; up -$884.10/+$13,174.90, against
restricted-baseline +$4,627.90/+$40,844.75. This removes 425/716 trades; do not
compare a restricted state's dollars with the unrestricted baseline as a gate.

Annual results remain uneven. Up is negative in three of four early years and
in 2025; 2026 January-September supplies $5,365.15, or 41.1% of its recent net.
Down is profitable in all four early years but loses in 2021-23; 2024-25 supply
$7,851.55 of its $9,611.15 recent net. Mixed loses in 2016 and 2021, and gains in
the other nine annual/partial-year cells. The full annual table is retained.

Paired four-calendar-week bootstrap intervals do not establish that the recent
up group outperforms its complement. Its mean net R is +0.0917 with an adjusted
98.33% interval [+0.0241,+0.1635], but its difference versus the complement is
+0.0587 with interval [-0.0140,+0.1346]. Early down is the exception to a blanket
"all comparisons include zero" statement: its difference is +0.0892 with
adjusted interval [+0.0052,+0.1813], in the direction opposite to skipping down.
Neither mixed-state mean is established negative. Adjustment covers three
primary groups within an era, not every mean/contrast jointly or prior studies.

Circular-placement controls support only a recent risk hint for skip-down:
it beats 56.5% of same-holding shifts for dollars and 91.5% for drawdown, versus
5.4%/29.7% early. Only-up beats 79.7%/54.45% recently but 2.2%/34.8% early.
These are descriptive ranks, not a joint significance test. Shifts preserve
circular trade-order run lengths, not calendar duration or volatility regimes.

## Decision, verification and artifacts

None of the three primary policies passes the frozen follow-up screen. Their
skipped sets are profitable in dollars in both eras, so no full gated-strategy
replay is triggered. The study supports neither a blanket mixed/down exclusion
nor a stable only-up rule. It leaves a recent skip-down risk tradeoff, with
contrary earlier evidence. No EA defaults, orders or live accounts were changed.

This is one fixed family of M30 SMA slope rules, not proof that all trend features
are useless. It does not test daily MA agreement, EMA variants, a hedge, or
execution realism. Repeatedly inspected history and modelled fills limit
confidence. Future-up timing remains attribution only.

Independent verification passed for:

- 191,781 M30 rows, 40 slope series/cutoffs, and all five state variants. Literal
  rolling SMA differences match the identity to at most 3.7e-12 in price units.
- All 83,340 labelled rows (five copies of 16,668 eligible trades), 136,410
  state episodes and 9,019 primary non-up spells, including 5,149 zero-trade spells.
- 159 summaries, 220 annual rows, 40 roll rows, 90 policy rows and 124,920 daily
  curve rows; all submission/fill/exit joins and future-timing partitions.
- All 60,000 saved bootstrap group draws and 12,000 placement draws, plus hashes.
  Eighteen focused boundary, causality and policy tests pass.

There are 191,575 common-valid feature rows: the first 200 warmup rows and six
zero-mean-true-range observations on March 16, 2020 are invalid. Invalid rows
break/censor episodes; no eligible submission is lost. No future state is
carried backward through these gaps.

- [Complete calculated tables](../../../Reports/rtl_ma_agreement_20261024/report_tables.md)
- [Comparison chart](../../../Reports/rtl_ma_agreement_20261024/ma_agreement.png)
- [Independent verification](../../../Reports/rtl_ma_agreement_20261024/independent_verification.json)
- [Economics provenance](../../../Reports/rtl_ma_agreement_20261024/provenance.json) and [feature provenance](../../../Reports/rtl_ma_agreement_20261024/feature_provenance.json)
- [Feature implementation](../../../python/analyze_rtl_ma_features.py), [economics](../../../python/analyze_rtl_ma_agreement.py), [independent verifier](../../../python/verify_rtl_ma_agreement.py), [tests](../../../python/test_rtl_ma_agreement.py), [report generator](../../../python/report_rtl_ma_agreement.py)

Background for the SMA definition and lag:
[StockCharts ChartSchool](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential).
