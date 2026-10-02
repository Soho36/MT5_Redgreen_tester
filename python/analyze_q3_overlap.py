"""Q3: overlapping vs steadily progressing bars before the signal (protocol: docs/Q3_OVERLAP_RESULTS.md).

Reads two 51-bar snapshot runs (bar 1 = signal, columns o1 h1 l1 c1 ...). For the N bars before
the signal (bars 2..N+1, signal excluded), N in {5, 10, 20}:
  OVL_N  = mean over neighbouring pairs of overlap / union  (0 = staircase, 1 = identical bars;
           union == 0 counts as 1)
  dir    = down if close[2] - open[N+1] < 0 else up
  groups = OVL terciles (cut points from the TRAIN trades only) x direction
Reports net PF / net $ / avg net R per group and period, Spearman(OVL_N, trend_eff), and the
pre-set rule: candidate only if net PF < 1 in both periods, >= 200 trades each, also at a
neighbouring N.

Usage: python analyze_q3_overlap.py [--train CSV --recent CSV]
"""

import argparse
from pathlib import Path

import numpy as np

from project_paths import PROJECT_ROOT
from verify_location_validation import read_rows

STUDY = PROJECT_ROOT / "Reports" / "entry_shape_20261002"
COST = 1.05
NS = (5, 10, 20)
MIN_N = 200


def load(path):
    rows = read_rows(Path(path))
    bars = np.array([[[float(r[f"{k}{b}"]) for k in "ohlc"] for b in range(1, 52)] for r in rows])
    net = np.array([float(r["trade_profit"]) for r in rows]) - COST
    risk = np.array([float(r["candle_range"]) for r in rows]) * 2.0
    return bars, net, net / risk


def features(bars, n):
    o, h, l, c = (bars[:, 1:n + 1, i] for i in range(4))      # bars 2..N+1, newest first
    hi = np.minimum(h[:, :-1], h[:, 1:]); lo = np.maximum(l[:, :-1], l[:, 1:])
    union = np.maximum(h[:, :-1], h[:, 1:]) - np.minimum(l[:, :-1], l[:, 1:])
    overlap = np.maximum(0.0, hi - lo)
    ratio = np.where(union > 0, overlap / np.where(union > 0, union, 1), 1.0)
    ovl = ratio.mean(axis=1)
    move = c[:, 0] - o[:, -1]
    trend_eff = move / np.maximum((h - l).sum(axis=1), 1e-9)
    return ovl, np.where(move < 0, "down", "up"), trend_eff


def pf(x):
    loss = -x[x < 0].sum()
    return x[x > 0].sum() / loss if loss else float("nan")


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=STUDY / "runband_shape_20261002_train_1.00.csv")
    ap.add_argument("--recent", default=STUDY / "runband_shape_20261002_recent_1.00.csv")
    args = ap.parse_args()
    data = {"2016-19": load(args.train), "2020-26": load(args.recent)}
    print("trades:", {p: len(d[1]) for p, d in data.items()}, "\n")

    flagged = {}
    for n in NS:
        feats = {p: features(d[0], n) for p, d in data.items()}
        cuts = np.quantile(feats["2016-19"][0], [1 / 3, 2 / 3])
        print(f"=== N = {n}   overlap tercile cuts (from 2016-19): {cuts[0]:.3f} / {cuts[1]:.3f}   "
              f"Spearman(OVL, trend_eff): " + ", ".join(f"{p} {spearman(f[0], f[2]):+.2f}" for p, f in feats.items()))
        print(f"  {'group':<14}" + "".join(f"{p + ': n':>14}{'net $':>8}{'PF':>7}{'avgR':>8}" for p in data))
        for t_i, t_name in enumerate(("low overlap", "mid overlap", "high overlap")):
            for d_name in ("down", "up"):
                line, pfs = f"  {t_name[:4] + ' ' + d_name:<14}", []
                for p, (bars, net, r) in data.items():
                    ovl, direction, _ = feats[p]
                    tert = np.digitize(ovl, cuts)
                    m = (tert == t_i) & (direction == d_name)
                    pfs.append((pf(net[m]), m.sum()))
                    line += f"{m.sum():>14}{net[m].sum():>8.0f}{pf(net[m]):>7.3f}{r[m].mean():>+8.3f}"
                bad = all(v < 1 and k >= MIN_N for v, k in pfs)
                flagged[(n, t_name, d_name)] = bad
                print(line + ("   << PF<1 both periods" if bad else ""))
        print()
    cands = [k for k, v in flagged.items() if v and any(flagged.get((m, k[1], k[2])) for m in NS if m != k[0])]
    print("Decision rule (PF < 1 in both periods, n >= 200, also at another N):",
          cands if cands else "no group qualifies -> no filter")


if __name__ == "__main__":
    main()
