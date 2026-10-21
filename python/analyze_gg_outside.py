"""Reconcile and compare the GG outside-bar sweep with the frozen no-cap GG run."""
import json
from pathlib import Path

import pandas as pd

from analyze_instrument_baseline import load, summary
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "gg_outside_20261020"
BASE = (ROOT / "Reports" / "gg_green_cap_review_20261020"
        / "runband_gggreen_20261020_cap0_1.00.csv")
COLUMNS = ["entry_time", "exit_time", "trade_profit", "candle_range"]


def main():
    manifest = json.loads((STUDY / "manifest.json").read_text(encoding="utf-8"))
    runs = {}
    for job in manifest["jobs"]:
        tag = job["tag"]
        path = STUDY / f"runband_{tag}_1.00.csv"
        if not (STUDY / f"{tag}.completed.json").exists():
            raise FileNotFoundError(f"Incomplete MT5 job: {tag}")
        d = load(path)
        stats = pd.read_csv(STUDY / f"runband_{tag}_1.00_stats.csv",
                            sep="\t", encoding="utf-16").iloc[0]
        assert len(d) == int(stats.trades), tag
        assert abs(d.trade_profit.sum() - stats.net_profit) < 1e-5, tag
        runs[tag] = d

    baseline = load(BASE)
    control = runs["ggout_20261020_control"]
    assert baseline[COLUMNS].equals(control[COLUMNS]), "Filter-off GG mismatch"
    print(f"Filter-off control exactly reproduces all {len(control):,} GG trades.")

    rows = []
    for label, lo, hi in (("2016-19", 2016, 2019), ("2020-26", 2020, 2026)):
        for job in manifest["jobs"]:
            d = runs[job["tag"]]
            p = d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi)]
            v = summary(p, 2.0)  # MNQ contract, $2 per index point
            rows.append({"period": label,
                         "setting": job["tag"].removeprefix("ggout_20261020_"),
                         "trades": len(p), "net_$": round(v["net_$"]),
                         "DD_$": round(v["maxDD_$"]),
                         "PF_net": round(v["PF_net"], 3),
                         "mean_net_R": round(v["net_R"], 3)})
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()

