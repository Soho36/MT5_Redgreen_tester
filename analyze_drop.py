"""
Inspect the relationship between the pre-entry % drop and trade outcome.

Reads the EA's trade-stats CSV (tab-separated, NO header) with columns:
    ticket, entry_time, exit_time, mae_money, mfe_money,
    trade_profit, candle_range, drop_percent

Run the EA once with the drop filter effectively OFF (MinDropPercent=0,
MaxDropPercent=0) so no trades are pre-filtered, then point this script at
the resulting CSV.

Dependencies: numpy only (matplotlib optional, for --plot).

Usage:
    python analyze_drop.py                       # auto-find trade_stats_rr_*.csv
    python analyze_drop.py trade_stats_rr_1.0.csv
    python analyze_drop.py path\\to\\file.csv --plot
"""

import sys
import csv
import glob
import argparse

import numpy as np

# Column order as written by SaveTradeStats() in the EA
TICKET, ENTRY_T, EXIT_T, MAE, MFE, PROFIT, RANGE, DROP = range(8)


def load(path):
    """Return (profit, drop, candle_range) as float numpy arrays."""
    profit, drop, rng = [], [], []
    skipped = 0
    with open(path, newline="") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if len(row) < 8:
                skipped += 1
                continue
            try:
                p = float(row[PROFIT])
                d = float(row[DROP])
                r = float(row[RANGE])
            except ValueError:
                # header row or stray line
                skipped += 1
                continue
            profit.append(p)
            drop.append(d)
            rng.append(r)
    if skipped:
        print(f"(skipped {skipped} unparsable line(s))")
    return np.array(profit), np.array(drop), np.array(rng)


def profit_factor(profits):
    wins = profits[profits > 0].sum()
    losses = -profits[profits < 0].sum()
    if losses == 0:
        return float("inf") if wins > 0 else float("nan")
    return wins / losses


def summarize(profits):
    n = len(profits)
    if n == 0:
        return dict(n=0, total=0.0, avg=0.0, winrate=0.0, pf=float("nan"))
    profits = np.asarray(profits, dtype=float)
    return dict(
        n=n,
        total=float(profits.sum()),
        avg=float(profits.mean()),
        winrate=100.0 * float((profits > 0).mean()),
        pf=profit_factor(profits),
    )


def corr(a, b):
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def spearman(a, b):
    if len(a) < 2:
        return float("nan")
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return corr(ra.astype(float), rb.astype(float))


def print_overall(profit, drop):
    s = summarize(profit)
    print("=" * 70)
    print("OVERALL (all trades, filter off)")
    print("=" * 70)
    print(f"  Trades       : {s['n']}")
    print(f"  Total profit : {s['total']:.2f}")
    print(f"  Avg / trade  : {s['avg']:.4f}")
    print(f"  Win rate     : {s['winrate']:.2f}%")
    print(f"  Profit factor: {s['pf']:.3f}")
    print(f"  drop% range  : {drop.min():.3f} .. {drop.max():.3f}")
    print()


def print_correlation(profit, drop):
    win = (profit > 0).astype(float)
    print("=" * 70)
    print("CORRELATION: drop_percent vs outcome")
    print("=" * 70)
    print(f"  Pearson  (drop% vs profit) : {corr(drop, profit):+.4f}")
    print(f"  Spearman (drop% vs profit) : {spearman(drop, profit):+.4f}   (rank-based, robust)")
    print(f"  Pearson  (drop% vs is_win) : {corr(drop, win):+.4f}")
    print("  Positive => bigger drop tends to mean a better / more-often-winning trade.")
    print()


def print_deciles(profit, drop, groups=10):
    """Split trades into equal-count buckets by drop%, show outcome per bucket."""
    print("=" * 70)
    print(f"BUCKET TABLE  (trades sorted by drop%, split into {groups} equal groups)")
    print("=" * 70)
    print(f"  {'bkt':>3} {'drop% range':>21} {'n':>6} {'avg':>9} "
          f"{'total':>10} {'win%':>7} {'PF':>7}")
    order = np.argsort(drop)
    d_sorted = drop[order]
    p_sorted = profit[order]
    n = len(profit)
    if n < groups:
        groups = n
    edges = np.linspace(0, n, groups + 1).astype(int)
    for b in range(groups):
        lo_i, hi_i = edges[b], edges[b + 1]
        if hi_i <= lo_i:
            continue
        seg_p = p_sorted[lo_i:hi_i]
        seg_d = d_sorted[lo_i:hi_i]
        s = summarize(seg_p)
        pf = f"{s['pf']:.2f}" if np.isfinite(s["pf"]) else "inf"
        print(f"  {b:>3} {seg_d.min():>9.3f}..{seg_d.max():<9.3f} {s['n']:>6} "
              f"{s['avg']:>9.4f} {s['total']:>10.2f} {s['winrate']:>6.1f}% {pf:>7}")
    print()


