"""Q21: short the breakdown of a rising trendline versus shorting any red bar in the same regime.

Frozen protocol: docs/trendlines/BREAKDOWN_SHORT_PROTOCOL.md. Reads the verified MT5 runs in
Reports/trendlines/trendline_breakdown_runs_20261006/ (verify_trendline_breakdown_trade.py first), applies the frozen
reading rule and writes summary.json, yearly.csv, labels.csv and trades_<job>.csv there.
Usage: analyze_trendline_breakdown.py [_rr2]  (the exploratory 2R follow-up writes summary_rr2.json etc.)
"""
import json
import sys

import numpy as np
import pandas as pd

from analyze_price_levels import PERIODS, ROOT, sha256
from analyze_support_interaction import drawdown_interval, trade_metrics
from analyze_trendline_limit import longest_losing_run
from trend_regimes import SOURCE
from verify_trendline_breakdown import RUN as CLASSIFY, STEM as CLASSIFY_STEM, bars
from prepare_trendline_breakdown import rr_label
from verify_trendline_breakdown_trade import RUN, STEM, load_fills, load_ledger, load_log

PROTOCOL = ROOT / "docs" / "trendlines" / "BREAKDOWN_SHORT_PROTOCOL.md"
COST, SEED, BOOT, TICK = 1.05, 20261006, 5000, 0.25
ALL_PERIODS = {"early": ("2010-06-07", "2016-01-01"), **PERIODS}
DECISION = tuple(PERIODS)
JOBS = ("primary", "s1", "c1", "c2")
RTL = {"train": dict(pf=1.106, mean_r=-0.004), "recent": dict(pf=1.107, mean_r=0.060)}


def period_of(times):
    out = pd.Series(None, index=times.index, dtype="object")
    for name, (start, end) in ALL_PERIODS.items():
        out[(times >= pd.Timestamp(start)) & (times < pd.Timestamp(end))] = name
    return out


def load(job):
    tag = f"{STEM}_{job}"
    v = json.loads((RUN / f"{tag}_verification.json").read_text())
    assert v["mismatched_rows"] == 0, (job, "replay mismatches")
    assert v["logged_not_expected_unexplained"] == 0 and v["expected_not_logged_unexplained"] == 0, job
    st = v["stats"]
    for key in ("log_errors", "send_errors", "cancel_errors", "close_errors"):
        assert int(st[key]) == 0, (job, key)
    a, n = v["audit"], v["audit"]["fills"]
    for key in ("fill_is_short", "fill_from_placed_order", "entry_matches_log", "stop_matches_log", "sl_is_order_stop",
                "fill_at_or_below_entry", "ledger_rows", "ledger_direction_short", "ledger_rr_matches_input",
                "ledger_entry_time_matches", "ledger_entry_price_matches", "ledger_stop_matches",
                "ledger_range_is_planned_r", "ledger_signal_is_s", "same_session_exit", "mt5_trades"):
        assert a[key] == n, (job, key)
    assert a["overlapping_trades"] == 0 and a["mt5_net_matches_ledger"]
    led = load_ledger(tag, rr_label(v["inputs"]))
    fills = load_fills(tag)
    assert (fills.fill_time.to_numpy() == led.entry_time.to_numpy()).all()
    led = pd.concat([led, fills[["order_bar", "s_time", "order_entry", "order_stop", "line", "anchor1_time",
                                 "anchor2_time"]]], axis=1)
    led["net"] = led.trade_profit - COST
    led["net_r"] = led.net / (2 * led.candle_range)
    led["exit_class"] = np.select([led.exit_reason == 4, led.qualified_time.notna()], ["stop", "target_qualified"],
                                  default="other_session")
    led["period"] = period_of(led.order_bar)
    led["year"] = led.order_bar.dt.year
    led["stop_on_fill_bar"] = (led.exit_class == "stop") & (led.exit_time.dt.floor("30min") == led.order_bar) & \
                              (led.entry_time.dt.floor("30min") == led.order_bar)
    return led, v


def m1_highs(minutes):
    """Bid high of each needed one-minute bar from the tester's source data."""
    want = set(minutes)
    parts = []
    for chunk in pd.read_csv(SOURCE, sep="\t", usecols=["<DATE>", "<TIME>", "<HIGH>"], chunksize=500000):
        t = pd.to_datetime(chunk["<DATE>"] + " " + chunk["<TIME>"], format="%Y.%m.%d %H:%M:%S")
        keep = t.isin(want)
        if keep.any():
            parts.append(pd.Series(chunk.loc[keep, "<HIGH>"].to_numpy(), index=t[keep]))
    return pd.concat(parts)


