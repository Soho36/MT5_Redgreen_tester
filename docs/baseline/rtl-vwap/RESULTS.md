# RTL session VWAP and price action

Completed 2026-10-26; [protocol](PROTOCOL.md) frozen 2026-10-25 before outcomes.
RTL only. **One worthwhile risk-management lead: avoid new signals far below
the full-session VWAP. No filter adopted; full replay is still required.**

This is more encouraging than a blanket above/below rule. Moderate dips below
VWAP contain substantial profits, and repeated crossings are not a losing subset.
Distance below VWAP distinguishes weaker trades, but the evidence does not establish
a reliably negative dollar expectancy in both eras or guarantee future improvement.

## Definition and data

Same uncapped M30 RTL/RR1 baseline: red candle, buy stop, original stop, first
qualifying bar-close exit/session flatten, $2/point and $1.05 round-trip cost.
16,668 eligible trades: 6,167 in 2016-19 and 10,501 in 2020-September 2026.
The incomplete October 1 tester endpoint is excluded.

Primary VWAP is cumulative minute HLC3 times traded volume divided by cumulative
volume, reset each full futures session. This uses actual **NQ** volume and prices
with MNQ dollar valuation; it is not a study of MNQ-specific volume. OHLCV VWAP is
an approximation to transaction VWAP. The source clock is Chicago+8h: normal
session 01:00-23:59, including overnight trading. The alternative cash anchor
starts at 16:30 (08:30 Chicago) and continues to session end.

All labels use completed information at order submission. Define
`z = (completed M30 close - VWAP) / A20`, where A20 is the arithmetic mean of
20 completed M30 true ranges, not Wilder smoothing. **Far below means z < -1**;
moderately below means -1 <= z < 0. This threshold was fixed before outcomes.
For example, VWAP 20,000 and A20 40 makes closes below 19,960 far below.

VWAP is unavailable for 553 orders at the session open (173 early/380 recent).
These remain unknown and are retained by every policy. Reclaim/loss requires
consecutive same-session endpoint comparisons; repeated crossings means at least
three strict side changes in six transitions (seven endpoints). Insufficient
history is unknown, never silently classified as orderly.

## Four questions answered

Primary full-session HLC3 VWAP, net after $1.05 cost. R is net PnL divided by the
trade's initial planned dollar risk; dollar totals and mean R need not share signs.

| Submission condition | Early trades | Early net $ | Early mean R | Recent trades | Recent net $ | Recent mean R |
|---|---:|---:|---:|---:|---:|---:|
| All RTL | 6,167 | 4,416.65 | -0.0143 | 10,501 | 38,399.95 | +0.0476 |
| Above VWAP, any distance | 2,257 | 1,830.65 | -0.0172 | 3,686 | 18,916.70 | +0.0672 |
| Below VWAP, any distance | 3,737 | 2,413.15 | -0.0130 | 6,435 | 17,500.25 | +0.0377 |
| Far below (z < -1) | 1,620 | 478.00 | -0.0342 | 2,886 | -5,035.30 | -0.0165 |
| Moderately below (-1 <= z < 0) | 2,117 | 1,935.15 | +0.0033 | 3,549 | 22,535.55 | +0.0818 |
| Moderately above (0 < z <= 1) | 1,388 | 237.10 | -0.0562 | 2,128 | 12,974.10 | +0.0706 |
| Far above (z > 1) | 869 | 1,593.55 | +0.0449 | 1,558 | 5,942.60 | +0.0626 |
| Reclaim VWAP | 5 | 12.75 | +0.2570 | 11 | -199.05 | -0.2124 |
| Lose VWAP | 782 | -107.60 | -0.0077 | 1,269 | 4,819.05 | +0.0658 |
| Repeated crossings | 444 | 1,403.30 | +0.0960 | 723 | 3,195.35 | +0.0772 |

Rows describe overlapping questions, not one additive partition; complete disjoint
partitions and unknowns are saved in the tables. Findings:

1. **Above/below alone:** neither side is consistently unprofitable. Skipping all
   below-VWAP trades sacrifices substantial useful exposure.
2. **Extension:** far below is weaker in mean R in both eras. Far above remains
   profitable; the mirror exhaustion rule is unsupported. Moderate dips below
   have positive mean R and dollars in both eras.
3. **Reclaim/loss:** only 5/11 reclaims at RTL submission, insufficient evidence.
   These are endpoint crossings of a moving reference, not a general test of
   intrabar VWAP bounce/reclaim entries. Losing VWAP is profitable recently.
4. **Repeated crossings:** profitable in both eras, with higher mean R than
   orderly trades. Skipping them cuts profit and fails to improve drawdown versus
   equally reduced exposure. The four-transition sensitivity does not establish
   a reliable chop filter either.

## The risk-management lead

Skip only new submissions with z < -1; leave unknowns and existing orders/positions
to the original strategy. This table omits existing ledger trades; it cannot model
additional trades freed by a skipped position.

