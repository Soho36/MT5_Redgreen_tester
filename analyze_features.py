"""
Analyse trade outcome by pre-entry BAR features (no indicators, bars only).

Reads the CSV written by RR_r_MFE_buy-stop-entry_features.cs (tab-separated,
WITH header): the usual trade columns plus signal_time, period_sec and the raw
OHLC of the last N bars at order placement (o1 h1 l1 c1 = signal red candle,
o2 h2 l2 c2 = the bar before it, ...).

Every feature is judged ON ITS OWN - features are never combined. For each one
the trades are split into equal-count buckets and each bucket gets n, total$,
avgR, win%, PF, plus PF in the first and second half of the history. What we
are looking for (the lesson from the red-run cap): a bucket that LOSES MONEY
(PF < 1) in BOTH halves, preferably at the edge of the range so excluding it
is a simple threshold rule in the EA.

R-multiple = net profit / (candle_range * point_value): exactly the trade's
result in units of its own risk (risk = h1 - l1). Scale-free, so bet sizing
from bigger candles cannot fake an edge.

Dependencies: numpy only.

Usage:
    python analyze_features.py                          # auto-find features_*.csv
    python analyze_features.py features_nowin_1.00.csv --commission 1
    python analyze_features.py --feature room --feature location
    python analyze_features.py --list                   # describe the features
"""

import os
import sys
import csv
import glob
import argparse

import numpy as np


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def _encoding(path):
    with open(path, "rb") as fh:
        head = fh.read(2)
    return "utf-16" if head in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"


def _to_dt(s):
    # MT5 "2010.06.10 06:23:40" -> numpy datetime64
    return np.datetime64(s.strip().replace(".", "-", 2).replace(" ", "T"), "s")


def load(path):
    with open(path, newline="", encoding=_encoding(path)) as fh:
        rows = list(csv.reader(fh, delimiter="\t"))
    if not rows or rows[0][0] != "ticket":
        sys.exit(f"{path}: no header row - is this a *_features EA export?")

    header, rows = rows[0], rows[1:]
    col = {name: i for i, name in enumerate(header)}
    nbars = max(int(name[1:]) for name in header if name[:1] == "o" and name[1:].isdigit())

    def num(r, name):
        v = r[col[name]] if col[name] < len(r) else ""
        return float(v) if v.strip() else np.nan

    profit, crange, entry, signal, period = [], [], [], [], []
    ohlc = []
    skipped = 0
    for r in rows:
        if len(r) < col["period_sec"] + 1:
            skipped += 1
            continue
        try:
            profit.append(float(r[col["trade_profit"]]))
            crange.append(float(r[col["candle_range"]]))
            entry.append(_to_dt(r[col["entry_time"]]))
            signal.append(_to_dt(r[col["signal_time"]]))
            period.append(float(r[col["period_sec"]]))
            ohlc.append([[num(r, f"{k}{b}") for k in "ohlc"] for b in range(1, nbars + 1)])
        except (ValueError, KeyError):
            skipped += 1
            for lst in (profit, crange, entry, signal, period):
                del lst[len(ohlc):]
            continue
    if skipped:
        print(f"(skipped {skipped} unparsable line(s))")

    bars = np.array(ohlc, dtype=float)            # shape (trades, nbars, 4)
    return {
        "profit": np.array(profit),
        "crange": np.array(crange),
        "entry": np.array(entry, dtype="datetime64[s]"),
        "signal": np.array(signal, dtype="datetime64[s]"),
        "period": np.array(period),
        "O": bars[:, :, 0], "H": bars[:, :, 1], "L": bars[:, :, 2], "C": bars[:, :, 3],
        "nbars": nbars,
    }


# --------------------------------------------------------------------------
# Features. Column 0 = bar 1 = the signal red candle, column 1 = bar 2, ...
# Each returns (values, labels): labels=None -> numeric (quantile buckets),
# labels=dict -> categorical (one bucket per category).
# --------------------------------------------------------------------------

def f_red_run(d, lb):
    red = d["C"] < d["O"]
    run = np.cumprod(red, axis=1).sum(axis=1)
    run = np.minimum(run, 7)
    return run.astype(float), {k: (str(k) if k < 7 else "7+") for k in range(1, 8)}


