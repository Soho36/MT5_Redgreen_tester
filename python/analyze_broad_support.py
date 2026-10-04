"""Q12 broad support-origin contact screen; see docs/levels/BROAD_SUPPORT_PROTOCOL.md."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_level_visit import CONFIGS, Q10, M30, TOTALS, load, contrast, decide
from analyze_price_levels import ROOT, PERIODS, SOURCES, build_level_maps, sha256
from analyze_support_interaction import trade_metrics, drawdown_interval
from broad_support import classify_contact, exact_contact
from level_visit import UNAVAILABLE, swing_lows
from trend_regimes import ROLLS

Q11 = ROOT / "Reports/levels/level_visit_20261004"
STUDY = ROOT / "Reports/levels/broad_support_20261004"
PROTOCOL = ROOT / "docs/levels/BROAD_SUPPORT_PROTOCOL.md"
CONTACT_GROUPS = ("support_revisit", "slice_through", "broken_contact", "not_departed_contact")


def verify_manifest(path):
    """Fail closed, with a useful path, instead of merely counting hash matches."""
    entries = json.loads(Path(path).read_text())["files"]
    for item in entries:
        p = Path(item["path"])
        if not p.is_file():
            raise FileNotFoundError(f"Manifest input missing: {p}")
        if sha256(p) != item["sha256"]:
            raise ValueError(f"Manifest input changed: {p}")
    return len(entries)


def classifications(census, bars):
    frames = []
    old = pd.read_csv(Q11 / "signals.csv", usecols=["event_id", "config", "group"])
    assert not old.duplicated(["event_id", "config"]).any()
    checked = 0
    for config, (n, sessions) in CONFIGS.items():
        pivots = swing_lows(bars.low.to_numpy(), bars.contract.to_numpy(), n)
        f = census.copy()
        f["group"] = [classify_contact(bars, int(s), n, sessions, pivots) for s in f.bar]
        reference = old[old.config == config].set_index("event_id").reindex(f.event_id).group
        assert reference.notna().all() and len(reference) == len(f)
        expected = reference.where(~reference.isin(CONTACT_GROUPS), "contact")
        assert np.array_equal(f.group, expected), config
        f["old_group"] = reference.to_numpy()
        f["config"] = config
        frames.append(f)
        checked += len(f)
        print(config, f.group.value_counts().to_dict(), flush=True)

    saved = pd.read_csv(Q10 / "potential_signals.csv")
    maps = build_level_maps(bars[["open", "high", "low", "close"]], pd.read_csv(ROLLS))
    for source in SOURCES:
        f = census.copy()
        levels = maps[source].reindex(f.signal_time).reset_index(drop=True)
        ref = saved[saved.source == source].set_index("event_id").reindex(f.event_id)
        assert np.array_equal(levels.status, ref.status), source
        assert np.allclose(levels.low, ref.low, equal_nan=True), source
        available = levels.status.eq("eligible")
        contact = exact_contact(f.signal_low, f.signal_high, levels.low)
        f["group"] = np.where(~available, "unavailable", np.where(contact, "contact", "no_contact"))
        f["old_group"] = ref.group.to_numpy()
        f["level"] = levels.low
        f["config"] = source
        frames.append(f)
        checked += len(f)
        print(source, f.group.value_counts().to_dict(), flush=True)
    return pd.concat(frames, ignore_index=True), checked


def member(f, group):
    if group == "all":
        return pd.Series(True, index=f.index)
    if group == "every_other":
        return f.group != "contact"
    if group == "unavailable":
        return f.group.isin((*UNAVAILABLE, "unavailable"))
    return f.group == group


def analyse(signals, trades):
    filled = signals[signals.filled].merge(trades, on="event_id", validate="many_to_one")
    rows, comparisons, details = [], [], []
    partitions = 0
    for config, all_signals in signals.groupby("config", sort=False):
        for period in PERIODS:
            c = all_signals[all_signals.period == period]
            t = filled[(filled.config == config) & (filled.period == period)].sort_values("exit_time")
            count, fills, net = TOTALS[period]
            assert len(c) == count and len(t) == fills and abs(t.net.sum() - net) < .01
            assert (c.signal_close < c.signal_open).all()
            assert t.event_id.is_unique and c.event_id.is_unique
            assert np.allclose(t.net_r, t.net / (2 * t.candle_range))
            masks = [member(c, label) for label in ("contact", "no_contact", "unavailable")]
            assert sum(int(m.sum()) for m in masks) == len(c)
            assert sum(int(c.loc[m, "baseline_attempt"].sum()) for m in masks) == int(c.baseline_attempt.sum())
            dd, peak, trough = drawdown_interval(t.net)
            dd_ids = set(t.iloc[peak:trough].event_id)
            a, rest, noncontact = (t[member(t, label)] for label in ("contact", "every_other", "no_contact"))
            assert len(a) + len(rest) == len(t) and abs(a.net.sum() + rest.net.sum() - t.net.sum()) < 1e-6
            assert len(noncontact) + int(member(t, "unavailable").sum()) == len(rest)
            partitions += 1
            for year in ["all"] + sorted(c.year.unique().tolist()):
                cy, ty = (x if year == "all" else x[x.year == year] for x in (c, t))
                for label in ("all", "contact", "every_other", "no_contact", "unavailable"):
                    cg, tg = cy[member(cy, label)], ty[member(ty, label)]
                    attempts = int(cg.baseline_attempt.sum())
                    assert len(tg) == int(cg.filled.sum())
                    rows.append(dict(config=config, period=period, year=year, group=label,
                                     potential_signals=len(cg), attempts=attempts,
                                     conversion=len(tg) / attempts if attempts else None,
                                     baseline_dd=dd if year == "all" else None,
                                     baseline_dd_net_contribution=float(tg[tg.event_id.isin(dd_ids)].net.sum())
                                     if year == "all" else None, **trade_metrics(tg)))
            yearly = [dict(year=int(y), candidate=trade_metrics(a[a.year == y]),
                           complement=trade_metrics(rest[rest.year == y])) for y in sorted(c.year.unique())]
            comparisons.append(dict(config=config, period=period, candidate_metrics=trade_metrics(a),
                                    complement_metrics=trade_metrics(rest), differences=contrast(a, rest, period),
                                    available_no_contact_differences=contrast(a, noncontact, period), yearly=yearly))
            for label, chunk in a.groupby("old_group"):
                details.append(dict(config=config, period=period, old_group=label, **trade_metrics(chunk)))
    return rows, comparisons, details, filled, partitions


def write_report(rows, comparisons, decision):
    lines = ["# Q12 broad support contact: generated results", "",
             "Original RTL exit; $1.05 round trip. Existing-fill attribution, not a filtered strategy run.", "",
             "| Definition | Period | Group | Signals | Attempts | Fills | Fill % | Net $ | PF | Mean R | Win % |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        if r["year"] != "all":
            continue
        fmt = lambda x: "n/a" if x is None else f"{x:.3f}"
        lines.append(f"| {r['config']} | {r['period']} | {r['group']} | {r['potential_signals']} | "
                     f"{r['attempts']} | {r['fills']} | {fmt(100*r['conversion'] if r['conversion'] is not None else None)} | "
                     f"{r['net']:.2f} | {fmt(r['pf'])} | {fmt(r['avg_net_r'])} | "
                     f"{fmt(100*r['win_rate'] if r['win_rate'] is not None else None)} |")
    lines += ["", "| Definition | Period | Comparator | PF difference [95% interval] | Mean R difference [95% interval] |",
              "|---|---|---|---:|---:|"]
    for c in comparisons:
        for field in ("differences", "available_no_contact_differences"):
            values = [c[field][k] for k in ("pf", "avg_net_r")]
            rendered = [f"{v['difference']:+.4f} [{v['lower']:+.4f}, {v['upper']:+.4f}]" for v in values]
            label = "every other" if field == "differences" else "available no contact"
            lines.append(f"| {c['config']} | {c['period']} | {label} | {' | '.join(rendered)} |")
    lines += ["", "```json", json.dumps(decision, indent=2), "```", ""]
    (STUDY / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    manifests = [Q10 / "provenance.json", Q11 / "provenance.json"]
    counts = {str(p): verify_manifest(p) for p in manifests}
    print("All upstream hashes verified:", counts, flush=True)
    census, trades, bars, _, _ = load()
    signals, checked = classifications(census, bars)
    rows, comparisons, details, filled, partitions = analyse(signals, trades)
    decision = decide([c for c in comparisons if c["config"] in CONFIGS])
    STUDY.mkdir(parents=True, exist_ok=True)
    signals.drop(columns="bar").to_csv(STUDY / "signals.csv", index=False)
    filled.drop(columns="bar").to_csv(STUDY / "trades.csv", index=False)
    pd.DataFrame(rows).to_csv(STUDY / "groups.csv", index=False)
    pd.DataFrame(details).to_csv(STUDY / "contact_breakdown.csv", index=False)
    verification = dict(manifest_entries=counts, signal_definitions_checked=checked,
                        partitions_reconciled=partitions, potential_signals=len(census),
                        attempts=int(census.baseline_attempt.sum()), fills=len(trades))
    for name, obj in (("contrasts", comparisons), ("decision", decision), ("verification", verification)):
        (STUDY / f"{name}.json").write_text(json.dumps(obj, indent=2), encoding="utf-8")
    paths = manifests + [Q10 / "potential_signals.csv", Q10 / "trades.csv", Q11 / "signals.csv", M30, ROLLS, PROTOCOL]
    paths += [ROOT / "python" / p for p in ("analyze_broad_support.py", "broad_support.py", "test_broad_support.py",
              "analyze_level_visit.py", "level_visit.py", "analyze_support_interaction.py",
              "analyze_price_levels.py", "analyze_breach_reclaim.py", "trend_regimes.py", "verify_location_validation.py")]
    provenance = dict(seed=20261004, files=[dict(path=str(p), sha256=sha256(p)) for p in paths])
    write_report(rows, comparisons, decision)
    provenance["outputs"] = [dict(path=str(p), sha256=sha256(p)) for p in sorted(STUDY.iterdir())
                             if p.name != "provenance.json" and p.is_file()]
    (STUDY / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
