# RTL session VWAP and price action

Frozen 2026-10-25 before viewing conditional outcomes. User authorized investigation
after committing the drawdown synthesis. Exploratory RTL-only attribution on
repeatedly inspected history, not fresh validation. No strategy/default changes.

## Source and availability

Use original Databento NQ continuous minutes, M30 reference and verified regime
trade ledger; check hashes against price-structure provenance. <VOL> is actual
NQ contract volume, copied into <TICKVOL>, not MNQ-specific volume. Validate
positive matching volumes, unique ordered timestamps, valid OHLC and exact M30
OHLC reconciliation. Minute timestamps are starts; information arrives one minute
later. Preserve all 16,668 eligible trades (6,167/10,501 in 2016-19/2020-Sep2026),
net $4,416.65/$38,399.95. Uncapped RTL M30 RR1 bar-close exit, original stop and
session handling, one MNQ-valued contract ($2/point), $1.05 cost. Exclude Oct1.

VWAP=sum(p*volume)/sum(volume), accumulated from session start. Primary minute
p=(H+L+C)/3. This is an OHLCV approximation, not transaction VWAP. Aggregate
minute price-volume products BEFORE M30 resampling. Reset by source date:
America/Chicago+8h, normal session01:00-23:59. At bar_time+30min include only
minutes strictly earlier than that time. Join latest available_at<=submitted,
exact matches allowed; a feature from another session is invalid.

Three fixed variants: full_hlc3 (primary), full_close (minute close price),
cash_hlc3 (reset16:30 source clock=08:30 Chicago, undefined before reset,
continue until session end). No optimized anchor or threshold calibration.

## Four questions

1. Location: sign of completed M30 close minus VWAP; above/below/at/unknown.
2. Extension: z=(close-VWAP)/A20; A20=arithmetic mean of20 observed true ranges,
   TR=max(H-L,abs(H-Cprev),abs(L-Cprev)), first invalid. A20<=0 is unknown.
   Bins: z<-1 far_below; -1<=z<0 below; z=0 at; 0<z<=1 above; z>1 far_above.
3. Reclaim: previous close<=previous VWAP and current close>current VWAP;
   loss: previous close>=previous VWAP and current close<current VWAP;
   otherwise same_side. Require consecutive observed same-anchor endpoints;
   first anchor bar unknown. These are moving-reference endpoint crossings,
   not verified intrabar touches or executable VWAP entries.
4. Repeated crossings: latest7 same-anchor endpoints (6 transitions), count
   strict opposite signs (product<0; zeros not crossings). Churn if>=3, otherwise
   orderly; insufficient history unknown. One sensitivity:5 endpoints/4transitions,
   churn>=2. No other windows or threshold search.

Save VWAP, cumulative volume, anchor age, A20, z, side/event/cross counts and
availability. No slope-agreement claim: VWAP direction and price location are
mechanically related. A20 roll-clean excludes21 consumed bars containing any
switch_bar. VWAP never spans a roll. No synthetic bars through missing periods.

## Outcomes and controls

Each variant/era: all and every category of the four partitions, annual and
roll-clean versions; unknown remains explicit. Report counts, active sessions/
weeks, gross/net R/dollars, PF, planned risk, holding, +$1/+$2 costs, closed-trade
and daily-close DD/duration. Partitions reconcile to baseline. Full observed
session calendars include flat days. Compare full_hlc3/cash_hlc3 additionally
on the common VWAP-available trade subset, disclosing availability.

Four fixed submission-only omission policies: skip_below, skip_far_above,
skip_far_below, skip_churn. Unknown retained. Additional sensitivity skip_churn4.
No accepted-order cancellation, early closure or delayed entry. Ledger omission
cannot create orders freed by skipped trades and is not a full replay.
Report losses avoided, winning dollars missed, retained trade/holding/planned-risk
fractions. Compare with baseline uniformly scaled to same holding (costs too);
fractional contracts are a diagnostic only, not executable one-MNQ sizing.

For four PRIMARY skipped subsets, paired circular4-calendar-week bootstrap,
5,000draws seed20261025; include empty weeks, ceil(nweeks/4) starts, trim to
nweeks. Save subset/complement sums/counts, subset mean-R and contrast intervals:
95% and98.75% (4-comparison adjustment, not prior research/all descriptions).

Time/risk confounds: submission blocks01:00-08:59,09:00-16:29,16:30-19:59,20:00+;
planned-dollar-risk tertiles within each era from all baseline trades (descriptive
only, not trading thresholds). Report subset/complement R/counts within time x
risk strata and subset-count-weighted differences over common-support strata;
report supported share. These are associations, not causal effects.

Placement:1,000 shared circular shifts of chronological trade-order skip masks
per era, seed20261026. Preserve skip count/circular trade runs, not calendar
duration/time-of-day/volatility. Save retained dollars/daily-close DD/holding and
baseline scaled to each holding. Rank actual minus same-holding advantages for
profit and DD separately. Apply to four primary policies only.

## Decision, artifacts and verification

Adequate subset:>=200trades/30active weeks in each era. Negative-edge candidate
requires skipped dollars AND mean net R negative in both eras, lower retained
daily DD in both, compatible sensitivity/confound evidence. Risk-only leads may
omit profitable trades: retain their profit/DD tradeoff and compare with static
exposure/placement, never reject only because profit falls. No adoption from this
screen. A survivor warrants a concrete full-replay proposal, not a validation claim.

Save feature/trade panels, partition/year/roll/common-anchor summaries, policies,
daily curves, uncertainty draws, confound/placement tables, hashes and audit.
Independently reconstruct sampled raw-minute VWAP, all feature math/asof joins,
economics/aggregations and policy arithmetic. Test resets, invalid volume,
boundaries, history/gaps and no-lookahead. Render/inspect compact chart. Update
plan/status/journal. No live deployment or new hedge.

Definitions:
- https://databento.com/docs/examples/basics-historical/technical-indicators?lang=python
- https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.timeAndSales.html
