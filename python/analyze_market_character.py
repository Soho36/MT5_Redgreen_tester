"""Why does ES differ from NQ? Market character from the 1-minute data, no EA (exploratory, 2026-10-08).

For every M30 bar i with range r = H - L > 0 (session 01:00-23:30, bar i+1 on the same date):
  plain    : enter at the open of bar i+1, barriers entry +/- r (the market-buy control's geometry)
  breakout : if bar i+1 trades at or above H, enter at max(H, that minute's open); stop L, target entry + (entry - L)
             (the RTL geometry, any candle colour; "red" rows keep only red signal bars)
Then, on 1-minute highs/lows until 23:30, which barrier is hit first? Expected R of a pure +/-1R bet = 2p - 1
(p = share hitting the target first). Same-minute double hits count 0.5. In the breakout entry minute only the
target is checked (a low in that minute may predate the entry). Unresolved by 23:30 are excluded (share reported).
No bar-close exit and no costs: this measures the market, not the strategy.
"hold" = after the target is hit first, does that M30 bar close at or above it (RTL exits on bar close).
Also variance ratios and lag-1 autocorrelation of within-day M30 returns (VR < 1 = mean reversion).

NQcoarse = NQ rounded to an ES-like grid (build_coarse_nq.py); its candle size is counted in grid steps.
Usage: python analyze_market_character.py   (writes Reports/market_character_20261008/)
"""

import numpy as np
import pandas as pd

from build_coarse_nq import grid as coarse_grid
from project_paths import PROJECT_ROOT as ROOT

DATA = {"NQ": r"F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv",
        "ES": r"F:\DATABENTO\ES_16_YEARS\MT5_ES_continuous_2010-2026_ohlcv-1m.csv",
        "NQcoarse": r"F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_coarse_2010-2026_ohlcv-1m.csv"}   # build_coarse_nq.py
# price step per bar year: 0.25, or the coarse grid (candle size is counted in these steps)
STEP = {"NQ": lambda y: TICK, "ES": lambda y: TICK, "NQcoarse": lambda y: float(coarse_grid([y])[0])}
END = "2026-07-15"          # same span as the MT5 runs (to 2026-07-14)
CUTOFF = 23 * 60 + 30       # session flatten
TICK = 0.25
OUT = ROOT / "Reports" / "market_character_20261008"
PERIODS = (("2010-15", 2010, 2015), ("2016-19", 2016, 2019), ("2020-26", 2020, 2026))
BINS = [0, 8, 16, 24, 32, 48, 64, 128, 10**6]
LABELS = ["<8", "8-16", "16-24", "24-32", "32-48", "48-64", "64-128", ">128"]


def load_m1(path):
    d = pd.read_csv(path, sep="\t", usecols=["<DATE>", "<TIME>", "<OPEN>", "<HIGH>", "<LOW>", "<CLOSE>"])
    d.columns = ["date", "time", "open", "high", "low", "close"]
    d["ts"] = pd.to_datetime(d["date"] + " " + d["time"], format="%Y.%m.%d %H:%M:%S")
    d = d[d.ts < END]
    d = d[d.ts.dt.hour * 60 + d.ts.dt.minute < CUTOFF].reset_index(drop=True)
    d["day"] = d.ts.dt.normalize()
    return d[["ts", "day", "open", "high", "low", "close"]]


def first_hit(hi, lo, up, dn, start, end, skip_low_first=False):
    """Return (1 target first / 0 stop first / 0.5 same minute / nan neither by end, row of the target hit or -1)."""
    h, l = hi[start:end] >= up, lo[start:end] <= dn
    if skip_low_first and len(l):
        l = l.copy()
        l[0] = False
    iu = np.argmax(h) if h.any() else None
    il = np.argmax(l) if l.any() else None
    if iu is None and il is None:
        return np.nan, -1
    if il is None or (iu is not None and iu < il):
        return 1.0, start + iu
    if iu is None or il < iu:
        return 0.0, -1
    return 0.5, -1


