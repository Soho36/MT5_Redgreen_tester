"""Plot how the 30-minute candle range of NQ changed from 2010 to 2026.

Builds M30 bars from the continuous 1-minute file and shows, per month:
  top    - monthly OHLC candles (log price scale)
  middle - median and 75th/90th percentile range in points
  bottom - median range as % of the close (removes the price-level growth)
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from project_paths import PROJECT_ROOT as ROOT

SRC = r"F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv"
OUT = ROOT / "Reports" / "m30_range_history_20261119"


def main():
    d = pd.read_csv(SRC, sep="\t", usecols=["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"])
    d.columns = ["date", "time", "open", "high", "low", "close"]
    d.index = pd.to_datetime(d["date"] + " " + d["time"], format="%Y.%m.%d %H:%M:%S")
    m30 = d.resample("30min").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    m30["range"] = m30.high - m30.low
    m30["pct"] = m30.range / m30.close * 100

    g = m30.resample("MS")
    monthly = pd.DataFrame({"median": g.range.median(), "p75": g.range.quantile(0.75),
                            "p90": g.range.quantile(0.90), "pct_median": g.pct.median(),
                            "bars": g.range.size()}).dropna()
    monthly = monthly[monthly.bars >= 100]          # drop partial months
    OUT.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(OUT / "m30_range_monthly.csv")

    ohlc = d.resample("MS").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()

    fig, (a0, a1, a2) = plt.subplots(3, 1, figsize=(13, 11), sharex=True,
                                     gridspec_kw={"height_ratios": [3, 3, 2]})
    up = ohlc.close >= ohlc.open
    width = pd.Timedelta(days=20)
    for mask, col in ((up, "#2E8B57"), (~up, "#D64545")):
        o = ohlc[mask]
        a0.vlines(o.index, o.low, o.high, color=col, lw=0.8)
        a0.bar(o.index, (o.close - o.open).abs().clip(lower=1e-9), bottom=o[["open", "close"]].min(axis=1),
               width=width, color=col, align="center")
    a0.set_yscale("log")
    a0.set_ylabel("NQ price (log)")
    a0.set_title("NQ monthly OHLC and 30-minute candle range, 2010-2026")
    a0.grid(alpha=0.3, which="both")
    a1.fill_between(monthly.index, monthly["median"], monthly.p90, color="#4C78A8", alpha=0.15, label="median to 90th pct")
    a1.plot(monthly.index, monthly.p75, color="#4C78A8", lw=0.8, alpha=0.6, label="75th pct")
    a1.plot(monthly.index, monthly["median"], color="#1F4E79", lw=1.6, label="median")
    a1.set_ylabel("M30 range (points)")
    a1.text(0.99, 0.95, "M30 range by month, all sessions", transform=a1.transAxes, ha="right", va="top")
    a1.legend(loc="upper left", frameon=False)
    a1.grid(alpha=0.3)

    a2.plot(monthly.index, monthly.pct_median, color="#E45756", lw=1.4)
    a2.set_ylabel("median range, % of price")
    a2.grid(alpha=0.3)
    a2.xaxis.set_major_locator(mdates.YearLocator())
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(OUT / "m30_range_history.png", dpi=130)

    yearly = m30.resample("YS").range.median()
    print("median M30 range by year (points):")
    print(yearly.round(1).to_string())


if __name__ == "__main__":
    main()
