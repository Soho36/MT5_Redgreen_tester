"""Path experiment, descriptive add-on (2026-10-09): gross R by signal-size bin, coarse NQ vs ES.

Reads Reports/path_experiment_20261009/group_metrics.csv (the study's own size-bin summaries of the broad
four-arm panel, effective-step matching, fixed panel weights renormalised within each bin) and prints RTL and
market-control gross R per bin with the coarse-NQ-minus-ES gaps. No new runs, no intervals, nothing tuned.

Usage: python report_path_size_bins.py
"""

import pandas as pd

from project_paths import PROJECT_ROOT as ROOT

GROUPS = ROOT / "Reports" / "path_experiment_20261009" / "group_metrics.csv"
ORDER = ["[0,8)", "[8,16)", "[16,24)", "[24,32)", "[32,48)", "[48,64)", "[64,128)", "[128,inf)"]


def main():
    g = pd.read_csv(GROUPS)
    pd.set_option("display.width", 200)
    for period in ("2010-15", "2016-19", "2020-26"):
        q = g[(g.period == period) & (g.panel == "coarse_ES_four_arm") & (g.size_basis == "effective")
              & (g["sample"] == "primary") & (g.group_kind == "size_bin")]
        t = q.pivot_table(index="group", columns="arm", values="gross_R")
        t["panel_weight"] = q.groupby("group").panel_weight_mass.first()
        t["control_gap"] = t["NQcoarse__control"] - t["ES__control"]
        t["rtl_gap"] = t["NQcoarse__rtl"] - t["ES__rtl"]
        t = t.reindex([b for b in ORDER if b in t.index])
        print(f"\n{period}: four-arm panel, effective steps, gross R by signal-size bin")
        print(t.to_string(float_format=lambda x: f"{x:+.3f}"))


if __name__ == "__main__":
    main()
