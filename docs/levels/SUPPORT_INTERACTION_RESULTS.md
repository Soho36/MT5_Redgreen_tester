# Q10: do support-interaction red candles make better RTL trades?

**Historical definition:** these completed tables require the candle to open
above the level. The user's subsequent clarification is broader: any qualifying
red candle whose range touches/crosses support, regardless of open or close
position. That broader comparison is pending. Subtypes below are descriptive,
not requirements for the active rule. [Current direction](README.md).

2026-10-03 · [Protocol and fixed-1R amendment](../SUPPORT_INTERACTION_PROTOCOL.md) ·
[Full tables](../../Reports/levels/support_interaction_fixed1r_20261003/report.md) ·
[Analysis](../../python/analyze_support_fixed1r.py).

## Answer

**With the user's fixed -1R stop / +1R take-profit experiment, current-session
support interaction concentrated the edge in 2016–2019, but did not clearly
distinguish better trades in 2020–2026.** The specific breach-and-close-below
setup was strong earlier and lost money recently. Reclaims show the reverse
pattern in dollar PF. No tested candidate meets the predefined follow-up rule.

Previous-week interactions have better point estimates in both periods, but
only 79/146 trades. Keep that as a sparse, exploratory observation, not an
established filter. Previous-session interactions do not replicate across periods.

## This is the requested strategy comparison

All qualifying red M30 signals across all enabled windows form the reference.
MaxRedRun=3 and the existing session safety remain. Buy stop = signal high,
SL = signal low, TP = signal high + full signal range. The profit exit is now
a fixed TP on touch for this separate experiment. No M1 speed or 90-minute
price-response outcome enters classification or selection.

The user changed the exit while an original-exit attribution screen was being
prepared. Those interim outputs remain in `Reports/levels/support_interaction_20261003/`;
they are **not** the results in this document. The new run uses rebuilt symbol
**`MNQcontDTBNT20102026_2`**, one-minute OHLC, one
contract, $2/point and $1.05 round-trip cost. There were no entry-price gaps or
SL overshoots in the recorded run. TP/SL exits are exactly +/-1 signal R gross;
costs and session exits make net outcomes different from exactly +/-1R.

Fresh support interaction means the candle **opens above a level already known
before it opened, then touches or breaches it**. It includes touch, reclaim,
close-below and exact-level-close cases. Every other signal is the complement,
including already-below and unavailable-level cases, which are shown separately.
The primary comparison is not restricted to similar breaches or no-contact
candles. Levels use the unchanged session/week maps and contract-roll exclusions.

## Whole population and opportunity

| Fixed-TP reference | 2016–19 | 2020–26 |
|---|---:|---:|
| Potential red signals before position availability | 19,624 | 32,446 |
| Actual order attempts | 14,645 | 24,208 |
| Potential signals with no attempt | 4,979 | 8,238 |
| Filled trades | 6,261 | 10,134 |
| Attempts without a fill | 8,384 | 14,074 |
| Observed attempt-to-fill conversion | 42.8% | 41.9% |

An existing position prevents a new order; a new red candle can replace a pending
one. Consequently the potential-signal census is larger than the attempt log.
The log precedes OrderSend, so its conversion is not a broker-accepted-order
fill probability. No trade return is invented for an unsubmitted/unfilled signal.

Fixed TP changes availability: this reference has **16,395 trades**, versus
14,968 in the original-exit research baseline. Reusing the old trades with
different labels would have missed that change.

## Current-session interaction versus every other red signal

| Period | Group | Trades | Net $ | Net PF | Avg net R | Net win rate |
|---|---|---:|---:|---:|---:|---:|
| 2016–19 | All reference trades | 6,261 | +3,140 | 1.055 | -0.036 | 53.3% |
| 2016–19 | Support interaction | 1,216 | +3,127 | **1.226** | **+0.055** | **56.8%** |
| 2016–19 | Every other signal | 5,045 | +14 | **1.000** | **-0.058** | **52.4%** |
| 2020–26 | All reference trades | 10,134 | +26,908 | 1.082 | +0.030 | 52.8% |
| 2020–26 | Support interaction | 2,013 | +6,604 | **1.079** | **+0.035** | **52.8%** |
| 2020–26 | Every other signal | 8,121 | +20,304 | **1.084** | **+0.029** | **52.8%** |

Earlier, about 19.4% of trades account for 99.6% of net dollars. Recently,
19.9% account for 24.5%, with nearly identical win rates and PFs. These are
attributions within the reference run, not a simulated support-only strategy.
Dollar PF weights the different signal risks; average R weights trades equally.
They need not agree, even with fixed gross 1:1 exits and one-contract sizing.

Interaction minus every other signal, 95% descriptive month-block intervals:

| Difference | 2016–19 | 2020–26 |
|---|---:|---:|
| Net PF | +0.226 [+0.010, +0.471] | -0.005 [-0.156, +0.141] |
| Average net R | +0.112 [+0.055, +0.173] | +0.005 [-0.042, +0.051] |

Average-R superiority occurs in 7/11 yearly slices, but the pooled recent
comparison does not establish an advantage. The candidate fails the rule
requiring both PF and average R superiority in both periods.

Interaction attempts convert to fills less often: **37.1% versus 44.4%** earlier,
**35.1% versus 44.0%** recently. A qualifying candle does not guarantee a trade.

## Which interaction?

