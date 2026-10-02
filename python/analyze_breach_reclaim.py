"""Q8 support breach/reclaim diagnostic. See docs/BREACH_RECLAIM_PROTOCOL.md."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_price_levels import (ROOT, BASE, PERIODS, SOURCES, build_level_maps,
                                  load_and_audit, sha256, metrics)
from trend_regimes import SOURCE, ROLLS
from verify_location_validation import read_rows

STUDY = ROOT / "Reports" / "breach_reclaim_20261003"
TREND = ROOT / "Reports" / "trend_rr_20261002"
TAG = "trendrr_20261002_f50_baseline"
GROUPS = ("no_contact", "touch_only", "breach_reclaim", "breach_unrecovered",
          "breach_exact_close", "opened_at_or_below", "unavailable")
BREACHES = ("breach_reclaim", "breach_unrecovered", "breach_exact_close")
HORIZONS = (1, 3, 6)
TICKS = (1, 2, 4)
TICK_SIZE = .25


def build_reference():
    parts = []
    columns = ["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"]
    for chunk in pd.read_csv(SOURCE, sep="\t", usecols=columns, chunksize=500000):
        chunk = chunk[chunk["<TIME>"] >= "01:00:00"].copy()
        chunk["minute"] = pd.to_datetime(chunk["<DATE>"] + " " + chunk["<TIME>"], format="%Y.%m.%d %H:%M:%S")
        chunk["bar"] = chunk.minute.dt.floor("30min")
        parts.append(chunk.groupby("bar").agg(open=("<OPEN>", "first"), high=("<HIGH>", "max"),
                    low=("<LOW>", "min"), close=("<CLOSE>", "last"), last_minute=("minute", "max")))
    reference = pd.concat(parts).groupby(level=0).agg(dict(open="first", high="max", low="min", close="last", last_minute="max"))
    assert reference.index.is_unique and reference.index.is_monotonic_increasing
    ends = (reference.last_minute + pd.Timedelta(minutes=1)).groupby(reference.index.normalize()).max()
    return reference[["open", "high", "low", "close"]], ends


def read_table(path):
    return pd.DataFrame(read_rows(path))


def load_attempts(trades, bars):
    paths = [TREND / f"{TAG}_signals.csv", TREND / f"runband_{TAG}_1.00.csv",
             TREND / f"runband_{TAG}_1.00_stats.csv", TREND / f"{TAG}.ini"]
    assert (TREND / f"{TAG}.completed.json").exists()
    ini = paths[3].read_text(encoding="utf-16").splitlines()
    for value in ("Model=1", "Period=M30", "Symbol=MNQcontDTBNT20102026_2", "BullRR=1.0", "BearRR=1.0", "AverageNearStopR=0"):
        assert value in ini, value
    stats = read_rows(paths[2])[0]
    assert int(stats["trend_export_errors"]) == 0 and int(stats["trend_close_errors"]) == 0
    assert float(stats["bull_rr"]) == float(stats["bear_rr"]) == 1
    ledger = read_table(paths[1])
    assert len(ledger) == int(stats["trades"])
    assert np.isclose(ledger.trade_profit.astype(float).sum(), float(stats["net_profit"]), rtol=0, atol=1e-6)
    for c in ("entry_time", "exit_time", "signal_time"):
        ledger[c] = pd.to_datetime(ledger[c], format="%Y.%m.%d %H:%M:%S")
    for period, (start, end) in PERIODS.items():
        old = trades[trades.period == period].reset_index(drop=True)
        new = ledger[ledger.entry_time.between(start, end, inclusive="left")].reset_index(drop=True)
        assert len(old) == len(new)
        for c in ("entry_time", "exit_time", "signal_time"):
            assert np.array_equal(old[c], new[c]), c
        for c in ("trade_profit", "candle_range", "red_run", "mae_money", "mfe_money", "signal_open", "signal_high", "signal_low", "signal_close"):
            assert np.array_equal(old[c].astype(float), new[c].astype(float)), c
        assert (new.assigned_rr.astype(float) == 1).all()

    raw = read_table(paths[0])
    for c in ("signal_time", "submission_time"):
        raw[c] = pd.to_datetime(raw[c], format="%Y.%m.%d %H:%M:%S")
    for c in ("open", "high", "low", "close", "red_run"):
        raw[c] = pd.to_numeric(raw[c])
    raw.rename(columns={c: "signal_" + c for c in ("open", "high", "low", "close")}, inplace=True)
    frames = []
    for period, (start, end) in PERIODS.items():
        f = raw[raw.submission_time.between(start, end, inclusive="left")].copy()
        f["period"] = period
        frames.append(f)
    attempts = pd.concat(frames, ignore_index=True)
    assert attempts.signal_time.is_unique
    assert (attempts.strategy == "RR").all() and attempts.red_run.between(1, 3).all()
    assert (attempts.signal_close < attempts.signal_open).all()
    assert (attempts.submission_time >= attempts.signal_time + pd.Timedelta(minutes=30)).all()
    lookup = bars.reindex(attempts.signal_time).reset_index(drop=True)
    for c in ("open", "high", "low", "close"):
        assert np.array_equal(attempts[f"signal_{c}"], lookup[c]), c
        assert np.allclose(attempts[f"signal_{c}"] / TICK_SIZE, np.round(attempts[f"signal_{c}"] / TICK_SIZE), rtol=0, atol=1e-8)
    attempts["candle_range"] = attempts.signal_high - attempts.signal_low
    assert (attempts.candle_range > 0).all()
    attempts["event_id"] = attempts.signal_time.dt.strftime("%Y%m%d_%H%M")
    attempts["year"] = attempts.submission_time.dt.year
    assert trades.signal_time.is_unique and trades.signal_time.isin(attempts.signal_time).all()
    attempts["filled"] = attempts.signal_time.isin(trades.signal_time)
    assert attempts.filled.sum() == len(trades)
    positions = bars.index.get_indexer(attempts.signal_time)
    assert (positions > 0).all()
    attempts["previous_close"] = bars.close.to_numpy()[positions - 1]
    matched = attempts.set_index("signal_time").reindex(trades.signal_time)
    assert (matched.submission_time.to_numpy() <= trades.entry_time.to_numpy()).all()
    return attempts, paths


def classify(f):
    missing = f.status != "eligible"
    level, o, low, close = f.low, f.signal_open, f.signal_low, f.signal_close
    return np.select([missing, o <= level, low > level, low == level,
                      close > level, close < level],
                     ["unavailable", "opened_at_or_below", "no_contact", "touch_only",
                      "breach_reclaim", "breach_unrecovered"], default="breach_exact_close")


def attach(attempts, maps):
    frames = []
    for source in SOURCES:
        f = pd.concat([attempts.reset_index(drop=True), maps[source].reindex(attempts.signal_time).reset_index(drop=True)], axis=1)
        assert f.status.notna().all()
        f["source"] = source
        f["group"] = classify(f)
        fresh = f.group.isin(BREACHES)
        f["penetration_ticks"] = ((f.low - f.signal_low) / TICK_SIZE).where(fresh)
        f["penetration_r"] = ((f.low - f.signal_low) / f.candle_range).where(fresh)
        assert (f.loc[fresh, "penetration_ticks"] >= 1).all()
        assert np.allclose(f.loc[fresh, "penetration_ticks"], f.loc[fresh, "penetration_ticks"].round(), rtol=0, atol=1e-8)
        p = f.penetration_ticks
        f["penetration_bin"] = np.select([p == 1, (p >= 2) & (p <= 4), (p >= 5) & (p <= 8), p > 8],
                                          ["1", "2_to_4", "5_to_8", "above_8"], default="not_fresh_breach")
        f["gap_down"] = (f.status == "eligible") & (f.previous_close >= f.low) & (f.signal_open < f.low)
        frames.append(f)
    f = pd.concat(frames, ignore_index=True)
    common = f.groupby("event_id").status.agg(lambda s: (s == "eligible").all())
    f["common"] = f.event_id.map(common)
    assert len(f) == len(attempts) * 3 and not f.duplicated(["event_id", "source"]).any()
    return f


def forward_response(events, bars, session_ends, horizon):
    loc = bars.index.get_indexer(events.signal_time)
    assert (loc >= 0).all()
    future = loc[:, None] + np.arange(1, horizon + 1)
    in_data = (future < len(bars)).all(axis=1)
    safe = np.minimum(future, len(bars) - 1)
    actual = bars.index.to_numpy()[safe]
    expected = events.signal_time.to_numpy()[:, None] + np.arange(1, horizon + 1) * np.timedelta64(30, "m")
    contiguous = (actual == expected).all(axis=1)
    endpoint = events.signal_time + pd.Timedelta(minutes=30 * (horizon + 1))
    ends = session_ends.reindex(events.signal_time.dt.normalize()).to_numpy()
    same_session = endpoint.to_numpy() <= ends
    fresh_submission = (events.submission_time >= events.signal_time + pd.Timedelta(minutes=30)) & (events.submission_time < events.signal_time + pd.Timedelta(minutes=60))
    reason = np.select([~fresh_submission, ~in_data, ~same_session, ~contiguous],
                       ["delayed_submission", "end_of_data", "session_end", "missing_bar"], default="eligible")
    valid = reason == "eligible"
    close = bars.close.to_numpy()[safe[:, -1]]
    upward = bars.high.to_numpy()[safe].max(axis=1)
    downward = bars.low.to_numpy()[safe].min(axis=1)
    result = pd.DataFrame(dict(event_id=events.event_id.to_numpy(), horizon=horizon, response_status=reason))
    for label, price in (("forward_r", close), ("up_excursion_r", upward), ("down_excursion_r", downward)):
        result[label] = np.where(valid, (price - events.signal_close) / events.candle_range, np.nan)
    result["up_half_r"] = np.where(valid, result.forward_r >= .5, np.nan)
    result["up_any"] = np.where(valid, result.forward_r > 0, np.nan)
    return result


def response_metrics(f):
    available = f[f.response_status == "eligible"]
    return dict(n=len(f), observed=len(available), filled_share=float(f.filled.mean()) if len(f) else None,
                mean_r=float(available.forward_r.mean()) if len(available) else None,
                median_r=float(available.forward_r.median()) if len(available) else None,
                up_half_rate=float(available.up_half_r.mean()) if len(available) else None,
                up_any_rate=float(available.up_any.mean()) if len(available) else None,
                mean_up_excursion_r=float(available.up_excursion_r.mean()) if len(available) else None,
                mean_down_excursion_r=float(available.down_excursion_r.mean()) if len(available) else None)


def trade_metrics(f):
    result = metrics(f)
    result["win_rate"] = float((f.net > 0).mean()) if len(f) else None
    result["mean_range"] = float(f.candle_range.mean()) if len(f) else None
    for key, values in (("mae", f.mae_money / (2 * f.candle_range)), ("mfe", f.mfe_money / (2 * f.candle_range))):
        result[f"mean_{key}_r"] = float(values.mean()) if len(f) else None
        result[f"median_{key}_r"] = float(values.median()) if len(f) else None
    return result


def difference(a, b, field, time_column, period):
    if a.empty or b.empty:
        return dict(difference=None, lower=None, upper=None, valid_resamples=0)
    start, end = PERIODS[period]
    months = pd.period_range(pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(days=1), freq="M")
    blocks = []
    for f in (a, b):
        g = f.groupby(f[time_column].dt.to_period("M"))[field].agg(["sum", "count"])
        blocks.append(g.reindex(months, fill_value=0).to_numpy())
    draws = np.random.default_rng(20261003).integers(0, len(months), size=(2000, len(months)))
    x, y = (v[draws].sum(axis=1) for v in blocks)
    valid = (x[:, 1] > 0) & (y[:, 1] > 0)
    delta = x[valid, 0] / x[valid, 1] - y[valid, 0] / y[valid, 1]
    low, high = np.quantile(delta, [.025, .975])
    return dict(difference=float(a[field].mean() - b[field].mean()), lower=float(low), upper=float(high), valid_resamples=int(valid.sum()))


def summarize(price, trades):
    price_rows, trade_rows, contrasts, exclusions, depth_rows = [], [], [], [], []
    for source in SOURCES:
        for period in PERIODS:
            p0 = price[(price.source == source) & (price.period == period)]
            t0 = trades[(trades.source == source) & (trades.period == period)]
            for population in ("source", "common"):
                p = p0 if population == "source" else p0[p0.common]
                t = t0 if population == "source" else t0[t0.common]
                for year in ["all"] + sorted(t0.year.unique().tolist()):
                    tp = t if year == "all" else t[t.year == year]
                    pp = p if year == "all" else p[p.year == year]
                    for group in GROUPS + ("all_fresh_breaches",):
                        selected = tp[tp.group.isin(BREACHES)] if group == "all_fresh_breaches" else tp[tp.group == group]
                        trade_rows.append(dict(source=source, period=period, population=population, year=year, group=group, **trade_metrics(selected)))
                        for horizon in HORIZONS:
                            pf = pp[pp.horizon == horizon]
                            selected = pf[pf.group.isin(BREACHES)] if group == "all_fresh_breaches" else pf[pf.group == group]
                            price_rows.append(dict(source=source, period=period, population=population, year=year, group=group,
                                                   horizon=horizon, **response_metrics(selected)))
                for horizon in HORIZONS:
                    pf = p[p.horizon == horizon]
                    for (group, status), rows in pf.groupby(["group", "response_status"]):
                        exclusions.append(dict(source=source, period=period, population=population, horizon=horizon,
                                               group=group, response_status=status, n=len(rows)))
                    for tick in TICKS:
                        f = pf[(pf.response_status == "eligible") & (pf.penetration_ticks >= tick)]
                        a, b = (f[f.group == g] for g in ("breach_reclaim", "breach_unrecovered"))
                        contrasts.append(dict(kind="price", source=source, period=period, population=population, horizon=horizon,
                                              min_ticks=tick, reclaim=response_metrics(a), unrecovered=response_metrics(b),
                                              mean_r=difference(a, b, "forward_r", "submission_time", period),
                                              probability=difference(a, b, "up_half_r", "submission_time", period)))
                for tick in TICKS:
                    f = t[t.penetration_ticks >= tick]
                    a, b = (f[f.group == g] for g in ("breach_reclaim", "breach_unrecovered"))
                    contrasts.append(dict(kind="trade", source=source, period=period, population=population,
                                          min_ticks=tick, reclaim=trade_metrics(a), unrecovered=trade_metrics(b),
                                          mean_r=difference(a, b, "net_r", "entry_time", period)))
                for depth in ("1", "2_to_4", "5_to_8", "above_8"):
                    for group in ("breach_reclaim", "breach_unrecovered"):
                        f = t[(t.penetration_bin == depth) & (t.group == group)]
                        depth_rows.append(dict(kind="trade", source=source, period=period, population=population, depth=depth,
                                               group=group, **trade_metrics(f)))
                        f = p[(p.penetration_bin == depth) & (p.group == group) & (p.horizon == 3)]
                        depth_rows.append(dict(kind="price", source=source, period=period, population=population, depth=depth,
                                               group=group, **response_metrics(f)))
    return price_rows, trade_rows, contrasts, exclusions, depth_rows


def decisions(contrasts):
    def price_pass(horizon=3, ticks=1, population="source", clear=False):
        rows = [r for r in contrasts if r["kind"] == "price" and r["source"] == "current_session" and
                r["horizon"] == horizon and r["min_ticks"] == ticks and r["population"] == population]
        assert len(rows) == 2
        return all(r["reclaim"]["observed"] >= 200 and r["unrecovered"]["observed"] >= 200 and
                   all(r[k]["difference"] is not None and r[k]["difference"] > 0 and
                       (not clear or r[k]["lower"] > 0) for k in ("mean_r", "probability")) for r in rows)
    filled = [r for r in contrasts if r["kind"] == "trade" and r["source"] == "current_session" and
              r["population"] == "source" and r["min_ticks"] == 1]
    assert len(filled) == 2
    trade_pass = all(r["reclaim"]["n"] >= 200 and r["unrecovered"]["n"] >= 200 and
                     r["reclaim"]["pf"] is not None and r["unrecovered"]["pf"] is not None and
                     r["reclaim"]["pf"] > max(1, r["unrecovered"]["pf"]) and r["mean_r"]["difference"] > 0 for r in filled)
    gates = dict(primary_price_clear_both_periods=price_pass(clear=True), trade_better_both_periods=trade_pass,
                 horizons_positive=all(price_pass(horizon=h) for h in (1, 6)),
                 depths_positive=all(price_pass(ticks=t) for t in (2, 4)), common_positive=price_pass(population="common"))
    return dict(gates=gates, candidate=all(gates.values()))


def fmt(x, digits=3):
    return "n/a" if x is None or pd.isna(x) else f"{x:,.{digits}f}"


def write_report(audits, attempts, contrasts, decision):
    lines = ["# Q8 breach/reclaim diagnostic tables", "", "[Frozen protocol](../../docs/BREACH_RECLAIM_PROTOCOL.md). 2026-10-03.",
             "", "Current-session low is primary; previous-session and previous-week lows are separate comparisons.",
             "", f"Candidate for a full strategy experiment: **{decision['candidate']}**. Gates: `{decision['gates']}`.",
             "", "## Baseline", "", f"Audits: `{audits}`", "",
             "All-attempt counts: `" + str(attempts.groupby("period").size().to_dict()) + "`.",
             "", "## Price response at 3 M30 bars, minimum 1 tick", "",
             "Further movement is measured from the signal close; +0.5R is a forward endpoint event, not a trade target or an observed stop-order event.",
             "", "| Sample | Source | Period | Reclaim n | Unrecovered n | Reclaim >=+0.5R | Unrecovered >=+0.5R | Difference pp [95%] | Reclaim mean R | Unrecovered mean R | Difference R [95%] |",
             "|---|---|---|---:|---:|---:|---:|---|---:|---:|---|"]
    for r in contrasts:
        if r["kind"] != "price" or r["horizon"] != 3 or r["min_ticks"] != 1:
            continue
        a, b, prob, mean = r["reclaim"], r["unrecovered"], r["probability"], r["mean_r"]
        pct = lambda x: fmt(100 * x, 1) if x is not None else "n/a"
        lines.append(f"| {r['population']} | {r['source']} | {r['period']} | {a['observed']} | {b['observed']} | {pct(a['up_half_rate'])}% | {pct(b['up_half_rate'])}% | {pct(prob['difference'])} [{pct(prob['lower'])}, {pct(prob['upper'])}] | {fmt(a['mean_r'])} | {fmt(b['mean_r'])} | {fmt(mean['difference'])} [{fmt(mean['lower'])}, {fmt(mean['upper'])}] |")
    lines += ["", "## Filled trade comparison, minimum 1 tick", "", "Net of $1.05 per round trip. MAE is signed; more negative means a larger adverse excursion.",
              "", "| Sample | Source | Period | Group | n | Net $ | PF | Avg net R | Win % | Avg MAE R | Avg MFE R |", "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in contrasts:
        if r["kind"] != "trade" or r["min_ticks"] != 1:
            continue
        for group in ("reclaim", "unrecovered"):
            m = r[group]
            lines.append(f"| {r['population']} | {r['source']} | {r['period']} | {group} | {m['n']} | {fmt(m['net'], 0)} | {fmt(m['pf'])} | {fmt(m['avg_net_r'])} | {fmt(100 * m['win_rate'], 1) if m['win_rate'] is not None else 'n/a'} | {fmt(m['mean_mae_r'])} | {fmt(m['mean_mfe_r'])} |")
    lines += ["", "Full groups and years: `price_groups.csv`, `trade_groups.csv`. Penetration bins: `depth_groups.csv`. All horizon/depth sensitivity contrasts and intervals: `contrasts.json`. Exclusions: `response_coverage.csv` and `level_coverage.csv`.",
              "", "These are exploratory associations on previously examined data. Price responses include unfilled attempts; trade PnL is conditional on a fill. Neither establishes that stop orders caused the move. No filtered-strategy performance is inferred from subset sums.", ""]
    (STUDY / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    print("Rebuilding reference and checking baseline...", flush=True)
    bars, ends = build_reference()
    bars.to_csv(STUDY / "m30_reference.csv")
    ends.to_csv(STUDY / "session_ends.csv")
    trades, audits, files = load_and_audit(bars)
    attempts, signal_files = load_attempts(trades, bars)
    print("Classifying all attempts and filled trades...", flush=True)
    features = attach(attempts, build_level_maps(bars, pd.read_csv(ROLLS)))
    outcome = trades[["signal_time", "entry_time", "exit_time", "trade_profit", "net", "net_r", "mae_money", "mfe_money"]]
    trade_features = features[features.filled].merge(outcome, on="signal_time", validate="many_to_one")
    assert len(trade_features) == len(trades) * 3
    responses = pd.concat([forward_response(attempts, bars, ends, h) for h in HORIZONS], ignore_index=True)
    price = features.merge(responses, on="event_id", validate="many_to_many")
    assert len(price) == len(attempts) * 3 * 3
    assert not price.duplicated(["event_id", "source", "horizon"]).any()
    features.to_csv(STUDY / "attempt_features.csv", index=False)
    trade_features.to_csv(STUDY / "trade_features.csv", index=False)
    responses.to_csv(STUDY / "forward_responses.csv", index=False)
    coverage = features.groupby(["source", "period", "status"]).size().rename("n").reset_index()
    coverage.to_csv(STUDY / "level_coverage.csv", index=False)
    print("Computing frozen contrasts and month-block intervals...", flush=True)
    pg, tg, contrasts, exclusions, depths = summarize(price, trade_features)
    for name, rows in (("price_groups", pg), ("trade_groups", tg), ("response_coverage", exclusions), ("depth_groups", depths)):
        pd.DataFrame(rows).to_csv(STUDY / f"{name}.csv", index=False)
    decision = decisions(contrasts)
    (STUDY / "contrasts.json").write_text(json.dumps(contrasts, indent=2), encoding="utf-8")
    (STUDY / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    paths = files + signal_files + [SOURCE, ROLLS, Path(__file__), ROOT / "python" / "analyze_price_levels.py",
                                   ROOT / "python" / "verify_location_validation.py", ROOT / "python" / "trend_regimes.py",
                                   ROOT / "docs" / "BREACH_RECLAIM_PROTOCOL.md"]
    provenance = dict(baseline_audits=audits, attempt_counts=attempts.groupby("period").size().to_dict(),
                      files=[dict(path=str(p), sha256=sha256(p)) for p in paths])
    (STUDY / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    write_report(audits, attempts, contrasts, decision)
    print(json.dumps(dict(attempt_counts=provenance["attempt_counts"], decision=decision), indent=2))
    print(f"Saved {STUDY / 'report.md'}")


if __name__ == "__main__":
    main()
