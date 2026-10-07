"""Q21 short the breakdown of a rising trendline; see docs/setups/trendlines/uptrend-breakdown/q21-breakdown-short/PROTOCOL.md.

Signal for the open of bar t: bar s = t - 1 is the breakdown candidate. The lines are the frozen Q14/Q20 ones
(python/trendline_limit.armed_lines), evaluated at the open of s from bars before s. A line is live if no close
since its first departure (close >= V + A) has been below V - depth_a x A, and it has not been spent; s breaks it if
close(s) < V(s) - depth_a x A (primary depth_a = 0, sensitivity S1 = 0.5). A red s that breaks a live line gives a
sell stop at low(s), stop loss high(s), for bar t only. Nothing here reads outcomes.

Spending is stateful. A is re-measured at every bar, so a larger A(s) can move a line's first departure past an
earlier close below it, or lift an earlier S1 break back inside D. A break is therefore recorded at the bar it
happens (judged with that bar's A), on every bar whether or not bar t is eligible, and the line stays spent:
one signal per line. line_states() is the pure per-bar part; run_spent() walks the bars in order.
"""

import numpy as np

from trendline_limit import armed_lines
from trendline_support import line_value

STATUSES = ("order", "gap_below", "not_red", "no_break", "no_line", "missing_history", "contract_roll",
            "invalid_atr")


def choose_broken(broken):
    """The reported line among those bar s breaks: highest V(s); ties: later j, then later i."""
    return max(broken, key=lambda z: (z["value"], z["j"], z["i"]))


def line_states(b, s, pivots, depth_a=0.0, n=5, sessions=5, min_sep=10, min_slope=0.02):
    """(reason_or_None, a, known_pivots, lines) at the open of bar s; each armed line gets `live` (ignoring
    spending: no close below V - depth_a x A after its first departure, up to s - 1), `breaks` (live and
    close(s) < V(s) - depth_a x A) and `departure` (the first departure bar)."""
    s = int(s)
    reason, a, known, lines = armed_lines(b, s, pivots, n, sessions, min_sep, min_slope)
    if reason:
        return reason, None, 0, []
    low, close = b.low.to_numpy(), b.close.to_numpy()
    for x in lines:
        after = np.arange(x["j"] + 1, s)
        v = line_value(x["i"], x["j"], low, after)
        first = int(np.argmax(close[after] >= v + a))  # armed lines have departed, so this exists
        x["departure"] = int(after[first])
        x["live"] = not (close[after[first + 1:]] < v[first + 1:] - depth_a * a).any()
        x["breaks"] = x["live"] and bool(close[s] < x["value"] - depth_a * a)
    return None, a, len(known), lines


def spent_by(lines):
    """Lines bar s breaks (spent from then on, whatever happens to the order)."""
    return {(x["i"], x["j"]) for x in lines if x["breaks"]}


def resolve(b, t, state, spent, bid=None):
    """(status, details) for the order the primary would rest during bar t, from bar s = t - 1's line_states()
    and the lines spent before s.

    Status order: unavailability at s (window, roll, ATR), a roll between s and t, no armed line, no live line
    broken by s, s not red, the bid at t's open already at or below low(s), order."""
    t = int(t)
    s = t - 1
    opn, high, low, close = (b[c].to_numpy() for c in ("open", "high", "low", "close"))
    contract = b.contract.to_numpy()
    info = dict(s_red=bool(close[s] < opn[s]), same_contract=bool(contract[s] == contract[t]))
    reason, a, known, lines = state
    if reason:
        return reason, info
    if not info["same_contract"]:
        return "contract_roll", info
    live = [x for x in lines if x["live"] and (x["i"], x["j"]) not in spent]
    broken = [x for x in live if x["breaks"]]
    info.update(atr=a, known_pivots=known, lines_armed=len(lines), lines_live=len(live), lines_broken=len(broken))
    if not lines:
        return "no_line", info
    if not broken:
        return "no_break", info
    x = choose_broken(broken)
    info.update(line=x["value"], anchor1=x["i"], anchor2=x["j"], retests=x["retests"], slope_a=x["slope_a"],
                anchor_sep=x["j"] - x["i"], bars_since_anchor2=s - x["j"], bars_since_departure=s - x["departure"],
                depth_a=(x["value"] - close[s]) / a, range_a=(high[s] - low[s]) / a,
                opens_above=bool(opn[s] >= x["value"]))
    if not info["s_red"]:
        return "not_red", info
    entry, stop = float(low[s]), float(high[s])
    info.update(entry=entry, stop=stop)
    bid = float(opn[t]) if bid is None else float(bid)
    return ("gap_below" if bid <= entry else "order"), info


def run_spent(states):
    """Walk bars in order. states: {s: line_states(...)} for every bar s. Returns {s: those of bar s's armed lines
    that were spent before s} (only the bar's own lines, so memory stays proportional to the states)."""
    spent, before = set(), {}
    for s in sorted(states):
        lines = states[s][3]
        before[s] = frozenset(k for k in ((x["i"], x["j"]) for x in lines) if k in spent)
        spent |= spent_by(lines)
    return before


def bar_signal(b, t, pivots, bid=None, depth_a=0.0, n=5, sessions=5, min_sep=10, min_slope=0.02):
    """Status for bar t on a small frame: walks every bar before t to build the spent set (tests, examples)."""
    t = int(t)
    states = {s: line_states(b, s, pivots, depth_a, n, sessions, min_sep, min_slope) for s in range(t)}
    return resolve(b, t, states[t - 1], run_spent(states)[t - 1], bid)
