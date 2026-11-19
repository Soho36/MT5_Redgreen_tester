"""Is MES today where NQ was in 2010-15? Cost share, candle size in ticks and gross R per year,
plus cost floors on the MES ledger (omission). Uses the cap-0 RTL ledgers from the cross study."""
import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT

R = ROOT / "Reports/rtl_vwap_cross_20261027"
COST, TICK = 1.05, 0.25
ERAS = (("2010-15", 2010, 2015), ("2016-19", 2016, 2019), ("2020-26", 2020, 2026))


def load(sym):
    t = pd.read_csv(R / f"trades_{sym}.csv", parse_dates=["entry_time", "exit_time"],
                    usecols=["entry_time", "exit_time", "trade_profit", "candle_range", "initial_risk_dollars"])
    t["risk"] = t.initial_risk_dollars
    t["ticks"] = t.candle_range / TICK
    t["gross_r"] = t.trade_profit / t.risk
    t["cost_r"] = COST / t.risk
    t["net"] = t.trade_profit - COST
    t["year"] = t.entry_time.dt.year
    return t.sort_values("exit_time")


def dd(x):
    e = np.cumsum(x)
    return float((np.maximum.accumulate(np.r_[0, e])[1:] - e).max()) if len(e) else 0.0


def main():
    led = {"NQ": load("NQ"), "ES": load("ES")}
    for sym, t in led.items():
        g = t.groupby("year")
        print(f"\n{sym} by year")
        print(pd.DataFrame({"median_ticks": g.ticks.median(), "cost_R": g.cost_r.mean(), "gross_R": g.gross_r.mean(),
                            "net_R": g.gross_r.mean() - g.cost_r.mean(), "net_usd": g.net.sum()}).round(3).to_string())
    es = led["ES"]
    print("\nMES floors (ledger omission)")
    for label, min_pts in (("none", 0), ("cost<=10% of risk (>=2.25 pts)", 2.25), (">=21 ticks, as NQ floor10", 5.25)):
        for era, a, b in ERAS:
            k = es[es.year.between(a, b) & (es.candle_range >= min_pts)]
            print(f"  {label:32s} {era}: trades {len(k):5d} gross_R {k.gross_r.mean():+.4f} "
                  f"net_R {(k.gross_r - k.cost_r).mean():+.4f} net ${k.net.sum():8.0f} DD ${dd(k.net.values):6.0f}")
    bins = [0, 8, 12, 16, 24, 32, 48, 64, 128, np.inf]
    for sym, t in led.items():
        t = t.assign(b=pd.cut(t.ticks, bins, right=False))
        print(f"\n{sym} gross R by signal size in ticks")
        print(t.groupby("b", observed=True).agg(trades=("gross_r", "size"), gross_R=("gross_r", "mean")).round(4).to_string())


if __name__ == "__main__":
    main()
