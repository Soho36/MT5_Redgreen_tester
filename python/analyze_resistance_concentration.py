"""Q16: concentration audit of Q15's falling-resistance candidates (Q13 diagnostics).

Protocol: docs/setups/trendlines/downtrend-breakout-long/q16-resistance-concentration/PROTOCOL.md. Descriptive only; no MT5 run.
Outputs Reports/trendlines/resistance_concentration_20261004/.
"""

import json
from pathlib import Path

import pandas as pd

from analyze_broad_support import verify_manifest
from analyze_price_levels import PERIODS, ROOT, sha256
from analyze_weekly_low_robustness import bootstrap_weeks, comparison, metrics, monday, omit_time, trimmed_mean

UPSTREAM = ROOT / "Reports/trendlines/trendline_resistance_20261004"
M30 = ROOT / "Reports/levels/breach_reclaim_20261003/m30_reference.csv"
STUDY = ROOT / "Reports/trendlines/resistance_concentration_20261004"
PROTOCOL = ROOT / "docs/setups/trendlines/downtrend-breakout-long/q16-resistance-concentration/PROTOCOL.md"
CANDIDATE, PRIMARY = "resistance_test", "week_n5"
FILLS = {"train": 412, "recent": 693}


def line_ids(f, times):
    """Line event = the two anchor bar times; NA outside contact groups."""
    f = f.copy()
    has = f.anchor1.notna()
    a1 = pd.Series(pd.NaT, index=f.index, dtype="datetime64[ns]")
    a2 = a1.copy()
    values = pd.Series(times).to_numpy()  # positional lookup; never align on a pandas index
    a1[has] = values[f.loc[has, "anchor1"].astype(int).to_numpy()]
    a2[has] = values[f.loc[has, "anchor2"].astype(int).to_numpy()]
    f["anchor1_time"], f["anchor2_time"] = a1, a2
    assert (f.loc[has, "anchor2_time"] < f.loc[has, "signal_time"]).all()
    assert (f.loc[has, "anchor1_time"] < f.loc[has, "anchor2_time"]).all()
    # Each M30 bar of the continuous reference belongs to one contract, so anchor times identify it.
    f["line_event"] = pd.NA
    f.loc[has, "line_event"] = (f.loc[has, "anchor1_time"].dt.strftime("%Y%m%d%H%M") + "_" +
                                f.loc[has, "anchor2_time"].dt.strftime("%Y%m%d%H%M"))
    f["active_week"] = monday(f.signal_time)
    return f


def load():
    manifest = UPSTREAM / "provenance.json"
    inputs = verify_manifest(manifest)
    outputs = json.loads(manifest.read_text())["outputs"]
    for item in outputs:
        if sha256(item["path"]) != item["sha256"]:
            raise ValueError(f"Changed Q15 output: {item['path']}")
    times = pd.read_csv(M30, usecols=[0], parse_dates=[0]).iloc[:, 0]
    assert times.is_monotonic_increasing and times.is_unique  # same order as level_visit.bar_frame
    s = pd.read_csv(UPSTREAM / "signals.csv", parse_dates=["signal_time"])
    s = s[s.config == PRIMARY].copy()
    t = pd.read_csv(UPSTREAM / "trades.csv", parse_dates=["signal_time", "entry_time", "exit_time"])
    t = t[t.config == PRIMARY].copy()
    assert len(s) == 52070 and len(t) == 14968 == int(s.filled.sum())
    s, t = line_ids(s, times), line_ids(t, times)
    ref = json.loads((UPSTREAM / "contrasts.json").read_text())
    for period, count in FILLS.items():
        a = t[(t.period == period) & (t.group == CANDIDATE)]
        r = next(x["candidate_metrics"] for x in ref
                 if x["question"] == "resistance" and x["config"] == PRIMARY and x["period"] == period)
        m = metrics(a)
        assert len(a) == count and a.line_event.notna().all()
        assert abs(m["net"] - r["net"]) < 1e-8 and abs(m["mean_r"] - r["avg_net_r"]) < 1e-12 and abs(m["pf"] - r["pf"]) < 1e-12
    return s, t, dict(input_hashes=inputs, output_hashes=len(outputs), potentials=len(s), fills=len(t),
                      candidates=sum(FILLS.values()))


