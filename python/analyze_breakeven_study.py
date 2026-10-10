"""Analyze the break-even stop study (protocol: docs/baseline/breakeven-stop/PROTOCOL.md).

Checks: the protocol is the version the runs were prepared from; the control ledger is byte-identical to the
saved baseline; both ledgers pass the audit against MT5's order/deal report; no failed stop modification; the
stop-move flag equals "logged MFE >= 1R" on every trade; every trade that differs from the control was moved
to break-even and closed at exactly the entry price.
Then applies the pre-set rule (beat the control on BOTH net $ and average net R in BOTH 2016-19 and 2020-26)
and prints the paired breakdown: trades cut at break-even, new trades, displaced trades.

Costs $1.05 per trade; R = profit / (candle range * $2). Periods by entry year.
Usage: python analyze_breakeven_study.py
"""

import json

import numpy as np
import pandas as pd

from analyze_instrument_baseline import load, max_dd
from analyze_price_levels import protocol_matches, sha256
from audit_granularity_ledgers import ensure_audited
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / "Reports" / "breakeven_20261010"
BASELINE = ROOT / "Reports" / "instrument_baseline_20261008" / "runband_instbase_20261008_mnq_1.00.csv"
COST = 1.05
PV = 2.0
GRID = 0.25
PERIODS = (("2010-15", 2010, 2015), ("2016-19", 2016, 2019), ("2020-26", 2020, 2026))
DECIDING = ("2016-19", "2020-26")
BOOT, SEED = 2000, 20261010


def prepare(path):
    d = load(path)
    d["risk"] = d.candle_range * PV
    d["net"] = d.trade_profit - COST
    d["gross_r"] = d.trade_profit / d.risk
    d["net_r"] = d.net / d.risk
    d["year"] = d.entry.dt.year
    return d


def in_period(d, lo, hi):
    return d[(d.year >= lo) & (d.year <= hi)]


def summary(d):
    net = d.net
    return {"trades": len(d), "win%": 100 * (d.trade_profit > 0).mean(), "net_$": net.sum(),
            "PF_net": net[net > 0].sum() / -net[net < 0].sum(), "maxDD_$": max_dd(net.to_numpy()),
            "gross_R": d.gross_r.mean(), "net_R": d.net_r.mean()}


def week_interval(be, ctl):
    """95% interval of (break-even minus control), resampling entry weeks; both runs share most weeks' trades."""
    def by_week(d):
        return d.groupby(d.entry.dt.to_period("W")).agg(usd=("net", "sum"), r=("net_r", "sum"), n=("net", "size"))
    w = by_week(be).join(by_week(ctl), how="outer", lsuffix="_b", rsuffix="_c").fillna(0.0).to_numpy()
    rng = np.random.default_rng(SEED)
    s = w[rng.integers(0, len(w), size=(BOOT, len(w)))].sum(axis=1)   # columns: usd_b r_b n_b usd_c r_c n_c
    d_usd = s[:, 0] - s[:, 3]
    d_r = s[:, 1] / s[:, 2] - s[:, 4] / s[:, 5]
    return np.percentile(d_usd, [2.5, 97.5]), np.percentile(d_r, [2.5, 97.5])


