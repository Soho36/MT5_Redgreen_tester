"""Q22: are RTL long signals at or after a rising-line break different from every other signal?

Frozen protocol: docs/trendlines/BREAKDOWN_RTL_PROTOCOL.md. Reuses Q10's original-exit census (no new MT5 run) and
the verified Q21 break events (python/trendline_breakdown.py; EA = Python on every bar). Group A: the red signal
candle itself breaks a live line. Group B: not A, and a bar 1-10 bars before the signal bar (same contract) breaks
one. Each is compared with every other signal under a two-sided gate (better -> failed-breakdown long candidate,
worse -> skip-filter candidate). Primary break = close below the line; sensitivity S1 = close > 0.5 x A below.
"""
import json
from functools import partial
from multiprocessing import Pool

import numpy as np
import pandas as pd

from analyze_broad_support import verify_manifest
from analyze_level_visit import M30, Q10, contrast, load
from analyze_price_levels import PERIODS, ROOT, sha256
from analyze_support_interaction import trade_metrics
from trend_regimes import ROLLS
from trendline_breakdown import choose_broken, spent_by
from verify_trendline_breakdown import RUN as CLASSIFY, STEM as CLASSIFY_STEM, _init, _states

OUT = ROOT / "Reports" / "trendlines" / "breakdown_rtl_20261006"
PROTOCOL = ROOT / "docs" / "trendlines" / "BREAKDOWN_RTL_PROTOCOL.md"
DAILY = ROOT / "Reports" / "trend_rr_20261002" / "daily_reference.csv"
CONFIGS = {"primary": 0.0, "s1": 0.5}
WINDOW = 10
GROUPS = ("A", "B")


def break_table(depth_a, n_bars, workers=4):
    """Per bar k: lines available, number of live lines k breaks (after spending), and the reported broken line.
    One ordered pass: line states in parallel, spending applied in bar order; only the summary is kept."""
    chunks = [list(range(k, min(k + 2000, n_bars))) for k in range(0, n_bars, 2000)]
    spent = set()
    avail, n_broken, line, atr = np.zeros(n_bars, bool), np.zeros(n_bars, int), np.full(n_bars, np.nan), \
        np.full(n_bars, np.nan)
    with Pool(workers, initializer=_init) as pool:
        for chunk in pool.imap(partial(_states, depth_a), chunks):
            for k, (reason, a, _, lines) in chunk:
                if reason:
                    continue
                avail[k], atr[k] = True, a
                broken = [x for x in lines if x["live"] and x["breaks"] and (x["i"], x["j"]) not in spent]
                n_broken[k] = len(broken)
                if broken:
                    line[k] = choose_broken(broken)["value"]
                spent |= spent_by(lines)
    return pd.DataFrame(dict(available=avail, n_broken=n_broken, line=line, atr=atr))


def assign_groups(breaks, contract, s, window=WINDOW):
    """'A' if bar s breaks a line; 'B' if not A and a bar 1..window before s in the same contract breaks one;
    otherwise 'other'."""
    breaks, contract, s = np.asarray(breaks, bool), np.asarray(contract), np.asarray(s, int)
    out = np.full(len(s), "other", dtype=object)
    for n, k in enumerate(s):
        if breaks[k]:
            out[n] = "A"
            continue
        before = np.arange(max(k - window, 0), k)
        if (breaks[before] & (contract[before] == contract[k])).any():
            out[n] = "B"
    return out


def cross_check(table, bars, job):
    """The break table must equal the verified Q21 classify-only log at every logged bar s (EA = Python)."""
    cls = pd.read_csv(CLASSIFY / f"{CLASSIFY_STEM}_{job}_bars.csv", parse_dates=["s_time"])
    cls = cls[~cls.status_ea.isin(["contract_roll"])]
    s = bars.index.get_indexer(cls.s_time)
    assert (s >= 0).all()
    avail = ~cls.status_ea.isin(["missing_history", "invalid_atr"]).to_numpy()
    ours = table.n_broken.to_numpy()[s]
    theirs = np.where(avail, cls.lines_broken_ea.fillna(0).astype(int).to_numpy(), 0)
    red_break = cls.status_ea.isin(["order", "gap_below"]).to_numpy()
    return dict(bars_compared=len(cls), n_broken_mismatches=int((ours != theirs).sum()),
                red_break_mismatches=int(((ours > 0) & (cls.s_red_ea.to_numpy() == 1) != red_break).sum()),
                log=str(CLASSIFY / f"{CLASSIFY_STEM}_{job}_bars.csv"))


