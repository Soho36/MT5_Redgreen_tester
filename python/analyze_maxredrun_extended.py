"""Analyse the MaxRedRun check on the extended test period (protocol: prepare_maxredrun_extended.py).

Checks each ledger against its MT5 stats and that trades entered before 2026-07-14 reproduce the original test
ledgers. Then compares off / cap 1 / cap 3 on the original test window, the new slice and the extended test.
Net = gross - $1.05 per trade (the original study used $1); R = profit / (signal range x $2); DD = net, trade by trade.
Usage: python analyze_maxredrun_extended.py
"""

import numpy as np
import pandas as pd

from analyze_instrument_baseline import COST, load, max_dd, summary
from analyze_signal_colour import edge_over_control
from prepare_maxredrun_extended import CAPS, STUDY
from project_paths import PROJECT_ROOT as ROOT

PV = 2.0
SPLIT = pd.Timestamp("2026-07-14")     # the original test ended here (ToDate=2026.07.14)
ORIGINAL = {0: ROOT / "Reports" / "maxredrun_clean_20261001" / "runband_mrr_clean_20261001_recent_cap0_1.00.csv",
            1: ROOT / "Reports" / "maxredrun_clean_20261001" / "runband_mrr_clean_20261001_recent_cap1_1.00.csv",
            3: ROOT / "Reports" / "rr_clean_20261001" / "runband_rrclean_20261001_recent_1p00_1.00.csv"}
WINDOWS = (("original test, 2020-01-02 to 2026-07-13", lambda d: d[d.entry < SPLIT]),
           ("NEW slice, 2026-07-14 to 2026-10-01", lambda d: d[d.entry >= SPLIT]),
           ("extended test, 2020-01-02 to 2026-10-01", lambda d: d))


def lab(cap):
    return "off" if cap == 0 else f"cap {cap}"


def load_run(cap):
    path = STUDY / f"runband_mrrext_20261013_cap{cap}_1.00.csv"
    d = load(path)
    s = pd.read_csv(path.with_name(path.stem + "_stats.csv"), sep="\t", encoding="utf-16").iloc[0]
    assert len(d) == int(s.trades) and abs(d.trade_profit.sum() - s.net_profit) < 1e-6, (cap, "MT5 stats")
    assert int(s.max_red_run) == cap, (cap, "cap flag")
    return d


def same(a, b):
    return len(a) == len(b) and (a.entry_time.values == b.entry_time.values).all() \
        and np.allclose(a.trade_profit, b.trade_profit)


def daily_net(d):
    return (d.trade_profit - COST).groupby(d.exit.dt.normalize()).sum()


def net_difference(a, b, rng):
    """Net $ of a minus b and its 95% interval, resampling exit days."""
    x = pd.concat([daily_net(a), daily_net(b)], axis=1, keys=["a", "b"], sort=True).fillna(0.0)
    diff = (x.a - x.b).to_numpy()
    idx = rng.integers(0, len(diff), (4000, len(diff)))
    return diff.sum(), *np.percentile(diff[idx].sum(1), [2.5, 97.5]), len(diff)


def main():
    runs = {c: load_run(c) for c in CAPS}
    print(f"{len(runs)} runs reconcile with MT5 stats; caps match. Data ends {max(d.exit.max() for d in runs.values())}.")
    print("Trades before 2026-07-14 reproduce the original test ledgers:",
          {lab(c): same(runs[c][runs[c].entry < SPLIT], load(ORIGINAL[c])) for c in CAPS})
    pd.set_option("display.width", 250)
    rng = np.random.default_rng(1)

    for title, cut in WINDOWS:
        rows = []
        for c in CAPS:
            s = summary(cut(runs[c]), PV)
            rows.append({"run": lab(c), "trades": s["trades"], "win%": s["win%"], "gross_$": cut(runs[c]).trade_profit.sum(),
                         "PF_gross": s["PF_gross"], "net_$": s["net_$"], "PF_net": s["PF_net"], "netDD_$": s["maxDD_$"],
                         "net/DD": s["net_$"] / s["maxDD_$"], "net_R": s["net_R"]})
        print(f"\n{title}\n" + pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
        for c in CAPS[1:]:
            d, lo, hi, n = net_difference(cut(runs[c]), cut(runs[0]), rng)
            e, elo, ehi = edge_over_control(cut(runs[c]), cut(runs[0]), PV, rng)
            print(f"  {lab(c)} minus off: net ${d:+,.0f} [{lo:+,.0f}, {hi:+,.0f}] over {n} days;"
                  f" mean gross R {e:+.3f} [{elo:+.3f}, {ehi:+.3f}]")

    print("\nBy entry year, off vs cap 3 (net $, net PF, net DD):")
    better = {"net": 0, "pf": 0, "dd": 0}
    years = sorted(runs[0].entry.dt.year.unique())
    for y in years:
        a, b = (summary(runs[c][runs[c].entry.dt.year == y], PV) for c in (0, 3))
        better["net"] += b["net_$"] > a["net_$"]; better["pf"] += b["PF_net"] > a["PF_net"]; better["dd"] += b["maxDD_$"] < a["maxDD_$"]
        print(f"  {y}: off {a['net_$']:>8,.0f} {a['PF_net']:.3f} {a['maxDD_$']:>6,.0f}   cap 3 {b['net_$']:>8,.0f} {b['PF_net']:.3f}"
              f" {b['maxDD_$']:>6,.0f}   net diff {b['net_$'] - a['net_$']:>+7,.0f}")
    print(f"  cap 3 better in {better['net']}/{len(years)} years on net $, {better['pf']}/{len(years)} on net PF,"
          f" {better['dd']}/{len(years)} on DD")

    print("\nThe trades the cap is meant to remove: signals after more than 3 reds, in the off ledger (mean gross R):")
    off = runs[0].assign(r=runs[0].trade_profit / (runs[0].candle_range * PV))
    for title, cut in WINDOWS[:2]:
        p = cut(off)
        deep, rest = p[p.red_run > 3], p[p.red_run <= 3]
        boot = [deep.r.sample(len(deep), replace=True, random_state=i).mean() for i in range(1000)]
        print(f"  {title}: run > 3: {len(deep):>5} trades, {deep.r.mean():+.3f} [{np.percentile(boot, 2.5):+.3f},"
              f" {np.percentile(boot, 97.5):+.3f}], net ${(deep.trade_profit - COST).sum():+,.0f};"
              f" run <= 3: {len(rest):>5} trades, {rest.r.mean():+.3f}")
    by_year = off[off.red_run > 3].groupby(off.entry.dt.year).agg(trades=("r", "size"), mean_r=("r", "mean"),
                                                                 net=("trade_profit", lambda x: (x - COST).sum()))
    print(by_year.to_string(float_format=lambda x: f"{x:+,.3f}"))


if __name__ == "__main__":
    main()
