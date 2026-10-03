"""Pure minute-path and matching operations for the frozen Q9 study."""

import numpy as np
import pandas as pd


def signal_path(path, level):
    """Path columns are open/high/low/close, in minute order."""
    breaches = np.flatnonzero(path[:, 2] < level)
    assert len(breaches), "Expected a fresh breach"
    first = int(breaches[0])
    closes = path[first:, 3]
    recovered = np.flatnonzero(closes > level)
    recovery = int(first + recovered[0]) if len(recovered) else None
    signs = np.sign(closes - level)
    signs = signs[signs != 0]
    return dict(breach_minute=first,
                recovery_delay=float(recovery - first + 1) if recovery is not None else np.nan,
                first_recovery_minute=float(recovery) if recovery is not None else np.nan,
                below_closes=int((closes < level).sum()),
                below_close_share=float((closes < level).mean()),
                recrossings=int(((signs[:-1] > 0) & (signs[1:] < 0)).sum()))


def barrier_path(path, origin, scale):
    """First touches of symmetric half-scale barriers; never invent tick order."""
    assert scale > 0
    upper, lower = origin + .5 * scale, origin - .5 * scale
    up = np.flatnonzero(path[:, 1] >= upper)
    down = np.flatnonzero(path[:, 2] <= lower)
    u, d = (int(up[0]) if len(up) else None), (int(down[0]) if len(down) else None)
    if u is None and d is None:
        first = "neither"
    elif d is None or (u is not None and u < d):
        first = "up"
    elif u is None or d < u:
        first = "down"
    elif path[u, 0] >= upper:
        first = "up"
    elif path[u, 0] <= lower:
        first = "down"
    else:
        first = "ambiguous"
    result = dict(hit_up=float(u is not None), hit_down=float(d is not None),
                  hit_both=float(u is not None and d is not None),
                  hit_up_only=float(u is not None and d is None),
                  hit_down_only=float(d is not None and u is None),
                  hit_neither=float(u is None and d is None))
    result.update({f"first_{name}": float(first == name) for name in ("up", "down", "ambiguous", "neither")})
    result["first_balance"] = result["first_up"] - result["first_down"]
    return result


def endpoint_metrics(values):
    v = np.asarray(values, dtype=float)
    known = np.isfinite(v)
    v = np.where(known, v, np.nan)
    up, down = v >= .5, v <= -.5
    return dict(return_=v, absolute=np.abs(v), up=np.where(known, up, np.nan),
                down=np.where(known, down, np.nan),
                balance=np.where(known, up.astype(float) - down.astype(float), np.nan),
                tails=np.where(known, up.astype(float) + down.astype(float), np.nan),
                positive=np.where(known, v > 0, np.nan))


MATCH_COLUMNS = ("log_depth_a", "log_a", "log_range_a", "breach_minute", "clock_minutes")
CALIPERS = np.array([np.log(2), np.log(2), np.log(2), 5., 120.])


def match_pairs(a, b):
    """Greedy closest pairs, fixed calipers, same year, no replacement."""
    aa, bb = a[list(MATCH_COLUMNS)].to_numpy() / CALIPERS, b[list(MATCH_COLUMNS)].to_numpy() / CALIPERS
    assert np.isfinite(aa).all() and np.isfinite(bb).all()
    years_a, years_b = a.year.to_numpy(), b.year.to_numpy()
    candidates = []
    for i, values in enumerate(aa):
        delta = np.abs(bb - values)
        indexes = np.flatnonzero((delta <= 1 + 1e-12).all(axis=1) & (years_b == years_a[i]))
        candidates.extend((float((delta[j] ** 2).sum()), i, int(j)) for j in indexes)
    candidates.sort()
    used_a, used_b, chosen = set(), set(), []
    for cost, i, j in candidates:
        if i not in used_a and j not in used_b:
            chosen.append((i, j, cost))
            used_a.add(i)
            used_b.add(j)
    return chosen


def covariate_balance(a, b):
    rows = []
    for column in MATCH_COLUMNS:
        x, y = a[column], b[column]
        pooled = np.sqrt((x.var() + y.var()) / 2)
        delta = x.mean() - y.mean()
        rows.append(dict(covariate=column, mean_a=float(x.mean()) if len(x) else None,
                         mean_b=float(y.mean()) if len(y) else None,
                         smd=float(delta / pooled) if pooled > 0 else (0. if delta == 0 else None)))
    return rows
