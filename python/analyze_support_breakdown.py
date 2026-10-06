"""Q23 stages 0-1: green signals whose sell stop sits at intact swing-low support (short mirror of Q18).

Frozen protocol: docs/levels/SUPPORT_BREAKDOWN_PROTOCOL.md. Reads the stage-0 MT5 run of the short mirror baseline
(Reports/levels/support_breakdown_20261006/), builds the green-signal census (the mirror of Q10's), checks attempts
and trades against it, classifies every signal with the frozen Q11 classifier as is (level_visit.classify), checks a
sample by independent re-derivation (verify_level_visit.direct), and applies Q18's stage-1 gate. Writes summary.json,
groups.csv, yearly.csv, labels.csv and signals.csv to the run folder.
"""
import json
import re
from functools import partial
from multiprocessing import Pool

import numpy as np
import pandas as pd

from analyze_level_visit import M30, contrast
from analyze_price_levels import PERIODS, ROOT, sha256
from analyze_support_interaction import trade_metrics
from level_visit import GROUPS, bar_frame, classify, swing_lows
from prepare_support_breakdown import PROTOCOL, RUN, STEM
from trend_regimes import ROLLS
from verify_level_visit import bars_with_contract, direct
from verify_location_validation import read_rows

TAG = f"{STEM}_baseline"
COST = 1.05
TIME = "%Y.%m.%d %H:%M:%S"
DAILY = ROOT / "Reports" / "trend_rr_20261002" / "daily_reference.csv"
CONFIGS = {"week_n5": (5, 5), "two_weeks_n5": (5, 10), "week_n3": (3, 5)}
PRIMARY = "week_n5"
ALL_PERIODS = {"early": ("2010-06-07", "2016-01-01"), **PERIODS}
NAMES = {"support_revisit": "breakdown_test", "slice_through": "poke_through", "broken_contact": "broken_downward_contact",
         "not_departed_contact": "not_departed_contact", "no_contact": "no_contact",
         "missing_history": "missing_history", "contract_roll": "contract_roll", "invalid_atr": "invalid_atr"}
CANDIDATE = "breakdown_test"
_B, _PIV = None, {}


def early_closes(path):
    text = path.read_text(encoding="utf-8-sig")
    dates = re.search(r"EC_DATE\[EC_COUNT\] = \{([^}]+)", text)[1].split(",")
    cuts = re.search(r"EC_FLAT_MIN\[EC_COUNT\] = \{([^}]+)", text)[1].split(",")
    return dict(zip([d.strip() for d in dates], map(int, cuts)))


def census_green(bars, flat, periods=ALL_PERIODS, max_run=3):
    """Mirror of analyze_support_interaction.census: green M30 bars (close > open) with green run 1..max_run,
    range > 0, whose submission bar (the next bar) opens at or after 01:00 and before the flatten cutoff."""
    f = bars[["open", "high", "low", "close"]].rename(columns=lambda c: "signal_" + c).copy()
    f["signal_time"] = f.index
    f["submission_time"] = pd.Series(bars.index, index=bars.index).shift(-1)
    green = f.signal_close > f.signal_open
    f["green_run"] = green.astype(int).groupby((~green).cumsum()).cumsum()
    f["candle_range"] = f.signal_high - f.signal_low
    clock = f.submission_time.dt.hour * 60 + f.submission_time.dt.minute
    cutoff = f.submission_time.dt.strftime("%Y%m%d").map(flat).fillna(1410)
    valid = green & f.green_run.between(1, max_run) & (f.candle_range > 0) & (clock >= 60) & (clock < cutoff)
    frames = []
    for period, (start, end) in periods.items():
        chosen = f[valid & f.submission_time.between(start, end, inclusive="left")].copy()
        chosen["period"] = period
        frames.append(chosen)
    f = pd.concat(frames).reset_index(drop=True)
    f["event_id"] = f.signal_time.dt.strftime("%Y%m%d_%H%M")
    f["year"] = f.submission_time.dt.year
    assert f.event_id.is_unique
    return f


def load_run():
    sig = pd.DataFrame(read_rows(RUN / f"{TAG}_signals.csv"))
    for c in ("signal_time", "submission_time"):
        sig[c] = pd.to_datetime(sig[c], format=TIME)
    sig["red_run"] = sig.red_run.astype(int)
    led = pd.DataFrame(read_rows(RUN / f"runband_{TAG}_1.00.csv"))
    for c in ("entry_time", "exit_time", "signal_time"):
        led[c] = pd.to_datetime(led[c], format=TIME)
    led["qualified_time"] = pd.to_datetime(led.qualified_time.replace("", np.nan), format=TIME)
    for c in ("trade_profit", "candle_range", "exit_reason", "base_entry", "initial_stop", "direction", "assigned_rr",
              "signal_high", "signal_low"):
        led[c] = pd.to_numeric(led[c])
    return sig, led.sort_values("entry_time").reset_index(drop=True)


