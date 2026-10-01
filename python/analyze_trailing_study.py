"""Analyze the trailing-stop study (protocol: docs/TRAILING_STOP_RESULTS.md).

Checks: CSVs reconcile with MT5 stats; each run's trail_distance_r matches its
job; trailing-off controls reproduce the flatten-fixed RR1 runs field by field;
counts failed stop modifications in the saved tester logs. Then applies the
pre-set rule: adopt a distance only if it beats the control on BOTH net $ and
average net R in BOTH periods.

Usage: python analyze_trailing_study.py [study_dir]
"""

import json
import sys
from pathlib import Path

from analyze_flatten_study import COMPARE_FIELDS, summarize
from project_paths import PROJECT_ROOT
from verify_location_validation import read_rows

STUDY = PROJECT_ROOT / "Reports" / "trailing_stop_20261001"
FLAT = PROJECT_ROOT / "Reports" / "flatten_fallback_20261001"


def main(study):
    manifest = json.loads((study / "manifest.json").read_text(encoding="utf-8"))
    res = {}
    for job in manifest["jobs"]:
        rows = read_rows(study / job["csv"])
        stats = read_rows(study / job["csv"].replace(".csv", "_stats.csv"))[0]
        assert len(rows) == int(stats["trades"]), (job["tag"], "trade count")
        assert abs(sum(float(r["trade_profit"]) for r in rows) - float(stats["net_profit"])) < 1e-6, (job["tag"], "PnL")
        assert abs(float(stats["trail_distance_r"]) - job["distance"]) < 1e-9, (job["tag"], "distance flag")
        log = (study / f"{job['tag']}.tester.log").read_text(encoding="utf-8", errors="replace")
        res[(job["period"], job["distance"])] = dict(summarize(rows), failed_modify=log.count("Trailing SL modify failed"))
        if job["distance"] == 0.0:
            ref = read_rows(FLAT / f"runband_flat_20261001_{job['period']}_fb_1p00_1.00.csv")
            assert len(ref) == len(rows), (job["tag"], "control count differs")
            for a, b in zip(ref, rows):
                assert all(a[k] == b[k] for k in COMPARE_FIELDS), (job["tag"], a["entry_time"])
            print(f"PASS: {job['period']} trailing-off control reproduces all {len(rows):,} flatten-fixed trades.")
    print(f"PASS: {len(res)} runs reconcile with MT5 stats and carry the right trail distance.\n")

    print(f"{'period':<7}{'trail':>6}{'trades':>7}{'net $':>9}{'net PF':>8}{'net DD':>8}{'avg R':>9}"
          f"{'x-date $':>9}{'failed mods':>12}")
    for (period, d), s in res.items():
        lab = "off" if d == 0 else f"{d:.2f}R"
        print(f"{period:<7}{lab:>6}{s['trades']:>7}{s['net']:>9.0f}{s['net_pf']:>8.3f}{s['net_dd']:>8.0f}"
              f"{s['avg_r']:>+9.4f}{s['cross_net']:>9.0f}{s['failed_modify']:>12}")

    print("\nDecision rule: beat the control on net $ AND avg net R in BOTH periods.")
    for d in sorted({d for _, d in res if d > 0}):
        ok = all(res[(p, d)]["net"] > res[(p, 0.0)]["net"] and res[(p, d)]["avg_r"] > res[(p, 0.0)]["avg_r"]
                 for p in ("train", "recent"))
        print(f"  {d:.2f}R: {'CANDIDATE' if ok else 'rejected'}")
    (study / "results.json").write_text(
        json.dumps({f"{p}_{d}": s for (p, d), s in res.items()}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else STUDY)