def cut_detail(both, cut):
    """Descriptive only (added after the result): what the baseline does with the trades the stop cuts."""
    out = {}
    bins = [-np.inf, -1 + 1e-9, 0, 1 - 1e-9, 1.5, 2, 3, np.inf]
    names = ["full stop", "-1..0", "0..1", "1..1.5", "1.5..2", "2..3", "3+"]
    peaks = [1 - 1e-9, 1.1, 1.25, 1.5, 2, np.inf]
    print("\nDetail on the cut trades (descriptive, baseline results, R before costs):")
    for lab, lo, hi in PERIODS[1:] + (("2016-26", 2016, 2026),):
        p, c = in_period(both, lo, hi), in_period(cut, lo, hi)
        groups = (("never touched +1R", p[~p.armed]), ("touched +1R, never back at entry", p[p.armed & ~p.index.isin(c.index)]),
                  ("touched +1R, back at entry (cut)", c))
        print(f"  {lab}:")
        for name, g in groups:
            print(f"     {name:34s} {len(g):6,} ({100 * len(g) / len(p):4.1f}%)  mean R {g.gross_r_c.mean():+.3f}  "
                  f"full stop {100 * (g.gross_r_c <= -1).mean():5.1f}%  profit {100 * (g.gross_r_c > 0).mean():5.1f}%")
        g = c.groupby(pd.cut(c.gross_r_c, bins=bins, labels=names), observed=False)
        table = pd.DataFrame({"n": g.size(), "share%": 100 * g.size() / len(c), "sum_R": g.gross_r_c.sum(),
                              "sum_$": g.trade_profit_c.sum()})
        print("     " + table.to_string(float_format=lambda x: f"{x:,.1f}").replace("\n", "\n     "))
        win = c.gross_r_c > 0
        need = 1 / (1 + c.gross_r_c[win].mean())
        moved = pd.to_datetime(c.be_time, format="%Y.%m.%d %H:%M:%S")
        minutes = lambda a, b: ((a - b).dt.total_seconds() / 60).median()
        low_c, low_b = c.mae_money_c / c.risk, c.mae_money / c.risk   # worst point: whole trade / before the cut
        deeper = win & (low_c < low_b - 1e-9)
        out[lab] = {"winners_mean_R": c.gross_r_c[win].mean(), "winners_median_R": c.gross_r_c[win].median(),
                    "recovery_rate": win.mean(), "recovery_rate_for_zero": need,
                    "min_entry_to_touch": minutes(moved, c.entry), "min_touch_to_entry": minutes(c.exit, moved),
                    "min_baseline_holds_on": minutes(c.exit_c, c.exit),
                    "min_to_stop": minutes(c.exit_c[c.gross_r_c <= -1], c.exit[c.gross_r_c <= -1]),
                    "min_to_winning_exit": minutes(c.exit_c[win], c.exit[win]),
                    "recoverers_new_low_after_return_%": 100 * deeper.sum() / win.sum(),
                    "recoverers_new_low_median_R": low_c[deeper].median(), "buckets": table.to_dict("index")}
        o = out[lab]
        print(f"     winners: mean {o['winners_mean_R']:+.2f} R, median {o['winners_median_R']:+.2f} R; "
              f"recovery rate {100 * o['recovery_rate']:.1f}% (zero expectancy needs {100 * need:.1f}%)")
        print(f"     median minutes: entry to +1R touch {o['min_entry_to_touch']:.0f}, touch to back at entry "
              f"{o['min_touch_to_entry']:.0f}, baseline holds on {o['min_baseline_holds_on']:.0f} "
              f"(to the stop {o['min_to_stop']:.0f}, to a winning exit {o['min_to_winning_exit']:.0f})")
        print(f"     recoverers that made a new low after coming back: {o['recoverers_new_low_after_return_%']:.1f}%, "
              f"median low {o['recoverers_new_low_median_R']:+.2f} R")
        g = c.groupby(pd.cut(c.mfe_money / c.risk, peaks, labels=["1.0-1.1", "1.1-1.25", "1.25-1.5", "1.5-2", "2+"]),
                      observed=False)
        peak = pd.DataFrame({"n": g.size(), "full_stop%": 100 * g.apply(lambda x: (x.gross_r_c <= -1).mean()),
                             "mean_R": g.gross_r_c.mean()})
        print("     by highest point before coming back (R):\n     "
              + peak.to_string(float_format=lambda x: f"{x:,.3f}").replace("\n", "\n     "))
    return out


