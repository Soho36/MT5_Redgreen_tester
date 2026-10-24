# RTL downtrend crystal ball, early signals: early costs far less than late

2026-10-25. Exploratory addendum to the [crystal-ball study](RESULTS.md), under
the [frozen early-signal addendum](EARLY_PROTOCOL.md). Current uncapped RTL only.

**Being early is much more forgiving than being late.** With stop and resume both
two sessions early, skipping downtrends still adds +20% to +59% net profit at
every size in both eras; two sessions late gives -9% to +28%. If the resume is
exactly at the low, stopping up to five sessions early still adds +8% to +130%.
By the rule fixed in advance, **a pullback-anticipation statistic is worth
building** (unadjusted closes agree). It is a necessary condition only: the
crystal ball never fires before a rally that keeps going, and a real predictor
will. No strategy defaults or live settings changed.

## Why this was tested

The user asked whether "up N% over n sessions, so a pullback is likely soon" is
worth building. Such a signal acts before the turn, so it errs early rather than
late. The first study measured only lateness.

## 1. Stop and resume both shifted

Change in net profit versus trading every session, roll-adjusted closes
(negative = early; late columns from the first study):

| Era | Drop | 5 early | 3 early | 2 early | 1 early | On time | 1 late | 2 late | 3 late |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2016-19 | 2% | -5% | -14% | +28% | +41% | +202% | +56% | -7% | -35% |
| 2016-19 | 3% | +8% | +25% | +59% | +59% | +152% | +71% | +15% | -10% |
| 2016-19 | 5% | +13% | +43% | +45% | +64% | +92% | +43% | +17% | -5% |
| 2016-19 | 10% | +14% | +19% | +20% | +28% | +36% | +17% | +3% | -1% |
| 2020-26 | 2% | -48% | -9% | +27% | +52% | +172% | +50% | -9% | -26% |
| 2020-26 | 3% | -38% | +2% | +31% | +45% | +134% | +46% | +7% | -15% |
| 2020-26 | 5% | -16% | +18% | +44% | +48% | +97% | +46% | +28% | +5% |
| 2020-26 | 10% | -1% | +18% | +24% | +29% | +39% | +18% | +16% | +8% |

Two sessions early beats 97.5% of shifted placements at every size and era;
three early does so for 3% and 5% drops. Five early mostly loses in 2020-26.

## 2. Stop early, resume exactly at the low

| Era | Drop | On time | 1 early | 2 early | 3 early | 5 early |
|---|---|---:|---:|---:|---:|---:|
| 2016-19 | 2% | +202% | +130% | +96% | +52% | +21% |
| 2016-19 | 3% | +152% | +120% | +113% | +91% | +72% |
| 2016-19 | 5% | +92% | +87% | +79% | +75% | +58% |
| 2016-19 | 10% | +36% | +36% | +32% | +34% | +28% |
| 2020-26 | 2% | +172% | +110% | +76% | +42% | +8% |
| 2020-26 | 3% | +134% | +87% | +73% | +49% | +19% |
| 2020-26 | 5% | +97% | +70% | +63% | +46% | +27% |
| 2020-26 | 10% | +39% | +33% | +30% | +28% | +24% |

All rows beat 97.5% of shifted placements. An imprecise stop is affordable when
the resume is right; this case assumes the end of every drop is known exactly.

![Crystal-ball gain by timing](../../../Reports/rtl_downtrend_early_20261025/timing.png)

## 3. Why early is cheaper: what sits next to the peak and the low

Descriptive check after the run (not in the addendum). RTL trades in the two
sessions on each side of the turns, 2% drops:

| Window | 2016-19 trades / net $ / mean R / mean risk $ | 2020-26 trades / net $ / mean R / mean risk $ |
|---|---|---|
| Last 2 rally sessions (skipped if early) | 525 / +3,987 / +0.176 / 26.5 | 1,518 / +30,184 / +0.225 / 80.3 |
| First 2 fall sessions (kept if late) | 517 / -3,033 / -0.181 / 28.6 | 1,469 / -26,221 / -0.131 / 87.9 |
| Last 2 fall sessions (kept if early) | 516 / -3,671 / -0.102 / 34.6 | 1,443 / -25,181 / -0.169 / 102.2 |
| First 2 rebound sessions (skipped if late) | 524 / +6,197 / +0.264 / 36.7 | 1,510 / +43,149 / +0.201 / 99.2 |

Both edges of a rally are good for RTL, and both edges of a fall are bad. Being
late costs the rebound, which in dollars is the most valuable window: volatility
is highest near lows, so stops and dollar results are largest there (mean risk
$99-133 recently versus $79 overall). In 2016-19 the rebound also wins in R per
trade at every size, so early is better both ways. In 2020-26, per trade in R,
two early and two late are about equal (retained +0.075 to +0.083 R versus
+0.083 to +0.089 R; baseline +0.048): **the recent early advantage is mostly a
dollar effect of the larger trades around lows.**

## What this means for the user's step 2

- There is room for an early warning, so building the pullback statistic is
  justified by the fixed rule.
- **The resume matters more than the stop.** Section 2 shows the stop can be
  several sessions early if the resume is on time. The live zigzag both stopped
  and resumed late; section 3 shows the late resume is the costlier part, since
  it gives up the rebound (2% drops: $43,149 versus $26,221 recently, $6,197
  versus $3,033 earlier). "Up N%, pullback soon" only covers
  the stop. Step 2 also needs an early resume signal (for example "down N%,
  bounce soon") and must never wait for confirmation.
- **False alarms are not in this ceiling.** The crystal ball skips only around
  drops that really happen. A predictor will also fire before rallies that
  continue, skipping RTL's best periods (+0.17 R per trade recently outside 2%
  drops), and will miss some drops. Step 2 must measure its hit rate against the
  base rate (a 2% drop starts about every 14 sessions recently).
- A predictor errs both early and late. Late was already shown to fail, so it
  must lean early.

## Limits

Ledger omission, not an MT5 replay. Dollar results lean on volatile sessions
near lows. All history has been used in earlier studies; this is exploratory.
Section 3 is a descriptive explanation chosen after seeing the main results.

## Verification

Addendum SHA256 (CRLF-normalized):
`655edc14bda6f3dd2faf54c907c17a5d8237622cd5902f8c598c3c0fd0eabe05`, checked before
and after the run; the original protocol is unchanged. The on-time reference
reproduces the first study exactly. **Independent verification: PASS** (7 of 7):
masks from explicit session ranges using the first verifier's separate zigzag,
all 144 rule/era ledger partitions and drawdowns, every circular shift, and the
decision. **All 15 focused tests pass** (5 new: start-of-history clipping,
merged overlaps, both early rule types, on-time equivalence).

- `python/analyze_rtl_downtrend_early.py`, `python/verify_rtl_downtrend_early.py`,
  `python/test_rtl_downtrend_early.py`, `python/report_rtl_downtrend_early.py`.
- Outputs: `Reports/rtl_downtrend_early_20261025/`;
  [calculated tables](../../../Reports/rtl_downtrend_early_20261025/report_tables.md).
