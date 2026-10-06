"""Q24 pre-trade check: the MT5 classify-only log (ReclaimMode=1, no orders) must be reproduced bar by bar by
python/support_reclaim.py (built on the frozen Q11 level functions): status, bar s, level, defining pivot, latest
member, members, entry, stop, risk, ATR and level counts. Also checks which bars were logged (eligible bars) and
writes outcome-free counts, including the min-risk and gap skips.

Usage: verify_support_reclaim.py [job] [depth_a]   (default: classify 0.0; S1: classify_s1 0.5)
"""
import json
import sys
from functools import partial
from multiprocessing import Pool

import numpy as np
import pandas as pd

from analyze_level_visit import M30
from analyze_price_levels import sha256
from level_visit import bar_frame, swing_lows
from analyze_price_levels import ROOT
from support_reclaim import level_states, resolve, run_spent
from trend_regimes import ROLLS
from verify_location_validation import read_rows
from verify_trendline_breakdown import eligible_times
from verify_trendline_limit import period_of

RUN = ROOT / "Reports" / "levels" / "support_reclaim_20261007"
STEM = "support_reclaim_20261007"
LINE_TOL = 1e-6
_B, _PIV = None, None


def load_log(tag):
    g = pd.DataFrame(read_rows(RUN / f"{tag}_reclaim.csv"))
    for c in ("bar_time", "s_time", "key_time", "t0_time"):
        g[c] = pd.to_datetime(g[c].replace("", np.nan), format="%Y.%m.%d %H:%M:%S")
    for c in ("open", "ask", "bid", "level", "atr", "entry", "stop", "risk"):
        g[c] = g[c].astype(float)
    for c in ("members", "known_pivots", "levels", "levels_live", "levels_broken", "s_red", "same_contract"):
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
    return [(s, level_states(_B, s, _PIV, depth_a)) for s in chunk]


def classify(b, g, depth_a):
    """Python status for every logged bar t: one ordered pass over all bars (spending), keeping only bars t - 1."""
    need = set((g.t - 1).tolist())
    chunks = [list(range(k, min(k + 2000, int(g.t.max())))) for k in range(0, int(g.t.max()), 2000)]
    spent, kept = set(), {}
    with Pool(4, initializer=_init) as pool:
        for chunk in pool.imap(partial(_states, depth_a), chunks):
            for s, state in chunk:
                levels = state[3]
                if s in need:
                    kept[s] = (state, frozenset(x["key"] for x in levels if x["key"] in spent))
                spent |= {x["key"] for x in levels if x["breaks"]}
    rows = []
    for t, ask in zip(g.t.tolist(), g.ask.tolist()):
        state, before = kept[t - 1]
        status, info = resolve(b, t, state, before, ask)
        rows.append(dict(t=t, status=status, **info))
    return pd.DataFrame(rows)


