"""Q4: recent pullback vs broader move (protocol: docs/baseline/q04-context/RESULTS.md).

Recent window = bars 2..R+1, older window = bars R+2..R+L+1 (bar 1 = signal, excluded).
Direction = sign of close(newest) - open(oldest); 0 counts as up. Groups = older x recent.
Settings (R, L): (5, 20) primary, (3, 10) and (10, 40) neighbours. Rule: candidate only if
net PF < 1 in both periods with >= 200 trades each, at the primary AND a neighbour.

Usage: python analyze_q4_context.py [--train CSV --recent CSV]
"""

import argparse

import numpy as np

from analyze_q3_overlap import STUDY, load, pf

SETTINGS = ((5, 20), (3, 10), (10, 40))
PRIMARY = (5, 20)
MIN_N = 200
GROUPS = (("up", "down", "pullback in advance"), ("down", "down", "decline in decline"),
          ("up", "up", "rally continuing"), ("down", "up", "bounce in decline"))


def direction(bars, newest, oldest):
    """bars[:, i] is bar i+1; window = bars newest..oldest (1-based, newest < oldest)."""
    move = bars[:, newest - 1, 3] - bars[:, oldest - 1, 0]
    return np.where(move < 0, "down", "up")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=STUDY / "runband_shape_20261002_train_1.00.csv")
    ap.add_argument("--recent", default=STUDY / "runband_shape_20261002_recent_1.00.csv")
    args = ap.parse_args()
    data = {"2016-19": load(args.train), "2020-26": load(args.recent)}
    print("trades:", {p: len(d[1]) for p, d in data.items()}, "\n")

    bad = {}
    for r, l in SETTINGS:
        print(f"=== recent {r} bars (2..{r + 1}), older {l} bars ({r + 2}..{r + l + 1})"
              + ("   [primary]" if (r, l) == PRIMARY else ""))
        print(f"  {'group':<22}" + "".join(f"{p + ': n':>14}{'net $':>8}{'PF':>7}{'avgR':>8}" for p in data))
        for older, recent, name in GROUPS:
            line, cells = f"  {name:<22}", []
            for p, (bars, net, rr) in data.items():
                m = (direction(bars, r + 2, r + l + 1) == older) & (direction(bars, 2, r + 1) == recent)
                cells.append((pf(net[m]), int(m.sum())))
                line += f"{m.sum():>14}{net[m].sum():>8.0f}{pf(net[m]):>7.3f}{rr[m].mean():>+8.3f}"
            bad[((r, l), name)] = all(v < 1 and k >= MIN_N for v, k in cells)
            print(line + ("   << PF<1 both periods" if bad[((r, l), name)] else ""))
        print()
    cands = [name for _, _, name in GROUPS
             if bad[(PRIMARY, name)] and any(bad[(s, name)] for s in SETTINGS if s != PRIMARY)]
    print("Decision rule (PF < 1 both periods, n >= 200, primary + a neighbour):",
          cands if cands else "no group qualifies -> no filter")


if __name__ == "__main__":
    main()
