"""
Analyse trade outcome by consecutive-red-run length.

Reads the CSV written by RR_r_MFE_buy-stop-limit-entry_runband.cs
(tab-separated, NO header):
    ticket, entry_time, exit_time, mae_money, mfe_money,
    trade_profit, candle_range, red_run

Run the EA once with the band OPEN (MinRedRun=1, MaxRedRun=0) so every trade is
taken and tagged with its true run length, then point this script at the CSV.

Unlike the MT5 seq optimization (which changes the trade population each pass),
this measures every run-length bucket WITHIN a single baseline run, and reports
both raw dollars and R-multiples (profit / candle_range == profit per unit risk,
since risk = entry(h1) - stop(l1) = candle_range).

Dependencies: numpy only.

Usage:
    python python/analyze_runlength.py                      # auto-find trade_stats_rr_*.csv
    python python/analyze_runlength.py trade_stats_rr_1.0.csv
"""

import sys
import csv
from project_paths import legacy_csv_candidates
import argparse

import numpy as np

TICKET, ENTRY_T, EXIT_T, MAE, MFE, PROFIT, RANGE, RUN = range(8)


def load(path):
    profit, rng, run = [], [], []
    skipped = 0
    with open(path, newline="") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if len(row) < 8:
                skipped += 1
                continue
            try:
                p = float(row[PROFIT])
                r = float(row[RANGE])
                k = int(round(float(row[RUN])))
            except ValueError:
                skipped += 1
                continue
            profit.append(p)
            rng.append(r)
            run.append(k)
    if skipped:
        print(f"(skipped {skipped} unparsable line(s))")
    return np.array(profit), np.array(rng), np.array(run, dtype=int)


def profit_factor(p):
    wins = p[p > 0].sum()
    losses = -p[p < 0].sum()
    if losses == 0:
        return float("inf") if wins > 0 else float("nan")
    return wins / losses


def fmt_pf(p):
    pf = profit_factor(p)
    return f"{pf:.2f}" if np.isfinite(pf) else "inf"


def by_run(profit, rng, run):
    print("=" * 78)
    print("OUTCOME BY EXACT RED-RUN LENGTH  (within one baseline run)")
    print("=" * 78)
    print(f"  {'run':>4} {'n':>7} {'total$':>11} {'avg$':>9} "
          f"{'avgR':>9} {'win%':>7} {'PF':>7}")
    valid = rng > 0
    for k in sorted(np.unique(run)):
        m = (run == k)
        p = profit[m]
        vm = m & valid
        rmult = profit[vm] / rng[vm]
        avgR = rmult.mean() if len(rmult) else float("nan")
        print(f"  {k:>4} {len(p):>7} {p.sum():>11.2f} {p.mean():>9.4f} "
              f"{avgR:>9.4f} {100.0 * (p > 0).mean():>6.1f}% {fmt_pf(p):>7}")
    print()


def cap_sweep(profit, rng, run):
    """The direct test of the 'halt if run > C' idea: keep only run <= C."""
    print("=" * 78)
    print("CAP SWEEP  (keep only trades with red_run <= C  ==  'halt if run > C')")
    print("=" * 78)
    print(f"  {'MaxRun C':>9} {'trades':>7} {'total$':>11} {'avg$':>9} "
          f"{'avgR':>9} {'win%':>7} {'PF':>7} {'%kept':>7}")
    valid = rng > 0
    total_n = len(profit)
    base_total = profit.sum()
    for c in sorted(np.unique(run)):
        m = (run <= c)
        p = profit[m]
        vm = m & valid
        rmult = profit[vm] / rng[vm]
        avgR = rmult.mean() if len(rmult) else float("nan")
        print(f"  {c:>9} {len(p):>7} {p.sum():>11.2f} {p.mean():>9.4f} "
              f"{avgR:>9.4f} {100.0 * (p > 0).mean():>6.1f}% {fmt_pf(p):>7} "
              f"{100.0 * len(p) / total_n:>6.1f}%")
    print()
    print(f"  Baseline (no cap) total = {base_total:.2f}")
    print("  A cap HELPS only where total$ >= baseline AND PF is >= baseline PF.")
    print("  If capping deep runs removes net-losing trades, total$ will exceed")
    print("  the baseline at some C -> that C is your 'halt if run > C' setting.")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", help="runband trade stats CSV (tab-separated, no header)")
    ap.add_argument("--commission", type=float, default=0.0,
                    help="cost per round-turn per trade (account currency), subtracted "
                         "from every trade's profit so all stats become NET. e.g. --commission 1")
    args = ap.parse_args()

    path = args.csv
    if not path:
        candidates = legacy_csv_candidates()
        if not candidates:
            sys.exit("No CSV given and no trade_stats_rr_*.csv found here or in data/legacy.")
        path = str(candidates[0])
        print(f"(auto-selected {path})\n")

    profit, rng, run = load(path)
    if len(profit) == 0:
        sys.exit("No usable rows found in " + path)

    if args.commission != 0.0:
        gross = profit.sum()
        profit = profit - args.commission   # per-trade, so win%/PF/avgR are all net
        print(f"Commission: {args.commission:.2f}/round-turn applied to {len(profit)} trades "
              f"= {args.commission * len(profit):.2f} total drag")
        print(f"Gross profit: {gross:.2f}  ->  Net profit: {profit.sum():.2f}\n")

    print(f"Total trades: {len(profit)}   total profit: {profit.sum():.2f}   "
          f"PF: {fmt_pf(profit)}\n")
    by_run(profit, rng, run)
    cap_sweep(profit, rng, run)


if __name__ == "__main__":
    main()
