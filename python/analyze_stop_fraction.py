"""Tighter RTL stop with a scaled target, NQ and YM (runs from prepare_stop_fraction.py).

R = profit / (actual risk x $/pt); the ledger's candle_range column holds the actual risk (entry - stop). Ledgers are
audited against the MT5 report first. k = 1.0 must reproduce the RTL_runband ledgers of the YM study. "Diff vs k=1" is
the mean gross R difference with a 95% interval resampling days jointly (analyze_signal_colour.edge_over_control).
Net R is the result per dollar risked, the fair measure when size is set by dollar risk; net $ is at one contract.
Trades before 2026-10-01, $1.05 per trade. Usage: python analyze_stop_fraction.py
"""
import json

import numpy as np
import pandas as pd

from analyze_instrument_baseline import COST, load, max_dd
from analyze_signal_colour import edge_over_control
from analyze_ym_baselines import CUTOFF
from audit_granularity_ledgers import ensure_audited
from audit_ym_control import GRID, PV
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports" / "stop_fraction_20261023"
BASE = ROOT / "Reports" / "ym_baselines_20261023"
PERIODS = (("2010-15", 2010, 2015), ("2016-19", 2016, 2019), ("2020-26", 2020, 2026))


def main():
    rng = np.random.default_rng(20261023)
    jobs = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))["jobs"]
    led = {}
    for job in jobs:
        sym = job["symbol"]
        ensure_audited(RUN, {**job, "mode": "rtl"}, {"symbol": sym, "grid_points": GRID[sym]}, PV[sym], fix_risk=True)
        led[job["instrument"], job["stop_fraction"]] = (load(RUN / f"runband_{job['tag']}_1.00_audited.csv"), PV[sym])
    for inst in ("nq", "ym"):
        new, old = led[inst, 1.0][0], load(BASE / f"runband_ymbase_20261023_rtl_{inst}_1.00_audited.csv")
        same = len(new) == len(old) and (new.entry_time.values == old.entry_time.values).all() \
            and np.allclose(new.trade_profit, old.trade_profit) and np.allclose(new.candle_range, old.candle_range)
        print(f"{inst.upper()} k=1 reproduces the RTL baseline ({len(old):,} trades): {same}")

    rows = []
    for (inst, k), (d, pv) in led.items():
        base = led[inst, 1.0][0]
        for lab, lo, hi in PERIODS:
            sel = lambda x: x[(x.entry.dt.year >= lo) & (x.entry.dt.year <= hi) & (x.entry < CUTOFF)]
            p, b = sel(d), sel(base)
            risk = p.candle_range * pv
            net = p.trade_profit - COST
            diff, lo_, hi_ = edge_over_control(p, b, pv, rng) if k < 1 else (0.0, 0.0, 0.0)
            rows.append({"inst": inst.upper(), "k": k, "period": lab, "trades": len(p),
                         "win%": 100 * (p.trade_profit > 0).mean(), "med_risk_$": risk.median(),
                         "gross_R": (p.trade_profit / risk).mean(), "diff_vs_k1": diff, "diff_lo": lo_, "diff_hi": hi_,
                         "cost_R": (COST / risk).mean(), "net_R": (net / risk).mean(), "net_$": net.sum(),
                         "PF_net": net[net > 0].sum() / -net[net < 0].sum(), "maxDD_$": max_dd(net.to_numpy())})
    t = pd.DataFrame(rows).sort_values(["inst", "period", "k"], ascending=[True, True, False])
    t.to_csv(RUN / "summary.csv", index=False)
    pd.set_option("display.width", 250)
    print("\n" + t.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    yr = []
    for (inst, k), (d, pv) in led.items():
        d = d[d.entry < CUTOFF]
        yr.append(((d.trade_profit - COST) / (d.candle_range * pv)).groupby(d.entry.dt.year).mean().rename(f"{inst}_k{k:g}"))
    y = pd.concat(yr, axis=1)
    y.to_csv(RUN / "net_R_by_year.csv")
    print("\nNet R per trade by year\n" + y.to_string(float_format=lambda x: f"{x:+.3f}"))
    for inst in ("nq", "ym"):
        for k in (0.75, 0.5):
            better = int((y[f"{inst}_k{k:g}"] > y[f"{inst}_k1"]).sum())
            print(f"{inst.upper()} k={k}: net R better than k=1 in {better} of {len(y)} years")


if __name__ == "__main__":
    main()