def gate(by_period, s1_by_period, years):
    """Two-sided frozen gate for one group. by_period: {period: (candidate trades, complement trades, contrast)}."""
    enough = all(len(x) >= 200 and len(y) >= 200 for x, y, _ in by_period.values())
    eligible = [r for r in years if r["candidate_fills"] >= 10 and r["complement_fills"] >= 10]
    up = sum(r["candidate_avg_r"] > r["complement_avg_r"] for r in eligible)
    down = sum(r["candidate_avg_r"] < r["complement_avg_r"] for r in eligible)
    diff = lambda c, k: c[k]["difference"]
    higher = all(diff(c, "pf") > 0 and diff(c, "avg_net_r") > 0 for _, _, c in by_period.values())
    lower = all(diff(c, "pf") < 0 and diff(c, "avg_net_r") < 0 for _, _, c in by_period.values())
    s1_higher = all(diff(c, "pf") > 0 and diff(c, "avg_net_r") > 0 for _, _, c in s1_by_period.values())
    s1_lower = all(diff(c, "pf") < 0 and diff(c, "avg_net_r") < 0 for _, _, c in s1_by_period.values())
    profitable = all(trade_metrics(x)["pf"] > 1 for x, _, _ in by_period.values())
    better = dict(enough_fills=enough, pf_gt_1_both=profitable, above_complement_both=higher,
                  years_better=int(up), eligible_years=len(eligible), years_ge_7=bool(up >= 7), s1_same_direction=s1_higher)
    worse = dict(enough_fills=enough, below_complement_both=lower, years_worse=int(down), eligible_years=len(eligible),
                 years_ge_7=bool(down >= 7), s1_same_direction=s1_lower)
    better["passes"] = all(v for v in better.values() if isinstance(v, bool))
    worse["passes"] = all(v for v in worse.values() if isinstance(v, bool))
    return dict(better=better, worse=worse)


def summary_rows(f, t_all, config):
    rows = []
    for period in PERIODS:
        cc, tt = f[f.period == period], t_all[t_all.period == period]
        for label, mask_c, mask_t in [("all", cc.group == cc.group, tt.group == tt.group)] + \
                [(g, cc.group == g, tt.group == g) for g in ("A", "B", "other")] + \
                [(f"every_other_than_{g}", cc.group != g, tt.group != g) for g in GROUPS]:
            c, t = cc[mask_c], tt[mask_t]
            attempts = int(c.baseline_attempt.sum())
            assert len(t) == int(c.filled.sum())
            rows.append(dict(config=config, period=period, group=label, potential_signals=len(c), attempts=attempts,
                             conversion=len(t) / attempts if attempts else None, **trade_metrics(t)))
    return rows


