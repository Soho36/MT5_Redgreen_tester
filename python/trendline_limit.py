"""Q20 buy limit resting on a rising trendline; see docs/trendlines/TRENDLINE_LIMIT_PROTOCOL.md.

Per-bar order price at the open of bar t, using closed bars only (bars < t). The lines are the frozen
Q14 ones (python/trendline_support.py), evaluated at bar t instead of at a red signal bar. Nothing
here reads outcomes. Arming after fills (one trade per departure episode) belongs to the trading run;
here a line is "armed" when it is valid, intact and departed, i.e. fills are ignored.
"""

import numpy as np

from trendline_support import candidate_pairs, line_state, line_value, window_start

TICK = 0.25
EPS = 1e-9  # same constant in mt5/experts/trendline_limit.mqh: a value exactly on a tick stays there
STATUSES = ("order", "no_line", "above_price", "missing_history", "contract_roll", "invalid_atr")


def floor_tick(x, tick=TICK):
    return np.floor(x / tick + EPS) * tick


def armed_lines(b, t, pivots, n=5, sessions=5, min_sep=10, min_slope=0.02):
    """(reason_or_None, a, known, lines): every valid, intact, departed rising line at the open of t."""
    low, close = b.low.to_numpy(), b.close.to_numpy()
    start = window_start(b.session_number.to_numpy(), b.contract.to_numpy(), t, sessions)
    if isinstance(start, str):
        return start, None, None, []
    a = b.atr.iloc[t]
    if not np.isfinite(a) or a <= 0:
        return "invalid_atr", None, None, []
    d = 0.5 * a
    known = pivots[(pivots >= start) & (pivots + n <= t - 1)]
    ii, jj = candidate_pairs(known, low, min_sep)
    steep = (low[jj] - low[ii]) / np.maximum(jj - ii, 1) >= min_slope * a
    lines = []
    for i, j in zip(ii[steep], jj[steep]):
        valid, broken, departed, retests = line_state(int(i), int(j), t, low, close, a, d)
        if valid and not broken and departed:
            lines.append(dict(i=int(i), j=int(j), value=float(line_value(i, j, low, t)), retests=retests,
                              slope_a=float((low[j] - low[i]) / (j - i) / a)))
    return None, a, known, lines


def choose_line(lines, ask):
    """The armed line with the highest value strictly below the ask; ties: later j, then later i."""
    below = [x for x in lines if x["value"] < ask]
    return max(below, key=lambda z: (z["value"], z["j"], z["i"])) if below else None


def bar_order(b, t, pivots, ask=None, stop_a=0.5, n=5, sessions=5, min_sep=10, min_slope=0.02):
    """(status, details) for the order the primary would rest during bar t.

    The line is the armed line with the highest V(t) strictly below the ask (default: bar t's open);
    ties go to the later j, then the later i. Limit = V rounded down to the tick; stop = limit - stop_a x A,
    rounded down. No line below the ask -> no order for this bar."""
    t = int(t)
    reason, a, known, lines = armed_lines(b, t, pivots, n, sessions, min_sep, min_slope)
    if reason:
        return reason, {}
    ask = float(b.open.iloc[t]) if ask is None else float(ask)
    info = dict(atr=a, known_pivots=len(known), lines_armed=len(lines))
    if not lines:
        return "no_line", info
    info["lines_below"] = sum(x["value"] < ask for x in lines)
    x = choose_line(lines, ask)
    if x is None:
        return "above_price", info
    limit = float(floor_tick(x["value"]))
    stop = float(floor_tick(limit - stop_a * a))
    return "order", dict(info, line=x["value"], limit=limit, stop=stop, anchor1=x["i"], anchor2=x["j"],
                         retests=x["retests"], slope_a=x["slope_a"], bars_since_anchor2=t - x["j"],
                         anchor_sep=x["j"] - x["i"], delta=(float(b.open.iloc[t]) - x["value"]) / a)
