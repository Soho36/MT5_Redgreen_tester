"""Q18 stage 2: stand-alone horizontal breakout candidate run; frozen protocol docs/setups/horizontal/resistance-breakout-long/q18-breakout/PROTOCOL.md.

Reads the GateMode=2 MT5 run, audits it, compares it with the stage-1 attribution and the baseline full strategy,
and applies the frozen (Q17) reading rule. Outputs into the run folder.
"""

import json

import numpy as np
import pandas as pd

from analyze_level_visit import load as load_q10
from analyze_price_levels import PERIODS, ROOT, sha256, protocol_matches
from analyze_support_interaction import drawdown_interval, trade_metrics
from verify_location_validation import read_rows
from verify_breakout_gate import load_gate

RUN = ROOT / "Reports" / "levels" / "breakout_standalone_20261004"
Q15 = ROOT / "Reports" / "levels" / "breakout_20261004"  # stage-1 attribution
TAG = "breakout_standalone_20261004_trade"
PROTOCOL = ROOT / "docs" / "setups" / "horizontal" / "resistance-breakout-long" / "q18-breakout" / "PROTOCOL.md"
COST, SEED = 1.05, 20261004
Q15_REF = {"train": dict(fills=751, pf=1.198, mean_r=0.049), "recent": dict(fills=1181, pf=1.192, mean_r=0.121)}


def period_of(times):
    out = pd.Series(pd.NA, index=times.index, dtype="object")
    for name, (start, end) in PERIODS.items():
        out[(times >= pd.Timestamp(start)) & (times < pd.Timestamp(end))] = name
    return out


def load_run():
    manifest = json.loads((RUN / "manifest.json").read_text())
    assert sha256(RUN / "RTL_level_gate.mq5") == manifest["expert_sha256"]
    assert protocol_matches(PROTOCOL, manifest["protocol_sha256"]), "protocol changed after freeze"
    assert (RUN / f"{TAG}.completed.json").exists()
    ini = (RUN / f"{TAG}.ini").read_text(encoding="utf-16").splitlines()
    for value in ("GateMode=2", "Model=1", "Period=M30", "Symbol=MNQcontDTBNT20102026_2", "MaxRedRun=3",
                  "MinLocation=0", "BullRR=1.0", "BearRR=1.0", "AverageNearStopR=0", "TrailDistanceR=0"):
        assert value in ini, value
    stats = read_rows(RUN / f"runband_{TAG}_1.00_stats.csv")[0]
    gate_stats = read_rows(RUN / f"{TAG}_gate_stats.csv")[0]
    for key in ("trend_export_errors", "trend_close_errors", "cancel_errors", "orphan_close_errors", "adds_placed"):
        assert int(stats[key]) == 0, key
    assert int(gate_stats["gate_errors"]) == 0 and int(gate_stats["gate_mode"]) == 2
    led = pd.DataFrame(read_rows(RUN / f"runband_{TAG}_1.00.csv"))
    assert len(led) == int(stats["trades"])
    assert np.isclose(led.trade_profit.astype(float).sum(), float(stats["net_profit"]), atol=1e-6)
    for c in ("entry_time", "exit_time", "signal_time"):
        led[c] = pd.to_datetime(led[c], format="%Y.%m.%d %H:%M:%S")
    led["qualified_time"] = pd.to_datetime(led.qualified_time.replace("", np.nan), format="%Y.%m.%d %H:%M:%S")
    for c in ("trade_profit", "candle_range", "signal_high", "signal_low", "exit_reason", "mae_money", "mfe_money"):
        led[c] = pd.to_numeric(led[c])
    assert (led.entry_time.dt.normalize() == led.exit_time.dt.normalize()).all(), "trade crosses a session"
    led["net"] = led.trade_profit - COST
    led["net_r"] = led.net / (2 * led.candle_range)
    led["exit_class"] = np.select([led.exit_reason == 4, led.qualified_time.notna()], ["stop", "target_qualified"],
                                  default="other_session")
    led["period"] = period_of(led.signal_time)
    led["year"] = led.signal_time.dt.year
    gate = load_gate(TAG)
    t = led.merge(gate[["signal_time", "group", "level", "atr", "action"]], on="signal_time", how="left",
                  validate="one_to_one")
    assert (t.group == "breakout_test").all() and (t.action == "placed").all(), "a non-candidate traded"
    assert np.allclose(t.signal_high, led.signal_high)
    t["entry_below_line"] = t.signal_high < t.level  # label: entry below L
    gate["period"] = period_of(gate.signal_time)
    return t, gate, stats, gate_stats, manifest


def week_bootstrap(t, period, repeats=5000):
    start, end = PERIODS[period]
    first = pd.Timestamp(start) - pd.Timedelta(days=pd.Timestamp(start).dayofweek)
    weeks = pd.date_range(first, pd.Timestamp(end) - pd.Timedelta(days=1), freq="7D")
    w = t.assign(week=t.signal_time.dt.normalize() - pd.to_timedelta(t.signal_time.dt.dayofweek, unit="D"))
    f = pd.DataFrame(dict(week=w.week, gains=w.net.clip(lower=0), losses=-w.net.clip(upper=0), r=w.net_r, n=1))
    blocks = f.groupby("week").sum().reindex(weeks, fill_value=0).to_numpy()
    v = blocks[np.random.default_rng(SEED).integers(0, len(weeks), size=(repeats, len(weeks)))].sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        pf, mean_r = v[:, 0] / v[:, 1], v[:, 2] / v[:, 3]
    q = lambda x: [float(z) for z in np.quantile(x[np.isfinite(x)], [.025, .975])]
    return dict(weeks=len(weeks), pf=q(pf), mean_r=q(mean_r))


