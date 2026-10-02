"""Independent, lagged daily labels from the existing continuous minute series."""
from pathlib import Path
import pandas as pd

SOURCE = Path(r"F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv")
ROLLS = SOURCE.with_name("MT5_NQ_continuous_2010-2026_rolls.csv")
FAST = (40, 50, 60)
VARIANTS = {"baseline": (1., 1.), "mild": (1.25, .75),
            "strong": (1.5, .75), "bull_only": (1.5, 1.),
            "bear_only": (1., .75), "reversed": (.75, 1.5)}


def label_daily(daily):
    """Rows are trading dates; every feature is shifted one completed date."""
    out = daily.copy().sort_index()
    out["previous_date"] = out.index.to_series().shift(1)
    out["previous_close"] = out["close"].shift(1)
    out["sma200"] = out["close"].rolling(200, min_periods=200).mean().shift(1)
    for n in FAST:
        out[f"sma{n}"] = out["close"].rolling(n, min_periods=n).mean().shift(1)
        regime = pd.Series("neutral", index=out.index)
        regime[(out.previous_close > out.sma200) & (out[f"sma{n}"] > out.sma200)] = "bull"
        regime[(out.previous_close < out.sma200) & (out[f"sma{n}"] < out.sma200)] = "bear"
        regime[out.sma200.isna()] = "warmup"
        out[f"regime{n}"] = regime
    return out


def build_reference(destination):
    parts = []
    for chunk in pd.read_csv(SOURCE, sep="\t", usecols=["<DATE>", "<TIME>", "<CLOSE>"], chunksize=500000):
        chunk = chunk[chunk["<TIME>"] >= "01:00:00"]
        parts.append(chunk.groupby("<DATE>")["<CLOSE>"].last())
    closes = pd.concat(parts).groupby(level=0).last()
    daily = closes.to_frame("close")
    daily.index = pd.to_datetime(daily.index, format="%Y.%m.%d")
    daily.index.name = "date"
    result = label_daily(daily)
    result.to_csv(destination, float_format="%.10f")
    return result


def build_m30_reference(destination):
    parts=[]
    for chunk in pd.read_csv(SOURCE,sep="\t",usecols=["<DATE>","<TIME>","<OPEN>","<HIGH>","<LOW>","<CLOSE>"],chunksize=500000):
        chunk=chunk[chunk["<TIME>"]>="01:00:00"].copy()
        chunk["bar_time"]=pd.to_datetime(chunk["<DATE>"]+" "+chunk["<TIME>"],format="%Y.%m.%d %H:%M:%S").dt.floor("30min")
        parts.append(chunk.groupby("bar_time").agg({"<OPEN>":"first","<HIGH>":"max","<LOW>":"min","<CLOSE>":"last"}))
    bars=pd.concat(parts).groupby(level=0).agg({"<OPEN>":"first","<HIGH>":"max","<LOW>":"min","<CLOSE>":"last"})
    bars.columns=["open","high","low","close"]
    bars.to_csv(destination)
    return bars