def counts(m):
    out = {}
    for period, f in m.groupby("period"):
        o = f[f.status_ea == "order"]
        out[period] = dict(eligible_bars=len(f), status=f.status_ea.value_counts().to_dict(),
                           breakdowns=int(f.status_ea.isin(["order", "gap_above", "min_risk"]).sum()),
                           orders=len(o), min_risk_skips=int((f.status_ea == "min_risk").sum()),
                           gap_skips=int((f.status_ea == "gap_above").sum()),
                           risk_points_median=round(float(o.risk_ea.median()), 2) if len(o) else None,
                           risk_a_median=round(float(o.risk_a.median()), 3) if len(o) else None,
                           depth_a_median=round(float(o.depth_a.median()), 3) if len(o) else None,
                           ask_to_level_points_median=round(float((o.level_ea - o.ask).median()), 2) if len(o) else None)
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
    py = classify(b, g, depth_a)
    times = b.index.to_numpy()
    for c, col in (("key", "key_time"), ("t0", "t0_time")):
        has = py[c].notna()
        py[col] = pd.NaT
        py.loc[has, col] = times[py.loc[has, c].astype(int).to_numpy()]
    for c in ("s_red", "same_contract"):
        py[c] = py[c].astype(int)
    m = g.merge(py, on="t", suffixes=("_ea", "_py"), validate="one_to_one")
    m["period"] = period_of(pd.DatetimeIndex(m.bar_time))
    same_status = m.status_ea == m.status_py
    lev = same_status & m.status_ea.isin(["order", "gap_above", "min_risk"])
    avail = m.atr_py.notna() & same_status
    checks = dict(s_time=pd.Series(s_time_ok, index=m.index), s_red=m.s_red_ea == m.s_red_py,
                  same_contract=m.same_contract_ea == m.same_contract_py,
                  level=(m.loc[lev, "level_ea"] - m.loc[lev, "level_py"]).abs() <= LINE_TOL,
                  key=m.loc[lev, "key_time_ea"] == m.loc[lev, "key_time_py"],
                  t0=m.loc[lev, "t0_time_ea"] == m.loc[lev, "t0_time_py"],
                  members=m.loc[lev, "members_ea"] == m.loc[lev, "members_py"],
                  entry=(m.loc[lev, "entry_ea"] - m.loc[lev, "entry_py"]).abs() <= LINE_TOL,
                  stop=(m.loc[lev, "stop_ea"] - m.loc[lev, "stop_py"]).abs() <= LINE_TOL,
                  risk=(m.loc[lev, "risk_ea"] - m.loc[lev, "risk_py"]).abs() <= LINE_TOL,
                  atr=(m.loc[avail, "atr_ea"] - m.loc[avail, "atr_py"]).abs() <= LINE_TOL)
    for c in ("known_pivots", "levels", "levels_live", "levels_broken"):
        checks[c] = m.loc[avail, f"{c}_ea"] == m.loc[avail, f"{c}_py"]
    bad = ~same_status
    for ok in checks.values():
        bad.loc[ok.index[~ok.to_numpy()]] = True
    result = dict(
        job=job, depth_a=depth_a, log_rows=len(g), first_bar=str(g.bar_time.min()), last_bar=str(g.bar_time.max()),
        eligible_expected=len(expected), logged_not_eligible=len(extra), eligible_not_logged=len(absent),
        not_eligible_examples=[str(x) for x in extra.head(10)], not_logged_examples=[str(x) for x in absent[:10]],
        ask_minus_bid=json.loads((g.ask - g.bid).round(2).value_counts().to_json()), open_ne_bid=int((g.open != g.bid).sum()),
        status_matches=int(same_status.sum()), status_mismatches=int((~same_status).sum()),
        orders_ea=int((m.status_ea == "order").sum()), orders_py=int((m.status_py == "order").sum()),
        field_mismatches={k: int((~v).sum()) for k, v in checks.items()},
        field_compared={k: int(len(v)) for k, v in checks.items()}, total_mismatched_rows=int(bad.sum()),
        crosstab=json.loads(pd.crosstab(m.status_py, m.status_ea).to_json()), log_sha256=sha256(RUN / f"{tag}_reclaim.csv"))
    (RUN / f"{tag}_verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    m[bad].to_csv(RUN / f"{tag}_mismatches.csv", index=False)
    (RUN / f"{tag}_counts.json").write_text(json.dumps(counts(m), indent=2), encoding="utf-8")
    keep = ["bar_time", "s_time", "period", "status_ea", "level_ea", "key_time_ea", "t0_time_ea", "members_ea", "entry_ea",
            "stop_ea", "risk_ea", "atr_ea", "levels_live_ea", "levels_broken_ea", "s_red_ea", "same_contract_ea",
            "depth_a", "risk_a"]
    m[keep].to_csv(RUN / f"{tag}_bars.csv", index=False)
    print(json.dumps({k: v for k, v in result.items() if k != "crosstab"}, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
