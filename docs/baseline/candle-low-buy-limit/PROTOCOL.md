# Buy limit at the last candle low

2026-11-23. User-requested exploratory test, fixed before outcomes.

- Completed M30 candle of any colour (including doji); buy limit exactly at its low.
- Stop = low - (high - low); resting take profit = high (1:1).
- User confirmed replacement of every unfilled order after each completed candle.
- One position at a time. Once filled, its original stop/target remain fixed.
- Existing MNQ research settings: entries 01:00 to before 23:30 on the synthetic
  Chicago+8 session clock; session flatten at 23:30, early-close calendar and
  next-session fallback. An order can execute on a new bar's opening quote before
  the EA cancels/replaces it, matching MT5's normal event ordering.
- Zero-range candles cancel the old order and produce no new order.
- If the low is already at/above ask when submitting, skip it: this test requires
  entry exactly at that low and does not substitute an immediate market entry.
- MNQcontDTBNT20102026_2, 2010-06-07 through 2026-09-30; 1-minute OHLC,
  one MNQ ($2/point), observed one-tick spread, $1.05 round-turn costs deducted.
- Main periods: 2010-15, 2016-19, 2020-Sep2026. Report trades, net, win rate,
  PF, mean R and closed-balance drawdown, including session-close exits.
- Native MT5 plus independent minute replay and focused boundary tests.
- Predeclared sensitivity: require ask one extra tick through entry before filling
  at the limit, and bid one extra tick beyond TP. Replay only, to assess touch fills.

No parameter search. History already used extensively; exploratory screen, not
untouched validation. OHLC assumes a price sequence within every minute and does
not model queue priority, tick-level slippage or liquidity. Baselines stay unchanged.
