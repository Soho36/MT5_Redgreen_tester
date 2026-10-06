"""Q24 buy the reclaim of a broken swing-low level; see docs/levels/SUPPORT_RECLAIM_PROTOCOL.md.

Order for the open of bar t: bar s = t - 1 is the breakdown candidate. Levels are the frozen Q11 ones
(level_visit.merge_levels / level_state), evaluated at the open of s from bars before s: known swing lows (N = 5)
in a one-week window merged from the lowest within D; L = lowest member's low; a level is identified by that
member (its defining pivot). s breaks an intact, departed level if open(s) >= L and close(s) < L - depth_a x A
(primary depth_a = 0, S1 = 0.5). The lowest broken level is used. Buy stop at L, stop low(s), if
R = L - low(s) >= min_risk x A and the ask at t's open is below L.

Spending is stateful, as in Q21: a breakdown spends its level whether or not an order follows, recorded on every
bar in order. level_states() is the pure per-bar part; run_spent() walks the bars. Nothing here reads outcomes.
"""

import numpy as np

from level_visit import level_state, merge_levels
from trendline_support import window_start

TICK = 0.25
STATUSES = ("order", "gap_above", "min_risk", "no_break", "no_level", "missing_history", "contract_roll",
            "invalid_atr")


def level_states(b, s, pivots, depth_a=0.0, n=5, sessions=5):
    """(reason_or_None, a, known_pivots, levels) at the open of bar s. Each level: key (defining pivot), level,
    t0, members, live (intact and departed) and breaks (live, open(s) >= L, close(s) < L - depth_a x A)."""
    s = int(s)
    start = window_start(b.session_number.to_numpy(), b.contract.to_numpy(), s, sessions)
    if isinstance(start, str):
        return start, None, 0, []
    a = b.atr.iloc[s]
    if not np.isfinite(a) or a <= 0:
        return "invalid_atr", None, 0, []
    d = 0.5 * a
    low, opn, close = b.low.to_numpy(), b.open.to_numpy(), b.close.to_numpy()
    known = pivots[(pivots >= start) & (pivots + n <= s - 1)]
    levels = []
    for lv in merge_levels(known.tolist(), low, d):
        L = lv["level"]
        broken, departed = level_state(L, lv["t0"], s, close, a, d)
        live = not broken and departed
        levels.append(dict(key=int(lv["members"][0]), level=float(L), t0=int(lv["t0"]), members=len(lv["members"]),
                           live=live, breaks=bool(live and opn[s] >= L and close[s] < L - depth_a * a)))
    return None, a, len(known), levels


def spent_by(levels):
    """Levels bar s breaks (spent from then on, whatever happens to the order)."""
    return {x["key"] for x in levels if x["breaks"]}


def run_spent(states):
    """Walk bars in order. states: {s: level_states(...)}. Returns {s: those of bar s's levels spent before s}."""
    spent, before = set(), {}
    for s in sorted(states):
        levels = states[s][3]
        before[s] = frozenset(x["key"] for x in levels if x["key"] in spent)
        spent |= spent_by(levels)
    return before


def choose_level(broken):
    """The lowest broken level (the first price must reclaim); ties: later defining pivot."""
    return min(broken, key=lambda z: (z["level"], -z["key"]))


def resolve(b, t, state, spent, ask=None, min_risk=0.25):
    """(status, details) for the buy stop of bar t, from bar s = t - 1's level_states() and the levels spent
    before s. Status order: unavailability at s, a roll between s and t, no live level, no fresh break,
    R < min_risk x A, the ask at t's open at or above L, order."""
    t = int(t)
    s = t - 1
    opn, low, close = b.open.to_numpy(), b.low.to_numpy(), b.close.to_numpy()
    contract = b.contract.to_numpy()
    info = dict(s_red=bool(close[s] < opn[s]), same_contract=bool(contract[s] == contract[t]))
    reason, a, known, levels = state
    if reason:
        return reason, info
    if not info["same_contract"]:
        return "contract_roll", info
    live = [x for x in levels if x["live"]]
    broken = [x for x in live if x["breaks"] and x["key"] not in spent]
    info.update(atr=a, known_pivots=known, levels=len(levels), levels_live=len(live), levels_broken=len(broken))
    if not live:
        return "no_level", info
    if not broken:
        return "no_break", info
    x = choose_level(broken)
    risk = x["level"] - low[s]
    info.update(level=x["level"], key=x["key"], t0=x["t0"], members=x["members"], entry=x["level"],
                stop=float(low[s]), risk=float(risk), depth_a=(x["level"] - close[s]) / a, risk_a=risk / a)
    if risk < min_risk * a:
        return "min_risk", info
    ask = float(opn[t]) + TICK if ask is None else float(ask)
    return ("gap_above" if ask >= x["level"] else "order"), info


def bar_signal(b, t, pivots, ask=None, depth_a=0.0, min_risk=0.25, n=5, sessions=5):
    """Status for bar t on a small frame: walks every bar before t to build the spent set (tests, examples)."""
    t = int(t)
    states = {s: level_states(b, s, pivots, depth_a, n, sessions) for s in range(t)}
    return resolve(b, t, states[t - 1], run_spent(states)[t - 1], ask, min_risk)
