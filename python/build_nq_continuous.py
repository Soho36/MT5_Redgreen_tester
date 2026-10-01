"""Build a continuous NQ 1-minute series for MT5 import from a Databento NQ.FUT DBN file.

Conventions (see docs/DATA_BUILD.md):
- Outright NQ contracts only (calendar spreads dropped). Contracts are keyed by
  instrument_id: Databento's one-digit-year names (NQM0) repeat every decade.
- Clock: America/Chicago (US DST) + 8 h, so a normal Globex session is 01:00-24:00
  on one calendar date, every year, with no DST shift.
- Roll: each session date trades the contract with the highest volume on the
  PREVIOUS session date (known in advance), never rolling back to an earlier expiry.
- Prices raw (no back-adjustment). Roll dates and contracts saved in a side file.
- Bars at 00:00-00:59 are dropped: they are the previous session's thin tail after
  16:00 Chicago (traded until ~16:30 before 2016) and would otherwise create
  next-date and "Saturday" fragments. Every session then starts at 01:00.

Usage: python build_nq_continuous.py <file.dbn> <out_dir>
Writes <out_dir>/MT5_NQ_continuous_2010-2026_ohlcv-1m.csv (MT5 bar import format)
and <out_dir>/MT5_NQ_continuous_2010-2026_rolls.csv.
"""

import sys
from pathlib import Path

import databento as db
import pandas as pd

STEM = "MT5_NQ_continuous_2010-2026"
SPREAD = 1   # MT5 <SPREAD> column, same as the earlier converter


def load(dbn):
    df = db.DBNStore.from_file(dbn).to_df(map_symbols=True, pretty_ts=True, price_type="float")
    df = df[df["symbol"].str.fullmatch(r"NQ[FGHJKMNQUVXZ]\d{1,2}")]
    ts = df.index.tz_convert("America/Chicago").tz_localize(None) + pd.Timedelta(hours=8)
    df = df.reset_index(drop=True).assign(ts=ts.values)
    tail = df["ts"].dt.hour == 0
    print(f"Dropping {int(tail.sum()):,} post-close tail rows (00:00-00:59, all contracts)")
    df = df[~tail]
    df["date"] = df["ts"].dt.normalize()
    return df[["ts", "date", "instrument_id", "symbol", "open", "high", "low", "close", "volume"]]


def choose_contracts(df):
    """Per date: previous date's highest-volume contract, never an earlier expiry."""
    expiry_rank = df.groupby("instrument_id")["ts"].max().rank(method="first")   # later last bar = later expiry
    vol = df.groupby(["date", "instrument_id"])["volume"].sum().reset_index()
    leader = vol.sort_values(["date", "volume"], ascending=[True, False]).drop_duplicates("date")
    leader = leader.set_index("date")["instrument_id"]
    dates = leader.index
    chosen, current = {}, None
    for i, d in enumerate(dates):
        candidate = leader.iloc[i - 1] if i > 0 else leader.iloc[0]
        if current is None or expiry_rank[candidate] > expiry_rank[current]:
            current = candidate
        chosen[d] = current
    return pd.Series(chosen, name="instrument_id")


def main(dbn, out_dir):
    out_dir = Path(out_dir)
    df = load(dbn)
    print(f"Outright 1-minute rows: {len(df):,}")
    chosen = choose_contracts(df)
    keep = df.merge(chosen.rename_axis("date").reset_index(), on=["date", "instrument_id"])
    keep = keep.sort_values("ts")
    assert keep["ts"].is_unique, "duplicate minutes after contract selection"

    names = df.drop_duplicates("instrument_id").set_index("instrument_id")["symbol"]
    first_day = df.groupby("instrument_id")["date"].min()
    rolls = chosen[chosen != chosen.shift()].rename_axis("date").reset_index()
    rolls["symbol"] = rolls["instrument_id"].map(names)
    rolls["contract_first_seen"] = rolls["instrument_id"].map(first_day).dt.date
    rolls["date"] = rolls["date"].dt.date
    rolls.to_csv(out_dir / f"{STEM}_rolls.csv", index=False)

    out = pd.DataFrame({
        "<DATE>": keep["ts"].dt.strftime("%Y.%m.%d"), "<TIME>": keep["ts"].dt.strftime("%H:%M:%S"),
        "<OPEN>": keep["open"], "<HIGH>": keep["high"], "<LOW>": keep["low"], "<CLOSE>": keep["close"],
        "<TICKVOL>": keep["volume"], "<VOL>": keep["volume"], "<SPREAD>": SPREAD})
    out.to_csv(out_dir / f"{STEM}_ohlcv-1m.csv", sep="\t", index=False, float_format="%.2f")
    print(f"Wrote {len(out):,} bars, {keep['date'].nunique():,} session dates, {len(rolls)} contract periods")
    print(f"Range {out['<DATE>'].iloc[0]} {out['<TIME>'].iloc[0]} -> {out['<DATE>'].iloc[-1]} {out['<TIME>'].iloc[-1]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
