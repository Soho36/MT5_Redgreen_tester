"""Q14 rising trendline map and signal classification; see docs/setups/trendlines/uptrend-bounce-long/q14-trendline-support/PROTOCOL.md.

Pure functions on arrays of consecutive M30 bars (the bar frame from level_visit.bar_frame).
Nothing here reads outcomes. A line is projected in bar-index space: one step per M30 bar,
overnight and weekend gaps included, which is how an MT5 chart draws a two-point trendline.
"""

import numpy as np

from level_visit import swing_lows

GROUPS = ("trendline_support", "slice_through", "broken_contact", "not_departed_contact", "no_contact",
          "missing_history", "contract_roll", "invalid_atr")
UNAVAILABLE = GROUPS[5:]
CONTACT_GROUPS = GROUPS[:4]


def line_value(i, j, low, k):
    """Value at bar k of the line through (i, low[i]) and (j, low[j])."""
    return low[i] + (low[j] - low[i]) * (k - i) / (j - i)


def candidate_pairs(known, low, min_sep):
    """Consecutive higher lows: for each known pivot j, the latest earlier pivot i with
    low[i] < low[j]. Every pivot between them is at or above low[j], so each anchor j has at
    most one partner. Kept if j - i >= min_sep."""
    known = np.asarray(known, dtype=int)
    ii, jj = [], []
    for k in range(1, len(known)):
        j = known[k]
        lower = np.flatnonzero(low[known[:k]] < low[j])
        if len(lower) and j - known[lower[-1]] >= min_sep:
            ii.append(known[lower[-1]])
            jj.append(j)
    return np.asarray(ii, dtype=int), np.asarray(jj, dtype=int)


def line_state(i, j, s, low, close, a, d):
    """(valid, broken, departed, retests) for one line, using bars before signal s only.

    valid:    no low between the anchors more than D below the line (it really underlies them).
    broken:   a close after anchor j more than D below the line.
    departed: a close after anchor j at least A above the line.
    retests:  earlier returns from above: bars after anchor j (before s) whose low reaches
              line + D after a close at least A above the line since anchor j or since the
              previous retest. 0 means the signal is the first retest; descriptive only.
    """
    between = np.arange(i + 1, j)
    if len(between) and (low[between] < line_value(i, j, low, between) - d).any():
        return False, False, False, 0
    after = np.arange(j + 1, s)
    if not len(after):
        return True, False, False, 0
    v = line_value(i, j, low, after)
    broken = bool((close[after] < v - d).any())
    away = close[after] >= v + a
    retests, armed = 0, False
    for reached, left in zip(low[after] <= v + d, away):
        if armed and reached:
            retests, armed = retests + 1, False
        armed = armed or bool(left)
    return True, broken, bool(away.any()), retests


def window_start(sn, contract, s, sessions):
    """First bar of the window, or an unavailability reason."""
    first = sn[s] - sessions
    if first < 0:
        return "missing_history"
    start = int(np.searchsorted(sn, first, side="left"))
    if not (contract[start:s + 1] == contract[s]).all():
        return "contract_roll"
    return start


def contacted_lines(b, s, n=5, sessions=5, min_sep=10, min_slope=0.02, pivots=None):
    """All valid rising lines whose zone the signal range overlaps.

    A line must rise at least min_slope x A per bar (A = the signal's lagged ATR); flatter
    lines are horizontal levels, studied in docs/setups/horizontal/.

    Returns (reason_or_None, a, d, known, lines) where lines are dicts with state.
    """
    low, high, close = b.low.to_numpy(), b.high.to_numpy(), b.close.to_numpy()
    contract, sn = b.contract.to_numpy(), b.session_number.to_numpy()
    start = window_start(sn, contract, s, sessions)
    if isinstance(start, str):
        return start, None, None, None, []
    a = b.atr.iloc[s]
    if not np.isfinite(a) or a <= 0:
        return "invalid_atr", None, None, None, []
    d = 0.5 * a
    if pivots is None:
        pivots = swing_lows(low, contract, n)
    # Known: both anchors inside the window and confirmed (bar + n closed) before s opens.
    known = pivots[(pivots >= start) & (pivots + n <= s - 1)]
    ii, jj = candidate_pairs(known, low, min_sep)
    steep = (low[jj] - low[ii]) / np.maximum(jj - ii, 1) >= min_slope * a
    ii, jj = ii[steep], jj[steep]
    v = line_value(ii, jj, low, s) if len(ii) else np.empty(0)
    hit = (low[s] <= v + d) & (high[s] >= v - d)
    lines = []
    for i, j, value in zip(ii[hit], jj[hit], v[hit]):
        valid, broken, departed, retests = line_state(int(i), int(j), s, low, close, a, d)
        if valid:
            lines.append(dict(i=int(i), j=int(j), value=float(value), broken=broken, departed=departed,
                              retests=retests, slope_a=float((low[j] - low[i]) / (j - i) / a)))
    return None, a, d, known, lines


def classify(b, s, n=5, sessions=5, min_sep=10, min_slope=0.02, pivots=None):
    """Q11-style group for one signal against rising trendlines. Returns (group, details)."""
    s = int(s)
    reason, a, d, known, lines = contacted_lines(b, s, n, sessions, min_sep, min_slope, pivots)
    if reason:
        return reason, {}
    low, opn, close = b.low.to_numpy(), b.open.to_numpy(), b.close.to_numpy()
    intact = [x for x in lines if not x["broken"] and x["departed"]]
    support = [x for x in intact if low[s] >= x["value"] - d]
    if support:
        group, chosen = "trendline_support", support
    elif intact:
        group, chosen = "slice_through", intact
    elif lines and all(x["broken"] for x in lines):
        group, chosen = "broken_contact", lines
    elif lines:  # unbroken, never-departed lines (possibly alongside broken ones)
        group, chosen = "not_departed_contact", [x for x in lines if not x["broken"]]
    else:
        return "no_contact", dict(atr=a, d=d, known_pivots=len(known))
    x = min(chosen, key=lambda z: (abs(low[s] - z["value"]), -z["j"], -z["i"]))
    v = x["value"]
    return group, dict(atr=a, d=d, known_pivots=len(known), qualifying=len(chosen), contacted=len(lines),
                       line=v, anchor1=x["i"], anchor2=x["j"], anchor_sep=x["j"] - x["i"], slope_a=x["slope_a"],
                       retests=x["retests"], depth_a=(v - low[s]) / a, wick_reaches=bool(low[s] <= v),
                       opens_below=bool(opn[s] < v), breaks_on_signal=bool(close[s] < v - d),
                       bars_since_anchor2=s - x["j"])


def classify_contact(b, s, n=5, sessions=5, min_sep=10, min_slope=0.02, pivots=None):
    """Broad (Q12-style) contact: any unbroken valid rising line, whatever the departure,
    depth or candle side. Lines broken before the signal are excluded: unlike a horizontal
    level, a broken rising line's projection has no remaining meaning as a price."""
    reason, _, _, _, lines = contacted_lines(b, int(s), n, sessions, min_sep, min_slope, pivots)
    return reason or ("contact" if any(not x["broken"] for x in lines) else "no_contact")
