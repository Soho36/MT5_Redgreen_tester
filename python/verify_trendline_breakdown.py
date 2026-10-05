"""Q21 pre-trade check: the MT5 classify-only log (BreakMode=1, no orders) must be reproduced bar by bar by
python/trendline_breakdown.py (built on the frozen Q14/Q20 line code): status, bar s, line value, entry, stop,
anchors, ATR, line counts, s colour and contract. Also checks which bars were logged (eligible bars) and writes
outcome-free counts.

Usage: verify_trendline_breakdown.py [job] [depth_a]   (default: classify 0.0; S1: classify_s1 0.5)
"""
import json
import re
import sys
from functools import partial
from multiprocessing import Pool

import numpy as np
import pandas as pd

from analyze_level_visit import M30
from analyze_price_levels import ROOT, sha256
from level_visit import bar_frame, swing_lows

from trend_regimes import ROLLS
from trendline_breakdown import line_states, resolve, run_spent
from verify_location_validation import read_rows
from verify_trendline_limit import period_of

RUN = ROOT / "Reports" / "trendlines" / "trendline_breakdown_20261006"
STEM = "trendline_breakdown_20261006"
END = pd.Timestamp("2026-07-14")
LINE_TOL = 1e-6
_B, _PIV = None, None


def load_log(tag):
    g = pd.DataFrame(read_rows(RUN / f"{tag}_breakdown.csv"))
    for c in ("bar_time", "s_time", "anchor1_time", "anchor2_time"):
        g[c] = pd.to_datetime(g[c].replace("", np.nan), format="%Y.%m.%d %H:%M:%S")
    for c in ("open", "ask", "bid", "line", "entry", "stop", "atr"):
        g[c] = g[c].astype(float)
    for c in ("known_pivots", "lines_armed", "lines_live", "lines_broken", "s_red", "same_contract"):
        g[c] = g[c].astype(int)
    assert g.bar_time.is_unique
    return g


def bars():
    return bar_frame(pd.read_csv(M30, index_col=0, parse_dates=[0]), pd.read_csv(ROLLS))


def _init():
    global _B, _PIV
    _B = bars()
    _PIV = swing_lows(_B.low.to_numpy(), _B.contract.to_numpy(), 5)


def _states(depth_a, chunk):
    """Pure per-bar line states for bars s in chunk (spending is applied afterwards, in bar order)."""
    return [(s, line_states(_B, s, _PIV, depth_a)) for s in chunk]


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


def counts(m):
    """Outcome-free counts per period: statuses, signals, lines spent and the C1/C2 bar sets."""
    out = {}
    for period, f in m.groupby("period"):
        signal = f.status_ea.isin(["order", "gap_below"])
        broke = f.status_ea.isin(["order", "gap_below", "not_red"])
        lines = f.anchor1_time_ea.astype(str) + "|" + f.anchor2_time_ea.astype(str)
        o = f[f.status_ea == "order"]
        avail = ~f.status_ea.isin(["missing_history", "contract_roll", "invalid_atr"])
        out[period] = dict(
            eligible_bars=len(f), status=f.status_ea.value_counts().to_dict(),
            breakdown_bars=int(broke.sum()), red_signals=int(signal.sum()), orders=len(o),
            gap_skips=int((f.status_ea == "gap_below").sum()),
            distinct_signal_lines=int(lines[signal].nunique()),
            c1_bars=int((avail & (f.lines_armed_ea > 0) & (f.s_red_ea == 1)).sum()),
            c2_bars=int(((f.s_red_ea == 1) & (f.same_contract_ea == 1)).sum()),
            risk_points_median=round(float((o.stop_ea - o.entry_ea).median()), 2) if len(o) else None,
            risk_a_median=round(float(o.range_a.median()), 3) if len(o) else None,
            depth_a_median=round(float(o.depth_a.median()), 3) if len(o) else None,
            opens_above_share=round(float(o.opens_above.astype(bool).mean()), 3) if len(o) else None)
    return out


