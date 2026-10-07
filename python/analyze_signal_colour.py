"""Analyse the signal-colour check (prepare_signal_colour.py). Exploratory, MNQ, no gate.

Same R and cost conventions as analyze_instrument_baseline.py. "RTL+GG" = the red and green ledgers run as two
separate accounts and summed by exit day (the user's "both at the same time").
Usage: python analyze_signal_colour.py
"""

import numpy as np
import pandas as pd

from analyze_instrument_baseline import COST, PERIODS, load, max_dd, summary
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports" / "signal_colour_20261008"
BASELINE = ROOT / "Reports" / "instrument_baseline_20261008" / "runband_instbase_20261008_mnq_1.00.csv"
PV = 2.0   # MNQ $ per point (checked in the MES comparison)
NAMES = ("red_cap3", "green_cap3", "red_nocap", "green_nocap", "any", "market_control")


def day_ci(d, rng):
    """95% interval of mean gross R, resampling whole days."""
    d = d.assign(r=d.trade_profit / (d.candle_range * PV), day=d.entry.dt.normalize())
    g = d.groupby("day").r.agg(["sum", "size"])
    s, n = g["sum"].to_numpy(), g["size"].to_numpy()
    idx = rng.integers(0, len(g), (2000, len(g)))
    m = s[idx].sum(1) / n[idx].sum(1)
    return np.percentile(m, [2.5, 97.5])


def main():
    runs = {n: load(RUN / f"runband_signal_20261008_{n}_1.00.csv") for n in NAMES}
    base = load(BASELINE)
    print("red_cap3 reproduces the baseline ledger:",
          len(base) == len(runs["red_cap3"]) and (base.entry_time.values == runs["red_cap3"].entry_time.values).all()
          and np.allclose(base.trade_profit, runs["red_cap3"].trade_profit))
    mc = runs["market_control"]
    print("market control entries at a bar open (mm:ss 00:00 or 30:00):",
          f"{mc.entry.dt.strftime('%M:%S').isin(['00:00', '30:00']).mean():.1%}")

    rng = np.random.default_rng(1)
    rows = []
    for lab, lo, hi in PERIODS:
        for n, d in runs.items():
            p = d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi)]
            s = summary(p, PV)
            ci = day_ci(p, rng) if lab != "all" else (np.nan, np.nan)
            rows.append({"period": lab, "run": n, **{k: s[k] for k in ("trades", "win%", "gross_R", "net_R", "PF_gross",
                         "PF_net", "net_$", "maxDD_$")}, "gross_R_lo": ci[0], "gross_R_hi": ci[1]})
    pd.set_option("display.width", 250)
    print("\n" + pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nTwo accounts summed by exit day (net $ after costs):")
    for a, b in (("red_cap3", "green_cap3"), ("red_nocap", "green_nocap")):
        daily = pd.concat([(runs[n].trade_profit - COST).groupby(runs[n].exit.dt.normalize()).sum() for n in (a, b)],
                          axis=1, keys=[a, b], sort=True).fillna(0.0)
        daily["both"] = daily[a] + daily[b]
        for lab, lo, hi in PERIODS:
            x = daily[(daily.index.year >= lo) & (daily.index.year <= hi)]
            print(f"  {lab:8s} " + "  ".join(f"{c}: net {x[c].sum():>9,.0f} DD {max_dd(x[c].to_numpy()):>7,.0f}"
                                             for c in daily.columns))
        print(f"  daily correlation {a} vs {b}: {daily[a].corr(daily[b]):+.2f}")

    yr = pd.DataFrame({n: d.assign(r=(d.trade_profit - COST) / (d.candle_range * PV)).groupby(d.entry.dt.year).r.mean()
                       for n, d in runs.items()})
    print("\nNet mean R by year:\n" + yr.to_string(float_format=lambda x: f"{x:+.3f}"))


if __name__ == "__main__":
    main()
