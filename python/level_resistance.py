"""Q18 horizontal swing-high resistance (breakout from below); see docs/setups/horizontal/resistance-breakout-long/q18-breakout/PROTOCOL.md.

Exact mirror of the frozen Q11 classifier (level_visit.classify, including its pre-outcome amendment):
negating prices turns confirmed swing highs into swing lows, a close above a level into a close below it,
and leaves true range (ATR) unchanged. Nothing here reads outcomes.
"""

import level_visit as lv
from trendline_resistance import mirror, swing_highs

GROUP_NAMES = {"support_revisit": "breakout_test", "slice_through": "poke_through",
               "broken_contact": "broken_upward_contact", "not_departed_contact": "not_departed_contact",
               "no_contact": "no_contact", "missing_history": "missing_history",
               "contract_roll": "contract_roll", "invalid_atr": "invalid_atr"}
GROUPS = tuple(GROUP_NAMES[g] for g in lv.GROUPS)
UNAVAILABLE = GROUPS[5:]
BROAD = ("breakout_test", "poke_through", "broken_upward_contact", "not_departed_contact")

__all__ = ["mirror", "swing_highs", "classify", "GROUPS", "UNAVAILABLE", "BROAD"]


def classify(m, s, n=5, sessions=5, pivots=None):
    """Classify signal s against swing-high levels. `m` is mirror(bars); pivots from swing_highs."""
    group, info = lv.classify(m, s, n=n, sessions=sessions, pivots=pivots)
    if "level" in info:
        info = dict(info)
        info["level"] = -info["level"]                          # resistance price L (highest member high)
        info["poke_a"] = info.pop("depth_a")                    # (signal high - L) / A
        info["opens_above"] = info.pop("opens_below")           # open > L
        info["closes_above_since"] = info.pop("closes_below_since")  # closes > L since the last member
        # wick_reaches now means high >= L; breaks_on_signal means close > L + D.
    return GROUP_NAMES[group], info
