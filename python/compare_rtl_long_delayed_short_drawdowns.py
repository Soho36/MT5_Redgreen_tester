"""Compare two independent one-MNQ books on common historical session closes."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

from analyze_rtl_failed_breakout_short import calendar
from project_paths import PROJECT_ROOT as ROOT

OUT = ROOT / "Reports/rtl_long_delayed_short_drawdowns_20261107"
REPORTS = ROOT / "Reports"
LONG = REPORTS / "ym_baselines_20261023/runband_ymbase_20261023_rtl_nq_1.00.csv"
SHORT = REPORTS / "rtl_delayed_failed_breakout_20261106/trades_delayed.csv"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    days = calendar()
    days = days[(days >= "2016-01-01") & (days < "2026-10-01")]
    pnl = pd.DataFrame(index=days)
    for name, path, fmt in [("long", LONG, {"sep": "\t", "encoding": "utf-16"}), ("short", SHORT, {})]:
        ledger = pd.read_csv(path, **fmt)
        date = pd.to_datetime(ledger.exit_time).dt.normalize()
        selected = date.between(days[0], days[-1])
        assert date[selected].isin(days).all()
        net = ledger.trade_profit[selected] - 1.05
        pnl[name] = net.groupby(date[selected]).sum().reindex(days, fill_value=0)
        assert np.isclose(pnl[name].sum(), net.sum())
    pnl["combined"] = pnl.long + pnl.short
    rows, episodes = [], []
    for period, p in [("2016-19", pnl.loc[:"2019"]), ("2020-Sep26", pnl.loc["2020":]), ("pooled", pnl)]:
        equity = p.cumsum()
        dd = equity - equity.cummax().clip(lower=0)
        tail = dd[["long","short"]].le(dd[["long","short"]].quantile(.1))
        rows.append(dict(period=period, sessions=len(p), dd_corr=dd.long.corr(dd.short),
                         pnl_corr=p.long.corr(p.short), simultaneous_deep_days=int(tail.all(axis=1).sum()),
                         **{c+"_maxdd": -dd[c].min() for c in p},
                         **{c+"_net": p[c].sum() for c in p}))
        if period == "pooled":
            for c in p:
                trough = dd[c].idxmin()
                before = equity[c].loc[:trough]
                peak = before[before == before.max()].index[-1] if before.max() >= 0 else None
                interval = p.loc[:trough] if peak is None else p.loc[(p.index > peak) & (p.index <= trough)]
                moves = interval.sum()
                assert np.isclose(moves[c], dd.at[trough,c])
                episodes.append(dict(book=c, peak=peak, trough=trough, **moves.to_dict()))
            daily = pd.concat([p.add_suffix("_pnl"), dd.add_suffix("_drawdown")], axis=1)
            daily.to_csv(OUT / "daily.csv", index_label="date", float_format="%.2f")
            fig, (ax, bx) = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True, layout="constrained")
            for c, label, color in [("long","RTL long","#245785"),("short","Delayed RTL short","#b96318")]:
                ax.plot(dd.index, dd[c], lw=1, label=label, color=color)
            bx.plot(dd.index, dd.long, lw=.85, label="RTL long alone", color="#7397b6")
            bx.plot(dd.index, dd.combined, lw=1.0, label="Long + delayed short", color="#187355")
            for axis in (ax,bx):
                axis.grid(axis="y", alpha=.22)
                axis.legend(loc="lower left", frameon=False)
                axis.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
            ax.set_title("Daily closing drawdowns · one MNQ per strategy · $1.05 per round trip")
            fig.savefig(OUT / "drawdowns.png", dpi=150)
            plt.close(fig)
    for name, data in [("summary",rows),("worst_episodes",episodes)]:
        frame = pd.DataFrame(data)
        print(frame.to_string(index=False))
        frame.to_csv(OUT / (name+".csv"), index=False, float_format="%.6f")


if __name__ == "__main__":
    main()
