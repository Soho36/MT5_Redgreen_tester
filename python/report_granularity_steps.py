"""Granularity study, descriptive add-on (2026-10-09): RTL minus control ordered by steps per candle.

Reads the study's saved tables (Reports/granularity_20261009/resolution.csv and contrast.csv) and lines up every
period x grid by the equal-origin mean of executed RTL trades' median grid steps per candle. Adds MES (native
0.25 grid) from the audited signal-colour ledgers for comparison. No new runs; nothing is tuned.

Usage: python report_granularity_steps.py
"""

import numpy as np
import pandas as pd

from analyze_instrument_baseline import PERIODS, load
from analyze_signal_colour import audited, edge_over_control
from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / "Reports" / "granularity_20261009"
MES = ROOT / "Reports" / "signal_colour_20261008_mes"


def nq_table():
    res = pd.read_csv(STUDY / "resolution.csv")
    con = pd.read_csv(STUDY / "contrast.csv")
    steps = (res[(res["mode"] == "rtl") & (res.period != "all")]
             .groupby(["period", "grid_points"]).grid_levels_med.mean().rename("steps"))
    c = con[(con.scope == "equal_origin_mean") & (con.period != "all")]
    c = c.set_index(["period", "grid_points"])[["contrast_R", "contrast_R_lo", "contrast_R_hi"]]
    return c.join(steps).reset_index().assign(symbol="NQ")


def mes_table():
    rng = np.random.default_rng(1)
    red = load(audited(MES / "runband_signal_20261008_red_cap3_mes_1.00.csv"))
    ctl = load(audited(MES / "runband_signal_20261008_market_control_mes_1.00.csv"))
    rows = []
    for lab, lo, hi in PERIODS[:3]:
        sel = lambda d: d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi)]
        e, elo, ehi = edge_over_control(sel(red), sel(ctl), 5.0, rng)
        rows.append({"period": lab, "grid_points": 0.25, "contrast_R": e, "contrast_R_lo": elo, "contrast_R_hi": ehi,
                     "steps": sel(red).candle_range.median() / 0.25, "symbol": "ES"})
    return pd.DataFrame(rows)


def main():
    t = pd.concat([nq_table(), mes_table()]).sort_values(["steps", "symbol"])
    pd.set_option("display.width", 200)
    print(t[["symbol", "period", "grid_points", "steps", "contrast_R", "contrast_R_lo", "contrast_R_hi"]]
          .to_string(index=False, float_format=lambda x: f"{x:+.3f}"))


if __name__ == "__main__":
    main()
