# Rejected-entry rescue: results (2026-11-13)

[Protocol](PROTOCOL.md), fixed before results. Outputs:
`Reports/entry_rescue_20261113/` (`compare.csv`, `summary.csv`, `buckets.csv`,
`rejection_frequency.csv`, `rescued_trades.csv`, `validation.json`).
Program: `python/analyze_entry_rescue.py`.

**Verdict: the rescue loses. Keep skipping a rejected entry.** A buy limit that
fills because price came back to the level within a minute selects failed
breakouts. Rescued trades are worse than normal trades in every era for GG,
and for the near-miss case the user described (0-2 ticks, between bars) in
both strategies.

## Validation

- With no rescue the study's engine copy equals `simulate_m30_ea` trade for trade
  in all four runs (RTL/GG x gate off/on).
- GG against the MT5 ledgers (`Reports/gg_vwap_ea_20261030`): the same trades
  except 17 in the first three days of data (EA warm-up) and 700 entries in the
  same minute with a different seconds stamp. MT5 has no entry on any bar the
  engine rejected, so the rejection rule matches.

## Frequency (gate on, as live)

| | Rejections 2010-26 | Per week 2025-26 | At the level or 1-2 ticks | Session open |
|---|---|---|---|---|
| GG | 2,582 | 1.08 | 84% | 24% |
| RTL | 324 | 0.56 | 36% | 77% |

About 1.6 a week for the two together, as the user observed. GG's are mostly
near misses between bars (a green bar closes near its high); RTL's are mostly
session-open gaps.

## Outcome, 1-minute rescue (gate on)

Mean net R per trade, bootstrap 95% interval for the rescued trades:

| | Era | Normal trades | Rescued trades | Rescue fill rate | Strategy net change |
|---|---|---|---|---|---|
| GG | 2010-15 | -0.144 | -0.200 [-0.276, -0.123] | 76% | -$257 |
| GG | 2016-19 | -0.019 | -0.234 [-0.351, -0.113] | 80% | -$757 |
| GG | 2020-26 | +0.045 | -0.029 [-0.189, +0.138] | 65% | -$1,831 |
| RTL | 2010-15 | -0.206 | -0.614 [-0.872, -0.346] | 66% | -$66 |
| RTL | 2016-19 | -0.009 | -0.393 [-0.844, +0.101] | 58% | +$21 |
| RTL | 2020-26 | +0.067 | +0.418 [-0.040, +0.926] | 43% | +$1,209 |

Net change includes displaced trades (a rescued trade holding the position when
a later signal arrives; GG 1,312 over 16 years).

By overshoot and place (all eras, 1-minute rescue):

| | Split | Rescued | Mean net R |
|---|---|---|---|
| GG | 0-2 ticks | 1,732 | -0.195 [-0.258, -0.130] |
| GG | between bars | 1,571 | -0.177 [-0.242, -0.111] |
| RTL | 0-2 ticks | 105 | -0.609 [-0.846, -0.368] |
| RTL | between bars | 68 | -0.762 [-1.041, -0.459] |
| RTL | > 8 ticks | 47 | +0.704 [+0.137, +1.313] |
| RTL | session open | 109 | +0.109 [-0.207, +0.444] |

RTL's positive recent number comes from large session-open gaps (47 trades), not
from the near misses, which lose heavily. Longer windows (2, 5, 25 minutes) fill
a few more and are no better (GG net -$3,131 to -$3,394 vs -$2,845 at 1 minute).

No strategy change.