def f_room(d, lb):
    hh_prev = np.max(d["H"][:, 1:lb + 1], axis=1)
    return (hh_prev - d["H"][:, 0]) / d["crange"], None


def f_location(d, lb):
    hh = np.max(d["H"][:, :lb], axis=1)
    ll = np.min(d["L"][:, :lb], axis=1)
    return (d["C"][:, 0] - ll) / (hh - ll), None


def f_sweep(d, lb):
    l1 = d["L"][:, 0]
    low5 = np.min(d["L"][:, 1:6], axis=1)
    low_lb = np.min(d["L"][:, 1:lb + 1], axis=1)
    v = np.where(l1 < low_lb, 2.0, np.where(l1 < low5, 1.0, 0.0))
    v[np.isnan(low_lb)] = np.nan
    return v, {0: "no new low", 1: "new 5-bar low", 2: f"new {lb}-bar low"}


def f_rel_size(d, lb):
    rng = d["H"] - d["L"]
    return rng[:, 0] / np.mean(rng[:, 1:lb + 1], axis=1), None


def f_close_loc(d, lb):
    return (d["C"][:, 0] - d["L"][:, 0]) / d["crange"], None


def f_vol_regime(d, lb):
    rng = d["H"] - d["L"]
    return np.mean(rng[:, :5], axis=1) / np.mean(rng, axis=1), None


def f_bar2(d, lb):
    h1, l1 = d["H"][:, 0], d["L"][:, 0]
    h2, l2 = d["H"][:, 1], d["L"][:, 1]
    higher_h, lower_l = h1 > h2, l1 < l2
    v = np.select([~higher_h & ~lower_l, ~higher_h & lower_l, higher_h & ~lower_l],
                  [0.0, 1.0, 2.0], default=3.0)
    v[np.isnan(h2)] = np.nan
    return v, {0: "inside", 1: "lower (LL, no HH)", 2: "higher (HH, no LL)", 3: "outside"}


def f_trend_eff(d, lb):
    k = min(10, d["nbars"] - 1)
    rng = d["H"] - d["L"]
    return (d["C"][:, 0] - d["C"][:, k]) / np.sum(rng[:, :k], axis=1), None


def f_fill_delay(d, lb):
    # bars that passed after the signal candle closed before the stop was hit
    dt = (d["entry"] - d["signal"]).astype(float)
    bars = np.floor(dt / d["period"]) - 1
    return np.clip(bars, 0, 3), {0: "same bar", 1: "1 bar later", 2: "2 bars later", 3: "3+ later"}


FEATURES = {
    "red_run":    (f_red_run,    "SANITY CHECK - consecutive reds ending at the signal; "
                                 "known result: 6-7 lose. If this doesn't show it, the pipeline is broken."),
    "room":       (f_room,       "Overhead: highest high of the previous LB bars minus entry, in R. "
                                 "<0 = nothing above entry; 0..RR = a recent high sits before the target."),
    "location":   (f_location,   "Where the signal closes inside the LB-bar high-low channel. "
                                 "0 = at the bottom (falling knife), 1 = at the top (shallow pullback)."),
    "sweep":      (f_sweep,      "Did the signal candle take out a recent low? (failed-breakdown setup)"),
    "rel_size":   (f_rel_size,   "Signal range / average range of the previous LB bars. "
                                 "<1 = stop tighter than normal noise, >1 = big candle, far target."),
    "close_loc":  (f_close_loc,  "Signal close position in its own range. 0 = closed on the low, "
                                 "higher = buyers pushed it back up (lower wick)."),
    "vol_regime": (f_vol_regime, "Avg range of last 5 bars / avg range of all logged bars. "
                                 "<1 = quiet/contracting, >1 = expanding."),
    "bar2":       (f_bar2,       "Signal candle vs the bar before it: inside / lower / higher / outside."),
    "trend_eff":  (f_trend_eff,  "Net close-to-close move over the last 10 bars / sum of their ranges. "
                                 "-1 = straight down, 0 = chop, +1 = straight up."),
    "fill_delay": (f_fill_delay, "How many bars after the signal the buy stop filled. "
                                 "Answers: should the order expire after k bars?"),
}

# Categories with no natural order: excluding any one of them is already a simple rule.
NOMINAL = {"bar2"}