def print_edge_vs_scaling(profit, drop, rng, groups=10):
    """
    Decisive test: is the extremes' outperformance a real EDGE or just bigger BETS?

    profit_per_range = trade_profit / candle_range  ~= profit in R-multiples
    (candle_range is the point-distance of the entry candle = the risk unit).

    If avg R-multiple ALSO rises at the extreme drop buckets, the edge is real.
    If it flattens while raw avg profit rises, the extremes were only bigger bets.
    """
    valid = rng > 0
    p, d, r = profit[valid], drop[valid], rng[valid]
    rmult = p / r
    print("=" * 70)
    print("EDGE vs SCALING  (profit / candle_range = profit in R-multiples)")
    print("=" * 70)
    print(f"  dropped {np.sum(~valid)} row(s) with candle_range <= 0")
    print(f"  Overall avg R-multiple: {rmult.mean():+.4f}")
    print(f"  Corr(drop%, R-multiple): pearson {corr(d, rmult):+.4f}  "
          f"spearman {spearman(d, rmult):+.4f}")
    print()
    print(f"  {'bkt':>3} {'drop% range':>21} {'n':>6} "
          f"{'avg$':>9} {'avgR':>9} {'win%':>7}")
    order = np.argsort(d)
    d_s, p_s, r_s = d[order], p[order], r[order]
    rm_s = rmult[order]
    n = len(p)
    edges = np.linspace(0, n, groups + 1).astype(int)
    for b in range(groups):
        lo_i, hi_i = edges[b], edges[b + 1]
        if hi_i <= lo_i:
            continue
        seg_p = p_s[lo_i:hi_i]
        seg_rm = rm_s[lo_i:hi_i]
        seg_d = d_s[lo_i:hi_i]
        print(f"  {b:>3} {seg_d.min():>9.3f}..{seg_d.max():<9.3f} {len(seg_p):>6} "
              f"{seg_p.mean():>9.4f} {seg_rm.mean():>9.4f} "
              f"{100.0 * (seg_p > 0).mean():>6.1f}%")
    print()
    print("  Compare avg$ vs avgR across buckets:")
    print("   - both rise at the extremes  -> real edge")
    print("   - avg$ rises but avgR is flat -> extremes were just bigger bets")
    print()


def print_threshold_sweep(profit, drop, steps=20):
    """What if MinDropPercent = T ? Keep only trades with drop% >= T."""
    print("=" * 70)
    print("THRESHOLD SWEEP  (keep only trades with drop% >= T)")
    print("=" * 70)
    print(f"  {'MinDrop%':>9} {'trades':>7} {'total':>10} {'avg':>9} "
          f"{'win%':>7} {'PF':>7} {'%kept':>7}")
    lo = max(0.0, float(drop.min()))
    hi = float(np.quantile(drop, 0.98))
    if hi <= lo:
        hi = float(drop.max())
    total_n = len(profit)
    for t in np.linspace(lo, hi, steps):
        sub = profit[drop >= t]
        s = summarize(sub)
        if s["n"] == 0:
            continue
        pf = f"{s['pf']:.2f}" if np.isfinite(s["pf"]) else "inf"
        print(f"  {t:>9.3f} {s['n']:>7} {s['total']:>10.2f} {s['avg']:>9.4f} "
              f"{s['winrate']:>6.1f}% {pf:>7} {100.0 * s['n'] / total_n:>6.1f}%")
    print()
    print("  Read this as: the edge is real only if avg/trade and PF climb as")
    print("  MinDrop% rises. If they stay flat, drop% is not selecting the edge.")
    print()


def maybe_plot(profit, drop, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib not installed - skipping plots)")
        return

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].scatter(drop, profit, s=8, alpha=0.3)
    axes[0].axhline(0, color="k", lw=0.8)
    axes[0].axvline(0, color="k", lw=0.8)
    axes[0].set_xlabel("drop_percent")
    axes[0].set_ylabel("trade_profit")
    axes[0].set_title("Per-trade: drop% vs profit")

    ts = np.linspace(max(0.0, float(drop.min())), float(np.quantile(drop, 0.98)), 40)
    avgs = [profit[drop >= t].mean() if (drop >= t).any() else np.nan for t in ts]
    axes[1].plot(ts, avgs, marker="o", ms=3)
    axes[1].axhline(profit.mean(), color="r", ls="--", label="baseline avg (no filter)")
    axes[1].set_xlabel("MinDropPercent threshold")
    axes[1].set_ylabel("avg profit / trade (kept trades)")
    axes[1].set_title("Avg profit vs drop threshold")
    axes[1].legend()

    out = path.rsplit(".", 1)[0] + "_dropanalysis.png"
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(f"Saved plot -> {out}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", help="trade stats CSV (tab-separated, no header)")
    ap.add_argument("--plot", action="store_true", help="also write a PNG of the relationship")
    args = ap.parse_args()

    path = args.csv
    if not path:
        candidates = sorted(glob.glob("trade_stats_rr_*.csv"))
        if not candidates:
            sys.exit("No CSV given and no trade_stats_rr_*.csv found in this folder.")
        path = candidates[0]
        print(f"(auto-selected {path})\n")

    profit, drop, rng = load(path)
    if len(profit) == 0:
        sys.exit("No usable rows found in " + path)

    print_overall(profit, drop)
    print_correlation(profit, drop)
    print_deciles(profit, drop)
    print_edge_vs_scaling(profit, drop, rng)
    print_threshold_sweep(profit, drop)
    if args.plot:
        maybe_plot(profit, drop, path)


if __name__ == "__main__":
    main()
