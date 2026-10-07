"""Analyse the signal-colour check (prepare_signal_colour.py). Exploratory, MNQ and MES, no gate.

Same R and cost conventions as analyze_instrument_baseline.py. "RTL+GG" = the red and green ledgers run as two
separate accounts and summed by exit day (the user's "both at the same time").
"Edge over control" = red cap 3 mean R minus market-control mean R, before costs, 95% interval resampling days jointly.
Usage: python analyze_signal_colour.py [mnq|mes]   (mes: red_cap3 + market_control only)
"""

import sys

import numpy as np
import pandas as pd

from analyze_instrument_baseline import COST, PERIODS, load, max_dd, summary
from project_paths import PROJECT_ROOT as ROOT

# key -> (run folder, $ per point (checked in the MES comparison), runs)
CONFIG = {
    "mnq": ("signal_colour_20261008", 2.0,
            ("red_cap3", "green_cap3", "red_nocap", "green_nocap", "any", "market_control")),
    "mes": ("signal_colour_20261008_mes", 5.0, ("red_cap3", "market_control")),
}


def per_day(d, pv):
    d = d.assign(r=d.trade_profit / (d.candle_range * pv), day=d.entry.dt.normalize())
    return d.groupby("day").r.agg(["sum", "size"])


def day_ci(d, pv, rng):
    """95% interval of mean gross R, resampling whole days."""
    g = per_day(d, pv)
    s, n = g["sum"].to_numpy(), g["size"].to_numpy()
    idx = rng.integers(0, len(g), (2000, len(g)))
    return np.percentile(s[idx].sum(1) / n[idx].sum(1), [2.5, 97.5])


def edge_over_control(a, b, pv, rng):
    """Mean gross R of a minus b and its 95% interval, resampling days jointly."""
    g = per_day(a, pv).join(per_day(b, pv), how="outer", lsuffix="_a", rsuffix="_b").fillna(0.0)
    sa, na, sb, nb = (g[c].to_numpy() for c in ("sum_a", "size_a", "sum_b", "size_b"))
    idx = rng.integers(0, len(g), (2000, len(g)))
    diff = sa[idx].sum(1) / na[idx].sum(1) - sb[idx].sum(1) / nb[idx].sum(1)
    return sa.sum() / na.sum() - sb.sum() / nb.sum(), *np.percentile(diff, [2.5, 97.5])


def main(key="mnq"):
    folder, pv, names = CONFIG[key]
    suffix = "" if key == "mnq" else f"_{key}"
    runs = {n: load(ROOT / "Reports" / folder / f"runband_signal_20261008_{n}{suffix}_1.00.csv") for n in names}
    base = load(ROOT / "Reports" / "instrument_baseline_20261008" / f"runband_instbase_20261008_{key}_1.00.csv")
    print(f"[{key}] red_cap3 reproduces the baseline ledger:",
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
            s = summary(p, pv)
            ci = day_ci(p, pv, rng) if lab != "all" else (np.nan, np.nan)
            rows.append({"period": lab, "run": n, **{k: s[k] for k in ("trades", "win%", "gross_R", "net_R", "PF_gross",
                         "PF_net", "net_$", "maxDD_$")}, "gross_R_lo": ci[0], "gross_R_hi": ci[1]})
    pd.set_option("display.width", 250)
    print("\n" + pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nEdge over control (red cap 3 minus market control, mean R before costs):")
    for lab, lo, hi in PERIODS[:3]:
        sel = lambda d: d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi)]
        e, elo, ehi = edge_over_control(sel(runs["red_cap3"]), sel(mc), pv, rng)
        print(f"  {lab}: {e:+.3f} [{elo:+.3f}, {ehi:+.3f}]")

    pairs = [(a, b) for a, b in (("red_cap3", "green_cap3"), ("red_nocap", "green_nocap")) if b in runs]
    if pairs:
        print("\nTwo accounts summed by exit day (net $ after costs):")
    for a, b in pairs:
        daily = pd.concat([(runs[n].trade_profit - COST).groupby(runs[n].exit.dt.normalize()).sum() for n in (a, b)],
                          axis=1, keys=[a, b], sort=True).fillna(0.0)
        daily["both"] = daily[a] + daily[b]
        for lab, lo, hi in PERIODS:
            x = daily[(daily.index.year >= lo) & (daily.index.year <= hi)]
            print(f"  {lab:8s} " + "  ".join(f"{c}: net {x[c].sum():>9,.0f} DD {max_dd(x[c].to_numpy()):>7,.0f}"
                                             for c in daily.columns))
        print(f"  daily correlation {a} vs {b}: {daily[a].corr(daily[b]):+.2f}")

    yr = pd.DataFrame({n: d.assign(r=(d.trade_profit - COST) / (d.candle_range * pv)).groupby(d.entry.dt.year).r.mean()
                       for n, d in runs.items()})
    print("\nNet mean R by year:\n" + yr.to_string(float_format=lambda x: f"{x:+.3f}"))


if __name__ == "__main__":
    main(*sys.argv[1:])
