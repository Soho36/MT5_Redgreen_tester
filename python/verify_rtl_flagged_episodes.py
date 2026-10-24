"""Independent reconstruction of the frozen RTL episode attribution.

No functions are imported from the episode analyzer. The already independently
verified price panels are hash-bound rather than rebuilding minute OHLC again.
Episode runs, as-of joins, frozen ranges, logged extrema and every summary are
recomputed here directly from those inputs and the original trade logger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "Reports/rtl_price_structure_20261024"
OUTPUT = ROOT / "Reports/rtl_flagged_episodes_20261024"
BASE = ROOT / "Reports/timeframe_baseline_20261015"
TAG = "tf_20261015_rtl_m30_rr1p0"
PROTOCOL = ROOT / "docs/baseline/rtl-price-structure/EPISODE_PROTOCOL.md"
PROTOCOL_SHA256 = "541a408b5fdc474dfb22478bd50f75f4dbd011c7e9f3474c30ab497f2cc66b12"
END = pd.Timestamp("2026-10-01")
ERAS = {"2016-19": (pd.Timestamp("2016-01-01"), pd.Timestamp("2020-01-01")),
        "2020-26": (pd.Timestamp("2020-01-01"), END)}
FLAGS = {"d1_main": ("d1", "low_eff_high_overlap"),
         "m30_main": ("m30", "low_eff_high_overlap"),
         "m30_broad_wick": ("m30", "high_overlap_high_wick"),
         "m30_triple": ("m30", "low_eff_high_overlap_high_wick")}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def numeric(actual, expected, label, atol=1e-8):
    np.testing.assert_allclose(np.asarray(actual, dtype=float), np.asarray(expected, dtype=float),
                               rtol=1e-10, atol=atol, equal_nan=True, err_msg=label)


def dates(actual, expected, label):
    # Concatenated D1/M30 CSVs contain both date-only and full ISO timestamps.
    # Parse that representation explicitly without silently coercing bad dates.
    a = pd.Series(pd.to_datetime(actual, format="ISO8601")).reset_index(drop=True)
    b = pd.Series(pd.to_datetime(expected, format="ISO8601")).reset_index(drop=True)
    assert ((a == b) | (a.isna() & b.isna())).all(), label


def same(actual, expected, label):
    a = pd.Series(actual).reset_index(drop=True).fillna("<NA>").astype(str)
    b = pd.Series(expected).reset_index(drop=True).fillna("<NA>").astype(str)
    assert a.equals(b), f"{label}: {pd.DataFrame({'actual': a, 'expected': b}).loc[a != b].head()}"


def source_checks():
    assert sha256(PROTOCOL) == PROTOCOL_SHA256, "Frozen episode protocol changed"
    provenance = json.loads((SOURCE / "provenance.json").read_text())
    verified = json.loads((SOURCE / "independent_verification.json").read_text())
    assert verified["status"] == "PASS"
    inputs = {str(PROTOCOL): PROTOCOL_SHA256}
    for name in ("trades.csv", "thresholds.csv", "summaries.csv", "named_wick_summary.csv",
                 *[f"features_{tf}_{n}.csv" for tf in ("d1", "m30") for n in (10, 20, 40)]):
        actual = sha256(SOURCE / name)
        assert actual == provenance["outputs_sha256"][name] == verified["artifact_sha256"][name], name
        inputs[str(SOURCE / name)] = actual
    for name in ("manifest.json", f"{TAG}.completed.json", f"runband_{TAG}_1.00.csv"):
        path = BASE / name
        actual = sha256(path)
        assert actual == provenance["inputs_sha256"][str(path)], name
        inputs[str(path)] = actual
    manifest = json.loads((BASE / "manifest.json").read_text())
    completion = json.loads((BASE / f"{TAG}.completed.json").read_text())
    raw_name = f"runband_{TAG}_1.00.csv"
    assert sha256(BASE / raw_name) == completion["outputs"][raw_name]
    logger = BASE / "RTL_timeframe.mq5"
    assert sha256(logger) == manifest["prepared_sha256"][logger.name]
    inputs[str(logger)] = sha256(logger)
    text = logger.read_text(encoding="utf-8-sig")
    for literal in ("PositionGetDouble(POSITION_PROFIT)", "g_maeMoney  = floating;",
                    "g_mfeMoney  = floating;", "g_maeMoney = MathMin(g_maeMoney, realized);",
                    "g_mfeMoney = MathMax(g_mfeMoney, realized);"):
        assert literal in text, f"Unrecognized excursion logger: {literal}"
    assert manifest["cost_per_trade"] == 1.05 and manifest["max_red_run"] == 0
    return inputs


def source_trades():
    old = pd.read_csv(SOURCE / "trades.csv")
    for col in ("submitted", "entry_time", "exit_time", "session", "week_start"):
        old[col] = pd.to_datetime(old[col])
    raw = pd.read_csv(BASE / f"runband_{TAG}_1.00.csv", sep="\t", encoding="utf-16")
    for col in ("entry_time", "exit_time"):
        raw[col] = pd.to_datetime(raw[col], format="%Y.%m.%d %H:%M:%S")
    assert len(old) == len(raw) == 25833
    assert old.ticket.is_unique and raw.ticket.is_unique
    raw = raw.set_index("ticket").loc[old.ticket]
    for col in ("entry_time", "exit_time"):
        dates(old[col], raw[col], f"Original ledger {col}")
    for col in ("trade_profit", "candle_range", "red_run", "location"):
        numeric(old[col], raw[col], f"Original ledger {col}")
    old["mae_money"] = raw.mae_money.to_numpy()
    old["mfe_money"] = raw.mfe_money.to_numpy()
    numeric(old.trade_profit, (old.exit_price - old.fill_price) * 2, "Raw gross PnL")
    numeric(old.initial_risk_dollars, (old.requested_price - old.original_sl) * 2, "Original planned risk")
    numeric(old.net_dollars, old.trade_profit - 1.05, "Research cost")
    numeric(old.net_r, old.net_dollars / old.initial_risk_dollars, "Net R")
    selected = old.loc[(old.session >= ERAS["2016-19"][0]) & (old.session < END)].copy()
    assert len(selected) == 16668
    assert selected.primary.all()
    assert len(selected.loc[selected.era == "2016-19"]) == 6167
    assert len(selected.loc[selected.era == "2020-26"]) == 10501
    selected["sampled_max_price"] = selected.fill_price + selected.mfe_money / 2
    selected["sampled_min_price"] = selected.fill_price + selected.mae_money / 2
    assert (selected.sampled_max_price >= selected.exit_price).all()
    assert (selected.sampled_min_price <= selected.exit_price).all()
    assert (selected.sampled_min_price <= selected.sampled_max_price).all()
    return selected.reset_index(drop=True)


def original_mask(frame, flag, prefix=""):
    low = frame[prefix + "low_eff"].to_numpy(bool)
    overlap = frame[prefix + "high_overlap"].to_numpy(bool)
    wick = frame[prefix + "high_wick"].to_numpy(bool)
    valid = frame[prefix + "valid"].to_numpy(bool)
    if flag.endswith("main"):
        return valid & low & overlap
    if flag == "m30_broad_wick":
        return valid & overlap & wick
    return valid & low & overlap & wick


def feature_source(tf, n):
    frame = pd.read_csv(SOURCE / f"features_{tf}_{n}.csv")
    for col in ("bar_time", "last_bar_time", "available_at", "history_start"):
        frame[col] = pd.to_datetime(frame[col])
    expected_availability = frame.bar_time + (pd.Timedelta(days=1) if tf == "d1" else pd.Timedelta(minutes=30))
    dates(frame.available_at, expected_availability, f"{tf}/{n} availability")
    assert frame.available_at.is_unique and frame.available_at.is_monotonic_increasing
    cuts = pd.read_csv(SOURCE / "thresholds.csv").set_index(["timeframe", "window"]).loc[(tf, n)]
    valid = frame.efficiency.notna().to_numpy()
    np.testing.assert_array_equal(frame.valid, valid)
    np.testing.assert_array_equal(frame.low_eff, valid & (frame.efficiency <= cuts.efficiency_low))
    np.testing.assert_array_equal(frame.high_overlap, valid & (frame.overlap >= cuts.overlap_high))
    np.testing.assert_array_equal(frame.high_wick, valid & (frame.wick >= cuts.wick_high))
    return frame.loc[frame.available_at < END].reset_index(drop=True)


def literal_episodes(frame, flags):
    """Find maximal runs with a literal row walk, not groupby/cumulative flags."""
    valid = frame.valid.to_numpy(bool)
    flags = np.asarray(flags, dtype=bool) & valid
    identifiers = np.zeros(len(frame), dtype=int)
    ages = np.zeros(len(frame), dtype=int)
    inventory = []
    i = 0
    while i < len(frame):
        if not flags[i]:
            i += 1
            continue
        begin = i
        while i + 1 < len(frame) and flags[i + 1]:
            i += 1
        last = i
        number = len(inventory) + 1
        left = begin == 0 or not valid[begin - 1]
        right = last + 1 == len(frame) or not valid[last + 1]
        clear = pd.NaT if right else frame.available_at.iloc[last + 1]
        start = frame.available_at.iloc[begin]
        last_true = frame.available_at.iloc[last]
        observed_end = END if last + 1 == len(frame) else frame.available_at.iloc[last + 1]
        inventory.append({"episode_id": number, "start": start, "last_true": last_true,
                          "first_clear": clear, "length": last - begin + 1,
                          "left_censored": left, "right_censored": right,
                          "observed_end": observed_end,
                          "elapsed_hours": (observed_end - start).total_seconds() / 3600,
                          "observed_span_hours": (last_true - start).total_seconds() / 3600})
        identifiers[begin:last + 1] = number
        ages[begin:last + 1] = np.arange(1, last - begin + 2)
        i += 1
    return identifiers, ages, pd.DataFrame(inventory)


def asof(frame, times):
    available = pd.DatetimeIndex(frame.available_at)
    query = pd.DatetimeIndex(times)
    positions = np.searchsorted(available, query, side="right") - 1
    known = (positions >= 0) & (query < END)
    return positions, np.asarray(known, dtype=bool)


def phase(length, age, left, right):
    if left or right:
        return "censored"
    if length < 3:
        return "short_episode"
    fraction = (age - .5) / length
    return "early" if fraction <= 1 / 3 else "middle" if fraction <= 2 / 3 else "late"


def location(price, high, low):
    return "above" if price > high else "below" if price < low else "inside"


def group_path(maximum, minimum, high, low):
    upper = maximum > high
    lower = minimum < low
    return "both" if upper and lower else "upper_only" if upper else "lower_only" if lower else "contained"


def expected_attribution(trades, frame, flag, tf, n):
    flags = original_mask(frame, flag)
    ids, ages, inventory = literal_episodes(frame, flags)
    positions, known = asof(frame, trades.submitted)
    assert known.all()
    matched = flags[positions]
    np.testing.assert_array_equal(matched, original_mask(trades, flag, f"{tf}_{n}_"))
    source = trades.loc[matched].copy()
    selected_positions = positions[matched]
    rows = []
    records = inventory.set_index("episode_id").to_dict("index")
    endpoint_positions = {when: asof(frame, source[column]) for when, column in
                          (("fill", "entry_time"), ("exit", "exit_time"))}
    for trade_number, (trade, pos) in enumerate(zip(source.itertuples(index=False), selected_positions)):
        identifier = ids[pos]
        episode = records[identifier]
        age = ages[pos]
        candles = frame.iloc[pos - n + 1:pos + 1]
        assert len(candles) == n
        high, low = float(candles.high.max()), float(candles.low.min())
        row = dict(ticket=trade.ticket, era=trade.era, episode_id=identifier,
                   submitted=trade.submitted, entry_time=trade.entry_time, exit_time=trade.exit_time,
                   available_at=frame.available_at.iloc[pos], episode_age=int(age),
                   retrospective_phase=phase(episode["length"], age, episode["left_censored"], episode["right_censored"]),
                   causal_age_bin="1" if age == 1 else "2-3" if age <= 3 else "4-8" if age <= 8 else "9+",
                   range_high=high, range_low=low,
                   range_start=frame.bar_time.iloc[pos - n + 1], bar_time=frame.bar_time.iloc[pos],
                   headroom_r=(high - trade.requested_price) / (trade.requested_price - trade.original_sl),
                   sampled_max_price=trade.sampled_max_price, sampled_min_price=trade.sampled_min_price,
                   path_group=group_path(trade.sampled_max_price, trade.sampled_min_price, high, low),
                   fill_location=location(trade.fill_price, high, low),
                   exit_location=location(trade.exit_price, high, low),
                   submission_delay_minutes=(trade.entry_time - trade.submitted).total_seconds() / 60,
                   holding_minutes=(trade.exit_time - trade.entry_time).total_seconds() / 60,
                   gross_dollars=trade.trade_profit, net_dollars=trade.net_dollars, net_r=trade.net_r,
                   session=trade.session, week_start=trade.week_start)
        for name in ("start", "last_true", "first_clear", "length", "left_censored", "right_censored"):
            row[name] = episode[name]
        row["phase_x_path"] = row["retrospective_phase"] + " | " + row["path_group"]
        for when, timestamp in (("fill", trade.entry_time), ("exit", trade.exit_time)):
            p, k = endpoint_positions[when]
            idx = p[trade_number]
            endpoint = "unknown" if not k[trade_number] or not frame.valid.iloc[idx] else (
                "unflagged" if not flags[idx] else "same_episode" if ids[idx] == identifier else "later_episode")
            row[when + "_episode_state"] = endpoint
            row[when + "_asof_available_at"] = frame.available_at.iloc[idx] if idx >= 0 else pd.NaT
            row[when + "_asof_episode_id"] = ids[idx] if idx >= 0 else np.nan
            row[when + "_at_or_after_clear"] = (timestamp >= episode["first_clear"]
                                                  if pd.notna(episode["first_clear"]) else None)
        rows.append(row)
    return pd.DataFrame(rows), inventory


DATE_FIELDS = {"submitted", "entry_time", "exit_time", "session", "week_start", "available_at", "bar_time",
               "start", "last_true", "first_clear", "observed_end", "range_start", "fill_asof_available_at",
               "exit_asof_available_at"}
TEXT_FIELDS = {"era", "retrospective_phase", "causal_age_bin", "path_group", "fill_episode_state",
               "exit_episode_state", "fill_location", "exit_location", "phase_x_path"}
BOOL_FIELDS = {"left_censored", "right_censored", "fill_at_or_after_clear", "exit_at_or_after_clear"}
DIMENSIONS = ("retrospective_phase", "causal_age_bin", "path_group", "fill_episode_state",
              "exit_episode_state", "fill_location", "exit_location", "phase_x_path")


def compare_fields(actual, expected, label):
    assert len(actual) == len(expected), label + " row count"
    for column in expected:
        if column == "gross_dollars" and "trade_profit" in actual:
            numeric(actual.trade_profit, expected[column], label + "/trade_profit")
            continue
        assert column in actual, f"Missing {label}/{column}"
        if column in DATE_FIELDS:
            dates(actual[column], expected[column], label + "/" + column)
        elif column in TEXT_FIELDS or column in BOOL_FIELDS:
            same(actual[column], expected[column], label + "/" + column)
        else:
            numeric(actual[column], expected[column], label + "/" + column)


def economic_metrics(part, positive_total=None, loss_total=None):
    """Calculate all reported statistics without sharing analyzer helpers."""
    net = part.net_dollars.to_numpy(float)
    positive = float(net[net > 0].sum())
    loss = float(-net[net < 0].sum())
    gross = float(part.gross_dollars.sum())
    positive_total = positive if positive_total is None else positive_total
    loss_total = loss if loss_total is None else loss_total
    count = len(part)
    return dict(trades=count, winners=int((net > 0).sum()), losers=int((net < 0).sum()),
                breakeven=int((net == 0).sum()), active_episodes=len(set(part.episode_id)),
                active_sessions=len(set(part.session)), active_weeks=len(set(part.week_start)),
                gross_dollars=gross, net_dollars=float(net.sum()), positive_net_dollars=positive, loss_dollars=loss,
                net_r_total=float(part.net_r.sum()), net_mean_r=float(part.net_r.sum() / count) if count else np.nan,
                dollar_pf=positive / loss if loss else np.nan,
                winning_dollars_share=positive / positive_total if positive_total else np.nan,
                losing_dollars_share=loss / loss_total if loss_total else np.nan,
                holding_hours=float(part.holding_minutes.sum() / 60),
                mean_holding_minutes=float(part.holding_minutes.sum() / count) if count else np.nan,
                mean_submission_delay_minutes=float(part.submission_delay_minutes.sum() / count) if count else np.nan,
                median_submission_delay_minutes=float(np.median(part.submission_delay_minutes)) if count else np.nan,
                mean_headroom_r=float(part.headroom_r.sum() / count) if count else np.nan)


def verify_summary(rows, expected, prior_row):
    assert not rows.duplicated(["dimension", "category"]).any()
    total = economic_metrics(expected)
    assert int(prior_row.trades) == len(expected)
    for new, old in (("gross_dollars", "gross_dollars"), ("net_dollars", "net_dollars"),
                     ("net_mean_r", "net_mean_r"), ("positive_net_dollars", "positive_net_dollars")):
        numeric([total[new]], [prior_row[old]], "Prior study " + old)
    numeric([total["loss_dollars"]], [-prior_row.negative_net_dollars], "Prior absolute losses")
    numeric([total["net_r_total"]], [prior_row.net_mean_r * prior_row.trades], "Prior R total")
    keys = set()
    pieces = [("all", "all", expected)]
    for dimension in DIMENSIONS:
        for category in sorted(set(expected[dimension])):
            pieces.append((dimension, category, expected.loc[expected[dimension] == category]))
    for dimension, category, part in pieces:
        keys.add((dimension, category))
        actual = rows.loc[(rows.dimension == dimension) & (rows.category == category)]
        assert len(actual) == 1, (dimension, category)
        values = economic_metrics(part, total["positive_net_dollars"], total["loss_dollars"])
        for field, value in values.items():
            numeric(actual[field], [value], f"Summary/{dimension}/{category}/{field}")
    assert set(zip(rows.dimension, rows.category)) == keys
    for dimension in DIMENSIONS:
        subset = rows.loc[rows.dimension == dimension]
        for additive in ("trades", "winners", "losers", "breakeven", "gross_dollars", "net_dollars",
                         "positive_net_dollars", "loss_dollars", "net_r_total", "holding_hours"):
            numeric([subset[additive].sum()], [total[additive]], f"Partition/{dimension}/{additive}")
        numeric([subset.winning_dollars_share.sum()], [1.0], "Winning-dollar shares")
        numeric([subset.losing_dollars_share.sum()], [1.0], "Losing-dollar shares")
    return len(pieces)


def verify_episode_pnl(actual, inventory, attribution, label):
    actual = actual.sort_values("episode_id").reset_index(drop=True)
    inventory = inventory.sort_values("episode_id").reset_index(drop=True)
    assert actual.episode_id.is_unique
    compare_fields(actual, inventory, label + "/boundaries")
    expected = inventory[["episode_id"]].copy()
    fields = ("trades", "winners", "losers", "gross_dollars", "net_dollars", "positive_net_dollars", "loss_dollars", "net_r_total")
    metrics_by_id = {int(identifier): economic_metrics(part)
                     for identifier, part in attribution.groupby("episode_id")}
    assert set(metrics_by_id).issubset(set(inventory.episode_id))
    for field in fields:
        expected[field] = [metrics_by_id.get(int(identifier), {}).get(field, 0) for identifier in inventory.episode_id]
    compare_fields(actual, expected, label + "/pnl")
    return int((expected.trades == 0).sum())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = args.output
    input_hashes = source_checks()
    trades = source_trades()
    provenance = json.loads((output / "provenance.json").read_text())
    assert provenance["protocol_sha256"] == PROTOCOL_SHA256
    for path, expected_hash in provenance["inputs_sha256"].items():
        assert sha256(path) == expected_hash, f"Changed episode input {path}"
    artifact_hashes = {}
    for name, expected_hash in provenance["outputs_sha256"].items():
        actual_hash = sha256(output / name)
        assert actual_hash == expected_hash, f"Changed episode artifact {name}"
        artifact_hashes[name] = actual_hash
    saved = {name: pd.read_csv(output / (name + ".csv")) for name in
             ("attribution", "episodes", "episode_era", "summaries", "reconciliation")}
    assert not saved["attribution"].duplicated(["flag", "window", "ticket"]).any()
    assert len(saved["reconciliation"]) == 24
    prior = pd.concat([pd.read_csv(SOURCE / "summaries.csv"), pd.read_csv(SOURCE / "named_wick_summary.csv")])
    reports, summary_count, selected_total, episode_count, era_episode_count = [], 0, 0, 0, 0
    for n in (10, 20, 40):
        panels = {tf: feature_source(tf, n) for tf in ("d1", "m30")}
        for flag, (tf, group) in FLAGS.items():
            expected, inventory = expected_attribution(trades, panels[tf], flag, tf, n)
            expected = expected.sort_values("ticket").reset_index(drop=True)
            actual = saved["attribution"].loc[(saved["attribution"].flag == flag) & (saved["attribution"].window == n)]
            actual = actual.sort_values("ticket").reset_index(drop=True)
            assert actual.timeframe.eq(tf).all()
            compare_fields(actual, expected, f"{flag}/{n}/attribution")
            originals = trades.set_index("ticket").loc[expected.ticket]
            for field in ("requested_price", "original_sl", "fill_price", "exit_price", "trade_profit", "mae_money", "mfe_money",
                          "initial_risk_dollars", "net_dollars", "net_r", "gross_r", "commission_r"):
                numeric(actual[field], originals[field], f"{flag}/{n}/original {field}")
            inv_actual = saved["episodes"].loc[(saved["episodes"].flag == flag) & (saved["episodes"].window == n)]
            zero_count = verify_episode_pnl(inv_actual, inventory, expected, f"{flag}/{n}/episodes")
            selected_total += len(expected)
            episode_count += len(inventory)
            for era, (start, stop) in ERAS.items():
                era_expected = expected.loc[expected.era == era]
                rows = saved["summaries"].loc[(saved["summaries"].flag == flag) & (saved["summaries"].window == n) &
                                               (saved["summaries"].era == era)]
                prior_row = prior.loc[(prior.timeframe == tf) & (prior.window == n) & (prior.era == era) & (prior.group == group)]
                assert len(prior_row) == 1
                summary_count += verify_summary(rows, era_expected, prior_row.iloc[0])
                relevant = inventory.loc[(inventory.start < stop) & (inventory.observed_end > start)]
                inv_era = saved["episode_era"].loc[(saved["episode_era"].flag == flag) & (saved["episode_era"].window == n) &
                                                   (saved["episode_era"].era == era)]
                zero_era = verify_episode_pnl(inv_era, relevant, era_expected, f"{flag}/{n}/{era}/episodes")
                era_episode_count += len(relevant)
                rec = saved["reconciliation"].loc[(saved["reconciliation"].flag == flag) &
                     (saved["reconciliation"].window == n) & (saved["reconciliation"].era == era)]
                assert len(rec) == 1 and bool(rec.iloc[0].passed)
                numeric(rec.trades, [len(era_expected)], "Reconciliation count")
                numeric(rec.net_dollars, [era_expected.net_dollars.sum()], "Reconciliation net")
                numeric(rec.prior_net_dollars, [prior_row.iloc[0].net_dollars], "Reconciliation prior net")
                reports.append(dict(flag=flag, timeframe=tf, window=n, era=era, selected_trades=len(era_expected),
                                    episodes_overlapping_era=len(relevant), zero_trade_episodes=zero_era,
                                    net_dollars=float(era_expected.net_dollars.sum()),
                                    net_r_total=float(era_expected.net_r.sum())))
            print(f"Verified {flag}/{n}: {len(expected)} trades, {len(inventory)} episodes ({zero_count} with zero eligible trades).", flush=True)
    assert selected_total == len(saved["attribution"])
    assert episode_count == len(saved["episodes"])
    assert era_episode_count == len(saved["episode_era"])
    assert summary_count == len(saved["summaries"])
    verification = dict(status="PASS", protocol_sha256=PROTOCOL_SHA256,
                        verification_program_sha256=sha256(__file__), independent_of_analyzer_helpers=True,
                        checked_input_sha256=input_hashes, checked_artifact_sha256=artifact_hashes,
                        original_ledger_trades=25833, eligible_trades=len(trades), selected_attribution_rows=selected_total,
                        full_history_episode_rows=episode_count, era_episode_rows=era_episode_count,
                        verified_summary_rows=summary_count, specification_eras=reports,
                        checks=["Frozen protocol and prior independently verified feature/ledger artifact hashes",
                                "Original raw excursion ledger and saved EA logger manifest hash",
                                "Literal maximal runs including pre-era history, invalid gaps, censoring and zero-trade episodes",
                                "Exact submission, fill and exit as-of availability, episode age, hindsight phase and clear timestamps",
                                "Literal last-n-candle frozen ranges excluding extra efficiency starting close",
                                "Raw MFE/MAE + fill price conversion without zero clamp; actual exit lies within envelope",
                                "Strict range touches, path groups and independent fill/exit endpoint locations",
                                "All selected trades match old flags; counts, dollars and R reconcile to original study",
                                "Every output summary, dollar-share denominator and complete partition independently recomputed",
                                "Per-episode and per-era episode economics including zero-trade inventory"],
                        scope="Attribution verification only. Historical phase and realized excursion paths are not executable predictors.")
    (output / "independent_verification.json").write_text(json.dumps(verification, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"PASS: {len(trades):,} eligible trades; {selected_total:,} overlapping-specification attributions; {summary_count:,} summaries.")


if __name__ == "__main__":
    main()
