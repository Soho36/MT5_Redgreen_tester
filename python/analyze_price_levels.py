"""Frozen Q6/Q7 level diagnostics; see docs/setups/horizontal/support-bounce-long/q06-q07-price-levels/PROTOCOL.md.

Reuses saved baseline trades; does not simulate or place orders.
Run with the project venv; outputs Reports/levels/price_levels_20261003/.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from trend_regimes import SOURCE, ROLLS, build_m30_reference
from verify_location_validation import read_rows

ROOT = Path(__file__).absolute().parent.parent
STUDY = ROOT / "Reports" / "levels" / "price_levels_20261003"
BASE = ROOT / "Reports" / "entry_shape_20261002"
SOURCES = ("previous_session", "current_session", "previous_week")
PERIODS = {"train": ("2016-01-01", "2020-01-01"),
           "recent": ("2020-01-02", "2026-07-14")}
THRESHOLDS = {"support": (0.25, 0.5, 0.75), "room": (0.5, 1.0, 1.5)}
PRIMARY = {"support": 0.5, "room": 1.0}
BINS = ("below_0", "exact_0", "0_to_0.5", "0.5_to_1", "above_1")


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def protocol_matches(path, recorded):
    """True if the file, or any committed version of it (renames followed), hashes to `recorded`.

    Run manifests record a protocol's hash when the runs were prepared. The docs were reorganised on 2026-10-07
    (paths and links only, docs/reference/moved_files.json), so the recorded version is checked against git history.
    Both line-ending conventions are tried, since the hash was taken on the working-tree file."""
    if sha256(path) == recorded:
        return True
    root = Path(__file__).resolve().parent.parent
    rel = Path(path).resolve().relative_to(root).as_posix()
    log = subprocess.run(["git", "log", "--follow", "--name-only", "--format=%H", "--", rel], cwd=root,
                         capture_output=True, text=True, check=True).stdout.split()
    for rev, name in zip(log[::2], log[1::2]):
        blob = subprocess.run(["git", "show", f"{rev}:{name}"], cwd=root, capture_output=True, check=True).stdout
        lf = blob.replace(b"\r\n", b"\n")
        if recorded in (hashlib.sha256(lf).hexdigest(), hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest()):
            return True
    # Runs prepared from a working file with mixed line endings: its raw hash is in no commit. The registry names
    # the commit holding that version; the current file must equal it except for line endings and link targets.
    entry = json.loads((root / "docs" / "reference" / "protocol_hashes.json").read_text()).get(recorded)
    if entry:
        blob = subprocess.run(["git", "show", f"{entry['commit']}:{entry['path']}"], cwd=root, capture_output=True,
                              check=True).stdout.decode("utf-8")
        return _paths_ignored(blob) == _paths_ignored(Path(path).read_text(encoding="utf-8"))
    return False


def _paths_ignored(text):
    """Protocol text with line endings, link targets and docs/ paths normalised (what the 2026-10-07 move changed)."""
    text = re.sub(r"\]\([^)]*\)", "]()", text.replace("\r\n", "\n"))
    return re.sub(r"docs/[^\s)`'\"]*", "docs/", text)


def distance_bin(values):
    v = np.asarray(values, dtype=float)
    return np.select([v < 0, v == 0, (v > 0) & (v <= .5),
                      (v > .5) & (v <= 1), v > 1], BINS, default="unavailable")


def aggregate_extremes(bars, key):
    grouped = bars.groupby(key, sort=True)
    result = grouped.agg(high=("high", "max"), low=("low", "min"),
                         source_start=("time", "min"), source_end=("time", "max"),
                         contract_min=("contract", "min"), contract_max=("contract", "max"))
    # idxmax/min select the first equal extreme: equal retests do not reset age.
    result["high_time"] = grouped.high.idxmax()
    result["low_time"] = grouped.low.idxmin()
    return result


def build_level_maps(bars, rolls):
    """Build maps for every bar, using only earlier bars for that row's levels."""
    b = bars.sort_index().copy()
    assert b.index.is_unique and not b.isna().any().any()
    assert (b.index.hour >= 1).all() and (b.index.dayofweek < 5).all()
    b["time"] = b.index
    b["session"] = b.index.normalize()
    b["week"] = b.session - pd.to_timedelta(b.index.dayofweek, unit="D")
    roll_dates = pd.to_datetime(rolls.date)
    assert roll_dates.is_monotonic_increasing and roll_dates.is_unique
    positions = np.searchsorted(roll_dates.to_numpy(), b.session.to_numpy(), side="right") - 1
    assert (positions >= 0).all(), "Roll ledger does not cover price history"
    b["contract"] = rolls.instrument_id.to_numpy()[positions]
    daily = aggregate_extremes(b, "session")
    weekly = aggregate_extremes(b, "week")
    previous = daily.shift(1).reindex(b.session)
    previous.index = b.index
    week = weekly.reindex(b.week - pd.Timedelta(days=7))
    week.index = b.index

    group = b.groupby("session", sort=False)
    current = pd.DataFrame(index=b.index)
    for side, operation in (("high", "cummax"), ("low", "cummin")):
        extreme = getattr(group[side], operation)()
        before = extreme.groupby(b.session).shift(1)
        new_extreme = before.isna() | (b[side] > before if side == "high" else b[side] < before)
        established = b.time.where(new_extreme).groupby(b.session).ffill()
        current[side] = before
        current[f"{side}_time"] = established.groupby(b.session).shift(1)
    current["source_start"] = group.time.transform("first")
    current["source_end"] = group.time.shift(1)
    for label, operation in (("contract_min", "cummin"), ("contract_max", "cummax")):
        current[label] = getattr(group.contract, operation)().groupby(b.session).shift(1)

    session_number = pd.Series(np.arange(len(daily)), index=daily.index)
    signal_session = b.session.map(session_number)
    maps = dict(previous_session=previous, current_session=current, previous_week=week)
    for name, frame in maps.items():
        missing = frame.source_end.isna()
        mismatch = (frame.contract_min != b.contract) | (frame.contract_max != b.contract)
        frame["status"] = np.select([missing, mismatch], ["missing_history", "contract_roll"], default="eligible")
        if name == "current_session":
            frame.loc[missing, "status"] = "no_prior_session_bar"
        known = ~missing
        assert (frame.loc[known, "source_end"] < frame.index[known]).all(), "Future level data"
        frame["signal_contract"] = b.contract
        for side in ("high", "low"):
            frame[f"{side}_age_hours"] = (b.time - frame[f"{side}_time"]).dt.total_seconds() / 3600
            frame[f"{side}_age_sessions"] = signal_session - frame[f"{side}_time"].dt.normalize().map(session_number)
            assert (frame.loc[known, f"{side}_time"] <= frame.loc[known, "source_end"]).all()
    return maps


