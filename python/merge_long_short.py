# Descriptive check (2026-10-07): merge the RTL long baseline and the Q23 green-candle short mirror
# (identical tester settings) into one equity curve. Exploratory, no gate.
import pandas as pd, numpy as np
R = r"I:\PycharmProjects\MT5_Redgreen_tester\Reports"
L = pd.read_csv(R + r"\trend_rr_20261002\runband_trendrr_20261002_f50_baseline_1.00.csv", sep="\t", encoding="utf-16")
S = pd.read_csv(R + r"\levels\support_breakdown_20261006\runband_support_breakdown_20261006_baseline_1.00.csv", sep="\t", encoding="utf-16")
COST = 1.05
out = {}
for name, d in (("long", L), ("short", S)):
    d = d.copy()
    d["exit"] = pd.to_datetime(d["exit_time"], format="%Y.%m.%d %H:%M:%S")
    d["entry"] = pd.to_datetime(d["entry_time"], format="%Y.%m.%d %H:%M:%S")
    d["net"] = d["trade_profit"] - COST * d["exit_volume"].clip(lower=1)
    print(name, len(d), d["entry"].min(), d["exit"].max(), "dirs", d.get("direction", pd.Series([1])).unique(), "rr", d["assigned_rr"].unique()[:5])
    out[name] = d
L, S = out["long"], out["short"]

# overlap: how often are both in a position at the same time
def intervals(d): return d[["entry", "exit"]].sort_values("entry").to_numpy()
li, si = intervals(L), intervals(S)
j = 0; ov = 0
for a, b in li:
    while j < len(si) and si[j][1] <= a: j += 1
    k = j
    while k < len(si) and si[k][0] < b:
        ov += 1; break
print("long trades overlapping a short in time:", ov, "of", len(li))

daily = pd.DataFrame({
    "long": L.groupby(L["exit"].dt.normalize())["net"].sum(),
    "short": S.groupby(S["exit"].dt.normalize())["net"].sum()}).fillna(0.0)
daily["combo"] = daily["long"] + daily["short"]

def dd(x):
    eq = x.cumsum(); return (eq.cummax() - eq).max()

def table(df, lab):
    rows = []
    for c in ("long", "short", "combo"):
        x = df[c]
        rows.append([lab, c, round(x.sum()), round(dd(x)), round(x.sum() / dd(x), 2) if dd(x) else np.nan])
    return rows

rows = []
for lab, lo, hi in (("2010-15", "2010", "2016-01-01"), ("2016-19", "2016-01-01", "2020-01-01"), ("2020-26", "2020-01-01", "2027"), ("all", "2010", "2027")):
    rows += table(daily[(daily.index >= lo) & (daily.index < hi)], lab)
print(pd.DataFrame(rows, columns=["period", "book", "net$", "maxDD$", "net/DD"]).to_string(index=False))

for f in ("D", "W", "ME", "QE"):
    g = daily.resample(f).sum()
    g = g[(g.long != 0) | (g.short != 0)]
    print(f"corr {f}: all {g.long.corr(g.short):+.3f}  2016+ {g[g.index>='2016'].long.corr(g[g.index>='2016'].short):+.3f}")

y = daily.groupby(daily.index.year).sum().round(0).astype(int)
y["short_offsets_long"] = np.where((y.long < 0) & (y.short > 0), "yes", "")
print(y.to_string())

q = daily.resample("QE").sum()
lq = q[q.long < 0]
print("losing long quarters:", len(lq), " short positive in", (lq.short > 0).sum(), " mean short in them", round(lq.short.mean()))
wq = q[q.long > 0]
print("winning long quarters:", len(wq), " short positive in", (wq.short > 0).sum(), " mean short in them", round(wq.short.mean()))

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(12, 5))
for c, col in (("long", "#2a7"), ("short", "#c44"), ("combo", "#246")):
    ax.plot(daily.index, daily[c].cumsum(), label=c, color=col, lw=1.2)
ax.axhline(0, color="#888", lw=0.6); ax.legend(); ax.set_ylabel(r"cumulative net \$ (1 MNQ, \$1.05 RT)")
ax.set_title("RTL long baseline vs green-candle short mirror, same settings, 2010-06 to 2026-07")
fig.tight_layout(); fig.savefig(r"I:\PycharmProjects\MT5_Redgreen_tester\docs\figures\long_short_equity.png", dpi=110)
