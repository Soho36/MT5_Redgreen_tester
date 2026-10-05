"""Q20: buy limit resting on a rising trendline versus the matched dip-buy control.

Frozen protocol: docs/trendlines/TRENDLINE_LIMIT_PROTOCOL.md. Reads the verified MT5 runs in
Reports/trendlines/trendline_limit_runs_20261005/ (verify_trendline_limit_trade.py first), applies the frozen
reading rule and writes summary.json, yearly.csv, labels.csv and report.md there.
"""
import json

import numpy as np
import pandas as pd

from analyze_price_levels import PERIODS, ROOT, sha256
from analyze_support_interaction import drawdown_interval, trade_metrics
from level_visit import swing_lows
from trend_regimes import SOURCE
from trendline_limit import armed_lines
from verify_location_validation import read_rows
from verify_trendline_limit import bars
from verify_trendline_limit_trade import RUN, TIME, load_fills

STEM = "trendline_limit_runs_20261005"
PROTOCOL = ROOT / "docs" / "trendlines" / "TRENDLINE_LIMIT_PROTOCOL.md"
COST, SEED, BOOT = 1.05, 20261005, 5000
ALL_PERIODS = {"early": ("2010-06-07", "2016-01-01"), **PERIODS}
DECISION = tuple(PERIODS)
SETTINGS = {"": "primary setting (stop 0.5 x A, touch)", "_tt": "trade-through (1 tick lower)",
            "_s025": "stop 0.25 x A", "_s100": "stop 1.0 x A"}
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
    st = v["stats"]
    for key in ("log_errors", "send_errors", "cancel_errors", "no_delta"):
        assert int(st[key]) == 0, (job, key)
    a = v["audit"]
    n = v["fills"]
    for key in ("fill_from_placed_order", "limit_matches_log", "stop_matches_log", "sl_is_order_stop",
                "fill_at_or_below_limit", "ledger_rows", "ledger_entry_time_matches", "ledger_entry_price_matches",
                "ledger_stop_matches", "ledger_range_is_planned_r", "same_session_exit", "mt5_trades"):
        assert a[key] == n, (job, key)
    assert a["overlapping_trades"] == 0 and a["mt5_net_matches_ledger"]
    led = pd.DataFrame(read_rows(RUN / f"runband_{tag}_1.00.csv"))
    for c in ("entry_time", "exit_time", "signal_time"):
        led[c] = pd.to_datetime(led[c], format=TIME)
    led["qualified_time"] = pd.to_datetime(led.qualified_time.replace("", np.nan), format=TIME)
    for c in ("trade_profit", "candle_range", "exit_reason", "base_entry", "initial_stop"):
        led[c] = pd.to_numeric(led[c])
    led = led.sort_values("entry_time").reset_index(drop=True)
    fills = load_fills(tag)
    assert (fills.fill_time.to_numpy() == led.entry_time.to_numpy()).all()
    led = pd.concat([led, fills[["order_bar", "order_limit", "order_stop", "line", "anchor1_time", "anchor2_time",
                                 "delta"]]], axis=1)
    led["net"] = led.trade_profit - COST
    led["net_r"] = led.net / (2 * led.candle_range)
    led["exit_class"] = np.select([led.exit_reason == 4, led.qualified_time.notna()], ["stop", "target_qualified"],
                                  default="other_session")
    led["period"] = period_of(led.order_bar)
    led["year"] = led.order_bar.dt.year
    led["stop_on_fill_bar"] = (led.exit_class == "stop") & (led.exit_time.dt.floor("30min") == led.order_bar) & \
                              (led.entry_time.dt.floor("30min") == led.order_bar)
    return led, v


def m1_lows(minutes):
    """Bid low of each needed one-minute bar from the tester's source data."""
    want = set(minutes)
    parts = []
    for chunk in pd.read_csv(SOURCE, sep="\t", usecols=["<DATE>", "<TIME>", "<LOW>"], chunksize=500000):
        t = pd.to_datetime(chunk["<DATE>"] + " " + chunk["<TIME>"], format="%Y.%m.%d %H:%M:%S")
        keep = t.isin(want)
        if keep.any():
            parts.append(pd.Series(chunk.loc[keep, "<LOW>"].to_numpy(), index=t[keep]))
    return pd.concat(parts)


def longest_losing_run(net):
    best = run = 0
    for x in net:
        run = run + 1 if x < 0 else 0
        best = max(best, run)
    return best


