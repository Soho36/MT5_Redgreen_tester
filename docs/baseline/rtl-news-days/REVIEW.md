# Review: do news days really hurt RTL?

Written 2026-11-10, after the [whole-day study](RESULTS.md) was committed.
The checks below were chosen after seeing its results. They explain why the
result came out as it did; they are not a new test.

**Plain answer: the evidence does not show it.** Since 2020 the gain from
skipping CPI, payroll and FOMC days comes from 15 of the 210 news days, the ones
that fell inside the four deepest drawdowns. A typical news day earned the same
as a typical ordinary day, and news-day trades were no worse per unit of risk.
With the VWAP filter on, skipping news days lowers profit and raises drawdown.
The study's conclusion, no baseline change, stands. "Promising" is too strong.

The study itself checks out: 29 hand-typed figures in RESULTS.md match the CSVs,
its six tests pass, and its random-day ranks reproduce exactly.

## A few days carry the result

2020–September 2026, original RTL, intraday equity drawdown:

| Scenario | Net | Equity DD |
|---|---|---|
| Original RTL | $38,400 | $5,942 |
| Skip every news day (the study's rule) | $42,139 | $4,037 |
| Skip only the 5 worst news days | $44,781 | $4,463 |
| Skip every news day except those 5 | $35,757 | $5,927 |
| Skip only the 15 news days inside the four deepest drawdowns | $44,483 | $4,037 |
| Skip only the other 195 news days | $36,056 | $5,942 |

- **The five worst:** 2025-04-04, 2026-06-17, 2026-02-13, 2022-05-11 and
  2026-03-06 lost $6,382 together. The other 205 news days made $2,643.
- **The typical day:** median news day +$23.8, median ordinary day +$24.2.
  114 news days were up and 96 were down.
- **The four deepest drawdowns:** Jan–Mar 2026 ($5,942), Feb–Apr 2025 ($5,007),
  Feb–Mar 2020 ($4,463) and Jun–Jul 2026 ($4,462). Four of the five worst news
  days sit inside them.
- **Other causes:** 4 April 2025, the worst, was a payrolls day in the middle of
  the tariff sell-off; a plain long lost $2,482 that session. 11 March 2020 was
  a CPI day in the middle of the COVID crash.

The "skip only" rows use hindsight and are not rules. They show where the result
sits: outside those few days, skipping news costs money and does nothing for
drawdown.

## Four more checks

**1. Most of the loss came before the news was out.** News-day trades in
2020–26, by when they ran:

| | Trades | Net | Mean net R |
|---|---|---|---|
| Closed before the release | 809 | −$2,912 | +0.021 |
| Open across the release | 115 | +$978 | +0.251 |
| Entered after the release | 368 | −$1,805 | +0.073 |

The [±30-minute follow-up](../rtl-news-windows/RESULTS.md) agrees: blocking only
the announcement window does not reproduce the whole-day result.

**2. Per unit of risk, news-day trades were not worse.** Mean net R per trade:

| Era | News days | Other days | Difference (95% range) |
|---|---|---|---|
| 2010–15 | −0.229 | −0.174 | −0.06 (−0.13 to +0.02) |
| 2016–19 | +0.027 | −0.020 | +0.05 (−0.07 to +0.16) |
| 2020–26 | +0.056 | +0.046 | +0.01 (−0.07 to +0.09) |

Every range includes zero. The dollars were lost by a few very large trades: in
2020–26 the 27 news-day trades in the largest 1% by dollar risk lost $3,715,
almost the whole −$3,739. The protocol asked for R to be reported; RESULTS.md
shows dollars only.

**3. It follows the market.** RTL is long-only. News-day totals, RTL against one
plain long per session:

| Year | RTL | Plain long |
|---|---|---|
| 2022 | −$3,488 | −$2,790 |
| 2023 | +$1,221 | +$4,787 |
| 2024 | +$3,577 | +$2,122 |
| 2025 | −$2,306 | −$709 |
| 2026 | −$2,637 | −$5,266 |

Skipping news days helped in the years the market itself fell on them and cost
money in the years it rose. In 2016–21, where the amounts are small, the signs
agree in three years of six. A plain long earned $20.9 per news session against
$5.5 on other sessions in 2016–19, and −$6.2 against +$24.1 since 2020. The rule
is a bet that the recent pattern continues.

**4. With the other filters on, it reverses.** 2020–26:

| Variant | News days earned | Net if skipped | Daily-close DD if skipped |
|---|---|---|---|
| Original RTL | −$3,739 | $38,400 → $42,139 | $5,781 → $3,804 |
| + exclude16-17 | −$1,227 | $39,851 → $41,078 | $5,095 → $3,708 |
| + VWAP | +$850 | $45,725 → $44,875 | $3,158 → $3,454 |
| + VWAP + exclude16-17 | +$2,379 | $47,259 → $44,880 | $2,698 → $2,961 |

These rows subtract whole sessions from each saved ledger and measure drawdown
at daily closes. The study proved that subtraction exact for the original RTL
only, so the filtered rows are estimates, not native runs. In 2016–19 news days
were profitable on all four variants.

## What still counts in the rule's favour

- The 99.67% rank against random days is correct, and it holds when the random
  days are also matched on day size (99.78%).
- Since 2020 news days are over-represented among the worst sessions: 13 of the
  worst 50, where about 6 would be expected. In 2016–19 it is 6 of 50, as
  expected.

Both come from the same few days inside the 2025 and 2026 drawdowns, in one era.

## What this means

- Treat the news-day rule as not shown. Only new data going forward can settle it.
- ES, YM and RTY are not fresh data for a calendar rule. They share the dates and
  the same market moves, so they would repeat the same few days.
- The tester fills stops at their level without slippage. Whether real fills
  around releases are worse is a separate question that needs forward (demo or
  live) fills.

## For the next study

- Commit PROTOCOL.md on its own before the runs, so the freeze shows in the
  history.
- Report R next to dollars, and add three rows: leave the worst days out, the
  plain long on the same days, and the variant with the other filters on.
- Keep the generated EA and the manifests in git. `Reports/` is ignored, so this
  study cannot be rebuilt from the repo alone.
- `report_rtl_news_days.py` has its conclusions and dozens of figures typed in
  as text. Compute them, or keep prose out of the generator.
- `build_news_calendar.py` has the cutoff date and the 2025/2026 counts typed
  in, and the BLS pages came through a web reader that no script reproduces.
  Extending the calendar needs both fixed.

## Reproduce

```powershell
& .\venv\Scripts\python.exe python\review_rtl_news_days.py
```

It needs the saved evidence in `Reports/` and the release times from the
±30-minute follow-up. It first confirms that its own drawdown code reproduces
the study's net, equity DD and random-day ranks, then prints each check and
writes [review_checks.csv](review_checks.csv).
