"""Q9: minute recovery speed and symmetric response; no trade simulation."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_price_levels import ROOT, SOURCES, PERIODS, sha256
from analyze_breach_reclaim import BREACHES, difference
from trend_regimes import SOURCE, ROLLS
from reclaim_speed import (signal_path, barrier_path, endpoint_metrics, match_pairs,
                           covariate_balance, MATCH_COLUMNS, CALIPERS)

UPSTREAM = ROOT / "Reports" / "levels" / "breach_reclaim_20261003"
STUDY = ROOT / "Reports" / "levels" / "reclaim_speed_20261003"
HORIZONS = (1, 3, 6)
FIELDS = tuple(f"{scale}_{metric}" for scale in ("r", "a") for metric in
               ("return", "absolute", "up", "down", "balance", "tails", "positive",
                "hit_up", "hit_down", "hit_both", "hit_up_only", "hit_down_only", "hit_neither",
                "first_up", "first_down", "first_ambiguous", "first_neither", "first_balance"))
INTERVAL_FIELDS = ("r_up", "r_down", "r_balance", "r_return", "r_absolute", "r_hit_both",
                   "a_up", "a_down", "a_balance", "a_return", "a_absolute", "a_hit_both")


def verify_upstream():
    p = json.loads((UPSTREAM / "provenance.json").read_text())
    for entry in p["files"]:
        assert sha256(entry["path"]) == entry["sha256"], f"Changed upstream input: {entry['path']}"
    return len(p["files"])


def load_minutes():
    parts = []
    columns = ["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"]
    for chunk in pd.read_csv(SOURCE, sep="\t", usecols=columns, chunksize=500000):
        chunk = chunk[(chunk["<DATE>"] >= "2015.12.01") & (chunk["<DATE>"] <= "2026.07.14") &
                      (chunk["<TIME>"] >= "01:00:00")]
        if chunk.empty:
            continue
        index = pd.to_datetime(chunk["<DATE>"] + " " + chunk["<TIME>"], format="%Y.%m.%d %H:%M:%S")
        parts.append(pd.DataFrame(chunk[columns[2:]].to_numpy(dtype=float), index=index,
                                  columns=["open", "high", "low", "close"]))
    minutes = pd.concat(parts)
    assert minutes.index.is_unique and minutes.index.is_monotonic_increasing
    return minutes


def lagged_scale(bars, rolls):
    positions = np.searchsorted(pd.to_datetime(rolls.date).to_numpy(), bars.index.to_numpy(), side="right") - 1
    assert (positions >= 0).all()
    ids = pd.Series(rolls.instrument_id.to_numpy()[positions], index=bars.index)
    previous = bars.close.groupby(ids).shift(1)
    tr = pd.concat([bars.high - bars.low, (bars.high - previous).abs(), (bars.low - previous).abs()], axis=1).max(axis=1)
    return tr.groupby(ids).transform(lambda s: s.rolling(14, min_periods=14).mean().shift(1))


def extract_features(features, minutes, scale):
    times = minutes.index.to_numpy(dtype="datetime64[ns]")
    values = minutes.to_numpy()
    unique = features.drop_duplicates("event_id").copy()
    cache = {}
    complete = 0
    for row in unique.itertuples():
        start, end = np.searchsorted(times, [row.signal_time.to_datetime64(), (row.signal_time + pd.Timedelta(minutes=30)).to_datetime64()])
        p = values[start:end]
        assert len(p) and np.array_equal([p[0, 0], p[:, 1].max(), p[:, 2].min(), p[-1, 3]],
                                        [row.signal_open, row.signal_high, row.signal_low, row.signal_close])
        full = len(p) == 30 and np.array_equal(times[start:end], row.signal_time.to_datetime64() + np.arange(30) * np.timedelta64(1, "m"))
        cache[row.event_id] = (start, end, full)
        complete += int(full)
    f = features.copy()
    f["atr_lag"] = scale.reindex(f.signal_time).to_numpy()
    f["atr_status"] = np.select([f.atr_lag.isna(), f.atr_lag <= 0],
                                ["insufficient_history", "nonpositive"], default="valid")
    positive_atr = f.atr_lag.where(f.atr_lag > 0)
    f["depth_a"] = (f.low - f.signal_low) / positive_atr
    f["range_a"] = f.candle_range / positive_atr
    f["strength_a"] = (f.signal_close - f.low) / positive_atr
    for col in ("breach_minute", "recovery_delay", "first_recovery_minute", "below_closes", "below_close_share", "recrossings", "approach_a_per_minute"):
        f[col] = np.nan
    f["signal_path_status"] = ["complete" if cache[k][2] else "missing_minutes" for k in f.event_id]
    descriptions = []
    for row in f[f.group.isin(BREACHES)].itertuples():
        start, end, full = cache[row.event_id]
        if not full:
            continue
        d = signal_path(values[start:end], row.low)
        velocity = np.nan
        ix = start + d["breach_minute"]
        if ix >= 6 and np.isfinite(row.atr_lag) and row.atr_lag > 0:
            recent = times[ix - 6:ix]
            expected = times[ix] - np.arange(6, 0, -1) * np.timedelta64(1, "m")
            if np.array_equal(recent, expected) and pd.Timestamp(recent[0]).normalize() == row.signal_time.normalize():
                velocity = (values[ix - 6, 3] - values[ix - 1, 3]) / (5 * row.atr_lag)
        descriptions.append(dict(index=row.Index, approach_a_per_minute=velocity, **d))
    d = pd.DataFrame(descriptions).set_index("index")
    f.loc[d.index, d.columns] = d
    reclaimed = f.group == "breach_reclaim"
    complete_mask = f.signal_path_status == "complete"
    assert f.loc[reclaimed & complete_mask, "recovery_delay"].notna().all()
    f["speed_group"] = np.select([~reclaimed, ~complete_mask, f.recovery_delay <= 2,
                                   f.recovery_delay <= 5, f.recovery_delay >= 6],
                                  ["not_final_reclaim", "missing_minutes", "fast", "middle", "slow"], default="error")
    assert not (f.speed_group == "error").any()
    f["clock_minutes"] = f.signal_time.dt.hour * 60 + f.signal_time.dt.minute
    for label, column in (("log_depth_a", "depth_a"), ("log_a", "atr_lag"), ("log_range_a", "range_a")):
        f[label] = np.log(f[column].where(f[column] > 0))
    return f, dict(unique_signal_candles_checked=len(unique), complete_signal_minutes=complete), cache


def build_responses(features, q8, minutes):
    events = features.drop_duplicates("event_id").set_index("event_id")
    times = minutes.index.to_numpy(dtype="datetime64[ns]")
    values = minutes.to_numpy()
    response = q8.copy()
    response["path_status"] = "endpoint_unavailable"
    atr = response.event_id.map(events.atr_lag)
    atr = atr.where(atr > 0)
    ranges = response.event_id.map(events.candle_range)
    for label, returns in (("r", response.forward_r), ("a", response.forward_r * ranges / atr)):
        for key, val in endpoint_metrics(returns).items():
            response[f"{label}_{key.rstrip('_')}"] = val
    for field in FIELDS:
        if field not in response:
            response[field] = np.nan
    checks = 0
    additions = []
    event_lookup = {row.Index: row for row in events.itertuples()}
    for row in response[response.response_status == "eligible"].itertuples():
        event = event_lookup[row.event_id]
        start_time = event.signal_time + pd.Timedelta(minutes=30)
        end_time = start_time + pd.Timedelta(minutes=row.horizon * 30)
        i, j = np.searchsorted(times, [start_time.to_datetime64(), end_time.to_datetime64()])
        path = values[i:j]
        assert len(path)
        expected_return = (path[-1, 3] - event.signal_close) / event.candle_range
        assert np.isclose(expected_return, row.forward_r, rtol=0, atol=1e-10)
        assert np.isclose((path[:, 1].max() - event.signal_close) / event.candle_range, row.up_excursion_r, rtol=0, atol=1e-10)
        assert np.isclose((path[:, 2].min() - event.signal_close) / event.candle_range, row.down_excursion_r, rtol=0, atol=1e-10)
        checks += 1
        full = len(path) == row.horizon * 30 and np.array_equal(times[i:j], start_time.to_datetime64() + np.arange(row.horizon * 30) * np.timedelta64(1, "m"))
        new = dict(index=row.Index, path_status="complete" if full else "missing_minutes")
        if full:
            for label, size in (("r", event.candle_range), ("a", event.atr_lag)):
                if np.isfinite(size) and size > 0:
                    new.update({f"{label}_{key}": val for key, val in barrier_path(path, event.signal_close, size).items()})
        additions.append(new)
    updates = pd.DataFrame(additions).set_index("index")
    response.loc[updates.index, updates.columns] = updates
    return response, checks


def summary(f):
    out = dict(n=len(f), n_endpoint=int(f.r_return.notna().sum()), n_atr=int(f.a_return.notna().sum()),
               n_path=int(f.r_hit_both.notna().sum()))
    out.update({name: float(f[name].mean()) if f[name].notna().any() else None for name in FIELDS})
    return out


def estimate(a, b, period, interval):
    output = {}
    for field in INTERVAL_FIELDS:
        x, y = a.dropna(subset=[field]), b.dropna(subset=[field])
        if interval:
            output[field] = difference(x, y, field, "submission_time", period)
        else:
            output[field] = dict(difference=float(x[field].mean() - y[field].mean()) if len(x) and len(y) else None)
    return output


def analyse(features, responses):
    data = features.merge(responses, on="event_id", validate="many_to_many")
    assert not data.duplicated(["event_id", "source", "horizon"]).any()
    groups, contrasts, pairs_out, balances = [], [], [], []
    for source in SOURCES:
        for period in PERIODS:
            base = data[(data.source == source) & (data.period == period)]
            for population in ("source", "common"):
                f = base if population == "source" else base[base.common]
                for year in ["all"] + sorted(f.year.unique().tolist()):
                    y = f if year == "all" else f[f.year == year]
                    for horizon in HORIZONS:
                        h = y[y.horizon == horizon]
                        for label in ("breach_reclaim", "breach_unrecovered", "fast", "middle", "slow"):
                            chosen = h[h.group == label] if label.startswith("breach") else h[h.speed_group == label]
                            groups.append(dict(source=source, period=period, population=population, year=year,
                                               horizon=horizon, group=label, **summary(chosen)))
            # Matching uses the fixed eligible 90-minute pool and only pre-outcome covariates.
            pool = base[(base.horizon == 3) & (base.response_status == "eligible") &
                        (base.signal_path_status == "complete")].dropna(subset=list(MATCH_COLUMNS))
            for contrast, cutoff in (("speed", 1), ("speed", 2), ("speed", 3), ("reclaim", 0)):
                if contrast == "speed":
                    a = pool[(pool.group == "breach_reclaim") & (pool.recovery_delay <= cutoff)]
                    b = pool[(pool.group == "breach_reclaim") & (pool.recovery_delay >= 6)]
                else:
                    a, b = pool[pool.group == "breach_reclaim"], pool[pool.group == "breach_unrecovered"]
                a, b = a.sort_values("signal_time"), b.sort_values("signal_time")
                pairs = match_pairs(a, b)
                for pair_id, (i, j, cost) in enumerate(pairs):
                    pairs_out.append(dict(source=source, period=period, contrast=contrast, cutoff=cutoff, pair_id=pair_id,
                                          a_event=a.iloc[i].event_id, b_event=b.iloc[j].event_id, cost=cost))
                ia, ib = ([p[0] for p in pairs], [p[1] for p in pairs])
                for selection, x, y in (("unmatched_pool", a, b), ("matched", a.iloc[ia], b.iloc[ib])):
                    for row in covariate_balance(x, y):
                        balances.append(dict(source=source, period=period, contrast=contrast, cutoff=cutoff,
                                             selection=selection, n_a=len(x), n_b=len(y), **row))
                    for horizon in HORIZONS:
                        hh = base[base.horizon == horizon].set_index("event_id")
                        xx, yy = hh.reindex(x.event_id), hh.reindex(y.event_id)
                        if selection == "matched":
                            valid = xx.r_return.notna().to_numpy() & yy.r_return.notna().to_numpy()
                            xx, yy = xx.iloc[np.flatnonzero(valid)], yy.iloc[np.flatnonzero(valid)]
                        else:
                            xx, yy = xx.dropna(subset=["r_return"]), yy.dropna(subset=["r_return"])
                        interval = horizon == 3 and cutoff in (0, 2)
                        contrasts.append(dict(source=source, period=period, contrast=contrast, cutoff=cutoff,
                                              selection=selection, horizon=horizon, a=summary(xx), b=summary(yy),
                                              difference=estimate(xx, yy, period, interval)))
    return data, groups, contrasts, pairs_out, balances


def decision(contrasts):
    def passes(h=3, cutoff=2, clear=False):
        selected = [r for r in contrasts if r["source"] == "current_session" and r["selection"] == "matched"
                    and r["contrast"] == "speed" and r["cutoff"] == cutoff and r["horizon"] == h]
        assert len(selected) == 2
        return all(r["a"]["n_atr"] >= 100 and r["b"]["n_atr"] >= 100 and
                   all(r["difference"][k]["difference"] is not None and r["difference"][k]["difference"] > 0 and
                       (not clear or r["difference"][k].get("lower", -1) > 0) for k in ("a_return", "a_balance")) for r in selected)
    gates = dict(primary_clear=passes(clear=True), neighboring_horizons=all(passes(h=h) for h in (1, 6)),
                 neighboring_speed_cutoffs=all(passes(cutoff=c) for c in (1, 3)))
    return dict(gates=gates, candidate=all(gates.values()))


def fmt(x, digits=3):
    return "n/a" if x is None or pd.isna(x) else f"{x:,.{digits}f}"


def report(groups, contrasts, verdict):
    lines = ["# Q9: speed and symmetric response tables", "", "[Frozen protocol](../../../docs/setups/horizontal/support-reclaim-long/q09-reclaim-speed/PROTOCOL.md).",
             "", f"Candidate for a separate early-entry experiment: **{verdict['candidate']}**. Gates: `{verdict['gates']}`.",
             "", "## Current-session raw groups at 90 minutes", "", "Endpoint and path probabilities are distinct; all values are from signal close, not a simulated fill.",
             "", "| Period | Group | n endpoint | n path | Up endpoint % | Down endpoint % | Balance pp | Mean R | Mean abs R | Up hit % | Down hit % | Both hit % | Up first % | Down first % | Ambiguous % |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    percent = lambda x: fmt(100 * x, 1) if x is not None else "n/a"
    for r in groups:
        if r["source"] != "current_session" or r["year"] != "all" or r["horizon"] != 3 or r["population"] != "source":
            continue
        values = [r["period"], r["group"], str(r["n_endpoint"]), str(r["n_path"])]
        values += [percent(r[k]) for k in ("r_up", "r_down", "r_balance")]
        values += [fmt(r[k]) for k in ("r_return", "r_absolute")]
        values += [percent(r[k]) for k in ("r_hit_up", "r_hit_down", "r_hit_both", "r_first_up", "r_first_down", "r_first_ambiguous")]
        lines.append("| " + " | ".join(values) + " |")
    lines += ["", "## Primary speed contrasts, fast <=2 versus slow >=6 minutes", "",
              "A is lagged 14-bar mean true range. Differences are fast minus slow. Intervals are descriptive month-block intervals with matching held fixed.",
              "", "| Source | Period | Sample | Fast n | Slow n | Up endpoint difference pp | Down endpoint difference pp | Mean A difference [95%] | A balance difference pp [95%] |",
              "|---|---|---|---:|---:|---:|---:|---|---|"]
    for r in contrasts:
        if r["contrast"] != "speed" or r["cutoff"] != 2 or r["horizon"] != 3:
            continue
        d = r["difference"]
        lines.append(f"| {r['source']} | {r['period']} | {r['selection']} | {r['a']['n']} | {r['b']['n']} | {percent(d['r_up']['difference'])} | {percent(d['r_down']['difference'])} | {fmt(d['a_return']['difference'])} [{fmt(d['a_return'].get('lower'))}, {fmt(d['a_return'].get('upper'))}] | {percent(d['a_balance']['difference'])} [{percent(d['a_balance'].get('lower'))}, {percent(d['a_balance'].get('upper'))}] |")
    lines += ["", "All source/year/horizon summaries: `groups.csv`. Raw/common-source groups are separate. All speed cutoffs and matched reclaim/unrecovered comparisons: `contrasts.json`. Pair audit and balance: `pairs.csv`, `balance.csv`. Missing minute windows and lagged volatility stay explicit in feature/coverage exports.", ""]
    (STUDY / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    print("Verifying upstream hashes and loading minute history...", flush=True)
    hash_count = verify_upstream()
    fpath = UPSTREAM / "attempt_features.csv"
    features = pd.read_csv(fpath, parse_dates=["signal_time", "submission_time"])
    q8 = pd.read_csv(UPSTREAM / "forward_responses.csv")
    bars = pd.read_csv(UPSTREAM / "m30_reference.csv", index_col=0, parse_dates=[0])
    minutes = load_minutes()
    reconstructed = minutes.groupby(minutes.index.floor("30min")).agg(dict(open="first", high="max", low="min", close="last"))
    pd.testing.assert_frame_equal(reconstructed, bars.reindex(reconstructed.index), check_names=False)
    scale = lagged_scale(bars, pd.read_csv(ROLLS))
    print("Extracting minute breach/recovery paths...", flush=True)
    features, audit, cache = extract_features(features, minutes, scale)
    del cache
    print("Checking endpoints and ordering symmetric barriers...", flush=True)
    responses, checks = build_responses(features, q8, minutes)
    features.to_csv(STUDY / "speed_features.csv", index=False)
    responses.to_csv(STUDY / "responses.csv", index=False)
    print("Matching comparable events and computing uncertainty...", flush=True)
    data, groups, contrasts, pairs, balance = analyse(features, responses)
    pd.DataFrame(groups).to_csv(STUDY / "groups.csv", index=False)
    pd.DataFrame(pairs).to_csv(STUDY / "pairs.csv", index=False)
    pd.DataFrame(balance).to_csv(STUDY / "balance.csv", index=False)
    data.groupby(["source", "period", "group", "speed_group", "horizon", "signal_path_status", "response_status", "path_status"]).size().rename("n").to_csv(STUDY / "coverage.csv")
    verdict = decision(contrasts)
    (STUDY / "contrasts.json").write_text(json.dumps(contrasts, indent=2), encoding="utf-8")
    (STUDY / "decision.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    audit.update(upstream_hashes_checked=hash_count, minute_rows=len(minutes), reference_bars_checked=len(reconstructed),
                 forward_windows_checked=checks, total_attempt_source_rows=len(features))
    paths = [SOURCE, ROLLS, fpath, UPSTREAM / "forward_responses.csv", UPSTREAM / "m30_reference.csv", Path(__file__),
             ROOT / "python" / "reclaim_speed.py", ROOT / "python" / "analyze_breach_reclaim.py",
             ROOT / "python" / "analyze_price_levels.py", ROOT / "docs" / "setups" / "horizontal" / "support-reclaim-long" / "q09-reclaim-speed" / "PROTOCOL.md"]
    provenance = dict(audits=audit, files=[dict(path=str(p), sha256=sha256(p)) for p in paths])
    (STUDY / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    report(groups, contrasts, verdict)
    print(json.dumps(dict(audits=audit, decision=verdict), indent=2))
    print(f"Saved {STUDY / 'report.md'}")


if __name__ == "__main__":
    main()