def load_and_audit(bars):
    manifest = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["symbol"] == "MNQcontDTBNT20102026_2"
    frames, audits, files = [], {}, []
    for period, (start, end) in PERIODS.items():
        job = next(j for j in manifest["jobs"] if j["period"] == period)
        path = BASE / job["csv"]
        stats_path = path.with_name(path.stem + "_stats.csv")
        ini_path = BASE / f"{job['tag']}.ini"
        assert (BASE / f"{job['tag']}.completed.json").exists()
        ini = ini_path.read_text(encoding="utf-16")
        for expected in ("Model=1", "Symbol=MNQcontDTBNT20102026_2", "Period=M30"):
            assert expected in ini.splitlines(), expected
        raw = pd.DataFrame(read_rows(path))
        stats = read_rows(stats_path)[0]
        for field, expected in (("risk_reward", 1), ("max_red_run", 3), ("min_location", 0),
                                ("snapshot_bars", 51), ("flatten_fallback", 1),
                                ("trail_distance_r", 0), ("early_close_calendar", 1)):
            assert float(stats[field]) == expected, field
        assert len(raw) == int(stats["trades"]) and raw.ticket.is_unique
        t = raw.iloc[:, :11].copy()
        for c in ("signal_time", "entry_time", "exit_time"):
            t[c] = pd.to_datetime(t[c], format="%Y.%m.%d %H:%M:%S")
        for c in ("trade_profit", "candle_range", "red_run", "mae_money", "mfe_money", "location", "period_sec"):
            t[c] = pd.to_numeric(t[c])
        assert np.isclose(t.trade_profit.sum(), float(stats["net_profit"]), atol=1e-7, rtol=0)
        assert (t.period_sec == 1800).all() and t.red_run.between(1, 3).all()
        assert t.entry_time.between(pd.Timestamp(start), pd.Timestamp(end), inclusive="left").all()
        assert (t.signal_time < t.entry_time).all() and (t.entry_time <= t.exit_time).all()
        loc = bars.index.get_indexer(t.signal_time)
        assert (loc >= 50).all(), "Missing signal/history"
        for short, field in zip("ohlc", ("open", "high", "low", "close")):
            exported = raw[[f"{short}{n}" for n in range(1, 52)]].to_numpy(dtype=float)
            reference = bars[field].to_numpy()[loc[:, None] - np.arange(51)]
            assert np.array_equal(exported, reference), f"{period}: snapshot {field} mismatch"
        for short, field in zip("ohlc", ("open", "high", "low", "close")):
            t[f"signal_{field}"] = raw[f"{short}1"].astype(float)
        assert (t.signal_close < t.signal_open).all()
        assert np.array_equal(t.signal_high - t.signal_low, t.candle_range)
        assert (t.candle_range > 0).all()
        old_path = ROOT / "Reports" / "rr_clean_20261001" / f"runband_rrclean_20261001_{period}_1p00_1.00.csv"
        old = pd.DataFrame(read_rows(old_path))
        assert len(old) == len(t)
        for field in ("entry_time", "exit_time", "trade_profit", "candle_range", "red_run", "location", "mae_money", "mfe_money"):
            if field.endswith("time"):
                assert np.array_equal(raw[field], old[field]), field
            else:
                assert np.array_equal(raw[field].astype(float), old[field].astype(float)), field
        t["period"] = period
        t["trade_id"] = period + "_" + t.ticket
        t["net"] = t.trade_profit - 1.05
        t["net_r"] = t.net / (2 * t.candle_range)
        t["year"] = t.entry_time.dt.year
        frames.append(t)
        audits[period] = dict(trades=len(t), gross=float(t.trade_profit.sum()),
                              net=float(t.net.sum()), candle_values_checked=len(t) * 51 * 4,
                              baseline_match=True, start=str(t.entry_time.min()), end=str(t.entry_time.max()))
        files.extend((path, stats_path, ini_path, old_path))
    return pd.concat(frames, ignore_index=True), audits, files


