"""Reconcile the GG outside-bar short MT5 sweep and compare with the long sweep."""
import json

import pandas as pd

from analyze_instrument_baseline import load, summary
from project_paths import PROJECT_ROOT as ROOT

SHORT = ROOT / "Reports" / "gg_outside_short_20261020"
LONG = ROOT / "Reports" / "gg_outside_20261020"


def main():
    jobs = json.loads((SHORT / "manifest.json").read_text(encoding="utf-8"))["jobs"]
    rows = []
    for job in jobs:
        short_tag = job["tag"]
        long_tag = short_tag.replace("ggshort_", "ggout_")
        short_path = SHORT / f"runband_{short_tag}_1.00.csv"
        long_path = LONG / f"runband_{long_tag}_1.00.csv"
        if not (SHORT / f"{short_tag}.completed.json").exists():
            raise FileNotFoundError(f"Incomplete MT5 run: {short_tag}")
        short = load(short_path)
        long = load(long_path)
        stats = pd.read_csv(SHORT / f"runband_{short_tag}_1.00_stats.csv",
                            sep="\t", encoding="utf-16").iloc[0]
        assert len(short) == int(stats.trades), short_tag
        assert abs(short.trade_profit.sum() - stats.net_profit) < 1e-5, short_tag
        for name, lo, hi in (("2016-19", 2016, 2019),
                             ("2020-26", 2020, 2026)):
            for side, d in (("short", short), ("long", long)):
                p = d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi)]
                v = summary(p, 2.0)  # MNQ, $2 per index point; costs inside summary
                rows.append({"period": name,
                             "setting": short_tag.removeprefix("ggshort_20261020_"),
                             "side": side, "trades": len(p),
                             "net_$": round(v["net_$"]),
                             "DD_$": round(v["maxDD_$"]),
                             "PF_net": round(v["PF_net"], 3),
                             "mean_net_R": round(v["net_R"], 3)})
    print("All 13 short ledgers reconcile with MT5 totals.")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()

