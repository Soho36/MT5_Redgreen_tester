"""The YM experiments on RTY (runs from prepare_rty_baselines.py), compared with NQ, ES and YM on the same windows.

CME RTY starts 2017-07-10, so the windows are 2018-19 and 2020-26 (2017 H2, the thin launch months, listed apart).
Market-entry ledgers are audited against the MT5 report first (audit_granularity_ledgers.ensure_audited, fix_risk on,
as audit_ym_control.py); the RTL buy-stop ledgers are audited too. NQ/ES/YM ledgers come from the YM study.
Same measures as analyze_ym_baselines / analyze_ym_control / analyze_ym_h1. Trades before 2026-10-01.
Usage: python analyze_rty_baselines.py
"""
import json

import numpy as np
import pandas as pd

from analyze_instrument_baseline import COST, load, point_value
from analyze_signal_colour import edge_over_control
from analyze_ym_baselines import CUTOFF, NAMES, summary
from analyze_ym_h1 import BINS, H1 as OTHER_H1, LABELS
from audit_granularity_ledgers import ensure_audited
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports" / "rty_baselines_20261023"
REP = ROOT / "Reports"
SYMBOL = "M2KcontDTBNT20172026"
PV, TICK = 5.0, 0.1
WINDOWS = (("2017H2", 2017, 2017), ("2018-19", 2018, 2019), ("2020-26", 2020, 2026), ("2018-26", 2018, 2026))
OTHER = {"nq": (0.25, 2.0), "es": (0.25, 5.0), "ym": (1.0, 0.5)}


def other_path(kind, inst, audited=False):
    sfx = "_audited" if audited else ""
    if kind == "control":
        return REP / "ym_control_20261023" / f"runband_ymctrl_20261023_control_{inst}_1.00{sfx}.csv"
    return REP / "ym_baselines_20261023" / f"runband_ymbase_20261023_{kind}_{inst}_1.00{sfx}.csv"


def window(d, lo, hi):
    return d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi) & (d.entry < CUTOFF)]


