"""Q20 pre-trade check: the MT5 classify-only log (LimitMode=1, no orders) must be reproduced bar by bar by
python/trendline_limit.py (built on the frozen Q14 line code): status, line value, limit, stop, anchors, ATR
and line counts. Also checks which bars were logged (eligible bars) and writes outcome-free counts.

Usage: verify_trendline_limit.py [tag]
"""
import json
import re
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

from analyze_level_visit import M30
from analyze_price_levels import PERIODS, ROOT, sha256
from level_visit import bar_frame, swing_lows
from trend_regimes import ROLLS
from trendline_limit import bar_order
from verify_location_validation import read_rows

RUN = ROOT / "Reports" / "trendlines" / "trendline_limit_20261005"
END = pd.Timestamp("2026-07-14")
LINE_TOL = 1e-6
_B, _PIV = None, None


def load_log(tag):
    g = pd.DataFrame(read_rows(RUN / f"{tag}_limit.csv"))
    g["bar_time"] = pd.to_datetime(g.bar_time, format="%Y.%m.%d %H:%M:%S")
    for c in ("anchor1_time", "anchor2_time"):
        g[c] = pd.to_datetime(g[c].replace("", np.nan), format="%Y.%m.%d %H:%M:%S")
    for c in ("open", "ask", "bid", "line", "limit", "stop", "atr"):
        g[c] = g[c].astype(float)
    for c in ("known_pivots", "lines_armed", "lines_below"):
        g[c] = g[c].astype(int)
    assert g.bar_time.is_unique
    return g


def bars():
    return bar_frame(pd.read_csv(M30, index_col=0, parse_dates=[0]), pd.read_csv(ROLLS))


def _init():
    global _B, _PIV
    _B = bars()
    _PIV = swing_lows(_B.low.to_numpy(), _B.contract.to_numpy(), 5)


def _classify(chunk):
    out = []
    for t, ask in chunk:
        status, info = bar_order(_B, t, _PIV, ask=ask)
        out.append(dict(t=t, status=status, **info))
    return out


def early_closes():
    text = (RUN / "early_closes.mqh").read_text(encoding="utf-8")
    dates = re.search(r"EC_DATE\[EC_COUNT\] = \{([^}]*)\}", text).group(1).split(",")
    mins = re.search(r"EC_FLAT_MIN\[EC_COUNT\] = \{([^}]*)\}", text).group(1).split(",")
    return {pd.Timestamp(str(d.strip())): int(m) for d, m in zip(dates, mins)}


def eligible_times(b, first):
    """Bars the EA should log: inside the enabled windows (01:00-23:30) and before the flatten cutoff."""
    ec = early_closes()
    idx = b.index[(b.index >= first) & (b.index < END)]
    minutes = idx.hour * 60 + idx.minute
    cutoff = np.array([ec.get(d, 23 * 60 + 30) for d in idx.normalize()])
    return idx[(minutes >= 60) & (minutes < 23 * 60 + 30) & (minutes < cutoff)]


def period_of(times):
    p = pd.Series("other", index=times)
    for name, (lo, hi) in PERIODS.items():
        p[(times >= pd.Timestamp(lo)) & (times < pd.Timestamp(hi))] = name
    p[times < pd.Timestamp("2016-01-01")] = "early_2010_15"
    return p.to_numpy()


