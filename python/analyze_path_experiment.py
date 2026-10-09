"""Validate and analyse complete passive-observer post-entry paths.

Uses frozen year/session/candle-resolution overlap strata and shared whole-day
bootstrap draws. Original raw ledgers must reproduce, and complete collector
positions must match audited reference trades. Does not alter trading rules.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_instrument_baseline import PERIODS
from build_coarse_nq import grid as coarse_grid
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports" / "path_experiment_20261009"
ARMS = [(i, m) for i in ("NQ", "NQcoarse", "ES") for m in ("rtl", "control")]
BINS = np.array([0, 8, 16, 24, 32, 48, 64, 128, np.inf])
SEED, BOOTSTRAPS, MIN_N, MIN_DAYS, BATCH = 20261009, 1000, 30, 10, 32
HOLES = {"2020-02-28", "2020-06-30"}
TOL = 1e-6
RETENTION = ("stop_before_same_bar_check", "administrative_exit_before_same_bar_check",
             "actual_same_bar_close_above", "actual_same_bar_close_below", "no_available_same_bar_check")
FEATURES = ["gross_R", "mae_R", "mfe_R", "hit05", "hit1", "stopbefore1", "stopafter1", "neither",
            *RETENTION, "hyp_close_above", "hyp_close_available", "pre1_hit_sum", "hit_at_exit",
            "same_check_rule_success", "locked_target_mismatch", "later_check_available", "later_check_above",
            "any_geometric_qualifying_close_after1", "any_rule_qualifying_check_after1"]
OUTPUTS = ["gross_R", "mean_mae_R", "mean_mfe_R", "p_reach05", "p_reach1", "p_stop_before1",
           "p_stop_after1", "p_neither", *["p_" + c + "_given_reach1" for c in RETENTION],
           "p_hypothetical_close_above_given_available_touch_bar",
           "p_hypothetical_touch_bar_close_available_given_reach1", "mean_mae_before1_given_reach1",
           "p_first1_at_exit_given_reach1", "p_actual_rule_condition_given_same_bar_check",
           "p_locked_target_mismatch", "p_close_above_given_actual_same_bar_check",
           *["p_joint_" + c for c in RETENTION],
           "p_first_actual_check_available_given_reach1", "p_close_above_given_first_actual_check",
           "p_eventual_close_above_given_reach1", "p_eventual_rule_qualifies_given_reach1"]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def read(path):
    with Path(path).open("rb") as f:
        prefix = f.read(2)
    return pd.read_csv(path, sep="\t", encoding="utf-16" if prefix in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig")


def times(series, empty=False):
    return pd.to_datetime(series.replace("", np.nan), format="%Y.%m.%d %H:%M:%S", errors="coerce" if empty else "raise")


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def close(a, b, message, atol=TOL):
    require(np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float), rtol=0, atol=atol), message)


def verify_manifest(run, manifest):
    require({(j["instrument"], j["mode"]) for j in manifest["jobs"]} == set(ARMS) and len(manifest["jobs"]) == 6,
            "Manifest must contain exactly the six instrument/mode arms")
    require(manifest.get("native_tick") == .25, "Frozen native tick differs")
    require(manifest.get("periods") == [list(p) for p in PERIODS], "Frozen periods differ")
    require(set(manifest.get("exclusion_dates", [])) == HOLES, "Frozen source-hole exclusions differ")
    settings = manifest.get("matching", {})
    require(settings.get("min_trades") == MIN_N and settings.get("min_entry_days") == MIN_DAYS,
            "Frozen matching support differs")
    require(settings.get("size_edges") == [0,8,16,24,32,48,64,128,None], "Frozen size bins differ")
    require(settings.get("sessions") == [["pre_cash",60,990],["early_cash",990,1200],["late_cash",1200,1410]],
            "Frozen source-clock sessions differ")
    bs = manifest.get("bootstrap", {})
    require(bs.get("draws") == BOOTSTRAPS and bs.get("seed") == SEED and bs.get("fixed_support_weights") is True,
            "Frozen bootstrap settings differ")
    require(bool(manifest.get("input_hashes")), "Frozen input hashes are absent")
    for name, expected in manifest.get("input_hashes", {}).items():
        p = Path(name)
        if not p.is_absolute():
            p = ROOT / p
        require(p.is_file() and digest(p) == expected, f"Frozen input changed: {p}")
    for job in manifest["jobs"]:
        mark = run / f"{job['tag']}.completed.json"
        require(mark.is_file(), f"Incomplete job {job['tag']}; finish run_path_experiment.py first")
        done = json.loads(mark.read_text(encoding="utf-8"))
        require(done.get("tag") == job["tag"], f"Completion tag differs: {mark}")
        for filename in job["outputs"]:
            p = run / filename
            require(p.is_file() and digest(p) == done.get("outputs", {}).get(filename),
                    f"Completed output missing or changed: {p}")
        proof_path = run / f"{job['tag']}.replication.json"
        require(proof_path.is_file(), f"Replication gate missing: {proof_path}")
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
        require(proof.get("tag") == job["tag"] and proof.get("raw_byte_equal") is True and
                proof.get("complete_times_profits_risk_equal") is True and proof.get("observer_errors") == 0,
                f"Replication gate failed: {job['tag']}")
        require(proof.get("path_sha256") == digest(run / f"path_{job['tag']}_trades.csv"),
                f"Replication gate binds a different collector: {job['tag']}")


def validated_sources(run, manifest):
    path = run / "source_calendar.json"
    require(path.is_file(), "True source calendar missing; run validate_path_sources.py")
    calendar = json.loads(path.read_text(encoding="utf-8"))
    require(calendar.get("all_source_checks_passed") is True and calendar.get("coarse_m30_quantization_exact") is True,
            "Source calendar validation failed")
    source_checks = json.loads((run / "source_checks.json").read_text(encoding="utf-8"))
    jobs = source_checks.get("jobs", [])
    require(source_checks.get("all_passed") is True and len(jobs) == 6 and
            {j["tag"] for j in jobs} == {j["tag"] for j in manifest["jobs"]},
            "All six definitive source bindings are required; rerun validate_path_sources.py")
    require(all(j.get("signal_ohlc_exact") is True and j.get("closed_bar_closes_exact") is True for j in jobs),
            "Source-order/bar binding flags failed")
    frames, union = {}, set()
    for instrument, filename in manifest["source_files"].items():
        cache = run / f"source_{instrument}_m30.csv"
        info = json.loads((run / f"source_{instrument}_metadata.json").read_text(encoding="utf-8"))
        require(info == calendar["source_metadata"][instrument], f"{instrument}: calendar/source metadata differ")
        require(info["source_sha256"] == manifest["input_hashes"][str(Path(filename))] and
                info["m30_sha256"] == digest(cache), f"{instrument}: source cache hash binding failed")
        frame = pd.read_csv(cache, index_col=0, parse_dates=True)
        require(len(frame) == info["m30_bars"] and not frame.index.duplicated().any(), f"{instrument}: cached M30 count/identity")
        require(list(frame.columns) == ["open","high","low","close"] and
                np.array_equal(frame.to_numpy(), np.rint(frame.to_numpy())), f"{instrument}: integer-quarter-point OHLC cache")
        require((frame.index >= pd.Timestamp(manifest["start"])).all() and
                (frame.index < pd.Timestamp(manifest["end_exclusive"])).all(), f"{instrument}: source cache date bounds")
        frames[instrument] = frame
        union |= set(info["trading_days"])
    require(calendar["trading_days"] == sorted(union) and len(union) == source_checks["common_calendar_days"],
            "True union source calendar differs")
    native, coarse = frames["NQ"], frames["NQcoarse"]
    require(native.index.equals(coarse.index), "Coarse/native source timestamps differ")
    grids = coarse_grid(native.index.year.to_numpy())[:, None] * 4
    require(np.array_equal(np.rint(native.to_numpy() / grids) * grids, coarse.to_numpy()),
            "Existing coarse source is not frozen yearly ties-even quantization")
    days = pd.DatetimeIndex(pd.to_datetime(calendar["trading_days"]))
    return frames, days, {"source_calendar_sha256":digest(path), "source_checks_sha256":digest(run / "source_checks.json"),
                          "source_metadata":calendar["source_metadata"]}


def retention_paths(t, bars, checks, tag, source=None):
    """Partition +1 reachers using the actual check closing the same hit bar.

    The check joins stay keyed by independent position identifier. Later checks
    supply secondary flags only; they never replace a missing same-bar check.
    """
    t = t.copy()
    early = (ROOT / "mt5/experts/early_closes.mqh").read_text(encoding="utf-8-sig")
    def calendar_array(name):
        return [int(v) for v in re.search(rf"{name}\[EC_COUNT\]\s*=\s*\{{([^}}]+)\}}",early).group(1).split(",")]
    cutoffs = dict(zip(calendar_array("EC_DATE"), calendar_array("EC_FLAT_MIN")))
    flag_columns = ["hyp_close_available", "hyp_close_above", "same_check_rule_success", "rule_exit_before_touch_bar_check",
                    "later_check_available", "later_check_above", "any_geometric_qualifying_close_after1", "any_rule_qualifying_check_after1"]
    detail_columns = ["same_bar_check_time_msc", "same_bar_check_close", "first_later_check_lag_bars",
                      "first_later_check_time_msc", "first_later_check_close", "first_later_check_actual_rule_condition",
                      "eventual_geometric_qualifying_lag_bars", "eventual_rule_qualifying_lag_bars"]
    t["retention_category"] = "unreached1"
    t[flag_columns],t[detail_columns] = 0.,np.nan
    hit = t.loc[t.hit1 == 1].copy()
    if len(hit):
        target = (hit.actual_fill+hit.actual_risk).to_numpy()
        barbook = bars.set_index("closed_bar")
        b = barbook.reindex(hit.hit1_bar)
        has_bar = b.eval_time_msc.notna().to_numpy()
        require((b.eval_time_msc.to_numpy()[has_bar] >= hit.first_hit_1_msc.to_numpy()[has_bar]).all(),
                f"{tag}: touch occurs after its bar-close evaluation")
        nominal_close = (hit.hit1_bar+pd.Timedelta(minutes=30)).astype("datetime64[ns]").astype("int64").to_numpy()//1000000
        eval_ms = np.where(has_bar,b.eval_time_msc.to_numpy(),nominal_close)
        before = hit.exit_time_msc.to_numpy() <= eval_ms
        if source is not None:
            hypothetical = source.close.reindex(hit.hit1_bar).to_numpy()/4
        else:
            hypothetical = b.closed_close.to_numpy()
        hit["hyp_close_available"] = np.isfinite(hypothetical).astype(float)
        hit["hyp_close_above"] = (hypothetical >= target).astype(float)
        checkbook = checks.set_index(["position_id","closed_bar"])
        index = pd.MultiIndex.from_arrays([hit.position_id,hit.hit1_bar],names=["position_id","closed_bar"])
        same = checkbook.reindex(index)
        has_same = same.check_time_msc.notna().to_numpy()
        require((same.check_time_msc.to_numpy()[has_same] >= hit.first_hit_1_msc.to_numpy()[has_same]).all(),
                f"{tag}: same-bar check precedes touch")
        hit["same_bar_check_time_msc"],hit["same_bar_check_close"] = same.check_time_msc.to_numpy(),same.closed_close.to_numpy()
        hit["same_check_rule_success"] = np.where(has_same,same.condition.to_numpy(),0.)
        reached = checks.merge(hit[["position_id","hit1_bar","first_hit_1_msc","actual_fill","actual_risk"]],
                               on="position_id",how="inner",suffixes=("","_path"))
        # checks already expose actual_fill/actual_risk; synthetic fixtures may
        # provide only path columns, so bind the target by position explicitly.
        target_book = pd.Series(target,index=hit.position_id)
        reached["actual_target"] = reached.position_id.map(target_book)
        prior = reached.loc[(reached.closed_bar < reached.hit1_bar)&reached.condition.astype(bool),"position_id"]
        prior_success = hit.position_id.isin(prior).to_numpy()
        exit_bar = hit.exit.dt.floor("30min")
        minute = exit_bar.dt.hour*60+exit_bar.dt.minute
        cutoff = exit_bar.dt.strftime("%Y%m%d").astype(int).map(cutoffs).fillna(1410)
        flatten_evidence = ((minute >= cutoff)|(hit.exit.dt.normalize()!=hit.entry.dt.normalize())).to_numpy()
        stop = hit.exit_reason.to_numpy()==4
        above = same.closed_close.to_numpy() >= target
        hit["retention_category"] = np.select([has_same&above,has_same&~above,~has_same&before&stop,
                                                ~has_same&before&~stop&flatten_evidence&~prior_success],
                                               ["actual_same_bar_close_above","actual_same_bar_close_below","stop_before_same_bar_check",
                                                "administrative_exit_before_same_bar_check"],default="no_available_same_bar_check")
        hit["rule_exit_before_touch_bar_check"] = (~has_same&before&prior_success).astype(float)
        later = reached.loc[(reached.closed_bar >= reached.hit1_bar)&(reached.check_time_msc >= reached.first_hit_1_msc)].sort_values("check_time_msc")
        first = later.drop_duplicates("position_id").set_index("position_id").reindex(hit.position_id)
        hit["later_check_available"] = first.check_time_msc.notna().to_numpy().astype(float)
        hit["later_check_above"] = (first.closed_close.to_numpy() >= target).astype(float)
        hit["first_later_check_time_msc"],hit["first_later_check_close"] = first.check_time_msc.to_numpy(),first.closed_close.to_numpy()
        hit["first_later_check_actual_rule_condition"] = first.condition.to_numpy()
        hit["first_later_check_lag_bars"] = ((first.closed_bar.to_numpy()-hit.hit1_bar.to_numpy())/np.timedelta64(30,"m")).astype(float)
        for feature, lag, eligible in (
                ("any_geometric_qualifying_close_after1","eventual_geometric_qualifying_lag_bars",later.closed_close>=later.actual_target),
                ("any_rule_qualifying_check_after1","eventual_rule_qualifying_lag_bars",later.condition.astype(bool))):
            q = later.loc[eligible].drop_duplicates("position_id").set_index("position_id").reindex(hit.position_id)
            hit[feature] = q.check_time_msc.notna().to_numpy().astype(float)
            hit[lag] = ((q.closed_bar.to_numpy()-hit.hit1_bar.to_numpy())/np.timedelta64(30,"m")).astype(float)
        columns = ["retention_category",*flag_columns,*detail_columns]
        t.loc[hit.index,columns] = hit[columns]
    for c in RETENTION:
        t[c] = (t.retention_category == c).astype(float)
    require(np.array_equal(t[list(RETENTION)].sum(axis=1),t.hit1),f"{tag}: touch-bar categories do not partition reachers")
    return t


def validated_paths(run, job, source=None):
    tag = job["tag"]
    paths = {kind: run / f"path_{tag}_{kind}.csv" for kind in ("trades", "bars", "checks", "orders", "summary")}
    t, bars, checks, orders, summary = (read(paths[k]) for k in ("trades", "bars", "checks", "orders", "summary"))
    raw, old_raw, audited, stats = (read(run / job["outputs"][0]), read(job["reference_raw"]),
                                   read(job["reference_audited"]), read(run / job["outputs"][1]))
    require(digest(run / job["outputs"][0]) == digest(job["reference_raw"]), f"{tag}: original raw bytes differ")
    pd.testing.assert_frame_equal(raw, old_raw, check_exact=True)
    require(len(summary) == len(stats) == 1, f"{tag}: summary/stat row count")
    s, ts = summary.iloc[0], stats.iloc[0]
    require(s.run_tag == ts.run_tag == tag, f"{tag}: wrong collector/tester tag")
    require(s.observer_errors == s.active_at_end == 0 and s.counts_match == s.profit_match == 1, f"{tag}: observer summary failed")
    require("max_entry_lag_msc" in summary and "first_quote_time_msc" in t, f"{tag}: first-observation timing gate is missing")
    require(s.max_entry_lag_msc == 0 and (t.first_quote_time_msc == t.entry_time_msc).all(), f"{tag}: incomplete entry quote observation")
    require(not t.position_id.duplicated().any() and not t.entry_order.duplicated().any(), f"{tag}: duplicate position/order")
    require(len(t) == len(audited) == s.exported_positions == s.history_entries == s.history_exits == s.tester_trades == ts.trades,
            f"{tag}: complete trade counts differ")
    close([t.trade_profit.sum()] * 4, [s.exported_profit, s.history_profit, s.tester_profit, ts.net_profit], f"{tag}: profit totals")
    close(t.loc[t.trade_profit > 0, "trade_profit"].sum(), ts.gross_profit, f"{tag}: gross gains")
    close(t.loc[t.trade_profit < 0, "trade_profit"].sum(), ts.gross_loss, f"{tag}: gross losses")
    require(ts.risk_reward == 1 and ts.max_red_run == (3 if job["mode"] == "rtl" else 0), f"{tag}: RR/cap setting")
    for field, value in (("early_close_calendar", 1), ("flatten_fallback", 1), ("trail_distance_r", 0)):
        require(field in ts.index and ts[field] == value, f"{tag}: setting {field}")
    old = audited.set_index("ticket")
    current = t.set_index("position_id")
    require(set(old.index) == set(current.index), f"{tag}: audited position identities differ")
    current = current.reindex(old.index)
    for c in ("entry_time", "exit_time"):
        require(np.array_equal(current[c], old[c]), f"{tag}: audited {c} differs")
    close(current.trade_profit, old.trade_profit, f"{tag}: audited PnL differs")
    close(current.requested_risk, old.candle_range, f"{tag}: audited original order risk differs")
    t["entry"], t["exit"] = times(t.entry_time), times(t.exit_time)
    close(t.entry_time_msc // 1000, t.entry.astype("datetime64[ns]").astype("int64") / 1e9, f"{tag}: entry clock")
    close(t.exit_time_msc // 1000, t.exit.astype("datetime64[ns]").astype("int64") / 1e9, f"{tag}: exit clock")
    require((t.exit_time_msc >= t.entry_time_msc).all() and (t.quote_samples > 0).all(), f"{tag}: quote coverage/order")
    close(t.requested_entry - t.initial_sl, t.requested_risk, f"{tag}: requested risk")
    close(t.actual_fill - t.initial_sl, t.actual_risk, f"{tag}: actual risk")
    require((t.actual_risk > 0).all() and (t.requested_risk > 0).all(), f"{tag}: nonpositive risk")
    close((t.exit_price - t.actual_fill) * float(job.get("pv", job["point_value"])), t.trade_profit, f"{tag}: price/PnL value")
    close(np.maximum(0, (t.actual_fill - t.min_bid) / t.actual_risk), t.mae_R, f"{tag}: MAE extrema")
    close(np.maximum(0, (t.max_bid - t.actual_fill) / t.actual_risk), t.mfe_R, f"{tag}: MFE extrema")
    require((t.min_bid <= t.entry_bid + TOL).all() and (t.max_bid >= t.entry_bid - TOL).all(), f"{tag}: entry quote outside extrema")
    require((t.min_bid <= t.exit_price + TOL).all() and (t.max_bid >= t.exit_price - TOL).all(), f"{tag}: exit fill outside extrema")
    require((t.max_mae_before_first_hit_1R >= 0).all() and
            (t.max_mae_before_first_hit_1R <= t.mae_R + TOL).all(), f"{tag}: pre-touch MAE")
    for suffix, threshold in (("05", .5), ("1", 1.0)):
        ms = t[f"first_hit_{suffix}_msc"]
        hit = ms > 0
        bar = times(t[f"first_hit_{suffix}_bar"], empty=True)
        require(np.array_equal(hit, t.mfe_R >= threshold - 1e-9), f"{tag}: hit{suffix} disagrees with MFE")
        require(((ms[hit] >= t.entry_time_msc[hit]) & (ms[hit] <= t.exit_time_msc[hit])).all(), f"{tag}: hit{suffix} outside trade")
        require(bar[~hit].isna().all() and bar[hit].notna().all(), f"{tag}: hit{suffix} bar presence")
        require(np.array_equal(bar[hit], pd.to_datetime(ms[hit], unit="ms").dt.floor("30min")), f"{tag}: hit{suffix} bar binding")
        t[f"hit{suffix}"] = hit.astype(float)
        t[f"hit{suffix}_bar"] = bar
    require(((t.first_hit_05_msc <= t.first_hit_1_msc) | (t.hit1 == 0)).all(), f"{tag}: hit ordering")
    successful = orders.loc[orders.order > 0].copy()
    require(not successful.order.duplicated().any(), f"{tag}: repeated successful arming order")
    omap = successful.set_index("order").reindex(t.entry_order)
    require(omap.arm_time_msc.notna().all(), f"{tag}: original arming metadata absent")
    close(omap.requested_entry, t.requested_entry, f"{tag}: requested entry association")
    close(omap.initial_sl, t.initial_sl, f"{tag}: SL association")
    close(omap.signal_high - omap.signal_low, t.requested_risk, f"{tag}: signal width association")
    require((omap.arm_time_msc.to_numpy() <= t.entry_time_msc.to_numpy()).all(), f"{tag}: submission after entry")
    require((omap.signal_mode == (0 if job["mode"] == "rtl" else 3)).all(), f"{tag}: signal mode")
    require((omap.order_type == (4 if job["mode"] == "rtl" else 0)).all(), f"{tag}: order type")
    require(((omap.signal_high >= np.maximum(omap.signal_open, omap.signal_close)) &
             (omap.signal_low <= np.minimum(omap.signal_open, omap.signal_close))).all(), f"{tag}: signal OHLC")
    t["signal_time"] = times(omap.signal_bar_open.reset_index(drop=True))
    require((t.signal_time.notna()).all(), f"{tag}: signal timestamps absent")
    t["signal_year"] = t.signal_time.dt.year
    t["effective_step"] = coarse_grid(t.signal_year.to_numpy()) if job["instrument"] == "NQcoarse" else .25
    steps = t.requested_risk / t.effective_step
    close(steps, np.rint(steps), f"{tag}: signal-grid membership")
    bars["closed_bar"] = times(bars.closed_bar_open, empty=True)
    require(not bars.eval_time_msc.duplicated().any(), f"{tag}: duplicate bar evaluation event")
    valid_bars = bars.loc[bars.closed_bar.notna()].copy()
    require(not valid_bars.closed_bar.duplicated().any(), f"{tag}: duplicate closed bar")
    close(bars.eval_time_msc // 1000, times(bars.eval_time).astype("datetime64[ns]").astype("int64") / 1e9, f"{tag}: bar clock")
    if len(checks):
        require(checks.position_id.isin(t.position_id).all(), f"{tag}: check has unknown position")
        checks["closed_bar"] = times(checks.closed_bar_open)
        require(not checks.duplicated(["position_id", "closed_bar"]).any(), f"{tag}: repeated same-bar target check")
        refs = t.set_index("position_id").reindex(checks.position_id)
        require(((checks.check_time_msc.to_numpy() >= refs.entry_time_msc.to_numpy()) &
                 (checks.check_time_msc.to_numpy() <= refs.exit_time_msc.to_numpy())).all(), f"{tag}: check outside held position")
        bound = bars.set_index("eval_time_msc").reindex(checks.check_time_msc)
        require(bound.closed_bar.notna().all() and np.array_equal(bound.closed_bar_open, checks.closed_bar_open), f"{tag}: check/bar binding")
        close(bound.closed_close, checks.closed_close, f"{tag}: check/bar price")
        close(refs.actual_fill, checks.actual_fill, f"{tag}: check/current-position fill")
        close(refs.actual_risk, checks.actual_risk, f"{tag}: check/current-position risk")
        close(refs.requested_risk, checks.requested_risk, f"{tag}: check/current-position requested risk")
        require((checks.locked_set == 1).all() and (checks.locked_risk > 0).all(), f"{tag}: invalid active locked target")
        close(checks.locked_entry + checks.locked_risk, checks.target, f"{tag}: actual rule target")
        require(np.array_equal(checks.condition.astype(bool), checks.closed_close >= checks.target), f"{tag}: actual rule comparator")
        checks["target_mismatch"] = ~np.isclose(checks.target, checks.actual_fill + checks.actual_risk, rtol=0, atol=TOL)
    else:
        checks["closed_bar"], checks["target_mismatch"] = pd.Series(dtype="datetime64[ns]"), pd.Series(dtype=bool)
    t["locked_target_mismatch"] = t.position_id.isin(checks.loc[checks.target_mismatch, "position_id"]).astype(float)
    if source is not None:
        signal_index = source.index.get_indexer(times(orders.signal_bar_open))
        require((signal_index >= 0).all(), f"{tag}: original signal absent from source")
        require(np.array_equal(orders[["signal_open","signal_high","signal_low","signal_close"]].to_numpy(),
                               source.iloc[signal_index].to_numpy()/4), f"{tag}: original signal OHLC differs from source")
        bar_index = source.index.get_indexer(valid_bars.closed_bar)
        require((bar_index >= 0).all() and np.array_equal(valid_bars.closed_close.to_numpy(),source.iloc[bar_index].close.to_numpy()/4),
                f"{tag}: observed bar close differs from source")
    require((valid_bars.eval_time_msc.to_numpy() >= (valid_bars.closed_bar+pd.Timedelta(minutes=30)).astype("datetime64[ns]").astype("int64").to_numpy()//1000000).all(),
            f"{tag}: evaluation precedes bar close")
    t = retention_paths(t,valid_bars,checks,tag,source)
    stop = t.exit_reason == 4
    t["stopbefore1"], t["stopafter1"] = (stop & (t.hit1 == 0)).astype(float), (stop & (t.hit1 == 1)).astype(float)
    t["neither"] = (~stop & (t.hit1 == 0)).astype(float)
    t["pre1_hit_sum"] = t.max_mae_before_first_hit_1R * t.hit1
    t["hit_at_exit"] = ((t.hit1 == 1) & (t.first_hit_1_msc == t.exit_time_msc)).astype(float)
    t["gross_R"] = t.trade_profit / (t.requested_risk * float(job.get("pv", job["point_value"])))
    t["instrument"], t["mode"], t["arm"] = job["instrument"], job["mode"], job["instrument"] + "__" + job["mode"]
    t["day"], t["year"] = t.entry.dt.normalize(), t.entry.dt.year
    minute = t.entry.dt.hour * 60 + t.entry.dt.minute
    t["session_id"] = np.select([minute < 990, minute < 1200], [0, 1], default=2)
    t["session"] = t.session_id.map({0: "pre_cash", 1: "early_cash", 2: "late_cash"})
    t["outside_matching_session"] = ~((minute >= 60) & (minute < 1410))
    t.loc[t.outside_matching_session,"session_id"] = 3
    t.loc[t.outside_matching_session,"session"] = "outside_matching_session"
    t["cross_date"] = t.entry.dt.normalize() != t.exit.dt.normalize()
    t["source_hole"] = t.day.dt.strftime("%Y-%m-%d").isin(HOLES)
    t["primary"] = ~t.cross_date & ~t.source_hole & ~t.outside_matching_session
    for style, x in (("effective", t.requested_risk / t.effective_step), ("native_ticks", t.requested_risk / .25)):
        bucket = np.searchsorted(BINS, x, side="right") - 1
        require(((bucket >= 0) & (bucket < len(BINS)-1)).all(), f"{tag}: invalid size bucket")
        t[f"bin_{style}"] = bucket
        t[f"cell_{style}"] = t.year * 100 + t.session_id * 10 + bucket
    t["baseline_ledger_source"] = audited.set_index("ticket").reindex(t.position_id).ledger_source.to_numpy()
    audit = {"tag": tag, "trades": len(t), "raw_rows": len(raw), "previously_recovered": int((t.baseline_ledger_source == "tester_orders_deals").sum()),
             "checks": len(checks), "locked_target_mismatch_positions": int(t.locked_target_mismatch.sum()),
             "requested_actual_risk_diff": int((~np.isclose(t.requested_risk, t.actual_risk, rtol=0, atol=TOL)).sum()),
             "rule_exit_before_touch_bar_check":int(t.rule_exit_before_touch_bar_check.sum()),
             "first_observation_zero_lag": True, "cross_date": int(t.cross_date.sum()), "source_hole_entries": int(t.source_hole.sum()),
             "hit1_at_exit": int(t.hit_at_exit.sum()), "outside_matching_session":int(t.outside_matching_session.sum()),
             "outside_session_positions":t.loc[t.outside_matching_session,["position_id","entry_time","exit_time"]].to_dict("records"),
             "all_passed": True}
    calendar = set(pd.to_datetime(bars.eval_time_msc, unit="ms").dt.normalize())
    return t, checks, audit, calendar


def derive_metrics(base):
    # Standardized conditional quantities use ratios of standardized joint
    # probabilities; no cell with zero touchers is silently discarded.
    out = base[..., :8].copy()
    values = [out[..., j] for j in range(8)]
    def ratio(a, b):
        return np.divide(a, b, out=np.full_like(np.asarray(a, dtype=float), np.nan), where=np.asarray(b) > 0)
    reach = base[..., FEATURES.index("hit1")]
    for c in RETENTION:
        values.append(ratio(base[..., FEATURES.index(c)], reach))
    values.extend([ratio(base[..., FEATURES.index("hyp_close_above")], base[..., FEATURES.index("hyp_close_available")]),
                   ratio(base[..., FEATURES.index("hyp_close_available")], reach),
                   ratio(base[..., FEATURES.index("pre1_hit_sum")], reach),
                   ratio(base[..., FEATURES.index("hit_at_exit")], reach)])
    available = base[..., FEATURES.index("actual_same_bar_close_above")] + base[..., FEATURES.index("actual_same_bar_close_below")]
    values.extend([ratio(base[..., FEATURES.index("same_check_rule_success")], available),
                   base[..., FEATURES.index("locked_target_mismatch")],
                   ratio(base[..., FEATURES.index("actual_same_bar_close_above")], available)])
    values.extend(base[..., FEATURES.index(c)] for c in RETENTION)
    values.extend([ratio(base[..., FEATURES.index("later_check_available")], reach),
                   ratio(base[..., FEATURES.index("later_check_above")], base[..., FEATURES.index("later_check_available")]),
                   ratio(base[..., FEATURES.index("any_geometric_qualifying_close_after1")], reach),
                   ratio(base[..., FEATURES.index("any_rule_qualifying_check_after1")], reach)])
    return np.stack(values, axis=-1)


def model(data, arms, weights, cell_column, day_index, label):
    groups = []
    point = np.zeros((len(arms), len(FEATURES)))
    sub = data.loc[data.arm.isin(arms)].copy()
    sub["_cell"] = sub[cell_column] if cell_column else 0
    sub = sub.loc[sub._cell.isin(weights)]
    sub["_day"] = sub.day.map(day_index)
    require(sub._day.notna().all(), "Trade day outside shared calendar")
    sub["_count"] = 1.
    fields = ["_count", *FEATURES]
    grouped = sub.groupby(["arm", "_cell", "_day"], sort=True)[fields].sum()
    for arm_idx, arm in enumerate(arms):
        for cell, weight in weights.items():
            try:
                g = grouped.xs((arm, cell), level=("arm", "_cell"))
            except KeyError as exc:
                raise ValueError(f"{label}: frozen supported cell lost all positions for {arm}/{cell}") from exc
            values = g[fields].to_numpy()
            point[arm_idx] += weight * values[:, 1:].sum(axis=0) / values[:, 0].sum()
            groups.append((arm_idx, weight, g.index.to_numpy(dtype=int), values))
    return {"label": label, "arms": arms, "groups": groups, "point": derive_metrics(point)}


def evaluate(model_data, frequencies):
    base = np.zeros((len(frequencies), len(model_data["arms"]), len(FEATURES)))
    valid = np.ones(len(frequencies), dtype=bool)
    for arm, weight, days, totals in model_data["groups"]:
        sampled = frequencies[:, days] @ totals
        n = sampled[:, 0]
        valid &= n > 0
        ratios = np.divide(sampled[:, 1:], n[:, None], out=np.zeros_like(sampled[:, 1:]), where=n[:, None] > 0)
        base[:, arm] += weight * ratios
    return derive_metrics(base), valid


def paired_bootstrap(models, day_count, seed):
    rng = np.random.default_rng(seed)
    accepted = {m["label"]: [] for m in models}
    have, attempts, rejected = 0, 0, 0
    while have < BOOTSTRAPS:
        require(attempts < BOOTSTRAPS * 20, "Too many unsupported joint bootstrap draws; intervals unavailable for frozen support")
        indices = rng.integers(0, day_count, (BATCH, day_count))
        frequencies = np.stack([np.bincount(row, minlength=day_count) for row in indices]).astype(float)
        outputs, valid = {}, np.ones(BATCH, dtype=bool)
        for m in models:
            outputs[m["label"]], okay = evaluate(m, frequencies)
            valid &= okay
        chosen = np.flatnonzero(valid)[:BOOTSTRAPS-have]
        consumed = int(chosen[-1] + 1) if len(chosen) and have + len(chosen) == BOOTSTRAPS else BATCH
        rejected += int((~valid[:consumed]).sum())
        attempts += consumed
        for label, values in outputs.items():
            accepted[label].append(values[chosen])
        have += len(chosen)
    return {k: np.concatenate(v, axis=0) for k, v in accepted.items()}, {"accepted": have, "attempted": attempts,
             "rejected": rejected, "rejected_fraction": rejected/attempts, "conditional_support_warning": rejected/attempts > .01}


def percentiles(values):
    finite = np.asarray(values)[np.isfinite(values)]
    return tuple(np.percentile(finite, [2.5, 97.5])) if len(finite) else (np.nan, np.nan)


def support(data, arms, style, period, panel):
    cell = f"cell_{style}"
    counts = data.groupby([cell, "arm"]).size().unstack("arm").reindex(columns=arms).fillna(0)
    days = data.groupby([cell, "arm"]).day.nunique().unstack("arm").reindex(index=counts.index, columns=arms).fillna(0)
    keep = (counts.min(axis=1) >= MIN_N) & (days.min(axis=1) >= MIN_DAYS)
    overlap = counts.loc[keep].min(axis=1)
    weights = (overlap / overlap.sum()).to_dict() if len(overlap) else {}
    rows = []
    for key in counts.index:
        year, session, bucket = int(key//100), int((key%100)//10), int(key%10)
        for arm in arms:
            rows.append({"period": period, "panel": panel, "size_basis": style, "cell": int(key),
                         "year": year, "session": ("pre_cash", "early_cash", "late_cash")[session],
                         "bin_index": bucket, "bin_lower": BINS[bucket], "bin_upper": BINS[bucket+1],
                         "arm": arm, "trades": int(counts.loc[key, arm]), "entry_days": int(days.loc[key, arm]),
                         "supported": bool(keep.loc[key]), "weight": weights.get(key, 0.)})
    return weights, rows


def table(frame, cols):
    def cell(v):
        if pd.isna(v): return ""
        return f"{v:.4f}" if isinstance(v, (float, np.floating)) else str(v)
    return "\n".join(["| "+" | ".join(cols)+" |", "| "+" | ".join("---" for _ in cols)+" |"] +
                      ["| "+" | ".join(cell(v) for v in row)+" |" for row in frame[cols].itertuples(index=False, name=None)])


def analyse(run=RUN):
    run = Path(run)
    manifest = json.loads((run/"manifest.json").read_text(encoding="utf-8"))
    verify_manifest(run, manifest)
    sources, days, source_proof = validated_sources(run,manifest)
    all_paths, all_checks, audits = [], [], []
    for job in manifest["jobs"]:
        paths, checks, audit, observed_days = validated_paths(run, job, sources[job["instrument"]])
        all_paths.append(paths)
        checks = checks.assign(instrument=job["instrument"], mode=job["mode"], tag=job["tag"])
        all_checks.append(checks)
        audits.append(audit)
        print(f"PASS {job['tag']}: {len(paths):,} positions and target checks validated.", flush=True)
    d = pd.concat(all_paths, ignore_index=True)
    require(np.isfinite(d[FEATURES].to_numpy(dtype=float)).all(), "Nonfinite path-analysis features")
    require(d.day.isin(days).all(), "True union source calendar omits an entry day")
    arm_keys = [i+"__"+m for i,m in ARMS]
    rows, contrasts, coverage, strata, unadjusted, bootstrap_checks, unavailable = [], [], [], [], [], [], []
    for pi, (period, lo, hi) in enumerate(PERIODS):
        p = d.loc[d.year.between(lo, hi)].copy()
        primary = p.loc[p.primary].copy()
        period_days = days[(days.year >= lo) & (days.year <= hi)]
        day_index = {day: i for i,day in enumerate(period_days)}
        models = []
        for sample, population in (("full_sample", p), ("primary", primary), ("primary_without_locked_mismatch", primary.loc[primary.locked_target_mismatch == 0])):
            label = "unadjusted:"+sample
            try:
                m = model(population, arm_keys, {0:1.}, None, day_index, label)
            except ValueError as exc:
                if sample != "primary_without_locked_mismatch":
                    raise
                unavailable.append({"period":period,"panel":"unadjusted","size_basis":"none","sample":sample,"reason":str(exc)})
                continue
            m["meta"] = {"period":period,"panel":"unadjusted","size_basis":"none","sample":sample}
            models.append(m)
        for style in ("effective", "native_ticks"):
            for panel, arms in (("six_arm_common", arm_keys), ("coarse_ES_four_arm", [a for a in arm_keys if a.startswith(("NQcoarse__", "ES__"))])):
                weights, srows = support(primary.loc[primary.arm.isin(arms)], arms, style, period, panel)
                strata.extend(srows)
                for arm in arms:
                    selected = primary.loc[(primary.arm == arm) & primary[f"cell_{style}"].isin(weights)]
                    total = p.loc[p.arm == arm]
                    eligible = primary.loc[primary.arm == arm]
                    coverage.append({"period":period,"panel":panel,"size_basis":style,"arm":arm,"full_trades":len(total),
                                     "primary_trades":len(eligible),"supported_trades":len(selected),"supported_days":selected.day.nunique(),
                                     "primary_days":eligible.day.nunique(),"cells":len(weights),
                                     "retained_primary_fraction":len(selected)/len(eligible) if len(eligible) else np.nan,
                                     "source_hole_excluded":int(total.source_hole.sum()),"cross_date_excluded":int(total.cross_date.sum()),
                                     "outside_matching_session_excluded":int(total.outside_matching_session.sum())})
                if not weights:
                    unavailable.append({"period":period,"panel":panel,"size_basis":style,"sample":"primary","reason":"No cells satisfy frozen overlap support"})
                    continue
                for sample, population in (("primary", primary), ("primary_without_locked_mismatch", primary.loc[primary.locked_target_mismatch == 0])):
                    label = ":".join([panel,style,sample])
                    try:
                        m = model(population, arms, weights, f"cell_{style}", day_index, label)
                    except ValueError as exc:
                        if sample != "primary_without_locked_mismatch":
                            raise
                        unavailable.append({"period":period,"panel":panel,"size_basis":style,"sample":sample,"reason":str(exc)})
                        continue
                    m["meta"] = {"period":period,"panel":panel,"size_basis":style,"sample":sample}
                    models.append(m)
        draws, stats = paired_bootstrap(models, len(period_days), SEED+pi)
        bootstrap_checks.append({"period":period,"calendar_days":len(period_days), "seed":SEED+pi, **stats})
        for m in models:
            for arm_idx, arm in enumerate(m["arms"]):
                instrument, mode = arm.split("__")
                for j, metric in enumerate(OUTPUTS):
                    lower, upper = percentiles(draws[m["label"]][:, arm_idx, j])
                    row = {**m["meta"], "instrument":instrument,"mode":mode,"metric":metric,
                           "value":float(m["point"][arm_idx,j]),"lo95":lower,"hi95":upper,
                           "finite_draws":int(np.isfinite(draws[m["label"]][:,arm_idx,j]).sum())}
                    (unadjusted if m["meta"]["panel"] == "unadjusted" else rows).append(row)
            pairs = []
            for instrument in ("NQ","NQcoarse","ES"):
                a,b = instrument+"__rtl",instrument+"__control"
                if a in m["arms"] and b in m["arms"]: pairs.append((a,b,"rtl_minus_control"))
            for mode in ("rtl","control"):
                for a,b in (("NQcoarse","ES"),("NQ","ES"),("NQ","NQcoarse")):
                    aa,bb=a+"__"+mode,b+"__"+mode
                    if aa in m["arms"] and bb in m["arms"]: pairs.append((aa,bb,"instrument_difference"))
            for a,b,kind in pairs:
                ia,ib=m["arms"].index(a),m["arms"].index(b)
                for j,metric in enumerate(OUTPUTS):
                    values=draws[m["label"]][:,ia,j]-draws[m["label"]][:,ib,j]
                    lower,upper=percentiles(values)
                    contrasts.append({**m["meta"],"kind":kind,"a":a,"b":b,"metric":metric,
                                      "difference":float(m["point"][ia,j]-m["point"][ib,j]),"lo95":lower,"hi95":upper,
                                      "finite_draws":int(np.isfinite(values).sum())})
        print(f"{period}: {len(models)} fixed models; bootstrap accepted {stats['accepted']}, rejected {stats['rejected']}.",flush=True)
    un = pd.DataFrame(unadjusted)
    # Unadjusted quantiles describe the actual trade distributions, without
    # pretending that an overlap-standardized distribution has these medians.
    quantiles=[]
    population_totals=[]
    for period,lo,hi in PERIODS:
        for (instrument,mode),g in d.loc[d.year.between(lo,hi)].groupby(["instrument","mode"]):
            quantiles.append({"period":period,"instrument":instrument,"mode":mode,"trades":len(g),
                              "median_mae_R":g.mae_R.median(),"p90_mae_R":g.mae_R.quantile(.9),
                              "median_mfe_R":g.mfe_R.median(),"p90_mfe_R":g.mfe_R.quantile(.9),
                              "median_hold_minutes":((g.exit-g.entry).dt.total_seconds()/60).median()})
    for period,lo,hi in PERIODS:
        period_data=d.loc[d.year.between(lo,hi)]
        for sample,population in (("full_sample",period_data),("primary",period_data.loc[period_data.primary])):
            for (instrument,mode),g in population.groupby(["instrument","mode"]):
                population_totals.append({"period":period,"sample":sample,"instrument":instrument,"mode":mode,
                                          "trades":len(g),"entry_days":g.day.nunique(),"trade_profit":g.trade_profit.sum(),
                                          "gross_profit":g.loc[g.trade_profit>0,"trade_profit"].sum(),
                                          "gross_loss":g.loc[g.trade_profit<0,"trade_profit"].sum(),
                                          "gross_R_sum":g.gross_R.sum(),"gross_R_mean":g.gross_R.mean(),
                                          "reach1_positions":int(g.hit1.sum()),"locked_target_mismatch_positions":int(g.locked_target_mismatch.sum())})
    frames={"unadjusted_by_period":un,"unadjusted_totals":pd.DataFrame(population_totals),"unadjusted_distributions":pd.DataFrame(quantiles),
            "matched_metrics":pd.DataFrame(rows),"matched_contrasts":pd.DataFrame(contrasts),
            "coverage":pd.DataFrame(coverage),"strata":pd.DataFrame(strata),"trade_paths":d,
            "target_checks":pd.concat(all_checks,ignore_index=True),
            "unavailable_models":pd.DataFrame(unavailable,columns=["period","panel","size_basis","sample","reason"])}
    for name,frame in frames.items():
        frame.to_csv(run/(name+".csv"),index=False,float_format="%.12g")
    validation={"all_passed":True,"jobs":audits,"bootstrap":bootstrap_checks,
                "matching":{"min_trades_per_arm_cell":MIN_N,"min_distinct_entry_days_per_arm_cell":MIN_DAYS,
                            "fixed_min_count_weights":True,"bins":[0,8,16,24,32,48,64,128,"inf"],
                            "entry_sessions_source_clock":["01:00-16:30","16:30-20:00","20:00-23:30"]},
                "calendar_days":len(days),"calendar_first":str(days[0].date()),"calendar_last":str(days[-1].date()),
                "date_clock":"America/Chicago local time +8 hours, timezone-free source clock",
                "observer_first_quote_zero_lag":True,"bootstrap_replicates":BOOTSTRAPS,
                "source_validation":source_proof,"analyzer_sha256":digest(__file__),"unavailable_models":unavailable}
    (run/"analysis_checks.json").write_text(json.dumps(validation,indent=2)+"\n",encoding="utf-8")
    selected=frames["matched_metrics"]
    main=selected.loc[(selected.size_basis=="effective")&(selected["sample"]=="primary")&
                      selected.metric.isin(["gross_R","mean_mae_R","mean_mfe_R","p_reach1","p_stop_before1",
                        "p_actual_same_bar_close_above_given_reach1","p_stop_before_same_bar_check_given_reach1"])]
    report=["# Post-entry path interaction experiment\n\n",
            f"All six unchanged-strategy observer runs reproduce the original raw ledgers and complete audited reference positions. {len(d):,} paths include previously unlogged fast stops. "
            "Counts, profits, risk/order bindings, extrema, hit times, target-check bindings and first-quote timing pass.\n\n",
            "Path R uses actual fill minus the original SL; gross expectancy R uses original requested entry minus SL. "
            "Signal width controls matching. Native/ES effective step is 0.25; yearly coarse NQ uses its original ES-like, ties-to-even history. "
            "Entry year and source-clock session determine strata; coarse resolution uses signal year. This clock is Chicago local time +8 hours.\n\n",
            "Primary comparisons exclude the two ES source-hole entry dates (2020-02-28 and 2020-06-30) across all arms and exclude cross-date positions. "
            "Fills outside the predefined [01:00,23:30) entry sessions have no matching cell and remain only in full-sample context. Full-sample means and distributions remain separate context. Overlap support requires at least 30 trades and 10 distinct entry days in every participating arm; "
            "weights are normalized minimum arm counts, fixed before path outcomes. Six-arm and broader coarse-NQ/ES four-arm panels use their own disclosed populations. "
            "Native-tick size matching and exclusion of positions with mismatched locked targets are sensitivities.\n\n",
            "The same 1,000 bootstrap samples of whole source-calendar days are shared by every model within each period. "
            "Support and weights stay fixed. A draw with any empty kept arm/cell is rejected in full and retried; attempts and rejection fractions are recorded. "
            "Finite bootstrap counts are disclosed per metric/contrast; zero conditional denominators yield unavailable draws. These percentile intervals are conditional on nonempty frozen cells; serial dependence spanning days and wider exploratory selection are not covered.\n\n",
            "Among trades reaching +1 actual-risk R, primary retention uses the actual ManageOpenPosition check closing that SAME touch bar. "
            "Later checks cannot replace it. Separate secondary metrics count any subsequent actual qualifying close while held and any actual-rule condition becoming true after the first touch, with lags disclosed. Outcomes partition reachers into stop-before-check, administrative exit-before-check with flatten evidence, actual close above/below, and unavailable check. Prior successful rule-check exits are disclosed and excluded from the administrative label. "
            "A hypothetical source close after exit is reported only as a separate secondary quantity. Joint category probabilities use all trades; conditional category shares divide standardized joint probabilities by standardized reach probability, and sum to one. Terminal exit fills enter extrema and touch flags; hit-at-exit is disclosed. "
            "Loss-making administrative exits are not stop-first events. A qualifying actual-rule check records its comparison condition, not successful order submission/execution. These are observed strategy populations, not isolated causal market effects.\n\n",
            "## Matched primary path metrics\n\n",
            table(main,["period","panel","instrument","mode","metric","value","lo95","hi95"]),
            "\n\n## Common-support coverage\n\n",
            table(frames["coverage"].loc[frames["coverage"].size_basis=="effective"],
                  ["period","panel","arm","primary_trades","supported_trades","retained_primary_fraction","cells"]),
            "\n\n## Bootstrap validation\n\n",table(pd.DataFrame(bootstrap_checks),["period","calendar_days","accepted","attempted","rejected","rejected_fraction"]),
            "\n\nComplete metric/contrast tables, raw population distributions, fixed strata/weights, position paths, target checks and provenance are saved beside this report. "
            "No trading filter or parameter change follows from this exploratory decomposition.\n"]
    (run/"ANALYSIS.md").write_text("".join(report),encoding="utf-8")
    print(f"Wrote path-analysis tables and report to {run}",flush=True)
    return frames,validation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir",type=Path,default=RUN)
    args=parser.parse_args()
    try: analyse(args.run_dir)
    except (OSError,ValueError,AssertionError,KeyError) as exc: parser.exit(1,f"Path analysis failed: {exc}\n")


if __name__=="__main__":
    main()
