"""Outcome-free M30 diagnostics for the fixed-grid NQ granularity experiment.

Quantization and OHLC aggregation commute because the quantizer is monotonic.
The source M1 bars are therefore aggregated once, then each grid is applied to
M30 prices. Static signal eligibility ignores open positions and pending
order state: it counts opportunities, never actual submissions or fills.
The red run carries across dates, as in the research EA.

Usage: python analyze_granularity_candles.py [Reports/granularity_20261009]
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT

SOURCE = Path(r"F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv")
DEFAULT_RUN = ROOT / "Reports" / "granularity_20261009"
START = "2010-06-07"
END_EXCLUSIVE = "2026-07-14"
PRICE_COLUMNS = ("<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>")
PERIODS = (("2010-15", 2010, 2015), ("2016-19", 2016, 2019),
           ("2020-26", 2020, 2026), ("all", 2010, 2026))
AGG = {"open": "first", "high": "max", "low": "min", "close": "last"}
WARNING = ("Static eligibility ignores the flat-position condition and pending-order state; "
           "pending buy-stops can persist across non-signal bars. Static counts are not actual fills.")


def _calendar(path):
    """Read exactly the two arrays used by the EA's early-close cutoff."""
    source = Path(path).read_text(encoding="utf-8")
    values = []
    for name in ("EC_DATE", "EC_FLAT_MIN"):
        match = re.search(r"\b" + name + r"\s*\[[^]]*\]\s*=\s*\{([^}]*)\}", source)
        if match is None:
            raise ValueError(f"Missing {name} array in {path}")
        values.append([int(x) for x in re.findall(r"\d+", match.group(1))])
    dates, minutes = values
    if len(dates) != len(minutes) or len(dates) != len(set(dates)):
        raise ValueError("Early-close arrays have unequal lengths or duplicate dates")
    if any(not 0 <= m <= 23 * 60 + 30 for m in minutes):
        raise ValueError("Early-close cutoff outside the normal session")
    return dict(zip(dates, minutes))


def _source_m30(path, start, end_exclusive, chunksize=250_000):
    """Validate selected M1 rows and aggregate without holding the whole CSV."""
    start, end_exclusive = pd.Timestamp(start), pd.Timestamp(end_exclusive)
    if end_exclusive <= start:
        raise ValueError("Study end must follow its start")
    parts, year_counts, days = [], {}, set()
    year_spans, year_price_sums = {}, {}
    last_time, source_rows = None, 0
    usecols = ["<DATE>", "<TIME>", *PRICE_COLUMNS]
    for chunk in pd.read_csv(path, sep="\t", usecols=usecols, chunksize=chunksize):
        t = pd.DatetimeIndex(pd.to_datetime(chunk["<DATE>"] + " " + chunk["<TIME>"],
                                          format="%Y.%m.%d %H:%M:%S"))
        if not t.is_monotonic_increasing or t.has_duplicates:
            raise ValueError("Source M1 timestamps are unordered or duplicated")
        if last_time is not None and len(t) and t[0] <= last_time:
            raise ValueError("Source M1 timestamps repeat or reverse across chunks")
        if len(t):
            last_time = t[-1]
        if not ((t.second == 0) & (t.microsecond == 0)).all():
            raise ValueError("Source timestamps are not minute-aligned")
        keep = (t >= start) & (t < end_exclusive)
        if not keep.any():
            continue
        t = t[keep]
        prices = chunk.loc[keep, list(PRICE_COLUMNS)].to_numpy(dtype=np.float64)
        if not np.isfinite(prices).all() or not (prices > 0).all():
            raise ValueError("Source has nonfinite or nonpositive study-window prices")
        units = np.rint(prices * 4)
        if not np.allclose(prices * 4, units, rtol=0, atol=1e-8):
            raise ValueError("Source study-window prices do not lie on the 0.25 lattice")
        units = units.astype(np.int64)
        o, h, l, c = units.T
        if not ((h >= np.maximum(o, c)) & (l <= np.minimum(o, c))).all():
            raise ValueError("Source study-window OHLC ordering is invalid")
        bars = pd.DataFrame(units, index=t.floor("30min"), columns=list(AGG))
        parts.append(bars.groupby(level=0, sort=True).agg(AGG))
        source_rows += len(t)
        years, counts = np.unique(t.year, return_counts=True)
        for year, count in zip(years, counts):
            year_counts[str(year)] = year_counts.get(str(year), 0) + int(count)
            subset = np.asarray(t.year == year)
            year_times = t[subset]
            label = str(year)
            if label not in year_spans:
                year_spans[label] = {"first": year_times[0].strftime("%Y.%m.%d %H:%M:%S")}
            year_spans[label]["last"] = year_times[-1].strftime("%Y.%m.%d %H:%M:%S")
            sums = units[subset].sum(axis=0, dtype=np.int64)
            if label not in year_price_sums:
                year_price_sums[label] = {name: 0 for name in AGG}
            for name, value in zip(AGG, sums):
                year_price_sums[label][name] += int(value)
        days.update(t.normalize().unique().strftime("%Y-%m-%d"))
    if not parts:
        raise ValueError("Source has no rows in the study window")
    # A chunk boundary may split an M30 bar; combine the partial OHLCs again.
    m30 = pd.concat(parts).groupby(level=0, sort=True).agg(AGG)
    metadata = dict(trading_days=sorted(days),
                    source_year_counts=dict(sorted(year_counts.items())), source_rows=source_rows,
                    source_year_spans=dict(sorted(year_spans.items())),
                    source_year_price_sums=dict(sorted(year_price_sums.items())))
    return m30, metadata