def stage0_checks(census, sig, led):
    stats = read_rows(RUN / f"{TAG}_short_stats.csv")[0]
    mt5 = read_rows(RUN / f"runband_{TAG}_1.00_stats.csv")[0]
    c = census.set_index("signal_time")
    a = c.reindex(sig.signal_time)
    t = c.reindex(led.signal_time)
    out = dict(
        attempts=len(sig), placed=int(stats["placed"]), send_failed=int(stats["send_failed"]),
        attempts_equal_placed_plus_failed=len(sig) == int(stats["placed"]) + int(stats["send_failed"]),
        attempts_in_census=int(a.event_id.notna().sum()),
        attempt_run_matches=int((a.green_run.to_numpy() == sig.red_run.to_numpy()).sum()),
        attempt_submission_matches=int((a.submission_time.to_numpy() == sig.submission_time.dt.floor("30min").to_numpy()).sum()),
        trades=len(led), trades_from_attempts=int(led.signal_time.isin(sig.signal_time).sum()),
        trades_in_census=int(t.event_id.notna().sum()),
        short=int((led.direction == -1).sum()), rr_is_1=int((led.assigned_rr == 1.0).sum()),
        entry_at_or_below_signal_low=int((led.base_entry <= t.signal_low.to_numpy() + 1e-9).sum()),
        stop_is_signal_high=int((led.initial_stop == t.signal_high.to_numpy()).sum()),
        range_is_signal_range=int(np.isclose(led.candle_range, t.candle_range.to_numpy()).sum()),
        same_session_exit=int((led.entry_time.dt.normalize() == led.exit_time.dt.normalize()).sum()),
        overlapping=int((led.entry_time.iloc[1:].to_numpy() < led.exit_time.iloc[:-1].to_numpy()).sum()),
        mt5_trades=int(mt5["trades"]), mt5_net_matches=bool(np.isclose(led.trade_profit.sum(), float(mt5["net_profit"]), atol=1e-6)),
        close_errors=int(stats["close_errors"]), export_errors=int(stats["export_errors"]),
        cancel_errors=int(stats["cancel_errors"]))
    n, m = len(sig), len(led)
    ok = (out["attempts_equal_placed_plus_failed"] and out["attempts_in_census"] == out["attempt_run_matches"] ==
          out["attempt_submission_matches"] == n and all(out[k] == m for k in (
              "trades_from_attempts", "trades_in_census", "short", "rr_is_1", "entry_at_or_below_signal_low",
              "stop_is_signal_high", "range_is_signal_range", "same_session_exit", "mt5_trades"))
          and out["overlapping"] == 0 and out["mt5_net_matches"]
          and out["close_errors"] == out["export_errors"] == out["cancel_errors"] == 0)
    out["all_pass"] = bool(ok)
    return out


def _init():
    global _B, _PIV
    _B = bar_frame(pd.read_csv(M30, index_col=0, parse_dates=[0]), pd.read_csv(ROLLS))
    for n in {n for n, _ in CONFIGS.values()}:
        _PIV[n] = swing_lows(_B.low.to_numpy(), _B.contract.to_numpy(), n)


def _classify(config, chunk):
    n, sessions = CONFIGS[config]
    low, opn = _B.low.to_numpy(), _B.open.to_numpy()
    out = []
    for s in chunk:
        group, info = classify(_B, s, n=n, sessions=sessions, pivots=_PIV[n])
        r = dict(bar=s, group=NAMES[group])
        if "level" in info:
            r.update(level=info["level"], members=info["members"], t0=info["t0"], atr=info["atr"],
                     depth_a=info["depth_a"], opens_below=info["opens_below"],
                     closes_below_since=info["closes_below_since"], level_age=s - info["t0"],
                     entry_at_or_below=bool(low[s] <= info["level"]))
        out.append(r)
    return out


