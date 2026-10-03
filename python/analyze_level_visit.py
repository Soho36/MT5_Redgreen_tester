"""Q11: intact one-week M30 swing-low support versus every other RTL signal.

Frozen protocol (with pre-outcome amendment): docs/LEVEL_VISIT_PROTOCOL.md.
Reuses Q10's original-exit census, attempts and fills; no new MT5 run.
Outputs Reports/levels/level_visit_20261004/.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_price_levels import PERIODS, sha256
from analyze_support_interaction import drawdown_interval, trade_metrics
from level_visit import GROUPS, UNAVAILABLE, bar_frame, classify, swing_lows
from trend_regimes import ROLLS

ROOT = Path(__file__).absolute().parent.parent
Q10 = ROOT / "Reports" / "levels" / "support_interaction_20261003"
M30 = ROOT / "Reports" / "levels" / "breach_reclaim_20261003" / "m30_reference.csv"
STUDY = ROOT / "Reports" / "levels" / "level_visit_20261004"
PROTOCOL = ROOT / "docs" / "LEVEL_VISIT_PROTOCOL.md"
CONFIGS = {"week_n5": (5, 5), "two_weeks_n5": (5, 10), "week_n3": (3, 5)}
PRIMARY = "week_n5"
SEED = 20261004
Q10_INTERACTION = ("touch_only", "breach_reclaim", "breach_unrecovered", "breach_exact_close")
TOTALS = {"train": (19624, 5697, 6485.15), "recent": (32446, 9271, 37980.95)}


def load():
    prov = json.loads((Q10 / "provenance.json").read_text())
    checked = 0
    for item in prov["files"]:
        if Path(item["path"]).exists():
            checked += sha256(item["path"]) == item["sha256"]
    census = pd.read_csv(Q10 / "potential_signals.csv", parse_dates=["signal_time", "submission_time"])
    weekly = census[(census.source == "previous_week") & census.group.isin(Q10_INTERACTION)].event_id
    census = census.drop_duplicates("event_id").copy()
    census["q10_previous_week_interaction"] = census.event_id.isin(weekly)
    keep = ["event_id", "signal_time", "submission_time", "signal_open", "signal_high", "signal_low", "signal_close",
            "red_run", "candle_range", "period", "year", "baseline_attempt", "filled", "q10_previous_week_interaction"]
    census = census[keep].reset_index(drop=True)
    trades = pd.read_csv(Q10 / "trades.csv", parse_dates=["signal_time", "entry_time", "exit_time"])
    trades = trades.drop_duplicates("event_id")[["event_id", "entry_time", "exit_time", "net", "net_r", "exit_class",
                                                  "mae_money", "mfe_money"]]
    for period, (potentials, fills, net) in TOTALS.items():
        c = census[census.period == period]
        assert len(c) == potentials, (period, len(c))
        t = trades[trades.event_id.isin(c.event_id)]
        assert len(t) == fills == int(c.filled.sum()), (period, len(t))
        assert abs(t.net.sum() - net) < 0.01, (period, t.net.sum())
    assert int(census.baseline_attempt.sum()) == 35632 and len(trades) == 14968
    bars = bar_frame(pd.read_csv(M30, index_col=0, parse_dates=[0]), pd.read_csv(ROLLS))
    census["bar"] = bars.index.get_indexer(census.signal_time)
    assert (census.bar >= 0).all()
    for col in ("open", "high", "low", "close"):
        assert np.allclose(bars[col].to_numpy()[census.bar], census[f"signal_{col}"]), col
    return census, trades, bars, checked, len(prov["files"])


def classify_all(census, bars):
    frames = []
    for name, (n, sessions) in CONFIGS.items():
        pivots = swing_lows(bars.low.to_numpy(), bars.contract.to_numpy(), n)
        rows = []
        for k in census.bar.to_numpy():
            group, info = classify(bars, k, n=n, sessions=sessions, pivots=pivots)
            rows.append(dict(group=group, **info))
        f = pd.concat([census.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
        f["config"] = name
        frames.append(f)
        print(name, f.group.value_counts().to_dict(), flush=True)
    out = pd.concat(frames, ignore_index=True)
    out["level_time"] = bars.index[out.t0.fillna(0).astype(int)].where(out.t0.notna())
    out["level_age_hours"] = (out.signal_time - out.level_time).dt.total_seconds() / 3600
    return out


def membership(f, label):
    if label == "all":
        return pd.Series(True, index=f.index)
    if label == "candidate":
        return f.group == "support_revisit"
    if label == "every_other":
        return f.group != "support_revisit"
    if label == "available_other":
        return (f.group != "support_revisit") & ~f.group.isin(UNAVAILABLE)
    if label == "unavailable":
        return f.group.isin(UNAVAILABLE)
    return f.group == label


LABELS = ("all", "candidate", "every_other", "available_other", "unavailable") + GROUPS


def contrast(a, b, period):
    start, end = PERIODS[period]
    months = pd.period_range(pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(days=1), freq="M")
    draws = np.random.default_rng(SEED).integers(0, len(months), size=(2000, len(months)))
    boot, point = [], []
    for t in (a, b):
        f = pd.DataFrame(dict(month=t.exit_time.dt.to_period("M"), gains=t.net.clip(lower=0),
                              losses=-t.net.clip(upper=0), net_r=t.net_r, count=1))
        blocks = f.groupby("month")[["gains", "losses", "net_r", "count"]].sum().reindex(months, fill_value=0).to_numpy()
        sampled = blocks[draws].sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            boot.append(dict(pf=sampled[:, 0] / sampled[:, 1], avg_net_r=sampled[:, 2] / sampled[:, 3]))
        point.append(trade_metrics(t))
    out = {}
    for field in ("pf", "avg_net_r"):
        ok = np.isfinite(boot[0][field]) & np.isfinite(boot[1][field])
        delta = boot[0][field][ok] - boot[1][field][ok]
        lo, hi = np.quantile(delta, [.025, .975])
        out[field] = dict(difference=point[0][field] - point[1][field], lower=float(lo), upper=float(hi),
                          valid_resamples=int(ok.sum()))
    return out


def analyse(f, trades):
    t_all = f[f.filled].merge(trades, on="event_id", validate="many_to_one")
    rows, contrasts = [], []
    for config in CONFIGS:
        for period in PERIODS:
            cc = f[(f.config == config) & (f.period == period)]
            tt = t_all[(t_all.config == config) & (t_all.period == period)].sort_values("exit_time")
            dd, peak, trough = drawdown_interval(tt.net)
            dd_events = set(tt.iloc[peak:trough].event_id)
            for year in ["all"] + sorted(cc.year.unique().tolist()):
                cy, ty = (x if year == "all" else x[x.year == year] for x in (cc, tt))
                for label in LABELS:
                    cg, tg = cy[membership(cy, label)], ty[membership(ty, label)]
                    attempts = int(cg.baseline_attempt.sum())
                    assert len(tg) == int(cg.filled.sum())
                    rows.append(dict(config=config, period=period, year=year, group=label, potential_signals=len(cg),
                                     attempts=attempts, conversion=len(tg) / attempts if attempts else None,
                                     trade_share=len(tg) / len(ty) if len(ty) else None,
                                     baseline_dd_net_contribution=float(tg[tg.event_id.isin(dd_events)].net.sum())
                                     if year == "all" else None, **trade_metrics(tg)))
            x, y = tt[membership(tt, "candidate")], tt[membership(tt, "every_other")]
            assert len(x) + len(y) == len(tt) and abs(x.net.sum() + y.net.sum() - tt.net.sum()) < 1e-6
            yearly = [dict(year=int(yr), candidate=trade_metrics(x[x.year == yr]), complement=trade_metrics(y[y.year == yr]))
                      for yr in sorted(tt.year.unique())]
            contrasts.append(dict(config=config, period=period, candidate_metrics=trade_metrics(x),
                                  complement_metrics=trade_metrics(y), differences=contrast(x, y, period), yearly=yearly))
    return rows, contrasts, t_all


def decide(contrasts):
    out = {}
    for config in CONFIGS:
        sel = [c for c in contrasts if c["config"] == config]
        enough = all(c[k]["fills"] >= 200 for c in sel for k in ("candidate_metrics", "complement_metrics"))
        profitable = all(c["candidate_metrics"]["pf"] > 1 for c in sel)
        better = all(c["differences"][k]["difference"] > 0 for c in sel for k in ("pf", "avg_net_r"))
        wins = sum(r["candidate"]["fills"] >= 10 and r["complement"]["fills"] >= 10 and
                   r["candidate"]["avg_net_r"] > r["complement"]["avg_net_r"] for c in sel for r in c["yearly"])
        counted = sum(r["candidate"]["fills"] >= 10 and r["complement"]["fills"] >= 10 for c in sel for r in c["yearly"])
        out[config] = dict(enough_trades=enough, profitable_both=profitable, better_both=better,
                           better_years=int(wins), counted_years=int(counted),
                           passes_core_rule=bool(enough and profitable and better and wins >= 7))
    sensitivities_agree = all(out[c]["better_both"] for c in CONFIGS if c != PRIMARY)
    out["primary_full_rerun_candidate"] = bool(out[PRIMARY]["passes_core_rule"] and sensitivities_agree)
    out["sensitivities_point_same_direction"] = bool(sensitivities_agree)
    return out


def descriptive(t_all):
    t = t_all[(t_all.config == PRIMARY) & (t_all.group == "support_revisit")].copy()
    t["depth_bin"] = pd.cut(t.depth_a, [-np.inf, -0.25, 0, 0.25, 0.5], labels=["near miss >0.25A above", "near miss <=0.25A",
                                                                             "undercut <=0.25A", "undercut 0.25-0.5A"])
    t["age_bin"] = pd.cut(t.level_age_hours, [0, 24, 72, np.inf], labels=["<1 day", "1-3 days", ">3 days"])
    t["members_bin"] = np.where(t.members > 1, "merged (2+ lows)", "single low")
    t["closes_below_bin"] = np.where(t.closes_below_since > 0, "closed below L before", "no close below L before")
    rows = []
    for label in ("wick_reaches", "opens_below", "depth_bin", "age_bin", "members_bin", "closes_below_bin",
                  "q10_previous_week_interaction"):
        for value, g in t.groupby(label, observed=True):
            for period, gp in g.groupby("period"):
                rows.append(dict(label=label, value=str(value), period=period, **trade_metrics(gp)))
    return rows


def report(rows, contrasts, decision, coverage):
    g = pd.DataFrame(rows)
    fmt = lambda v, d=3: "n/a" if v is None or pd.isna(v) else f"{v:,.{d}f}"
    lines = ["# Q11: one-week M30 swing-low support versus every other signal", "",
             "Original RTL exit, $1.05 round trip. Level source: confirmed M30 swing lows (N bars each side) "
             "in a rolling window. No filtered-strategy simulation.", "",
             "| Config | Period | Group | Potential | Attempts | Fills | Conv % | Net $ | PF | Avg net R | Win % |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in g[(g.year == "all") & g.group.isin(("all", "candidate", "every_other") + GROUPS[1:])].itertuples():
        lines.append(f"| {r.config} | {r.period} | {r.group} | {r.potential_signals} | {r.attempts} | {r.fills} | "
                     f"{fmt(100 * r.conversion if r.conversion else None, 1)} | {fmt(r.net, 2)} | {fmt(r.pf)} | "
                     f"{fmt(r.avg_net_r)} | {fmt(100 * r.win_rate if r.win_rate is not None else None, 1)} |")
    lines += ["", "| Config | Period | PF diff [95%] | Avg R diff [95%] |", "|---|---|---:|---:|"]
    for c in contrasts:
        d = c["differences"]
        lines.append(f"| {c['config']} | {c['period']} | {fmt(d['pf']['difference'])} [{fmt(d['pf']['lower'])}, "
                     f"{fmt(d['pf']['upper'])}] | {fmt(d['avg_net_r']['difference'])} [{fmt(d['avg_net_r']['lower'])}, "
                     f"{fmt(d['avg_net_r']['upper'])}] |")
    lines += ["", "Decision:", "", "```json", json.dumps(decision, indent=2), "```", "",
              "Coverage (potential signals by group):", "", "```", coverage.to_string(), "```", ""]
    (STUDY / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    print("Loading and verifying Q10 census, attempts and fills...", flush=True)
    census, trades, bars, checked, listed = load()
    print("Classifying every potential signal (three fixed settings)...", flush=True)
    f = classify_all(census, bars)
    f.drop(columns=["bar"]).to_csv(STUDY / "signals.csv", index=False)
    coverage = f.groupby(["config", "period", "group"]).size().unstack("group", fill_value=0)
    coverage.to_csv(STUDY / "coverage.csv")
    print("Comparing outcomes...", flush=True)
    rows, contrasts, t_all = analyse(f, trades)
    decision = decide(contrasts)
    pd.DataFrame(rows).to_csv(STUDY / "groups.csv", index=False)
    pd.DataFrame(descriptive(t_all)).to_csv(STUDY / "candidate_labels.csv", index=False)
    t_all.to_csv(STUDY / "trades.csv", index=False)
    (STUDY / "contrasts.json").write_text(json.dumps(contrasts, indent=2, default=str), encoding="utf-8")
    (STUDY / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    paths = [Q10 / n for n in ("potential_signals.csv", "trades.csv", "provenance.json")] + \
            [M30, ROLLS, PROTOCOL, Path(__file__), ROOT / "python" / "level_visit.py"]
    prov = dict(q10_hashes_matched=checked, q10_hashes_listed=listed, potential_signals=len(census),
                attempts=int(census.baseline_attempt.sum()), fills=len(trades), seed=SEED,
                files=[dict(path=str(p), sha256=sha256(p)) for p in paths])
    (STUDY / "provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    report(rows, contrasts, decision, coverage)
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
