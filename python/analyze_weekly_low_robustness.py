"""Q13: audit time/event/trade concentration of Q12 previous-week-low contact."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_broad_support import verify_manifest
from analyze_price_levels import ROOT, PERIODS, sha256

UPSTREAM = ROOT / "Reports/levels/broad_support_20261004"
Q10 = ROOT / "Reports/levels/support_interaction_20261003"
STUDY = ROOT / "Reports/levels/weekly_low_robustness_20261004"
PROTOCOL = ROOT / "docs/levels/WEEKLY_LOW_ROBUSTNESS_PROTOCOL.md"
SEED = 20261004


def monday(times):
    return times.dt.normalize() - pd.to_timedelta(times.dt.dayofweek, unit="D")


def identify_events(f):
    """Source week + contract defines a level; signal week is the resampling cluster."""
    f = f.copy()
    f["active_week"] = monday(f.signal_time)
    f["source_week"] = monday(f.source_start)
    f["weekly_event"] = f.source_week.dt.strftime("%Y%m%d") + "_" + f.signal_contract.astype("Int64").astype(str)
    eligible = f.status == "eligible"
    assert (f.loc[eligible, "active_week"] - f.loc[eligible, "source_week"] == pd.Timedelta(days=7)).all()
    assert (f.loc[eligible, "source_end"] < f.loc[eligible, "signal_time"]).all()
    f.loc[~eligible, "weekly_event"] = pd.NA
    return f


def metrics(f):
    gains, losses = f.net.clip(lower=0).sum(), -f.net.clip(upper=0).sum()
    return dict(fills=len(f), net=float(f.net.sum()), sum_r=float(f.net_r.sum()),
                mean_r=float(f.net_r.mean()) if len(f) else None,
                median_r=float(f.net_r.median()) if len(f) else None,
                pf=float(gains / losses) if losses else None,
                win_rate=float((f.net > 0).mean()) if len(f) else None)


def comparison(a, b):
    x, y = metrics(a), metrics(b)
    diff = lambda k: x[k] - y[k] if x[k] is not None and y[k] is not None else None
    return dict(candidate=x, complement=y, mean_r_difference=diff("mean_r"), pf_difference=diff("pf"))


def trimmed_mean(values, fraction):
    x = np.sort(np.asarray(values, dtype=float))
    k = int(len(x) * fraction)
    return float(x[k:len(x) - k].mean()) if len(x) else None


def omit_time(a, b, column, value):
    """Delete the same calendar unit from both populations."""
    return comparison(a[a[column] != value], b[b[column] != value])


def bootstrap_weeks(a, b, start, end, repeats=5000):
    start, end = pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(days=1)
    first = start.normalize() - pd.Timedelta(days=start.dayofweek)
    last = end.normalize() - pd.Timedelta(days=end.dayofweek)
    weeks = pd.date_range(first, last, freq="7D")
    draws = np.random.default_rng(SEED).integers(0, len(weeks), size=(repeats, len(weeks)))
    estimates = []
    for f in (a, b):
        x = pd.DataFrame(dict(week=f.active_week, gains=f.net.clip(lower=0), losses=-f.net.clip(upper=0),
                              net_r=f.net_r, count=1))
        blocks = x.groupby("week").sum().reindex(weeks, fill_value=0).to_numpy()
        v = blocks[draws].sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            estimates.append(dict(pf=v[:, 0] / v[:, 1], mean_r=v[:, 2] / v[:, 3]))
    out = dict(calendar_weeks=len(weeks), resamples=repeats)
    for key in ("pf", "mean_r"):
        delta = estimates[0][key] - estimates[1][key]
        delta = delta[np.isfinite(delta)]
        lo, hi = np.quantile(delta, [.025, .975])
        out[key] = dict(lower=float(lo), upper=float(hi), valid_resamples=len(delta))
    return out


def load():
    manifest = UPSTREAM / "provenance.json"
    inputs = verify_manifest(manifest)
    outputs = json.loads(manifest.read_text())["outputs"]
    for item in outputs:
        if sha256(item["path"]) != item["sha256"]:
            raise ValueError(f"Changed Q12 output: {item['path']}")
    s = pd.read_csv(UPSTREAM / "signals.csv", parse_dates=["signal_time", "submission_time"])
    s = s[s.config == "previous_week"].copy()
    t = pd.read_csv(UPSTREAM / "trades.csv", parse_dates=["signal_time", "submission_time", "entry_time", "exit_time"])
    t = t[t.config == "previous_week"].copy()
    q = pd.read_csv(Q10 / "potential_signals.csv", parse_dates=["source_start", "source_end"])
    q = q[q.source == "previous_week"]
    columns = ["event_id", "source_start", "source_end", "signal_contract", "status", "low"]
    s = identify_events(s.merge(q[columns], on="event_id", validate="one_to_one"))
    expected = (s.status == "eligible") & (s.signal_low <= s.low) & (s.signal_high >= s.low)
    assert np.array_equal(expected, s.group == "contact")
    assert np.allclose(s.level, s.low, equal_nan=True)
    assert len(s) == 52070 and s.baseline_attempt.sum() == 35632 and len(t) == s.filled.sum() == 14968
    assert set(t.event_id) == set(s.loc[s.filled, "event_id"])
    metadata = ["event_id", "active_week", "source_week", "weekly_event", "signal_contract"]
    t = t.merge(s[metadata], on="event_id", validate="one_to_one")
    original = json.loads((UPSTREAM / "contrasts.json").read_text())
    for period, count in (("train", 101), ("recent", 175)):
        a = t[(t.period == period) & (t.group == "contact")]
        assert len(a) == count and a.weekly_event.notna().all()
        ref = next(x["candidate_metrics"] for x in original if x["config"] == "previous_week" and x["period"] == period)
        m = metrics(a)
        assert abs(m["net"] - ref["net"]) < 1e-8
        assert abs(m["mean_r"] - ref["avg_net_r"]) < 1e-12
        assert abs(m["pf"] - ref["pf"]) < 1e-12
    assert (t.groupby("weekly_event").active_week.nunique() <= 1).all()
    return s, t, dict(input_hashes=inputs, output_hashes=len(outputs), potentials=len(s), fills=len(t), contacts=276)


def event_table(s, t):
    rows = []
    for (period, event), c in s[s.group == "contact"].groupby(["period", "weekly_event"]):
        f = t[(t.period == period) & (t.weekly_event == event) & (t.group == "contact")]
        rest = t[(t.period == period) & (t.group != "contact")]
        same_week = rest[rest.active_week == c.active_week.iloc[0]]
        m = metrics(f)
        rows.append(dict(period=period, weekly_event=event, active_week=c.active_week.iloc[0],
                         source_week=c.source_week.iloc[0], contract=int(c.signal_contract.iloc[0]),
                         level=float(c.low.iloc[0]), potential_signals=len(c), attempts=int(c.baseline_attempt.sum()),
                         excess_r=m["sum_r"] - len(f) * rest.net_r.mean(),
                         same_week_rest_fills=len(same_week), same_week_rest_mean_r=same_week.net_r.mean(),
                         same_week_mean_r_difference=f.net_r.mean() - same_week.net_r.mean(), **m))
        assert c.low.nunique() == 1 and len(f) == c.filled.sum()
    return pd.DataFrame(rows)


def concentration(a, b, events, period):
    rows = []
    for unit, frame, key, ks in (("trade", a, "event_id", (1, 5, 10, 20)),
                                ("weekly_event", events, "weekly_event", (1, 3, 5, 10))):
        for rank in ("net", "net_r" if unit == "trade" else "sum_r"):
            positive = frame[frame[rank] > 0].sort_values([rank, key], ascending=[False, True])
            gross_positive = positive[rank].sum()
            total = frame[rank].sum()
            for k in ks:
                top = positive.head(k)
                removed = a[a[key].isin(top[key])]
                left = a[~a[key].isin(top[key])]
                value = float(top[rank].sum())
                rows.append(dict(period=period, unit=unit, ranking=rank, requested_k=k, removed_units=len(top),
                                 removed_trades=len(removed), contribution=value,
                                 share_gross_positive=value / gross_positive if gross_positive else None,
                                 share_total_net=value / total if total else None,
                                 removed_net=float(removed.net.sum()), removed_sum_r=float(removed.net_r.sum()),
                                 removed_excess_r=float(removed.excess_r.sum()),
                                 remainder=comparison(left, b), ids=top[key].tolist()))
    return rows


def main():
    s, t, audit = load()
    print("Verified Q12 population and hashes:", audit, flush=True)
    rest_means = t[t.group != "contact"].groupby("period").net_r.mean()
    t["excess_r"] = t.net_r - t.period.map(rest_means)
    events = event_table(s, t)
    # No observed event crosses the train/recent split; never silently double-count one.
    assert events.weekly_event.is_unique
    summaries, years, omissions, weeks, trims, tops = [], [], [], [], [], []
    for period in ("train", "recent", "pooled"):
        f = t if period == "pooled" else t[t.period == period]
        e = events if period == "pooled" else events[events.period == period]
        a, b = f[f.group == "contact"], f[f.group != "contact"]
        filled_events = e[e.fills > 0]
        paired = filled_events[filled_events.same_week_rest_fills > 0]
        assert filled_events.fills.sum() == len(a)
        assert abs(filled_events.net.sum() - a.net.sum()) < 1e-8
        assert abs(filled_events.sum_r.sum() - a.net_r.sum()) < 1e-10
        start, end = PERIODS[period] if period != "pooled" else (PERIODS["train"][0], PERIODS["recent"][1])
        summary = dict(period=period, **comparison(a, b), potential_contact_events=len(e),
                       filled_events=len(filled_events), single_trade_events=int((filled_events.fills == 1).sum()),
                       max_trades_per_event=int(filled_events.fills.max()),
                       median_trades_per_event=float(filled_events.fills.median()),
                       trades_in_repeat_events=int(filled_events.loc[filled_events.fills > 1, "fills"].sum()),
                       positive_dollar_events=int((filled_events.net > 0).sum()),
                       positive_r_events=int((filled_events.sum_r > 0).sum()),
                       equal_event_mean_r=float(filled_events.mean_r.mean()),
                       equal_event_same_week_difference=float(paired.same_week_mean_r_difference.mean()),
                       paired_events=len(paired), paired_positive=int((paired.same_week_mean_r_difference > 0).sum()),
                       total_excess_r=float(a.excess_r.sum()), bootstrap=bootstrap_weeks(a, b, start, end))
        summaries.append(summary)
        for year in sorted(f.year.unique()):
            ay, by = a[a.year == year], b[b.year == year]
            if period != "pooled":
                years.append(dict(period=period, year=int(year), filled_events=ay.weekly_event.nunique(),
                                  excess_r=float(ay.excess_r.sum()), **comparison(ay, by)))
            omissions.append(dict(period=period, omitted_year=int(year), **omit_time(a, b, "year", year)))
        for week in sorted(a.active_week.unique()):
            weeks.append(dict(period=period, omitted_week=str(pd.Timestamp(week).date()),
                              **omit_time(a, b, "active_week", week)))
        for fraction in (0, .05, .10):
            x, y = trimmed_mean(a.net_r, fraction), trimmed_mean(b.net_r, fraction)
            trims.append(dict(period=period, per_tail=fraction, candidate_mean_r=x, complement_mean_r=y,
                              difference=x-y, candidate_removed_each_tail=int(len(a)*fraction),
                              complement_removed_each_tail=int(len(b)*fraction)))
        tops += concentration(a, b, filled_events, period)
    STUDY.mkdir(parents=True, exist_ok=True)
    events.to_csv(STUDY / "weekly_events.csv", index=False)
    t[t.group == "contact"].sort_values("signal_time").to_csv(STUDY / "contact_trades.csv", index=False)
    audit.update(weekly_events_with_signals=len(events), weekly_events_with_fills=int((events.fills > 0).sum()),
                 yearly_rows=len(years), year_deletions=len(omissions), week_deletions=len(weeks))
    outputs = dict(summary=summaries, yearly=years, leave_one_year_out=omissions,
                   leave_one_week_out=weeks, trimmed=trims, concentration=tops, verification=audit)
    for name, data in outputs.items():
        (STUDY / f"{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    # Flat copies make the detailed sensitivity tables easy to inspect.
    for name, data in outputs.items():
        if isinstance(data, list):
            pd.json_normalize(data).to_csv(STUDY / f"{name}.csv", index=False)
    paths = [UPSTREAM / "provenance.json", UPSTREAM / "signals.csv", UPSTREAM / "trades.csv",
             UPSTREAM / "contrasts.json", Q10 / "potential_signals.csv", PROTOCOL, Path(__file__),
             ROOT / "python/test_weekly_low_robustness.py", ROOT / "python/analyze_broad_support.py",
             ROOT / "python/analyze_price_levels.py"]
    prov = dict(seed=SEED, files=[dict(path=str(p), sha256=sha256(p)) for p in paths],
                outputs=[dict(path=str(p), sha256=sha256(p)) for p in sorted(STUDY.iterdir())
                         if p.name != "provenance.json" and p.is_file()])
    (STUDY / "provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
