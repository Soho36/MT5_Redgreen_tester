"""Baseline trade paths (descriptive, 2026-10-10): what price does between entry and exit.

Input: Reports/trade_paths_20261010 (prepare_trade_paths.py): the unchanged baseline plus a passive log of every
tester quote while a position is open. Levels are in R = signal-candle range, measured from the fill price.
A level counts as reached when a quote is at or beyond it (how the tester triggers an order resting there).

Checks: the ledger is byte-identical to the saved baseline; one path per ledger trade, in order; fill minus stop
equals the logged risk; path highs/lows reproduce the ledger's MFE/MAE on every trade; non-stop exits end on the
last quote; "touched +1R, later back at the entry" reproduces the trades the break-even run cut.

Usage: python analyze_trade_paths.py
"""

import json

import numpy as np
import pandas as pd

from analyze_instrument_baseline import load
from analyze_price_levels import sha256
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports" / "trade_paths_20261010"
TAG = "paths_20261010_baseline"
BASELINE = ROOT / "Reports" / "instrument_baseline_20261008" / "runband_instbase_20261008_mnq_1.00.csv"
BE_RUN = ROOT / "Reports" / "breakeven_20261010" / "runband_be_20261010_1r_1.00.csv"
PV = 2.0
BAR_MS = 1_800_000
UP = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
DOWN = (0.25, 0.5, 0.75)
PERIODS = (("2016-19", 2016, 2019), ("2020-26", 2020, 2026), ("2016-26", 2016, 2026))
RECORD = np.dtype([("ticket", "<i8"), ("t", "<i8"), ("p", "<f8")])


def first(mask):
    i = int(np.argmax(mask))
    return i if mask[i] else -1