def longest_losing_run(net):
    best = run = 0
    for x in net:
        run = run + 1 if x < 0 else 0
        best = max(best, run)
    return best


def summary(t):
    m = trade_metrics(t)
    dd, _, _ = drawdown_interval(t.sort_values("exit_time").net)
    m.update(closed_trade_dd=dd, longest_losing_run=longest_losing_run(t.sort_values("exit_time").net),
             largest_trade_share=float(t.net.max() / t.net.sum()) if len(t) and t.net.sum() > 0 else None)
    return m


def main():
    t, gate, stats, gate_stats, manifest = load_run()
    census, base_trades, _, _, _ = load_q10()  # hash-verified Q10 baseline population and fills
    base = census[census.filled].merge(base_trades, on="event_id", validate="one_to_one")
    q15 = pd.read_csv(Q15 / "trades.csv", parse_dates=["signal_time", "entry_time", "exit_time"])
    q15 = q15[(q15.config == "week_n5") & (q15.group == "breakout_test")]
    rows, yearly, contrasts = [], [], {}
    for period in PERIODS:
        s = t[t.period == period]
        b = base[base.period == period]
        a = q15[q15.period == period]
        g = gate[gate.period == period]
        assert len(a) == Q15_REF[period]["fills"]
        shared = s.merge(b[["signal_time", "entry_time", "exit_time", "net"]], on="signal_time", suffixes=("", "_base"))
        identical = ((shared.entry_time == shared.entry_time_base) & (shared.exit_time == shared.exit_time_base) &
                     np.isclose(shared.net, shared.net_base))
        freed = s[~s.signal_time.isin(b.signal_time)]
        displaced = a[~a.signal_time.isin(s.signal_time)]
        row = dict(period=period, standalone=summary(s), q15_attribution=summary(a), baseline=summary(b),
                   entry_below_line=summary(s[s.entry_below_line]), entry_at_or_above_line=summary(s[~s.entry_below_line]),
                   candidate_orders_placed=int((g.action == "placed").sum()),
                   fill_rate=len(s) / int((g.action == "placed").sum()),
                   shared_with_baseline=len(shared), shared_identical=int(identical.sum()),
                   shared_with_q15=int(s.signal_time.isin(a.signal_time).sum()),
                   freed_trades=summary(freed), displaced_q15_trades=summary(displaced),
                   bootstrap=week_bootstrap(s, period))
        rows.append(row)
        for year in sorted(s.year.unique()):
            sy, by = s[s.year == year], b[b.year == year]
            yearly.append(dict(period=period, year=int(year), standalone=summary(sy), baseline_mean_r=float(by.net_r.mean()),
                               baseline_pf=trade_metrics(by)["pf"], counted=len(sy) >= 10,
                               beats_baseline=bool(len(sy) >= 10 and sy.net_r.mean() > by.net_r.mean())))
        contrasts[period] = dict(pf_gt_1=row["standalone"]["pf"] > 1, mean_r_gt_0=row["standalone"]["avg_net_r"] > 0,
                                 mean_r_gt_baseline=row["standalone"]["avg_net_r"] > row["baseline"]["avg_net_r"])
    years_beat = sum(y["beats_baseline"] for y in yearly)
    years_counted = sum(y["counted"] for y in yearly)
    survives = all(all(c.values()) for c in contrasts.values()) and years_beat >= 7
    decision = dict(periods=contrasts, years_beating_baseline=years_beat, years_counted=years_counted,
                    survives_own_execution=bool(survives))
    audit = dict(trades_total=len(t), trades_in_periods=int(t.period.notna().sum()), mt5_net_profit=float(stats["net_profit"]),
                 gate_counts={k: int(v) for k, v in gate_stats.items()}, all_trades_are_candidates=True,
                 sessions_crossed=0, expert_sha256=manifest["expert_sha256"], protocol_sha256=manifest["protocol_sha256"])
    t.to_csv(RUN / "standalone_trades.csv", index=False)
    pd.json_normalize(yearly).to_csv(RUN / "yearly.csv", index=False)
    for name, obj in (("summary", rows), ("yearly", yearly), ("decision", decision), ("audit", audit)):
        (RUN / f"{name}.json").write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
    paths = [RUN / "manifest.json", RUN / "RTL_level_gate.mq5", RUN / "level_gate.mqh", RUN / f"{TAG}.ini",
             RUN / f"runband_{TAG}_1.00.csv", RUN / f"runband_{TAG}_1.00_stats.csv", RUN / f"{TAG}_gate.csv",
             Q15 / "trades.csv", PROTOCOL, ROOT / "python" / "analyze_breakout_standalone.py"]
    (RUN / "provenance.json").write_text(json.dumps(dict(seed=SEED, files=[dict(path=str(p), sha256=sha256(p))
                                                                         for p in paths]), indent=2), encoding="utf-8")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
