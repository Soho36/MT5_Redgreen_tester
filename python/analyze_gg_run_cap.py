"""Analyse the GG run-cap train/test (protocol: prepare_gg_run_cap.py) and draw the RTL + GG equity curves.

1. Checks every GG ledger against its MT5 stats, and cap 3 / off against the 2026-10-08 green ledgers.
2. Applies the pre-set rule to 2016-19 (highest gross PF; a tie within 0.005 goes to the larger cap, off = largest),
   then shows the winner against off on 2020-26.
3. RTL + GG as two accounts summed by exit day, like for like (no cap on either) and as adopted
   (RTL cap 3 + GG at the cap this study supports). Chart: docs/figures/rtl_gg_equity.png.
Same R and cost conventions as analyze_signal_colour.py. Usage: python analyze_gg_run_cap.py
"""

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from analyze_instrument_baseline import COST, PERIODS, load, max_dd, summary
from analyze_signal_colour import edge_over_control
from prepare_gg_run_cap import CAPS, STUDY
from project_paths import PROJECT_ROOT as ROOT

OLD = ROOT / "Reports" / "signal_colour_20261008"
FIGURE = ROOT / "docs" / "figures" / "rtl_gg_equity.png"
PV, TIE = 2.0, 0.005
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"
SERIES = (("RTL", "#2a78d6"), ("GG", "#eb6834"), ("Both", "#1baf7a"))   # dataviz reference palette, slots 1-3


def lab(cap):
    return "off" if cap == 0 else str(cap)


def load_gg(cap):
    path = STUDY / f"runband_ggcap_20261013_cap{cap}_1.00.csv"
    d = load(path)
    s = pd.read_csv(path.with_name(path.stem + "_stats.csv"), sep="\t", encoding="utf-16").iloc[0]
    assert len(d) == int(s.trades) and abs(d.trade_profit.sum() - s.net_profit) < 1e-6, (cap, "MT5 stats")
    assert int(s.max_red_run) == cap, (cap, "cap flag")
    return d


def same(a, b):
    return len(a) == len(b) and (a.entry_time.values == b.entry_time.values).all() \
        and np.allclose(a.trade_profit, b.trade_profit)


def period(d, lo, hi):
    return d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi)]


