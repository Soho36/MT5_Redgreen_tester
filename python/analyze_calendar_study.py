"""Analyze the early-close calendar study (Reports/early_close_calendar_20261001).

Checks: CSVs reconcile with MT5 stats and carry the right calendar flag; the 2016-2026
calendar-off control reproduces Reports/newdata_check_20261001 field by field (previous
EA build, same symbol). Then compares calendar off vs on: trades, net $, PF, DD, avg R,
cross-date trades and longest hold.

Usage: python analyze_calendar_study.py [study_dir]
"""

import json
import sys
from pathlib import Path

from analyze_flatten_study import COMPARE_FIELDS, summarize
from project_paths import PROJECT_ROOT
from verify_location_validation import read_rows

STUDY = PROJECT_ROOT / "Reports" / "early_close_calendar_20261001"
PREVIOUS = PROJECT_ROOT / "Reports" / "newdata_check_20261001" / "runband_newdata_20261001_2016_2026_rr1_1.00.csv"


def main(study):
    manifest = json.loads((study / "manifest.json").read_text(encoding="utf-8"))
    res = {}
    for job in manifest["jobs"]:
        rows = read_rows(study / job["csv"])
        stats = read_rows(study / job["csv"].replace(".csv", "_stats.csv"))[0]
        assert len(rows) == int(stats["trades"]), (job["tag"], "trade count")
        assert abs(sum(float(r["trade_profit"]) for r in rows) - float(stats["net_profit"])) < 1e-6, (job["tag"], "PnL")
        assert int(stats["early_close_calendar"]) == int(job["calendar"]), (job["tag"], "calendar flag")
        res[(job["period"], job["rr"], job["calendar"])] = summarize(rows)
        if job["period"] == "full":
            prev = read_rows(PREVIOUS)
            assert len(prev) == len(rows), "control count differs from previous build"
            for a, b in zip(prev, rows):
                assert all(a[k] == b[k] for k in COMPARE_FIELDS), ("control differs", a["entry_time"])
            print(f"PASS: calendar-off control reproduces all {len(rows):,} trades of the previous EA build.")
    print(f"PASS: {len(res)} runs reconcile with MT5 stats and carry the right calendar flag.\n")

    print(f"{'period':<7}{'RR':>5} {'calendar':<9}{'trades':>7}{'net $':>9}{'net PF':>8}{'net DD':>8}{'avg R':>9}"
          f"{'x-date':>7}{'x-date $':>9}{'max hold h':>11}")
    for (period, rr, cal), s in res.items():
        if period == "full":
            continue
        print(f"{period:<7}{rr:>5.1f} {'on' if cal else 'off':<9}{s['trades']:>7}{s['net']:>9.0f}{s['net_pf']:>8.3f}"
              f"{s['net_dd']:>8.0f}{s['avg_r']:>+9.4f}{s['cross']:>7}{s['cross_net']:>9.0f}{s['max_hold_h']:>11.1f}")
    (study / "results.json").write_text(
        json.dumps({f"{p}_{rr}_{c}": s for (p, rr, c), s in res.items()}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else STUDY)
