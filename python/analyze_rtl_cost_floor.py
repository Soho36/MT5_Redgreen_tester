"""Summarise the native RTL cost-floor runs (docs/baseline/rtl-cost-floor/PROTOCOL.md)."""
import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports/rtl_cost_floor_20261119"
ARMS = ("control", "floor20", "floor10", "floor05")
ERAS = (("2010-15", 2010, 2015), ("2016-19", 2016, 2019), ("2020-Sep26", 2020, 2026))
PT = 2.0


def load(arm):
    t = pd.read_csv(RUN / f"runband_costfloor_20261119_{arm}_1.00.csv", sep="\t", encoding="utf-16")
    for c in ("entry_time", "exit_time"):
        t[c] = pd.to_datetime(t[c], format="%Y.%m.%d %H:%M:%S")
    t["risk"] = t.candle_range * PT
    return t.sort_values("exit_time").reset_index(drop=True)


def dd(x):
    e = np.cumsum(x)
    return float((np.maximum.accumulate(np.r_[0, e])[1:] - e).max()) if len(e) else 0.0


def main():
    led = {a: load(a) for a in ARMS}
    stats = {a: pd.read_csv(RUN / f"runband_costfloor_20261119_{a}_1.00_stats.csv", sep="\t", encoding="utf-16") for a in ARMS}
    ctrl_keys = set(led["control"].entry_time)
    rows = []
    for cost in (1.05, 0.50):
        for a in ARMS:
            t = led[a]
            for name, y0, y1 in ERAS + (("pooled", 2010, 2026),):
                g = t[t.entry_time.dt.year.between(y0, y1)]
                net = g.trade_profit - cost
                rows.append({"cost": cost, "arm": a, "era": name, "trades": len(g), "net": round(net.sum(), 2),
                             "net_R": round((net / g.risk).mean(), 4), "gross_R": round((g.trade_profit / g.risk).mean(), 4),
                             "closed_dd": round(dd(net.values), 2),
                             "freed_trades": int((~g.entry_time.isin(ctrl_keys)).sum()),
                             "freed_net": round((g.trade_profit - cost)[~g.entry_time.isin(ctrl_keys)].sum(), 2)})
    out = pd.DataFrame(rows)
    out.to_csv(RUN / "summary.csv", index=False)
    pd.set_option("display.width", 200)
    print(out.to_string(index=False))
    print("\nMT5 gross equity DD (whole run, before costs):")
    for a in ARMS:
        s = stats[a].iloc[0]
        print(f"  {a}: trades {s.trades}, gross net {s.net_profit}, equity DD {s.equity_dd}")


if __name__ == "__main__":
    main()