def main(job="classify", depth_a="0.0"):
    depth_a = float(depth_a)
    tag = f"{STEM}_{job}"
    g = load_log(tag)
    b = bars()
    pos = pd.Series(np.arange(len(b)), index=b.index)
    assert g.bar_time.isin(b.index).all()
    expected = eligible_times(b, g.bar_time.min())
    extra, absent = g.bar_time[~g.bar_time.isin(expected)], expected[~expected.isin(g.bar_time)]
    g["t"] = pos.reindex(g.bar_time).to_numpy()
    s_time_ok = g.s_time.to_numpy() == b.index.to_numpy()[g.t.to_numpy() - 1]
    # Every bar s up to the last logged one: a break spends its line whether or not bar s + 1 is eligible.
    every = list(range(int(g.t.max())))
    chunks = [every[k:k + 2000] for k in range(0, len(every), 2000)]
    with Pool(4, initializer=_init) as pool:  # 4 of 8 cores: keep the machine responsive
        states = dict(x for chunk in pool.imap(partial(_states, depth_a), chunks) for x in chunk)
    spent = run_spent(states)
    py = pd.DataFrame([dict(t=t, status=st, **info) for t, bid in zip(g.t.tolist(), g.bid.tolist())
                       for st, info in [resolve(b, t, states[t - 1], spent[t - 1], bid)]])
    times = b.index.to_numpy()
    for c in ("anchor1", "anchor2"):
        has = py[c].notna()
        py[f"{c}_time"] = pd.NaT
        py.loc[has, f"{c}_time"] = times[py.loc[has, c].astype(int).to_numpy()]
    py["s_red"] = py.s_red.astype(int)
    py["same_contract"] = py.same_contract.astype(int)
    m = g.merge(py, on="t", suffixes=("_ea", "_py"), validate="one_to_one")
    m["period"] = period_of(pd.DatetimeIndex(m.bar_time))
    same_status = m.status_ea == m.status_py
    lined = same_status & m.status_ea.isin(["order", "gap_below", "not_red"])
    priced = same_status & m.status_ea.isin(["order", "gap_below"])
    avail = m.atr_py.notna() & same_status
    checks = dict(
        s_time=pd.Series(s_time_ok, index=m.index),
        s_red=m.s_red_ea == m.s_red_py,
        same_contract=m.same_contract_ea == m.same_contract_py,
        line=(m.loc[lined, "line_ea"] - m.loc[lined, "line_py"]).abs() <= LINE_TOL,
        anchors=(m.loc[lined, "anchor1_time_ea"] == m.loc[lined, "anchor1_time_py"]) &
                (m.loc[lined, "anchor2_time_ea"] == m.loc[lined, "anchor2_time_py"]),
        entry=m.loc[priced, "entry_ea"] == m.loc[priced, "entry_py"],
        stop=m.loc[priced, "stop_ea"] == m.loc[priced, "stop_py"],
        atr=(m.loc[avail, "atr_ea"] - m.loc[avail, "atr_py"]).abs() <= LINE_TOL)
    for c in ("known_pivots", "lines_armed", "lines_live", "lines_broken"):
        checks[c] = m.loc[avail, f"{c}_ea"] == m.loc[avail, f"{c}_py"]
    bad = ~same_status
    for ok in checks.values():
        bad.loc[ok.index[~ok.to_numpy()]] = True
    line_diff = (m.loc[lined, "line_ea"] - m.loc[lined, "line_py"]).abs()
    atr_diff = (m.loc[avail, "atr_ea"] - m.loc[avail, "atr_py"]).abs()
    result = dict(
        job=job, depth_a=depth_a, log_rows=len(g), first_bar=str(g.bar_time.min()), last_bar=str(g.bar_time.max()),
        eligible_expected=len(expected), logged_not_eligible=len(extra), eligible_not_logged=len(absent),
        not_eligible_examples=[str(x) for x in extra.head(10)], not_logged_examples=[str(x) for x in absent[:10]],
        ask_minus_bid=json.loads((g.ask - g.bid).round(2).value_counts().to_json()),
        open_ne_bid=int((g.open != g.bid).sum()),
        status_matches=int(same_status.sum()), status_mismatches=int((~same_status).sum()),
        orders_ea=int((m.status_ea == "order").sum()), orders_py=int((m.status_py == "order").sum()),
        field_mismatches={k: int((~v).sum()) for k, v in checks.items()},
        field_compared={k: int(len(v)) for k, v in checks.items()},
        total_mismatched_rows=int(bad.sum()),
        signals_per_line_max=int(m[m.status_ea.isin(["order", "gap_below", "not_red"])]
                                 .groupby(["anchor1_time_ea", "anchor2_time_ea"]).size().max()),
        max_line_abs_diff=float(line_diff.max()) if len(line_diff) else None,
        max_atr_abs_diff=float(atr_diff.max()) if len(atr_diff) else None,
        crosstab=json.loads(pd.crosstab(m.status_py, m.status_ea).to_json()),
        log_sha256=sha256(RUN / f"{tag}_breakdown.csv"))
    (RUN / f"{tag}_verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    m[bad].to_csv(RUN / f"{tag}_mismatches.csv", index=False)
    (RUN / f"{tag}_counts.json").write_text(json.dumps(counts(m), indent=2), encoding="utf-8")
    keep = ["bar_time", "s_time", "period", "status_ea", "line_ea", "entry_ea", "stop_ea", "atr_ea",
            "anchor1_time_ea", "anchor2_time_ea", "lines_armed_ea", "lines_live_ea", "lines_broken_ea", "s_red_ea",
            "same_contract_ea", "retests", "slope_a", "anchor_sep", "bars_since_anchor2", "bars_since_departure",
            "depth_a", "range_a", "opens_above"]
    m[keep].to_csv(RUN / f"{tag}_bars.csv", index=False)
    print(json.dumps({k: v for k, v in result.items() if k != "crosstab"}, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
