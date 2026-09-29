"""Train/test check of MaxRedRun: select on 2015-2019, then judge the frozen value on 2020-2026.

Selection rule (fixed before the runs, see RESEARCH_RESULTS.md): winner = highest
gross PF on the training runs; a tie within 0.005 goes to the larger MaxRedRun.
MaxRedRun = 0 means the filter is off.

Usage: python evaluate_maxredrun_train.py Reports/maxredrun_train_20260929
"""

import sys
from pathlib import Path

import numpy as np

from verify_location_validation import read_rows

COMMISSION = 1.0
POINT_VALUE = 2.0
TIE = 0.005


def pf(x):
    loss = -x[x < 0].sum()
    return x[x > 0].sum() / loss if loss else float("nan")


def balance_dd(x):
    eq = np.cumsum(x)
    return float(np.max(np.maximum.accumulate(np.r_[0, eq])[1:] - eq))


def load(directory, tag):
    rows = read_rows(directory / f"runband_{tag}_1.00.csv")
    stats = read_rows(directory / f"runband_{tag}_1.00_stats.csv")[0]
    gross = np.array([float(r["trade_profit"]) for r in rows])
    assert len(rows) == int(stats["trades"]), (tag, "trade count mismatch")
    assert abs(gross.sum() - float(stats["net_profit"])) < 1e-6, (tag, "PnL mismatch")
    cap = int(stats["max_red_run"])
    assert all(cap == 0 or int(r["red_run"]) <= cap for r in rows), (tag, "filter violated")
    risk = np.array([float(r["candle_range"]) for r in rows]) * POINT_VALUE
    net = gross - COMMISSION
    return dict(tag=tag, cap=cap, trades=len(rows), gross=gross.sum(), gross_pf=pf(gross),
                gross_R=float(np.mean(gross / risk)), net=net.sum(), net_pf=pf(net),
                net_dd=balance_dd(net), first=rows[0]["entry_time"][:10], last=rows[-1]["entry_time"][:10])


def table(title, results):
    print(title)
    print(f"  {'MaxRedRun':>9} {'trades':>7} {'gross$':>9} {'grossPF':>8} {'grossR':>8} "
          f"{'net$':>9} {'netPF':>6} {'netDD':>7}   first .. last entry")
    for r in results:
        cap = "off" if r["cap"] == 0 else r["cap"]
        print(f"  {cap:>9} {r['trades']:>7} {r['gross']:>9.0f} {r['gross_pf']:>8.3f} {r['gross_R']:>+8.3f} "
              f"{r['net']:>9.0f} {r['net_pf']:>6.3f} {r['net_dd']:>7.0f}   {r['first']} .. {r['last']}")
    print()


def main(directory):
    directory = Path(directory)
    train = [load(directory, f"train1519_run{k}") for k in range(8)]
    table("TRAIN 2015-2019", train)

    best = max(r["gross_pf"] for r in train)
    tied = [r for r in train if r["gross_pf"] >= best - TIE]
    # cap 0 = no filter = least restrictive of all
    winner = max(tied, key=lambda r: 99 if r["cap"] == 0 else r["cap"])
    print(f"Selection: best gross PF {best:.3f}; within {TIE}: "
          f"{[('off' if r['cap'] == 0 else r['cap']) for r in tied]} -> winner MaxRedRun = "
          f"{'off' if winner['cap'] == 0 else winner['cap']}\n")

    test = [load(directory, t) for t in ("test2026_off", f"test2026_run{winner['cap']}")
            if (directory / f"runband_{t}_1.00.csv").exists()]
    if test:
        table("TEST 2020-2026 (frozen winner vs off)", test)


if __name__ == "__main__":
    main(sys.argv[1])
