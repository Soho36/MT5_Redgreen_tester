"""Q15 falling trendline resistance; see docs/setups/trendlines/downtrend-breakout-long/q15-falling-resistance/PROTOCOL.md.

Exact mirror of trendline_support: negating prices (high <-> -low, open/close -> -open/-close)
turns lines through consecutive lower swing highs into lines through consecutive higher swing
lows, a close above a line into a close below it, and leaves true range (ATR) unchanged.
Nothing here reads outcomes.
"""

import trendline_support as ts
from level_visit import swing_lows

GROUP_NAMES = {"trendline_support": "resistance_test", "slice_through": "poke_through",
               "broken_contact": "broken_contact", "not_departed_contact": "not_departed_contact",
               "no_contact": "no_contact", "missing_history": "missing_history",
               "contract_roll": "contract_roll", "invalid_atr": "invalid_atr"}
GROUPS = tuple(GROUP_NAMES[g] for g in ts.GROUPS)
UNAVAILABLE = GROUPS[5:]
BROAD = ("resistance_test", "poke_through", "not_departed_contact")


def mirror(b):
    """Bar frame with prices negated and high/low swapped; contract, sessions and ATR kept."""
    m = b.copy()
    m["open"], m["high"], m["low"], m["close"] = -b.open, -b.low, -b.high, -b.close
    return m


def swing_highs(high, contract, n):
    """Indices whose high is > the n highs before and >= the n highs after, same contract."""
    return swing_lows(-high, contract, n)


def classify(m, s, n=5, sessions=5, min_sep=10, min_slope=0.02, pivots=None):
    """Classify signal s against falling lines. `m` is mirror(bars); pivots from swing_highs."""
    group, info = ts.classify(m, s, n, sessions, min_sep, min_slope, pivots)
    if "line" in info:
        info = dict(info)
        info["line"] = -info.pop("line")              # resistance price V
        info["poke_a"] = info.pop("depth_a")          # (signal high - V) / A
        info["opens_above"] = info.pop("opens_below")
        info["slope_a"] = -info["slope_a"]            # negative: falling
        # wick_reaches now means high >= V; breaks_on_signal means close > V + D.
    return GROUP_NAMES[group], info


def classify_contact(m, s, n=5, sessions=5, min_sep=10, min_slope=0.02, pivots=None):
    """Broad contact with any unbroken falling line."""
    return ts.classify_contact(m, s, n, sessions, min_sep, min_slope, pivots)