def main():
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    assert protocol_matches(ROOT / manifest["protocol"], manifest["protocol_sha256"]), "protocol changed after the runs"
    jobs = {j["tag"].rsplit("_", 1)[1]: j for j in manifest["jobs"]}
    assert sha256(RUN / jobs["off"]["outputs"][0]) == sha256(BASELINE), "control differs from the baseline ledger"
    print("PASS: control ledger is byte-identical to the saved baseline.")

    frames = {}
    for key, job in jobs.items():
        audited = ensure_audited(RUN, {**job, "mode": "rtl"}, {"symbol": manifest["symbol"], "grid_points": GRID}, PV)
        audit = json.loads((RUN / f"{job['tag']}.ledger_audit.json").read_text(encoding="utf-8"))
        assert audit["recovered_trades"] == 0, (job["tag"], "logger missed trades; the be_time flag would be unknown")
        stats = pd.read_csv(RUN / job["outputs"][1], sep="\t", encoding="utf-16").iloc[0]
        log = (RUN / f"{job['tag']}.tester.log").read_text(encoding="utf-8", errors="replace")
        assert stats.be_failed == 0 and "Breakeven SL modify failed" not in log, (job["tag"], "failed stop moves")
        assert abs(stats.breakeven_at_r - job["breakeven_at_r"]) < 1e-9, (job["tag"], "input flag")
        d = prepare(audited)
        d["armed"] = d.be_time.notna() if "be_time" in d else False
        assert d.armed.sum() == stats.be_moves, (job["tag"], "stop moves vs flagged trades")
        if job["breakeven_at_r"] > 0:   # independent of the new code: the EA's tick-level MFE must say the same
            reached = d.mfe_money >= job["breakeven_at_r"] * d.risk - 1e-9
            assert (d.armed == reached).all(), (job["tag"], "be_time flag disagrees with the logged MFE")
        assert d.entry_time.is_unique
        frames[key] = d
    ctl, be = frames["off"], frames["1r"]
    print("PASS: both ledgers match MT5's deal report (0 trades recovered), 0 failed stop moves, "
          f"{int(be.armed.sum()):,} stops moved to entry; the flag equals 'logged MFE >= 1R' on every trade.\n")

    # ---- paired view: the same trade has the same entry time in both runs
    m = be.merge(ctl, on="entry_time", how="outer", suffixes=("", "_c"), indicator=True)
    both = m[m._merge == "both"].astype({"armed": bool})   # the outer merge left the flag as object
    assert np.allclose(both.candle_range, both.candle_range_c)
    changed = (both.exit_time != both.exit_time_c) | ~np.isclose(both.trade_profit, both.trade_profit_c)
    cut = both[changed]
    assert cut.armed.all() and (cut.trade_profit == 0).all(), "a changed trade is not a break-even exit"
    be_exit = be[be.armed & (be.trade_profit <= 0)]
    assert (be_exit.trade_profit == 0).all(), "a break-even stop filled away from the entry price"
    new = m[m._merge == "left_only"]
    gone = m[m._merge == "right_only"]
    year_c = pd.to_datetime(gone.entry_time, format="%Y.%m.%d %H:%M:%S").dt.year

    pd.set_option("display.width", 250)
    rows, res = [], {}
    for lab, lo, hi in PERIODS + (("all", 2010, 2026),):
        for name, d in (("control", ctl), ("break-even", be)):
            s = summary(in_period(d, lo, hi))
            s["BE_exit%"] = 100 * (in_period(d, lo, hi).armed & (in_period(d, lo, hi).trade_profit == 0)).mean()
            rows.append({"period": lab, "run": name, **s})
            res[f"{lab}_{name}"] = s
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nBreak-even minus control, 95% interval from resampling weeks:")
    for lab, lo, hi in PERIODS:
        usd, r = week_interval(in_period(be, lo, hi), in_period(ctl, lo, hi))
        d_usd = res[f"{lab}_break-even"]["net_$"] - res[f"{lab}_control"]["net_$"]
        d_r = res[f"{lab}_break-even"]["net_R"] - res[f"{lab}_control"]["net_R"]
        res[f"{lab}_diff"] = {"net_$": d_usd, "net_$_ci": list(usd), "net_R": d_r, "net_R_ci": list(r)}
        print(f"  {lab}: net $ {d_usd:+,.0f} [{usd[0]:+,.0f}, {usd[1]:+,.0f}]   avg net R {d_r:+.4f} [{r[0]:+.4f}, {r[1]:+.4f}]")

    print("\nDecision rule: beat the control on net $ AND avg net R in BOTH 2016-19 and 2020-26.")
    ok = all(res[f"{p}_break-even"][k] > res[f"{p}_control"][k] for p in DECIDING for k in ("net_$", "net_R"))
    for p in DECIDING:
        b, c = res[f"{p}_break-even"], res[f"{p}_control"]
        print(f"  {p}: net $ {'better' if b['net_$'] > c['net_$'] else 'worse'}, "
              f"avg net R {'better' if b['net_R'] > c['net_R'] else 'worse'}")
    print(f"  -> {'CANDIDATE' if ok else 'rejected'}")
    res["decision"] = "candidate" if ok else "rejected"

    print("\nBy year (break-even minus control):")
    yr = pd.DataFrame({"trades_c": ctl.groupby("year").size(), "trades_b": be.groupby("year").size(),
                       "net_$_c": ctl.groupby("year").net.sum(), "net_$_b": be.groupby("year").net.sum(),
                       "net_R_c": ctl.groupby("year").net_r.mean(), "net_R_b": be.groupby("year").net_r.mean(),
                       "DD_c": ctl.groupby("year").net.apply(lambda x: max_dd(x.to_numpy())),
                       "DD_b": be.groupby("year").net.apply(lambda x: max_dd(x.to_numpy()))})
    yr["d_$"] = yr["net_$_b"] - yr["net_$_c"]
    yr["d_R"] = yr["net_R_b"] - yr["net_R_c"]
    print(yr.to_string(float_format=lambda x: f"{x:,.3f}"))
    late = yr.loc[2016:2026]
    res["years_2016_26"] = {"n": len(late), "net_$_better": int((late["d_$"] > 0).sum()),
                            "net_R_better": int((late["d_R"] > 0).sum()), "DD_lower": int((late.DD_b < late.DD_c).sum())}
    print(f"2016-26: net $ better in {res['years_2016_26']['net_$_better']}/{len(late)} years, avg net R better in "
          f"{res['years_2016_26']['net_R_better']}/{len(late)}, drawdown lower in {res['years_2016_26']['DD_lower']}/{len(late)}")

    print("\nPaired breakdown (same entry time = same trade; R before costs):")
    for lab, lo, hi in PERIODS:
        b_all, c = in_period(both, lo, hi), in_period(cut, lo, hi)
        n_new, n_gone = in_period(new, lo, hi), gone[(year_c >= lo) & (year_c <= hi)]
        loss, win = c.gross_r_c <= -1, c.gross_r_c > 0
        total = res[f"{lab}_break-even"]["net_$"] - res[f"{lab}_control"]["net_$"]
        parts = -c.trade_profit_c.sum() + n_new.net.sum() - n_gone.net_c.sum()
        assert abs(total - parts) < 1e-6, (lab, total, parts)
        out = {"reached_1R": int(b_all.armed.sum()), "reached_1R_%": 100 * b_all.armed.mean(), "cut": len(c),
               "cut_%_of_reached": 100 * len(c) / b_all.armed.sum(),
               "cut_ctl_full_loss": int(loss.sum()), "cut_ctl_profit": int(win.sum()),
               "cut_ctl_other": int((~loss & ~win).sum()), "cut_ctl_gross_R_mean": c.gross_r_c.mean(),
               "cut_ctl_gross_R_winners": c.gross_r_c[win].mean(), "cut_ctl_$": c.trade_profit_c.sum(),
               "new": len(n_new), "new_net_$": n_new.net.sum(), "new_net_R": n_new.net_r.mean(),
               "new_gross_R": n_new.gross_r.mean(),
               "gone": len(n_gone), "gone_net_$": n_gone.net_c.sum(), "gone_net_R": n_gone.net_r_c.mean()}
        res[f"{lab}_paired"] = out
        print(f"  {lab}: {len(b_all):,} shared trades, {out['reached_1R']:,} touched +1R ({out['reached_1R_%']:.1f}%); "
              f"{len(c):,} of those cut at break-even ({out['cut_%_of_reached']:.1f}%)")
        print(f"     the control's result for the cut trades: {out['cut_ctl_full_loss']:,} full losses, "
              f"{out['cut_ctl_other']:,} smaller losses/flat, {out['cut_ctl_profit']:,} profits "
              f"(avg {out['cut_ctl_gross_R_winners']:+.2f} R); mean {out['cut_ctl_gross_R_mean']:+.3f} R, "
              f"total ${out['cut_ctl_$']:+,.0f}")
        print(f"     -> cutting them changes net $ by {-out['cut_ctl_$']:+,.0f}")
        print(f"     new trades (position freed): {len(n_new):,}, net ${out['new_net_$']:+,.0f}, "
              f"mean R {out['new_gross_R']:+.3f} before / {out['new_net_R']:+.3f} after costs")
        print(f"     control trades no longer taken: {len(n_gone):,}, net ${out['gone_net_$']:+,.0f} "
              f"-> net $ change {-out['gone_net_$']:+,.0f}")
        print(f"     total change {total:+,.0f} = {-out['cut_ctl_$']:+,.0f} {out['new_net_$']:+,.0f} {-out['gone_net_$']:+,.0f}")

    # ---- how much rests on the tester's assumed order of prices inside a minute
    moved = pd.to_datetime(be_exit.be_time, format="%Y.%m.%d %H:%M:%S")
    same_minute = int((moved.dt.floor("min") == be_exit.exit.dt.floor("min")).sum())
    through = int((cut.exit_time == cut.exit_time_c).sum())
    wait = (be_exit.exit - moved).dt.total_seconds() / 60
    res["intrabar"] = {"be_exits": len(be_exit), "same_minute_as_move": same_minute,
                       "same_tick_as_control_stop": through, "median_minutes_move_to_exit": float(wait.median())}
    print(f"\nBreak-even exits: {len(be_exit):,}, all at exactly the entry price. {same_minute} "
          f"({100 * same_minute / len(be_exit):.1f}%) in the same minute as the stop move; median wait "
          f"{wait.median():.0f} minutes. {through} left on the tick that also hit the control's original stop.")
    res["cut_detail"] = cut_detail(both, cut)
    (RUN / "results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