def labels(t, bars, table, daily):
    """Descriptive labels for group A trades (primary break)."""
    s = t.bar.to_numpy()
    v, a = table.line.to_numpy()[s], table.atr.to_numpy()[s]
    minutes = t.signal_time.dt.hour * 60 + t.signal_time.dt.minute
    regime = daily.regime50.reindex(t.signal_time.dt.normalize()).to_numpy()
    lab = pd.DataFrame(dict(
        depth=pd.cut((v - t.signal_close.to_numpy()) / a, [-np.inf, 0.25, 0.5, 1.0, np.inf],
                     labels=["<=0.25 A", "0.25-0.5", "0.5-1", ">1"]),
        range=pd.cut(t.candle_range.to_numpy() / a, [0, 1.0, 1.5, 2.5, np.inf], labels=["<=1 A", "1-1.5", "1.5-2.5", ">2.5"]),
        opens_above=np.where(t.signal_open.to_numpy() >= v, "opened above line", "opened below line"),
        lines_broken=np.where(table.n_broken.to_numpy()[s] >= 2, ">=2 lines", "1 line"),
        segment=np.select([minutes < 600, minutes < 1380], ["morning", "main"], "evening"),
        regime=regime), index=t.index)
    out = []
    for name in lab.columns:
        for (period, value), g in t.assign(lab=lab[name]).groupby(["period", "lab"], observed=True):
            m = trade_metrics(g)
            out.append(dict(label=name, value=str(value), period=period, trades=m["fills"], net=round(m["net"], 2),
                            pf=round(m["pf"], 3) if m["pf"] else None, mean_r=round(m["avg_net_r"], 4)))
    return pd.DataFrame(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_entries = verify_manifest(Q10 / "provenance.json")
    census, trades, bars, _, _ = load()
    assert (census.signal_close < census.signal_open).all(), "RTL signals are red candles"
    contract = bars.contract.to_numpy()
    tables, checks, frames, t_alls = {}, {}, {}, {}
    for config, depth in CONFIGS.items():
        path = OUT / f"break_table_{config}.csv"
        if path.exists():
            table = pd.read_csv(path)
        else:
            table = break_table(depth, len(bars))
            table.to_csv(path, index=False)
        assert len(table) == len(bars)
        tables[config] = table
        checks[config] = cross_check(table, bars, "classify" if config == "primary" else "classify_s1")
        assert checks[config]["n_broken_mismatches"] == 0 and checks[config]["red_break_mismatches"] == 0, checks
        f = census.copy()
        f["group"] = assign_groups(table.n_broken.to_numpy() > 0, contract, f.bar.to_numpy())
        frames[config] = f
        t_alls[config] = f[f.filled].merge(trades, on="event_id", validate="one_to_one")
    rows, contrasts, years, gates = [], {}, {}, {}
    for config in CONFIGS:
        f, t_all = frames[config], t_alls[config]
        rows += summary_rows(f, t_all, config)
        for g in GROUPS:
            per = {}
            for period in PERIODS:
                tt = t_all[t_all.period == period].sort_values("exit_time")
                x, y = tt[tt.group == g], tt[tt.group != g]
                assert len(x) + len(y) == len(tt) and abs(x.net.sum() + y.net.sum() - tt.net.sum()) < 1e-6
                per[period] = (x, y, contrast(x, y, period))
            contrasts[(config, g)] = per
            yrs = []
            for yr in sorted(t_all[t_all.period.isin(PERIODS)].year.unique()):
                ty = t_all[(t_all.year == yr) & t_all.period.isin(PERIODS)]
                x, y = ty[ty.group == g], ty[ty.group != g]
                yrs.append(dict(config=config, group=g, year=int(yr), candidate_fills=len(x), complement_fills=len(y),
                                candidate_avg_r=x.net_r.mean() if len(x) else np.nan,
                                complement_avg_r=y.net_r.mean() if len(y) else np.nan,
                                candidate_net=x.net.sum(), complement_net=y.net.sum()))
            years[(config, g)] = yrs
    for g in GROUPS:
        gates[g] = gate(contrasts[("primary", g)], contrasts[("s1", g)], years[("primary", g)])
    daily = pd.read_csv(DAILY, index_col=0, parse_dates=[0])
    ta = t_alls["primary"]
    lab = labels(ta[ta.group == "A"], bars, tables["primary"], daily)
    out = dict(protocol=str(PROTOCOL), protocol_sha256=sha256(PROTOCOL), frozen_commit="1112d71",
               q10_manifest_entries=manifest_entries, cross_checks=checks, gates=gates,
               contrasts={f"{c}_{g}_{p}": dict(candidate=trade_metrics(x), complement=trade_metrics(y), differences=d)
                          for (c, g), per in contrasts.items() for p, (x, y, d) in per.items()},
               hashes={str(p): sha256(p) for p in [PROTOCOL, Q10 / "potential_signals.csv", Q10 / "trades.csv", M30,
                                                     ROLLS, DAILY, ROOT / "python" / "analyze_breakdown_rtl.py",
                                                     ROOT / "python" / "trendline_breakdown.py"]
                       + [OUT / f"break_table_{c}.csv" for c in CONFIGS]})
    (OUT / "summary.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    pd.DataFrame(rows).to_csv(OUT / "groups.csv", index=False)
    pd.DataFrame([r for v in years.values() for r in v]).to_csv(OUT / "yearly.csv", index=False)
    lab.to_csv(OUT / "labels.csv", index=False)
    print(json.dumps(dict(cross_checks=checks, gates=gates), indent=1, default=float))
    for r in rows:
        if r["group"] in ("A", "B", "other", "every_other_than_A", "every_other_than_B"):
            print(f"{r['config']:7s} {r['period']:6s} {r['group']:19s} pot={r['potential_signals']:6d} "
                  f"fills={r['fills']:5d} net={r['net']:9.0f} pf={r['pf'] or 0:.3f} avgR={r['avg_net_r'] or 0:+.4f} "
                  f"win={r['win_rate'] or 0:.3f}")


if __name__ == "__main__":
    main()
