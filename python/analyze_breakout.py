"""Q18 stage 1: horizontal swing-high breakout versus every other RTL signal.

Frozen protocol: docs/levels/BREAKOUT_PROTOCOL.md. Reuses Q10's original-exit census,
attempts and fills (hash-verified); no new MT5 run. Outputs Reports/levels/breakout_20261004/.
Broad contact is context only (not a candidate).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

import level_resistance as lr
from analyze_broad_support import verify_manifest
from analyze_level_visit import M30, Q10, TOTALS, contrast, decide, load
from analyze_price_levels import PERIODS, sha256
from analyze_support_interaction import drawdown_interval, trade_metrics
from trend_regimes import ROLLS

ROOT = Path(__file__).absolute().parent.parent
STUDY = ROOT / "Reports" / "levels" / "breakout_20261004"
PROTOCOL = ROOT / "docs" / "levels" / "BREAKOUT_PROTOCOL.md"
CONFIGS = {"week_n5": (5, 5), "two_weeks_n5": (5, 10), "week_n3": (3, 5)}
PRIMARY = "week_n5"
GROUPS, UNAVAILABLE = lr.GROUPS, lr.UNAVAILABLE
QUESTIONS = {"breakout": ("breakout_test",), "broad": lr.BROAD}
LABELS = {"breakout": ("all", "candidate", "every_other", "available_other", "unavailable") + GROUPS[1:5],
          "broad": ("all", "candidate", "every_other", "available_no_contact", "unavailable")}


def classify_all(census, bars):
    m = lr.mirror(bars)
    frames = []
    for name, (n, sessions) in CONFIGS.items():
        pivots = lr.swing_highs(bars.high.to_numpy(), bars.contract.to_numpy(), n)
        rows = []
        for k in census.bar.to_numpy():
            group, info = lr.classify(m, k, n, sessions, pivots)
            rows.append(dict(group=group, **info))
        f = pd.concat([census.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
        f["config"] = name
        f["broad_contact"] = f.group.isin(lr.BROAD)
        frames.append(f)
        print(name, f.group.value_counts().to_dict(), flush=True)
    out = pd.concat(frames, ignore_index=True)
    out["level_time"] = bars.index[out.t0.fillna(0).astype(int)].where(out.t0.notna())
    out["level_age_hours"] = (out.signal_time - out.level_time).dt.total_seconds() / 3600
    out["signal_low_holds"] = out.signal_low >= out.level - out.d  # broken group: retest held from above
    return out, 0


def member(f, question, label):
    inside = f.group.isin(QUESTIONS[question])
    if label == "all":
        return pd.Series(True, index=f.index)
    if label == "candidate":
        return inside
    if label == "every_other":
        return ~inside
    if label == "available_other":
        return ~inside & ~f.group.isin(UNAVAILABLE)
    if label == "available_no_contact":
        return f.group == "no_contact"
    if label == "unavailable":
        return f.group.isin(UNAVAILABLE)
    return f.group == label


def analyse(f, trades):
    t_all = f[f.filled].merge(trades, on="event_id", validate="many_to_one")
    rows, contrasts, partitions = [], [], 0
    for config in CONFIGS:
        for period in PERIODS:
            cc = f[(f.config == config) & (f.period == period)]
            tt = t_all[(t_all.config == config) & (t_all.period == period)].sort_values("exit_time")
            potentials, fills, net = TOTALS[period]
            assert len(cc) == potentials and len(tt) == fills and abs(tt.net.sum() - net) < .01
            assert cc.event_id.is_unique and tt.event_id.is_unique
            assert np.allclose(tt.net_r, tt.net / (2 * tt.candle_range))
            masks = [cc.group == g for g in GROUPS]
            assert sum(int(x.sum()) for x in masks) == len(cc)
            assert sum(int(cc.loc[x, "baseline_attempt"].sum()) for x in masks) == int(cc.baseline_attempt.sum())
            dd, peak, trough = drawdown_interval(tt.net)
            dd_events = set(tt.iloc[peak:trough].event_id)
            for question, labels in LABELS.items():
                x, y = tt[member(tt, question, "candidate")], tt[member(tt, question, "every_other")]
                assert len(x) + len(y) == len(tt) and abs(x.net.sum() + y.net.sum() - tt.net.sum()) < 1e-6
                partitions += 1
                for year in ["all"] + sorted(cc.year.unique().tolist()):
                    cy, ty = (v if year == "all" else v[v.year == year] for v in (cc, tt))
                    for label in labels:
                        cg, tg = cy[member(cy, question, label)], ty[member(ty, question, label)]
                        attempts = int(cg.baseline_attempt.sum())
                        assert len(tg) == int(cg.filled.sum())
                        rows.append(dict(question=question, config=config, period=period, year=year, group=label,
                                         potential_signals=len(cg), attempts=attempts,
                                         conversion=len(tg) / attempts if attempts else None,
                                         baseline_dd=dd if year == "all" else None,
                                         baseline_dd_net_contribution=float(tg[tg.event_id.isin(dd_events)].net.sum())
                                         if year == "all" else None, **trade_metrics(tg)))
                yearly = [dict(year=int(yr), candidate=trade_metrics(x[x.year == yr]),
                               complement=trade_metrics(y[y.year == yr])) for yr in sorted(cc.year.unique())]
                item = dict(question=question, config=config, period=period, candidate_metrics=trade_metrics(x),
                            complement_metrics=trade_metrics(y), differences=contrast(x, y, period), yearly=yearly)
                if question == "broad":
                    item["available_no_contact_differences"] = contrast(x, tt[member(tt, question, "available_no_contact")], period)
                contrasts.append(item)
    return rows, contrasts, t_all, partitions


def descriptive(t_all):
    t = t_all[t_all.config == PRIMARY].copy()
    c = t[t.group == "breakout_test"].copy()
    c["entry_vs_level"] = np.where(c.poke_a >= 0, "entry at/above L (fill = strict break)", "entry below L")
    c["poke_bin"] = pd.cut(c.poke_a, [-0.5, -0.25, 0, 0.25, 0.5], include_lowest=True,
                           labels=["high 0.25-0.5A below", "high <=0.25A below", "high <=0.25A above", "high 0.25-0.5A above"])
    c["age_bin"] = pd.cut(c.level_age_hours, [0, 24, 72, np.inf], labels=["<1 day", "1-3 days", ">3 days"])
    c["members_bin"] = np.where(c.members > 1, "merged (2+ highs)", "single high")
    c["false_breakouts"] = np.where(c.closes_above_since > 0, "closed above L before", "no close above L before")
    rows = []
    for label in ("entry_vs_level", "poke_bin", "opens_above", "age_bin", "members_bin", "false_breakouts"):
        for value, g in c.groupby(label, observed=True):
            for period, gp in g.groupby("period"):
                rows.append(dict(group="breakout_test", label=label, value=str(value), period=period, **trade_metrics(gp)))
    b = t[t.group == "broken_upward_contact"].copy()
    b["retest"] = np.where(b.signal_low_holds, "true retest (low >= L - D)", "fell back through")
    for value, g in b.groupby("retest"):
        for period, gp in g.groupby("period"):
            rows.append(dict(group="broken_upward_contact", label="retest", value=value, period=period, **trade_metrics(gp)))
    return rows


def report(rows, contrasts, decisions, coverage):
    g = pd.DataFrame(rows)
    fmt = lambda v, d=3: "n/a" if v is None or pd.isna(v) else f"{v:,.{d}f}"
    lines = ["# Q18 stage 1: horizontal swing-high breakout, generated results", "",
             "Original RTL exit, $1.05 round trip. Level source: confirmed M30 swing highs (N bars each side) "
             "in a rolling window, merged within D. Existing-fill attribution. Broad contact is context only.", "",
             "| Question | Config | Period | Group | Potential | Attempts | Fills | Conv % | Net $ | PF | Avg net R | Win % |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in g[g.year == "all"].itertuples():
        lines.append(f"| {r.question} | {r.config} | {r.period} | {r.group} | {r.potential_signals} | {r.attempts} | "
                     f"{r.fills} | {fmt(100 * r.conversion if r.conversion else None, 1)} | {fmt(r.net, 2)} | {fmt(r.pf)} | "
                     f"{fmt(r.avg_net_r)} | {fmt(100 * r.win_rate if r.win_rate is not None else None, 1)} |")
    lines += ["", "| Question | Config | Period | Comparator | PF diff [95%] | Avg R diff [95%] |", "|---|---|---|---|---:|---:|"]
    for c in contrasts:
        for field, name in (("differences", "every other"), ("available_no_contact_differences", "available no contact")):
            if field in c:
                d = c[field]
                lines.append(f"| {c['question']} | {c['config']} | {c['period']} | {name} | {fmt(d['pf']['difference'])} "
                             f"[{fmt(d['pf']['lower'])}, {fmt(d['pf']['upper'])}] | {fmt(d['avg_net_r']['difference'])} "
                             f"[{fmt(d['avg_net_r']['lower'])}, {fmt(d['avg_net_r']['upper'])}] |")
    lines += ["", "Decisions:", "", "```json", json.dumps(decisions, indent=2), "```", "",
              "Coverage (potential signals by group):", "", "```", coverage.to_string(), "```", ""]
    (STUDY / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    manifests = [Q10 / "provenance.json", ROOT / "Reports/levels/level_visit_20261004/provenance.json"]
    counts = {str(p): verify_manifest(p) for p in manifests}
    print("Upstream hashes verified:", counts, flush=True)
    census, trades, bars, _, _ = load()
    print("Classifying every potential signal (three fixed settings)...", flush=True)
    f, checked = classify_all(census, bars)
    coverage = f.groupby(["config", "period", "group"]).size().unstack("group", fill_value=0)
    print("Comparing outcomes...", flush=True)
    rows, contrasts, t_all, partitions = analyse(f, trades)
    decisions = {q: decide([c for c in contrasts if c["question"] == q]) for q in QUESTIONS}
    f.drop(columns=["bar"]).to_csv(STUDY / "signals.csv", index=False)
    coverage.to_csv(STUDY / "coverage.csv")
    t_all.drop(columns=["bar"]).to_csv(STUDY / "trades.csv", index=False)
    pd.DataFrame(rows).to_csv(STUDY / "groups.csv", index=False)
    pd.DataFrame(descriptive(t_all)).to_csv(STUDY / "candidate_labels.csv", index=False)
    verification = dict(manifest_entries=counts, partitions_reconciled=partitions,
                        potential_signals=len(census), attempts=int(census.baseline_attempt.sum()), fills=len(trades))
    for name, obj in (("contrasts", contrasts), ("decision", decisions), ("verification", verification)):
        (STUDY / f"{name}.json").write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
    report(rows, contrasts, decisions, coverage)
    paths = manifests + [Q10 / "potential_signals.csv", Q10 / "trades.csv", M30, ROLLS, PROTOCOL]
    paths += [ROOT / "python" / p for p in ("analyze_breakout.py", "level_resistance.py", "test_level_resistance.py",
              "level_visit.py", "trendline_resistance.py", "analyze_level_visit.py", "analyze_broad_support.py",
              "analyze_support_interaction.py", "analyze_price_levels.py")]
    prov = dict(seed=20261004, files=[dict(path=str(p), sha256=sha256(p)) for p in paths])
    prov["outputs"] = [dict(path=str(p), sha256=sha256(p)) for p in sorted(STUDY.iterdir())
                       if p.is_file() and p.name != "provenance.json"]
    (STUDY / "provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(json.dumps(decisions, indent=2))


if __name__ == "__main__":
    main()
