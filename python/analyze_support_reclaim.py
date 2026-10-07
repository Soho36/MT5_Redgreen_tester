"""Q24: buy the reclaim of a broken swing-low level versus the RTL entry on the same candles.

Frozen protocol: docs/setups/horizontal/support-reclaim-long/q25-support-reclaim/PROTOCOL.md. Reads the verified MT5 runs in
Reports/levels/support_reclaim_runs_20261007/ (verify_support_reclaim_trade.py first), applies the frozen reading
rule and writes summary.json, yearly.csv, labels.csv and trades_<job>.csv there.
Usage: analyze_support_reclaim.py [nocancel]   (the exploratory follow-up without cancellation on a touch of the low)
"""
import json
import sys

import numpy as np
import pandas as pd

from analyze_price_levels import PERIODS, ROOT, sha256
from analyze_support_interaction import trade_metrics
from analyze_trendline_breakdown import ALL_PERIODS, describe, period_of, week_bootstrap
from verify_support_reclaim import RUN as CLASSIFY, STEM as CLASSIFY_STEM, bars
from prepare_support_reclaim import VARIANTS
from verify_support_reclaim_trade import load_ledger, load_log, load_table, minutes

PROTOCOL = ROOT / "docs" / "setups" / "horizontal" / "support-reclaim-long" / "q25-support-reclaim" / "PROTOCOL.md"
DAILY = ROOT / "Reports" / "trend_rr_20261002" / "daily_reference.csv"
COST, SEED = 1.05, 20261007
DECISION = tuple(PERIODS)
JOBS = ("primary", "c1", "primary_s1", "c1_s1")
RTL = {"train": dict(pf=1.106, mean_r=-0.004), "recent": dict(pf=1.107, mean_r=0.060)}


def load(job, run, stem):
    tag = f"{stem}_{job}"
    v = json.loads((run / f"{tag}_verification.json").read_text())
    assert v["mismatched_rows"] == 0, (job, "replay mismatches")
    assert v["logged_not_expected_unexplained"] == 0 and v["expected_not_logged_unexplained"] == 0, job
    assert v["order_life"]["disagree"] == 0, (job, "order life")
    for key in ("log_errors", "send_errors", "cancel_errors", "close_errors"):
        assert int(v["stats"][key]) == 0, (job, key)
    a, n = v["audit"], v["audit"]["fills"]
    for key in ("fill_from_placed_order", "entry_matches_log", "stop_matches_log", "sl_is_order_stop",
                "fill_at_or_above_entry", "fill_within_life", "ledger_rows", "ledger_rr_is_1",
                "ledger_entry_time_matches", "ledger_entry_price_matches", "ledger_stop_matches",
                "ledger_range_is_planned_r", "ledger_signal_is_s", "same_session_exit", "mt5_trades"):
        assert a[key] == n, (job, key)
    assert a["overlapping_trades"] == 0 and a["mt5_net_matches_ledger"]
    led = load_ledger(tag, run)
    fills = load_table(run / f"{tag}_fills.csv", ("fill_time", "order_bar", "s_time", "key_time"),
                       ("fill_price", "sl", "order_entry", "order_stop", "level", "age"))
    assert (fills.fill_time.to_numpy() == led.entry_time.to_numpy()).all()
    led = pd.concat([led, fills[["order_bar", "s_time", "order_entry", "order_stop", "level", "key_time", "age"]]], axis=1)
    led["net"] = led.trade_profit - COST
    led["net_r"] = led.net / (2 * led.candle_range)
    led["exit_class"] = np.select([led.exit_reason == 4, led.qualified_time.notna()], ["stop", "target_qualified"],
                                  default="other_session")
    led["period"] = period_of(led.order_bar)
    led["year"] = led.order_bar.dt.year
    led["stop_on_fill_bar"] = (led.exit_class == "stop") & \
        (led.exit_time.dt.floor("30min") == led.entry_time.dt.floor("30min"))
    cancels = load_table(run / f"{tag}_cancels.csv", ("cancel_time", "order_bar"), ("order_entry", "order_stop", "age"))
    cancels["period"] = period_of(cancels.order_bar)
    log = load_log(run / f"{tag}_reclaim.csv")
    log["period"] = period_of(log.bar_time)
    return led, cancels, log, v