def classify_all(census, bars):
    census["bar"] = bars.index.get_indexer(census.signal_time)
    assert (census.bar >= 0).all()
    for col in ("open", "high", "low", "close"):
        assert np.allclose(bars[col].to_numpy()[census.bar], census[f"signal_{col}"]), col
    frames = []
    chunks = [census.bar.tolist()[k:k + 3000] for k in range(0, len(census), 3000)]
    with Pool(4, initializer=_init) as pool:
        for config in CONFIGS:
            rows = [r for c in pool.imap(partial(_classify, config), chunks) for r in c]
            f = pd.concat([census.reset_index(drop=True), pd.DataFrame(rows).drop(columns="bar")], axis=1)
            f["config"] = config
            frames.append(f)
    return pd.concat(frames, ignore_index=True)


def independent_check(f):
    """Re-derive sampled signals on raw lows with plain loops (verify_level_visit.direct; no study code)."""
    b = bars_with_contract()
    groups_q11 = {v: k for k, v in NAMES.items()}
    checked, bad = 0, []
    for config, (n, sessions) in CONFIGS.items():
        g = f[f.config == config]
        picks = pd.concat([g[g.group == x].sample(min(40, (g.group == x).sum()), random_state=1)
                           for x in g.group.unique()] + [g.sample(200, random_state=23)])
        for r in picks.itertuples():
            group, level = direct(b, b.index.get_loc(r.signal_time), n, sessions)
            checked += 1
            same_level = level is None or (pd.notna(r.level) and abs(level - r.level) < 1e-9)
            if group != groups_q11[r.group] or not same_level:
                bad.append(dict(config=config, signal_time=str(r.signal_time), saved=r.group, direct=group))
    return dict(sampled=checked, mismatches=len(bad), examples=bad[:10])


def attach_trades(f, led):
    t = led.assign(net=led.trade_profit - COST)
    t["net_r"] = t.net / (2 * t.candle_range)
    t["exit_class"] = np.select([t.exit_reason == 4, t.qualified_time.notna()], ["stop", "target_qualified"],
                                default="other_session")
    t = t[["signal_time", "entry_time", "exit_time", "net", "net_r", "exit_class", "trade_profit"]]
    return f.merge(t, on="signal_time", how="left", validate="many_to_one").assign(filled=lambda x: x.net.notna())


