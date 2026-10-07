"""Q19: concentration audit of the Q18 breakout result (Q16 diagnostics).

Protocol: docs/setups/horizontal/resistance-breakout-long/q19-breakout-concentration/PROTOCOL.md. Primary: stage-2 stand-alone trades versus the baseline
full strategy. Secondary: stage-1 attribution versus every other signal. Descriptive only; no MT5 run.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_broad_support import verify_manifest
from analyze_level_visit import load as load_q10
from analyze_price_levels import PERIODS, ROOT, sha256
from analyze_resistance_concentration import concentration, week_frame
from analyze_weekly_low_robustness import bootstrap_weeks, comparison, metrics, monday, omit_time, trimmed_mean
from verify_breakout_gate import load_gate

STAGE1 = ROOT / "Reports/levels/breakout_20261004"
STAGE2 = ROOT / "Reports/levels/breakout_standalone_20261004"
M30 = ROOT / "Reports/levels/breach_reclaim_20261003/m30_reference.csv"
STUDY = ROOT / "Reports/levels/breakout_concentration_20261005"
PROTOCOL = ROOT / "docs/setups/horizontal/resistance-breakout-long/q19-breakout-concentration/PROTOCOL.md"
REF = {"standalone": {"train": (1083, 1742.35), "recent": (1685, 12029.75)},
       "attribution": {"train": (751, 1471.45), "recent": (1181, 8265.45)}}


def level_event(level, t0_time):
    """Level price + latest member time; NA when either is missing."""
    ok = level.notna() & t0_time.notna()
    out = pd.Series(pd.NA, index=level.index, dtype="object")
    out[ok] = level[ok].map(lambda v: f"{v:.2f}") + "@" + t0_time[ok].dt.strftime("%Y%m%d%H%M")
    return out


def prepare(frame):
    f = frame.copy()
    f["active_week"] = monday(f.signal_time)
    f["event_id"] = f.signal_time.dt.strftime("%Y%m%d%H%M")
    return f


def load():
    checked = {str(p): verify_manifest(p) for p in (STAGE1 / "provenance.json", STAGE2 / "provenance.json")}
    for item in json.loads((STAGE1 / "provenance.json").read_text())["outputs"]:
        if sha256(item["path"]) != item["sha256"]:
            raise ValueError(f"Changed stage-1 output: {item['path']}")
    census, base_trades, _, _, _ = load_q10()
    base = census[census.filled].merge(base_trades, on="event_id", validate="one_to_one")
    base = prepare(base[["signal_time", "period", "year", "net", "net_r"]])
    # Stage 2: stand-alone trades with their level identity from the gate log.
    s2 = pd.read_csv(STAGE2 / "standalone_trades.csv", parse_dates=["signal_time", "entry_time", "exit_time"])
    s2 = s2[s2.period.notna()].merge(load_gate("breakout_standalone_20261004_trade")[["signal_time", "t0_time"]],
                                     on="signal_time", validate="one_to_one")
    s2["level_event"] = level_event(s2.level, s2.t0_time)
    s2 = prepare(s2)
    # Stage 1: attribution trades; t0 bar index -> time.
    times = pd.read_csv(M30, usecols=[0], parse_dates=[0]).iloc[:, 0].to_numpy()
    s1 = pd.read_csv(STAGE1 / "trades.csv", parse_dates=["signal_time", "entry_time", "exit_time"])
    s1 = s1[s1.config == "week_n5"].copy()
    has = s1.t0.notna()
    s1["t0_time"] = pd.NaT
    s1.loc[has, "t0_time"] = times[s1.loc[has, "t0"].astype(int).to_numpy()]
    s1["level_event"] = level_event(s1.level, s1.t0_time)
    s1["entry_below_line"] = s1.poke_a < 0
    s1 = prepare(s1)
    pops = {"standalone": (s2, base), "attribution": (s1[s1.group == "breakout_test"], s1[s1.group != "breakout_test"])}
    for name, (a, b) in pops.items():
        for period, (n, net) in REF[name].items():
            x = a[a.period == period]
            assert len(x) == n and abs(x.net.sum() - net) < 0.01, (name, period, len(x), x.net.sum())
            assert x.level_event.notna().all() and (x.t0_time < x.signal_time).all()
    return pops, checked


def event_ledger(a, b):
    week_mean = b.groupby("active_week").net_r.mean()
    rows = []
    for (period, event), f in a.groupby(["period", "level_event"]):
        diff = (f.net_r - f.active_week.map(week_mean)).dropna()
        rows.append(dict(period=period, level_event=event, first_signal=f.signal_time.min(), last_signal=f.signal_time.max(),
                         weeks_spanned=f.active_week.nunique(), same_week_compared=len(diff),
                         same_week_missing=len(f) - len(diff),
                         same_week_mean_r_difference=diff.mean() if len(diff) else None,
                         excess_r=float(f.excess_r.sum()), **metrics(f)))
    return pd.DataFrame(rows)


def audit(name, a, b, label="primary"):
    a, b = a.copy(), b.copy()
    a["excess_r"] = a.net_r - a.period.map(b.groupby("period").net_r.mean())
    events = event_ledger(a, b)
    out = dict(summary=[], yearly=[], leave_one_year_out=[], leave_one_week_out=[], trimmed=[], concentration=[])
    for period in ("train", "recent", "pooled"):
        x = a if period == "pooled" else a[a.period == period]
        y = b if period == "pooled" else b[b.period == period]
        e = events if period == "pooled" else events[events.period == period]
        start, end = PERIODS[period] if period != "pooled" else (PERIODS["train"][0], PERIODS["recent"][1])
        w = week_frame(x)
        assert e.fills.sum() == len(x) and abs(e.net.sum() - x.net.sum()) < 1e-6 and abs(w.net.sum() - x.net.sum()) < 1e-6
        out["summary"].append(dict(
            population=name, label=label, period=period, **comparison(x, y), filled_level_events=len(e),
            single_trade_events=int((e.fills == 1).sum()), max_trades_per_event=int(e.fills.max()),
            trades_in_repeat_events=int(e.loc[e.fills > 1, "fills"].sum()),
            positive_dollar_events=int((e.net > 0).sum()), positive_r_events=int((e.sum_r > 0).sum()),
            equal_event_mean_r=float(e.mean_r.mean()),
            equal_event_same_week_difference=float(e.same_week_mean_r_difference.mean()),
            same_week_positive_events=int((e.same_week_mean_r_difference > 0).sum()),
            same_week_missing_trades=int(e.same_week_missing.sum()), filled_weeks=len(w),
            positive_dollar_weeks=int((w.net > 0).sum()), positive_r_weeks=int((w.sum_r > 0).sum()),
            total_excess_r=float(x.excess_r.sum()), bootstrap=bootstrap_weeks(x, y, start, end)))
        for year in sorted(x.year.unique()):
            xy, yy = x[x.year == year], y[y.year == year]
            if period != "pooled":
                out["yearly"].append(dict(population=name, label=label, period=period, year=int(year),
                                          level_events=xy.level_event.nunique(), excess_r=float(xy.excess_r.sum()),
                                          **comparison(xy, yy)))
            if label == "primary":
                out["leave_one_year_out"].append(dict(population=name, period=period, omitted_year=int(year),
                                                      **omit_time(x, y, "year", year)))
        if label != "primary":
            continue
        for week in sorted(x.active_week.unique()):
            out["leave_one_week_out"].append(dict(population=name, period=period, omitted_week=str(pd.Timestamp(week).date()),
                                                  **omit_time(x, y, "active_week", week)))
        for fraction in (0, .05, .10):
            p, q = trimmed_mean(x.net_r, fraction), trimmed_mean(y.net_r, fraction)
            out["trimmed"].append(dict(population=name, period=period, per_tail=fraction, candidate_mean_r=p,
                                       complement_mean_r=q, difference=p - q))
        trades = x.assign(sum_r=x.net_r)
        for rows in (concentration(x, y, trades, "event_id", ("net", "sum_r"), (1, 5, 10, 20), "trade", period),
                     concentration(x, y, e, "level_event", ("net", "sum_r"), (1, 3, 5, 10), "level_event", period),
                     concentration(x, y, w, "active_week", ("net", "sum_r"), (1, 3, 5, 10), "calendar_week", period)):
            out["concentration"] += [dict(population=name, **r) for r in rows]
    return out, events.assign(population=name)


def main():
    pops, checked = load()
    print("Verified Q18 stage-1/2 hashes:", checked, flush=True)
    results, ledgers = {}, []
    for name, (a, b) in pops.items():
        out, ev = audit(name, a, b)
        narrow, _ = audit(name, a[a.entry_below_line], b, label="secondary_entry_below_level")
        for k in out:
            out[k] += narrow[k]
        for k, v in out.items():
            results.setdefault(k, []).extend(v)
        ledgers.append(ev)
    STUDY.mkdir(parents=True, exist_ok=True)
    pd.concat(ledgers).to_csv(STUDY / "level_events.csv", index=False)
    for name, data in results.items():
        (STUDY / f"{name}.json").write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        pd.json_normalize(data).to_csv(STUDY / f"{name}.csv", index=False)
    (STUDY / "verification.json").write_text(json.dumps(dict(manifests=checked, populations={
        n: {p: len(a[a.period == p]) for p in PERIODS} for n, (a, _) in pops.items()}), indent=2), encoding="utf-8")
    paths = [STAGE1 / "provenance.json", STAGE2 / "provenance.json", STAGE1 / "trades.csv", STAGE2 / "standalone_trades.csv",
             M30, PROTOCOL, Path(__file__), ROOT / "python/analyze_resistance_concentration.py",
             ROOT / "python/analyze_weekly_low_robustness.py"]
    prov = dict(seed=20261004, files=[dict(path=str(p), sha256=sha256(p)) for p in paths],
                outputs=[dict(path=str(p), sha256=sha256(p)) for p in sorted(STUDY.iterdir())
                         if p.is_file() and p.name != "provenance.json"])
    (STUDY / "provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
