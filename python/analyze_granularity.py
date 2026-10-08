"""Analyse fixed-grid MNQ resolution; all intervals pair the same whole entry days.

Manifest: variants, paired rtl/control jobs, trading_days, pv=2, native_tick=.25.
Native must reproduce the prior signal-colour ledgers exactly. Each job requires
a completion marker with matching output hashes. RTL minus control is a strategy
comparison, not an isolated causal entry effect.
Usage: python analyze_granularity.py [--run-dir PATH] [--partial]
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_instrument_baseline import COST, PERIODS, load, point_value, summary
from analyze_signal_colour import per_day
from audit_granularity_ledgers import ensure_audited
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports" / "granularity_20261009"
OLD = ROOT / "Reports" / "signal_colour_20261008"
MODES = ("rtl", "control")
BOOTSTRAPS = 2000
SEED = 20261009
BATCH = 24


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def completed(run, job):
    """Return an actionable reason for an incomplete or modified job."""
    marker = run / f"{job['tag']}.completed.json"
    if not marker.exists():
        return "completion marker missing"
    try:
        done = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"invalid completion marker: {exc}"
    if done.get("tag") != job["tag"]:
        return "completion marker tag differs"
    for name in job["outputs"]:
        path = run / name
        if not path.is_file():
            return f"missing output {name}"
        expected = done.get("outputs", {}).get(name)
        if not expected or sha256(path) != expected:
            return f"output hash differs from completion marker: {name}"
    return None


def validate_manifest(manifest):
    variants = manifest["variants"]
    keys = [v["key"] for v in variants]
    if len(keys) != len(set(keys)):
        raise ValueError("Variant keys must be unique")
    for v in variants:
        k, origin = v["k"], v["origin_ticks"]
        if not isinstance(k, int) or k < 1 or not isinstance(origin, int) or not 0 <= origin < k:
            raise ValueError(f"Invalid native-compatible grid: {v}")
        tick = float(manifest.get("native_tick", 0.25))
        if not np.isclose(v["grid_points"], k * tick) or not np.isclose(v["origin_points"], origin * tick):
            raise ValueError(f"Grid points and integer tick metadata disagree: {v}")
    if sum(v["k"] == 1 and v["origin_ticks"] == 0 for v in variants) != 1:
        raise ValueError("Manifest needs exactly one native k=1, origin=0 variant")
    jobs = {}
    for job in manifest["jobs"]:
        key = (job["variant"], job["mode"])
        if key in jobs or key[0] not in keys or key[1] not in MODES or not job.get("outputs"):
            raise ValueError(f"Invalid or duplicate job: {job}")
        jobs[key] = job
    missing = [(v["key"], mode) for v in variants for mode in MODES if (v["key"], mode) not in jobs]
    if missing:
        raise ValueError(f"Manifest is missing rtl/control pairs: {missing}")
    return variants, jobs


def native_replication(path, mode):
    old_name = "red_cap3" if mode == "rtl" else "market_control"
    old_path = OLD / f"runband_signal_20261008_{old_name}_1.00.csv"
    if not old_path.is_file():
        raise FileNotFoundError(f"Native replication ledger missing: {old_path}")
    new_raw = pd.read_csv(path, sep="\t", encoding="utf-16")
    old_raw = pd.read_csv(old_path, sep="\t", encoding="utf-16")
    exclude = [c for c in ("symbol",) if c in new_raw.columns or c in old_raw.columns]
    pd.testing.assert_frame_equal(new_raw.drop(columns=exclude, errors="ignore"),
                                  old_raw.drop(columns=exclude, errors="ignore"),
                                  check_exact=True)
    byte_equal = path.read_bytes() == old_path.read_bytes()
    if not exclude and not byte_equal:
        raise ValueError(f"Native {mode} matches parsed values but not the original CSV bytes")
    return {"mode": mode, "trades": len(new_raw), "all_fields_equal": True,
            "byte_equal": byte_equal, "excluded_columns": exclude,
            "reference": str(old_path.relative_to(ROOT))}


def validate_ledger(d, variant, pv):
    if d.empty:
        raise ValueError(f"Empty ledger for {variant['key']}")
    if not np.isfinite(d["trade_profit"]).all() or not np.isfinite(d["candle_range"]).all():
        raise ValueError(f"Non-finite profit or candle range for {variant['key']}")
    if (d["candle_range"] <= 0).any():
        raise ValueError(f"Nonpositive risk in ledger for {variant['key']}")
    levels = d["candle_range"].to_numpy() / variant["grid_points"]
    good = np.isclose(levels, np.rint(levels), rtol=0, atol=1e-7)
    if not good.all():
        bad = d.loc[~good, ["entry_time", "candle_range"]].head(5)
        raise ValueError(f"Candle ranges do not lie on {variant['grid_points']}-point grid:\n{bad}")
    if (d["trade_profit"] < 0).any() and not np.isclose(point_value(d), pv):
        raise ValueError(f"Ledger stop losses imply a point value different from ${pv}: {variant['key']}")



def reconcile_tester(d, stats_path, job):
    """Reconcile the complete ledger against the single RR1 tester summary."""
    stats = pd.read_csv(stats_path, sep="\t", encoding="utf-16")
    required = {"run_tag", "risk_reward", "trades", "net_profit", "gross_profit", "gross_loss"}
    missing = required.difference(stats.columns)
    if len(stats) != 1 or missing:
        raise ValueError(f"{job['tag']}: expected one tester-summary row; missing fields {sorted(missing)}")
    row = stats.iloc[0]
    if row["run_tag"] != job["tag"]:
        raise ValueError(f"{job['tag']}: tester-summary tag differs: {row['run_tag']}")
    if not np.isfinite(float(row["risk_reward"])) or not np.isclose(float(row["risk_reward"]), 1.0, rtol=0, atol=1e-9):
        raise ValueError(f"{job['tag']}: tester summary does not use RR1")
    count = float(row["trades"])
    if not np.isfinite(count) or count != len(d):
        raise ValueError(f"{job['tag']}: ledger has {len(d)} trades, tester reports {row['trades']}")
    expected_totals = {"net_profit": float(d.trade_profit.sum()),
                       "gross_profit": float(d.loc[d.trade_profit > 0, "trade_profit"].sum()),
                       "gross_loss": float(d.loc[d.trade_profit < 0, "trade_profit"].sum())}
    differences = {}
    for field, total in expected_totals.items():
        value = float(row[field])
        if not np.isfinite(value) or not np.isclose(total, value, rtol=0, atol=1e-6):
            raise ValueError(f"{job['tag']}: ledger {field}={total:.10f}, tester={value:.10f}")
        differences[field] = total - value
    settings = {"max_red_run": 3 if job["mode"] == "rtl" else 0,
                "early_close_calendar": 1, "flatten_fallback": 1, "trail_distance_r": 0}
    checked = {}
    for field, expected in settings.items():
        if field in row.index:
            value = float(row[field])
            if not np.isfinite(value) or not np.isclose(value, expected, rtol=0, atol=1e-9):
                raise ValueError(f"{job['tag']}: tester setting {field}={value}, expected {expected}")
            checked[field] = expected
    control_open_fraction = None
    if job["mode"] == "control":
        exact = d.entry.dt.minute.isin([0, 30]) & (d.entry.dt.second == 0) & (d.entry.dt.microsecond == 0)
        control_open_fraction = float(exact.mean())
    return {"tag": job["tag"], "trades": len(d), "passed": True,
            "profit_differences": differences, "settings_checked": checked,
            "settings_absent": sorted(set(settings).difference(checked)),
            "control_exact_m30_timestamp_fraction": control_open_fraction}


def aligned_calendar(manifest, ledgers):
    if not manifest.get("trading_days"):
        raise ValueError("manifest.trading_days is required: every native M1 source session in the tester date range")
    days = pd.DatetimeIndex(pd.to_datetime(manifest["trading_days"], format="%Y-%m-%d"))
    if days.has_duplicates or not days.is_monotonic_increasing:
        raise ValueError("manifest.trading_days must be unique and sorted")
    for key, d in ledgers.items():
        entry_days = d["entry"].dt.normalize()
        absent = entry_days[~entry_days.isin(days)].unique()
        if len(absent):
            raise ValueError(f"Ledger {key} contains dates outside manifest calendar: {absent[:5]}")
    return days


def bootstrap_means(sums, counts, seed):
    """B x arms ratio means with common paired day samples, bounded memory."""
    if sums.shape != counts.shape or sums.ndim != 2 or sums.shape[0] == 0:
        raise ValueError("Bootstrap needs aligned nonempty day-by-arm arrays")
    rng = np.random.default_rng(seed)
    result = np.empty((BOOTSTRAPS, sums.shape[1]), dtype=float)
    for start in range(0, BOOTSTRAPS, BATCH):
        end = min(start + BATCH, BOOTSTRAPS)
        indices = rng.integers(0, sums.shape[0], (end - start, sums.shape[0]))
        numerator = sums[indices].sum(axis=1)
        denominator = counts[indices].sum(axis=1)
        if (denominator == 0).any():
            raise ValueError("A resampled arm has zero trades; the sample is too sparse")
        result[start:end] = numerator / denominator
    return result


def interval(values):
    return tuple(float(x) for x in np.percentile(values, [2.5, 97.5]))


def meta(v):
    return {name: v[name] for name in ("key", "symbol", "k", "origin_ticks", "grid_points", "origin_points")}


def markdown_table(frame, columns):
    """Save Markdown without the optional tabulate dependency."""
    def cell(x):
        if pd.isna(x):
            return ""
        if isinstance(x, (float, np.floating)):
            return f"{x:+.4f}"
        return str(x)
    return "\n".join(["| " + " | ".join(columns) + " |",
                       "| " + " | ".join("---" for _ in columns) + " |"] +
                      ["| " + " | ".join(cell(x) for x in row) + " |"
                       for row in frame[columns].itertuples(index=False, name=None)])


def analyse(run, partial=False):
    manifest_path = run / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Prepare the experiment first; manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    variants, jobs = validate_manifest(manifest)
    failures = {key: completed(run, job) for key, job in jobs.items()}
    failures = {key: reason for key, reason in failures.items() if reason}
    if failures and not partial:
        details = "\n".join(f"  {jobs[key]['tag']}: {reason}" for key, reason in failures.items())
        raise RuntimeError(f"{len(failures)} jobs are incomplete or invalid. Finish the run before analysis:\n{details}\n"
                           f"Run: python python/run_mt5_job.py {run} {manifest.get('expert', 'RTL_granularity')}\n"
                           "Use --partial only for an explicitly provisional analysis of complete pairs.")
    variants = [v for v in variants if all((v["key"], mode) not in failures for mode in MODES)]
    native = next((v for v in variants if v["k"] == 1), None)
    if native is None:
        raise RuntimeError("Both native jobs must complete before any analysis or paired native comparison")
    pv = float(manifest.get("pv", 2.0))
    replication = [native_replication(run / jobs[(native["key"], mode)]["outputs"][0], mode) for mode in MODES]
    ledgers = {}
    tester_checks = []
    for v in variants:
        for mode in MODES:
            job = jobs[(v["key"], mode)]
            if len(job["outputs"]) < 2:
                raise ValueError(f"{job['tag']}: tester-summary output is missing from manifest")
            audited_path = ensure_audited(run, job, v, pv)
            d = load(audited_path)
            validate_ledger(d, v, pv)
            check = reconcile_tester(d, run / job["outputs"][1], job)
            audit = json.loads((run / f"{job['tag']}.ledger_audit.json").read_text(encoding="utf-8"))
            check.update(raw_trades=audit["raw_trades"], recovered_trades=audit["recovered_trades"],
                         recovered_profit=audit["recovered_profit"], audit_file=f"{job['tag']}.ledger_audit.json")
            tester_checks.append(check)
            ledgers[(v["key"], mode)] = d
    days = aligned_calendar(manifest, ledgers)
    arm_keys = [(v["key"], mode) for v in variants for mode in MODES]
    daily = {key: per_day(ledgers[key], pv).reindex(days, fill_value=0) for key in arm_keys}
    sums = np.column_stack([daily[key]["sum"].to_numpy() for key in arm_keys])
    counts = np.column_stack([daily[key]["size"].to_numpy() for key in arm_keys])
    summary_rows, contrast_rows, resolution_rows, year_rows, daily_rows = [], [], [], [], []
    for v in variants:
        for mode in MODES:
            d = ledgers[(v["key"], mode)]
            enriched = d.assign(day=d["entry"].dt.normalize(),
                                net_r=(d.trade_profit - COST) / (d.candle_range * pv),
                                net_money=d.trade_profit - COST)
            extra = enriched.groupby("day")[["net_r", "net_money"]].sum().reindex(days, fill_value=0)
            part = daily[(v["key"], mode)]
            for day, gross_sum, trades, net_sum, net_money in zip(days, part["sum"], part["size"],
                                                                extra["net_r"], extra["net_money"]):
                daily_rows.append({**meta(v), "mode": mode, "day": day.strftime("%Y-%m-%d"),
                                   "trades": int(trades), "gross_R_sum": gross_sum,
                                   "net_R_sum": net_sum, "net_$": net_money})
            for year, p in d.groupby(d.entry.dt.year):
                year_rows.append({**meta(v), "mode": mode, "year": int(year), **summary(p, pv)})
    native_index = next(i for i, v in enumerate(variants) if v["key"] == native["key"])
    for period_index, (label, lo, hi) in enumerate(PERIODS):
        mask = (days.year >= lo) & (days.year <= hi)
        if not mask.any():
            raise ValueError(f"No calendar days for {label}")
        ns = counts[mask].sum(axis=0)
        if (ns == 0).any():
            raise ValueError(f"At least one arm has no trades in {label}")
        means = sums[mask].sum(axis=0) / ns
        draws = bootstrap_means(sums[mask], counts[mask], SEED + period_index)
        contrasts = means[0::2] - means[1::2]
        contrast_draws = draws[:, 0::2] - draws[:, 1::2]
        native_draw = contrast_draws[:, native_index]
        for i, v in enumerate(variants):
            for m, mode in enumerate(MODES):
                d = ledgers[(v["key"], mode)]
                p = d[(d.entry.dt.year >= lo) & (d.entry.dt.year <= hi)]
                stats = summary(p, pv)
                if not np.isclose(stats["gross_R"], means[2 * i + m], atol=1e-12):
                    raise AssertionError("Trade and aligned-day gross means differ")
                lower, upper = interval(draws[:, 2 * i + m])
                summary_rows.append({**meta(v), "mode": mode, "period": label, **stats,
                                     "gross_R_lo": lower, "gross_R_hi": upper,
                                     "calendar_days": int(mask.sum()),
                                     "active_days": int((daily[(v["key"], mode)].loc[mask, "size"] > 0).sum())})
                levels = p.candle_range / v["grid_points"]
                resolution_rows.append({**meta(v), "mode": mode, "period": label, "trades": len(p),
                                        "range_points_med": p.candle_range.median(),
                                        "native_ticks_med": (p.candle_range / manifest.get("native_tick", 0.25)).median(),
                                        "grid_levels_p10": levels.quantile(0.1),
                                        "grid_levels_med": levels.median(), "grid_levels_p90": levels.quantile(0.9),
                                        "grid_integral_fraction": float(np.isclose(levels, np.rint(levels), rtol=0, atol=1e-7).mean())})
            lower, upper = interval(contrast_draws[:, i])
            delta_lower, delta_upper = interval(contrast_draws[:, i] - native_draw)
            contrast_rows.append({**meta(v), "scope": "origin", "period": label,
                                  "origins": 1, "rtl_gross_R": means[2 * i], "control_gross_R": means[2 * i + 1],
                                  "contrast_R": contrasts[i], "contrast_R_lo": lower, "contrast_R_hi": upper,
                                  "delta_native_R": contrasts[i] - contrasts[native_index],
                                  "delta_native_R_lo": delta_lower, "delta_native_R_hi": delta_upper,
                                  "calendar_days": int(mask.sum())})
        for k in sorted({v["k"] for v in variants}):
            indices = np.array([i for i, v in enumerate(variants) if v["k"] == k])
            mean_draw = contrast_draws[:, indices].mean(axis=1)
            lower, upper = interval(mean_draw)
            delta_lower, delta_upper = interval(mean_draw - native_draw)
            value = contrasts[indices].mean()
            contrast_rows.append({"key": f"mean_k{k}", "symbol": "", "k": k, "origin_ticks": np.nan,
                                  "grid_points": k * manifest.get("native_tick", 0.25), "origin_points": np.nan,
                                  "scope": "equal_origin_mean", "period": label, "origins": len(indices),
                                  "rtl_gross_R": means[2 * indices].mean(),
                                  "control_gross_R": means[2 * indices + 1].mean(),
                                  "contrast_R": value, "contrast_R_lo": lower, "contrast_R_hi": upper,
                                  "delta_native_R": value - contrasts[native_index],
                                  "delta_native_R_lo": delta_lower, "delta_native_R_hi": delta_upper,
                                  "calendar_days": int(mask.sum())})
    frames = {"summary": pd.DataFrame(summary_rows), "contrast": pd.DataFrame(contrast_rows),
              "resolution": pd.DataFrame(resolution_rows), "yearly": pd.DataFrame(year_rows),
              "daily": pd.DataFrame(daily_rows)}
    for name, frame in frames.items():
        frame.to_csv(run / f"{name}.csv", index=False, float_format="%.12g")
    checks = {"complete": not failures, "analyzed_variants": len(variants), "analyzed_jobs": len(arm_keys),
              "calendar_days": len(days), "calendar_first": days[0].strftime("%Y-%m-%d"),
              "calendar_last": days[-1].strftime("%Y-%m-%d"), "bootstrap_draws": BOOTSTRAPS,
              "bootstrap_seed": SEED, "bootstrap_batch": BATCH, "point_value": pv,
              "native_replication": replication,
              "tester_reconciliation": {"all_passed": True, "jobs": len(tester_checks), "details": tester_checks},
              "excluded_jobs": [{"variant": key[0], "mode": key[1], "reason": reason} for key, reason in failures.items()]}
    (run / "analysis_checks.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    status = "PROVISIONAL: complete job pairs only.\n\n" if failures else "All manifest jobs completed and their collected output hashes match.\n\n"
    report = ["# Fixed-grid MNQ granularity experiment\n\n", status,
              f"Native RTL ({replication[0]['trades']:,} trades) and control ({replication[1]['trades']:,} trades) reproduce every prior trade field exactly; CSV byte equality: "
              f"RTL={replication[0]['byte_equal']}, control={replication[1]['byte_equal']}.\n\n",
              f"All {len(tester_checks)} tester summaries reconcile trade counts and gross ledger profit totals within $0.000001; tags, RR1 and recorded strategy settings pass. Control orders and fills are associated within the same M30 bar; exact-boundary timestamp fractions are descriptive because the first generated tick may be delayed.\n\n",
              f"Recovered {sum(c['recovered_trades'] for c in tester_checks):,} positions omitted by the original OnTick logger, using original order requested price minus SL and complete deal times/profits. Raw files and every field of originally logged rows remain intact. Recovered excursions and signal labels are unknown (NaN), and are unused in this analysis. Per-job ledger_audit.json files record provenance and recovery counts.\n\n",
              f"R uses recorded candle range times ${pv:g}/point. Gross results exclude costs; net results deduct ${COST:.2f} per trade, matching prior analyses. "
              "All ledger candle ranges are integer multiples of their configured grid step.\n\n",
              f"The common calendar has {len(days):,} native M1 source dates ({checks['calendar_first']} to {checks['calendar_last']}); "
              "zero-trade sessions are retained. All strategies use the same 2,000 paired bootstrap draws of whole entry days within each period "
              f"(seed {SEED} plus period index). Percentile intervals are 95%. Mean R is total sampled R divided by total sampled trades, not an unweighted mean of daily averages.\n\n",
              "RTL minus control compares two complete strategies with different entries, stops and opportunities while flat. It does not isolate a causal breakout-entry effect. "
              "Equal-origin means average origin-level expectancy differences; origins are equally weighted and are not independent data sets. "
              "Their intervals preserve covariance with each other and with native. Daily resampling treats days as independent and does not capture longer serial dependence. "
              "This is exploratory sensitivity analysis, without a confirmatory gate.\n\n",
              "## Equal-weight means across grid origins\n\n",
              markdown_table(frames["contrast"].query("scope == 'equal_origin_mean'"),
                             ["period", "k", "origins", "rtl_gross_R", "control_gross_R", "contrast_R", "contrast_R_lo", "contrast_R_hi",
                              "delta_native_R", "delta_native_R_lo", "delta_native_R_hi"]),
              "\n\n## Individual grid origins\n\n",
              markdown_table(frames["contrast"].query("scope == 'origin'"),
                             ["period", "key", "k", "origin_ticks", "contrast_R", "contrast_R_lo", "contrast_R_hi",
                              "delta_native_R", "delta_native_R_lo", "delta_native_R_hi"]),
              "\n\nFiles: summary.csv (trade metrics and mean gross-R intervals), contrast.csv (paired strategy and native comparisons), "
              "resolution.csv (traded candle size in points, native ticks and coarse grid levels), yearly.csv, daily.csv (aligned day totals), "
              "and analysis_checks.json (replication and completion validation). Trade-size summaries describe executed trades and are not signal-eligibility counts.\n"]
    (run / "ANALYSIS.md").write_text("".join(report), encoding="utf-8")
    print(f"Analyzed {len(variants)} variants / {len(arm_keys)} jobs; native ledgers reproduce exactly.")
    print(frames["contrast"].query("scope == 'equal_origin_mean'")[["period", "k", "origins", "rtl_gross_R", "control_gross_R",
          "contrast_R", "delta_native_R", "delta_native_R_lo", "delta_native_R_hi"]].to_string(index=False, float_format=lambda x: f"{x:+.4f}"))
    print(f"Wrote analysis tables and report to {run}")
    return frames, checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=RUN)
    parser.add_argument("--partial", action="store_true", help="Analyse complete pairs only; native pair is still required")
    args = parser.parse_args()
    try:
        analyse(args.run_dir, partial=args.partial)
    except (OSError, ValueError, RuntimeError, AssertionError, KeyError) as exc:
        parser.exit(1, f"Granularity analysis failed: {exc}\n")


if __name__ == "__main__":
    main()