def event_table(s, t, rest_week_mean):
    rows = []
    cand = t[t.group == CANDIDATE]
    for (period, event), c in s[s.group == CANDIDATE].groupby(["period", "line_event"]):
        f = cand[(cand.period == period) & (cand.line_event == event)]
        rest_mean = t[(t.period == period) & (t.group != CANDIDATE)].net_r.mean()
        week_diff = (f.net_r - f.active_week.map(rest_week_mean)).dropna()
        m = metrics(f)
        rows.append(dict(period=period, line_event=event, anchor1_time=c.anchor1_time.iloc[0],
                         anchor2_time=c.anchor2_time.iloc[0], first_signal=c.signal_time.min(),
                         last_signal=c.signal_time.max(), weeks_spanned=c.active_week.nunique(),
                         potential_signals=len(c), attempts=int(c.baseline_attempt.sum()),
                         excess_r=m["sum_r"] - len(f) * rest_mean,
                         same_week_compared=len(week_diff), same_week_missing=len(f) - len(week_diff),
                         same_week_mean_r_difference=week_diff.mean() if len(week_diff) else None, **m))
        assert len(f) == int(c.filled.sum())
    return pd.DataFrame(rows)


def concentration(a, b, frame, key, ranks, ks, unit, period):
    """Largest positive units by each ranking: share, removal stress against the fixed complement."""
    rows = []
    for rank in ranks:
        positive = frame[frame[rank] > 0].sort_values([rank, key], ascending=[False, True])
        gross, total = positive[rank].sum(), frame[rank].sum()
        for k in ks:
            top = positive.head(k)
            removed, left = a[a[key].isin(top[key])], a[~a[key].isin(top[key])]
            value = float(top[rank].sum())
            rows.append(dict(period=period, unit=unit, ranking=rank, requested_k=k, removed_units=len(top),
                             removed_trades=len(removed), contribution=value,
                             share_gross_positive=value / gross if gross else None,
                             share_total_net=value / total if total else None,
                             removed_net=float(removed.net.sum()), removed_sum_r=float(removed.net_r.sum()),
                             removed_excess_r=float(removed.excess_r.sum()),
                             remainder=comparison(left, b), ids=[str(x) for x in top[key]]))
    return rows


def week_frame(a):
    g = a.groupby("active_week").agg(net=("net", "sum"), sum_r=("net_r", "sum")).reset_index()
    return g


