"""Q1/Q2 diagnostics under the frozen protocol in docs/baseline/q01-q02-preceding-candles/PROTOCOL.md.

Run from the project root:
  python python/analyze_preceding_candles.py Reports/preceding_candles_20260930
No filter optimization or simulated full-strategy filtering is performed.
"""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from analyze_features import load
from project_paths import PROJECT_ROOT
from verify_location_validation import read_rows

LOOKBACKS = (5, 10, 20, 50)


def features(d, n):
    """Column 0 = signal; the preceding window is columns 1..n inclusive."""
    if n < 2 or d["C"].shape[1] < n + 1:
        raise ValueError(f"Need signal plus {n} preceding bars")
    close = d["C"][:, 1:n + 1]
    red_share = np.mean(close < d["O"][:, 1:n + 1], axis=1)
    # Newer closes are on the left: lower newer close = chronological decline.
    down_share = np.mean(close[:, :-1] < close[:, 1:], axis=1)
    interrupted = (red_share >= 0.6) & (down_share >= 0.6)
    prior_low = np.min(d["L"][:, 1:n + 1], axis=1)
    breach = d["L"][:, 0] < prior_low
    # 0=no breach, 1=breach without recovery, 2=breach with recovery.
    recovery = np.where(breach, np.where(d["C"][:, 0] > prior_low, 2, 1), 0)
    valid = np.logical_and.reduce([
        np.isfinite(d[key][:, :n + 1]).all(axis=1) for key in "OHLC"
    ])
    return red_share, down_share, interrupted, recovery, valid


def verify_export(path, reference_path):
    rows = read_rows(path)
    reference = read_rows(reference_path)
    stats = read_rows(path.with_name(path.stem + "_stats.csv"))[0]
    if int(stats["snapshot_bars"]) != 51 or int(stats["max_red_run"]) != 3 or float(stats["min_location"]) != 0:
        raise AssertionError("Unexpected study inputs")
    assert len(rows) == len(reference) == int(stats["trades"]), "Trade count differs"
    for actual, expected in zip(rows, reference, strict=True):
        for key in expected:
            if key in ("entry_time", "exit_time"):
                assert actual[key] == expected[key], (key, "logging changed a trade")
            else:
                assert abs(float(actual[key]) - float(expected[key])) <= 1e-8, (key, "logging changed a trade")
    gross = sum(float(row["trade_profit"]) for row in rows)
    assert abs(gross - float(stats["net_profit"])) < 1e-6, "MT5 PnL mismatch"
    return len(rows)


def pf(values):
    loss = -values[values < 0].sum()
    return float(values[values > 0].sum() / loss) if loss else None


def metrics(gross, risk, mask, commission):
    values, risks = gross[mask], risk[mask]
    net = values - commission
    return dict(n=int(mask.sum()), gross=float(values.sum()), gross_pf=pf(values),
                gross_avg_r=float(np.mean(values / risks)) if len(values) else None,
                net=float(net.sum()), net_pf=pf(net),
                net_avg_r=float(np.mean(net / risks)) if len(values) else None)


