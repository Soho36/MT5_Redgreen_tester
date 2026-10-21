"""Reconcile the red range-breakdown short sweep and compare periods/settings."""
import json

import pandas as pd

from analyze_instrument_baseline import load, summary
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "gg_red_breakdown_short_20261021"


def main():
    jobs = json.loads((STUDY / "manifest.json").read_text(encoding="utf-8"))["jobs"]
    rows = []
    for job in jobs:
        tag = job["tag"]
        if not (STUDY / f"{tag}.completed.json").exists():
            raise FileNotFoundError(f"Incomplete MT5 run: {tag}")
        d = load(STUDY / f"runband_{tag}_1.00.csv")
        stats = pd.read_csv(STUDY / f"runband_{tag}_1.00_stats.csv",
                            sep="\t", encoding="utf-16").iloc[0]
        assert len(d) == int(stats.trades), tag
        assert abs(d.trade_profit.sum() - stats.net_profit) < 1e-5, tag
        for name, lo, hi in (("2016-19", 2016, 2019),
                             ("2020-26", 2020, 2026)):
            p = d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi)]
            v = summary(p, 2.0)
            rows.append({"period": name,
                         "setting": tag.removeprefix("ggredbreak_20261021_"),
                         "trades": len(p), "net_$": round(v["net_$"]),
                         "DD_$": round(v["maxDD_$"]),
                         "PF_net": round(v["PF_net"], 3),
                         "mean_net_R": round(v["net_R"], 3)})
    print("All 13 red-breakdown ledgers reconcile with MT5 totals.")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()


