"""Describe cross-date positions and missing 23:30 flatten callbacks.

This is an attribution diagnostic, not a simulated no-overnight strategy.
"""

from collections import Counter
import json
import re

from analyze_exit_study import dt
from project_paths import PROJECT_ROOT
from verify_location_validation import read_rows


def main():
    directory = PROJECT_ROOT / "Reports/exit_thresholds_20260930"
    result = []
    for phase in ("train", "recent"):
        for rr in (1, 2):
            tag = f"exit_20260930_{phase}_close_{rr}p00"
            rows = read_rows(directory / f"runband_{tag}_{rr:.2f}.csv")
            log = (directory / f"{tag}.agent.log").read_text(encoding="utf-8-sig")
            cutoff = set(re.findall(r"(\d{4}\.\d{2}\.\d{2}) 23:30:00[^\n]*Flatten cutoff reached", log))
            cross = [r for r in rows if r["entry_time"][:10] != r["exit_time"][:10]]
            same = [r for r in rows if r["entry_time"][:10] == r["exit_time"][:10]]
            entrydays = {r["entry_time"][:10] for r in cross}
            result.append(dict(phase=phase, rr=rr, cross_n=len(cross),
                               cross_net=sum(float(r["trade_profit"]) - 1 for r in cross),
                               same_date_net=sum(float(r["trade_profit"]) - 1 for r in same),
                               entry_dates_with_cross_date_trades=len(entrydays),
                               those_dates_with_2330_flatten_log=sorted(entrydays & cutoff),
                               entry_month_counts=dict(sorted(Counter(r["entry_time"][5:7] for r in cross).items())),
                               max_days=max((dt(r["exit_time"]) - dt(r["entry_time"])).total_seconds() / 86400 for r in cross),
                               largest_cross_date_trades=sorted(cross, key=lambda r: float(r["trade_profit"]), reverse=True)[:5]))
    path = directory / "cross_date_audit.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for row in result:
        print(row["phase"], row["rr"], "cross-date n/net:", row["cross_n"], row["cross_net"],
              "same-date net:", row["same_date_net"], "max days:", round(row["max_days"], 2),
              "cross-date entry dates WITH cutoff:", row["those_dates_with_2330_flatten_log"])
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
