"""Analyze the clean-data MaxRedRun train/test (protocol: docs/MAXREDRUN_CLEAN_RESULTS.md).

Checks each CSV against its MT5 stats (incl. the max_red_run flag) and that no trade crosses
a date. Applies the pre-set selection rule to the 2016-2019 runs (highest gross PF; a tie
within 0.005 goes to the larger cap, off = largest), then shows the 2020-2026 test runs if present.

Usage: python analyze_maxredrun_clean_study.py [study_dir]
"""

import json
import sys
from pathlib import Path

import numpy as np

from analyze_flatten_study import summarize
from project_paths import PROJECT_ROOT
from verify_location_validation import read_rows

STUDY = PROJECT_ROOT / "Reports" / "maxredrun_clean_20261001"
TIE = 0.005


def pf(x):
    loss = -x[x < 0].sum()
    return x[x > 0].sum() / loss if loss else float("nan")


def load(study, job):
    rows = read_rows(study / job["csv"])
    stats = read_rows(study / job["csv"].replace(".csv", "_stats.csv"))[0]
    gross = np.array([float(r["trade_profit"]) for r in rows])
    assert len(rows) == int(stats["trades"]), (job["tag"], "trade count")
    assert abs(gross.sum() - float(stats["net_profit"])) < 1e-6, (job["tag"], "PnL")
    assert int(stats["max_red_run"]) == job["cap"], (job["tag"], "cap flag")
    s = summarize(rows)
    assert s["cross"] == 0, (job["tag"], "cross-date trades")
    return dict(s, gross=float(gross.sum()), gross_pf=pf(gross))


def table(title, res):
    print(title)
    print(f"  {'cap':>4}{'trades':>7}{'gross $':>9}{'gross PF':>9}{'net $':>9}{'net PF':>8}{'net DD':>8}{'avg R':>9}")
    for cap, s in sorted(res.items(), key=lambda kv: (kv[0] == 0, kv[0])):
        lab = "off" if cap == 0 else str(cap)
        print(f"  {lab:>4}{s['trades']:>7}{s['gross']:>9.0f}{s['gross_pf']:>9.3f}{s['net']:>9.0f}"
              f"{s['net_pf']:>8.3f}{s['net_dd']:>8.0f}{s['avg_r']:>+9.4f}")
    print()


def main(study):
    jobs = json.loads((study / "manifest.json").read_text(encoding="utf-8"))["jobs"]
    train = {j["cap"]: load(study, j) for j in jobs if j["period"] == "train"}
    print(f"PASS: {len(train)} training runs reconcile with MT5 stats; caps match; no cross-date trades.\n")
    table("TRAIN 2016-2019 (selection by gross PF)", train)
    best = max(s["gross_pf"] for s in train.values())
    tied = [c for c, s in train.items() if s["gross_pf"] >= best - TIE]
    winner = max(tied, key=lambda c: 99 if c == 0 else c)
    print(f"Selection: best gross PF {best:.3f}; within {TIE}: "
          f"{['off' if c == 0 else c for c in tied]} -> winner MaxRedRun = {'off' if winner == 0 else winner}\n")

    test = {j["cap"]: load(study, j) for j in jobs if j["period"] == "recent"
            if (study / j["csv"]).exists()}
    if test:
        table("TEST 2020-2026 (frozen winner vs off)", test)
    (study / "results.json").write_text(json.dumps({"train": train, "test": test, "winner": winner}, indent=1),
                                        encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else STUDY)
