"""Analyze the flatten-fallback rerun (Reports/flatten_fallback_20261001).

Checks: every CSV reconciles with its MT5 stats; each run's flatten_fallback
matches its job; the fallback-OFF RR1 control reproduces the earlier cap-3 run
field by field. Then compares old (fallback off) vs fixed (fallback on) runs.
Net = gross - $1 per trade; R = net / (signal range x $2); DD = net closed balance.

Usage: python analyze_flatten_study.py [study_dir]
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

from project_paths import PROJECT_ROOT
from verify_location_validation import read_rows

REPORTS = PROJECT_ROOT / "Reports"
STUDY = REPORTS / "flatten_fallback_20261001"
# Earlier fallback-OFF runs with identical settings, for the before/after comparison.
OLD = {
    ("recent", rr): REPORTS / "rr_cap3_corrected_20260930" / f"runband_rr_cap3_corrected_20260930_{rr:.2f}.csv"
    for rr in (1.0, 1.1, 2.0, 2.5)
}
OLD[("train", 1.0)] = REPORTS / "exit_thresholds_20260930" / "runband_exit_20260930_train_close_1p00_1.00.csv"
OLD[("train", 2.0)] = REPORTS / "exit_thresholds_20260930" / "runband_exit_20260930_train_close_2p00_2.00.csv"
COMPARE_FIELDS = ("entry_time", "exit_time", "mae_money", "mfe_money", "trade_profit", "candle_range", "red_run")


def ts(s):
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")


def pf(x):
    loss = -x[x < 0].sum()
    return x[x > 0].sum() / loss if loss else float("nan")


def dd(x):
    eq = np.cumsum(x)
    return float(np.max(np.maximum.accumulate(np.r_[0, eq])[1:] - eq))


def summarize(rows):
    net = np.array([float(r["trade_profit"]) - 1.0 for r in rows])
    risk = np.array([float(r["candle_range"]) for r in rows]) * 2.0
    hold_h = np.array([(ts(r["exit_time"]) - ts(r["entry_time"])).total_seconds() / 3600 for r in rows])
    cross = np.array([r["entry_time"][:10] != r["exit_time"][:10] for r in rows])
    return dict(trades=len(rows), net=float(net.sum()), net_pf=pf(net), net_dd=dd(net),
                avg_r=float(np.mean(net / risk)), cross=int(cross.sum()),
                cross_net=float(net[cross].sum()), same_day_net=float(net[~cross].sum()),
                max_hold_h=float(hold_h.max()), holds_over_24h=int((hold_h > 24).sum()))


def main(study):
    manifest = json.loads((study / "manifest.json").read_text(encoding="utf-8"))
    results = {}
    for job in manifest["jobs"]:
        rows = read_rows(study / job["csv"])
        stats = read_rows(study / job["csv"].replace(".csv", "_stats.csv"))[0]
        assert len(rows) == int(stats["trades"]), (job["tag"], "trade count")
        gross = sum(float(r["trade_profit"]) for r in rows)
        assert abs(gross - float(stats["net_profit"])) < 1e-6, (job["tag"], "PnL")
        assert int(stats["flatten_fallback"]) == int(job["fallback"]), (job["tag"], "fallback flag")
        results[job["tag"]] = dict(job, **summarize(rows))
        if not job["fallback"]:
            old = read_rows(OLD[(job["period"], job["rr"])])
            assert len(old) == len(rows), (job["tag"], "control trade count differs from old run")
            for a, b in zip(old, rows):
                assert all(a[k] == b[k] for k in COMPARE_FIELDS), (job["tag"], a["entry_time"], "differs")
            print(f"PASS: fallback-OFF control reproduces all {len(rows):,} trades of the earlier run field by field.")
    print(f"PASS: {len(results)} runs reconcile with MT5 stats and carry the right fallback flag.\n")

    print(f"{'period':<7}{'RR':>5} {'':<6}{'trades':>7}{'net $':>10}{'net PF':>8}{'net DD':>8}{'avg R':>8}"
          f"{'x-date':>7}{'x-date $':>9}{'max hold h':>11}")
    for job in manifest["jobs"]:
        if not job["fallback"]:
            continue
        key = (job["period"], job["rr"])
        pairs = [("old", summarize(read_rows(OLD[key])))] if key in OLD else []
        pairs.append(("fixed", results[job["tag"]]))
        for label, s in pairs:
            print(f"{job['period']:<7}{job['rr']:>5.1f} {label:<6}{s['trades']:>7}{s['net']:>10.0f}{s['net_pf']:>8.3f}"
                  f"{s['net_dd']:>8.0f}{s['avg_r']:>+8.4f}{s['cross']:>7}{s['cross_net']:>9.0f}{s['max_hold_h']:>11.1f}")
    (study / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else STUDY)