def labels(t, b, daily):
    """Descriptive labels for primary trades from the verified classify-only bar table (bar t = order bar)."""
    cls = pd.read_csv(CLASSIFY / f"{CLASSIFY_STEM}_classify_bars.csv", parse_dates=["bar_time", "s_time", "t0_time_ea"])
    x = t[["order_bar"]].merge(cls.rename(columns={"bar_time": "order_bar"}), on="order_bar", how="left",
                               validate="many_to_one")
    assert (x.status_ea == "order").all()
    pos = pd.Series(np.arange(len(b)), index=b.index)
    age = pos.reindex(x.s_time).to_numpy() - pos.reindex(x.t0_time_ea).to_numpy()
    minutes_ = t.order_bar.dt.hour * 60 + t.order_bar.dt.minute
    lab = pd.DataFrame(dict(
        depth=pd.cut(x.depth_a.to_numpy(), [-np.inf, 0.25, 0.5, 1.0, np.inf], labels=["<=0.25 A", "0.25-0.5", "0.5-1", ">1"]),
        risk=pd.cut(x.risk_a.to_numpy(), [0, 0.5, 1.0, 1.5, np.inf], labels=["0.25-0.5 A", "0.5-1", "1-1.5", ">1.5"]),
        fill_bar=t.age.map({0: "1st bar", 1: "2nd bar", 2: "3rd bar"}).to_numpy(),
        level_age=pd.cut(age, [0, 20, 50, np.inf], labels=["<=20 bars", "21-50", ">50"]),
        members=np.where(x.members_ea.to_numpy() > 1, "merged", "single"),
        segment=np.select([minutes_ < 600, minutes_ < 1380], ["morning", "main"], "evening"),
        regime=daily.regime50.reindex(t.order_bar.dt.normalize()).to_numpy()), index=t.index)
    out = []
    for name in lab.columns:
        for (period, value), g in t.assign(lab=lab[name]).groupby(["period", "lab"], observed=True):
            if period in DECISION:
                m = trade_metrics(g)
                out.append(dict(label=name, value=str(value), period=period, trades=m["fills"], net=round(m["net"], 2),
                                pf=round(m["pf"], 3) if m["pf"] else None, mean_r=round(m["avg_net_r"], 4)))
    return pd.DataFrame(out)