def counts(m, b):
    """Outcome-free counts: statuses, delta distribution and how often bar t's range reaches the limit."""
    low = b.low.to_numpy()
    out = {}
    for period, f in m.groupby("period"):
        o = f[f.status_ea == "order"]
        t = o.t.to_numpy()
        # Bars are bid prices and the tester spread is one tick: a buy limit fills when ask <= limit,
        # i.e. bid low <= limit - spread. "touch" = bid low reaches the limit; "fillable" adds the spread.
        spread = (o.ask - o.bid).to_numpy()
        touch = low[t] <= o.limit_ea.to_numpy()
        through = low[t] <= o.limit_ea.to_numpy() - spread
        lines = o.anchor1_time_ea.astype(str) + "|" + o.anchor2_time_ea.astype(str)
        out[period] = dict(eligible_bars=len(f), status=f.status_ea.value_counts().to_dict(),
                           order_share=round(len(o) / len(f), 4), distinct_lines=int(lines.nunique()),
                           delta_quantiles={str(q): round(float(o.delta.quantile(q)), 3)
                                            for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
                           touch_bars=int(touch.sum()), touch_share=round(float(touch.mean()), 4),
                           fillable_bars=int(through.sum()), fillable_share=round(float(through.mean()), 4),
                           lines_touched=int(lines[touch].nunique()),
                           stop_distance_points_median=round(float((o.limit_ea - o.stop_ea).median()), 2))
    return out


def main(tag="trendline_limit_20261005_classify"):
    g = load_log(tag)
    b = bars()
    pos = pd.Series(np.arange(len(b)), index=b.index)
    missing_in_bars = int((~g.bar_time.isin(b.index)).sum())
    assert missing_in_bars == 0
    expected = eligible_times(b, g.bar_time.min())
    extra, absent = g.bar_time[~g.bar_time.isin(expected)], expected[~expected.isin(g.bar_time)]
    g["t"] = pos.reindex(g.bar_time).to_numpy()
    jobs = list(zip(g.t.tolist(), g.ask.tolist()))
    chunks = [jobs[k:k + 2000] for k in range(0, len(jobs), 2000)]
    with Pool(8, initializer=_init) as pool:
        py = pd.DataFrame([r for chunk in pool.map(_classify, chunks) for r in chunk])
    times = b.index.to_numpy()
    for c in ("anchor1", "anchor2"):
        has = py[c].notna()
        py[f"{c}_time"] = pd.NaT
        py.loc[has, f"{c}_time"] = times[py.loc[has, c].astype(int).to_numpy()]
    m = g.merge(py, on="t", suffixes=("_ea", "_py"), validate="one_to_one")
    m["period"] = period_of(pd.DatetimeIndex(m.bar_time))
    same_status = m.status_ea == m.status_py
    both = same_status & (m.status_ea == "order")
    avail = m.atr_py.notna() & same_status
    checks = dict(
        line=(m.loc[both, "line_ea"] - m.loc[both, "line_py"]).abs() <= LINE_TOL,
        limit=m.loc[both, "limit_ea"] == m.loc[both, "limit_py"],
        stop=m.loc[both, "stop_ea"] == m.loc[both, "stop_py"],
        anchors=(m.loc[both, "anchor1_time_ea"] == m.loc[both, "anchor1_time_py"]) &
                (m.loc[both, "anchor2_time_ea"] == m.loc[both, "anchor2_time_py"]),
        known=m.loc[avail, "known_pivots_ea"] == m.loc[avail, "known_pivots_py"],
        armed=m.loc[avail, "lines_armed_ea"] == m.loc[avail, "lines_armed_py"])
    below = avail & m.lines_below_py.notna()
    checks["below"] = m.loc[below, "lines_below_ea"] == m.loc[below, "lines_below_py"]
    bad = ~same_status
    for ok in checks.values():
        bad.loc[ok.index[~ok.to_numpy()]] = True
    atr_diff = (m.loc[avail, "atr_ea"] - m.loc[avail, "atr_py"]).abs()
    line_diff = (m.loc[both, "line_ea"] - m.loc[both, "line_py"]).abs()
    result = dict(
        log_rows=len(g), first_bar=str(g.bar_time.min()), last_bar=str(g.bar_time.max()),
        eligible_expected=len(expected), logged_not_eligible=len(extra), eligible_not_logged=len(absent),
        not_eligible_examples=[str(x) for x in extra.head(10)], not_logged_examples=[str(x) for x in absent[:10]],
        ask_minus_open=json.loads((g.ask - g.open).round(2).value_counts().to_json()),
        open_ne_bid=int((g.open != g.bid).sum()),
        status_matches=int(same_status.sum()), status_mismatches=int((~same_status).sum()),
        orders_ea=int((m.status_ea == "order").sum()), orders_py=int((m.status_py == "order").sum()),
        field_mismatches={k: int((~v).sum()) for k, v in checks.items()},
        field_compared={k: int(len(v)) for k, v in checks.items()},
        total_mismatched_rows=int(bad.sum()),
        max_line_abs_diff=float(line_diff.max()) if len(line_diff) else None,
        max_atr_abs_diff=float(atr_diff.max()), crosstab=json.loads(pd.crosstab(m.status_py, m.status_ea).to_json()),
        log_sha256=sha256(RUN / f"{tag}_limit.csv"))
    (RUN / f"{tag}_verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    m[bad].to_csv(RUN / f"{tag}_mismatches.csv", index=False)
    (RUN / f"{tag}_counts.json").write_text(json.dumps(counts(m, b), indent=2), encoding="utf-8")
    m[["bar_time", "period", "status_ea", "line_ea", "limit_ea", "stop_ea", "atr_ea", "anchor1_time_ea",
       "anchor2_time_ea", "delta", "retests", "slope_a", "bars_since_anchor2", "anchor_sep", "lines_armed_ea"]] \
        .to_csv(RUN / f"{tag}_bars.csv", index=False)
    print(json.dumps({k: v for k, v in result.items() if k != "crosstab"}, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
