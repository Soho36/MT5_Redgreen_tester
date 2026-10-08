"""Coarsened NQ (exploratory, 2026-10-08): does NQ behave like ES when its candles span as few ticks as ES's?

Rounds every NQ 1-minute price to the nearest multiple of a per-year grid g = k x 0.25, where k = the NQ/ES
ratio of median M30 range that year (rounded, >= 1). NQ candles then span about as many grid steps as ES
candles. Rounding is monotonic, so high >= open/close >= low still holds. Volumes unchanged.
k was measured from the two continuous files (median M30 range in ticks, NQ / ES per year).

Usage: python build_coarse_nq.py <NQ MT5 csv> <out csv>
"""

import sys

import numpy as np
import pandas as pd

TICK = 0.25
K = {2010: 2, 2011: 2, 2012: 2, 2013: 2, 2014: 2, 2015: 2, 2016: 2, 2017: 3, 2018: 3, 2019: 3,
     2020: 4, 2021: 4, 2022: 4, 2023: 4, 2024: 5, 2025: 5, 2026: 6}


def grid(years):
    """Grid in points for an array of years."""
    return np.vectorize(K.get)(years) * TICK


def main(src, out):
    d = pd.read_csv(src, sep="\t")
    g = grid(d["<DATE>"].str[:4].astype(int).to_numpy())
    for c in ("<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"):
        d[c] = np.round(d[c].to_numpy() / g) * g
    assert (d["<HIGH>"] >= d[["<OPEN>", "<CLOSE>"]].max(axis=1)).all()
    assert (d["<LOW>"] <= d[["<OPEN>", "<CLOSE>"]].min(axis=1)).all()
    d.to_csv(out, sep="\t", index=False, float_format="%.2f")
    print(f"Wrote {len(d):,} bars to {out}")


if __name__ == "__main__":
    main(*sys.argv[1:])
