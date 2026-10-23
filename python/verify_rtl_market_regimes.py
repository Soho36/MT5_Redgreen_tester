"""Independent audits for the frozen RTL daily regime screen.

No analysis helpers are imported. Labels use explicit past-array slices, HTML
orders/deals are parsed independently, and arithmetic is rebuilt from source.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import statistics
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / "Reports/rtl_market_regimes_20261023"
BASE = ROOT / "Reports/timeframe_baseline_20261015"
TAG = "tf_20261015_rtl_m30_rr1p0"
RAW = BASE / f"runband_{TAG}_1.00.csv"
MINUTES = Path(r"F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv")
ROLLS = MINUTES.with_name("MT5_NQ_continuous_2010-2026_rolls.csv")
PROTOCOL = ROOT / "docs/baseline/rtl-market-regimes/PROTOCOL.md"
PROTOCOL_SHA256 = "c3e8d6035ae712cb0cbf5da666f87d2f4ace29e6722fb314591c7d28464b32fa"
ERAS = {"2016-19": ("2016-01-01", "2020-01-01"),
        "2020-26": ("2020-01-01", "2026-10-01")}
GROUPS = tuple(f"{trend}_{vol}" for trend in ("bull", "neutral", "bear")
               for vol in ("normal", "elevated"))
CAUSAL_COLUMNS = ["previous_date", "previous_close", "sma50", "sma200", "trend",
                  "volatility_prior", "volatility_threshold_p70", "volatility_threshold_p75",
                  "volatility_threshold_p80", "volatility_robust_prior", "volatility_robust_threshold",
                  "group", "group_p70", "group_p80", "group_roll_robust"]


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def json_scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported verification JSON value: {type(value).__name__}")


def linear_percentile(values, probability):
    """Explicit sorted-array interpolation, independent of pandas quantile."""
    values = sorted(float(value) for value in values)
    if not values or not all(math.isfinite(value) for value in values):
        return math.nan
    location = (len(values) - 1) * probability
    low = int(math.floor(location))
    high = int(math.ceil(location))
    return values[low] + (location - low) * (values[high] - values[low])


def reference_labels(closes, switch_dates=()):
    """Return labels from literal past slices specified by the frozen protocol."""
    closes = closes.sort_index().astype(float)
    assert closes.index.is_unique and np.isfinite(closes).all() and (closes > 0).all()
    dates, price = closes.index, closes.to_numpy()
    switches = {pd.Timestamp(date).normalize() for date in switch_dates}
    returns = np.full(len(price), np.nan)
    returns[1:] = np.log(price[1:] / price[:-1])
    robust_returns = returns.copy()
    for i, date in enumerate(dates):
        if date in switches:
            robust_returns[i] = np.nan
    vol = np.full(len(price), np.nan)
    robust_vol = np.full(len(price), np.nan)
    for t in range(20, len(price)):
        sample = returns[t-19:t+1]
        assert len(sample) == 20 and np.isfinite(sample).all()
        vol[t] = statistics.stdev(sample)
        sample = robust_returns[t-19:t+1]
        sample = sample[np.isfinite(sample)]
        if len(sample) >= 15:
            robust_vol[t] = statistics.stdev(sample)
    rows = []
    for d, date in enumerate(dates):
        row = {"date": date, "close": price[d], "return_log": returns[d],
               "previous_date": dates[d-1] if d else pd.NaT,
               "previous_close": price[d-1] if d else np.nan,
               "sma50": statistics.fmean(price[d-50:d]) if d >= 50 else np.nan,
               "sma200": statistics.fmean(price[d-200:d]) if d >= 200 else np.nan,
               "volatility20": vol[d], "volatility_prior": vol[d-1] if d else np.nan,
               "volatility_robust20": robust_vol[d],
               "volatility_robust_prior": robust_vol[d-1] if d else np.nan,
               "roll_date": date in switches}
        trend = "warmup"
        if d >= 200:
            if row["previous_close"] > row["sma200"] and row["sma50"] > row["sma200"]:
                trend = "bull"
            elif row["previous_close"] < row["sma200"] and row["sma50"] < row["sma200"]:
                trend = "bear"
            else:
                trend = "neutral"
        row["trend"] = trend
        for percentile in (70, 75, 80):
            history = vol[d-253:d-1] if d >= 253 else []
            threshold = linear_percentile(history, percentile / 100) if len(history) == 252 else np.nan
            row[f"volatility_threshold_p{percentile}"] = threshold
            group = "warmup"
            if trend != "warmup" and math.isfinite(threshold) and math.isfinite(row["volatility_prior"]):
                group = trend + ("_elevated" if row["volatility_prior"] > threshold else "_normal")
            row["group" if percentile == 75 else f"group_p{percentile}"] = group
        history = robust_vol[d-253:d-1] if d >= 253 else []
        threshold = linear_percentile(history, .75) if len(history) == 252 else np.nan
        row["volatility_robust_threshold"] = threshold
        row["group_roll_robust"] = "warmup"
        if trend != "warmup" and math.isfinite(threshold) and math.isfinite(row["volatility_robust_prior"]):
            row["group_roll_robust"] = trend + ("_elevated" if row["volatility_robust_prior"] > threshold else "_normal")
        rows.append(row)
    return pd.DataFrame(rows).set_index("date")


def minute_closes(path=MINUTES):
    """Independent daily last-close reduction directly from the original minute file."""
    parts = []
    for chunk in pd.read_csv(path, sep="\t", usecols=["<DATE>", "<TIME>", "<CLOSE>"], chunksize=350000):
        eligible = chunk.loc[chunk["<TIME>"] >= "01:00:00"]
        parts.append(eligible.groupby("<DATE>", sort=False)["<CLOSE>"].last())
    closes = pd.concat(parts).groupby(level=0, sort=True).last()
    closes.index = pd.to_datetime(closes.index, format="%Y.%m.%d")
    closes.index.name = "date"
    return closes


def report_trades(path):
    """Recover original planned prices and complete deal history from HTML."""
    cell_pattern = re.compile(r"<td\b[^>]*>(.*?)</td>", re.I)
    tag_pattern = re.compile(r"<[^>]*>")
    time_pattern = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$")
    orders, results, active, section = {}, [], None, None
    number = lambda value: float(value.replace(" ", "").replace("\xa0", ""))
    with Path(path).open(encoding="utf-16") as stream:
        for line in stream:
            if ">Orders<" in line:
                section = "orders"
            elif ">Deals<" in line:
                section = "deals"
            if "<tr" not in line or "</tr>" not in line:
                continue
            cells = [html.unescape(tag_pattern.sub("", text)).strip() for text in cell_pattern.findall(line)]
            if not cells or not time_pattern.match(cells[0]):
                continue
            if section == "orders" and len(cells) == 11 and cells[3] == "buy stop":
                assert cells[2] == "MNQcontDTBNT20102026_2"
                ticket = int(cells[1])
                assert ticket not in orders
                orders[ticket] = {"submitted": cells[0], "requested_price": number(cells[5]),
                                  "original_sl": number(cells[6]), "state": cells[9]}
            elif section == "deals" and len(cells) == 13 and cells[3] != "balance":
                assert cells[2] == "MNQcontDTBNT20102026_2"
                assert number(cells[5]) == 1 and number(cells[8]) == 0 and number(cells[9]) == 0
                if cells[3:5] == ["buy", "in"]:
                    assert active is None
                    ticket = int(cells[7])
                    assert orders[ticket]["state"] == "filled"
                    active = dict(orders[ticket], ticket=ticket, entry_time=cells[0],
                                  fill_price=number(cells[6]), entry_profit=number(cells[10]))
                elif cells[3:5] == ["sell", "out"]:
                    assert active is not None
                    results.append(dict(active, exit_time=cells[0],
                                        trade_profit=active["entry_profit"]+number(cells[10]),
                                        exit_comment=cells[12]))
                    active = None
                else:
                    raise AssertionError(f"Unsupported deal: {cells}")
    assert active is None and results
    frame = pd.DataFrame(results)
    assert frame.ticket.is_unique
    for column in ("submitted", "entry_time", "exit_time"):
        frame[column] = pd.to_datetime(frame[column], format="%Y.%m.%d %H:%M:%S")
    return frame


def expect_close(actual, expected, context, tolerance=1e-8):
    assert np.allclose(np.asarray(actual, dtype=float), np.asarray(expected, dtype=float),
                       rtol=1e-10, atol=tolerance, equal_nan=True), context


def check_future_invariance(closes, switches):
    cut = len(closes) // 2
    original = reference_labels(closes, switches)
    changed = closes.copy()
    changed.iloc[cut:] *= np.linspace(1.2, 2.5, len(changed)-cut)
    altered = reference_labels(changed, switches)
    pd.testing.assert_frame_equal(original[CAUSAL_COLUMNS].iloc[:cut+1],
                                  altered[CAUSAL_COLUMNS].iloc[:cut+1], check_exact=True)
    return {"perturbation_session": str(closes.index[cut].date()), "unchanged_decision_rows": cut+1}


def full_year_negative_gate(year_rows):
    """Partial 2026 is excluded even when its trade count exceeds thirty."""
    eligible = [row for row in year_rows if 2016 <= int(row["year"]) <= 2025 and row["trades"] >= 30]
    negative = sum(row["net_dollars"] < 0 for row in eligible)
    return len(eligible) >= 5 and negative >= .6 * len(eligible)


# Summary and artifact checks are defined below; kept independent of analyzer code.

def checked_ledger(raw, report):
    """Join original sources and independently audit order timing and initial risk."""
    raw = raw.copy()
    for column in ("entry_time", "exit_time"):
        raw[column] = pd.to_datetime(raw[column])
    assert raw.ticket.is_unique and report.ticket.is_unique
    assert set(raw.ticket) == set(report.ticket), "HTML/ledger ticket coverage"
    merged = raw.merge(report, on="ticket", validate="one_to_one", suffixes=("", "_html"))
    for column in ("entry_time", "exit_time"):
        assert (merged[column] == merged[column + "_html"]).all(), column + " HTML agreement"
    expect_close(merged.trade_profit, merged.trade_profit_html, "HTML gross PnL")
    assert (merged.submitted <= merged.entry_time).all(), "submission after entry"
    assert (merged.entry_time <= merged.exit_time).all(), "entry after exit"
    session = merged.submitted.dt.normalize()
    assert (session == merged.entry_time.dt.normalize()).all(), "cross-date pending orders"
    assert (session == merged.exit_time.dt.normalize()).all(), "cross-date positions"
    assert (merged.submitted.dt.hour >= 1).all(), "excluded session minutes"
    ordered = merged.sort_values(["entry_time", "exit_time", "ticket"], kind="stable")
    assert (ordered.entry_time.iloc[1:].to_numpy() >= ordered.exit_time.iloc[:-1].to_numpy()).all(), "overlapping positions"
    merged["session"] = session
    merged["initial_risk_dollars"] = (merged.requested_price - merged.original_sl) * 2
    merged["fill_risk_dollars"] = (merged.fill_price - merged.original_sl) * 2
    assert (merged.initial_risk_dollars > 0).all(), "nonpositive planned risk"
    expect_close(merged.initial_risk_dollars, merged.candle_range * 2, "candle-range initial risk")
    merged["net_dollars"] = merged.trade_profit - 1.05
    merged["gross_r"] = merged.trade_profit / merged.initial_risk_dollars
    merged["net_r"] = merged.net_dollars / merged.initial_risk_dollars
    merged["commission_r"] = 1.05 / merged.initial_risk_dollars
    merged["holding_minutes"] = (merged.exit_time - merged.entry_time).dt.total_seconds() / 60
    merged["week_start"] = merged.session.dt.to_period("W-SUN").dt.start_time
    merged["year"] = merged.session.dt.year
    merged["primary"] = (merged.session >= "2016-01-01") & (merged.session < "2026-10-01")
    for stress in (1, 2):
        merged[f"stress{stress}_net_dollars"] = merged.net_dollars - stress
        merged[f"stress{stress}_net_r"] = merged[f"stress{stress}_net_dollars"] / merged.initial_risk_dollars
    return merged


def independent_metrics(frame, calendar):
    """Use explicit calendar sums and running peaks; never analyzer helpers."""
    calendar = pd.DatetimeIndex(calendar)
    daily_map = frame.groupby("session").net_dollars.sum().to_dict()
    daily = [float(daily_map.get(day, 0.)) for day in calendar]
    weekly = {}
    for day, value in zip(calendar, daily):
        week = day - pd.Timedelta(days=day.weekday())
        weekly[week] = weekly.get(week, 0.) + value
    count = len(frame)
    positive = frame.loc[frame.net_dollars > 0, "net_dollars"].sum()
    negative = frame.loc[frame.net_dollars < 0, "net_dollars"].sum()
    equity = peak = drawdown = 0.
    duration = 0
    peak_day = calendar[0]
    for day, value in zip(calendar, daily):
        equity += value
        if equity >= peak - 1e-9:
            peak, peak_day = max(peak, equity), day
        else:
            duration = max(duration, (day - peak_day).days)
        drawdown = max(drawdown, peak - equity)
    closed_equity = closed_peak = closed_dd = 0.
    for value in frame.sort_values(["exit_time", "entry_time", "ticket"], kind="stable").net_dollars:
        closed_equity += value
        closed_peak = max(closed_peak, closed_equity)
        closed_dd = max(closed_dd, closed_peak - closed_equity)
    result = {
        "trades": count, "active_sessions": frame.session.nunique(),
        "active_weeks": frame.week_start.nunique(), "eligible_sessions": len(calendar),
        "eligible_weeks": len(pd.date_range(calendar[0] - pd.Timedelta(days=calendar[0].weekday()),
                                             calendar[-1] - pd.Timedelta(days=calendar[-1].weekday()), freq="W-MON")),
        "gross_dollars": frame.trade_profit.sum(), "net_dollars": frame.net_dollars.sum(),
        "gross_mean_r": frame.gross_r.mean(), "net_mean_r": frame.net_r.mean(),
        "dollar_pf": positive / -negative if negative else math.nan,
        "risk_mean": frame.initial_risk_dollars.mean(),
        "risk_median": frame.initial_risk_dollars.median(),
        "commission_mean_r": frame.commission_r.mean(),
        "holding_minutes": frame.holding_minutes.sum(),
        "holding_minutes_total": frame.holding_minutes.sum(),
        "holding_minutes_mean": frame.holding_minutes.mean(),
        "mean_holding_minutes": frame.holding_minutes.mean(),
        "holding_hours": frame.holding_minutes.sum() / 60,
        "worst_day": min(daily), "worst_week": min(weekly.values()),
        "mean_worst5pct_sessions": statistics.fmean(sorted(daily)[:math.ceil(.05 * len(daily))]),
        "worst5pct_session_mean": statistics.fmean(sorted(daily)[:math.ceil(.05 * len(daily))]),
        "closed_trade_dd": closed_dd, "daily_close_dd": drawdown,
        "daily_dd_duration_days": duration,
    }
    for stress in (1, 2):
        result[f"stress{stress}_net_dollars"] = frame[f"stress{stress}_net_dollars"].sum()
        result[f"stress{stress}_net_mean_r"] = frame[f"stress{stress}_net_r"].mean()
        result[f"stress{stress}_mean_r"] = frame[f"stress{stress}_net_r"].mean()
    return result


def audit_metric_row(row, part, complement, calendar, label):
    expected = independent_metrics(part, calendar)
    expected["difference_net_r"] = part.net_r.mean() - complement.net_r.mean()
    expected["complement_trades"] = len(complement)
    expected["complement_net_mean_r"] = complement.net_r.mean()
    verified = []
    for key, value in expected.items():
        if key in row.index:
            expect_close(row[key], value, f"{label}: {key}", tolerance=2e-7)
            verified.append(key)
    essential = {"trades", "active_sessions", "active_weeks", "eligible_sessions",
                 "gross_mean_r", "net_mean_r", "net_dollars", "dollar_pf", "risk_mean",
                 "risk_median", "commission_mean_r", "worst_day", "worst_week",
                 "daily_close_dd", "daily_dd_duration_days", "closed_trade_dd",
                 "eligible_weeks", "worst5pct_session_mean", "holding_hours", "mean_holding_minutes",
                 "stress1_net_dollars", "stress1_mean_r", "stress2_net_dollars", "stress2_mean_r"}
    assert essential.issubset(verified), f"Missing mandatory metrics in {label}: {essential-set(verified)}"
    return verified


def bootstrap_audit(frame, calendar, saved, rng):
    """Rebuild each draw as week multiplicities rather than indexing trade arrays."""
    first = calendar[0] - pd.Timedelta(days=calendar[0].weekday())
    last = calendar[-1] - pd.Timedelta(days=calendar[-1].weekday())
    weeks = pd.date_range(first, last, freq="W-MON")
    starts = rng.integers(0, len(weeks), size=(10000, math.ceil(len(weeks) / 4)))
    offsets = np.arange(4)
    samples = ((starts[:, :, None] + offsets) % len(weeks)).reshape(10000, -1)[:, :len(weeks)]
    multiplicity = np.zeros((10000, len(weeks)), dtype=np.int32)
    np.add.at(multiplicity, (np.arange(10000)[:, None], samples), 1)
    total_count = frame.groupby("week_start").size().reindex(weeks, fill_value=0).to_numpy()
    total_r = frame.groupby("week_start").net_r.sum().reindex(weeks, fill_value=0).to_numpy()
    all_counts, all_sums = multiplicity @ total_count, multiplicity @ total_r
    invalid = {}
    for group in GROUPS + ("all",):
        part = frame if group == "all" else frame.loc[frame.group == group]
        counts = part.groupby("week_start").size().reindex(weeks, fill_value=0).to_numpy()
        sums = part.groupby("week_start").net_r.sum().reindex(weeks, fill_value=0).to_numpy()
        sampled_counts, sampled_sums = multiplicity @ counts, multiplicity @ sums
        means = np.divide(sampled_sums, sampled_counts, out=np.full(10000, np.nan), where=sampled_counts > 0)
        other_counts = all_counts - sampled_counts
        complement = np.divide(all_sums - sampled_sums, other_counts,
                               out=np.full(10000, np.nan), where=other_counts > 0)
        distributions = {"mean_net_r": means}
        if group != "all":
            distributions["difference_net_r"] = means - complement
        row = saved.loc[saved.group == group].iloc[0]
        invalid[group] = {}
        for metric, values in distributions.items():
            valid = values[np.isfinite(values)]
            invalid[group][metric] = {"invalid": int((~np.isfinite(values)).sum()),
                                      "degenerate": bool(len(valid) and np.ptp(valid) == 0)}
            for level, alpha in (("95", .05), ("99_1667", .05 / 6)):
                if len(valid):
                    low, high = np.quantile(valid, [alpha / 2, 1 - alpha / 2], method="linear")
                else:
                    low = high = math.nan
                for suffix, expected in (("low", low), ("high", high)):
                    column = f"{metric}_ci{level}_{suffix}"
                    assert column in row.index, f"Missing {column}"
                    expect_close(row[column], expected, f"{group}: bootstrap {column}", tolerance=1e-9)
    return invalid


def independently_screen(ledger, closes):
    result = {}
    for group in GROUPS:
        era_parts = [ledger.loc[(ledger.session >= start) & (ledger.session < end)]
                     for start, end in ERAS.values()]
        groups = [part.loc[part.group == group] for part in era_parts]
        coverage = all(len(part) >= 200 and part.week_start.nunique() >= 30 for part in groups)
        negative = all(part.net_dollars.sum() < 0 and part.net_r.mean() < 0 for part in groups)
        below = all(group_part.net_r.mean() < part.loc[part.group != group].net_r.mean()
                    for part, group_part in zip(era_parts, groups))
        annual = []
        for year in range(2016, 2026):
            part = ledger.loc[(ledger.year == year) & (ledger.group == group)]
            annual.append({"year": year, "trades": len(part), "net_dollars": part.net_dollars.sum()})
        eligible = [row for row in annual if row["trades"] >= 30]
        negative_years = sum(row["net_dollars"] < 0 for row in eligible)
        sensitivities = True
        for label in ("group_p70", "group_p80", "group_roll_robust"):
            for era in era_parts:
                part = era.loc[era[label] == group]
                sensitivities &= (len(part) >= 200 and part.week_start.nunique() >= 30
                                  and part.net_dollars.sum() < 0 and part.net_r.mean() < 0)
        checks = {"coverage": bool(coverage), "negative_both_eras": bool(negative),
                  "below_complement_both_eras": bool(below),
                  "annual_negative_share": bool(full_year_negative_gate(annual)),
                  "sensitivities": bool(sensitivities)}
        result[group] = {"checks": checks, "qualifies": all(checks.values()),
                         "full_year_count": len(eligible),
                         "negative_full_year_count": negative_years,
                         "negative_full_year_fraction": negative_years / len(eligible) if eligible else None}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, default=STUDY)
    parser.add_argument("--skip-bootstrap", action="store_true",
                        help="Fast development check; result is explicitly incomplete.")
    args = parser.parse_args()
    assert sha256(PROTOCOL) == PROTOCOL_SHA256, "Frozen protocol content changed"
    output = args.study
    print("Reading original minute file and independent HTML orders/deals...", flush=True)
    closes = minute_closes()
    rolls = pd.read_csv(ROLLS)
    assert rolls.date.is_unique and (rolls.instrument_id.iloc[1:].to_numpy() != rolls.instrument_id.iloc[:-1].to_numpy()).all()
    switches = pd.to_datetime(rolls.date.iloc[1:])
    expected = reference_labels(closes, switches)
    daily_reference = pd.read_csv(ROOT / "Reports/trend_rr_20261002/daily_reference.csv", parse_dates=["date"])
    daily_reference = daily_reference.set_index("date")
    assert closes.index.equals(daily_reference.index), "Original minute/daily-reference dates"
    expect_close(closes, daily_reference.close, "Original minute/daily-reference closes", tolerance=0)
    m30 = pd.read_csv(ROOT / "Reports/trend_rr_20261002/m30_reference.csv", parse_dates=["bar_time"])
    m30_closes = m30.groupby(m30.bar_time.dt.normalize()).close.last()
    assert closes.index.equals(m30_closes.index), "Original minute/M30 dates"
    expect_close(closes, m30_closes, "Original minute/M30 closes", tolerance=0)
    features = pd.read_csv(output / "daily_features.csv", parse_dates=["date", "previous_date"]).set_index("date")
    assert features.index.equals(expected.index), "Feature date coverage"
    numeric_columns = list(expected.select_dtypes(include="number").columns)
    for column in numeric_columns:
        expect_close(features[column], expected[column], f"Feature {column}", tolerance=1e-9)
    for column in ("trend", "group", "group_p70", "group_p80", "group_roll_robust", "roll_date"):
        assert features[column].equals(expected[column]), f"Independent feature {column}"
    assert features.previous_date.equals(expected.previous_date), "Feature prior dates"
    ready = expected.group != "warmup"
    assert (expected.previous_date.loc[ready] < expected.index[ready]).all()
    causal_result = check_future_invariance(closes, switches)
    report = report_trades(BASE / f"{TAG}.htm")
    raw = pd.read_csv(RAW, sep="\t", encoding="utf-16")
    ledger = checked_ledger(raw, report)
    assert len(ledger) == 25833 and ledger.trade_profit.sum() == 62579., "Saved full-run baseline"
    completion = json.loads((BASE / f"{TAG}.completed.json").read_text())
    assert sha256(RAW) == completion["outputs"][RAW.name], "Saved run completion ledger hash"
    for label in ("group", "group_p70", "group_p80", "group_roll_robust"):
        ledger[label] = ledger.session.map(expected[label])
        assert ledger[label].notna().all(), "Missing session labels"
        assert ledger.loc[ledger.primary, label].isin(GROUPS).all(), "Primary warmup/unlabelled trades"
    saved = pd.read_csv(output / "trades.csv")
    assert saved.ticket.is_unique and set(saved.ticket) == set(ledger.ticket), "Saved trade coverage"
    saved = saved.set_index("ticket").sort_index()
    ledger = ledger.set_index("ticket", drop=False).sort_index()
    for column in ("submitted", "entry_time", "exit_time", "session", "week_start"):
        assert (pd.to_datetime(saved[column]) == ledger[column]).all(), f"Trade {column}"
    columns = ("requested_price", "original_sl", "fill_price", "initial_risk_dollars", "fill_risk_dollars",
               "trade_profit", "net_dollars", "gross_r", "net_r", "commission_r", "holding_minutes",
               "stress1_net_dollars", "stress2_net_dollars", "stress1_net_r", "stress2_net_r", "year")
    for column in columns:
        expect_close(saved[column], ledger[column], f"Trade {column}")
    for column in ("primary", "group", "group_p70", "group_p80", "group_roll_robust"):
        assert saved[column].equals(ledger[column]), f"Trade {column}"
    ledger = ledger.reset_index(drop=True)
    incomplete = ledger.loc[ledger.session >= "2026-10-01"]
    assert len(incomplete) == 1 and incomplete.exit_comment.str.contains("end of test").all(), "Partial endpoint"
    assert incomplete.session.eq(pd.Timestamp("2026-10-01")).all()
    assert (~incomplete.primary).all()
    summary = pd.read_csv(output / "summaries.csv")
    assert len(summary) == 14 and not summary.duplicated(["era", "group"]).any()
    yearly = pd.read_csv(output / "yearly.csv")
    assert len(yearly) == 77 and not yearly.duplicated(["year", "group"]).any()
    sensitivity = pd.read_csv(output / "sensitivities.csv")
    assert not sensitivity.duplicated(["sensitivity", "era", "group"]).any()
    rng = np.random.default_rng(20261023)
    intervals, baseline, metric_names = {}, {}, set()
    print("Verifying 2 eras, 6 groups, annual/sensitivity metrics and paired block intervals...", flush=True)
    for era, (start, end) in ERAS.items():
        frame = ledger.loc[(ledger.session >= start) & (ledger.session < end)]
        calendar = closes.index[(closes.index >= start) & (closes.index < end)]
        rows = summary.loc[summary.era == era]
        assert set(rows.group) == set(GROUPS + ("all",)), f"{era} summary groups"
        baseline[era] = {"trades": len(frame), "gross_dollars": float(frame.trade_profit.sum()),
                         "net_dollars": float(frame.net_dollars.sum())}
        assert rows.loc[rows.group != "all", "trades"].sum() == len(frame)
        for group in GROUPS + ("all",):
            part = frame if group == "all" else frame.loc[frame.group == group]
            complement = frame.loc[~frame.ticket.isin(part.ticket)]
            row = rows.loc[rows.group == group].iloc[0]
            metric_names.update(audit_metric_row(row, part, complement, calendar, f"{era}/{group}"))
        if not args.skip_bootstrap:
            intervals[era] = bootstrap_audit(frame, calendar, rows, rng)
        for variant, label in (("p70", "group_p70"), ("p80", "group_p80"), ("roll_robust", "group_roll_robust")):
            variant_rows = sensitivity.loc[(sensitivity.era == era) & (sensitivity.sensitivity == variant)]
            assert set(GROUPS).issubset(variant_rows.group), f"{era}/{variant} groups"
            for group in variant_rows.group:
                assert group in GROUPS + ("all",)
                part = frame if group == "all" else frame.loc[frame[label] == group]
                complement = frame.loc[~frame.ticket.isin(part.ticket)]
                row = variant_rows.loc[variant_rows.group == group].iloc[0]
                metric_names.update(audit_metric_row(row, part, complement, calendar, f"{era}/{variant}/{group}"))
    for year in range(2016, 2027):
        start, end = pd.Timestamp(year, 1, 1), min(pd.Timestamp(year+1, 1, 1), pd.Timestamp("2026-10-01"))
        frame = ledger.loc[(ledger.session >= start) & (ledger.session < end)]
        calendar = closes.index[(closes.index >= start) & (closes.index < end)]
        rows = yearly.loc[yearly.year == year]
        assert set(rows.group) == set(GROUPS + ("all",)), f"{year} yearly groups"
        for group in GROUPS + ("all",):
            part = frame if group == "all" else frame.loc[frame.group == group]
            complement = frame.loc[~frame.ticket.isin(part.ticket)]
            row = rows.loc[rows.group == group].iloc[0]
            metric_names.update(audit_metric_row(row, part, complement, calendar, f"{year}/{group}"))
    candidate = json.loads((output / "candidate_gates.json").read_text())
    independent = independently_screen(ledger, closes)
    assert len(candidate["groups"]) == 6
    for item in candidate["groups"]:
        reference = independent[item["group"]]
        for key in ("checks", "qualifies", "full_year_count", "negative_full_year_count"):
            assert item[key] == reference[key], f"Candidate {item['group']}: {key}"
        expect_close(item["negative_full_year_fraction"], reference["negative_full_year_fraction"],
                     f"Candidate {item['group']}: annual negative fraction")
    qualified = [group for group in GROUPS if independent[group]["qualifies"]]
    assert set(candidate["qualified_groups"]) == set(qualified)
    selection = None
    if qualified:
        earlier = ledger.loc[(ledger.session >= "2016-01-01") & (ledger.session < "2020-01-01")]
        selection = min(qualified, key=lambda group: (earlier.loc[earlier.group == group, "net_r"].mean(), group))
    assert candidate["selected_candidate"] == selection
    assert candidate["conditional_steps_triggered"] == bool(qualified)
    standalone = {}
    for tag, path, start, end in (
        ("train_cap0", ROOT / "Reports/maxredrun_clean_20261001/runband_mrr_clean_20261001_train_cap0_1.00.csv", "2016-01-01", "2020-01-01"),
        ("extended_cap0", ROOT / "Reports/maxredrun_extended_20261013/runband_mrrext_20261013_cap0_1.00.csv", "2020-01-01", "2026-10-02"),
    ):
        independent_run = pd.read_csv(path, sep="\t", encoding="utf-16")
        for column in ("entry_time", "exit_time"):
            independent_run[column] = pd.to_datetime(independent_run[column], format="%Y.%m.%d %H:%M:%S")
        comparable = ledger.loc[(ledger.session >= start) & (ledger.session < end)]
        comparable = comparable.sort_values(["entry_time", "exit_time"]).reset_index(drop=True)
        independent_run = independent_run.sort_values(["entry_time", "exit_time"]).reset_index(drop=True)
        assert len(comparable) == len(independent_run), f"{tag} exact slice count"
        for column in ("entry_time", "exit_time"):
            assert comparable[column].equals(independent_run[column]), f"{tag} exact {column}"
        for column in ("trade_profit", "candle_range", "red_run", "location", "mae_money", "mfe_money"):
            expect_close(comparable[column], independent_run[column], f"{tag} {column}", tolerance=1e-9)
        standalone[tag] = {"rows": len(independent_run), "gross_dollars": float(independent_run.trade_profit.sum()),
                           "sha256": sha256(path), "all_trade_timestamps_profit_risk_and_context_match": True}
    provenance = json.loads((output / "provenance.json").read_text())
    for filename, digest in provenance["inputs_sha256"].items():
        assert sha256(filename) == digest, f"Input provenance {filename}"
    for filename, digest in provenance["outputs_sha256"].items():
        assert sha256(output / filename) == digest, f"Output provenance {filename}"
    artifacts = ["summaries.csv", "daily_features.csv", "trades.csv", "yearly.csv",
                 "sensitivities.csv", "candidate_gates.json", "audit.json", "provenance.json"]
    result = {
        "status": "PARTIAL_SKIP_BOOTSTRAP" if args.skip_bootstrap else "PASS",
        "protocol_sha256": sha256(PROTOCOL),
        "verification_program_sha256": sha256(Path(__file__)),
        "original_minute_sha256": sha256(MINUTES),
        "original_rolls_sha256": sha256(ROLLS),
        "original_raw_ledger_sha256": sha256(RAW),
        "original_html_sha256": sha256(BASE / f"{TAG}.htm"),
        "artifact_sha256": {filename: sha256(output / filename) for filename in artifacts},
        "source_sessions": len(closes), "full_ledger_trades": len(ledger),
        "standalone_baseline_reconciliations": standalone,
        "provenance_input_and_output_hashes": "PASS",
        "primary_trades": int(ledger.primary.sum()), "eras": baseline,
        "partial_endpoint_trades": len(incomplete),
        "partial_endpoint_gross_dollars": float(incomplete.trade_profit.sum()),
        "features_independently_recomputed": list(expected.columns),
        "daily_close_sources_reconciled": ["original minutes", "saved M30 reference", "saved daily reference"],
        "timing_risk_and_join_checks": "PASS", "future_perturbation": causal_result,
        "summary_metrics_independently_recomputed": sorted(metric_names),
        "bootstrap": intervals,
        "independent_candidate_gates": independent,
        "qualified_groups": qualified, "selected_candidate": selection,
    }
    (output / "independent_verification.json").write_text(json.dumps(result, indent=2, allow_nan=False, default=json_scalar) + "\n",
                                                         encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "full_ledger_trades", "primary_trades",
                                                  "eras", "qualified_groups")}, indent=2))


if __name__ == "__main__":
    main()

