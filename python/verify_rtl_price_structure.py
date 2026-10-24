"""Independent verification of the frozen RTL price-structure exploration.

No price-structure analyzer helpers are imported. Original baseline parsing and
portfolio arithmetic reuse the previous independent verifier, while OHLC,
structure features, thresholds and decision-time joins are rebuilt here.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from verify_rtl_market_regimes import (
    checked_ledger, expect_close, independent_metrics, report_trades, sha256,
)

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / "Reports/rtl_price_structure_20261024"
PROTOCOL = ROOT / "docs/baseline/rtl-price-structure/PROTOCOL.md"
PROTOCOL_SHA256 = "dcde54820c8f914b64f5e51d801c7b6a34e9d5ead3b0734d92d273cb829e2729"
BASE = ROOT / "Reports/timeframe_baseline_20261015"
TAG = "tf_20261015_rtl_m30_rr1p0"
M30 = ROOT / "Reports/trend_rr_20261002/m30_reference.csv"
MINUTES = Path(r"F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv")
ROLLS = MINUTES.with_name("MT5_NQ_continuous_2010-2026_rolls.csv")
ERAS = {"2016-19": ("2016-01-01", "2020-01-01"),
        "2020-26": ("2020-01-01", "2026-10-01")}
GROUPS = ("low_eff_high_overlap", "low_eff_other_overlap",
          "other_eff_high_overlap", "other_eff_other_overlap")
NAMED = ("low_eff_high_overlap_high_wick", "high_overlap_high_wick")


def original_ohlc():
    """Rebuild every four-price bar using a different raw chunk boundary."""
    parts, count, last_timestamp = [], 0, None
    for chunk in pd.read_csv(MINUTES, sep="\t", chunksize=350000,
                             usecols=["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"]):
        count += len(chunk)
        last_timestamp = str(chunk.iloc[-1]["<DATE>"]) + " " + str(chunk.iloc[-1]["<TIME>"])
        take = chunk.loc[chunk["<TIME>"] >= "01:00:00"].copy()
        timestamps = pd.to_datetime(take["<DATE>"] + " " + take["<TIME>"],
                                    format="%Y.%m.%d %H:%M:%S")
        take["bar_time"] = timestamps.dt.floor("30min")
        parts.append(take.groupby("bar_time").agg({"<OPEN>": "first", "<HIGH>": "max",
                                                  "<LOW>": "min", "<CLOSE>": "last"}))
    bars = pd.concat(parts).groupby(level=0).agg({"<OPEN>": "first", "<HIGH>": "max",
                                                "<LOW>": "min", "<CLOSE>": "last"})
    bars.columns = ["open", "high", "low", "close"]
    reference = pd.read_csv(M30, index_col="bar_time", parse_dates=["bar_time"])
    pd.testing.assert_frame_equal(bars, reference, check_exact=True, check_freq=False)
    daily = bars.groupby(bars.index.normalize()).agg({"open": "first", "high": "max",
                                                      "low": "min", "close": "last"})
    daily.index.name = "date"
    daily_reference = pd.read_csv(ROOT / "Reports/trend_rr_20261002/daily_reference.csv",
                                  index_col="date", parse_dates=["date"])
    assert daily.index.equals(daily_reference.index)
    expect_close(daily.close, daily_reference.close, "Daily source closes", tolerance=0)
    assert pd.Timestamp(last_timestamp) == pd.Timestamp("2026-10-01 02:59:00")
    return bars, daily, {"raw_minute_rows": count, "m30_bars": len(bars),
                         "daily_bars": len(daily), "all_ohlc_exact": True,
                         "last_source_timestamp": last_timestamp}


def percentile(values, probability):
    """Literal linear interpolation, independent of pandas/numpy quantiles."""
    values = sorted(float(x) for x in values)
    assert values and all(math.isfinite(x) for x in values)
    location = (len(values) - 1) * probability
    lower, upper = math.floor(location), math.ceil(location)
    return values[lower] + (location - lower) * (values[upper] - values[lower])


def literal_features(bars, n, switches):
    """Compute each window independently, using n+1 closes and n OHLC rows."""
    prices = bars[["open", "high", "low", "close"]].to_numpy(dtype=float)
    dates = bars.index.normalize()
    switch_dates = pd.DatetimeIndex(switches).normalize()
    switch_positions = np.array([np.flatnonzero(dates == day)[0] for day in switch_dates
                                 if (dates == day).any()], dtype=int)
    output = np.full((len(bars), 4), np.nan)
    clean = np.zeros(len(bars), dtype=bool)
    for end in range(n, len(bars)):
        history = prices[end-n:end+1]
        candles = history[1:]
        changes = np.diff(history[:, 3])
        path = np.abs(changes).sum()
        output[end, 0] = abs(history[-1, 3] - history[0, 3]) / path if path else 0.
        shared = np.maximum(0., np.minimum(candles[1:, 1], candles[:-1, 1]) -
                            np.maximum(candles[1:, 2], candles[:-1, 2]))
        span = np.maximum(candles[1:, 1], candles[:-1, 1]) - np.minimum(candles[1:, 2], candles[:-1, 2])
        pairs = np.ones(n-1)
        np.divide(shared, span, out=pairs, where=span > 0)
        output[end, 1] = pairs.mean()
        ranges = candles[:, 1] - candles[:, 2]
        wick = np.zeros(n)
        valid = ranges > 0
        wick[valid] = 1 - np.abs(candles[valid, 3] - candles[valid, 0]) / ranges[valid]
        output[end, 2] = wick.mean()
        output[end, 3] = (wick >= .80).mean()
        clean[end] = not ((switch_positions >= end-n) & (switch_positions <= end)).any()
    result = pd.DataFrame(output, index=bars.index,
                          columns=["efficiency", "overlap", "wick", "wick80_fraction"])
    result["roll_clean"] = clean
    return result


def calibration(features, timeframe):
    available = features.index + (pd.Timedelta(minutes=30) if timeframe == "M30" else pd.Timedelta(days=1))
    rows = features.loc[(available < pd.Timestamp("2016-01-01")) & features.efficiency.notna()]
    return {"efficiency_low": percentile(rows.efficiency, 1/3),
            "overlap_high": percentile(rows.overlap, 2/3),
            "wick_high": percentile(rows.wick, 2/3), "calibration_windows": len(rows)}


def classify(features, cuts):
    result = features.copy()
    valid = result.efficiency.notna()
    low = result.efficiency <= cuts["efficiency_low"]
    high = result.overlap >= cuts["overlap_high"]
    result["group"] = np.where(low, "low_eff_", "other_eff_") + np.where(high, "high_overlap", "other_overlap")
    result.loc[~valid, "group"] = "warmup"
    result["high_wick"] = valid & (result.wick >= cuts["wick_high"])
    return result


def reference_positions(bars, submitted, timeframe):
    decisions = pd.DatetimeIndex(submitted)
    if timeframe == "D1":
        return np.searchsorted(bars.index, decisions.normalize(), side="left") - 1
    return np.searchsorted(bars.index + pd.Timedelta(minutes=30), decisions, side="right") - 1


def future_invariance(bars, n, switches):
    cut = min(len(bars) - 2, max(n + 2, len(bars) // 2))
    sample = bars.iloc[:cut+50].copy()
    before = literal_features(sample, n, switches)
    sample.iloc[cut:] *= np.linspace(1.2, 2.0, len(sample)-cut)[:, None]
    after = literal_features(sample, n, switches)
    pd.testing.assert_frame_equal(before.iloc[:cut], after.iloc[:cut], check_exact=True)
    return {"mutated_from": str(sample.index[cut]), "unchanged_rows": cut}


def base_ledger():
    raw_path = BASE / f"runband_{TAG}_1.00.csv"
    raw = pd.read_csv(raw_path, sep="\t", encoding="utf-16")
    original = report_trades(BASE / f"{TAG}.htm")
    ledger = checked_ledger(raw, original).sort_values(["entry_time", "ticket"]).reset_index(drop=True)
    completion = json.loads((BASE / f"{TAG}.completed.json").read_text())
    assert sha256(raw_path) == completion["outputs"][raw_path.name]
    assert len(ledger) == 25833 and ledger.trade_profit.sum() == 62579.
    for era, (start, stop) in ERAS.items():
        ledger.loc[(ledger.session >= start) & (ledger.session < stop), "era"] = era
    incomplete = ledger.loc[ledger.session >= "2026-10-01"]
    assert len(incomplete) == 1 and incomplete.iloc[0].exit_comment == "end of test"
    return ledger


def json_scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def validate_sources(output):
    """All source/output hashes are checked against actual bytes, including data."""
    old = json.loads((ROOT / "Reports/rtl_market_regimes_20261023/provenance.json").read_text())
    source_hashes = {}
    for path in (MINUTES, ROLLS, M30, BASE / f"{TAG}.htm", BASE / f"{TAG}.ini",
                 BASE / f"runband_{TAG}_1.00.csv", BASE / f"runband_{TAG}_1.00_stats.csv",
                 BASE / "manifest.json", BASE / f"{TAG}.completed.json"):
        actual = sha256(path)
        assert old["inputs_sha256"][str(path)] == actual, f"Changed original source: {path}"
        source_hashes[str(path)] = actual
    saved_provenance = json.loads((output / "provenance.json").read_text())
    assert saved_provenance["protocol_sha256"] == PROTOCOL_SHA256
    for path, expected in saved_provenance.get("inputs_sha256", {}).items():
        assert sha256(path) == expected, f"Analyzer input changed: {path}"
    for name, expected in saved_provenance.get("outputs_sha256", {}).items():
        assert sha256(output / name) == expected, f"Analyzer output changed: {name}"
    return source_hashes


def compare_features(output, bars_by_timeframe, switches, ledger):
    thresholds = pd.read_csv(output / "thresholds.csv")
    assert len(thresholds) == 6
    assert not thresholds.duplicated(["timeframe", "window"]).any()
    saved = pd.read_csv(output / "trades.csv")
    assert saved.ticket.is_unique and set(saved.ticket) == set(ledger.ticket)
    saved = saved.set_index("ticket").reindex(ledger.ticket).reset_index()
    for column in ("submitted", "entry_time", "exit_time", "session", "week_start"):
        assert np.array_equal(pd.to_datetime(saved[column]), ledger[column]), f"Saved {column}"
    for column in ("requested_price", "original_sl", "fill_price", "initial_risk_dollars",
                   "fill_risk_dollars", "trade_profit", "net_dollars", "gross_r", "net_r", "commission_r", "holding_minutes",
                   "stress1_net_dollars", "stress2_net_dollars", "stress1_net_r", "stress2_net_r"):
        expect_close(saved[column], ledger[column], f"Saved ledger {column}")
    assert np.array_equal(saved.primary, ledger.primary)
    audited, feature_map = [], {}
    for timeframe, bars in bars_by_timeframe.items():
        for n in (10, 20, 40):
            print(f"Independent literal windows: {timeframe} {n}", flush=True)
            expected = literal_features(bars, n, switches)
            cuts = calibration(expected, timeframe.upper())
            row = thresholds.loc[(thresholds.timeframe.str.lower() == timeframe) & (thresholds.window == n)]
            assert len(row) == 1
            for key, value in cuts.items():
                expect_close(row.iloc[0][key], value, f"Cutoff {timeframe}/{n}/{key}")
            expected = classify(expected, cuts)
            feature_map[(timeframe, n)] = expected
            actual = pd.read_csv(output / f"features_{timeframe}_{n}.csv", index_col=0, parse_dates=[0])
            assert actual.index.equals(expected.index), f"{timeframe}/{n} feature coverage"
            for column in ("open", "high", "low", "close"):
                expect_close(actual[column], bars[column], f"Feature source OHLC {timeframe}/{n}/{column}", tolerance=0)
            valid = expected.efficiency.notna()
            for column in ("efficiency", "overlap", "wick", "wick80_fraction"):
                expect_close(actual.loc[valid, column], expected.loc[valid, column], f"{timeframe}/{n} {column}", tolerance=1e-11)
            assert np.array_equal(actual.valid, valid), f"{timeframe}/{n} validity"
            assert np.array_equal(actual.loc[valid, "roll_clean"], expected.loc[valid, "roll_clean"])
            assert np.array_equal(actual.loc[valid, "group"], expected.loc[valid, "group"])
            assert np.array_equal(actual.loc[valid, "high_wick"], expected.loc[valid, "high_wick"])
            available = bars.index + (pd.Timedelta(days=1) if timeframe == "d1" else pd.Timedelta(minutes=30))
            if "available_at" in actual:
                assert np.array_equal(pd.to_datetime(actual.available_at), available)
            if "history_start" in actual:
                assert np.array_equal(pd.to_datetime(actual.history_start.iloc[n:]), bars.index[:-n])
            if "last_bar_time" in actual:
                assert np.array_equal(pd.to_datetime(actual.last_bar_time), bars.index)
            prefix = f"{timeframe}_{n}_"
            pos = reference_positions(bars, ledger.submitted, timeframe.upper())
            assert (pos >= 0).all()
            matched = expected.iloc[pos].reset_index(drop=True)
            matched_dates = bars.index[pos]
            assert np.array_equal(pd.to_datetime(saved[prefix + "last_bar_time"]), matched_dates)
            assert (available[pos] <= pd.DatetimeIndex(ledger.submitted)).all()
            if timeframe == "d1":
                assert (matched_dates < pd.DatetimeIndex(ledger.session)).all()
            ready = matched.efficiency.notna().to_numpy()
            for column in ("efficiency", "overlap", "wick", "wick80_fraction"):
                expect_close(saved.loc[ready, prefix+column], matched.loc[ready, column], f"Trade {prefix}{column}", tolerance=1e-11)
                ledger[prefix+column] = matched[column].to_numpy()
            for column in ("group", "high_wick", "roll_clean"):
                assert np.array_equal(saved.loc[ready, prefix+column], matched.loc[ready, column]), f"Trade {prefix}{column}"
                ledger[prefix+column] = matched[column].to_numpy()
            ledger[prefix+"high_overlap"] = matched.overlap.to_numpy() >= cuts["overlap_high"]
            ledger[prefix+"last_bar_time"] = matched_dates
            assert ready[ledger.primary].all(), "Primary warmup rows"
            # Independent method is additionally checked for future invariance on a
            # small boundary-spanning slice; unit tests also exercise the analyzer.
            causal = future_invariance(bars.iloc[:200], n, switches)
            audited.append({"timeframe": timeframe, "window": n, **cuts,
                             "feature_rows": len(actual), "trade_rows": len(saved),
                             "future_invariance": causal})
    return ledger, feature_map, audited


def selection(frame, prefix, group):
    if group == "all":
        return pd.Series(True, index=frame.index)
    if group == NAMED[0]:
        return frame[prefix+"group"].eq(GROUPS[0]) & frame[prefix+"high_wick"]
    if group == NAMED[1]:
        return frame[prefix+"high_overlap"] & frame[prefix+"high_wick"]
    assert group in GROUPS
    return frame[prefix+"group"].eq(group)


def metric_audit(row, part, calendar, prefix, label):
    expected = independent_metrics(part, calendar)
    expected.update(planned_risk_total=part.initial_risk_dollars.sum(),
                    positive_net_dollars=part.loc[part.net_dollars > 0, "net_dollars"].sum(),
                    negative_net_dollars=part.loc[part.net_dollars < 0, "net_dollars"].sum(),
                    adequate_coverage=len(part) >= 200 and part.week_start.nunique() >= 30)
    for field in ("efficiency", "overlap", "wick", "wick80_fraction"):
        expected["mean_"+field] = part[prefix+field].mean()
    names = set()
    for key, value in expected.items():
        if key in row.index:
            expect_close(row[key], value, label+"/"+key, tolerance=2e-7)
            names.add(key)
    mandatory = {"trades", "net_dollars", "gross_dollars", "gross_mean_r", "net_mean_r",
                 "active_sessions", "active_weeks", "eligible_sessions", "eligible_weeks",
                 "dollar_pf", "risk_mean", "risk_median", "commission_mean_r", "holding_hours",
                 "mean_holding_minutes", "worst_day", "worst_week", "worst5pct_session_mean",
                 "closed_trade_dd", "daily_close_dd", "daily_dd_duration_days", "planned_risk_total",
                 "positive_net_dollars", "negative_net_dollars", "adequate_coverage",
                 "mean_efficiency", "mean_overlap", "mean_wick", "mean_wick80_fraction",
                 "stress1_net_dollars", "stress1_mean_r", "stress2_net_dollars", "stress2_mean_r"}
    assert mandatory.issubset(names), f"Missing mandatory metrics {label}: {mandatory-names}"
    return names


def one_row(table, **keys):
    mask = pd.Series(True, index=table.index)
    for key, value in keys.items():
        mask &= table[key].eq(value)
    rows = table.loc[mask]
    assert len(rows) == 1, f"Expected one row: {keys}; got {len(rows)}"
    return rows.iloc[0]


def session_audit(table, frame, calendar, **keys):
    mask = pd.Series(True, index=table.index)
    for key, value in keys.items():
        mask &= table[key].eq(value)
    rows = table.loc[mask].sort_values("session")
    assert len(rows) == len(calendar) and not rows.session.duplicated().any(), keys
    assert np.array_equal(pd.to_datetime(rows.session), calendar), keys
    reference = frame.groupby("session").net_dollars.sum().to_dict()
    expect_close(rows.net_dollars, [reference.get(day, 0.) for day in calendar], str(keys), tolerance=2e-7)


def outcome_audit(output, ledger, daily):
    tables = {name: pd.read_csv(output / (name+".csv")) for name in
              ("summaries", "yearly", "wick_summary", "named_wick_summary", "roll_sensitivity", "roll_coverage", "session_pnl")}
    expected_lengths = dict(summaries=60, yearly=396, wick_summary=32,
                            named_wick_summary=12, roll_sensitivity=72, roll_coverage=12)
    for name, count in expected_lengths.items():
        assert len(tables[name]) == count, f"Unexpected {name} coverage"
    names, checked, session_count = set(), {}, 0
    for era, (start, end) in ERAS.items():
        frame = ledger.loc[ledger.era == era]
        calendar = daily.index[(daily.index >= start) & (daily.index < end)]
        assert frame.session.isin(calendar).all()
        for timeframe in ("d1", "m30"):
            for n in (10, 20, 40):
                prefix = f"{timeframe}_{n}_"
                groups = GROUPS+("all",)+(NAMED if timeframe == "m30" else ())
                assert frame[prefix+"group"].isin(GROUPS).all()
                assert sum((frame[prefix+"group"] == g).sum() for g in GROUPS) == len(frame)
                clean = frame.loc[frame[prefix+"roll_clean"]]
                row = one_row(tables["roll_coverage"], timeframe=timeframe, window=n, era=era)
                for column, value in dict(full_trades=len(frame), retained_trades=len(clean),
                                          retained_fraction=len(clean)/len(frame),
                                          retained_holding_fraction=clean.holding_minutes.sum()/frame.holding_minutes.sum()).items():
                    expect_close(row[column], value, f"Roll coverage {era}/{prefix}/{column}")
                checked["roll_coverage"] = checked.get("roll_coverage", 0)+1
                for group in groups:
                    part = frame.loc[selection(frame, prefix, group)]
                    key = dict(timeframe=timeframe, window=n, era=era, group=group)
                    kind = "summaries" if group in GROUPS+("all",) else "named_wick_summary"
                    names |= metric_audit(one_row(tables[kind], **key), part, calendar, prefix, str(key))
                    checked[kind] = checked.get(kind, 0)+1
                    roll_part = clean.loc[selection(clean, prefix, group)]
                    names |= metric_audit(one_row(tables["roll_sensitivity"], **key), roll_part, calendar, prefix, "roll/"+str(key))
                    checked["roll_sensitivity"] = checked.get("roll_sensitivity", 0)+1
                    for year in sorted(frame.year.unique()):
                        annual = part.loc[part.year == year]
                        dates = calendar[calendar.year == year]
                        annual_row = one_row(tables["yearly"], **key, year=year)
                        assert annual_row.partial == (year == 2026)
                        names |= metric_audit(annual_row, annual, dates, prefix, f"{year}/"+str(key))
                        checked["yearly"] = checked.get("yearly", 0)+1
                    if n == 20 and group in GROUPS+("all",):
                        session_audit(tables["session_pnl"], part, calendar, **key, curve="group_contribution")
                        session_count += len(calendar)
                    if n == 20 and group in GROUPS:
                        for high in (False, True):
                            wick_part = part.loc[part[prefix+"high_wick"].eq(high)]
                            wick_row = one_row(tables["wick_summary"], **key, wick_state="high" if high else "other")
                            names |= metric_audit(wick_row, wick_part, calendar, prefix, "wick/"+str(key))
                            checked["wick_summary"] = checked.get("wick_summary", 0)+1
    assert checked == expected_lengths, (checked, expected_lengths)
    return {"rows": checked, "metric_names": sorted(names), "group_session_rows": session_count}


def bootstrap_audit(output, ledger, daily):
    """Recreate paired draws using a week-multiplicity matrix, not sample indexing."""
    saved = pd.read_csv(output / "uncertainty.csv")
    assert len(saved) == 20
    rng, verified = np.random.default_rng(20261024), []
    for era, (start, end) in ERAS.items():
        frame = ledger.loc[ledger.era == era]
        calendar = daily.index[(daily.index >= start) & (daily.index < end)]
        first = calendar[0]-pd.Timedelta(days=calendar[0].weekday())
        last = calendar[-1]-pd.Timedelta(days=calendar[-1].weekday())
        weeks = pd.date_range(first, last, freq="W-MON")
        starts = rng.integers(0, len(weeks), size=(10000, math.ceil(len(weeks)/4)))
        multiplicity = np.zeros((10000, len(weeks)), dtype=np.int64)
        positions = np.stack([(starts+i) % len(weeks) for i in range(4)], axis=2).reshape(10000, -1)[:, :len(weeks)]
        np.add.at(multiplicity, (np.arange(10000)[:, None], positions), 1)
        assert (multiplicity.sum(axis=1) == len(weeks)).all()
        whole = frame.groupby("week_start").net_r.agg(["sum", "count"]).reindex(weeks, fill_value=0)
        total_sums = multiplicity @ whole["sum"].to_numpy()
        total_counts = multiplicity @ whole["count"].to_numpy()
        for timeframe in ("d1", "m30"):
            prefix = f"{timeframe}_20_"
            for group in GROUPS+(NAMED if timeframe == "m30" else ()):
                mask = selection(frame, prefix, group)
                part, other = frame.loc[mask], frame.loc[~mask]
                weekly = part.groupby("week_start").net_r.agg(["sum", "count"]).reindex(weeks, fill_value=0)
                sums = multiplicity @ weekly["sum"].to_numpy()
                counts = multiplicity @ weekly["count"].to_numpy()
                means = np.divide(sums, counts, out=np.full(10000, np.nan), where=counts > 0)
                rest_count = total_counts-counts
                rest_mean = np.divide(total_sums-sums, rest_count, out=np.full(10000, np.nan), where=rest_count > 0)
                diff = means-rest_mean
                row = one_row(saved, era=era, timeframe=timeframe, window=20, group=group)
                for field, value in dict(trades=len(part), active_weeks=part.week_start.nunique(),
                                        net_mean_r=part.net_r.mean(), complement_trades=len(other),
                                        complement_net_mean_r=other.net_r.mean(),
                                        difference_net_r=part.net_r.mean()-other.net_r.mean(),
                                        bootstrap_valid_mean_draws=np.isfinite(means).sum(),
                                        bootstrap_valid_difference_draws=np.isfinite(diff).sum()).items():
                    expect_close(row[field], value, f"Bootstrap {era}/{timeframe}/{group}/{field}")
                for metric, values in (("mean_net_r", means), ("difference_net_r", diff)):
                    finite = values[np.isfinite(values)]
                    for suffix, alpha in (("95", .05), ("97_5", .025)):
                        for bound, q in (("low", alpha/2), ("high", 1-alpha/2)):
                            column = f"{metric}_ci{suffix}_{bound}"
                            if suffix == "97_5" and group != GROUPS[0]:
                                assert pd.isna(row[column])
                            else:
                                expected = percentile(finite, q) if len(finite) else np.nan
                                expect_close(row[column], expected, f"Bootstrap interval {era}/{timeframe}/{group}/{column}", tolerance=1e-9)
                verified.append(dict(era=era, timeframe=timeframe, group=group, draws=10000, calendar_weeks=len(weeks)))
    return verified


def balance_dd(values):
    balance = np.concatenate(([0.], np.cumsum(values, dtype=float)))
    return float(np.max(np.maximum.accumulate(balance)-balance))


def controls_audit(output, ledger, daily):
    omissions = pd.read_csv(output / "omission.csv")
    draws_saved = pd.read_csv(output / "placement_draws.csv")
    summary = pd.read_csv(output / "placement_summary.csv")
    sessions = pd.read_csv(output / "session_pnl.csv")
    assert len(omissions) == 24 and len(draws_saved) == 16000 and len(summary) == 8
    rng, verified, session_count = np.random.default_rng(20261024), [], 0
    for era, (start, end) in ERAS.items():
        frame = ledger.loc[ledger.era == era].sort_values(["entry_time", "ticket"], kind="stable")
        calendar = daily.index[(daily.index >= start) & (daily.index < end)]
        day_ids = calendar.get_indexer(frame.session)
        pnl, hours = frame.net_dollars.to_numpy(), frame.holding_minutes.to_numpy()/60
        for timeframe, group in (("d1", GROUPS[0]), ("m30", GROUPS[0]), ("m30", NAMED[0]), ("m30", NAMED[1])):
            prefix = f"{timeframe}_20_"
            skip = selection(frame, prefix, group).to_numpy()
            kept, omitted = frame.loc[~skip], frame.loc[skip]
            fraction = kept.holding_minutes.sum()/frame.holding_minutes.sum()
            fractions = dict(retained_holding_fraction=fraction, retained_trade_fraction=len(kept)/len(frame),
                             retained_planned_risk_fraction=kept.initial_risk_dollars.sum()/frame.initial_risk_dollars.sum(),
                             skip_trades=len(omitted), skipped_loss_dollars_avoided=-omitted.loc[omitted.net_dollars < 0, "net_dollars"].sum(),
                             skipped_profit_dollars_missed=omitted.loc[omitted.net_dollars > 0, "net_dollars"].sum(),
                             skipped_net_dollars=omitted.net_dollars.sum())
            fractions.update(retained_risk_fraction=fractions["retained_planned_risk_fraction"],
                             skipped_trades=fractions["skip_trades"], losses_avoided=fractions["skipped_loss_dollars_avoided"],
                             profits_missed=fractions["skipped_profit_dollars_missed"])
            key = dict(era=era, timeframe=timeframe, window=20, group=group)
            scaled = frame.copy()
            for column in ("net_dollars", "trade_profit", "initial_risk_dollars", "fill_risk_dollars", "stress1_net_dollars", "stress2_net_dollars", "holding_minutes"):
                scaled[column] = scaled[column]*fraction
            for curve, part in (("baseline", frame), ("omitted", kept), ("static_holding_scaled", scaled)):
                row = one_row(omissions, **key, curve=curve)
                metric_audit(row, part, calendar, prefix, "Control/"+str(key)+"/"+curve)
                for column, value in fractions.items():
                    expect_close(row[column], value, f"Omission {key}/{curve}/{column}")
                expect_close(row.pnl_scale, fraction if curve == "static_holding_scaled" else 1., f"Scale {key}/{curve}")
                session_audit(sessions, part, calendar, **key, curve=curve)
                session_count += len(calendar)
            offsets = rng.integers(0, len(frame), size=2000)
            saved = draws_saved.loc[(draws_saved.era == era) & (draws_saved.timeframe == timeframe) & (draws_saved.group == group)].sort_values("draw")
            assert len(saved) == 2000 and np.array_equal(saved.draw, np.arange(2000))
            assert np.array_equal(saved.offset, offsets), f"Placement seed/order {key}"
            rebuilt = []
            target_hours = kept.holding_minutes.sum()/60
            for offset in offsets:
                keep = ~skip[(np.arange(len(frame))-offset) % len(frame)]
                assert keep.sum() == len(kept)
                day_pnl = np.zeros(len(calendar))
                np.add.at(day_pnl, day_ids[keep], pnl[keep])
                retained_pnl = pnl[keep].sum()
                retained_hours = hours[keep].sum()
                dd = balance_dd(day_pnl)
                exposure_scale = target_hours/retained_hours
                rebuilt.append((keep.sum(), retained_pnl, dd, retained_hours, exposure_scale,
                                retained_pnl*exposure_scale, dd*exposure_scale))
            columns = ["retained_trades", "net_dollars", "daily_close_dd", "holding_hours", "exposure_scale",
                       "exposure_scaled_net_dollars", "exposure_scaled_daily_close_dd"]
            expected = pd.DataFrame(rebuilt, columns=columns)
            for column in columns:
                expect_close(saved[column], expected[column], f"Placement draws {key}/{column}", tolerance=2e-7)
            daily_map = kept.groupby("session").net_dollars.sum().to_dict()
            actual_net, actual_dd = kept.net_dollars.sum(), balance_dd([daily_map.get(day, 0.) for day in calendar])
            values = dict(draws=2000, distinct_offsets=len(set(offsets)), actual_net_dollars=actual_net,
                          actual_daily_close_dd=actual_dd, actual_holding_hours=target_hours, **fractions)
            for field in ("net_dollars", "daily_close_dd", "holding_hours", "exposure_scaled_net_dollars", "exposure_scaled_daily_close_dd"):
                for suffix, q in (("p025", .025), ("p50", .5), ("p975", .975)):
                    values[field+"_"+suffix] = percentile(expected[field], q)
            values.update(raw_fraction_net_at_least_actual=float((expected.net_dollars >= actual_net-1e-9).mean()),
                          raw_fraction_dd_at_most_actual=float((expected.daily_close_dd <= actual_dd+1e-9).mean()),
                          matched_fraction_net_at_least_actual=float((expected.exposure_scaled_net_dollars >= actual_net-1e-9).mean()),
                          matched_fraction_dd_at_most_actual=float((expected.exposure_scaled_daily_close_dd <= actual_dd+1e-9).mean()))
            row = one_row(summary, **key)
            for column, value in values.items():
                expect_close(row[column], value, f"Placement summary {key}/{column}", tolerance=2e-7)
            verified.append({**key, "placement_draws": len(offsets), "exact_skip_counts": True, "seed_reproduced": True})
    return {"comparisons": verified, "omission_rows": len(omissions), "placement_draw_rows": len(draws_saved),
            "omission_session_rows": session_count}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, default=STUDY)
    args = parser.parse_args()
    assert sha256(PROTOCOL) == PROTOCOL_SHA256, "Frozen protocol changed"
    output = args.study
    print("Checking original source bytes and rebuilding all OHLC from minutes...", flush=True)
    hashes = validate_sources(output)
    bars, daily, source_audit = original_ohlc()
    rolls = pd.read_csv(ROLLS)
    assert rolls.date.is_unique
    assert (rolls.instrument_id.iloc[1:].to_numpy() != rolls.instrument_id.iloc[:-1].to_numpy()).all()
    switches = pd.to_datetime(rolls.date.iloc[1:])
    assert pd.DatetimeIndex(switches).isin(daily.index).all()
    ledger = base_ledger()
    ledger, _, feature_audit = compare_features(output, {"d1": daily, "m30": bars}, switches, ledger)
    print("Auditing all outcome, annual, wick and roll rows...", flush=True)
    outcomes = outcome_audit(output, ledger, daily)
    print("Reproducing 10,000 paired four-week bootstrap draws in each era...", flush=True)
    intervals = bootstrap_audit(output, ledger, daily)
    print("Reproducing omission controls and all 16,000 circular placement draws...", flush=True)
    controls = controls_audit(output, ledger, daily)
    assert len(pd.read_csv(output / "session_pnl.csv")) == outcomes["group_session_rows"]+controls["omission_session_rows"]
    assert sha256(PROTOCOL) == PROTOCOL_SHA256
    provenance = json.loads((output / "provenance.json").read_text())
    artifacts = {name: sha256(output/name) for name in provenance["outputs_sha256"]}
    assert artifacts == provenance["outputs_sha256"], "Study changed during verification"
    result = dict(status="PASS", protocol_sha256=PROTOCOL_SHA256,
                  verification_program_sha256=sha256(Path(__file__)),
                  original_source_sha256=hashes, artifact_sha256=artifacts,
                  full_ledger_trades=len(ledger), primary_trades=int(ledger.primary.sum()),
                  eras={era: {"trades": len(part), "gross_dollars": float(part.trade_profit.sum()),
                              "net_dollars": float(part.net_dollars.sum())}
                        for era, part in ledger.loc[ledger.primary].groupby("era")},
                  source_ohlc=source_audit, features=feature_audit, outcomes=outcomes,
                  bootstrap=intervals, controls=controls,
                  original_html_ledger_risk_costs_endpoint="PASS",
                  future_invariance="PASS", pre2016_calibration="PASS", decision_time_asof="PASS",
                  provenance_input_and_output_hashes="PASS")
    (output / "independent_verification.json").write_text(json.dumps(result, indent=2, allow_nan=False, default=json_scalar)+"\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "full_ledger_trades", "primary_trades", "eras", "source_ohlc")}, indent=2))


if __name__ == "__main__":
    main()

