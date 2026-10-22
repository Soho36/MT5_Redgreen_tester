"""Split RTL into buy-stop gain and plain-long background on NQ, ES and YM (runs: prepare_ym_control.py).

Control = market buy at every M30 bar open while flat (same stop distance and exit as RTL). Gain = RTL mean
gross R minus control mean gross R, 95% interval resampling days jointly (as analyze_signal_colour.py).
Audited ledgers only (audit_ym_control.py). Trades entered before 2026-10-01, as in analyze_ym_baselines.py.
Usage: python analyze_ym_control.py
"""
import json

import numpy as np
import pandas as pd

from analyze_instrument_baseline import load
from analyze_signal_colour import day_ci, edge_over_control
from analyze_ym_baselines import CUTOFF, PERIODS
from audit_ym_control import PV
from project_paths import PROJECT_ROOT as ROOT

CTRL = ROOT / "Reports" / "ym_control_20261023"
BASE = ROOT / "Reports" / "ym_baselines_20261023"
OLD_NQ_CONTROL = ROOT / "Reports" / "signal_colour_20261008" / "runband_signal_20261008_market_control_1.00_audited.csv"


def audited(run, tag):
    return load(run / f"runband_{tag}_1.00_audited.csv")


def main():
    rng = np.random.default_rng(20261023)
    jobs = {j["instrument"]: j for j in json.loads((CTRL / "manifest.json").read_text())["jobs"] if j["mode"] == 3}
    rtl = {i: audited(BASE, f"ymbase_20261023_rtl_{i}") for i in jobs}
    ctrl = {i: audited(CTRL, f"ymctrl_20261023_control_{i}") for i in jobs}

    check = audited(CTRL, "ymctrl_20261023_red_nocap_ym")
    same = len(check) == len(rtl["ym"]) and (check.entry_time.values == rtl["ym"].entry_time.values).all() \
        and np.allclose(check.trade_profit, rtl["ym"].trade_profit)
    print(f"Signal EA mode 0 on YM reproduces RTL_runband YM ({len(check):,} trades): {same}")
    old = load(OLD_NQ_CONTROL)
    new = ctrl["nq"][ctrl["nq"].entry <= old.entry.max()]
    key = lambda d: d.sort_values("entry_time").set_index("entry_time").trade_profit   # recovered rows sit elsewhere
    a, b = key(old), key(new)
    same = a.index.equals(b.index) and np.allclose(a.values, b.values)
    print(f"NQ control reproduces the 2026-10-08 audited control to 2026-07-14 ({len(old):,} trades): {same}")

    rows = []
    for lab, lo, hi in PERIODS:
        for inst in ("nq", "es", "ym"):
            pv = PV[jobs[inst]["symbol"]]
            sel = lambda d: d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi) & (d.entry < CUTOFF)]
            a, b = sel(rtl[inst]), sel(ctrl[inst])
            gain, glo, ghi = edge_over_control(a, b, pv, rng)
            clo, chi = day_ci(b, pv, rng)
            rows.append({"period": lab, "inst": inst.upper(), "rtl_trades": len(a), "ctrl_trades": len(b),
                         "rtl_R": (a.trade_profit / (a.candle_range * pv)).mean(),
                         "ctrl_R": (b.trade_profit / (b.candle_range * pv)).mean(), "ctrl_lo": clo, "ctrl_hi": chi,
                         "gain_R": gain, "gain_lo": glo, "gain_hi": ghi,
                         "ctrl_win%": 100 * (b.trade_profit > 0).mean()})
    t = pd.DataFrame(rows)
    t.to_csv(CTRL / "summary.csv", index=False)
    pd.set_option("display.width", 250)
    print("\n" + t.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    yr = []
    for inst in ("nq", "es", "ym"):
        pv = PV[jobs[inst]["symbol"]]
        for name, d in (("rtl", rtl[inst]), ("ctrl", ctrl[inst])):
            d = d[d.entry < CUTOFF]
            r = (d.trade_profit / (d.candle_range * pv)).groupby(d.entry.dt.year).mean()
            yr.append(r.rename(f"{inst}_{name}"))
    y = pd.concat(yr, axis=1)
    for inst in ("nq", "es", "ym"):
        y[f"{inst}_gain"] = y[f"{inst}_rtl"] - y[f"{inst}_ctrl"]
    y.to_csv(CTRL / "years.csv")
    print("\nGross R by year\n" + y.to_string(float_format=lambda x: f"{x:+.3f}"))
    print("\nYears with positive buy-stop gain:", {i: int((y[f"{i}_gain"] > 0).sum()) for i in ("nq", "es", "ym")},
          "of", len(y))


if __name__ == "__main__":
    main()
