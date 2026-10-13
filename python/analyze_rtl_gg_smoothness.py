"""Is RTL + GG a smoother equity curve than either alone? (2026-10-13, user question; descriptive, no gate)

Both run with no cap (the baseline), as two accounts summed by exit day, net of $1.05 a trade.
Adding the two doubles the size, so dollars are compared at equal size ("Half each" = half of RTL + half of GG)
and the rest uses measures that do not depend on size: share of winning days / weeks / months, mean / st. dev.
(annualised from days), net / drawdown, time under water and losing streaks.
Chart: docs/figures/rtl_gg_underwater.png. Usage: python analyze_rtl_gg_smoothness.py
"""

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from analyze_gg_run_cap import GRID, INK, MUTED, OLD, SURFACE, load_gg
from analyze_instrument_baseline import COST, load, max_dd
from analyze_signal_colour import edge_over_control
from project_paths import PROJECT_ROOT as ROOT

FIGURE = ROOT / "docs" / "figures" / "rtl_gg_underwater.png"
PERIODS = (("2016-19", "2016-01-01", "2020-01-01"), ("2020-26", "2020-01-01", "2026-07-14"))
SERIES = (("RTL", "#2a78d6"), ("GG", "#eb6834"), ("Half each", "#1baf7a"))


def daily():
    rtl, gg = load(OLD / "runband_signal_20261008_red_nocap_1.00_audited.csv"), load_gg(0)
    x = pd.concat([(d.trade_profit - COST).groupby(d.exit.dt.normalize()).sum() for d in (rtl, gg)],
                  axis=1, keys=["RTL", "GG"], sort=True).fillna(0.0)
    x["Both"] = x.RTL + x.GG
    x["Half each"] = x.Both / 2
    return x, rtl, gg


def longest_run(flags):
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def under_water(x):
    """Longest stretch in calendar days from an equity high to the next new high (to the period end if none)."""
    eq = x.cumsum()
    highs = eq[eq >= eq.cummax()].index
    edges = list(highs) + [eq.index[-1]]
    return max((b - a).days for a, b in zip(edges[:-1], edges[1:])) if len(edges) > 1 else 0


def sharpe(x):
    return x.mean() / x.std() * np.sqrt(252)


def measures(x):
    w, m = x.resample("W").sum(), x.resample("ME").sum()
    w = w[w != 0]
    return {"net $": x.sum(), "max DD $": max_dd(x.to_numpy()), "net / DD": x.sum() / max_dd(x.to_numpy()),
            "mean / st.dev (yearly)": sharpe(x), "winning days %": 100 * (x > 0).sum() / (x != 0).sum(),
            "winning weeks %": 100 * (w > 0).mean(), "winning months %": 100 * (m > 0).mean(),
            "losing months": f"{(m < 0).sum()} of {len(m)}", "worst month $": m.min(),
            "worst month / average month": m.min() / m.mean(), "longest losing run, days": longest_run(x[x != 0] < 0),
            "longest losing run, months": longest_run(m < 0), "longest under water, days": under_water(x)}


def both_in_position(rtl, gg, lo, hi):
    """Share of the time RTL holds a position during which GG holds one too."""
    a = rtl[(rtl.entry >= lo) & (rtl.entry < hi)][["entry", "exit"]].to_numpy()
    b = gg[(gg.entry >= lo) & (gg.entry < hi)][["entry", "exit"]].to_numpy()
    j, overlap, hit = 0, pd.Timedelta(0), 0
    for s, e in a:
        while j < len(b) and b[j][1] <= s:
            j += 1
        k, any_overlap = j, False
        while k < len(b) and b[k][0] < e:
            overlap += min(e, b[k][1]) - max(s, b[k][0])
            any_overlap = True
            k += 1
        hit += any_overlap
    return overlap / (a[:, 1] - a[:, 0]).sum(), hit / len(a)


def blocked_split(x, other, rng):
    """Trades of x entered while `other` holds a position (one account would have to skip them) against the rest."""
    oe, ox = other.entry.to_numpy(), other.exit.to_numpy()
    i = np.searchsorted(oe, x.entry.to_numpy(), side="right") - 1
    during = (i >= 0) & (ox[np.clip(i, 0, None)] > x.entry.to_numpy())
    out = []
    for p in (x[during], x[~during]):
        out.append(f"{len(p):,} trades ({100 * len(p) / len(x):.0f}%), net ${(p.trade_profit - COST).sum():,.0f},"
                   f" gross R {(p.trade_profit / (p.candle_range * 2.0)).mean():+.3f}")
    e, lo, hi = edge_over_control(x[during], x[~during], 2.0, rng)
    return out[0], out[1], f"{e:+.3f} [{lo:+.3f}, {hi:+.3f}]"


