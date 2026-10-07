"""Analyze the clean-data RR check (protocol: docs/baseline/rr-clean-data/RESULTS.md).

Checks every CSV against its MT5 stats and that no trade crosses a date, prints the
results per period and RR, and applies the pre-set rule: adopt 2.5R only if 2.0, 2.5
and 3.0 all beat 1.0 on net $ and net PF in both periods.

Usage: python analyze_rr_clean_study.py [study_dir]
"""

import json
import sys
from pathlib import Path

from analyze_flatten_study import summarize
from project_paths import PROJECT_ROOT
from verify_location_validation import read_rows

STUDY = PROJECT_ROOT / "Reports" / "rr_clean_20261001"


def main(study):
    manifest = json.loads((study / "manifest.json").read_text(encoding="utf-8"))
    res = {}
    for job in manifest["jobs"]:
        rows = read_rows(study / job["csv"])
        stats = read_rows(study / job["csv"].replace(".csv", "_stats.csv"))[0]
        assert len(rows) == int(stats["trades"]), (job["tag"], "trade count")
        assert abs(sum(float(r["trade_profit"]) for r in rows) - float(stats["net_profit"])) < 1e-6, (job["tag"], "PnL")
        s = summarize(rows)
        assert s["cross"] == 0, (job["tag"], "cross-date trades present")
        res[(job["period"], job["rr"])] = s
    print(f"PASS: {len(res)} runs reconcile with MT5 stats; no trade crosses a date.\n")

    print(f"{'period':<7}{'RR':>5}{'trades':>7}{'net $':>9}{'net PF':>8}{'net DD':>8}{'net/DD':>8}{'avg R':>9}")
    for (period, rr), s in res.items():
        print(f"{period:<7}{rr:>5.1f}{s['trades']:>7}{s['net']:>9.0f}{s['net_pf']:>8.3f}{s['net_dd']:>8.0f}"
              f"{s['net'] / s['net_dd']:>8.2f}{s['avg_r']:>+9.4f}")

    ok = all(res[(p, rr)]["net"] > res[(p, 1.0)]["net"] and res[(p, rr)]["net_pf"] > res[(p, 1.0)]["net_pf"]
             for p in ("train", "recent") for rr in (2.0, 2.5, 3.0))
    print("\nDecision rule (2.0, 2.5 and 3.0 all beat 1.0 on net $ and net PF in both periods):",
          "MET -> adopt 2.5R" if ok else "NOT met -> keep 1.0R")
    (study / "results.json").write_text(json.dumps({f"{p}_{rr}": s for (p, rr), s in res.items()}, indent=1),
                                        encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else STUDY)
