"""Q18 stage-2 pre-trade check: the MT5 level gate (GateMode=1, no orders) must reproduce the stage-1 Python
classification for every census signal: group, level price, latest member time and ATR."""

import json
import sys

import numpy as np
import pandas as pd

from analyze_price_levels import ROOT, sha256
from verify_location_validation import read_rows

RUN = ROOT / "Reports" / "levels" / "breakout_standalone_20261004"
STAGE1 = ROOT / "Reports" / "levels" / "breakout_20261004"
M30 = ROOT / "Reports" / "levels" / "breach_reclaim_20261003" / "m30_reference.csv"


def load_gate(tag):
    g = pd.DataFrame(read_rows(RUN / f"{tag}_gate.csv"))
    g["signal_time"] = pd.to_datetime(g.signal_time, format="%Y.%m.%d %H:%M:%S")
    g["t0_time"] = pd.to_datetime(g.t0_time.replace("", np.nan), format="%Y.%m.%d %H:%M:%S")
    for c in ("level", "atr", "signal_high", "signal_low"):
        g[c] = g[c].astype(float)
    g["members"] = g.members.astype(int)
    assert g.signal_time.is_unique
    return g


def main(tag="breakout_standalone_20261004_classify"):
    g = load_gate(tag)
    times = pd.read_csv(M30, usecols=[0], parse_dates=[0]).iloc[:, 0].to_numpy()
    q = pd.read_csv(STAGE1 / "signals.csv", parse_dates=["signal_time"])
    q = q[q.config == "week_n5"].copy()
    has = q.t0.notna()
    q["t0_time"] = pd.NaT
    q.loc[has, "t0_time"] = times[q.loc[has, "t0"].astype(int).to_numpy()]
    m = q.merge(g, on="signal_time", how="left", suffixes=("_py", "_ea"), validate="one_to_one")
    missing = int(m.group_ea.isna().sum())
    m = m[m.group_ea.notna()]
    assert np.allclose(m.signal_high_py, m.signal_high_ea) and np.allclose(m.signal_low_py, m.signal_low_ea)
    same = m.group_py == m.group_ea
    contact = m.level_py.notna() & same
    level_diff = (m.loc[contact, "level_py"] - m.loc[contact, "level_ea"]).abs()
    t0_same = (m.loc[contact, "t0_time_py"] == m.loc[contact, "t0_time_ea"])
    members_same = (m.loc[contact, "members_py"] == m.loc[contact, "members_ea"])
    avail = m.atr_py.notna() & (m.atr_ea > 0)
    mism = m[~same][["event_id", "signal_time", "period", "group_py", "group_ea", "level_py", "level_ea", "atr_py", "atr_ea"]]
    result = dict(gate_rows=len(g), census_signals=len(q), census_missing_in_gate=missing, compared=len(m),
                  group_matches=int(same.sum()), group_mismatches=int((~same).sum()),
                  candidate_py=int((m.group_py == "breakout_test").sum()),
                  candidate_ea=int((m.group_ea == "breakout_test").sum()),
                  max_level_abs_diff=float(level_diff.max()), t0_matches=int(t0_same.sum()),
                  members_match=int(members_same.sum()), contacts_compared=int(contact.sum()),
                  max_atr_abs_diff=float((m.loc[avail, "atr_py"] - m.loc[avail, "atr_ea"]).abs().max()),
                  gate_sha256=sha256(RUN / f"{tag}_gate.csv"),
                  crosstab=json.loads(pd.crosstab(m.group_py, m.group_ea).to_json()),
                  mismatch_examples=json.loads(mism.head(20).to_json(orient="records", date_format="iso")))
    (RUN / f"{tag}_verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    mism.to_csv(RUN / f"{tag}_mismatches.csv", index=False)
    print(json.dumps({k: v for k, v in result.items() if k not in ("crosstab", "mismatch_examples")}, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
