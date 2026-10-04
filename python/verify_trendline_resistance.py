"""Independent checks of Q15 outputs. Re-derives sampled signals directly on raw highs with plain
loops (no price mirroring; does not import trendline_resistance, trendline_support or level_visit),
then reconciles partitions and recounts candidate trades from the saved ledger."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from verify_level_visit import bars_with_contract

ROOT = Path(__file__).absolute().parent.parent
STUDY = ROOT / "Reports" / "trendlines" / "trendline_resistance_20261004"
CONFIGS = {"week_n5": (5, 5), "two_weeks_n5": (5, 10), "week_n3": (3, 5)}
DISJOINT = ("resistance_test", "poke_through", "broken_contact", "not_departed_contact", "no_contact",
            "missing_history", "contract_roll", "invalid_atr")
BROAD = ("resistance_test", "poke_through", "not_departed_contact")


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
    found = {"test": [], "poke": [], "broken": [], "near": []}
    for idx, j in enumerate(piv):
        earlier = [i for i in piv[:idx] if high[i] > high[j]]
        if not earlier:
            continue
        i = earlier[-1]
        if j - i < 10 or (high[i] - high[j]) / (j - i) < 0.02 * a:
            continue
        val = lambda k: high[i] + (high[j] - high[i]) * (k - i) / (j - i)
        v = val(s)
        if not (high[s] >= v - d and low[s] <= v + d):
            continue
        if any(high[k] > val(k) + d for k in range(i + 1, j)):
            continue
        broken = any(close[k] > val(k) + d for k in range(j + 1, s))
        departed = any(close[k] <= val(k) - a for k in range(j + 1, s))
        key = ("test" if high[s] <= v + d else "poke") if (departed and not broken) else ("broken" if broken else "near")
        found[key].append((v, i, j))
    for key, group in (("test", "resistance_test"), ("poke", "poke_through"), ("near", "not_departed_contact"),
                       ("broken", "broken_contact")):
        if found[key]:
            return group, min(found[key], key=lambda x: (abs(high[s] - x[0]), -x[2], -x[1]))[0]
    return "no_contact", None


def main():
    b = bars_with_contract()
    days = sorted(set(b.index.normalize()))
    signals = pd.read_csv(STUDY / "signals.csv", parse_dates=["signal_time"])
    checked, mismatches = 0, []
    for config, (n, sessions) in CONFIGS.items():
        f = signals[signals.config == config]
        picks = pd.concat([f[f.group == g].sample(min(40, int((f.group == g).sum())), random_state=15)
                           for g in DISJOINT if (f.group == g).any()] + [f.sample(200, random_state=1515)])
        for r in picks.itertuples():
            group, line = direct(b, days, b.index.get_loc(r.signal_time), n, sessions)
            checked += 1
            same = line is None or (pd.notna(r.line) and abs(line - r.line) < 1e-6)
            if group != r.group or not same:
                mismatches.append(dict(config=config, signal_time=str(r.signal_time), saved=r.group, direct=group,
                                       saved_line=r.line, direct_line=line))
    groups = pd.read_csv(STUDY / "groups.csv")
    g = groups[groups.year == "all"].set_index(["question", "config", "period", "group"])
    trades = pd.read_csv(STUDY / "trades.csv")
    partitions = 0
    for config in CONFIGS:
        for period in ("train", "recent"):
            total = g.loc[("resistance", config, period, "all")]
            parts = g.loc[[("resistance", config, period, x) for x in ("candidate",) + DISJOINT[1:5] + ("unavailable",)]]
            for col in ("potential_signals", "attempts", "fills"):
                assert parts[col].sum() == total[col], (config, period, col)
            assert abs(parts.net.sum() - total.net) < 1e-6
            for question in ("resistance", "broad"):
                pair = g.loc[[(question, config, period, x) for x in ("candidate", "every_other")]]
                for col in ("potential_signals", "attempts", "fills"):
                    assert pair[col].sum() == total[col], (question, config, period, col)
                assert abs(pair.net.sum() - total.net) < 1e-6
                inside = trades[(trades.config == config) & (trades.period == period)]
                inside = inside[inside.group.isin(("resistance_test",) if question == "resistance" else BROAD)]
                cand = g.loc[(question, config, period, "candidate")]
                assert len(inside) == cand.fills and abs(inside.net.sum() - cand.net) < 1e-6
                # PF and mean R recomputed from the ledger
                gains, losses = inside.net.clip(lower=0).sum(), -inside.net.clip(upper=0).sum()
                assert abs(gains / losses - cand.pf) < 1e-9 and abs(inside.net_r.mean() - cand.avg_net_r) < 1e-9
                partitions += 1
    result = dict(sampled_signals_checked=checked, mismatches=len(mismatches), mismatch_examples=mismatches[:10],
                  partitions_reconciled=partitions)
    (STUDY / "verification_independent.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    assert not mismatches


if __name__ == "__main__":
    main()
