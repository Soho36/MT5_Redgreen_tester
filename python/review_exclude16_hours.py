"""Is the 16:00-17:00 entry exclusion special? Every one-hour entry exclusion, replayed.

Written on 2026-11-11 for a review of the exclusion studies
(docs/baseline/rtl-vwap/EXCLUDE_16_RESULTS.md, docs/baseline/rtl-open-halves/RESULTS.md).
The minute simulator reproduces every native MT5 trade of normal RTL and GG. Here it
replays both with each one-hour entry window closed in turn (pending orders cancelled,
no new orders, open positions exit normally), which no native study did. The question:
how does closing 16:00-17:00 rank among closing any other hour?
It also bootstraps the native 2026-11-01 runs week by week (exclusion minus original).

After-the-fact diagnostics on reused history; nothing adopted. "Daily DD" is closed-trade
P&L by submission session, as in the studies' Daily DD column. It is not the sampled
intraday equity DD, which needs native equity paths.

Reads
  the checked minute cache of rtl_weekly_engine / verify_rtl_failed_breakout_short
  Reports/rtl_gg_exclude16_20261101/ex16_20261101_*_trades.csv   native originals and exclusions
Writes
  docs/baseline/rtl-open-halves/hour_exclusion_replays.csv             one hour at a time
  docs/baseline/rtl-open-halves/half_hour_exclusion_replays.csv        one half-hour bar at a time, 15:30-17:30

Run:  .\\venv\\Scripts\\python.exe python\\review_exclude16_hours.py     (add "halves" for the second file only)
"""
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

import rtl_weekly_engine as engine
from project_paths import PROJECT_ROOT as ROOT
from verify_rtl_failed_breakout_short import CACHE

NATIVE = ROOT / "Reports/rtl_gg_exclude16_20261101"
OUT = ROOT / "docs/baseline/rtl-open-halves/hour_exclusion_replays.csv"
ERAS = {"2016-19": ("2016-01-01", "2020-01-01"), "2020-26": ("2020-01-01", "2026-10-01"),
        "2016-26": ("2016-01-01", "2026-10-01")}
HOURS = list(range(1, 23))  # the hour starting 01:00 ... 22:00; each closes two half-hour bars
STRATEGY = {"red": "rtl", "green": "gg"}
COST = 1.05
SEED = 20261111
_BARS = _CUT = None


def daily_dd(sessions, net):
    eq = pd.Series(net).groupby(np.asarray(sessions)).sum().sort_index().cumsum().to_numpy()
    return float((np.maximum.accumulate(np.r_[0.0, eq])[1:] - eq).max()) if len(eq) else 0.0


def _init():
    global _BARS, _CUT
    _BARS = engine.load_minutes(cache=CACHE)
    _CUT = engine.load_cutoffs()


def replay(task):
    signal, blocked, label = task
    sim, _ = engine.simulate_m30_ea(_BARS, cutoffs=_CUT, signal=signal, blocked_minutes=blocked)
    session = pd.to_datetime(sim.submitted).dt.normalize()
    net = (sim.exit_price - sim.fill) * 2 - COST
    rows = []
    for era, (a, b) in ERAS.items():
        m = (session >= a) & (session < b)
        rows.append(dict(strategy=STRATEGY[signal], hour=label, era=era, trades=int(m.sum()),
                         net=float(net[m].sum()), daily_dd=daily_dd(session[m], net[m])))
    return rows


