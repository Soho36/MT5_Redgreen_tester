"""Readable yearly view of the existing Q13 data; no new selection rules."""

import json

import numpy as np
import pandas as pd

from analyze_broad_support import verify_manifest
from analyze_price_levels import ROOT, sha256

STUDY = ROOT / "Reports/levels/weekly_low_robustness_20261004"


def main():
    manifest = STUDY / "provenance.json"
    verify_manifest(manifest)
    for entry in json.loads(manifest.read_text())["outputs"]:
        assert sha256(entry["path"]) == entry["sha256"], entry["path"]
    y = pd.read_csv(STUDY / "yearly.csv").sort_values("year")
    contact = pd.read_csv(STUDY / "contact_trades.csv")
    all_trades = pd.read_csv(ROOT / "Reports/levels/broad_support_20261004/trades.csv")
    all_trades = all_trades[all_trades.config == "previous_week"]
    events = contact.groupby(["year", "weekly_event"]).agg(
        fills=("net_r", "size"), sum_r=("net_r", "sum"), mean_r=("net_r", "mean"))
    lines = ["| Year | PWL trades | PWL avg R | Other RTL avg R | Difference | Weekly events |",
             "|---|---:|---:|---:|---:|---:|"]
    details = ["| Year | Events | Positive total R | Sum of event R | Median event total R | Equal-event avg R/trade |",
               "|---|---:|---:|---:|---:|---:|"]
    for row in y.to_dict("records"):
        year = row["year"]
        a = contact[contact.year == year]
        b = all_trades[(all_trades.year == year) & (all_trades.group != "contact")]
        e = events.loc[year]
        assert len(a) == row["candidate.fills"] and len(b) == row["complement.fills"]
        assert len(e) == row["filled_events"]
        assert np.isclose(a.net_r.mean(), row["candidate.mean_r"])
        assert np.isclose(b.net_r.mean(), row["complement.mean_r"])
        assert np.isclose(a.net_r.mean() - b.net_r.mean(), row["mean_r_difference"])
        assert np.isclose(e.sum_r.sum(), a.net_r.sum())
        label = f"{year}*" if year == 2026 else str(year)
        lines.append(f"| {label} | {len(a)} | {a.net_r.mean():+.3f} | {b.net_r.mean():+.3f} | "
                     f"{a.net_r.mean()-b.net_r.mean():+.3f} | {len(e)} |")
        details.append(f"| {label} | {len(e)} | {int((e.sum_r > 0).sum())}/{len(e)} | {e.sum_r.sum():+.3f} | "
                       f"{e.sum_r.median():+.3f} | {e.mean_r.mean():+.3f} |")
    assert len(contact) == 276 and len(events) == 126
    print("\n".join(lines))
    print("\n".join(details))
    for period, g in y.groupby("period", sort=False):
        weighted = (g["candidate.fills"] * g.mean_r_difference).sum() / g["candidate.fills"].sum()
        print(period, "equal-year difference", g.mean_r_difference.mean(), "PWL-count-weighted difference", weighted)
    print("Verified 11 yearly comparisons and 126 event sums against saved trade outcomes.")


if __name__ == "__main__":
    main()