def attach_levels(trades, maps):
    frames = []
    for source, level_map in maps.items():
        ref = level_map.reindex(trades.signal_time).reset_index(drop=True)
        assert ref.status.notna().all()
        f = pd.concat([trades.reset_index(drop=True), ref], axis=1)
        f["source"] = source
        f["support"] = (f.signal_low - f.low) / f.candle_range
        f["room"] = (f.high - f.signal_high) / f.candle_range
        unavailable = f.status != "eligible"
        f.loc[unavailable, ["support", "room"]] = np.nan
        for feature in ("support", "room"):
            f[f"{feature}_bin"] = distance_bin(f[feature])
        f["low_relation"] = np.select([unavailable, f.signal_high < f.low, f.signal_low > f.low],
                                       ["unavailable", "entirely_below", "entirely_above"], default="spans_or_touches")
        frames.append(f)
    output = pd.concat(frames, ignore_index=True)
    common = output.groupby("trade_id").status.agg(lambda s: (s == "eligible").all())
    output["common"] = output.trade_id.map(common)
    return output


def metrics(frame):
    x = frame.net.to_numpy()
    gains, losses = x[x > 0].sum(), -x[x < 0].sum()
    return dict(n=len(x), net=float(x.sum()), pf=float(gains / losses) if losses else None,
                avg_net=float(x.mean()) if len(x) else None,
                avg_net_r=float(frame.net_r.mean()) if len(x) else None)


