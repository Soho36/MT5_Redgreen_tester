"""Independent Q20 artifact, arithmetic and 1R exit audit; never rewrites saved runs.

Writes Reports/trendlines/trendline_limit_audit_20261005/audit.json.
Uses original MT5 ledgers/check logs, not the derived trades_*.csv files.
This supplements the saved order replay; it does not rerun the MT5 tester.
"""
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from verify_location_validation import read_rows
from analyze_price_levels import protocol_matches

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "Reports" / "trendlines" / "trendline_limit_runs_20261005"
OUT = RUN.parent / "trendline_limit_audit_20261005"
PERIODS = {"early": ("2010-06-07", "2016-01-01"),
           "train": ("2016-01-01", "2020-01-01"),
           "recent": ("2020-01-02", "2026-07-14")}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def frame(path):
    return pd.DataFrame(read_rows(path))


def audit():
    manifest = json.loads((RUN / "manifest.json").read_text())
    summary = json.loads((RUN / "summary.json").read_text())
    hashes = {
        "expert": digest(RUN / "RTL_trendline_limit.mq5") == manifest["expert_sha256"],
        "include": digest(RUN / "trendline_limit.mqh") == manifest["include_sha256"],
        "protocol": protocol_matches(ROOT / "docs" / "setups" / "trendlines" / "uptrend-bounce-long" / "q20-trendline-limit" / "PROTOCOL.md", manifest["protocol_sha256"]),
        "deltas": digest(RUN / manifest["deltas"]) == manifest["deltas_sha256"],
        "classify_bars": digest(RUN.parent / "trendline_limit_20261005" / "trendline_limit_20261005_classify_bars.csv") == manifest["classify_bars_sha256"],
    }
    for job in manifest["jobs"]:
        tag = job["tag"]
        done = json.loads((RUN / f"{tag}.completed.json").read_text())
        hashes.update({name: digest(RUN / name) == expected for name, expected in done["outputs"].items()})
    assert all(hashes.values()), {k: v for k, v in hashes.items() if not v}
    bars = pd.read_csv(ROOT / "Reports" / "levels" / "breach_reclaim_20261003" / "m30_reference.csv", index_col=0, parse_dates=[0])
    calendar = (RUN / "early_closes.mqh").read_text(encoding="utf-8-sig")
    dates = re.search(r"EC_DATE\[EC_COUNT\] = \{([^}]*)\}", calendar)[1].split(",")
    minutes = re.search(r"EC_FLAT_MIN\[EC_COUNT\] = \{([^}]*)\}", calendar)[1].split(",")
    cutoffs = dict(zip((x.strip() for x in dates), map(int, minutes)))
    results, runs = {}, {}
    for job in manifest["jobs"]:
        if job["inputs"]["LimitMode"] == 1:
            continue
        tag = job["tag"]
        name = tag.removeprefix("trendline_limit_runs_20261005_")
        led = frame(RUN / f"runband_{tag}_1.00.csv")
        fills = frame(RUN / f"{tag}_fills.csv")
        checks = frame(RUN / f"{tag}_checks.csv")
        ini = (RUN / f"{tag}.ini").read_text(encoding="utf-16")
        inputs = {x.split("=", 1)[0]: x.split("=", 1)[1].split("||")[0] for x in ini.split("[TesterInputs]")[1].split("[")[0].splitlines() if "=" in x}
        assert all(float(inputs[k]) == 1 for k in ("RiskReward", "BullRR", "BearRR"))
        for col in ("entry_time", "exit_time", "qualified_time"):
            led[col] = pd.to_datetime(led[col].replace("", np.nan), format="%Y.%m.%d %H:%M:%S")
        cutoff = led.entry_time.dt.normalize() + pd.to_timedelta(led.entry_time.dt.strftime("%Y%m%d").map(cutoffs).fillna(1410), unit="min")
        assert led.exit_time.le(cutoff).all(), (name, "exit after flatten")
        for col in ("trade_profit", "candle_range", "base_entry", "initial_stop", "assigned_rr", "exit_price", "base_volume", "broker_costs"):
            led[col] = pd.to_numeric(led[col])
        assert (led.assigned_rr == 1).all()
        assert (led.base_volume == 1).all() and (led.broker_costs == 0).all()
        assert np.allclose(led.trade_profit, (led.exit_price - led.base_entry) * 2, atol=1e-9)
        led["order_bar"] = pd.to_datetime(fills.order_bar, format="%Y.%m.%d %H:%M:%S")
        led["net"] = led.trade_profit - 1.05
        led["net_r"] = led.net / (2 * led.candle_range)
        runs[name] = led
        by_ticket = led.set_index("ticket")
        ref = by_ticket.reindex(checks.ticket)
        expected_target = ref.base_entry.to_numpy() + (ref.base_entry - ref.initial_stop).to_numpy()
        target = pd.to_numeric(checks.target).to_numpy()
        assert np.allclose(target, expected_target, atol=1e-8, rtol=0)
        assert (pd.to_numeric(checks.assigned_rr) == 1).all()
        ct = pd.to_datetime(checks.bar_time, format="%Y.%m.%d %H:%M:%S")
        assert np.allclose(pd.to_numeric(checks.bar_close), bars.close.reindex(ct), atol=1e-9, rtol=0)
        qualified = pd.to_numeric(checks.bar_close).to_numpy() >= target
        assert np.array_equal(pd.to_numeric(checks.qualified).to_numpy(), qualified.astype(int))
        q = checks[qualified].assign(time=pd.to_datetime(checks.loc[qualified, "check_time"], format="%Y.%m.%d %H:%M:%S")).groupby("ticket").time.min()
        expected_q = led.ticket.map(q)
        assert (expected_q.eq(led.qualified_time) | (expected_q.isna() & led.qualified_time.isna())).all()
        targets = led.qualified_time.notna()
        assert led.loc[targets, "exit_time"].eq(led.loc[targets, "qualified_time"]).all()
        stat = frame(RUN / f"runband_{tag}_1.00_stats.csv").iloc[0]
        assert len(led) == int(stat.trades)
        assert math.isclose(led.trade_profit.sum(), float(stat.net_profit), abs_tol=1e-6)
        metrics = {}
        for period, (lo, hi) in PERIODS.items():
            t = led[(led.order_bar >= lo) & (led.order_bar < hi)]
            net = t.net.to_numpy()
            eq = np.r_[0., np.cumsum(t.sort_values("exit_time").net)]
            values = dict(fills=len(t), net=float(net.sum()),
                          pf=float(net[net > 0].sum() / -net[net < 0].sum()),
                          avg_net_r=float(t.net_r.mean()), win_rate=float((net > 0).mean()),
                          closed_dd=float((np.maximum.accumulate(eq) - eq).max()))
            for key, value in values.items():
                assert math.isclose(value, summary["summary"][name][period][key], abs_tol=1e-7), (name, period, key)
            metrics[period] = values
        results[name] = dict(trades=len(led), target_checks=len(checks), target_exits=int(targets.sum()), metrics=metrics)
    # Recompute the main annual comparison, independently of yearly.csv.
    wins, eligible = [], []
    for year in range(2016, 2027):
        p, c = [t[t.order_bar.dt.year == year] for t in (runs["primary"], runs["c1"])]
        if len(p) >= 10 and len(c) >= 10:
            eligible.append(year)
            if p.net_r.mean() > c.net_r.mean():
                wins.append(year)
    assert wins == [2021, 2025] and len(eligible) == 9
    # Rebuild the descriptive bootstrap from the raw-ledger arithmetic above.
    bootstrap = {}
    for period in ("train", "recent"):
        lo, hi = PERIODS[period]
        weeks = pd.period_range(lo, pd.Timestamp(hi) - pd.Timedelta(days=1), freq="W")
        samples = np.random.default_rng(20261005).integers(0, len(weeks), size=(5000, len(weeks)))
        draws = []
        for name in ("primary", "c1"):
            t = runs[name]
            t = t[(t.order_bar >= lo) & (t.order_bar < hi)]
            table = pd.DataFrame(dict(week=t.order_bar.dt.to_period("W"), r=t.net_r, count=1,
                                      gain=t.net.clip(lower=0), loss=-t.net.clip(upper=0)))
            blocks = table.groupby("week")[["r", "count", "gain", "loss"]].sum().reindex(weeks, fill_value=0).to_numpy()
            sums = blocks[samples].sum(axis=1)
            draws.append((sums[:, 0] / sums[:, 1], sums[:, 2] / sums[:, 3]))
        intervals = dict(mean_r_diff=np.quantile(draws[0][0] - draws[1][0], [.025, .975]).tolist(),
                         pf_diff=np.quantile(draws[0][1] - draws[1][1], [.025, .975]).tolist())
        for key, value in intervals.items():
            assert np.allclose(value, summary["bootstrap"][period][key], atol=1e-10, rtol=0)
        bootstrap[period] = intervals
    # The trading-build classify output must be identical to the original.
    cls = RUN.parent / "trendline_limit_20261005" / "trendline_limit_20261005_classify_limit.csv"
    classify_identical = digest(cls) == digest(RUN / "trendline_limit_runs_20261005_classify_limit.csv")
    assert classify_identical
    return dict(hash_checks=len(hashes), all_hashes_match=True, classify_byte_identical=classify_identical,
                runs=results, bootstrap=bootstrap, eligible_years=eligible, years_beating_c1=wins,
                scope="Saved outputs and every logged target check re-audited; order replays are the previously saved verification outputs.")


if __name__ == "__main__":
    result = audit()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