def block_difference(r, entry, a, b, rng, resamples=2000):
    """Resample common calendar months, including empty months/group cells."""
    month = entry.astype("datetime64[M]").astype(int)
    ids = month - month.min()
    count = int(ids.max()) + 1
    ca = np.bincount(ids, weights=a, minlength=count)
    cb = np.bincount(ids, weights=b, minlength=count)
    sa = np.bincount(ids, weights=np.where(a, r, 0), minlength=count)
    sb = np.bincount(ids, weights=np.where(b, r, 0), minlength=count)
    if not a.any() or not b.any():
        return dict(difference_r=None, lower_r=None, upper_r=None, bootstrap_valid=0)
    sampled = rng.integers(0, count, size=(resamples, count))
    na, nb = ca[sampled].sum(axis=1), cb[sampled].sum(axis=1)
    keep = (na > 0) & (nb > 0)
    delta = sa[sampled].sum(axis=1)[keep] / na[keep] - sb[sampled].sum(axis=1)[keep] / nb[keep]
    lo, hi = np.quantile(delta, [0.025, 0.975]) if len(delta) else (None, None)
    return dict(difference_r=float(r[a].mean() - r[b].mean()),
                lower_r=float(lo) if lo is not None else None,
                upper_r=float(hi) if hi is not None else None,
                bootstrap_valid=int(keep.sum()))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value, digits=3):
    return "n/a" if value is None else f"{value:.{digits}f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--reference", type=Path, default=PROJECT_ROOT / "Reports/maxredrun_train_20260929")
    parser.add_argument("--commission", type=float, default=1.0)
    args = parser.parse_args()
    summaries, contrasts, baselines = [], [], []
    rng = np.random.default_rng(20260930)
    for phase, reference in (("train", "train1519_run3"), ("recent", "test2026_run3")):
        path = args.directory / f"runband_bars_20260930_{phase}_1.00.csv"
        count = verify_export(path, args.reference / f"runband_{reference}_1.00.csv")
        d = load(path)
        assert len(d["profit"]) == count, "Loader skipped rows"
        # Common complete-history population across every N.
        valid = np.logical_and.reduce([np.isfinite(d[key][:, :51]).all(axis=1) for key in "OHLC"])
        assert (d["crange"] > 0).all(), "Nonpositive risk"
        assert np.allclose(d["H"][:, 0] - d["L"][:, 0], d["crange"], atol=1e-8), "Snapshot/signal range mismatch"
        assert (d["C"][:, 0] < d["O"][:, 0]).all(), "Non-red signal"
        assert (d["entry"] >= d["signal"] + d["period"].astype("timedelta64[s]")).all(), "Snapshot contains future bars"
        assert (np.cumprod(d["C"] < d["O"], axis=1).sum(axis=1) <= 3).all(), "Snapshot/red-run mismatch"
        print(f"PASS {phase}: {count:,} trades identical to reference; {int(valid.sum()):,} complete snapshots.")
        gross, risk = d["profit"], d["crange"] * 2.0
        year = d["entry"].astype("datetime64[Y]").astype(int) + 1970
        blocks = {phase: valid}
        for y in sorted(set(year)):
            blocks[str(y)] = valid & (year == y)
        if phase == "train":
            blocks.update({"2015-2017": valid & (year <= 2017), "2018-2019": valid & (year >= 2018)})
        else:
            blocks.update({"2020-2022": valid & (year <= 2022), "2023-2026": valid & (year >= 2023)})
        baselines.append(dict(phase=phase, missing=int((~valid).sum()), **metrics(gross, risk, valid, args.commission)))
        for n in LOOKBACKS:
            red, down, interrupted, recovery, feature_valid = features(d, n)
            assert (feature_valid[valid]).all()
            groups = {"interrupted": {"flagged": interrupted, "other": ~interrupted},
                      "recovery": {"no_breach": recovery == 0, "breach_no_recovery": recovery == 1,
                                   "breach_recovered": recovery == 2}}
            for name, share in (("red_share", red), ("down_share", down)):
                groups[name] = {"below_0.4": share < .4, "0.4_to_below_0.6": (share >= .4) & (share < .6), "at_least_0.6": share >= .6}
            for name, categories in groups.items():
                for category, mask in categories.items():
                    for block, population in blocks.items():
                        summaries.append(dict(phase=phase, period=block, feature=name, lookback=n,
                                              category=category, **metrics(gross, risk, mask & population, args.commission)))
            for question, a, b in (("interrupted", interrupted, ~interrupted),
                                    ("recovery", recovery == 2, recovery == 1)):
                a, b = a & valid, b & valid
                contrasts.append(dict(phase=phase, question=question, lookback=n,
                                      n_a=int(a.sum()), n_b=int(b.sum()),
                                      **block_difference(gross / risk, d["entry"], a, b, rng)))

    write_csv(args.directory / "buckets.csv", summaries)
    write_csv(args.directory / "contrasts.csv", contrasts)
    payload = dict(baselines=baselines, contrasts=contrasts, buckets=summaries)
    (args.directory / "diagnostics.json").write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    lines = ["# Preceding-candle diagnostics: Q1 / Q2", "", "Generated from actual cap-3 MT5 snapshot runs.",
             "Exploratory, previously examined history; no new strategy filter was applied.",
             "Net assumes $1/trade; R uses signal range times $2/point.", "",
             "## Q1: interrupted-decline proxy", "",
             "Flag = both preceding red share and downward-close share >= 0.6.", "",
             "| Period | N | Flagged n | Flagged gross PF | Other gross PF | Flagged net PF | Other net PF |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for feature in ("interrupted", "recovery"):
        if feature == "recovery":
            lines += ["", "## Q2: recovery after a low breach", "",
                      "| Period | N | Recovered n | Unrecovered n | Recovered gross PF | Unrecovered gross PF | Recovered net PF | Unrecovered net PF |",
                      "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for phase in ("train", "recent"):
            for n in LOOKBACKS:
                rows = {r["category"]: r for r in summaries if r["phase"] == phase and r["period"] == phase and r["feature"] == feature and r["lookback"] == n}
                a, b = (rows["flagged"], rows["other"]) if feature == "interrupted" else (rows["breach_recovered"], rows["breach_no_recovery"])
                counts = f"{a['n']}" if feature == "interrupted" else f"{a['n']} | {b['n']}"
                lines.append(f"| {phase} | {n} | {counts} | {fmt(a['gross_pf'])} | {fmt(b['gross_pf'])} | {fmt(a['net_pf'])} | {fmt(b['net_pf'])} |")
    lines += ["", "## Gross average-R differences", "",
              "Q1 = flagged minus other (hypothesis: negative). Q2 = recovered minus unrecovered (hypothesis: positive).",
              "Common-month block bootstrap, 2,000 resamples. Unadjusted descriptive 95% intervals; no multiple-testing claim.", "",
              "| Period | Question | N | Difference R | Lower | Upper |",
              "|---|---|---:|---:|---:|---:|"]
    for r in contrasts:
        lines.append(f"| {r['phase']} | {r['question']} | {r['lookback']} | {fmt(r['difference_r'])} | {fmt(r['lower_r'])} | {fmt(r['upper_r'])} |")
    lines += ["", "All bins, years, fixed chronological subdivisions, and no-breach controls are retained in `buckets.csv`.",
              "No subset drawdown is presented as a full-strategy result. Groups with few trades have wide or unstable estimates."]
    (args.directory / "DIAGNOSTICS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