def describe(t):
    r = trade_metrics(t) if len(t) else dict(fills=0)
    if len(t):
        r.update(closed_dd=drawdown_interval(t.sort_values("exit_time").net)[0],
                 longest_losing_run=longest_losing_run(t.sort_values("exit_time").net),
                 largest_trade_share=float(t.net.max() / t.net.sum()) if t.net.sum() > 0 else None,
                 avg_r_points=float(t.candle_range.mean()), cost_share_r=float((COST / (2 * t.candle_range)).mean()),
                 stops_on_fill_bar=int(t.stop_on_fill_bar.sum()), ohlc_ambiguous=int(t.ohlc_ambiguous.sum()))
    return r


def volume(log, period):
    """Orders placed / gap skips from the verified run log, per period of the order bar."""
    start, end = ALL_PERIODS[period]
    p = log[(log.bar_time >= pd.Timestamp(start)) & (log.bar_time < pd.Timestamp(end))]
    return dict(placed=int((p.action == "placed").sum()), gap_skips=int((p.action == "gap_below").sum()))


def week_bootstrap(p, c, period):
    """Paired calendar-week resampling of primary minus control: mean net R and PF."""
    start, end = PERIODS[period]
    weeks = pd.period_range(pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(days=1), freq="W")

    def by_week(t):
        g = t.assign(w=t.order_bar.dt.to_period("W")).groupby("w")
        return (g.net_r.sum().reindex(weeks, fill_value=0).to_numpy(), g.net_r.count().reindex(weeks, fill_value=0).to_numpy(),
                g.net.apply(lambda x: x[x > 0].sum()).reindex(weeks, fill_value=0).to_numpy(),
                g.net.apply(lambda x: -x[x < 0].sum()).reindex(weeks, fill_value=0).to_numpy())
    ps, pn, pg, pl = by_week(p)
    cs, cn, cg, cl = by_week(c)
    idx = np.random.default_rng(SEED).integers(0, len(weeks), size=(BOOT, len(weeks)))
    mean_diff = ps[idx].sum(1) / pn[idx].sum(1) - cs[idx].sum(1) / cn[idx].sum(1)
    pf_diff = pg[idx].sum(1) / pl[idx].sum(1) - cg[idx].sum(1) / cl[idx].sum(1)
    q = lambda x: [float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975))]
    return dict(weeks=len(weeks), mean_r_diff=q(mean_diff), pf_diff=q(pf_diff))


def labels(led, b):
    """Descriptive labels for primary trades from the verified classify-only bar table (bar t = order bar)."""
    cls = pd.read_csv(CLASSIFY / f"{CLASSIFY_STEM}_classify_bars.csv", parse_dates=["bar_time", "s_time"])
    x = led[["order_bar"]].merge(cls.rename(columns={"bar_time": "order_bar"}), on="order_bar", how="left",
                                 validate="many_to_one")
    assert (x.status_ea == "order").all()
    pos = pd.Series(np.arange(len(b)), index=b.index)
    s = pos.reindex(x.s_time).to_numpy()
    lo, hi, cl = b.low.to_numpy()[s], b.high.to_numpy()[s], b.close.to_numpy()[s]
    minutes = x.order_bar.dt.hour * 60 + x.order_bar.dt.minute
    return pd.DataFrame(dict(depth_a=x.depth_a, range_a=x.range_a, close_location=(cl - lo) / (hi - lo),
                             opens_above=x.opens_above.astype(bool), slope_a=x.slope_a, anchor_sep=x.anchor_sep,
                             bars_since_anchor2=x.bars_since_anchor2, bars_since_departure=x.bars_since_departure,
                             retests=x.retests, lines_broken=x.lines_broken_ea,
                             segment=np.select([minutes < 600, minutes < 1380], ["morning", "main"], "evening")),
                        index=led.index)


def label_table(led):
    bins = dict(
        depth=pd.cut(led.depth_a, [-np.inf, 0.25, 0.5, 1.0, np.inf], labels=["<=0.25 A", "0.25-0.5", "0.5-1", ">1"]),
        range=pd.cut(led.range_a, [0, 1.0, 1.5, 2.5, np.inf], labels=["<=1 A", "1-1.5", "1.5-2.5", ">2.5"]),
        close_location=pd.cut(led.close_location, [-0.01, 0.2, 0.5, 1.0], labels=["close in low 20%", "20-50%", ">50%"]),
        opens_above=led.opens_above.map({True: "opened above line", False: "opened below line"}),
        slope=pd.cut(led.slope_a, [0, 0.04, 0.08, np.inf], labels=["0.02-0.04 A/bar", "0.04-0.08", ">0.08"]),
        anchor_sep=pd.cut(led.anchor_sep, [0, 20, 46, np.inf], labels=["10-20 bars", "21-46", ">46"]),
        bars_since_anchor2=pd.cut(led.bars_since_anchor2, [0, 20, 50, np.inf], labels=["<=20 bars", "21-50", ">50"]),
        bars_since_departure=pd.cut(led.bars_since_departure, [0, 10, 30, np.inf], labels=["<=10 bars", "11-30", ">30"]),
        retests=pd.cut(led.retests, [-1, 0, 1, np.inf], labels=["0 retests", "1", ">=2"]),
        lines_broken=pd.cut(led.lines_broken, [0, 1, np.inf], labels=["1 line", ">=2 lines"]),
        segment=led.segment)
    out = []
    for name, lab in bins.items():
        for (period, value), g in led.assign(lab=lab).groupby(["period", "lab"], observed=True):
            if period in DECISION:
                m = trade_metrics(g)
                out.append(dict(label=name, value=str(value), period=period, trades=m["fills"], net=round(m["net"], 2),
                                pf=round(m["pf"], 3) if m["pf"] else None, mean_r=round(m["avg_net_r"], 4)))
    return pd.DataFrame(out)


