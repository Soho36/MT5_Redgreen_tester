"""Independent checks of Q18 stage 1: re-derive sampled signals directly on raw highs with plain loops
(no price mirroring; does not import level_resistance, level_visit or trendline modules), then reconcile
partitions and recount candidate trades from the saved ledger."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from verify_level_visit import bars_with_contract

ROOT = Path(__file__).absolute().parent.parent
STUDY = ROOT / "Reports" / "levels" / "breakout_20261004"
CONFIGS = {"week_n5": (5, 5), "two_weeks_n5": (5, 10), "week_n3": (3, 5)}
DISJOINT = ("breakout_test", "poke_through", "broken_upward_contact", "not_departed_contact", "no_contact",
            "missing_history", "contract_roll", "invalid_atr")


def direct(b, days, s, n, sessions):
    t, con = b.index, b.contract.to_numpy()
    pos = days.index(t[s].normalize())
    if pos - sessions < 0:
        return "missing_history", None
    start = int(np.searchsorted(t, days[pos - sessions]))
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
        if i - n < 0 or i + n > s - 1:
            continue
        if any(con[k] != con[i] for k in range(i - n, i + n + 1)):
            continue
        if all(high[i] > high[k] for k in range(i - n, i)) and all(high[i] >= high[k] for k in range(i + 1, i + n + 1)):
            piv.append(i)
    piv.sort(key=lambda i: (-high[i], i))
    levels = []
    for i in piv:  # greedy from the highest swing high
        if levels and levels[-1][0] - high[i] <= d:
            levels[-1][1].append(i)
        else:
            levels.append([high[i], [i]])
    found = {"test": [], "poke": [], "broken": [], "near": []}
    for L, members in levels:
        if not (high[s] >= L - d and low[s] <= L + d):
            continue
        t0 = max(members)
        seg = close[t0 + 1:s]
        broken = len(seg) > 0 and seg.max() > L + d
        departed = len(seg) > 0 and seg.min() <= L - a
        if not broken and departed:
            found["test" if high[s] <= L + d else "poke"].append((L, t0))
        elif broken:
            found["broken"].append((L, t0))
        else:
            found["near"].append((L, t0))
    for key, group in (("test", "breakout_test"), ("poke", "poke_through"), ("broken", "broken_upward_contact"),
                       ("near", "not_departed_contact")):
        if found[key]:
            return group, min(found[key], key=lambda x: (abs(high[s] - x[0]), -x[1]))[0]
    return "no_contact", None


def main():
    b = bars_with_contract()
    days = sorted(set(b.index.normalize()))
    signals = pd.read_csv(STUDY / "signals.csv", parse_dates=["signal_time"])
    checked, mismatches = 0, []
    for config, (n, sessions) in CONFIGS.items():
        f = signals[signals.config == config]
        picks = pd.concat([f[f.group == g].sample(min(40, int((f.group == g).sum())), random_state=18)
                           for g in DISJOINT if (f.group == g).any()] + [f.sample(200, random_state=1818)])
        for r in picks.itertuples():
            group, level = direct(b, days, b.index.get_loc(r.signal_time), n, sessions)
            checked += 1
            same = level is None or (pd.notna(r.level) and abs(level - r.level) < 1e-9)
            if group != r.group or not same:
                mismatches.append(dict(config=config, signal_time=str(r.signal_time), saved=r.group, direct=group,
                                       saved_level=r.level, direct_level=level))
    groups = pd.read_csv(STUDY / "groups.csv")
    g = groups[groups.year == "all"].set_index(["question", "config", "period", "group"])
    trades = pd.read_csv(STUDY / "trades.csv")
    partitions = 0
    for config in CONFIGS:
        for period in ("train", "recent"):
            total = g.loc[("breakout", config, period, "all")]
            parts = g.loc[[("breakout", config, period, x) for x in ("candidate",) + DISJOINT[1:5] + ("unavailable",)]]
            for col in ("potential_signals", "attempts", "fills"):
                assert parts[col].sum() == total[col], (config, period, col)
            assert abs(parts.net.sum() - total.net) < 1e-6
            pair = g.loc[[("breakout", config, period, x) for x in ("candidate", "every_other")]]
            for col in ("potential_signals", "attempts", "fills"):
                assert pair[col].sum() == total[col]
            cand = g.loc[("breakout", config, period, "candidate")]
            inside = trades[(trades.config == config) & (trades.period == period) & (trades.group == "breakout_test")]
            gains, losses = inside.net.clip(lower=0).sum(), -inside.net.clip(upper=0).sum()
            assert len(inside) == cand.fills and abs(inside.net.sum() - cand.net) < 1e-6
            assert abs(gains / losses - cand.pf) < 1e-9 and abs(inside.net_r.mean() - cand.avg_net_r) < 1e-9
            partitions += 1
    result = dict(sampled_signals_checked=checked, mismatches=len(mismatches), mismatch_examples=mismatches[:10],
                  partitions_reconciled=partitions)
    (STUDY / "verification_independent.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    assert not mismatches


if __name__ == "__main__":
    main()