def describe(t):
    r = trade_metrics(t) if len(t) else dict(fills=0)
    if len(t):
        r.update(closed_dd=drawdown_interval(t.sort_values("exit_time").net)[0],
                 longest_losing_run=longest_losing_run(t.sort_values("exit_time").net),
                 largest_trade_share=float(t.net.max() / t.net.sum()) if t.net.sum() > 0 else None,
                 avg_r_points=float(t.candle_range.mean()), cost_share_r=float((COST / (2 * t.candle_range)).mean()),
                 stops_on_fill_bar=int(t.stop_on_fill_bar.sum()), ohlc_ambiguous=int(t.ohlc_ambiguous.sum()))
    return r


def week_bootstrap(p, c, period):
    """Paired calendar-week resampling of primary minus control: mean net R and PF."""
    start, end = PERIODS[period]
    weeks = pd.period_range(pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(days=1), freq="W")
    def by_week(t):
        w = t.order_bar.dt.to_period("W")
        g = t.assign(w=w).groupby("w")
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


def labels(led, b, pivots):
    """Descriptive labels for primary trades, from the line that carried the filled order."""
    pos = pd.Series(np.arange(len(b)), index=b.index)
    low, opn, close = b.low.to_numpy(), b.open.to_numpy(), b.close.to_numpy()
    rows = []
    for r in led.itertuples():
        t = int(pos[r.order_bar])
        _, a, _, lines = armed_lines(b, t, pivots)
        x = next(z for z in lines if b.index[z["i"]] == r.anchor1_time and b.index[z["j"]] == r.anchor2_time)
        fb = int(pos[r.entry_time.floor("30min")])
        minutes = r.order_bar.hour * 60 + r.order_bar.minute
        rows.append(dict(first_retest=x["retests"] == 0, slope_a=x["slope_a"], bars_since_anchor2=t - x["j"],
                         anchor_sep=x["j"] - x["i"], fill_bar_red=bool(close[fb] < opn[fb]),
                         segment="morning" if minutes < 600 else ("main" if minutes < 1380 else "evening"),
                         depth_a=(r.line - low[fb]) / a))
    return pd.DataFrame(rows, index=led.index)


def label_table(led):
    bins = dict(
        first_retest=led.first_retest.map({True: "first retest", False: "later retest"}),
        slope=pd.cut(led.slope_a, [0, 0.04, 0.08, np.inf], labels=["0.02-0.04 A/bar", "0.04-0.08", ">0.08"]),
        bars_since_anchor2=pd.cut(led.bars_since_anchor2, [0, 20, 50, np.inf], labels=["<=20 bars", "21-50", ">50"]),
        anchor_sep=pd.cut(led.anchor_sep, [0, 20, 46, np.inf], labels=["10-20 bars", "21-46", ">46"]),
        fill_bar=led.fill_bar_red.map({True: "fill bar red", False: "fill bar green/flat"}),
        segment=led.segment,
        depth=pd.cut(led.depth_a, [-np.inf, 0.25, 0.5, np.inf], labels=["<=0.25 A below line", "0.25-0.5", ">0.5"]))
    out = []
    for name, lab in bins.items():
        for (period, value), g in led.assign(lab=lab).groupby(["period", "lab"], observed=True):
            if period in DECISION:
                m = trade_metrics(g)
                out.append(dict(label=name, value=str(value), period=period, trades=m["fills"], net=round(m["net"], 2),
                                pf=round(m["pf"], 3) if m["pf"] else None, mean_r=round(m["avg_net_r"], 4)))
    return pd.DataFrame(out)


