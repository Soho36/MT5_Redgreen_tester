"""Independent checks of Q11 outputs: direct re-derivation for sampled signals,
plus whole-population partitions. Does not import level_visit."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from trend_regimes import ROLLS

ROOT = Path(__file__).absolute().parent.parent
STUDY = ROOT / "Reports" / "levels" / "level_visit_20261004"
M30 = ROOT / "Reports" / "levels" / "breach_reclaim_20261003" / "m30_reference.csv"
CONFIGS = {"week_n5": (5, 5), "two_weeks_n5": (5, 10), "week_n3": (3, 5)}
DISJOINT = ("support_revisit", "slice_through", "broken_contact", "not_departed_contact", "no_contact",
            "missing_history", "contract_roll", "invalid_atr")


def bars_with_contract():
    b = pd.read_csv(M30, index_col=0, parse_dates=[0])
    rolls = pd.read_csv(ROLLS)
    dates = pd.to_datetime(rolls.date).tolist()
    ids = rolls.instrument_id.tolist()
    contract, j = [], 0
    for t in b.index.normalize():
        while j + 1 < len(dates) and dates[j + 1] <= t:
            j += 1
        contract.append(ids[j])
    b["contract"] = contract
    return b


def direct(b, s, n, sessions):
    t = b.index
    days = sorted(set(t.normalize()))
    day = t[s].normalize()
    pos = days.index(day)
    if pos - sessions < 0:
        return "missing_history", None
    first_day = days[pos - sessions]
    start = int(np.searchsorted(t, first_day))
    con = b.contract.to_numpy()
    if any(con[k] != con[s] for k in range(start, s + 1)):
        return "contract_roll", None
    trs = []
    for k in range(s - 14, s):
        if k < 1 or con[k] != con[s] or con[k - 1] != con[s]:
            return "invalid_atr", None
        h, l, pc = b.high.iloc[k], b.low.iloc[k], b.close.iloc[k - 1]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    a = sum(trs) / 14
    if a <= 0:
        return "invalid_atr", None
    d = a / 2
    low, high, close = b.low.to_numpy(), b.high.to_numpy(), b.close.to_numpy()
    piv = []
    for i in range(start, s):
        if i + n > s - 1 or i - n < 0:
            continue
        if any(con[k] != con[i] for k in range(i - n, i + n + 1)):
            continue
        if all(low[i] < low[k] for k in range(i - n, i)) and all(low[i] <= low[k] for k in range(i + 1, i + n + 1)):
            piv.append(i)
    piv.sort(key=lambda i: (low[i], i))
    levels = []
    for i in piv:
        if levels and low[i] - levels[-1][0] <= d:
            levels[-1][1].append(i)
        else:
            levels.append([low[i], [i]])
    found = {"revisit": [], "slice": [], "broken": [], "near": []}
    for L, members in levels:
        if not (low[s] <= L + d and high[s] >= L - d):
            continue
        t0 = max(members)
        seg = close[t0 + 1:s]
        broken = len(seg) > 0 and seg.min() < L - d
        departed = len(seg) > 0 and seg.max() >= L + a
        if not broken and departed:
            found["revisit" if low[s] >= L - d else "slice"].append((L, t0))
        elif broken:
            found["broken"].append((L, t0))
        else:
            found["near"].append((L, t0))
    for key, group in (("revisit", "support_revisit"), ("slice", "slice_through"), ("broken", "broken_contact"),
                       ("near", "not_departed_contact")):
        if found[key]:
            # nearest to the signal low; ties go to the most recent level (descriptive only)
            return group, min(found[key], key=lambda x: (abs(low[s] - x[0]), -x[1]))[0]
    return "no_contact", None


def main():
    b = bars_with_contract()
    signals = pd.read_csv(STUDY / "signals.csv", parse_dates=["signal_time"])
    rng = np.random.default_rng(11)
    checked, mismatches = 0, []
    for config, (n, sessions) in CONFIGS.items():
        f = signals[signals.config == config]
        # every candidate-relevant group represented, plus a random draw
        picks = pd.concat([f[f.group == g].sample(min(40, (f.group == g).sum()), random_state=1) for g in DISJOINT if (f.group == g).any()]
                          + [f.sample(200, random_state=int(rng.integers(1e6)))])
        for r in picks.itertuples():
            s = b.index.get_loc(r.signal_time)
            group, level = direct(b, s, n, sessions)
            checked += 1
            same_level = level is None or (pd.notna(r.level) and abs(level - r.level) < 1e-9)
            if group != r.group or not same_level:
                mismatches.append(dict(config=config, signal_time=str(r.signal_time), saved=r.group, direct=group,
                                       saved_level=r.level, direct_level=level))
    groups = pd.read_csv(STUDY / "groups.csv")
    g = groups[groups.year == "all"].set_index(["config", "period", "group"])
    partitions = 0
    for config in CONFIGS:
        for period in ("train", "recent"):
            total = g.loc[(config, period, "all")]
            parts = g.loc[[(config, period, x) for x in DISJOINT]]
            pair = g.loc[[(config, period, x) for x in ("candidate", "every_other")]]
            for col in ("potential_signals", "attempts", "fills"):
                assert parts[col].sum() == total[col] == pair[col].sum(), (config, period, col)
            assert abs(parts.net.sum() - total.net) < 1e-6 and abs(pair.net.sum() - total.net) < 1e-6
            partitions += 1
    result = dict(sampled_signals_checked=checked, mismatches=len(mismatches), mismatch_examples=mismatches[:10],
                  partitions_reconciled=partitions)
    (STUDY / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    assert not mismatches


if __name__ == "__main__":
    main()
