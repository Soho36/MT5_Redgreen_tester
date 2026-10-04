"""Q12 contact eligibility. Prior breaks and departures never retire a level."""

import numpy as np

from level_visit import merge_levels, swing_lows


def classify_contact(b, s, n=5, sessions=5, pivots=None):
    """Return contact/no_contact or an availability reason using pre-signal levels."""
    low, high = b.low.to_numpy(), b.high.to_numpy()
    contract, sn = b.contract.to_numpy(), b.session_number.to_numpy()
    first = sn[s] - sessions
    if first < 0:
        return "missing_history"
    start = int(np.searchsorted(sn, first, side="left"))
    if not (contract[start:s + 1] == contract[s]).all():
        return "contract_roll"
    a = b.atr.iloc[s]
    if not np.isfinite(a) or a <= 0:
        return "invalid_atr"
    if pivots is None:
        pivots = swing_lows(low, contract, n)
    known = pivots[(pivots >= start) & (pivots + n < s)]
    d = 0.5 * a
    levels = merge_levels(known.tolist(), low, d)
    return "contact" if any(low[s] <= v["level"] + d and high[s] >= v["level"] - d
                            for v in levels) else "no_contact"


def exact_contact(low, high, level):
    """Inclusive range contact, independent of candle open, close or past breaks."""
    return (low <= level) & (level <= high)