def main():
    manifest = json.loads((RUN / "manifest.json").read_text())
    assert sha256(PROTOCOL) == manifest["protocol_sha256"], "protocol changed after the runs were prepared"
    runs, verif = {}, {}
    for job in [f"{n}{s}" for n in ("primary", "c1") for s in SETTINGS] + ["c2"]:
        runs[job], verif[job] = load(job)
    need = pd.concat([t.entry_time.dt.floor("min") for t in runs.values()]).unique()
    lows = m1_lows(need)
    for t in runs.values():
        fill_low = lows.reindex(t.entry_time.dt.floor("min")).to_numpy()
        assert not np.isnan(fill_low).any()
        t["ohlc_ambiguous"] = fill_low <= t.initial_stop.to_numpy()
    summary = {}
    for job, t in runs.items():
        summary[job] = {p: describe(t[t.period == p]) for p in ALL_PERIODS}
    # Years and the reading rule.
    years = range(2016, 2027)
    yearly = []
    for suffix in SETTINGS:
        p, c = runs["primary" + suffix], runs["c1" + suffix]
        for y in years:
            a, b_ = p[p.year == y], c[c.year == y]
            yearly.append(dict(setting=suffix or "primary", year=y, primary_trades=len(a), c1_trades=len(b_),
                               primary_mean_r=a.net_r.mean(), c1_mean_r=b_.net_r.mean(),
                               primary_net=a.net.sum(), c1_net=b_.net.sum(),
                               eligible=len(a) >= 10 and len(b_) >= 10,
                               beats=bool(len(a) >= 10 and len(b_) >= 10 and a.net_r.mean() > b_.net_r.mean())))
    yearly = pd.DataFrame(yearly)
    prim = yearly[yearly.setting == "primary"]
    s = lambda job, p, k: summary[job][p][k]
    rule = {}
    for p in DECISION:
        rule[f"{p}_trades_ge_200"] = s("primary", p, "fills") >= 200
        rule[f"{p}_pf_gt_1"] = s("primary", p, "pf") > 1
        rule[f"{p}_mean_r_gt_0"] = s("primary", p, "avg_net_r") > 0
        rule[f"{p}_mean_r_gt_c1"] = s("primary", p, "avg_net_r") > s("c1", p, "avg_net_r")
        rule[f"{p}_tt_pf_gt_1"] = s("primary_tt", p, "pf") > 1
        rule[f"{p}_tt_mean_r_gt_c1_tt"] = s("primary_tt", p, "avg_net_r") > s("c1_tt", p, "avg_net_r")
        rule[f"{p}_s025_mean_r_gt_c1"] = s("primary_s025", p, "avg_net_r") > s("c1_s025", p, "avg_net_r")
        rule[f"{p}_s100_mean_r_gt_c1"] = s("primary_s100", p, "avg_net_r") > s("c1_s100", p, "avg_net_r")
    rule["years_beating_c1"] = int(prim.beats.sum())
    rule["eligible_years"] = int(prim.eligible.sum())
    rule["years_ge_7_of_11"] = int(prim.beats.sum()) >= 7
    passed = all(v for k, v in rule.items() if isinstance(v, bool))
    boot = {p: week_bootstrap(runs["primary"][runs["primary"].period == p], runs["c1"][runs["c1"].period == p], p)
            for p in DECISION}
    b = bars()
    pivots = swing_lows(b.low.to_numpy(), b.contract.to_numpy(), 5)
    pr = runs["primary"]
    pr = pd.concat([pr, labels(pr, b, pivots)], axis=1)
    lab = label_table(pr)
    out = dict(protocol=str(PROTOCOL), protocol_sha256_now=sha256(PROTOCOL), frozen_commit="4c86411",
               cost=COST, seed=SEED, summary=summary, rule=rule, passed=passed, bootstrap=boot, rtl_context=RTL,
               verification={k: dict(fills=v["fills"], placed=v["placed"], mismatched_rows=v["mismatched_rows"],
                                     logged_not_expected=v["logged_not_expected"],
                                     expected_not_logged=v["expected_not_logged"],
                                     fill_in_order_bar=v["audit"]["fill_in_order_bar"]) for k, v in verif.items()})
    (RUN / "summary.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    yearly.to_csv(RUN / "yearly.csv", index=False)
    lab.to_csv(RUN / "labels.csv", index=False)
    for job, t in runs.items():
        t.to_csv(RUN / f"trades_{job}.csv", index=False)
    print(json.dumps(dict(rule=rule, passed=passed, bootstrap=boot), indent=1, default=float))
    for job in runs:
        for p in ALL_PERIODS:
            x = summary[job][p]
            print(f"{job:14s} {p:7s} n={x['fills']:5d} net={x.get('net', 0):10.2f} pf={x.get('pf') or 0:.3f} "
                  f"meanR={x.get('avg_net_r') or 0:+.4f} win={x.get('win_rate') or 0:.3f} "
                  f"stop={x.get('exit_stop', 0)} tgt={x.get('exit_target_qualified', 0)} "
                  f"dd={x.get('closed_dd', 0):.0f} Rpts={x.get('avg_r_points', 0):.2f} cost={x.get('cost_share_r', 0):.3f} "
                  f"fillbarstop={x.get('stops_on_fill_bar', 0)} amb={x.get('ohlc_ambiguous', 0)}")
    print(prim[["year", "primary_trades", "c1_trades", "primary_mean_r", "c1_mean_r", "beats"]].to_string())


if __name__ == "__main__":
    main()
