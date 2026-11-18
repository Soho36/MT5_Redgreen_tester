"""Three volatility questions on the native RTL baseline ledger (one MNQ, $1.05 per trade).

1. Costs: is the weak 2010-15 period explained by fixed costs being a larger share of R?
2. Adaptive size filter: signal-candle risk relative to the recent typical M30 range.
3. Volatility ramp: when recent M30 ranges rise above their longer average, do the
   next sessions go down, and would skipping them help RTL?

Skips here are ledger omissions, not replays: a skipped order can free a later one in MT5.
"""
import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT

SRC = r"F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv"
LEDGER = ROOT / "Reports" / "rtl_midpoint_20261116" / "trades_baseline.csv"
OUT = ROOT / "Reports" / "volatility_regimes_20261119"
COST = 1.05
PT = 2.0                      # $ per point, one MNQ
ERAS = (("2010-15", 2010, 2015), ("2016-19", 2016, 2019), ("2020-26", 2020, 2026))


def era(y):
    for name, a, b in ERAS:
        if a <= y <= b:
            return name


def max_dd(pnl):
    eq = np.cumsum(pnl)
    return float(np.max(np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq)) if len(eq) else 0.0


def load_m30():
    d = pd.read_csv(SRC, sep="\t", usecols=["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"])
    d.columns = ["date", "time", "open", "high", "low", "close"]
    d.index = pd.to_datetime(d["date"] + " " + d["time"], format="%Y.%m.%d %H:%M:%S")
    m = d.resample("30min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    m["range"] = m.high - m.low
    return m


def session_table(m30):
    g = m30.groupby(m30.index.normalize())
    s = pd.DataFrame({"med_range": g.range.median(), "open": g.open.first(), "close": g.close.last()})
    s["prior5"] = s.med_range.rolling(5).median().shift(1)        # known before the session starts
    s["prior60"] = s.med_range.rolling(60).median().shift(1)
    s["ramp"] = s.prior5 / s.prior60
    s["fwd1"] = s.close / s.close.shift(1) - 1                      # this session close-to-close
    s["fwd5"] = s.close.shift(-4) / s.close.shift(1) - 1            # this + next 4 sessions
    s["fwd20"] = s.close.shift(-19) / s.close.shift(1) - 1
    return s


def costs(t):
    t = t.copy()
    t["cost_r"] = COST / t.risk
    rows = []
    for y, g in t.groupby(t.year):
        rows.append({"year": y, "trades": len(g), "median_risk_pts": g.risk.median() / PT,
                     "cost_in_R": g.cost_r.mean(), "gross_R": g.gross_r.mean(), "net_R": g.net_r.mean(),
                     "net_$": g.net.sum()})
    yearly = pd.DataFrame(rows)
    # Counterfactual: every trade pays the 2020-26 median cost-in-R instead of $1.05
    recent_cost_r = t.loc[t.year >= 2020, "cost_r"].median()
    t["net_r_scaled"] = t.gross_r - recent_cost_r
    era_rows = []
    for name, g in t.groupby("era", sort=False):
        era_rows.append({"era": name, "trades": len(g), "cost_in_R": g.cost_r.mean(), "gross_R": g.gross_r.mean(),
                         "net_R": g.net_r.mean(), "net_R_at_2020s_cost": g.net_r_scaled.mean(),
                         "gross_R_ci": ci(g.gross_r.values)})
    return yearly, pd.DataFrame(era_rows), recent_cost_r


def ci(x, n=2000, seed=1):
    rng = np.random.default_rng(seed)
    b = [rng.choice(x, len(x)).mean() for _ in range(n)]
    return f"{np.percentile(b, 2.5):+.4f} to {np.percentile(b, 97.5):+.4f}"


def rel_size(t):
    t = t.copy()
    t["q"] = t.groupby("era").rel.transform(lambda s: pd.qcut(s, 5, labels=False) + 1)
    out = t.groupby(["era", "q"], sort=False).agg(trades=("net", "size"), rel_lo=("rel", "min"), rel_hi=("rel", "max"),
                                                  gross_R=("gross_r", "mean"), net_R=("net_r", "mean"),
                                                  net_usd=("net", "sum")).reset_index()
    return out


def ramp_tables(s, t):
    s = s.dropna(subset=["ramp"]).copy()
    s["era"] = s.index.year.map(era)
    s["bucket"] = pd.cut(s.ramp, [0, 0.8, 1.0, 1.2, 1.5, 2.0, 99], labels=["<0.8", "0.8-1", "1-1.2", "1.2-1.5", "1.5-2", ">2"])
    market = s.groupby(["era", "bucket"], observed=True).agg(sessions=("ramp", "size"),
                                                             next1_pct=("fwd1", lambda x: x.mean() * 100),
                                                             next5_pct=("fwd5", lambda x: x.mean() * 100),
                                                             next20_pct=("fwd20", lambda x: x.mean() * 100),
                                                             next20_up_share=("fwd20", lambda x: (x > 0).mean())).reset_index()
    tt = t.merge(s[["ramp", "bucket"]], left_on="sday", right_index=True, how="left")
    trades = tt.groupby(["era", "bucket"], observed=True).agg(trades=("net", "size"), gross_R=("gross_r", "mean"),
                                                              net_R=("net_r", "mean"), net_usd=("net", "sum")).reset_index()
    return market, trades, tt


def halt_sim(tt, n_random=500, seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    for name, g in tt.groupby("era", sort=False):
        g = g.sort_values("exit_time")
        base_net, base_dd = g.net.sum(), max_dd(g.net.values)
        days = g.sday.unique()
        for thr in (1.2, 1.5, 2.0):
            skip = g.ramp > thr
            kept = g[~skip]
            nd = g.loc[skip, "sday"].nunique()
            # random control: skip the same number of sessions chosen at random
            r_net, r_dd = [], []
            for _ in range(n_random):
                pick = set(rng.choice(days, nd, replace=False))
                k = g[~g.sday.isin(pick)]
                r_net.append(k.net.sum())
                r_dd.append(max_dd(k.net.values))
            rows.append({"era": name, "halt_if_ramp_above": thr, "sessions_skipped": nd,
                         "share_sessions": nd / len(days), "net_base": base_net, "net_halt": kept.net.sum(),
                         "skipped_trades_net": g.loc[skip, "net"].sum(), "dd_base": base_dd,
                         "dd_halt": max_dd(kept.net.values), "random_net_median": np.median(r_net),
                         "random_dd_median": np.median(r_dd),
                         "dd_beats_random_share": float(np.mean(np.array(r_dd) > max_dd(kept.net.values)))})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t = pd.read_csv(LEDGER, parse_dates=["submitted", "entry_time", "exit_time"])
    t["year"] = t.entry_time.dt.year
    t["era"] = t.year.map(era)
    t["sday"] = t.submitted.dt.normalize()

    yearly, eras, rc = costs(t)
    print(f"\n=== 1. Costs (cost per trade ${COST}; 2020-26 median cost = {rc:.4f} R) ===")
    print(yearly.round(4).to_string(index=False))
    print(eras.round(4).to_string(index=False))

    m30 = load_m30()
    s = session_table(m30)
    # typical M30 range of the 20 sessions before the signal's session
    s["typ20"] = s.med_range.rolling(20).median().shift(1)
    t = t.merge(s[["typ20"]], left_on="sday", right_index=True, how="left")
    t["rel"] = (t.risk / PT) / t.typ20
    rs = rel_size(t.dropna(subset=["rel"]))
    print("\n=== 2. Signal risk / typical M30 range of prior 20 sessions, quintiles per era ===")
    print(rs.round(3).to_string(index=False))

    market, trades, tt = ramp_tables(s, t)
    print("\n=== 3a. Ramp = median M30 range of prior 5 sessions / prior 60. Market afterwards ===")
    print(market.round(3).to_string(index=False))
    print("\n=== 3b. RTL trades by ramp bucket ===")
    print(trades.round(4).to_string(index=False))
    hs = halt_sim(tt.dropna(subset=["ramp"]))
    print("\n=== 3c. Halt sessions with ramp above threshold (ledger omission) vs random skips of as many sessions ===")
    print(hs.round(2).to_string(index=False))

    for name, df in (("costs_yearly", yearly), ("costs_eras", eras), ("relative_size", rs),
                     ("ramp_market", market), ("ramp_trades", trades), ("ramp_halt", hs)):
        df.to_csv(OUT / f"{name}.csv", index=False)


if __name__ == "__main__":
    main()
