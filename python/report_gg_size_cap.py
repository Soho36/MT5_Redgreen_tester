"""Write the verified GG size-cap results and chart."""
import json
import shutil
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, PathPatch
from matplotlib.path import Path as MPath
from prepare_gg_size_cap import RUN, DOC, PRIMARY
from audit_granularity_ledgers import digest

USD = chr(36)
ERAS = ("2016-19", "2020-26")
NAME = {"2010-15": "2010-15 (secondary)", "2016-19": "2016-19", "2020-26": "2020-Sep 2026", "2016-26": "2016-Sep 2026"}
ARMS = {"base": "All entry windows", "ex16": "No entries 16:00-17:00"}
# Categorical slots 1 and 2 of the validated chart palette, light surface; text never wears these.
COLORS = {"base": "#2a78d6", "ex16": "#eb6834"}
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
MONEY = {"net_dollars", "sampled_equity_dd", "worst_session_equity_dd", "max_risk_dollars", "worst_trade", "stress1_net",
         "stress2_net", "net_change", "capped_trades_net", "other_trades_net", "new_trades_net"}
SIGNED_R = {"mean_net_R", "stress1_mean_R", "stress2_mean_R"}


def money(x):
    return f"{'-' if x < 0 else ''}{USD}{abs(x):,.2f}"


def rule(x):
    return "Normal GG" if x == 0 else f"Cap >= {x:g}x"