Each subtype is compared with its **own full complement**, not just the other
breach subtype. The table shows candidate PF / complement PF.

| Current-session subtype | Earlier trades | Earlier PF comparison | Recent trades | Recent PF comparison |
|---|---:|---:|---:|---:|
| Breach and close below | 604 | **1.356 / 1.012** | 1,020 | **0.958 / 1.105** |
| Breach and reclaim above | 508 | **1.020 / 1.060** | 931 | **1.266 / 1.062** |

The user's close-below example earns +$2,558 earlier but loses $2,082 recently.
Only 30.0%/28.9% of these attempts fill: entry occurs after price recovers to
the candle high. That confirmation is part of the tested strategy, but it
does not yield consistent superiority for this candle category.

Reclaim PF improves recently but not earlier. Its mean-R differences versus
the full complement are +0.029 [-0.072, +0.127] and +0.034 [-0.023, +0.088].
Positive point estimates are not a reliable cross-period profitability result.

Touch-only samples are 59/31 trades (PF 2.328/0.680), exact-close 45/31
(2.380/1.306). They are sparse and not adopted separately. Excluding touches
from the aggregate gives PF 1.212/1.082, preserving the period-dependent result.

Restricting the control to known levels does not rescue the conclusion:
eligible-level complements have PF 0.988/1.094. No-contact-only PF is 0.990/1.098.
The primary all-other complement is retained; coverage cases are never hidden.

## Other support definitions

| Source | Earlier interaction / other PF | Earlier interaction trades | Recent interaction / other PF | Recent interaction trades |
|---|---:|---:|---:|---:|
| Previous session | 1.327 / 1.037 | 257 | 0.962 / 1.093 | 448 |
| Previous calendar week | **1.444 / 1.049** | **79** | **1.255 / 1.078** | **146** |

Weekly interaction mean net R is +0.199/+0.106 versus -0.039/+0.029 in the
complement, with superiority in 8/11 yearly slices meeting the minimum annual
counts. The PF-difference intervals include zero in both periods; the recent
mean-R difference is +0.076R [-0.086, +0.258]. Only 1.3%/1.4% of trades belong
to this weekly subset. It fails the predefined 200-per-period sample threshold.
This observation merits retention, without presenting a sparse secondary source
as a confirmed replacement for the primary result. Older swing levels are untested.

## Drawdown attribution and exit accounting

Current-session group exits:

| Period | Group | TP | SL | Session/other |
|---|---|---:|---:|---:|
| 2016–19 | Interaction | 619 | 477 | 120 |
| 2016–19 | Every other | 2,481 | 2,271 | 293 |
| 2020–26 | Interaction | 974 | 878 | 161 |
| 2020–26 | Every other | 4,057 | 3,614 | 450 |

All-reference closed-equity net drawdown is $1,571/$4,656. Within each period's
baseline peak-to-trough interval, interaction trades contribute -$92/-$1,100
and the complement -$1,479/-$3,556. These signed contributions add to the
reference drawdown. Separate selected-trade closed-equity drawdowns are
$781/$3,812 for interaction and $1,801/$6,470 for the complement; their peaks
and troughs differ, so those maxima do not add.

None of those subset drawdowns is a support-only strategy backtest. Skipping
other trades changes availability, replacements and subsequent entries. No
candidate qualifies for the separately specified support-only rerun, and no
production strategy change is adopted. The fixed-TP reference itself was fully
rerun in MT5; only its subgroup comparisons are attribution.

## Verification and artifacts

- Separate EA compiled with **0 errors, 0 warnings**; full-history tester run
  completed in 52.8 seconds. Production EA and defaults are unchanged.
- Full-history audit: **25,552 trades**, **51,104 report deals**, and **58,965
  accepted buy-stop orders**. Every reported buy stop has equal planned SL/TP
  distances. Ledger, report, profit, volume and timestamps reconcile.
- No bar-close profit checks occurred, no entry gaps or SL overshoots were
  observed, and trade/export/cancellation error counters are zero. Session
  flattening still applies; none of the recorded trades crosses a trading date.
- The two study periods contain **52,070 potential signals**, **38,853 attempts**
  and **16,395 fills**. All attempt OHLC/red-run values match the census/reference.
- Independent verification checks **321,954** geometry rows, **117** whole-
  population table checks, **18** contrasts, all order brackets and **19** hashes.
  Three focused tests cover geometry/complements, initial-zero drawdown and
  next-available-bar/calendar census rules.
- Full membership, yearly groups, R quantiles/bands, TP/SL/session counts,
  conversion and coverage are saved beside the report, including
  `verification.json`, `run_audit.json`, and `provenance.json`.

All results are exploratory on already inspected history. Bootstrap intervals
use 2,000 common calendar-month resamples and no multiple-comparison adjustment.
One-minute OHLC is the accepted screening model, not historical tick execution.

Reproduce analysis and checks with the project venv:

```powershell
.\venv\Scripts\python.exe python\analyze_support_fixed1r.py
.\venv\Scripts\python.exe python\verify_support_fixed1r.py
.\venv\Scripts\python.exe -m unittest discover -s python -p test_support_interaction.py -v
```

The isolated EA/config generator is `python/prepare_support_fixed1r.py`; it
refuses to overwrite a completed run. The source, binary, compile log, inputs,
MT5 reports and logs are in `Reports/levels/support_fixed1r_20261003/`.