def main(suffix=""):
    manifest = json.loads((RUN / "manifest.json").read_text())
    runs, verif = {}, {}
    for job in JOBS:
        runs[job], verif[job] = load(job + suffix)
    need = pd.concat([t.entry_time.dt.floor("min") for t in runs.values()]).unique()
    highs = m1_highs(need)
    for t in runs.values():
        fill_high = highs.reindex(t.entry_time.dt.floor("min")).to_numpy()
        assert not np.isnan(fill_high).any()
        t["ohlc_ambiguous"] = fill_high >= t.initial_stop.to_numpy() - TICK  # the ask reached the stop
    logs = {job: load_log(RUN / f"{STEM}_{job}{suffix}_breakdown.csv") for job in JOBS}
    summary = {job: {p: dict(describe(t[t.period == p]), **volume(logs[job], p)) for p in ALL_PERIODS}
               for job, t in runs.items()}
    yearly = []
    for job in ("primary", "s1"):
        p, c = runs[job], runs["c1"]
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
        rule[f"{p}_s1_pf_gt_1"] = s("s1", p, "pf") > 1
        rule[f"{p}_s1_mean_r_gt_c1"] = s("s1", p, "avg_net_r") > s("c1", p, "avg_net_r")
    rule["years_beating_c1"] = int(prim.beats.sum())
    rule["eligible_years"] = int(prim.eligible.sum())
    rule["years_ge_7_of_11"] = int(prim.beats.sum()) >= 7
    passed = all(v for v in rule.values() if isinstance(v, bool))
    boot = {p: week_bootstrap(runs["primary"][runs["primary"].period == p], runs["c1"][runs["c1"].period == p], p)
            for p in DECISION}
    b = bars()
    pr = pd.concat([runs["primary"], labels(runs["primary"], b)], axis=1)
    lab = label_table(pr)
    out = dict(protocol=str(PROTOCOL), protocol_sha256_now=sha256(PROTOCOL),
               protocol_sha256_at_prepare=manifest["protocol_sha256"], frozen_commit="04630e8", cost=COST, seed=SEED,
               summary=summary, rule=rule, passed=passed, bootstrap=boot, rtl_context=RTL,
               verification={k: dict(fills=v["audit"]["fills"], placed=v["audit"]["placed"],
                                     mismatched_rows=v["mismatched_rows"], boundary_fills=v["boundary_fills"],
                                     logged_not_expected=v["logged_not_expected"],
                                     expected_not_logged=v["expected_not_logged"]) for k, v in verif.items()})
    (RUN / f"summary{suffix}.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    yearly.to_csv(RUN / f"yearly{suffix}.csv", index=False)
    lab.to_csv(RUN / f"labels{suffix}.csv", index=False)
    pr.to_csv(RUN / f"trades_primary{suffix}.csv", index=False)
    for job in JOBS[1:]:
        runs[job].to_csv(RUN / f"trades_{job}{suffix}.csv", index=False)
    print(json.dumps(dict(rule=rule, passed=passed, bootstrap=boot), indent=1, default=float))
    for job in runs:
        for p in ALL_PERIODS:
            x = summary[job][p]
            print(f"{job:8s} {p:7s} n={x['fills']:5d} placed={x['placed']:5d} net={x.get('net', 0):10.2f} "
                  f"pf={x.get('pf') or 0:.3f} meanR={x.get('avg_net_r') or 0:+.4f} medR={x.get('median_net_r') or 0:+.3f} "
                  f"win={x.get('win_rate') or 0:.3f} stop={x.get('exit_stop', 0)} tgt={x.get('exit_target_qualified', 0)} "
                  f"oth={x.get('exit_other_session', 0)} dd={x.get('closed_dd', 0):.0f} Rpts={x.get('avg_r_points', 0):.2f} "
                  f"cost={x.get('cost_share_r', 0):.3f} fbstop={x.get('stops_on_fill_bar', 0)} amb={x.get('ohlc_ambiguous', 0)}")
    print(yearly.to_string())


if __name__ == "__main__":
    main(*sys.argv[1:])