def table(title, runs, lo, hi):
    rows = [{"cap": lab(c), **{k: v for k, v in summary(period(d, lo, hi), PV).items()
                               if k in ("trades", "win%", "gross_R", "net_R", "PF_gross", "PF_net", "net_$", "maxDD_$")}}
            for c, d in sorted(runs.items(), key=lambda kv: (kv[0] == 0, kv[0]))]
    t = pd.DataFrame(rows)
    t["net/DD"] = t["net_$"] / t["maxDD_$"]
    print(f"\n{title}\n" + t.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    return t.set_index("cap")


def daily_net(d):
    return (d.trade_profit - COST).groupby(d.exit.dt.normalize()).sum()


def pair(rtl, gg):
    x = pd.concat([daily_net(rtl), daily_net(gg)], axis=1, keys=["RTL", "GG"], sort=True).fillna(0.0)
    x["Both"] = x.RTL + x.GG
    return x


def pair_table(title, x):
    print(f"\n{title}  (net $ after costs / max DD on daily closes)")
    for name, lo, hi in PERIODS:
        p = x[(x.index.year >= lo) & (x.index.year <= hi)]
        print(f"  {name:8s} " + "  ".join(f"{c}: {p[c].sum():>8,.0f} / {max_dd(p[c].to_numpy()):>6,.0f}" for c in x.columns)
              + f"   daily corr {p.RTL.corr(p.GG):+.2f}")


def plot(panels):
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans"], "font.size": 10})
    fig, axes = plt.subplots(1, len(panels), figsize=(6.6 * len(panels), 5.2), sharey=True, facecolor=SURFACE)
    money = FuncFormatter(lambda v, _: f"{v / 1000:,.0f}k" if v else "0")
    for ax, (title, x) in zip(np.atleast_1d(axes), panels):
        eq = x.cumsum()
        ax.set_facecolor(SURFACE)
        for name, colour in SERIES:
            ax.plot(eq.index, eq[name], color=colour, lw=2 if name == "Both" else 1.6, label=name,
                    solid_joinstyle="round", solid_capstyle="round")
        ends = eq.iloc[-1].sort_values()
        at = ends.to_numpy().copy()
        for i in range(1, len(at)):          # end labels at least 3.5k apart so RTL and GG do not overprint
            at[i] = max(at[i], at[i - 1] + 3500)
        for name, y in zip(ends.index, at):
            ax.annotate(f"{name}  {ends[name] / 1000:,.1f}k", (eq.index[-1], y), xytext=(6, 0),
                        textcoords="offset points", va="center", color=INK, fontsize=9)
        ax.axhline(0, color="#c3c2b7", lw=1)
        ax.set_xticks(pd.to_datetime([f"{y}-01-01" for y in range(2012, 2027, 2)]), [str(y) for y in range(2012, 2027, 2)])
        ax.set_title(title, loc="left", color=INK, fontsize=11, fontweight="semibold")
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_axisbelow(True)
        ax.tick_params(colors=MUTED, length=0)
        ax.yaxis.set_major_formatter(money)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xlim(eq.index[0], eq.index[-1] + pd.Timedelta(days=900))
    np.atleast_1d(axes)[0].set_ylabel(r"Net \$ after \$1.05 a trade, 1 MNQ each", color=MUTED)
    np.atleast_1d(axes)[0].legend(loc="upper left", frameon=False, labelcolor=INK)
    fig.suptitle("RTL and GG as two accounts, MNQ M30, 2010-06 to 2026-07", x=0.01, ha="left", color=INK,
                 fontsize=12, fontweight="semibold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIGURE, dpi=130, facecolor=SURFACE)
    print(f"\nWrote {FIGURE}")


def main():
    gg = {c: load_gg(c) for c in CAPS}
    old = {0: load(OLD / "runband_signal_20261008_green_nocap_1.00.csv"),
           3: load(OLD / "runband_signal_20261008_green_cap3_1.00.csv")}
    print(f"{len(gg)} GG runs reconcile with MT5 stats; caps match.")
    print("Reproduce the 2026-10-08 green ledgers:", {lab(c): same(gg[c], old[c]) for c in old})
    pd.set_option("display.width", 250)

    train = table("TRAIN 2016-19 (selection by gross PF)", gg, 2016, 2019)
    best = train.PF_gross.max()
    tied = [c for c in CAPS if train.PF_gross[lab(c)] >= best - TIE]
    winner = max(tied, key=lambda c: 99 if c == 0 else c)
    print(f"Selection: best gross PF {best:.3f}; within {TIE}: {[lab(c) for c in tied]} -> winner = {lab(winner)}")

    test = table("TEST 2020-26 (winner against off; other caps for reference only)", gg, 2020, 2026)
    w, off = test.loc[lab(winner)], test.loc["off"]
    passes = winner != 0 and w.PF_net > off.PF_net and w["maxDD_$"] < off["maxDD_$"]
    print(f"Winner {lab(winner)} vs off: net PF {w.PF_net:.3f} vs {off.PF_net:.3f}, net DD {w['maxDD_$']:,.0f} vs "
          f"{off['maxDD_$']:,.0f}, net $ {w['net_$']:,.0f} vs {off['net_$']:,.0f} -> {'PASS' if passes else 'no pass'}")
    table("2010-15 (reference)", gg, 2010, 2015)

    rng = np.random.default_rng(1)
    print("\nMean gross R, each cap minus off, 95% interval resampling days jointly:")
    for c in CAPS[1:]:
        cells = []
        for name, lo, hi in PERIODS[1:3]:
            e, elo, ehi = edge_over_control(period(gg[c], lo, hi), period(gg[0], lo, hi), PV, rng)
            cells.append(f"{name} {e:+.3f} [{elo:+.3f}, {ehi:+.3f}]")
        print(f"  cap {c}: " + "   ".join(cells))

    red = {c: load(OLD / f"runband_signal_20261008_red_{n}_1.00_audited.csv") for c, n in ((0, "nocap"), (3, "cap3"))}
    print("\nGG trades by green-run length (off):",
          (gg[0].red_run.clip(upper=5).value_counts(normalize=True).sort_index() * 100).round(1).to_dict())
    print("RTL trades by red-run length (off): ",
          (red[0].red_run.clip(upper=5).value_counts(normalize=True).sort_index() * 100).round(1).to_dict())

    adopted = winner if passes else 0
    like = pair(red[0], gg[0])
    used = pair(red[3], gg[adopted])
    pair_table("LIKE FOR LIKE: RTL off + GG off", like)
    pair_table(f"AS ADOPTED: RTL cap 3 + GG {lab(adopted)}", used)
    pair_table("2026-10-08 table for reference: RTL cap 3 + GG cap 3", pair(red[3], gg[3]))
    plot([("No run cap on either", like), (f"RTL cap 3 (baseline) + GG {'no cap' if adopted == 0 else 'cap ' + lab(adopted)}", used)])


if __name__ == "__main__":
    main()