def main():
    jobs = {j["kind"]: j for j in json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))["jobs"]}
    for kind in ("control", "red_nocap", "rtl"):
        mode = "control" if kind == "control" else "rtl"
        ensure_audited(RUN, {**jobs[kind], "mode": mode}, {"symbol": SYMBOL, "grid_points": TICK}, PV, fix_risk=True)
        a = json.loads((RUN / f"{jobs[kind]['tag']}.ledger_audit.json").read_text(encoding="utf-8"))
        print(f"audit {kind}: {a['raw_trades']:,} raw + {a['recovered_trades']} recovered")
    led = {k: load(RUN / j["outputs"][0]) for k, j in jobs.items()}
    for k in ("control", "red_nocap", "rtl"):
        led[k] = load(RUN / f"runband_{jobs[k]['tag']}_1.00_audited.csv")
    print("$ per point from ledgers:", {k: point_value(d) for k, d in led.items()})
    same = len(led["red_nocap"]) == len(led["rtl"]) and np.allclose(
        led["red_nocap"].sort_values("entry_time").trade_profit.values, led["rtl"].sort_values("entry_time").trade_profit.values)
    print(f"Signal EA mode 0 reproduces RTL_runband on RTY ({len(led['rtl']):,} trades): {same}")
    for day in ("2020.03.16", "2025.11.28"):
        print(f"RTL trades on {day} (data gap): {(led['rtl'].entry_time.str[:10] == day).sum()}")

    pd.set_option("display.width", 250)
    fmt = lambda x: f"{x:,.3f}"
    rows = []
    for s in NAMES:
        for lab, lo, hi in WINDOWS:
            rows.append({"strategy": NAMES[s], "window": lab, "inst": "RTY", **summary(window(led[s], lo, hi), PV)})
            if lab == "2017H2":
                continue
            for inst, (_, pv) in OTHER.items():
                d = load(other_path(s, inst, audited=(s == "rtl")))
                rows.append({"strategy": NAMES[s], "window": lab, "inst": inst.upper(), **summary(window(d, lo, hi), pv)})
    t = pd.DataFrame(rows)
    t.to_csv(RUN / "summary.csv", index=False)
    print("\n" + t.to_string(index=False, float_format=fmt))

    d = led["rtl"][led["rtl"].entry < CUTOFF]
    yr = {NAMES[s]: (led[s][led[s].entry < CUTOFF].trade_profit - COST).groupby(led[s].entry.dt.year).sum() for s in NAMES}
    y = pd.DataFrame(yr)
    print("\nRTY net $ by year\n" + y.round(0).to_string())

    rng = np.random.default_rng(20261023)
    rows = []
    for lab, lo, hi in WINDOWS[1:]:
        sets = {"RTY": (led["rtl"], led["control"], PV)}
        for inst, (_, pv) in OTHER.items():
            sets[inst.upper()] = (load(other_path("rtl", inst, True)), load(other_path("control", inst, True)), pv)
        for inst, (a, b, pv) in sets.items():
            a, b = window(a, lo, hi), window(b, lo, hi)
            g, glo, ghi = edge_over_control(a, b, pv, rng)
            rows.append({"window": lab, "inst": inst, "rtl_R": (a.trade_profit / (a.candle_range * pv)).mean(),
                         "ctrl_R": (b.trade_profit / (b.candle_range * pv)).mean(), "gain_R": g, "gain_lo": glo,
                         "gain_hi": ghi})
    c = pd.DataFrame(rows)
    c.to_csv(RUN / "control.csv", index=False)
    print("\nBuy-stop gain over plain long\n" + c.to_string(index=False, float_format=fmt))

    rows = []
    for era, lo, hi in (("2018-26", 2018, 2026),):
        a, b = window(led["rtl"], lo, hi), window(led["control"], lo, hi)
        a = a.assign(bk=pd.cut(a.candle_range / TICK, BINS, labels=LABELS, right=False))
        b = b.assign(bk=pd.cut(b.candle_range / TICK, BINS, labels=LABELS, right=False))
        print(f"\nRTY median RTL candle {era}: {(a.candle_range / TICK).median():.0f} ticks")
        for lab in LABELS:
            x, z = a[a.bk == lab], b[b.bk == lab]
            if min(len(x), len(z)) < 200:
                continue
            g, glo, ghi = edge_over_control(x, z, PV, rng)
            rows.append({"ticks": lab, "rtl_trades": len(x), "rtl_R": (x.trade_profit / (x.candle_range * PV)).mean(),
                         "ctrl_R": (z.trade_profit / (z.candle_range * PV)).mean(), "gain_R": g, "gain_lo": glo,
                         "gain_hi": ghi, "cost_R": (COST / (x.candle_range * PV)).mean()})
    k = pd.DataFrame(rows)
    k.to_csv(RUN / "ticks_buckets.csv", index=False)
    print("RTY by candle size in ticks\n" + k.to_string(index=False, float_format=fmt))

    rows = []
    h1_paths = {"RTY": (RUN / f"runband_{jobs['rtl_h1']['tag']}_1.00.csv", TICK, PV)}
    for inst, (tick, pv) in OTHER.items():
        h1_paths[inst.upper()] = (OTHER_H1[inst], tick, pv)
    for inst, (path, tick, pv) in h1_paths.items():
        m30 = led["rtl"] if inst == "RTY" else load(other_path("rtl", inst.lower(), True))
        for tf, d in (("M30", m30), ("H1", load(path))):
            for lab, lo, hi in WINDOWS[1:]:
                p = window(d, lo, hi)
                net = p.trade_profit - COST
                rows.append({"inst": inst, "tf": tf, "window": lab, "trades": len(p),
                             "med_ticks": (p.candle_range / tick).median(),
                             "gross_R": (p.trade_profit / (p.candle_range * pv)).mean(),
                             "cost_R": (COST / (p.candle_range * pv)).mean(), "net_$": net.sum(),
                             "PF_net": net[net > 0].sum() / -net[net < 0].sum(),
                             "overnight": int((d.exit.dt.normalize() != d.entry.dt.normalize()).sum())})
    h = pd.DataFrame(rows)
    h.to_csv(RUN / "m30_vs_h1.csv", index=False)
    print("\nRTL M30 versus H1\n" + h.to_string(index=False, float_format=fmt))
    h1 = load(h1_paths["RTY"][0])
    h1 = h1[h1.entry < CUTOFF]
    print("\nRTY H1 net $ by year\n" + (h1.trade_profit - COST).groupby(h1.entry.dt.year).sum().round(0).to_string())


if __name__ == "__main__":
    main()
