"""Is YM held back by ticks per candle? Edge and costs by candle size in ticks, and RTL M30 versus H1 (2026-10-23).

1. Ticks per candle: RTL and plain-long control (audited M30 ledgers, prepare_ym_control.py) bucketed by signal candle
   range in ticks (NQ/ES 0.25, YM 1.0). MNQ and MYM both pay $0.50 per tick, so at equal ticks $1.05 costs the
   same R on both. Gain interval resamples days jointly (analyze_signal_colour.edge_over_control).
2. RTL M30 versus H1 on NQ, ES, YM: H1 from prepare_ym_h1.py (YM, ES) and the 2026-10-15 timeframe study (NQ),
   all with the tick-level session cutoff. Gross R, cost in R, net. Trades before 2026-10-01.
Usage: python analyze_ym_h1.py
"""
import numpy as np
import pandas as pd

from analyze_instrument_baseline import COST, load, max_dd
from analyze_signal_colour import edge_over_control
from analyze_ym_baselines import CUTOFF, PERIODS
from project_paths import PROJECT_ROOT as ROOT

REP = ROOT / "Reports"
INST = {"nq": (0.25, 2.0), "es": (0.25, 5.0), "ym": (1.0, 0.5)}   # tick size, $ per point
BINS = [0, 10, 20, 30, 45, 70, 110, np.inf]
LABELS = ["<10", "10-20", "20-30", "30-45", "45-70", "70-110", "110+"]
M30 = {i: REP / "ym_baselines_20261023" / f"runband_ymbase_20261023_rtl_{i}_1.00_audited.csv" for i in INST}
CTRL = {i: REP / "ym_control_20261023" / f"runband_ymctrl_20261023_control_{i}_1.00_audited.csv" for i in INST}
H1 = {"nq": REP / "timeframe_baseline_20261015" / "runband_tf_20261015_rtl_h1_rr1p0_1.00.csv",
      "es": REP / "ym_h1_20261023" / "runband_ymh1_20261023_rtl_h1_es_1.00.csv",
      "ym": REP / "ym_h1_20261023" / "runband_ymh1_20261023_rtl_h1_ym_1.00.csv"}


def r_of(d, pv):
    return d.trade_profit / (d.candle_range * pv)


def ticks_table(rng):
    rows = []
    for inst, (tick, pv) in INST.items():
        rtl, ctrl = load(M30[inst]), load(CTRL[inst])
        for era, lo, hi in (("2016-26", 2016, 2026), ("2010-15", 2010, 2015)):
            def sel(d):
                d = d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi) & (d.entry < CUTOFF)]
                return d.assign(b=pd.cut(d.candle_range / tick, BINS, labels=LABELS, right=False))
            a_all, b_all = sel(rtl), sel(ctrl)
            for lab in LABELS:
                a, b = a_all[a_all.b == lab], b_all[b_all.b == lab]
                if min(len(a), len(b)) < 200:
                    continue
                gain, lo_, hi_ = edge_over_control(a, b, pv, rng)
                rows.append({"era": era, "inst": inst.upper(), "ticks": lab, "rtl_trades": len(a),
                             "rtl_R": r_of(a, pv).mean(), "ctrl_R": r_of(b, pv).mean(), "gain_R": gain,
                             "gain_lo": lo_, "gain_hi": hi_, "cost_R": (COST / (a.candle_range * pv)).mean()})
            print(f"{inst.upper()} {era}: median RTL candle {(a_all.candle_range / tick).median():.0f} ticks")
    return pd.DataFrame(rows)


def timeframe_table():
    rows = []
    for inst, (tick, pv) in INST.items():
        for tf, path in (("M30", M30[inst]), ("H1", H1[inst])):
            d = load(path)
            overnight = int((d.exit.dt.normalize() != d.entry.dt.normalize()).sum())
            for lab, lo, hi in PERIODS:
                p = d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi) & (d.entry < CUTOFF)]
                net = p.trade_profit - COST
                rows.append({"inst": inst.upper(), "tf": tf, "period": lab, "trades": len(p),
                             "med_ticks": (p.candle_range / tick).median(), "gross_R": r_of(p, pv).mean(),
                             "cost_R": (COST / (p.candle_range * pv)).mean(), "net_R": (net / (p.candle_range * pv)).mean(),
                             "gross_$": p.trade_profit.sum(), "net_$": net.sum(),
                             "PF_net": net[net > 0].sum() / -net[net < 0].sum(), "maxDD_$": max_dd(net.to_numpy()),
                             "overnight": overnight})
    return pd.DataFrame(rows)


def main():
    pd.set_option("display.width", 250)
    fmt = lambda x: f"{x:,.3f}"
    t = ticks_table(np.random.default_rng(20261023))
    t.to_csv(REP / "ym_h1_20261023" / "ticks_buckets.csv", index=False)
    for era in ("2016-26", "2010-15"):
        print(f"\nBy candle size in ticks, {era}\n" + t[t.era == era].drop(columns="era").to_string(index=False, float_format=fmt))
    f = timeframe_table()
    f.to_csv(REP / "ym_h1_20261023" / "m30_vs_h1.csv", index=False)
    print("\nRTL M30 versus H1\n" + f.to_string(index=False, float_format=fmt))
    ym = load(H1["ym"])
    ym = ym[ym.entry < CUTOFF]
    yearly = (ym.trade_profit - COST).groupby(ym.entry.dt.year).sum()
    print("\nYM H1 net $ by year\n" + yearly.round(0).to_string())
    print("YM H1 positive years:", int((yearly > 0).sum()), "of", len(yearly))


if __name__ == "__main__":
    main()
