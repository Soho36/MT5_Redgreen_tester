"""Q17 pre-trade check: the MT5 gate's classification (GateMode=1, no orders) must reproduce Q15's
Python classification for every census signal: group, line value, anchors and ATR."""

import json
import sys

import numpy as np
import pandas as pd

from analyze_price_levels import ROOT, sha256
from verify_location_validation import read_rows

RUN = ROOT / "Reports" / "trendlines" / "resistance_standalone_20261004"
Q15 = ROOT / "Reports" / "trendlines" / "trendline_resistance_20261004"
M30 = ROOT / "Reports" / "levels" / "breach_reclaim_20261003" / "m30_reference.csv"


def load_gate(tag):
    g = pd.DataFrame(read_rows(RUN / f"{tag}_gate.csv"))
    g["signal_time"] = pd.to_datetime(g.signal_time, format="%Y.%m.%d %H:%M:%S")
    for c in ("anchor1_time", "anchor2_time"):
        g[c] = pd.to_datetime(g[c].replace("", np.nan), format="%Y.%m.%d %H:%M:%S")
    for c in ("line", "atr", "signal_high", "signal_low"):
        g[c] = g[c].astype(float)
    assert g.signal_time.is_unique
    return g


def compare(tag):
    g = load_gate(tag)
    times = pd.read_csv(M30, usecols=[0], parse_dates=[0]).iloc[:, 0].to_numpy()
    q = pd.read_csv(Q15 / "signals.csv", parse_dates=["signal_time"])
    q = q[q.config == "week_n5"].copy()
    has = q.anchor1.notna()
    q["anchor1_time"], q["anchor2_time"] = pd.NaT, pd.NaT
    q.loc[has, "anchor1_time"] = times[q.loc[has, "anchor1"].astype(int).to_numpy()]
    q.loc[has, "anchor2_time"] = times[q.loc[has, "anchor2"].astype(int).to_numpy()]
    m = q.merge(g, on="signal_time", how="left", suffixes=("_py", "_ea"), validate="one_to_one")
    missing = int(m.group_ea.isna().sum())
    m = m[m.group_ea.notna()]
    same_group = m.group_py == m.group_ea
    assert np.allclose(m.signal_high_py, m.signal_high_ea) and np.allclose(m.signal_low_py, m.signal_low_ea)
    contact = m.line_py.notna() & same_group
    line_diff = (m.loc[contact, "line_py"] - m.loc[contact, "line_ea"]).abs()
    anchors_same = ((m.loc[contact, "anchor1_time_py"] == m.loc[contact, "anchor1_time_ea"]) &
                    (m.loc[contact, "anchor2_time_py"] == m.loc[contact, "anchor2_time_ea"]))
    avail = m.atr_py.notna() & (m.atr_ea > 0)
    atr_diff = (m.loc[avail, "atr_py"] - m.loc[avail, "atr_ea"]).abs()
    mismatches = m[~same_group][["event_id", "signal_time", "period", "group_py", "group_ea", "line_py", "line_ea",
                                 "atr_py", "atr_ea"]]
    cross = pd.crosstab(m.group_py, m.group_ea)
    result = dict(gate_rows=len(g), census_signals=len(q), census_missing_in_gate=missing, compared=len(m),
                  group_matches=int(same_group.sum()), group_mismatches=int((~same_group).sum()),
                  candidate_py=int((m.group_py == "resistance_test").sum()),
                  candidate_ea=int((m.group_ea == "resistance_test").sum()),
                  candidate_both=int(((m.group_py == "resistance_test") & (m.group_ea == "resistance_test")).sum()),
                  max_line_abs_diff=float(line_diff.max()) if len(line_diff) else None,
                  anchors_match=int(anchors_same.sum()), anchors_compared=int(contact.sum()),
                  max_atr_abs_diff=float(atr_diff.max()), gate_sha256=sha256(RUN / f"{tag}_gate.csv"),
                  crosstab=json.loads(cross.to_json()),
                  mismatch_examples=json.loads(mismatches.head(20).to_json(orient="records", date_format="iso")))
    return result, mismatches


def main(tag="resistance_standalone_20261004_classify"):
    result, mismatches = compare(tag)
    (RUN / f"{tag}_verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    mismatches.to_csv(RUN / f"{tag}_mismatches.csv", index=False)
    print(json.dumps({k: v for k, v in result.items() if k not in ("crosstab", "mismatch_examples")}, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
