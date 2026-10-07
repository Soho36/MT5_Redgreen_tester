"""Compare the RTL baseline on MNQ and MES (runs prepared by prepare_instrument_baseline.py).

R per trade = trade_profit / (candle_range * $ per point): the stop sits one candle range below the entry.
$ per point is read from the ledgers (1R losers), so the symbol settings are checked rather than assumed.
Costs: $1.05 per contract per trade, as in the NQ studies. Descriptive comparison, no gate.
Usage: python analyze_instrument_baseline.py
"""

import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports" / "instrument_baseline_20261008"
OLD_MNQ = ROOT / "Reports" / "trend_rr_20261002" / "runband_trendrr_20261002_f50_baseline_1.00.csv"
COST = 1.05
GAP_DAYS = ("2020.02.28", "2020.06.30")   # ES source data stops mid-session (docs/reference/DATA_BUILD.md)
PERIODS = (("2010-15", 2010, 2015), ("2016-19", 2016, 2019), ("2020-26", 2020, 2026), ("all", 2010, 2026))


def load(path):
    d = pd.read_csv(path, sep="\t", encoding="utf-16")
    d["entry"] = pd.to_datetime(d["entry_time"], format="%Y.%m.%d %H:%M:%S")
    d["exit"] = pd.to_datetime(d["exit_time"], format="%Y.%m.%d %H:%M:%S")
    return d


def point_value(d):
    """$ per point from trades that lost exactly their candle range (the stop)."""
    ratio = (-d["trade_profit"] / d["candle_range"]).round(6)
    return float(ratio[d["trade_profit"] < 0].mode().iloc[0])


def max_dd(x):
    eq = np.cumsum(x)
    return float(np.max(np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq)) if len(x) else 0.0


def summary(d, pv):
    risk = d["candle_range"] * pv
    gross_r = d["trade_profit"] / risk
    net = d["trade_profit"] - COST
    net_r = net / risk
    win, loss = net[net > 0].sum(), -net[net < 0].sum()
    return {"trades": len(d), "win%": 100 * (d["trade_profit"] > 0).mean(),
            "med_risk_pts": d["candle_range"].median(), "cost_R": (COST / risk).mean(),
            "gross_R": gross_r.mean(), "net_R": net_r.mean(),
            "PF_gross": d.loc[d.trade_profit > 0, "trade_profit"].sum() / -d.loc[d.trade_profit < 0, "trade_profit"].sum(),
            "PF_net": win / loss, "net_$": net.sum(), "maxDD_$": max_dd(net.to_numpy()),
            "net_R_sum": net_r.sum(), "maxDD_R": max_dd(net_r.to_numpy())}


def main():
    mnq = load(RUN / "runband_instbase_20261008_mnq_1.00.csv")
    mes = load(RUN / "runband_instbase_20261008_mes_1.00.csv")

    old = load(OLD_MNQ)
    same = (len(old) == len(mnq) and (old["entry_time"].values == mnq["entry_time"].values).all()
            and np.allclose(old["trade_profit"], mnq["trade_profit"]))
    print(f"MNQ rerun reproduces the trend-RR baseline ledger ({len(old):,} trades): {same}")

    pv = {"MNQ": point_value(mnq), "MES": point_value(mes)}
    print(f"$ per point from ledgers: {pv}")
    on_gap = mes[mes["entry_time"].str[:10].isin(GAP_DAYS)]
    print(f"MES trades on the 2 ES data-gap days: {len(on_gap)}, net ${(on_gap.trade_profit - COST).sum():.2f}")

    rows = []
    for lab, lo, hi in PERIODS:
        for name, d in (("MNQ", mnq), ("MES", mes)):
            p = d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi)]
            rows.append({"period": lab, "symbol": name, **summary(p, pv[name])})
    t = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print("\n" + t.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    yr = []
    for name, d in (("MNQ", mnq), ("MES", mes)):
        for y, p in d.groupby(d.entry.dt.year):
            s = summary(p, pv[name])
            yr.append({"year": y, "symbol": name, "trades": s["trades"], "net_R": s["net_R"], "PF_net": s["PF_net"],
                       "net_$": s["net_$"]})
    y = pd.DataFrame(yr).pivot(index="year", columns="symbol")
    print("\n" + y.to_string(float_format=lambda x: f"{x:,.3f}"))

    # do the two instruments trade the same moments?
    k = lambda d: set(d["entry_time"].str[:16])
    both = len(k(mnq) & k(mes))
    print(f"\nEntries in the same minute on both: {both:,} ({both / len(mnq):.1%} of MNQ, {both / len(mes):.1%} of MES)")
    dm = mnq.assign(r=(mnq.trade_profit - COST) / (mnq.candle_range * pv["MNQ"])).groupby(mnq.exit.dt.normalize()).r.sum()
    de = mes.assign(r=(mes.trade_profit - COST) / (mes.candle_range * pv["MES"])).groupby(mes.exit.dt.normalize()).r.sum()
    dd = pd.concat([dm, de], axis=1, keys=["MNQ", "MES"], sort=True).fillna(0)
    print(f"Daily net-R correlation MNQ vs MES: {dd.MNQ.corr(dd.MES):+.2f}")


if __name__ == "__main__":
    main()