# --------------------------------------------------------------------------
# Stats
# --------------------------------------------------------------------------

def profit_factor(p):
    wins = p[p > 0].sum()
    losses = -p[p < 0].sum()
    if losses == 0:
        return float("inf") if wins > 0 else float("nan")
    return wins / losses


def fmt_pf(pf):
    return f"{pf:.2f}" if np.isfinite(pf) else "  -"


def buckets(values, labels, nb):
    """-> list of (label, mask), in feature order"""
    ok = np.isfinite(values)
    if labels is not None:
        return [(labels[c], ok & (values == c)) for c in sorted(labels) if np.any(values[ok] == c)]

    v = values[ok]
    edges = np.unique(np.quantile(v, np.linspace(0, 1, nb + 1)))
    idx = np.full(len(values), -1)
    idx[ok] = np.clip(np.searchsorted(edges, v, side="right") - 1, 0, len(edges) - 2)
    return [(f"{edges[b]:+.2f} .. {edges[b + 1]:+.2f}", idx == b) for b in range(len(edges) - 1)]


def report(name, desc, values, labels, d, nb, halves, base):
    p, R = d["net"], d["R"]
    first, second = halves
    print("=" * 96)
    print(f"{name.upper()}  -  {desc}")
    print("=" * 96)
    missing = int(np.sum(~np.isfinite(values)))
    if missing:
        print(f"  ({missing} trades without enough bars - excluded)")
    print(f"  {'bucket':<22} {'n':>6} {'total$':>10} {'avgR':>7} {'z':>6} {'win%':>6} "
          f"{'PF':>6} | {'PF 1st':>6} {'PF 2nd':>6} |")
    sd_R = np.std(R)
    rows = []
    for label, m in buckets(values, labels, nb):
        n = int(m.sum())
        if n == 0:
            continue
        pb = p[m]
        avgR = R[m].mean()
        z = (avgR - base["avgR"]) / (sd_R / np.sqrt(n))
        pf, pf1, pf2 = profit_factor(pb), profit_factor(p[m & first]), profit_factor(p[m & second])
        # stable loser: loses money overall AND in each half, AND is worse than average
        stable = pf < 1 and pf1 < 1 and pf2 < 1 and z < 0
        flag = "<< LOSER both halves" if stable else ("<  loses overall only" if pf < 1 else "")
        rows.append([name, label, n, pb.sum(), pf, pf1, pf2, z, stable])
        print(f"  {label:<22} {n:>6} {pb.sum():>10.2f} {avgR:>+7.3f} {z:>+6.1f} "
              f"{100 * (pb > 0).mean():>5.1f}% {fmt_pf(pf):>6} | {fmt_pf(pf1):>6} {fmt_pf(pf2):>6} | {flag}")
    print()

    # How would excluding it look as an EA rule? A bucket is a TAIL when it and
    # every bucket between it and one end of the range are stable losers -> one
    # threshold removes them all (e.g. red_run 6 and 7+ -> "MaxRedRun = 5").
    flags = [r[8] for r in rows]
    losers = []
    for i, r in enumerate(rows):
        if not r[8]:
            continue
        if name in NOMINAL:
            rule = "category -> skip it"
        elif all(flags[:i + 1]) or all(flags[i:]):
            rule = "tail -> simple threshold"
        else:
            rule = "middle -> suspicious"
        losers.append(tuple(r[:8]) + (rule,))
    return losers


def summary(all_losers, base, n_total):
    print("=" * 96)
    print("SUMMARY - worse-than-average buckets that lose money in BOTH halves (candidates to EXCLUDE)")
    print("=" * 96)
    print(f"  Baseline: {n_total} trades, total {base['total']:.2f}, PF {fmt_pf(base['pf'])} "
          f"(1st {fmt_pf(base['pf1'])} / 2nd {fmt_pf(base['pf2'])}), avgR {base['avgR']:+.3f}")
    if not all_losers:
        print("  None. No single bar feature isolates a stable losing group.")
        print()
        return
    print(f"  {'feature':<11} {'bucket':<22} {'n':>6} {'total$':>10} {'PF':>6} "
          f"{'PF 1st':>6} {'PF 2nd':>6} {'z':>6}  rule")
    for f, label, n, tot, pf, pf1, pf2, z, rule in sorted(all_losers, key=lambda x: x[7]):
        print(f"  {f:<11} {label:<22} {n:>6} {tot:>10.2f} {fmt_pf(pf):>6} "
              f"{fmt_pf(pf1):>6} {fmt_pf(pf2):>6} {z:>+6.1f}  {rule}")
    print()
    print("  Sorted by z (most clearly worse than average first). Excluding a bucket")
    print("  would ADD -total$ to the result (before any population effect in MT5).")
    print("  |z| < 2 is within chance for this many buckets. |z| >= 3 + a sensible")
    print("  mechanism + a tail/category rule = worth building as an EA filter and re-testing.")
    print()