| Era | Measure | Baseline | Skip far below | Same-holding static baseline |
|---|---|---:|---:|---:|
| 2016-19 | Net profit | $4,416.65 | $3,938.65 | $3,189.77 |
| 2016-19 | Daily-close max DD | $2,143.15 | $931.95 | $1,547.82 |
| 2016-19 | Longest daily DD, calendar days | 906 | 641 | 906 |
| 2020-Sep2026 | Net profit | $38,399.95 | $43,435.25 | $27,719.54 |
| 2020-Sep2026 | Daily-close max DD | $5,781.15 | $3,084.05 | $4,173.20 |
| 2020-Sep2026 | Longest daily DD, calendar days | 283 | 392 | 283 |

Early: 10.8% less profit, 56.5% less DD. Recent: 13.1% more profit, 46.7% less DD.
Depth improves in both eras but **recent duration increases by 109 days**.
The maximum depth and maximum duration need not belong to the same episode;
duration includes an unfinished underwater stretch up to the sample end.

The policy retains approximately 72.2% of holding time but only 61.1% of planned
dollar risk in both eras. The omitted trades are larger-risk trades; the recent
far-below mean risk is $111.59 against $78.95 overall. Same-holding scaling does
not equalize dollar risk. It is a fractional-size diagnostic, not executable
sizing for one MNQ contract.

Early losses avoided $25,053.40 versus winning dollars missed $25,531.40; recent
$164,254.85 versus $159,219.55. This is a small net difference between large
gross streams; many profitable trades are also omitted.

## Robustness and qualifications

- **Minute close VWAP:** very similar. Retained net/DD $3,894/$921 early and
  $43,084/$3,084 recent. Roll-clean samples preserve the primary tradeoff.
- **Cash-open VWAP:** substantially weaker: retained net/DD $3,695/$1,746 early
  and $40,784/$5,279 recent. Recent cash DD slightly exceeds its same-holding
  comparator ($5,236). Only 24-25% of baseline trades have cash VWAP available.
  Even on common-available trades, the anchors select different conditions:
  full-session far-below earns -$929/-$5,452 early/recent; cash far-below
  +$721/-$2,384. This limits any claim that the result applies to arbitrary VWAPs.
- **Time and risk:** within fixed time blocks and risk tertiles, far-below minus
  complement mean R remains negative: -0.050 early and -0.083 recent, with full
  stratum support. This is descriptive adjustment, not proof of causation.
- **Uncertainty:** adjusted 98.75% block-bootstrap intervals for the far-below
  mean R include zero in both eras: [-0.109,+0.042] and [-0.071,+0.041]. Its
  contrast with other trades includes zero early [-0.110,+0.057], but is below
  zero recently [-0.161,-0.018]. We have stronger evidence of recent relative
  weakness than of an absolutely negative expected return.
- **Placement controls:** actual profit/DD advantages over same-holding scaling
  beat 73.9%/99.8% of shifted masks early and 99.4%/99.5% recently. The early profit
  result is ordinary. These are descriptive ranks over 1,000 circular trade-order
  shifts, not a global significance test or time/volatility-matched control.
- **Annual stability:** far-below net dollars are negative in 8/11 years (2026
  partial) but positive in 2017, 2019 and 2024. Skipping sacrifices $4,649.55 in 2024.
- **Costs:** extra $1/trade makes retained early net -$608.35 (baseline -$1,750.35).
  Retained recent net stays $35,820.25. The early edge remains cost-fragile.
- **Data and scope:** all history has been examined repeatedly. Actual slippage,
  intraday open-equity extremes and freed-order effects are not modeled here.
  Uniform session-wide volume rescaling cancels in VWAP; nonuniform source-volume
  differences would not. No independent instrument or fresh forward test is claimed.

The strict negative-edge screen **does not pass**: omitted early dollars are
positive. The risk-only clause in the frozen protocol supports a separate full
replay proposal because both eras improve relative to same-holding scaling on
profit and drawdown depth. This is not a changed threshold or a claim that the
original negative-edge test passed. See [replay proposal](REPLAY_PROPOSAL.md).

## Verification and reproduction

Independent reconstruction passes all 5,511,965 minute rows, 191,786 M30 OHLC bars,
191,781 feature rows per variant, 50,004 labelled trade rows, all economic tables,
40,000 bootstrap group draws and 8,000 placement draws. Thirteen focused feature/
economics tests pass. Protocol and all 23 artifact hashes match the verification
record. The [comparison chart](vwap_summary.png) was rendered and visually checked.

Generated tables, ledgers and JSON audits: `Reports/rtl_vwap_20261025/` (gitignored).
Code: `python/build_rtl_vwap_features.py`, `analyze_rtl_vwap.py`,
`verify_rtl_vwap.py`, `report_rtl_vwap.py`; tests `test_rtl_vwap*.py`.

```powershell
.\venv\Scripts\python.exe python\build_rtl_vwap_features.py
.\venv\Scripts\python.exe python\analyze_rtl_vwap.py
.\venv\Scripts\python.exe python\verify_rtl_vwap.py
.\venv\Scripts\python.exe -m unittest discover -s python -p 'test_rtl_vwap*.py'
.\venv\Scripts\python.exe python\report_rtl_vwap.py
```