def events(m1, step):
    hi, lo, op = m1.high.to_numpy(), m1.low.to_numpy(), m1.open.to_numpy()
    m1["bar"] = m1.ts.dt.floor("30min")
    bar_close = m1.groupby("bar").close.transform("last").to_numpy()   # close of the M30 bar holding each minute
    hold = lambda res, k, target: float(bar_close[k] >= target) if res == 1.0 else np.nan
    m1["row"] = np.arange(len(m1))
    bars = m1.groupby("bar").agg(day=("day", "first"), o=("open", "first"), h=("high", "max"), l=("low", "min"),
                                 c=("close", "last"), first=("row", "min"), last=("row", "max")).reset_index()
    day_end = m1.groupby("day").row.max() + 1
    rows = []
    b = bars.to_dict("list")
    for i in range(len(bars) - 1):
        if b["day"][i] != b["day"][i + 1] or b["bar"][i + 1] - b["bar"][i] != pd.Timedelta(minutes=30):
            continue
        r = b["h"][i] - b["l"][i]
        if r <= 0:
            continue
        s, e1, end = b["first"][i + 1], b["last"][i + 1] + 1, day_end[b["day"][i]]
        entry = op[s]
        plain, k = first_hit(hi, lo, entry + r, entry - r, s, end)
        plain_hold = hold(plain, k, entry + r)
        brk, brk_hold, touched = np.nan, np.nan, False
        touch = np.nonzero(hi[s:e1] >= b["h"][i])[0]
        if len(touch):
            touched = True
            j = s + touch[0]
            fill = max(b["h"][i], op[j])
            target = fill + (fill - b["l"][i])
            brk, k = first_hit(hi, lo, target, b["l"][i], j, end, skip_low_first=True)
            brk_hold = hold(brk, k, target)
        rows.append((b["bar"][i], r / step(b["bar"][i].year), b["c"][i] < b["o"][i], plain, plain_hold, touched, brk, brk_hold))
    return pd.DataFrame(rows, columns=["bar", "ticks", "red", "plain", "plain_hold", "touched", "breakout",
                                       "breakout_hold"])


def summarise(ev, sym):
    out = []
    for lab, lo_, hi_ in PERIODS:
        p = ev[(ev.bar.dt.year >= lo_) & (ev.bar.dt.year <= hi_)]
        for sel, q in (("all", p), ("red", p[p.red])):
            pl, br = q.plain.dropna(), q.breakout.dropna()
            out.append({"sym": sym, "period": lab, "signals": sel, "n_plain": len(pl),
                        "plain_R": 2 * pl.mean() - 1, "n_break": len(br), "break_R": 2 * br.mean() - 1,
                        "gain": 2 * (br.mean() - pl.mean()),
                        "plain_hold_%": 100 * q.plain_hold.mean(), "break_hold_%": 100 * q.breakout_hold.mean(),
                        "unresolved_plain_%": 100 * q.plain.isna().mean(),
                        "unresolved_break_%": 100 * (q.touched & q.breakout.isna()).sum() / max(q.touched.sum(), 1)})
    return out


def by_ticks(ev, sym):
    p = ev[ev.bar.dt.year >= 2016].copy()
    p["b"] = pd.cut(p.ticks, BINS, labels=LABELS, right=False)
    g = p.groupby("b", observed=False).agg(n=("plain", "count"), plain=("plain", "mean"), brk=("breakout", "mean"),
                                         n_brk=("breakout", "count"), ph=("plain_hold", "mean"),
                                         bh=("breakout_hold", "mean"))
    return pd.DataFrame({"sym": sym, "ticks": g.index, "n_plain": g.n.values, "plain_R": 2 * g.plain.values - 1,
                         "n_break": g.n_brk.values, "break_R": 2 * g.brk.values - 1,
                         "gain": 2 * (g.brk.values - g.plain.values), "plain_hold_%": 100 * g.ph.values,
                         "break_hold_%": 100 * g.bh.values})


def returns_stats(m1, sym):
    bars = m1.groupby(m1.ts.dt.floor("30min")).agg(day=("day", "first"), c=("close", "last"))
    bars["ret"] = np.log(bars.c).groupby(bars.day).diff()
    out = []
    for y, g in bars.groupby(bars.index.year):
        r = g.ret.dropna()
        lag = g.ret.groupby(g.day).shift(1)
        row = {"sym": sym, "year": y, "ac1": r.corr(lag.loc[r.index])}
        for q in (2, 4, 8):
            s = g.ret.groupby(g.day).rolling(q).sum().dropna()
            row[f"VR{q}"] = s.var() / (q * r.var())
        out.append(row)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summ, ticks, rets = [], [], []
    for sym, path in DATA.items():
        m1 = load_m1(path)
        ev = events(m1, STEP[sym])
        ev.to_csv(OUT / f"events_{sym}.csv", index=False)
        print(f"{sym}: {len(ev):,} signal bars")
        summ += summarise(ev, sym)
        ticks.append(by_ticks(ev, sym))
        rets += returns_stats(m1, sym)
    pd.set_option("display.width", 250)
    s = pd.DataFrame(summ)
    t = pd.concat(ticks)
    r = pd.DataFrame(rets)
    for name, df in (("summary", s), ("by_ticks", t), ("returns", r)):
        df.to_csv(OUT / f"{name}.csv", index=False)
    f = lambda x: f"{x:+.3f}"
    print("\nFirst-passage +/-1R (expected R = 2p - 1), before costs:\n" + s.to_string(index=False, float_format=f))
    print("\n2016-26 by signal-candle ticks (all colours):\n" + t.to_string(index=False, float_format=f))
    print("\nWithin-day M30 returns: lag-1 autocorrelation and variance ratios:\n"
          + r.pivot(index="year", columns="sym", values=["ac1", "VR2", "VR4", "VR8"]).to_string(float_format=f))


if __name__ == "__main__":
    main()
