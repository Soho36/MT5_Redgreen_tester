"""Q11 level map and signal classification; see docs/LEVEL_VISIT_PROTOCOL.md.

Pure functions on arrays of consecutive M30 bars. Nothing here reads outcomes.
"""

import numpy as np
import pandas as pd

GROUPS = ("support_revisit", "slice_through", "broken_contact", "not_departed_contact", "no_contact",
          "missing_history", "contract_roll", "invalid_atr")
UNAVAILABLE = GROUPS[5:]


def bar_frame(bars, rolls):
    """Add contract, session number and lagged ATR (A) to the M30 reference."""
    b = bars.sort_index().copy()
    assert b.index.is_unique and not b[["open", "high", "low", "close"]].isna().any().any()
    session = b.index.normalize()
    b["session_number"] = pd.factorize(session, sort=True)[0]
    positions = np.searchsorted(pd.to_datetime(rolls.date).to_numpy(), session.to_numpy(), side="right") - 1
    assert (positions >= 0).all(), "Roll ledger does not cover price history"
    b["contract"] = rolls.instrument_id.to_numpy()[positions]
    previous = b.close.groupby(b.contract).shift(1)
    tr = pd.concat([b.high - b.low, (b.high - previous).abs(), (b.low - previous).abs()], axis=1).max(axis=1)
    b["atr"] = tr.groupby(b.contract).transform(lambda s: s.rolling(14, min_periods=14).mean().shift(1))
    return b


def swing_lows(low, contract, n):
    """Indices i whose low is < the n lows before and <= the n lows after, same contract."""
    low, contract = np.asarray(low, float), np.asarray(contract)
    out = []
    for i in range(n, len(low) - n):
        if not (contract[i - n:i + n + 1] == contract[i]).all():
            continue
        if low[i] < low[i - n:i].min() and low[i] <= low[i + 1:i + n + 1].min():
            out.append(i)
    return np.asarray(out, dtype=int)


def merge_levels(pivots, low, d):
    """Greedy from the lowest pivot: a level holds pivots within D of its lowest member."""
    order = sorted(pivots, key=lambda i: (low[i], i))
    levels, k = [], 0
    while k < len(order):
        start = low[order[k]]
        members = [order[k]]
        k += 1
        while k < len(order) and low[order[k]] - start <= d:
            members.append(order[k])
            k += 1
        levels.append(dict(level=start, members=members, t0=max(members), first=min(members)))
    return levels


def level_state(level, t0, s, close, a, d):
    """Broken/departed using only closes of bars after t0 and before signal s."""
    after = close[t0 + 1:s]
    broken = bool(len(after) and after.min() < level - d)
    departed = bool(len(after) and after.max() >= level + a)
    return broken, departed


def classify(b, signal_index, n=5, sessions=5, pivots=None):
    """Classify one signal bar index against its window's swing-low levels.

    Returns (group, details). `pivots` may be precomputed swing_lows for speed.
    """
    s = int(signal_index)
    low, high, close = b.low.to_numpy(), b.high.to_numpy(), b.close.to_numpy()
    opn, contract, sn = b.open.to_numpy(), b.contract.to_numpy(), b.session_number.to_numpy()
    first_session = sn[s] - sessions
    if first_session < 0:
        return "missing_history", {}
    start = int(np.searchsorted(sn, first_session, side="left"))
    if not (contract[start:s + 1] == contract[s]).all():
        return "contract_roll", {}
    a = b.atr.iloc[s]
    if not np.isfinite(a) or a <= 0:
        return "invalid_atr", {}
    d = 0.5 * a
    if pivots is None:
        pivots = swing_lows(low, contract, n)
    # Known: pivot bar inside the window and confirmed (bar i+n closed) before s opens.
    known = pivots[(pivots >= start) & (pivots + n <= s - 1)]
    levels = merge_levels(known.tolist(), low, d)
    contacted = []
    for lv in levels:
        L = lv["level"]
        if low[s] <= L + d and high[s] >= L - d:
            broken, departed = level_state(L, lv["t0"], s, close, a, d)
            contacted.append(dict(lv, broken=broken, departed=departed))
    intact = [x for x in contacted if not x["broken"] and x["departed"]]
    # Amendment: the signal may undercut a level by at most D (no deep slice-through).
    revisit = [x for x in intact if low[s] >= x["level"] - d]
    if revisit:
        group, chosen = "support_revisit", revisit
    elif intact:
        group, chosen = "slice_through", intact
    elif any(x["broken"] for x in contacted):
        group, chosen = "broken_contact", [x for x in contacted if x["broken"]]
    elif contacted:
        group, chosen = "not_departed_contact", contacted
    else:
        return "no_contact", dict(atr=a, d=d, known_pivots=len(known), levels=len(levels))
    lv = min(chosen, key=lambda x: (abs(low[s] - x["level"]), -x["t0"]))
    L, t0 = lv["level"], lv["t0"]
    details = dict(atr=a, d=d, known_pivots=len(known), levels=len(levels), qualifying=len(chosen),
                   level=L, members=len(lv["members"]), t0=t0, first=lv["first"],
                   depth_a=(L - low[s]) / a, wick_reaches=bool(low[s] <= L), opens_below=bool(opn[s] < L),
                   breaks_on_signal=bool(close[s] < L - d),
                   closes_below_since=int((close[t0 + 1:s] < L).sum()), range_a=(high[s] - low[s]) / a)
    return group, details