def table(frame, cols):
    out = ["| " + " | ".join(cols.values()) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in frame.iterrows():
        cells = []
        for c in cols:
            x = r[c]
            if c == "threshold": x = rule(x)
            elif c == "arm": x = ARMS[x]
            elif c == "period": x = NAME.get(str(x), str(x))
            elif c in MONEY: x = money(x)
            elif c in SIGNED_R: x = f"{x:+.4f}"
            elif c in ("net_per_equity_dd", "profit_factor"): x = f"{x:.2f}"
            elif isinstance(x, float): x = f"{x:,.0f}"
            cells.append(str(x))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def cell(s, arm, ratio, era, col):
    return s.loc[s.arm.eq(arm) & s.threshold.eq(ratio) & s.period.eq(era), col].iloc[0]


def screen(s, arm):
    """The protocol's rule: reasons it fails (empty list = met)."""
    fails = []
    for era in ERAS:
        if not cell(s, arm, PRIMARY, era, "sampled_equity_dd") < cell(s, arm, 0, era, "sampled_equity_dd"):
            fails.append(f"{PRIMARY:g}x equity DD is not lower in {NAME[era]}")
        if not cell(s, arm, PRIMARY, era, "net_per_equity_dd") > cell(s, arm, 0, era, "net_per_equity_dd"):
            fails.append(f"{PRIMARY:g}x net/DD is not higher in {NAME[era]}")
        for ratio in sorted(set(s.threshold) - {0, PRIMARY}):
            if cell(s, arm, ratio, era, "net_per_equity_dd") < cell(s, arm, 0, era, "net_per_equity_dd"):
                fails.append(f"{ratio:g}x net/DD is below normal GG in {NAME[era]}")
    return fails


def reading(s, parts):
    """Plain statements computed from the tables and the control ledger, 2020-Sep 2026, all entry windows."""
    era, ratios = "2020-26", sorted(set(s.threshold) - {0})
    change = {r: cell(s, "base", r, era, "net_dollars") - cell(s, "base", 0, era, "net_dollars") for r in ratios}
    ctl = pd.read_csv(RUN / "ggcap_20261111_base_control_trades.csv")
    ctl = ctl.loc[ctl.session.ge("2020-01-01") & ctl.session.lt("2026-10-01")]
    ref = ctl.loc[ctl.prior_count.ge(5)]
    bands = []
    for lo, hi in zip(ratios, ratios[1:] + [float("inf")]):
        b = ref.loc[ref.ratio.ge(lo) & ref.ratio.lt(hi)]
        bands.append(f"{lo:g}x to {hi:g}x" .replace(" to infx", " and more") + f" {money(b.net_dollars.sum())} ({len(b)} trades)")
    big = ctl.loc[ctl.initial_risk_dollars.ge(500)]
    known = big.prior_count.ge(5)
    capped_big = int((known & big.ratio.ge(PRIMARY)).sum())
    large_day = big.loc[known & big.ratio.lt(PRIMARY)]
    same = all(cell(s, "base", r, era, c) == cell(s, "base", 0, era, c) for r in ratios
               for c in ("max_risk_dollars", "worst_trade", "worst_session_equity_dd"))
    d = parts.loc[parts.arm.eq("base") & parts.threshold.eq(PRIMARY) & parts.period.eq(era)].iloc[0]
    text = "## Reading the result\n\nAll figures here are 2020-September 2026 with all entry windows.\n\n"
    text += ("- **Only one threshold looks acceptable.** Net change: " + ", ".join(f"{money(change[r])} at {r:g}x" for r in ratios) +
             ". Normal-GG trades by signal size: " + "; ".join(bands) + ". There is no steady pattern from smaller to larger candles, "
             "so the better result at one threshold reads as a selected cell, not as a property of large candles.\n")
    text += ("- **The cap does not limit the largest bets.** " +
             (f"The largest initial risk ({money(cell(s, 'base', 0, era, 'max_risk_dollars'))}), the worst trade "
              f"({money(cell(s, 'base', 0, era, 'worst_trade'))}) and the worst-session DD "
              f"({money(cell(s, 'base', 0, era, 'worst_session_equity_dd'))}) are the same at every threshold. " if same else "") +
             f"Of {len(big)} normal-GG trades that risked {USD}500 or more, {PRIMARY:g}x removes {capped_big}. "
             f"{len(large_day)} came in sessions whose earlier bars were large too (median range {large_day['median'].median():.0f} points "
             f"against {ref['median'].median():.0f} for a typical trade), and {int((~known).sum())} had fewer than five earlier bars. "
             "A size measured against the session's own bars lets those through.\n")
    text += (f"- **The trades that replace capped ones did worse.** At {PRIMARY:g}x the {int(d.capped_trades_removed)} capped trades had earned "
             f"{money(d.capped_trades_net)}; the {int(d.new_trades)} trades that exist only with the cap earned {money(d.new_trades_net)}.\n")
    return text


def column(ax, x, width, height, color, radius_px=4):
    """Thin column: rounded data end, square at the baseline."""
    inv = ax.transData.inverted()
    (x0, y0), (x1, y1) = inv.transform([(0, 0), (radius_px, radius_px)])
    rx, ry = min(abs(x1 - x0), width / 2), min(abs(y1 - y0), abs(height))
    s = 1 if height >= 0 else -1
    left, right, top = x - width / 2, x + width / 2, height
    verts = [(left, 0), (left, top - s * ry), (left, top), (left + rx, top), (right - rx, top), (right, top),
             (right, top - s * ry), (right, 0), (left, 0)]
    codes = [MPath.MOVETO, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CURVE3, MPath.CURVE3,
             MPath.LINETO, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none", zorder=3))


def chart(s):
    ratios = sorted(set(s.threshold))
    labels = ["Normal"] + [f"Cap {r:g}x" for r in ratios[1:]]
    fig, axs = plt.subplots(2, 2, figsize=(11, 7.2), facecolor=SURFACE)
    fig.subplots_adjust(left=.075, right=.985, top=.8, bottom=.07, hspace=.42, wspace=.16)
    width, shift = .13, .071
    drawn = []
    for col, era in enumerate(ERAS):
        for row, (field, title) in enumerate((("net_dollars", "Net profit"), ("sampled_equity_dd", "Largest equity drawdown"))):
            ax = axs[row, col]
            values = {arm: [cell(s, arm, r, era, field) for r in ratios] for arm in ARMS}
            low = min(0, min(min(v) for v in values.values()))
            high = max(max(v) for v in values.values())
            ax.set_facecolor(SURFACE)
            ax.set_xlim(-.9, len(ratios) - .4)
            ax.set_ylim(low * 1.15, high * 1.2)
            ax.set_xticks(range(len(ratios)), labels)
            ax.set_title(f"{title}, {NAME[era]}", loc="left", fontsize=11, color=INK, pad=8)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: f"{'-' if x < 0 else ''}{USD}{abs(x):,.0f}"))
            ax.grid(axis="y", color=GRID, linewidth=.8, zorder=0)
            ax.set_axisbelow(True)
            for side in ("top", "right", "left"):
                ax.spines[side].set_visible(False)
            ax.spines["bottom"].set_color(AXIS)
            ax.axhline(0, color=AXIS, linewidth=.8, zorder=2)
            ax.tick_params(axis="both", length=0, labelsize=9, labelcolor=MUTED)
            ax.tick_params(axis="x", labelcolor=INK2)
            drawn.append((ax, values))
    fig.canvas.draw()  # fix the layout so a 4-pixel corner radius is known in data units
    for ax, values in drawn:
        for arm, sign in zip(ARMS, (-1, 1)):
            for i, value in enumerate(values[arm]):
                column(ax, i + sign * shift, width, value, COLORS[arm])
        # Direct labels on the primary arm only, beside the bar's end so a taller neighbour cannot cover them;
        # the tables carry the rest.
        for i, value in enumerate(values["base"]):
            ax.annotate(f"{'-' if value < 0 else ''}{USD}{abs(value):,.0f}", (i - shift - width / 2, value), xytext=(-4, -1),
                        textcoords="offset points", ha="right", va="top", fontsize=8.5, color=INK2)
    fig.text(.075, .945, "GG size cap: skip signals several times larger than the session's typical bar",
             fontsize=13.5, color=INK, ha="left")
    fig.text(.075, .908, "One MNQ contract, native MT5 replays, $1.05 per trade. Values shown for all entry windows.",
             fontsize=9.5, color=INK2, ha="left")
    fig.legend(handles=[Patch(facecolor=COLORS[a], edgecolor="none", label=ARMS[a]) for a in ARMS], loc="upper left",
               bbox_to_anchor=(.068, .895), ncols=2, frameon=False, fontsize=9.5, labelcolor=INK2, handlelength=1.1,
               handleheight=.9, columnspacing=1.6)
    (DOC / "img").mkdir(exist_ok=True)
    fig.savefig(DOC / "img/comparison.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)


def main():
    v = json.loads((RUN / "verification.json").read_text())
    assert v["all_passed"] and digest(RUN / "summary.csv") == v["summary_sha256"]
    assert digest(RUN / "decomposition.csv") == v["decomposition_sha256"]
    s = pd.read_csv(RUN / "summary.csv")
    s["period"] = s.period.astype(str)
    parts = pd.read_csv(RUN / "decomposition.csv")
    chart(s)
    fails = screen(s, "base")
    verdict = ("Meets the pre-set screen as a risk rule" if not fails
               else "Does not meet the pre-set screen: " + "; ".join(fails))
    text = (f"# GG size cap on outsized signal candles\n\nCompleted 2026-11-11 under the [frozen protocol](PROTOCOL.md). "
            f"Exploratory.\n\n**{verdict}.**\n\n")
    for era in ERAS:
        g = lambda ratio, col: cell(s, "base", ratio, era, col)
        text += (f"- **{NAME[era]}, {PRIMARY:g}x, all entry windows:** net {money(g(0, 'net_dollars'))} -> {money(g(PRIMARY, 'net_dollars'))}; "
                 f"equity DD {money(g(0, 'sampled_equity_dd'))} -> {money(g(PRIMARY, 'sampled_equity_dd'))}; "
                 f"net/DD {g(0, 'net_per_equity_dd'):.2f} -> {g(PRIMARY, 'net_per_equity_dd'):.2f}; "
                 f"largest single risk {money(g(0, 'max_risk_dollars'))} -> {money(g(PRIMARY, 'max_risk_dollars'))}.\n")
    second = screen(s, "ex16")
    text += ("- **With no entries 16:00-17:00 (secondary):** " +
             ("the same screen is met." if not second else "the same screen is not met: " + "; ".join(second) + ".") + "\n")
    text += reading(s, parts)
    text += f"""
![Net profit and equity drawdown by rule](img/comparison.png)

## Exact test

A green GG signal is rejected when its high-low range (wicks included) is at
least k times the median range of **all earlier M30 candles of the same full
session** (both colours, at least five earlier bars, the signal itself and
later bars excluded). Rejected means what the EA already does for its other
filters: no buy stop is placed and a pending one is cancelled. k = {PRIMARY:g} is
primary; 4 and 6 are the neighbours fixed beforehand. Everything else is normal
GG: entry at the signal high, stop at its low, 1R candle-close exit, 23:30 and
early-close flatten, one MNQ contract, no VWAP gate. $1.05 per completed
position. The primary sample ends before October 1, 2026.

5x was chosen after ledger cuts of this same history, so this is a check of a
selected threshold on reused data. It can show that the idea fails; a pass is
only a reason for a forward trial.

## Results by era
"""
    cols = {"threshold": "Rule", "trades": "Trades", "capped_signals": "Capped signals", "net_dollars": "Net",
            "mean_net_R": "Mean net R", "sampled_equity_dd": "Equity DD", "net_per_equity_dd": "Net/DD",
            "worst_session_equity_dd": "Worst-session DD", "max_risk_dollars": "Largest risk",
            "worst_trade": "Worst trade", "profit_factor": "Net PF"}
    for arm, label in ARMS.items():
        text += f"\n### {label}\n"
        for period in ("2016-19", "2020-26", "2016-26", "2010-15"):
            p = s.loc[s.arm.eq(arm) & s.period.eq(period)].sort_values("threshold")
            text += f"\n**{NAME[period]}**\n\n" + table(p, cols)
    text += """
## Where the profit change comes from

A capped signal removes its own trade. Its absence also changes what happens
next: other control trades disappear and trades appear that the control never
took. The three parts add up to the net change.

"""
    order = {"2016-19": 0, "2020-26": 1, "2016-26": 2}
    p = parts.loc[parts.period.isin(order)].sort_values(["arm", "threshold", "period"], key=lambda c: c.map(order) if c.name == "period" else c)
    text += table(p, {"arm": "Windows", "threshold": "Rule", "period": "Period", "net_change": "Net change",
                      "capped_trades_removed": "Capped trades removed", "capped_trades_net": "Their net",
                      "other_trades_removed": "Other trades gone", "other_trades_net": "Their net",
                      "new_trades": "New trades", "new_trades_net": "Their net"})
    text += f"\n## Cost sensitivity at {PRIMARY:g}x, all entry windows\n\n"
    p = s.loc[s.arm.eq("base") & s.threshold.isin((0, PRIMARY)) & s.period.isin(ERAS)].sort_values(["period", "threshold"])
    text += table(p, {"period": "Period", "threshold": "Rule", "net_dollars": "Net at $1.05", "stress1_net": "Net at $2.05",
                      "stress2_net": "Net at $3.05", "mean_net_R": "Mean net R", "stress1_mean_R": "R at $2.05",
                      "stress2_mean_R": "R at $3.05"})
    text += f"\n## Annual results at {PRIMARY:g}x, all entry windows\n\n"
    years = [str(y) for y in range(2010, 2027)]
    a = s.loc[s.arm.eq("base") & s.threshold.isin((0, PRIMARY)) & s.period.isin(years)]
    wide = a.pivot(index="period", columns="threshold", values=["net_dollars", "sampled_equity_dd", "capped_signals"])
    text += "| Year | Normal net | Cap net | Normal equity DD | Cap equity DD | Capped signals |\n|---|---|---|---|---|---|\n"
    for y in years:
        r = wide.loc[y]
        text += (f"| {y} | {money(r['net_dollars', 0.0])} | {money(r['net_dollars', PRIMARY])} | "
                 f"{money(r['sampled_equity_dd', 0.0])} | {money(r['sampled_equity_dd', PRIMARY])} | "
                 f"{int(r['capped_signals', PRIMARY])} |\n")
    better_net = int((wide["net_dollars", PRIMARY] > wide["net_dollars", 0.0]).sum())
    better_dd = int((wide["sampled_equity_dd", PRIMARY] < wide["sampled_equity_dd", 0.0]).sum())
    main_years = [y for y in years if int(y) >= 2016]
    w = wide.loc[main_years]
    text += (f"\nSince 2016 the cap has the higher net in {int((w['net_dollars', PRIMARY] > w['net_dollars', 0.0]).sum())} of "
             f"{len(main_years)} years and the lower equity DD in {int((w['sampled_equity_dd', PRIMARY] < w['sampled_equity_dd', 0.0]).sum())} "
             f"(all 17 years: {better_net} and {better_dd}).\n")
    text += "\n## Verification and limits\n\n"
    text += f"- Raw minutes checked: {v['raw_minutes']:,}; M30 bars rebuilt: {v['m30_bars']:,}. Compilation: zero errors and warnings.\n"
    for j in v["jobs"]:
        text += (f"- {j['tag']}: {j['decisions']:,} candidate decisions ({j['capped_decisions']:,} capped), all rebuilt from raw minutes; "
                 f"all {j['fills']:,} native trades match the independent minute replay in entry/exit minute, requested/fill/stop/exit "
                 f"price and submission bar; gross equity DD {money(j['native_gross_equity_dd'])} equals MT5's"
                 + ("; ledger byte-identical to the saved run" if j["control_byte_identical"] else "") + ".\n")
    text += """
- No accepted order came from a capped signal. Report, ledger and trade
  economics agree. Trades common to a cap run and its control are identical.
- Equity DD uses marked-to-market equity on generated OHLC quotes, after
  costs. No real-tick or slippage validation. One contract throughout; R is
  not a fixed-dollar sizing model.
- Reused history, and the primary threshold was chosen on it: exploratory, not
  out of sample. No live strategy or default changed.

## Evidence and reproduction

[Protocol](PROTOCOL.md), [prepare](../../../python/prepare_gg_size_cap.py),
[analysis/checks](../../../python/analyze_gg_size_cap.py),
[cap helper](../../../mt5/experts/gg_size_cap_research.mqh),
[tests](../../../python/test_gg_size_cap.py),
[first look](../../../python/explore_gg_session_filters.py).

Reports/gg_size_cap_20261111/ holds the frozen inputs, native reports, ledgers,
decision logs, equity observations and verification.
[Summary CSV](summary.csv), [decomposition](decomposition.csv).

Run with the project venv and MT5 closed: python/prepare_gg_size_cap.py (new
study only), python/run_mt5_job.py Reports/gg_size_cap_20261111 GG_size_cap,
then python/analyze_gg_size_cap.py and python/report_gg_size_cap.py.
"""
    (DOC / "RESULTS.md").write_text(text, encoding="utf-8")
    for name in ("summary.csv", "decomposition.csv"):
        shutil.copyfile(RUN / name, DOC / name)
    print(verdict)


if __name__ == "__main__":
    main()