# --------------------------------------------------------------------------

def find_csv():
    here = [p for p in glob.glob("features_*.csv") if not p.endswith("_stats.csv")]
    common = os.path.join(os.environ.get("APPDATA", ""), "MetaQuotes", "Terminal", "Common", "Files")
    there = [p for p in glob.glob(os.path.join(common, "features_*.csv")) if not p.endswith("_stats.csv")]
    candidates = here or there
    if not candidates:
        sys.exit("No CSV given and no features_*.csv found here or in MT5 Common\\Files.")
    return max(candidates, key=os.path.getmtime)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", help="features CSV from the _features EA")
    ap.add_argument("--feature", action="append", choices=list(FEATURES),
                    help="analyse only this feature (repeatable). Default: all")
    ap.add_argument("--list", action="store_true", help="describe the features and exit")
    ap.add_argument("--buckets", type=int, default=5, help="equal-count buckets per numeric feature")
    ap.add_argument("--lookback", type=int, default=20, help="LB: bars of context for room/location/sweep/rel_size")
    ap.add_argument("--commission", type=float, default=0.0,
                    help="cost per round-turn per trade, subtracted from every trade (stats become NET)")
    ap.add_argument("--point-value", type=float, default=2.0,
                    help="$ per 1.0 price move per lot (MNQ = 2.0), used for R-multiples")
    ap.add_argument("--split-date", help="YYYY-MM-DD boundary between the halves (default: median entry)")
    args = ap.parse_args()

    if args.list:
        for name, (_, desc) in FEATURES.items():
            print(f"{name:<11} {desc}")
        return

    path = args.csv or find_csv()
    print(f"File: {path}\n")
    d = load(path)
    n = len(d["profit"])
    if n == 0:
        sys.exit("No usable rows.")

    lb = min(args.lookback, d["nbars"] - 1)
    if lb != args.lookback:
        print(f"(lookback reduced to {lb}: only {d['nbars']} bars logged per trade)")

    d["net"] = d["profit"] - args.commission
    d["R"] = d["net"] / (d["crange"] * args.point_value)

    if args.split_date:
        split = np.datetime64(args.split_date, "s")
    else:
        split = np.sort(d["entry"])[n // 2]
    first = d["entry"] < split
    halves = (first, ~first)

    p = d["net"]
    base = {"total": p.sum(), "pf": profit_factor(p), "avgR": d["R"].mean(),
            "pf1": profit_factor(p[first]), "pf2": profit_factor(p[~first])}

    gross_R = d["profit"] / (d["crange"] * args.point_value)
    losers_R = gross_R[gross_R < 0]
    print(f"Trades: {n}   {str(d['entry'].min())[:10]} .. {str(d['entry'].max())[:10]}   "
          f"halves split at {str(split)[:10]}")
    if args.commission:
        print(f"Commission {args.commission:.2f}/trade: gross {d['profit'].sum():.2f} -> net {p.sum():.2f}")
    print(f"Total {base['total']:.2f}   PF {fmt_pf(base['pf'])}   avgR {base['avgR']:+.3f}")
    print(f"Point-value check: median losing trade = {np.median(losers_R):+.2f}R "
          f"(should be about -1.00; if not, fix --point-value)\n")

    all_losers = []
    for name in args.feature or FEATURES:
        fn, desc = FEATURES[name]
        values, labels = fn(d, lb)
        all_losers += report(name, desc.replace("LB", str(lb)), values, labels, d,
                             args.buckets, halves, base)
    summary(all_losers, base, n)


if __name__ == "__main__":
    main()