def main(variant=""):
    run, stem, _ = VARIANTS[variant]
    manifest = json.loads((run / "manifest.json").read_text())
    runs, cancels, logs, verif = {}, {}, {}, {}
    for job in JOBS:
        runs[job], cancels[job], logs[job], verif[job] = load(job, run, stem)
    mt, _, ml, _ = minutes()
    for t in runs.values():
        k = np.searchsorted(mt, t.entry_time.dt.floor("min").to_numpy())
        assert (mt[k] == t.entry_time.dt.floor("min").to_numpy()).all()
        t["ohlc_ambiguous"] = ml[k] <= t.initial_stop.to_numpy()   # the fill minute also reached the stop
    summary = {}
    for job, t in runs.items():
        summary[job] = {}
        for p in ALL_PERIODS:
            lg, cc = logs[job][logs[job].period == p], cancels[job][cancels[job].period == p]
            summary[job][p] = dict(describe(t[t.period == p]), placed=int(lg.action.isin(["placed", "replaced"]).sum()),
                                   cancels=cc.reason.value_counts().to_dict(),
                                   fills_by_bar=t[t.period == p].age.value_counts().sort_index().to_dict())
    skips = {job: json.loads((CLASSIFY / f"{CLASSIFY_STEM}_{job}_counts.json").read_text())
             for job in ("classify", "classify_s1")}
    yearly = []
    for job, ctl in (("primary", "c1"), ("primary_s1", "c1_s1")):
        p, c = runs[job], runs[ctl]
        for y in range(2016, 2027):
            a, b_ = p[p.year == y], c[c.year == y]
            yearly.append(dict(run=job, year=y, trades=len(a), c1_trades=len(b_), mean_r=a.net_r.mean(),
                               c1_mean_r=b_.net_r.mean(), net=a.net.sum(), c1_net=b_.net.sum(),
                               eligible=len(a) >= 10 and len(b_) >= 10,
                               beats=bool(len(a) >= 10 and len(b_) >= 10 and a.net_r.mean() > b_.net_r.mean())))
    yearly = pd.DataFrame(yearly)
    prim = yearly[yearly.run == "primary"]
    s = lambda job, p, k: summary[job][p][k]
    rule = {}
    for p in DECISION:
        rule[f"{p}_trades_ge_200"] = s("primary", p, "fills") >= 200
        rule[f"{p}_pf_gt_1"] = s("primary", p, "pf") > 1
        rule[f"{p}_mean_r_gt_0"] = s("primary", p, "avg_net_r") > 0
        rule[f"{p}_mean_r_gt_c1"] = s("primary", p, "avg_net_r") > s("c1", p, "avg_net_r")
        rule[f"{p}_s1_pf_gt_1"] = s("primary_s1", p, "pf") > 1
        rule[f"{p}_s1_mean_r_gt_c1"] = s("primary_s1", p, "avg_net_r") > s("c1_s1", p, "avg_net_r")
    rule["years_beating_c1"] = int(prim.beats.sum())
    rule["eligible_years"] = int(prim.eligible.sum())
    rule["years_ge_7_of_11"] = int(prim.beats.sum()) >= 7
    passed = all(v for v in rule.values() if isinstance(v, bool))
    boot = {p: week_bootstrap(runs["primary"][runs["primary"].period == p], runs["c1"][runs["c1"].period == p], p, SEED)
            for p in DECISION}
    b = bars()
    daily = pd.read_csv(DAILY, index_col=0, parse_dates=[0])
    lab = labels(runs["primary"], b, daily)
    out = dict(protocol=str(PROTOCOL), protocol_sha256_now=sha256(PROTOCOL),
               protocol_sha256_at_prepare=manifest["protocol_sha256"], frozen_commit="57bc971", cost=COST, seed=SEED,
               summary=summary, skips=skips, rule=rule, passed=passed, bootstrap=boot, rtl_context=RTL,
               verification={k: dict(fills=v["audit"]["fills"], mismatched_rows=v["mismatched_rows"],
                                     order_life=v["order_life"]) for k, v in verif.items()})
    (run / "summary.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    yearly.to_csv(run / "yearly.csv", index=False)
    lab.to_csv(run / "labels.csv", index=False)
    for job, t in runs.items():
        t.to_csv(run / f"trades_{job}.csv", index=False)
    print(json.dumps(dict(rule=rule, passed=passed, bootstrap=boot), indent=1, default=float))
    for job in runs:
        for p in ALL_PERIODS:
            x = summary[job][p]
            print(f"{job:10s} {p:6s} n={x['fills']:5d} placed={x['placed']:5d} net={x.get('net', 0):9.0f} "
                  f"pf={x.get('pf') or 0:.3f} meanR={x.get('avg_net_r') or 0:+.4f} win={x.get('win_rate') or 0:.3f} "
                  f"stop={x.get('exit_stop', 0)} tgt={x.get('exit_target_qualified', 0)} oth={x.get('exit_other_session', 0)} "
                  f"dd={x.get('closed_dd', 0):.0f} Rpts={x.get('avg_r_points', 0):.2f} cost={x.get('cost_share_r', 0):.3f} "
                  f"fbstop={x.get('stops_on_fill_bar', 0)} amb={x.get('ohlc_ambiguous', 0)} cancels={x['cancels']} "
                  f"bars={x['fills_by_bar']}")
    print(yearly.to_string())


if __name__ == "__main__":
    main(*sys.argv[1:])
