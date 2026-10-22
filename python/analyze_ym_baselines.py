"""Four baselines (RTL, GG, RTL-short, GG-short) on YM next to NQ and ES (runs from prepare_ym_baselines.py).

R per trade = trade_profit / (candle_range * $ per point); the stop sits one candle range from the entry for
longs and shorts. $ per point is read from the ledgers (1R losers). Costs $1.05 per trade on every symbol.
The comparison table ends at 2026-10-01 (the end of the NQ data); YM's later weeks are listed separately.
Descriptive comparison, no gate. Usage: python analyze_ym_baselines.py
"""
import json

import numpy as np
import pandas as pd

from analyze_instrument_baseline import COST, load, max_dd, point_value
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports" / "ym_baselines_20261023"
CUTOFF = pd.Timestamp("2026-10-01")
PERIODS = (("2010-15", 2010, 2015), ("2016-19", 2016, 2019), ("2020-26", 2020, 2026), ("all", 2010, 2026))
NAMES = {"rtl": "RTL", "gg": "GG", "rtl_short": "RTL-short", "gg_short": "GG-short"}
GAP_DAYS = {"ym": ("2020.02.27", "2020.02.28", "2020.03.16", "2020.06.30"), "es": ("2020.02.28", "2020.06.30")}
PREVIOUS = {  # earlier NQ ledgers of the same EA and inputs
    "rtl": ROOT / "Reports" / "server_clock_20261021" / "runband_clock_20261021_rtl_research_1.00.csv",
    "gg": ROOT / "Reports" / "server_clock_20261021" / "runband_clock_20261021_gg_research_1.00.csv",
    "rtl_short": ROOT / "Reports" / "gg_outside_short_20261020" / "runband_ggshort_20261020_control_1.00.csv",
    "gg_short": ROOT / "Reports" / "gg_red_outside_short_20261021" / "runband_ggredshort_20261021_control_1.00.csv",
}


def summary(d, pv):
    risk = d["candle_range"] * pv
    gross_r = d["trade_profit"] / risk
    net = d["trade_profit"] - COST
    net_r = net / risk
    half = 1.96 * gross_r.std(ddof=1) / np.sqrt(len(d))
    return {"trades": len(d), "win%": 100 * (d["trade_profit"] > 0).mean(), "med_risk_$": risk.median(),
            "gross_R": gross_r.mean(), "gross_R_lo": gross_r.mean() - half, "gross_R_hi": gross_r.mean() + half,
            "net_R": net_r.mean(), "PF_net": net[net > 0].sum() / -net[net < 0].sum(),
            "net_$": net.sum(), "maxDD_$": max_dd(net.to_numpy())}


def main():
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    led, pv = {}, {}
    for job in manifest["jobs"]:
        d = load(RUN / job["outputs"][0])
        led[job["strategy"], job["instrument"]] = d
        pv[job["strategy"], job["instrument"]] = point_value(d)
    print("$ per point from ledgers:", {f"{s}/{i}": v for (s, i), v in pv.items()})

    for s, old_path in PREVIOUS.items():
        new, old = led[s, "nq"], load(old_path)
        if s in ("rtl", "gg"):
            same = len(old) == len(new) and (old.entry_time.values == new.entry_time.values).all() \
                and np.allclose(old.trade_profit, new.trade_profit)
            print(f"NQ {NAMES[s]} reproduces {old_path.parent.name} ({len(old):,} trades): {same}")
        else:   # earlier short runs started 2016-01-01; compare from the second week on
            k = lambda d: d[d.entry >= "2016-01-11"].set_index("entry_time").trade_profit
            a, b = k(old), k(new)
            print(f"NQ {NAMES[s]} vs {old_path.parent.name} from 2016-01-11: {len(a):,} vs {len(b):,} trades, "
                  f"same entries {a.index.equals(b.index)}, same profits {np.allclose(a.values, b.values) if a.index.equals(b.index) else '-'}")

    for inst, days in GAP_DAYS.items():
        for s in NAMES:
            d = led[s, inst]
            g = d[d.entry_time.str[:10].isin(days)]
            print(f"{inst.upper()} {NAMES[s]} trades on data-hole days: {len(g)}, net ${(g.trade_profit - COST).sum():,.0f}")

    pd.set_option("display.width", 250)
    rows = []
    for s in NAMES:
        for lab, lo, hi in PERIODS:
            for inst in ("nq", "es", "ym"):
                d = led[s, inst]
                p = d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi) & (d.entry < CUTOFF)]
                rows.append({"strategy": NAMES[s], "period": lab, "inst": inst.upper(), **summary(p, pv[s, inst])})
    t = pd.DataFrame(rows)
    t.to_csv(RUN / "summary.csv", index=False)
    print("\n" + t.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    yr = []
    for s in NAMES:
        d = led[s, "ym"]
        d = d[d.entry < CUTOFF]
        for y, p in d.groupby(d.entry.dt.year):
            r = summary(p, pv[s, "ym"])
            yr.append({"year": y, "strategy": NAMES[s], "net_$": r["net_$"], "gross_R": r["gross_R"]})
    y = pd.DataFrame(yr).pivot(index="year", columns="strategy")
    y.to_csv(RUN / "ym_years.csv")
    print("\nYM by year\n" + y.to_string(float_format=lambda x: f"{x:,.3f}"))
    print("\nYM years with positive net $:", {NAMES[s]: int((y["net_$"][NAMES[s]] > 0).sum()) for s in NAMES},
          "of", len(y))

    late = [{"strategy": NAMES[s], **summary(led[s, "ym"][led[s, "ym"].entry >= CUTOFF], pv[s, "ym"])} for s in NAMES]
    print("\nYM after 2026-10-01 (not in the table)\n" + pd.DataFrame(late)[["strategy", "trades", "net_$"]].to_string(index=False))

    # long legs together: same-minute overlap and daily correlation per instrument
    for inst in ("nq", "es", "ym"):
        daily = {}
        for s in NAMES:
            d = led[s, inst]
            d = d[d.entry < CUTOFF]
            daily[NAMES[s]] = ((d.trade_profit - COST) / (d.candle_range * pv[s, inst])).groupby(d.exit.dt.normalize()).sum()
        dd = pd.DataFrame(daily).fillna(0)
        print(f"\n{inst.upper()} daily net-R correlation\n" + dd.corr().round(2).to_string())


if __name__ == "__main__":
    main()