def audit_level_samples(features, bars, rolls):
    """Independent direct-window checks, stratified to include exclusion cases."""
    dates = bars.index.normalize().unique()
    roll_dates = pd.to_datetime(rolls.date).to_numpy()
    roll_ids = rolls.instrument_id.to_numpy()
    count = 0
    for _, group in features.groupby(["source", "period", "status"]):
        for row in group.sample(n=min(100, len(group)), random_state=20261003).itertuples():
            day = row.signal_time.normalize()
            if row.source == "current_session":
                start, end = day, row.signal_time
            elif row.source == "previous_session":
                start = dates[dates.searchsorted(day) - 1]
                end = start + pd.Timedelta(days=1)
            else:
                end = day - pd.Timedelta(days=day.dayofweek)
                start = end - pd.Timedelta(days=7)
            a, z = bars.index.searchsorted([start, end])
            window = bars.iloc[a:z]
            if window.empty:
                assert row.status in ("missing_history", "no_prior_session_bar")
                assert np.isnan(row.support) and np.isnan(row.room)
                count += 1
                continue
            assert (window.index < row.signal_time).all()
            high, low = window.high.max(), window.low.min()
            assert row.high == high and row.low == low
            assert row.high_time == window.high.idxmax() and row.low_time == window.low.idxmin()
            assert row.source_start == window.index[0] and row.source_end == window.index[-1]
            ids = roll_ids[np.searchsorted(roll_dates, window.index.to_numpy(), side="right") - 1]
            signal_contract = roll_ids[np.searchsorted(roll_dates, row.signal_time.to_datetime64(), side="right") - 1]
            eligible = np.all(ids == signal_contract)
            assert row.status == ("eligible" if eligible else "contract_roll")
            if eligible:
                assert row.support == (row.signal_low - low) / row.candle_range
                assert row.room == (high - row.signal_high) / row.candle_range
            else:
                assert np.isnan(row.support) and np.isnan(row.room)
            count += 1
    return count


def masks(frame, feature, threshold):
    d = frame[feature]
    if feature == "support":
        return d > threshold, (d >= 0) & (d <= threshold)
    return (d > 0) & (d <= threshold), d > threshold


def bootstrap_difference(frame, bad, control, period):
    """Paired month blocks, mean net R of hypothesized bad group minus control."""
    start, end = PERIODS[period]
    months = pd.period_range(pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(days=1), freq="M")
    aggregates = []
    for mask in (bad, control):
        selected = frame.loc[mask].copy()
        grouped = selected.groupby(selected.entry_time.dt.to_period("M")).net_r.agg(["sum", "count"])
        aggregates.append(grouped.reindex(months, fill_value=0).to_numpy())
    rng = np.random.default_rng(20261003)
    draws = rng.integers(0, len(months), size=(2000, len(months)))
    a, b = (v[draws].sum(axis=1) for v in aggregates)
    valid = (a[:, 1] > 0) & (b[:, 1] > 0)
    if not valid.any():
        return dict(lower=None, upper=None, valid_resamples=0)
    diff = a[valid, 0] / a[valid, 1] - b[valid, 0] / b[valid, 1]
    low, high = np.quantile(diff, [.025, .975])
    return dict(lower=float(low), upper=float(high), valid_resamples=int(valid.sum()))


def compare(features):
    groups, coverage, contrasts, ages = [], [], [], []
    for source in SOURCES:
        source_frame = features[features.source == source]
        for period in PERIODS:
            all_rows = source_frame[source_frame.period == period]
            for status, rows in all_rows.groupby("status"):
                coverage.append(dict(source=source, period=period, status=status, n=len(rows), share=len(rows) / len(all_rows)))
            for population in ("source", "common"):
                f = all_rows[(all_rows.status == "eligible") & ((all_rows.common) if population == "common" else True)]
                for side in ("high", "low"):
                    ages.append(dict(source=source, period=period, population=population, side=side, n=len(f),
                                     median_hours=float(f[f"{side}_age_hours"].median()),
                                     median_sessions=float(f[f"{side}_age_sessions"].median())))
                for year in ["all"] + sorted(f.year.unique().tolist()):
                    y = f if year == "all" else f[f.year == year]
                    for feature in ("support", "room"):
                        for label in ["all"] + list(BINS):
                            selected = y if label == "all" else y[y[f"{feature}_bin"] == label]
                            groups.append(dict(source=source, period=period, population=population, year=year,
                                               feature=feature, group=label, share=len(selected) / len(y) if len(y) else 0,
                                               **metrics(selected)))
                for feature, thresholds in THRESHOLDS.items():
                    for threshold in thresholds:
                        bad, control = masks(f, feature, threshold)
                        bm, cm = metrics(f[bad]), metrics(f[control])
                        qualifies = (bm["n"] >= 200 and cm["n"] >= 200 and
                                     bm["pf"] is not None and cm["pf"] is not None and
                                     bm["pf"] < 1 < cm["pf"])
                        delta = bm["avg_net_r"] - cm["avg_net_r"] if bm["n"] and cm["n"] else None
                        contrasts.append(dict(source=source, period=period, population=population, feature=feature,
                                              threshold=threshold, bad=bm, control=cm, difference_net_r=delta,
                                              interval=bootstrap_difference(f, bad, control, period), qualifies=bool(qualifies)))
    decisions = {}
    for feature, primary in PRIMARY.items():
        def passes(population, threshold):
            rows = [r for r in contrasts if r["source"] == "previous_session" and r["feature"] == feature
                    and r["population"] == population and r["threshold"] == threshold]
            assert len(rows) == 2
            return all(r["qualifies"] for r in rows)
        gates = dict(primary_both_periods=passes("source", primary),
                     neighbor_both_periods=any(passes("source", t) for t in THRESHOLDS[feature] if t != primary),
                     common_both_periods=passes("common", primary))
        decisions[feature] = dict(gates=gates, candidate=all(gates.values()))
    return groups, coverage, contrasts, ages, decisions


