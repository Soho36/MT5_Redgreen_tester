"""Time-of-day diagnostic (protocol: docs/TIME_OF_DAY_RESULTS.md).

Checks the SnapshotBars=1 runs reproduce the baseline (Reports/rr_clean_20261001, RR 1.0)
field by field, then reports net results by session block of order placement
(signal bar open + 30 min) and of fill, per period and per year, and applies the rule:
a block is a candidate only if its net PF < 1 in both periods.

Usage: python analyze_time_of_day.py [study_dir]
"""

import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from analyze_flatten_study import COMPARE_FIELDS
from project_paths import PROJECT_ROOT
from verify_location_validation import read_rows

STUDY = PROJECT_ROOT / "Reports" / "time_of_day_20261002"
BASE = PROJECT_ROOT / "Reports" / "rr_clean_20261001"
COST = 1.05
BLOCKS = [("Asia", "01:00", "09:00"), ("Europe", "09:00", "16:00"), ("US open", "16:00", "18:00"),
          ("US midday", "18:00", "21:00"), ("US afternoon", "21:00", "23:59")]


def block(t):
    hm = t.strftime("%H:%M")
    for name, lo, hi in BLOCKS:
        if lo <= hm < hi:
            return name
    return "other"


def pf(x):
    loss = -x[x < 0].sum()
    return x[x > 0].sum() / loss if loss else float("nan")


def load(period):
    rows = read_rows(STUDY / f"runband_tod_20261002_{period}_1.00.csv")
    stats = read_rows(STUDY / f"runband_tod_20261002_{period}_1.00_stats.csv")[0]
    assert len(rows) == int(stats["trades"])
    assert abs(sum(float(r["trade_profit"]) for r in rows) - float(stats["net_profit"])) < 1e-6
    ref = read_rows(BASE / f"runband_rrclean_20261001_{period}_1p00_1.00.csv")
    # Snapshot exports write fixed decimals (-11.00000000 vs -11.0): compare numbers as numbers.
    same = lambda x, y: x == y or (x.replace(".", "", 1).lstrip("-").isdigit() and float(x) == float(y))
    assert len(ref) == len(rows) and all(all(same(a[k], b[k]) for k in COMPARE_FIELDS) for a, b in zip(ref, rows)), \
        f"{period}: snapshot run differs from the baseline"
    out = []
    for r in rows:
        placed = datetime.strptime(r["signal_time"], "%Y.%m.%d %H:%M:%S") + timedelta(minutes=30)
        filled = datetime.strptime(r["entry_time"], "%Y.%m.%d %H:%M:%S")
        net = float(r["trade_profit"]) - COST
        out.append(dict(placed=block(placed), filled=block(filled), year=filled.year, net=net,
                        r=net / (float(r["candle_range"]) * 2.0)))
    return out


def table(trades, key):
    groups = defaultdict(list)
    for t in trades:
        groups[t[key]].append(t)
    res = {}
    for name, *_ in BLOCKS + [("other",)]:
        g = groups.get(name)
        if not g:
            continue
        net = np.array([t["net"] for t in g]); r = np.array([t["r"] for t in g])
        res[name] = dict(n=len(g), net=float(net.sum()), pf=pf(net), avg_r=float(r.mean()))
    return res


def main():
    data = {p: load(p) for p in ("train", "recent")}
    print("PASS: both snapshot runs reproduce the baseline trades field by field.\n")
    for key, title in (("placed", "BY PLACEMENT BLOCK (decision basis)"), ("filled", "BY FILL BLOCK")):
        print(title)
        print(f"  {'block':<14}{'2016-19: n':>11}{'net $':>8}{'PF':>7}{'avgR':>8}  |{'2020-26: n':>11}{'net $':>8}{'PF':>7}{'avgR':>8}")
        tr, rc = table(data["train"], key), table(data["recent"], key)
        for name in tr.keys() | rc.keys():
            a, b = tr.get(name), rc.get(name)
            fa = f"{a['n']:>11}{a['net']:>8.0f}{a['pf']:>7.3f}{a['avg_r']:>+8.3f}" if a else " " * 34
            fb = f"{b['n']:>11}{b['net']:>8.0f}{b['pf']:>7.3f}{b['avg_r']:>+8.3f}" if b else ""
            print(f"  {name:<14}{fa}  |{fb}")
        print()
    both = data["train"] + data["recent"]
    moved = np.mean([t["placed"] != t["filled"] for t in both])
    print(f"Orders filled in a later block than placed: {moved:.1%}\n")
    print("NET $ BY YEAR AND PLACEMENT BLOCK")
    years = sorted({t["year"] for t in both})
    print(f"  {'block':<14}" + "".join(f"{y:>8}" for y in years))
    for name, *_ in BLOCKS:
        vals = [sum(t["net"] for t in both if t["placed"] == name and t["year"] == y) for y in years]
        print(f"  {name:<14}" + "".join(f"{v:>8.0f}" for v in vals))
    tr, rc = table(data["train"], "placed"), table(data["recent"], "placed")
    cands = [n for n in tr if n in rc and tr[n]["pf"] < 1 and rc[n]["pf"] < 1]
    print(f"\nDecision rule (net PF < 1 in both periods): {cands if cands else 'no block qualifies -> windows unchanged'}")


if __name__ == "__main__":
    STUDY = Path(sys.argv[1]) if len(sys.argv) > 1 else STUDY
    main()