def plot(x):
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans"], "font.size": 10})
    p = x[x.index >= "2020-01-01"]
    fig, axes = plt.subplots(3, 1, figsize=(11, 6.2), sharex=True, sharey=True, facecolor=SURFACE)
    for ax, (name, colour) in zip(axes, SERIES):
        eq = p[name].cumsum()
        dd = eq - eq.cummax()
        ax.set_facecolor(SURFACE)
        ax.fill_between(dd.index, dd, 0, color=colour, alpha=0.18, lw=0)
        ax.plot(dd.index, dd, color=colour, lw=1.4)
        ax.set_title(f"{name}: deepest {dd.min():,.0f}, longest under water {under_water(p[name])} days", loc="left",
                     color=INK, fontsize=10, fontweight="semibold")
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_axisbelow(True)
        ax.tick_params(colors=MUTED, length=0)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1000:,.0f}k" if v else "0"))
        for s in ax.spines.values():
            s.set_visible(False)
    axes[1].set_ylabel(r"Net \$ below the last equity high", color=MUTED)
    fig.suptitle("Drawdowns at equal size, 2020-01 to 2026-07: RTL, GG, and half of each", x=0.01, ha="left",
                 color=INK, fontsize=12, fontweight="semibold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIGURE, dpi=130, facecolor=SURFACE)
    print(f"\nWrote {FIGURE}")


def main():
    x, rtl, gg = daily()
    pd.set_option("display.width", 250)
    rng = np.random.default_rng(1)
    for name, lo, hi in PERIODS:
        p = x[(x.index >= lo) & (x.index < hi)]
        t = pd.DataFrame({c: measures(p[c]) for c in ("RTL", "GG", "Both", "Half each")})
        print(f"\n{name}  ({len(p)} trading days)\n" + t.to_string(float_format=lambda v: f"{v:,.2f}"))
        corr = {f: p.RTL.resample(f).sum().corr(p.GG.resample(f).sum()) for f in ("D", "W", "ME")}
        print("  correlation RTL vs GG: " + ", ".join(f"{k} {v:+.2f}" for k, v in zip(("daily", "weekly", "monthly"), corr.values())))
        print(f"  st. dev of a day: RTL {p.RTL.std():,.0f}, GG {p.GG.std():,.0f}, half each {p['Half each'].std():,.0f}"
              f" ({100 * (1 - p['Half each'].std() / ((p.RTL.std() + p.GG.std()) / 2)):.0f}% below their average)")
        v = p[["RTL", "GG", "Both"]].to_numpy()
        idx = rng.integers(0, len(v), (4000, len(v)))
        s = v[idx].mean(1) / v[idx].std(1) * np.sqrt(252)             # resampling days jointly
        for i, c in enumerate(("RTL", "GG")):
            d = s[:, 2] - s[:, i]
            print(f"  mean / st.dev, both minus {c}: {sharpe(p.Both) - sharpe(p[c]):+.2f}"
                  f" [{np.percentile(d, 2.5):+.2f}, {np.percentile(d, 97.5):+.2f}]")
        share, hit = both_in_position(rtl, gg, pd.Timestamp(lo), pd.Timestamp(hi))
        print(f"  while RTL is in a trade, GG is in one too {100 * share:.0f}% of the time;"
              f" {100 * hit:.0f}% of RTL trades overlap a GG trade")
        cut = lambda d: d[(d.entry >= lo) & (d.entry < hi)].reset_index(drop=True)
        for label, a, b in (("GG", cut(gg), cut(rtl)), ("RTL", cut(rtl), cut(gg))):
            during, flat, diff = blocked_split(a, b, rng)
            print(f"  {label} entered while the other is in a trade: {during}\n  {label} entered while the other is flat:"
                  f"       {flat}\n     difference in mean gross R: {diff}")
        both_lose = ((p.RTL < 0) & (p.GG < 0)).sum() / ((p.RTL < 0) | (p.GG < 0)).sum()
        print(f"  on days when at least one loses, both lose on {100 * both_lose:.0f}%;"
              f" RTL's losing days: GG also loses on {100 * ((p.RTL < 0) & (p.GG < 0)).sum() / (p.RTL < 0).sum():.0f}%")
    plot(x)


if __name__ == "__main__":
    main()