def _quantize(units, k, origin_ticks):
    """Nearest grid level, with exact half-grid ties rounded upward."""
    k, origin_ticks = int(k), int(origin_ticks)
    if k <= 0 or not 0 <= origin_ticks < k:
        raise ValueError("Grid k must be positive and origin_ticks must be in [0,k)")
    delta = units - origin_ticks
    return origin_ticks + k * np.floor_divide(2 * delta + k, 2 * k)


def _entry_window(times, calendar):
    dates = times.year * 10000 + times.month * 100 + times.day
    minutes = times.hour * 60 + times.minute
    cutoff = np.array([calendar.get(int(date), 23 * 60 + 30) for date in dates])
    return np.asarray((minutes >= 60) & (minutes < cutoff))


def _static_eligibility(prices, entry_window):
    """Signal is the preceding available M30 bar, even across sessions."""
    red = prices[:, 3] < prices[:, 0]
    ids = np.arange(len(red), dtype=np.int64)
    last_nonred = np.maximum.accumulate(np.where(~red, ids, -1))
    red_run = np.where(red, ids - last_nonred, 0)
    signal = red & (red_run >= 1) & (red_run <= 3) & (prices[:, 1] > prices[:, 2])
    eligible = np.zeros(len(red), dtype=bool)
    eligible[1:] = signal[:-1] & entry_window[1:]
    return eligible


def _row(variant, period, group_type, year, select, prices, entry_window, eligible, native):
    o, h, l, c = prices[select].T
    ranges = h - l
    k = int(variant["k"])
    return dict(key=variant["key"], k=k, grid_points=k / 4,
                origin_ticks=int(variant["origin_ticks"]),
                origin_points=int(variant["origin_ticks"]) / 4,
                group_type=group_type, period=period, year=year,
                raw_m30_bars=int(select.sum()), raw_m30_red=int((c < o).sum()),
                raw_m30_green=int((c > o).sum()), raw_m30_doji=int((c == o).sum()),
                raw_m30_zero_range=int((ranges == 0).sum()),
                median_range_points=float(np.median(ranges) / 4),
                median_range_native_ticks=float(np.median(ranges)),
                median_range_grid_steps=float(np.median(ranges) / k),
                entry_window_bars=int((entry_window & select).sum()),
                static_red_cap3_eligible=int((eligible & select).sum()),
                static_red_cap3_lost_vs_native=int((native & ~eligible & select).sum()),
                static_red_cap3_gained_vs_native=int((eligible & ~native & select).sum()))


def analyze(run_dir=DEFAULT_RUN):
    """Write candle_diagnostics.csv and return source-day/row metadata."""
    run = Path(run_dir)
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    variants = manifest["variants"]
    if not variants:
        raise ValueError("Manifest contains no variants")
    keys = [v["key"] for v in variants]
    if len(keys) != len(set(keys)):
        raise ValueError("Variant keys must be unique")
    source = Path(manifest.get("source_file", manifest.get("source_csv", SOURCE)))
    start = manifest.get("start", START)
    end_exclusive = manifest.get("end_exclusive", END_EXCLUSIVE)
    m30, metadata = _source_m30(source, start, end_exclusive)
    # Prefer the frozen calendar copied beside the EA, otherwise baseline.
    calendar_path = run / "early_closes.mqh"
    if not calendar_path.exists():
        calendar_path = ROOT / "mt5" / "experts" / "early_closes.mqh"
    calendar = _calendar(calendar_path)
    entry_window = _entry_window(m30.index, calendar)
    native_prices = m30.to_numpy(dtype=np.int64)
    native_eligible = _static_eligibility(native_prices, entry_window)
    years = np.asarray(m30.index.year)
    rows = []
    for variant in variants:
        k, origin_ticks = int(variant["k"]), int(variant["origin_ticks"])
        prices = _quantize(native_prices, k, origin_ticks)
        if not np.all((prices - origin_ticks) % k == 0):
            raise AssertionError("Quantized prices do not lie on their grid")
        if not np.all(2 * np.abs(prices - native_prices) <= k):
            raise AssertionError("Quantization displacement exceeds half a grid")
        o, h, l, c = prices.T
        if not np.all((h >= np.maximum(o, c)) & (l <= np.minimum(o, c))):
            raise AssertionError("Quantization broke OHLC ordering")
        if k == 1 and origin_ticks == 0 and not np.array_equal(prices, native_prices):
            raise AssertionError("Native-grid identity check failed")
        if np.any(((native_prices[:, 3] < native_prices[:, 0]) & (c > o)) |
                  ((native_prices[:, 3] > native_prices[:, 0]) & (c < o))):
            raise AssertionError("Monotonic quantization reversed a candle's colour")
        eligible = _static_eligibility(prices, entry_window)
        for period, lo, hi in PERIODS:
            select = (years >= lo) & (years <= hi)
            if select.any():
                rows.append(_row(variant, period, "period", "", select, prices,
                                 entry_window, eligible, native_eligible))
        for year in sorted(np.unique(years)):
            rows.append(_row(variant, str(year), "year", int(year), years == year,
                             prices, entry_window, eligible, native_eligible))
    output = pd.DataFrame(rows)
    run.mkdir(parents=True, exist_ok=True)
    output.to_csv(run / "candle_diagnostics.csv", index=False, float_format="%.6f")
    (run / "source_calendar.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: validated {metadata['source_rows']:,} M1 rows, {len(m30):,} M30 bars; "
          f"wrote {len(output)} diagnostic rows for {len(variants)} variants.")
    print("WARNING: " + WARNING)
    print("Raw candle counts/medians use candle dates; eligibility uses the next available bar's entry date.")
    return metadata


if __name__ == "__main__":
    result = analyze(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RUN)
    print(json.dumps({"source_rows": result["source_rows"],
                      "source_year_counts": result["source_year_counts"],
                      "trading_days": len(result["trading_days"])}, indent=2))
