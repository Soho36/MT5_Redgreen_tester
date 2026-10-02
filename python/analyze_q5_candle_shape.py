"""Q5: signal-candle shape (protocol: docs/Q5_CANDLE_SHAPE_RESULTS.md).

Signal bar = bar 1 (always red). Shares of its range: body = (o-c)/r, upper = (h-o)/r,
lower = (c-l)/r. Shapes in order: doji (body <= 0.10), hammer (lower >= 0.60, upper <= 0.15),
shooting star (upper >= 0.60, lower <= 0.15), full body (body >= 0.80), other.
Rule: candidate only if net PF < 1 in both periods with >= 200 trades each.

Usage: python analyze_q5_candle_shape.py [--train CSV --recent CSV]
"""

import argparse

import numpy as np

from analyze_q3_overlap import STUDY, load, pf

MIN_N = 200
SHAPES = ("doji", "hammer", "shooting star", "full body", "other")


def classify(bars):
    o, h, l, c = (bars[:, 0, i] for i in range(4))
    rng = h - l
    assert np.all(rng > 0) and np.all(c < o), "signal bars must be red with a positive range"
    body, upper, lower = (o - c) / rng, (h - o) / rng, (c - l) / rng
    return np.select([body <= 0.10, (lower >= 0.60) & (upper <= 0.15), (upper >= 0.60) & (lower <= 0.15), body >= 0.80],
                     list(SHAPES[:4]), default="other")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=STUDY / "runband_shape_20261002_train_1.00.csv")
    ap.add_argument("--recent", default=STUDY / "runband_shape_20261002_recent_1.00.csv")
    args = ap.parse_args()
    data = {"2016-19": load(args.train), "2020-26": load(args.recent)}
    shapes = {p: classify(d[0]) for p, d in data.items()}
    print(f"  {'shape':<15}" + "".join(f"{p + ': n':>14}{'share':>7}{'net $':>8}{'PF':>7}{'avgR':>8}" for p in data))
    cands = []
    for s in SHAPES:
        line, cells = f"  {s:<15}", []
        for p, (bars, net, rr) in data.items():
            m = shapes[p] == s
            cells.append((pf(net[m]), int(m.sum())))
            line += f"{m.sum():>14}{m.mean():>7.1%}{net[m].sum():>8.0f}{pf(net[m]):>7.3f}{rr[m].mean():>+8.3f}"
        if all(v < 1 and k >= MIN_N for v, k in cells):
            cands.append(s); line += "   << PF<1 both periods"
        print(line)
    print("\nDecision rule (PF < 1 in both periods, n >= 200 each):", cands if cands else "no shape qualifies -> no filter")


if __name__ == "__main__":
    main()
