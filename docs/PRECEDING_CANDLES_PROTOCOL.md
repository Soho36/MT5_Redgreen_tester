# Q1 / Q2 first diagnostic protocol

Fixed on 2026-09-30 before running the new diagnostics. No new entry filters or
parameter optimization are part of this first scan.

## Population and collection

- Run the actual runband EA with `MaxRedRun=3`, `MinLocation=0`, RR=1,
  the same MNQ M30 symbol, sessions, and 1-minute OHLC model as the frozen runs.
- Repeat 2015-01-01 to 2020-01-01 and 2020-01-02 to 2026-07-14 separately,
  with `SnapshotBars=51` and unique run tags.
- Verify the logger changes no trades: compare all original trade fields to
  `train1519_run3` and `test2026_run3`, and reconcile counts/PnL with MT5 stats.
- Snapshot raw OHLC at order placement, not fill. Replaced orders get replaced
  snapshots; green bars do not move an existing order's snapshot.
- Exclude incomplete history from diagnostics, never silently shorten N.
- The data have already been examined. Call this exploratory chronology, not
  a fresh out-of-sample test. Do not choose a new winner from 2020–2026.

## Exact definitions

Bar 1 is the completed signal, bar 2 the preceding bar. Use N in {5,10,20,50}.

### Q1: interrupted-decline proxy

- `red_share_N`: fraction of bars 2..N+1 with close < open; dojis are not red.
- `down_share_N`: fraction of the N-1 adjacent close comparisons within that
  same window which move downward in chronological order. Equal closes do not
  count as downward. No extra boundary bar is used.
- Fixed descriptive bins for each share: `<0.4`, `0.4 to <0.6`, `>=0.6`.
- Primary flag: both shares >= 0.6. All trades already pass the red-run cap.
  This is a density proxy for interrupted declines, not proof of a particular
  small-green-candle pattern. The 0.6 threshold is a working definition, not
  a researched optimal cutoff.
- Compare flagged trades with the complement and retain both component-bin
  tables so an apparent result cannot be attributed to an unnamed definition.

### Q2: low breach and recovery

Let `prior_low_N = min(low[2], ..., low[N+1])`.

- `no_breach`: signal low >= prior_low_N (equal lows do not break it).
- `breach_no_recovery`: signal low < prior_low_N and close <= prior_low_N.
- `breach_recovered`: signal low < prior_low_N and close > prior_low_N.
- A close exactly at the old low is not a recovery. Classifications use only
  completed bars, independent of the later buy-stop fill.

## Reporting and decisions

Report each category's count, gross PF, gross average R, modeled net PF/net
average R/net total dollars ($1 per round-turn, $2 per price point), and years.
Use fixed chronological subdivisions 2015–2017, 2018–2019, 2020–2022,
2023–2026 plus both whole periods. Retain every N and every category.
For direct comparisons, bootstrap the **difference in average gross R** between
the two Q1 groups and between the two breached-low Q2 groups by common calendar
month blocks (2,000 resamples, seed 20260930). Preserve months with no trades in
a group. Intervals are descriptive, unadjusted for multiple comparisons and
not proof of statistical significance. Sparse groups must be labeled.

No claim of a strategy DD/profit improvement from a subset table. A promising
pattern must have reasonable counts, the same direction across periods, and
nearby-N support before a separately specified full-strategy test. If no such
pattern appears, record that outcome and leave the EA's entry rules unchanged.