def main():
    bars = bar_frame(pd.read_csv(M30, index_col=0, parse_dates=[0]), pd.read_csv(ROLLS))
    census = census_green(bars, early_closes(RUN / "early_closes.mqh"))
    sig, led = load_run()
    checks = stage0_checks(census, sig, led)
    assert checks["all_pass"], checks
    census["baseline_attempt"] = census.signal_time.isin(sig.signal_time)
    f = attach_trades(classify_all(census, bars), led)
    for config in CONFIGS:  # partitions reconcile with the stage-0 ledger
        g = f[f.config == config]
        assert int(g.filled.sum()) == len(led) and abs(g.net.sum() - (led.trade_profit - COST).sum()) < 1e-6
    indep = independent_check(f)
    assert indep["mismatches"] == 0, indep
    rows, contrasts, yearly = [], {}, []
    for config in CONFIGS:
        for period in ALL_PERIODS:
            c = f[(f.config == config) & (f.period == period)]
            for label, mask in [("all", c.group == c.group), ("candidate", c.group == CANDIDATE),
                                ("every_other", c.group != CANDIDATE)] + [(NAMES[g], c.group == NAMES[g]) for g in GROUPS]:
                cg = c[mask]
                tg = cg[cg.filled]
                rows.append(dict(config=config, period=period, group=label, potential_signals=len(cg),
                                 attempts=int(cg.baseline_attempt.sum()), **trade_metrics(tg)))
            if period in PERIODS:
                t = c[c.filled]
                x, y = t[t.group == CANDIDATE], t[t.group != CANDIDATE]
                contrasts[(config, period)] = dict(candidate=trade_metrics(x), complement=trade_metrics(y),
                                                   differences=contrast(x, y, period))
        t = f[(f.config == config) & f.filled & f.period.isin(PERIODS)]
        for yr in sorted(t.year.unique()):
            x, y = t[(t.year == yr) & (t.group == CANDIDATE)], t[(t.year == yr) & (t.group != CANDIDATE)]
            yearly.append(dict(config=config, year=int(yr), candidate_fills=len(x), complement_fills=len(y),
                               candidate_avg_r=x.net_r.mean(), complement_avg_r=y.net_r.mean(),
                               candidate_net=x.net.sum(), complement_net=y.net.sum()))
    yearly = pd.DataFrame(yearly)
    gate = {}
    for config in CONFIGS:
        sel = [contrasts[(config, p)] for p in PERIODS]
        yc = yearly[yearly.config == config]
        elig = yc[(yc.candidate_fills >= 10) & (yc.complement_fills >= 10)]
        gate[config] = dict(
            enough_fills=all(c[k]["fills"] >= 200 for c in sel for k in ("candidate", "complement")),
            candidate_pf_gt_1=all((c["candidate"]["pf"] or 0) > 1 for c in sel),
            better_both=all(c["differences"][k]["difference"] > 0 for c in sel for k in ("pf", "avg_net_r")),
            better_years=int((elig.candidate_avg_r > elig.complement_avg_r).sum()), eligible_years=len(elig))
        gate[config]["core_rule"] = bool(gate[config]["enough_fills"] and gate[config]["candidate_pf_gt_1"] and
                                         gate[config]["better_both"] and gate[config]["better_years"] >= 7)
    agree = all(gate[c]["better_both"] for c in CONFIGS if c != PRIMARY)
    passed = bool(gate[PRIMARY]["core_rule"] and agree)
    # Descriptive labels inside the primary candidate group.
    daily = pd.read_csv(DAILY, index_col=0, parse_dates=[0])
    cand = f[(f.config == PRIMARY) & (f.group == CANDIDATE) & f.filled].copy()
    cand["regime"] = daily.regime50.reindex(cand.signal_time.dt.normalize()).to_numpy()
    bins = dict(entry=cand.entry_at_or_below.map({True: "low at or below L (fill = break)", False: "low above L"}),
                depth=pd.cut(cand.depth_a, [-np.inf, -0.25, 0, 0.25, np.inf],
                             labels=["low > 0.25 A above L", "0-0.25 A above", "0-0.25 A below", ">0.25 A below"]),
                opens_below=cand.opens_below.map({True: "opens below L", False: "opens at/above L"}),
                members=np.where(cand.members > 1, "merged", "single"),
                age=pd.cut(cand.level_age, [0, 20, 50, np.inf], labels=["<=20 bars", "21-50", ">50"]),
                false_breakdowns=pd.cut(cand.closes_below_since, [-1, 0, 2, np.inf], labels=["0", "1-2", ">=3"]),
                regime=cand.regime)
    labels = []
    for name, lab in bins.items():
        for (period, value), g in cand.assign(lab=lab).groupby(["period", "lab"], observed=True):
            m = trade_metrics(g)
            labels.append(dict(label=name, value=str(value), period=period, trades=m["fills"], net=round(m["net"], 2),
                               pf=round(m["pf"], 3) if m["pf"] else None, mean_r=round(m["avg_net_r"], 4)))
    out = dict(protocol=str(PROTOCOL), protocol_sha256=sha256(PROTOCOL), frozen_commit="0d33caa",
               stage0_checks=checks, independent_check=indep, gate=gate, sensitivities_agree=agree, stage1_passed=passed,
               contrasts={f"{c}_{p}": v for (c, p), v in contrasts.items()},
               hashes={str(p): sha256(p) for p in [PROTOCOL, M30, ROLLS, DAILY, RUN / f"runband_{TAG}_1.00.csv",
                                                     RUN / f"{TAG}_signals.csv", RUN / "RTL_short_mirror.mq5",
                                                     ROOT / "python" / "analyze_support_breakdown.py"]})
    (RUN / "summary.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    pd.DataFrame(rows).to_csv(RUN / "groups.csv", index=False)
    yearly.to_csv(RUN / "yearly.csv", index=False)
    pd.DataFrame(labels).to_csv(RUN / "labels.csv", index=False)
    f.drop(columns=["signal_open", "signal_high", "signal_low", "signal_close"]).to_csv(RUN / "signals.csv", index=False)
    print(json.dumps(dict(stage0=checks, independent=indep, gate=gate, agree=agree, passed=passed), indent=1, default=float))
    for r in rows:
        if r["group"] in ("all", "candidate", "every_other"):
            print(f"{r['config']:13s} {r['period']:6s} {r['group']:12s} pot={r['potential_signals']:6d} "
                  f"att={r['attempts']:6d} fills={r['fills']:5d} net={r.get('net', 0):10.0f} pf={r.get('pf') or 0:.3f} "
                  f"avgR={r.get('avg_net_r') or 0:+.4f} win={r.get('win_rate') or 0:.3f}")
    for (c, p), v in contrasts.items():
        d = v["differences"]
        print(c, p, "dPF", round(d["pf"]["difference"], 3), [round(d["pf"]["lower"], 3), round(d["pf"]["upper"], 3)],
              "dR", round(d["avg_net_r"]["difference"], 4), [round(d["avg_net_r"]["lower"], 3), round(d["avg_net_r"]["upper"], 3)])


if __name__ == "__main__":
    main()