def half_hours():
    """Close a single half-hour bar around the cash open (16:30) instead of a whole hour."""
    bars = (930, 960, 990, 1020, 1050)
    tasks = [(signal, (), -1) for signal in STRATEGY] + [(signal, (m,), m) for signal in STRATEGY for m in bars]
    with Pool(5, initializer=_init) as pool:
        r = pd.DataFrame([row for part in pool.map(replay, tasks, chunksize=1) for row in part])
    base = r[r.hour == -1].set_index(["strategy", "era"])
    x = r[r.hour != -1].copy()
    key = list(zip(x.strategy, x.era))
    x["net_change"] = x.net.to_numpy() - base.loc[key, "net"].to_numpy()
    x["dd_change"] = x.daily_dd.to_numpy() - base.loc[key, "daily_dd"].to_numpy()
    x["trades_removed"] = base.loc[key, "trades"].to_numpy() - x.trades.to_numpy()
    x["bar"] = (x.hour // 60).astype(str).str.zfill(2) + ":" + (x.hour % 60).astype(str).str.zfill(2)
    x.drop(columns="hour").to_csv(OUT.with_name("half_hour_exclusion_replays.csv"), index=False)
    for strategy in ("rtl", "gg"):
        print(f"\n=== {strategy.upper()}: closing one half-hour bar for new orders (change against the original)")
        print(x[x.strategy == strategy].pivot(index="bar", columns="era", values=["net_change", "dd_change", "trades_removed"])
              .round(0).astype(int).to_string())


def native(strategy, variant, policy):
    t = pd.read_csv(NATIVE / f"ex16_20261101_{strategy}_{variant}_{policy}_trades.csv", parse_dates=["session", "week_start"])
    return t[t["sample"] == "primary"]


def weekly_bootstrap():
    """Exclusion minus original, native runs, resampling whole weeks."""
    rng = np.random.default_rng(SEED)
    print("\n=== native 2026-11-01 runs: exclusion minus original, 95% interval from resampled weeks")
    for strategy in ("rtl", "gg"):
        for variant in ("base", "vwap"):
            a, s = native(strategy, variant, "all"), native(strategy, variant, "skip")
            for era, (lo, hi) in ERAS.items():
                wa = a[(a.session >= lo) & (a.session < hi)].groupby("week_start").net_dollars.sum()
                ws = s[(s.session >= lo) & (s.session < hi)].groupby("week_start").net_dollars.sum()
                d = ws.sub(wa, fill_value=0.0).to_numpy()
                draws = rng.choice(d, size=(4000, len(d)), replace=True).sum(axis=1)
                ya = a[(a.session >= lo) & (a.session < hi)].groupby("year").net_dollars.sum()
                ys = s[(s.session >= lo) & (s.session < hi)].groupby("year").net_dollars.sum()
                better = int((ys.sub(ya, fill_value=0.0) > 0).sum())
                print(f"{strategy.upper():3s} {variant:4s} {era}: net change {d.sum():+9,.0f}  "
                      f"[{np.percentile(draws, 2.5):+9,.0f}, {np.percentile(draws, 97.5):+9,.0f}]  "
                      f"weeks better {int((d > 0).sum())} / worse {int((d < 0).sum())}  years better {better}/{len(ya)}")


def main():
    tasks = [(signal, () if hour is None else (hour * 60, hour * 60 + 30), -1 if hour is None else hour)
             for signal in STRATEGY for hour in [None] + HOURS]
    with Pool(5, initializer=_init) as pool:
        rows = [r for part in pool.map(replay, tasks, chunksize=1) for r in part]
    r = pd.DataFrame(rows)

    # the simulator must reproduce the native original and the native 16:00-17:00 exclusion
    for strategy in ("rtl", "gg"):
        for hour, policy in ((-1, "all"), (16, "skip")):
            n = native(strategy, "base", policy)
            for era, (lo, hi) in ERAS.items():
                p = n[(n.session >= lo) & (n.session < hi)]
                got = r[(r.strategy == strategy) & (r.hour == hour) & (r.era == era)].iloc[0]
                assert got.trades == len(p) and abs(got.net - p.net_dollars.sum()) < 0.01, (strategy, policy, era)
                assert abs(got.daily_dd - daily_dd(p.session, p.net_dollars.to_numpy())) < 0.01
    print("Simulator reproduces native trades, net and daily DD for RTL and GG, original and 16-17 exclusion.")

    base = r[r.hour == -1].set_index(["strategy", "era"])
    x = r[r.hour != -1].copy()
    key = list(zip(x.strategy, x.era))
    x["net_change"] = x.net.to_numpy() - base.loc[key, "net"].to_numpy()
    x["dd_change"] = x.daily_dd.to_numpy() - base.loc[key, "daily_dd"].to_numpy()
    x["ratio_change"] = (x.net / x.daily_dd).to_numpy() - (base.loc[key, "net"] / base.loc[key, "daily_dd"]).to_numpy()
    x["trades_removed"] = base.loc[key, "trades"].to_numpy() - x.trades.to_numpy()
    for col in ("net_change", "dd_change", "ratio_change"):
        better_high = col != "dd_change"
        x[col + "_rank"] = x.groupby(["strategy", "era"])[col].rank(ascending=not better_high, method="min").astype(int)
    x.to_csv(OUT, index=False)

    pd.set_option("display.width", 250)
    for strategy in ("rtl", "gg"):
        print(f"\n=== {strategy.upper()}: closing one entry hour at a time (change against the original; rank 1 = best of {len(HOURS)})")
        wide = x[x.strategy == strategy].pivot(index="hour", columns="era", values=["net_change", "dd_change"]).round(0).astype(int)
        print(wide.to_string())
        for era in ERAS:
            g = x[(x.strategy == strategy) & (x.era == era)]
            h = g[g.hour == 16].iloc[0]
            print(f"{era}: closing 16-17 changes net {h.net_change:+,.0f} (rank {h.net_change_rank}), daily DD {h.dd_change:+,.0f} "
                  f"(rank {h.dd_change_rank}), net/DD {h.ratio_change:+.2f} (rank {h.ratio_change_rank}); "
                  f"hours that raise net: {int((g.net_change > 0).sum())}/{len(g)}, lower DD: {int((g.dd_change < 0).sum())}/{len(g)}, "
                  f"raise net/DD: {int((g.ratio_change > 0).sum())}/{len(g)}; "
                  f"net change across hours: median {g.net_change.median():+,.0f}, range {g.net_change.min():+,.0f} to {g.net_change.max():+,.0f}")
    weekly_bootstrap()


if __name__ == "__main__":
    if sys.argv[1:] == ["halves"]:
        half_hours()
    else:
        main()
        half_hours()