def fmt(value, digits=3):
    return "n/a" if value is None or pd.isna(value) else f"{value:,.{digits}f}"


def write_report(study, audits, groups, coverage, contrasts, ages, decisions):
    lines = ["# Q6/Q7: price-level proximity and overhead room", "", "2026-10-03. Frozen definitions: [protocol](../../../docs/setups/horizontal/support-bounce-long/q06-q07-price-levels/PROTOCOL.md).",
             "Analysis: `python/analyze_price_levels.py`. Full tables and per-trade features: `Reports/levels/price_levels_20261003/`.", "",
             "## Decision", ""]
    for feature, result in decisions.items():
        lines.append(f"- {feature}: **{'candidate for a separately specified full MT5 rerun' if result['candidate'] else 'no filter qualifies'}**. Gates: `{result['gates']}`.")
    lines += ["", "Primary source is the previous completed session. Current-session and previous-week comparisons are secondary, not selected alternatives.",
              "No strategy improvement or filtered drawdown is inferred from subset results. All history is previously examined and outcomes use one-minute OHLC.",
              "", "## Baseline and verification", "", "| Period | Trades | Gross $ | Net $ | Candle values checked |", "|---|---:|---:|---:|---:|"]
    for period, audit in audits.items():
        lines.append(f"| {period} | {audit['trades']:,} | {audit['gross']:,.2f} | {audit['net']:,.2f} | {audit['candle_values_checked']:,} |")
    lines += ["", "All 51 candles per trade match the independently rebuilt minute-source M30 history. Original baseline trade fields match the saved RR=1 run; trade count and gross profit reconcile with tester statistics. Cost is $1.05 per round trip; net R uses the original signal range and $2/point.",
              "", "## Coverage", "", "| Source | Period | Status | Trades | Share |", "|---|---|---|---:|---:|"]
    for r in coverage:
        lines.append(f"| {r['source']} | {r['period']} | {r['status']} | {r['n']:,} | {r['share']:.1%} |")
    lines += ["", "Contract-roll exclusions apply to the entire source window. Current-session first bars have no eligible reference. Common-population tables use only trades eligible for all three sources.",
              "", "## Planned contrasts", "", "Bad/control below mean the hypothesized weak group and comparison group; the names do not assert an observed effect.",
              "Support: far (>0.5R) / near (0-0.5R). Room: limited (>0 to 1R) / more (>1R). Negative distances and overhead equality are separate descriptive bins.",
              "", "| Population | Source | Question | Period | Bad n | Control n | Bad net $ | Control net $ | Bad PF | Control PF | Bad avg R | Control avg R | Difference R [95% interval] |",
              "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in contrasts:
        if r["threshold"] != PRIMARY[r["feature"]]:
            continue
        b, c, ci = r["bad"], r["control"], r["interval"]
        lines.append(f"| {r['population']} | {r['source']} | {r['feature']} | {r['period']} | {b['n']:,} | {c['n']:,} | {fmt(b['net'], 0)} | {fmt(c['net'], 0)} | {fmt(b['pf'])} | {fmt(c['pf'])} | {fmt(b['avg_net_r'])} | {fmt(c['avg_net_r'])} | {fmt(r['difference_net_r'])} [{fmt(ci['lower'])}, {fmt(ci['upper'])}] |")
    lines += ["", "Intervals are descriptive month-block bootstraps, unadjusted for multiple comparisons. PF is dollar-weighted; average R weights trades differently, so the rankings can differ.",
              "", "## Distance groups (source-specific eligible sample)", "", "| Source | Question | Period | Distance R | Trades | Share | Net $ | PF | Avg net R |",
              "|---|---|---|---|---:|---:|---:|---:|---:|"]
    for r in groups:
        if r["population"] != "source" or r["year"] != "all":
            continue
        lines.append(f"| {r['source']} | {r['feature']} | {r['period']} | {r['group']} | {r['n']:,} | {r['share']:.1%} | {fmt(r['net'], 0)} | {fmt(r['pf'])} | {fmt(r['avg_net_r'])} |")
    lines += ["", "## Annual primary contrasts", "", "The annual counts, PF, net dollars and net R for every distance bin and all sources are in `groups.csv`. Annual primary-threshold contrasts are in `annual_contrasts.csv`.",
              "", "## Age", "", "These summarize formation age within the defined source window; age was not optimized.",
              "", "| Source | Period | Extreme | Median hours | Median trading sessions |", "|---|---|---|---:|---:|"]
    for r in ages:
        if r["population"] == "source":
            lines.append(f"| {r['source']} | {r['period']} | {r['side']} | {r['median_hours']:.1f} | {r['median_sessions']:.1f} |")
    lines += ["", "## Reproduce", "", "```powershell", ".\\venv\\Scripts\\python.exe python\\analyze_price_levels.py",
              ".\\venv\\Scripts\\python.exe -m unittest discover -s python -p test_price_levels.py -v", "```", "",
              "`provenance.json` stores input/script/protocol hashes and audit counts. `contrasts.json` includes all predefined neighboring thresholds; `features.csv` contains the exact reference prices/timestamps, exclusion reasons, signed distances, and formation ages for each trade/source.", ""]
    (study / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=STUDY)
    args = parser.parse_args()
    study = args.output
    study.mkdir(parents=True, exist_ok=True)
    reference = study / "m30_reference.csv"
    # Rebuild each invocation: no stale reference cache can silently change the input.
    print("Rebuilding independent M30 reference...", flush=True)
    bars = build_m30_reference(reference)
    rolls = pd.read_csv(ROLLS)
    print("Auditing saved baseline and all signal snapshots...", flush=True)
    trades, audits, files = load_and_audit(bars)
    maps = build_level_maps(bars, rolls)
    features = attach_levels(trades, maps)
    sample_checks = audit_level_samples(features, bars, rolls)
    assert len(features) == len(trades) * len(SOURCES)
    assert not features.duplicated(["trade_id", "source"]).any()
    features.to_csv(study / "features.csv", index=False)
    print("Computing frozen comparisons...", flush=True)
    groups, coverage, contrasts, ages, decisions = compare(features)
    pd.DataFrame(groups).to_csv(study / "groups.csv", index=False)
    pd.DataFrame(coverage).to_csv(study / "coverage.csv", index=False)
    pd.DataFrame(ages).to_csv(study / "ages.csv", index=False)
    annual = []
    for (source, period, year), f in features[features.status == "eligible"].groupby(["source", "period", "year"]):
        for feature, threshold in PRIMARY.items():
            for population in ("source", "common"):
                sample = f if population == "source" else f[f.common]
                bad, control = masks(sample, feature, threshold)
                for name, mask in (("bad", bad), ("control", control)):
                    annual.append(dict(source=source, period=period, year=int(year), feature=feature,
                                       population=population, group=name, **metrics(sample[mask])))
    pd.DataFrame(annual).to_csv(study / "annual_contrasts.csv", index=False)
    (study / "contrasts.json").write_text(json.dumps(contrasts, indent=2), encoding="utf-8")
    (study / "decisions.json").write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    paths = files + [SOURCE, ROLLS, Path(__file__), ROOT / "docs" / "setups" / "horizontal" / "support-bounce-long" / "q06-q07-price-levels" / "PROTOCOL.md"]
    provenance = dict(audits=audits, files=[dict(path=str(p), sha256=sha256(p)) for p in paths],
                      common_trades=int(features[features.source == "previous_session"].common.sum()),
                      reference_bars=len(bars), independent_window_checks=sample_checks)
    (study / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    write_report(study, audits, groups, coverage, contrasts, ages, decisions)
    print(json.dumps(dict(audits=audits, decisions=decisions, common_trades=provenance["common_trades"]), indent=2))
    print(f"Report saved: {study / 'report.md'}")


if __name__ == "__main__":
    main()