def audit_population(t, s, events, mask, label):
    """All Q13 diagnostics for candidate trades selected by `mask` versus every other signal."""
    summaries, years, omissions, weeks, trims, tops = [], [], [], [], [], []
    for period in ("train", "recent", "pooled"):
        f = t if period == "pooled" else t[t.period == period]
        a, b = f[mask.loc[f.index]], f[f.group != CANDIDATE]
        start, end = PERIODS[period] if period != "pooled" else (PERIODS["train"][0], PERIODS["recent"][1])
        e = events if period == "pooled" else events[events.period == period]
        e = e[e.line_event.isin(a.line_event)] if label != "primary" else e
        filled = e[e.fills > 0]
        if label == "primary":
            assert filled.fills.sum() == len(a) and abs(filled.net.sum() - a.net.sum()) < 1e-8
            assert abs(filled.sum_r.sum() - a.net_r.sum()) < 1e-10
        w = week_frame(a)
        assert abs(w.net.sum() - a.net.sum()) < 1e-8
        summary = dict(population=label, period=period, **comparison(a, b), filled_line_events=a.line_event.nunique(),
                       filled_weeks=a.active_week.nunique(), total_excess_r=float(a.excess_r.sum()),
                       bootstrap=bootstrap_weeks(a, b, start, end))
        if label == "primary":
            summary.update(single_trade_events=int((filled.fills == 1).sum()),
                           max_trades_per_event=int(filled.fills.max()),
                           trades_in_repeat_events=int(filled.loc[filled.fills > 1, "fills"].sum()),
                           positive_dollar_events=int((filled.net > 0).sum()),
                           positive_r_events=int((filled.sum_r > 0).sum()),
                           equal_event_mean_r=float(filled.mean_r.mean()),
                           equal_event_same_week_difference=float(filled.same_week_mean_r_difference.mean()),
                           same_week_positive_events=int((filled.same_week_mean_r_difference > 0).sum()),
                           same_week_missing_trades=int(filled.same_week_missing.sum()),
                           positive_dollar_weeks=int((w.net > 0).sum()), positive_r_weeks=int((w.sum_r > 0).sum()))
        summaries.append(summary)
        for year in sorted(f.year.unique()):
            ay, by = a[a.year == year], b[b.year == year]
            if period != "pooled":
                years.append(dict(population=label, period=period, year=int(year),
                                  filled_line_events=ay.line_event.nunique(),
                                  excess_r=float(ay.excess_r.sum()), **comparison(ay, by)))
            if label == "primary":
                omissions.append(dict(period=period, omitted_year=int(year), **omit_time(a, b, "year", year)))
        if label != "primary":
            continue
        for week in sorted(a.active_week.unique()):
            weeks.append(dict(period=period, omitted_week=str(pd.Timestamp(week).date()),
                              **omit_time(a, b, "active_week", week)))
        for fraction in (0, .05, .10):
            x, y = trimmed_mean(a.net_r, fraction), trimmed_mean(b.net_r, fraction)
            trims.append(dict(period=period, per_tail=fraction, candidate_mean_r=x, complement_mean_r=y,
                              difference=x - y, candidate_removed_each_tail=int(len(a) * fraction),
                              complement_removed_each_tail=int(len(b) * fraction)))
        trades = a.assign(sum_r=a.net_r)
        tops += concentration(a, b, trades, "event_id", ("net", "sum_r"), (1, 5, 10, 20), "trade", period)
        tops += concentration(a, b, filled, "line_event", ("net", "sum_r"), (1, 3, 5, 10), "line_event", period)
        tops += concentration(a, b, w, "active_week", ("net", "sum_r"), (1, 3, 5, 10), "calendar_week", period)
    return summaries, years, omissions, weeks, trims, tops


def main():
    s, t, audit = load()
    print("Verified Q15 population and hashes:", audit, flush=True)
    rest = t[t.group != CANDIDATE]
    t["excess_r"] = t.net_r - t.period.map(rest.groupby("period").net_r.mean())
    rest_week_mean = rest.groupby("active_week").net_r.mean()
    events = event_table(s, t, rest_week_mean)
    assert not events.duplicated(["period", "line_event"]).any()
    primary = audit_population(t, s, events, t.group == CANDIDATE, "primary")
    narrow = audit_population(t, s, events, (t.group == CANDIDATE) & (t.poke_a < 0), "secondary_entry_below_line")
    STUDY.mkdir(parents=True, exist_ok=True)
    events.to_csv(STUDY / "line_events.csv", index=False)
    t[t.group == CANDIDATE].sort_values("signal_time").to_csv(STUDY / "candidate_trades.csv", index=False)
    names = ("summary", "yearly", "leave_one_year_out", "leave_one_week_out", "trimmed", "concentration")
    outputs = {n: p + q for n, p, q in zip(names, primary, narrow)}
    audit.update(line_events_with_signals=len(events), line_events_with_fills=int((events.fills > 0).sum()),
                 week_deletions=len(outputs["leave_one_week_out"]))
    outputs["verification"] = audit
    for name, data in outputs.items():
        (STUDY / f"{name}.json").write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        if isinstance(data, list):
            pd.json_normalize(data).to_csv(STUDY / f"{name}.csv", index=False)
    paths = [UPSTREAM / "provenance.json", UPSTREAM / "signals.csv", UPSTREAM / "trades.csv", UPSTREAM / "contrasts.json",
             M30, PROTOCOL, Path(__file__), ROOT / "python/test_resistance_concentration.py",
             ROOT / "python/analyze_weekly_low_robustness.py"]
    prov = dict(seed=20261004, files=[dict(path=str(p), sha256=sha256(p)) for p in paths],
                outputs=[dict(path=str(p), sha256=sha256(p)) for p in sorted(STUDY.iterdir())
                         if p.is_file() and p.name != "provenance.json"])
    (STUDY / "provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(json.dumps([x for x in outputs["summary"]], indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
