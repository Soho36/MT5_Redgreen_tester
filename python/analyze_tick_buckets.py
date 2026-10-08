"""Exploratory (2026-10-08): RTL (red cap 3) vs market-buy control by signal-candle size in ticks, MNQ vs MES, 2016-26.
Gross mean R; "gain" = red minus control. Asks whether ES lags NQ because its candles span fewer ticks.
Usage: python analyze_tick_buckets.py
"""
import pandas as pd
from analyze_instrument_baseline import load
from project_paths import PROJECT_ROOT as ROOT

R = str(ROOT / "Reports")
files = {
    ("NQ", "red"): (R + r"\signal_colour_20261008\runband_signal_20261008_red_cap3_1.00.csv", 2.0),
    ("NQ", "ctrl"): (R + r"\signal_colour_20261008\runband_signal_20261008_market_control_1.00.csv", 2.0),
    ("ES", "red"): (R + r"\signal_colour_20261008_mes\runband_signal_20261008_red_cap3_mes_1.00.csv", 5.0),
    ("ES", "ctrl"): (R + r"\signal_colour_20261008_mes\runband_signal_20261008_market_control_mes_1.00.csv", 5.0),
}
bins = [0, 8, 16, 24, 32, 48, 64, 128, 10000]
labels = ["<8", "8-16", "16-24", "24-32", "32-48", "48-64", "64-128", ">128"]
rows = []
for (sym, run), (f, pv) in files.items():
    d = load(f)
    d = d[d.entry.dt.year >= 2016]
    d["ticks"] = d.candle_range / 0.25
    d["r"] = d.trade_profit / (d.candle_range * pv)
    d["b"] = pd.cut(d.ticks, bins, labels=labels, right=False)
    g = d.groupby("b", observed=True).r.agg(["mean", "size"])
    for b, x in g.iterrows():
        rows.append((sym, run, b, x["mean"], int(x["size"])))
t = pd.DataFrame(rows, columns=["sym", "run", "ticks", "R", "n"])
p = t.pivot_table(index="ticks", columns=["sym", "run"], values=["R", "n"], observed=False).reindex(labels)
for s in ("NQ", "ES"):
    p[("gain", s, "")] = p[("R", s, "red")] - p[("R", s, "ctrl")]
pd.set_option("display.width", 250)
print("2016-2026, gross mean R by signal-candle size in ticks")
print(p.round(3).to_string())