def build_features(rec, led):
    """One row per trade from its quote path (plus the exit fill as the last point)."""
    cut = np.flatnonzero(np.diff(rec["ticket"])) + 1
    starts, ends = np.concatenate([[0], cut]), np.concatenate([cut, [len(rec)]])
    assert len(starts) == len(led) and np.array_equal(rec["ticket"][starts], led.ticket.to_numpy()), "paths vs ledger"
    assert (rec["t"][starts] == -1).all() and (rec["t"][starts + 1] == -2).all(), "path headers"
    fill, stop = rec["p"][starts], rec["p"][starts + 1]
    risk = fill - stop
    assert np.array_equal(risk, led.candle_range.to_numpy()), "fill minus stop differs from the logged risk"
    profit = led.trade_profit.to_numpy()
    exit_price = fill + profit / PV
    entry_ms = led.entry.to_numpy().astype("datetime64[ms]").astype("int64")
    exit_ms = led.exit.to_numpy().astype("datetime64[ms]").astype("int64")
    stopped = exit_price == stop
    assert (exit_price >= stop).all(), "an exit below the stop price"

    rows = []
    for i, (a, b) in enumerate(zip(starts, ends)):
        t, d = rec["t"][a + 2:b], rec["p"][a + 2:b] - fill[i]      # d: quote minus fill, exact (0.25 grid)
        assert t[0] == entry_ms[i], (i, "first quote is not the entry tick")
        if not stopped[i]:
            assert t[-1] == exit_ms[i] and d[-1] == exit_price[i] - fill[i], (i, "non-stop exit is not the last quote")
        bars_seen = np.unique(t // BAR_MS)
        t = np.append(t, exit_ms[i])
        d = np.append(d, exit_price[i] - fill[i])
        k, bar = risk[i], t // BAR_MS
        row = {"mfe": d.max() / k, "mae": d.min() / k, "bars": len(np.unique(bar)), "entry_tick_r": d[0] / k,
               "minutes": (exit_ms[i] - entry_ms[i]) / 60000, "same_bar_exit": bar[-1] == bar[0]}
        before_exit_bar = bar < bar[-1]
        prev_close = d[before_exit_bar][-1] if before_exit_bar.any() else -np.inf
        row["kind"] = "stop" if stopped[i] else ("target" if prev_close >= k else "flatten")
        for level in UP:
            j = first(d >= level * k)
            row[f"up{level}"] = j >= 0
            row[f"up{level}_i"] = j
            row[f"up{level}_back"] = j >= 0 and bool((d[j + 1:] <= 0).any())
            if level == 1.0:
                row["touch_min"] = (t[j] - entry_ms[i]) / 60000 if j >= 0 else np.nan
                row["low_before_touch"] = d[:j + 1].min() / k if j >= 0 else np.nan
                row["low_after_touch"] = d[j:].min() / k if j >= 0 else np.nan
                row["touch_in_entry_bar"] = j >= 0 and bar[j] == bar[0]
                # exit at the first bar open after the touch bar = the touch bar itself closed at or above +1R
                later = bars_seen[bars_seen > bar[j]] if j >= 0 else bars_seen[:0]
                row["exit_after_touch_bar"] = j >= 0 and len(later) > 0 and bar[-1] == later[0]
        for level in DOWN:
            j = first(d <= -level * k)
            row[f"dn{level}"] = j >= 0
            row[f"dn{level}_i"] = j
            row[f"dn{level}_back"] = j >= 0 and bool((d[j + 1:] >= 0).any())
        rows.append(row)
    f = pd.DataFrame(rows)
    f["final"] = profit / (risk * PV)
    for col in ("ticket", "entry_time", "exit_time", "candle_range", "trade_profit", "mfe_money", "mae_money"):
        f[col] = led[col].to_numpy()
    f["year"] = led.entry.dt.year.to_numpy()
    reached = np.maximum(f.mfe * risk * PV, profit), np.minimum(f.mae * risk * PV, profit)
    assert np.allclose(reached[0], f.mfe_money, atol=1e-9) and np.allclose(reached[1], f.mae_money, atol=1e-9), "MFE/MAE"
    return f


def check_against_breakeven(f):
    """Independent run: the break-even EA cut exactly the trades that touched +1R and later quoted at/below entry."""
    be = load(BE_RUN)
    m = f.merge(be, on="entry_time", suffixes=("", "_be"))
    changed = (m.exit_time != m.exit_time_be) | ~np.isclose(m.trade_profit, m.trade_profit_be)
    predicted = m["up1.0_back"]
    # a path that ends exactly at the entry price on its own exit tick is "back" here but unchanged there
    edge = predicted & ~changed & (m.trade_profit == 0)
    assert (predicted == (changed | edge)).all(), "path 'back at entry' set differs from the break-even run"
    assert (m["up1.0"] == m.be_time.notna()).all(), "+1R touch differs from the break-even run's stop moves"
    return int(changed.sum()), int(edge.sum()), len(m)


def pct(x):
    return 100 * float(np.mean(x)) if len(x) else float("nan")


def follow(g, n, level=0.0):
    """What follows for the trades in g; +/- = rough 95% range of the mean, treating trades as independent."""
    return {"n": len(g), "of_all%": 100 * len(g) / n, "then_stop%": pct(g.kind == "stop"),
            "then_profit%": pct(g.final > 0), "mean_final_R": g.final.mean(),
            "holding_from_there": g.final.mean() - level, "+/-": 1.96 * g.final.std() / np.sqrt(len(g))}


LOW_EDGES = [-np.inf, 1e-9, 0.25, 0.5, 0.75, 1.0000001]   # on minus the lowest point, in R
LOW_LABELS = ["never below entry", "0..-0.25R", "-0.25..-0.5R", "-0.5..-0.75R", "-0.75..-1R"]


def bucket_table(values, edges, labels, extra=None):
    g = pd.cut(values, edges, labels=labels, right=False)
    t = pd.DataFrame({"n": values.groupby(g, observed=False).size()})
    t["share%"] = 100 * t.n / len(values)
    if extra is not None:
        t["mean_final_R"] = extra.groupby(g, observed=False).mean()
    return t


def show(title, table, fmt="{:,.2f}"):
    print(f"\n  {title}")
    print("     " + table.to_string(float_format=lambda x: fmt.format(x)).replace("\n", "\n     "))


def report(f, label):
    out = {}
    n = len(f)
    print(f"\n{'=' * 100}\n{label}: {n:,} baseline trades, mean final R {f.final.mean():+.3f} before costs")
    stop, target, flat = f.kind == "stop", f.kind == "target", f.kind == "flatten"
    touch = f["up1.0"]

    t = pd.DataFrame({"n": f.groupby("kind").size(), "share%": 100 * f.groupby("kind").size() / n,
                      "mean_R": f.groupby("kind").final.mean(), "median_min": f.groupby("kind").minutes.median(),
                      "median_bars": f.groupby("kind").bars.median(), "sum_R": f.groupby("kind").final.sum()})
    show("1. How trades end (stop = original stop; target = exit after a bar closing >= +1R; flatten = session end)", t)
    out["endings"] = t.to_dict("index")

    rows = []
    def add(name, mask, parent=None):
        g = f[mask]
        rows.append({"path": name, "n": len(g), "of_all%": 100 * len(g) / n,
                     "of_parent%": 100 * len(g) / parent.sum() if parent is not None else np.nan,
                     "mean_R": g.final.mean(), "sum_R": g.final.sum()})
    add("never touches +1R", ~touch)
    add("  -> stopped", ~touch & stop, ~touch)
    add("  -> session end with a profit", ~touch & flat & (f.final > 0), ~touch)
    add("  -> session end with a loss or flat", ~touch & flat & (f.final <= 0), ~touch)
    add("touches +1R", touch)
    back, same = f["up1.0_back"], target & f.exit_after_touch_bar   # same: the touch bar itself closes >= +1R
    add("  -> never back at entry", touch & ~back, touch)
    add("       -> the touch bar closes >= +1R: exit", touch & ~back & same, touch & ~back)
    add("       -> a later bar closes >= +1R: exit", touch & ~back & target & ~same, touch & ~back)
    add("       -> session end", touch & ~back & flat, touch & ~back)
    add("  -> back at entry", back, touch)
    add("       -> stopped", back & stop, back)
    add("       -> a bar closes >= +1R: exit", back & target, back)
    add("       -> session end", back & flat, back)
    tree = pd.DataFrame(rows).set_index("path")
    assert (~touch & target).sum() == 0 and (touch & ~back & stop).sum() == 0
    show("2. The path tree", tree)
    out["tree"] = tree.reset_index().to_dict("records")   # branch names repeat under different parents

    s = f[stop]
    t = bucket_table(s.mfe, [-1e-9, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, np.inf],
                     ["under +0.1R", "+0.1..0.25R", "+0.25..0.5R", "+0.5..0.75R", "+0.75..1R", "+1..1.5R", "+1.5..2R", "+2R or more"])
    t["cum%"] = t["share%"].cumsum()
    show(f"3. Stopped trades ({len(s):,}): the highest point they reached first", t)
    out["stopped_by_high"] = t.to_dict("index")
    out["stopped_in_entry_bar%"] = pct(s.same_bar_exit)
    print(f"     stopped inside the entry's own M30 bar: {out['stopped_in_entry_bar%']:.1f}% ; median minutes to the stop {s.minutes.median():.0f}")

    w = f[target]
    t = bucket_table(-w.mae, LOW_EDGES, LOW_LABELS, w.final)
    t["cum%"] = t["share%"].cumsum()
    assert t.n.sum() == len(w)
    show(f"4a. Winning exits ({len(w):,}): the lowest point of the trade", t)
    out["winners_by_low"] = t.to_dict("index")
    t = bucket_table(w.final, [-np.inf, 1, 1.25, 1.5, 2, 3, 5, np.inf],
                     ["under +1R", "+1..1.25R", "+1.25..1.5R", "+1.5..2R", "+2..3R", "+3..5R", "+5R or more"])
    t["sum_R"] = w.final.groupby(pd.cut(w.final, [-np.inf, 1, 1.25, 1.5, 2, 3, 5, np.inf], labels=t.index, right=False),
                                 observed=False).sum()
    t["sum_R%"] = 100 * t.sum_R / w.final.sum()
    show("4b. Winning exits: final result", t)
    out["winners_by_final"] = t.to_dict("index")
    give = w.mfe - w.final
    out["winners"] = {"mean_final": w.final.mean(), "median_final": w.final.median(), "mean_peak": w.mfe.mean(),
                      "mean_giveback": give.mean(), "median_giveback": give.median(),
                      "exit_at_touch_bar_close%": pct(w.exit_after_touch_bar), "median_minutes": w.minutes.median()}
    print(f"     winners: final mean {w.final.mean():+.2f}R median {w.final.median():+.2f}R; best point mean {w.mfe.mean():+.2f}R; "
          f"given back from the best point mean {give.mean():.2f}R median {give.median():.2f}R; "
          f"{pct(w.exit_after_touch_bar):.1f}% exit at the close of the touch bar")

    rows = [{"level": f"-{level}R", **follow(f[f[f"dn{level}"]], n, -level)} for level in DOWN[::-1]]
    rows += [{"level": f"+{level}R", **follow(f[f[f"up{level}"]], n, level)} for level in UP]
    t = pd.DataFrame(rows).set_index("level")
    show("5. Level map: the first time price is at a level, what follows (holding = mean final R minus the level)", t, "{:,.3f}")
    out["level_map"] = t.to_dict("index")

    rows = []
    for name, levels in (("up", UP[:6]), ("dn", DOWN)):
        for level in levels:
            reach, back = f[f"{name}{level}"], f[f"{name}{level}_back"]
            rows.append({"first": f"{'up to +' if name == 'up' else 'down to -'}{level}R",
                         "of_those_reaching%": 100 * back.sum() / reach.sum(), **follow(f[back], n)})
    t = pd.DataFrame(rows).set_index("first")
    show("6. Back at the entry price after an excursion: what follows (holding = mean final R, the entry is 0)", t, "{:,.3f}")
    out["back_at_entry"] = t.to_dict("index")

    rows = []
    for level in DOWN:
        up_i, dn_i = f[f"up{level}_i"], f[f"dn{level}_i"]
        up_first = (up_i >= 0) & ((dn_i < 0) | (up_i < dn_i))
        dn_first = (dn_i >= 0) & ((up_i < 0) | (dn_i < up_i))
        rows.append({"first move": f"+{level}R before -{level}R", **follow(f[up_first], n, level)})
        rows.append({"first move": f"-{level}R before +{level}R", **follow(f[dn_first], n, -level)})
        rows.append({"first move": f"neither +/-{level}R", **follow(f[~up_first & ~dn_first], n)})
    t = pd.DataFrame(rows).set_index("first move")
    show("8. The first move: which side is reached first, and what follows", t, "{:,.3f}")
    out["first_move"] = t.to_dict("index")

    tt = f[touch]
    t = bucket_table(-tt.low_before_touch, LOW_EDGES, LOW_LABELS, tt.final)
    assert t.n.sum() == len(tt)
    show(f"7. Trades that touch +1R ({len(tt):,}): the lowest point before the touch", t)
    out["touch_low_before"] = t.to_dict("index")
    out["touch"] = {"median_minutes_to_touch": tt.touch_min.median(), "touch_in_entry_bar%": pct(tt.touch_in_entry_bar),
                    "at_entry_tick%": pct(tt.touch_min == 0)}
    print(f"     median minutes from entry to the +1R touch {tt.touch_min.median():.0f}; touch inside the entry's own bar "
          f"{pct(tt.touch_in_entry_bar):.1f}%; already at +1R on the entry tick {pct(tt.touch_min == 0):.1f}%")
    return out


def main():
    ledger_path = RUN / f"runband_{TAG}_1.00.csv"
    assert sha256(ledger_path) == sha256(BASELINE), "this run is not the saved baseline"
    led = load(ledger_path)
    rec = np.fromfile(RUN / f"ticks_{TAG}.bin", dtype=RECORD)
    f = build_features(rec, led)
    cut, edge, shared = check_against_breakeven(f)
    print(f"PASS: ledger byte-identical to the saved baseline; {len(f):,} paths ({len(rec) - 2 * len(f):,} quotes) in ledger "
          f"order; path highs and lows reproduce the ledger's MFE and MAE on every trade.")
    print(f"PASS: against the separate break-even run ({shared:,} shared trades): the same +1R touches, and "
          f"'touched +1R, later back at entry' = the {cut:,} trades it cut (+{edge} ending exactly at entry on their own exit).")
    f.to_csv(RUN / "trade_features.csv", index=False)
    pd.set_option("display.width", 250)
    res = {label: report(f[(f.year >= lo) & (f.year <= hi)], label) for label, lo, hi in PERIODS}
    (RUN / "results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
