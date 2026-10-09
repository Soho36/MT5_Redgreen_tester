"""Export descriptive frozen-support cell, size-bin and session path metrics.

Reconstructs the validated primary matched estimates before writing anything.
Group summaries renormalize the existing panel cell weights, then derive
conditional quantities from weighted joint events and weighted reach rates.
No new support, filters, bootstrap intervals or strategy rules are introduced.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_path_experiment as analysis

RUN = analysis.RUN
TOL = 1e-8


def require(condition, message):
    analysis.require(condition, message)


def validate_inputs(run):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    proof = json.loads((run / "analysis_checks.json").read_text(encoding="utf-8"))
    require(proof.get("all_passed") is True, "The frozen path analysis did not pass")
    require(proof.get("analyzer_sha256") == analysis.digest(analysis.__file__),
            "Analyzer code differs from the validated analysis")
    analysis.verify_manifest(run, manifest)
    source = proof["source_validation"]
    for filename, key in (("source_calendar.json", "source_calendar_sha256"),
                          ("source_checks.json", "source_checks_sha256")):
        require(analysis.digest(run / filename) == source[key], f"Analysis source provenance changed: {filename}")
    calendar = json.loads((run / "source_calendar.json").read_text(encoding="utf-8"))
    require(calendar["source_metadata"] == source["source_metadata"], "Validated source metadata differs")
    paths = pd.read_csv(run / "trade_paths.csv", parse_dates=["day"])
    strata = pd.read_csv(run / "strata.csv")
    matched = pd.read_csv(run / "matched_metrics.csv")
    require(np.isfinite(paths[analysis.FEATURES].to_numpy()).all(), "Nonfinite validated path features")
    require(not paths.duplicated(["arm", "position_id"]).any(), "Repeated validated position")
    jobs = {j["tag"]: j for j in proof["jobs"]}
    require(set(jobs) == {j["tag"] for j in manifest["jobs"]}, "Analysis job identities differ")
    for job in manifest["jobs"]:
        tag = job["tag"]
        arm = job["instrument"] + "__" + job["mode"]
        current = paths.loc[paths.arm == arm].set_index("position_id")
        original = analysis.read(run / f"path_{tag}_trades.csv").set_index("position_id")
        require(len(current) == len(original) == jobs[tag]["trades"] and jobs[tag]["all_passed"] is True,
                f"{tag}: validated path count differs")
        require(set(current.index) == set(original.index), f"{tag}: validated position identities differ")
        current = current.reindex(original.index)
        for name in original.columns:
            if pd.api.types.is_numeric_dtype(original[name]):
                require(np.allclose(current[name].to_numpy(dtype=float), original[name].to_numpy(dtype=float),
                                    atol=TOL, rtol=0, equal_nan=True), f"{tag}: validated collector column differs: {name}")
            else:
                require(np.array_equal(current[name].fillna("").to_numpy(), original[name].fillna("").to_numpy()),
                        f"{tag}: validated collector column differs: {name}")
    provenance = {filename: analysis.digest(run / filename) for filename in
                  ("manifest.json", "analysis_checks.json", "trade_paths.csv", "strata.csv", "matched_metrics.csv")}
    return paths, strata, matched, proof, provenance


def counts(frame):
    return {"trades":len(frame), "entry_days":frame.day.nunique(),
            "reach05_positions":int(frame.hit05.sum()), "reach1_positions":int(frame.hit1.sum()),
            "stop_before1_positions":int(frame.stopbefore1.sum()), "stop_after1_positions":int(frame.stopafter1.sum()),
            "neither_positions":int(frame.neither.sum()),
            "same_bar_check_positions":int((frame.actual_same_bar_close_above+frame.actual_same_bar_close_below).sum()),
            "eventual_geometric_qualifying_positions":int(frame.any_geometric_qualifying_close_after1.sum()),
            "eventual_rule_qualifying_positions":int(frame.any_rule_qualifying_check_after1.sum())}


def export(run=RUN):
    run = Path(run)
    paths, strata, matched, proof, provenance = validate_inputs(run)
    require(set(matched.loc[matched["sample"] == "primary", "metric"]) == set(analysis.OUTPUTS),
            "Primary matched metric schema differs")
    primary = paths.loc[paths.primary].copy()
    cell_rows, group_rows, reconstructions = [], [], []
    for period, lo, hi in analysis.PERIODS:
        period_data = primary.loc[primary.year.between(lo, hi)]
        for panel in ("six_arm_common", "coarse_ES_four_arm"):
            for basis in ("effective", "native_ticks"):
                support = strata.loc[(strata.period == period) & (strata.panel == panel) &
                                     (strata.size_basis == basis) & strata.supported].copy()
                expected = matched.loc[(matched.period == period) & (matched.panel == panel) &
                                       (matched.size_basis == basis) & (matched["sample"] == "primary")]
                if support.empty:
                    require(expected.empty, f"{period}/{panel}/{basis}: estimates without supported cells")
                    continue
                require(not support.duplicated(["arm", "cell"]).any(), "Duplicate frozen support record")
                weights = support[["cell", "weight"]].drop_duplicates()
                require(not weights.cell.duplicated().any(), "Arm-specific fixed weights differ")
                require(np.isclose(weights.weight.sum(), 1., atol=TOL, rtol=0), "Panel fixed weights do not sum to one")
                arms = sorted(support.arm.unique())
                require(len(support) == len(weights)*len(arms), "Frozen common support is incomplete across arms")
                column = "cell_" + basis
                grouped = period_data.groupby(["arm", column], sort=True)
                means = grouped[analysis.FEATURES].mean()
                trade_counts, day_counts = grouped.size(), grouped.day.nunique()
                keys = pd.MultiIndex.from_frame(support[["arm", "cell"]])
                base = means.reindex(keys).to_numpy()
                require(np.isfinite(base).all(), "Supported cell features missing")
                require(np.array_equal(trade_counts.reindex(keys).to_numpy(), support.trades.to_numpy()) and
                        np.array_equal(day_counts.reindex(keys).to_numpy(), support.entry_days.to_numpy()),
                        f"{period}/{panel}/{basis}: primary cell counts differ from frozen strata")
                metrics = analysis.derive_metrics(base)
                meta = {"period":period, "panel":panel, "size_basis":basis, "sample":"primary"}
                for i, (_, cell) in enumerate(support.iterrows()):
                    arm_data = period_data.loc[period_data.arm == cell.arm]
                    selected = arm_data.loc[arm_data[column] == cell.cell]
                    instrument, mode = cell.arm.split("__")
                    cell_rows.append({**meta, "cell":int(cell.cell), "year":int(cell.year), "session":cell.session,
                                      "bin_index":int(cell.bin_index), "bin_lower":cell.bin_lower, "bin_upper":cell.bin_upper,
                                      "arm":cell.arm, "instrument":instrument, "mode":mode, "weight":cell.weight,
                                      "panel_supported_cells":len(weights), "period_primary_trades":len(arm_data),
                                      **counts(selected), **dict(zip(analysis.OUTPUTS,metrics[i]))})
                # Verify full weighted reconstruction before creating any files.
                for arm in arms:
                    rows = support.arm.to_numpy() == arm
                    weighted = np.sum(base[rows]*support.loc[rows,"weight"].to_numpy()[:,None],axis=0)
                    values = analysis.derive_metrics(weighted)
                    instrument, mode = arm.split("__")
                    ref = expected.loc[(expected.instrument == instrument)&(expected["mode"] == mode)].set_index("metric")
                    require(set(ref.index) == set(analysis.OUTPUTS), f"Matched output missing: {period}/{panel}/{basis}/{arm}")
                    require(np.allclose(values,ref.reindex(analysis.OUTPUTS).value.to_numpy(),atol=TOL,rtol=0,equal_nan=True),
                            f"Weighted primary reconstruction differs: {period}/{panel}/{basis}/{arm}")
                    reconstructions.append({"period":period,"panel":panel,"size_basis":basis,"arm":arm,
                                            "metrics":len(values),"maximum_absolute_difference":
                                            float(np.nanmax(np.abs(values-ref.reindex(analysis.OUTPUTS).value.to_numpy())))})
                # Condition the existing overlap population on one category,
                # then renormalize its already-frozen cell weights.
                for kind, category_column in (("size_bin","bin_index"),("session","session")):
                    for category in support[category_column].drop_duplicates():
                        mask = support[category_column] == category
                        category_support = support.loc[mask]
                        category_cells = category_support.cell.unique()
                        mass = category_support[["cell","weight"]].drop_duplicates().weight.sum()
                        for arm in arms:
                            rows = mask.to_numpy() & (support.arm.to_numpy() == arm)
                            weighted = np.sum(base[rows]*support.loc[rows,"weight"].to_numpy()[:,None],axis=0)/mass
                            values = analysis.derive_metrics(weighted)
                            arm_data = period_data.loc[period_data.arm == arm]
                            selected = arm_data.loc[arm_data[column].isin(category_cells)]
                            eligible = arm_data.loc[arm_data["bin_"+basis] == category] if kind == "size_bin" else arm_data.loc[arm_data.session == category]
                            instrument, mode = arm.split("__")
                            bucket = int(category) if kind == "size_bin" else None
                            label = (f"[{analysis.BINS[bucket]:g},{analysis.BINS[bucket+1]:g})"
                                     if bucket is not None else str(category))
                            group_rows.append({**meta, "group_kind":kind,"group":label,
                                               "session":str(category) if kind == "session" else "all_supported_sessions",
                                               "bin_index":bucket,"bin_lower":analysis.BINS[bucket] if bucket is not None else np.nan,
                                               "bin_upper":analysis.BINS[bucket+1] if bucket is not None else np.nan,
                                               "arm":arm,"instrument":instrument,"mode":mode,
                                               "supported_cells":len(category_cells),"panel_supported_cells":len(weights),
                                               "panel_weight_mass":mass,"within_group_weight_sum":1.,
                                               "period_primary_trades":len(arm_data),
                                               "primary_group_trades":len(eligible),"primary_group_entry_days":eligible.day.nunique(),
                                               "retained_primary_group_fraction":len(selected)/len(eligible) if len(eligible) else np.nan,
                                               **counts(selected),**dict(zip(analysis.OUTPUTS,values))})
    cells, groups = pd.DataFrame(cell_rows), pd.DataFrame(group_rows)
    require(len(cells)>0 and len(groups)>0, "No supported path groups to export")
    cells.to_csv(run/"cell_metrics.csv",index=False,float_format="%.12g")
    groups.to_csv(run/"group_metrics.csv",index=False,float_format="%.12g")
    result = {"all_passed":True,"descriptive_point_estimates_only":True,"sample":"primary",
              "no_new_support_or_filter":True,"conditional_rates":"ratio of weighted joint event to weighted reach/check probability",
              "group_weights":"original fixed panel cell weights renormalized within session or size-bin category",
              "analysis_analyzer_sha256":proof["analyzer_sha256"],"exporter_sha256":analysis.digest(__file__),
              "inputs":provenance,"outputs":{name:analysis.digest(run/name) for name in ("cell_metrics.csv","group_metrics.csv")},
              "cell_rows":len(cells),"group_rows":len(groups),"reconstructed_primary_arms":len(reconstructions),
              "reconstructed_primary_metric_values":sum(r["metrics"] for r in reconstructions),
              "reconstruction_maximum_absolute_difference":max(r["maximum_absolute_difference"] for r in reconstructions),
              "reconstructions":reconstructions}
    (run/"group_checks.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(f"PASS: reconstructed {result['reconstructed_primary_metric_values']:,} primary matched values; "
          f"exported {len(cells):,} cells and {len(groups):,} descriptive groups.",flush=True)
    return cells,groups,result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir",type=Path,default=RUN)
    args=parser.parse_args()
    try:
        export(args.run_dir)
    except (OSError,ValueError,AssertionError,KeyError) as exc:
        parser.exit(1,f"Grouped path export failed: {exc}\n")


if __name__=="__main__":
    main()

