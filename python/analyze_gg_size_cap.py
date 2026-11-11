"""Independent decisions, minute replay, native economics and equity for the GG size cap."""
import json
import numpy as np
import pandas as pd
import rtl_weekly_engine as engine
from prepare_gg_size_cap import RUN, DOC, ARMS
from audit_granularity_ledgers import digest, ensure_audited
from analyze_gg_large_candle import features, PERIODS, TICK
from analyze_rtl_vwap_cross import parse_report, economics, INSTRUMENTS
from verify_exclude16_replay import DTYPE, equity_metrics, maxdd
from verify_rtl_failed_breakout_short import load_quote_index

# W1600W1700=false closes the 16:00 and 16:30 bars for new orders (bar-open minutes of the day)
BLOCKED = {True: (), False: (960, 990)}
KEY = ["submitted", "entry_time"]


def capped(f, ratio, min_prior=5):
    """Signals the cap rejects: range at least ratio x the median earlier-session range."""
    if not np.isfinite(ratio) or ratio < 0 or (0 < ratio <= 1) or min_prior < 1:
        raise ValueError("Invalid size-cap parameters")
    return (ratio > 0) & f.prior_count.ge(min_prior) & f["median"].gt(0) & (f["range"] + 1e-9 >= ratio * f["median"])


def check_decisions(job, f):
    d = pd.read_csv(RUN / f"size_cap_{job['tag']}.tsv", sep="\t", parse_dates=["time", "signal_bar"])
    f = f.set_index("bar_time")
    indices = f.index.get_indexer(d.signal_bar)
    assert (indices >= 0).all()
    expected_signal = np.searchsorted(f.index.to_numpy(), d.time.dt.floor("30min").to_numpy()) - 1
    assert np.array_equal(indices, expected_signal), "Signal must be previous completed observed M30 bar"
    ref = f.iloc[indices].reset_index()
    same_day = d.time.dt.normalize().eq(ref.session)
    ref.loc[~same_day, ["prior_count", "median", "ratio"]] = 0
    for c in ("high", "low", "prior_count", "median", "ratio"):
        np.testing.assert_allclose(d[c], ref[c], rtol=0, atol=1e-9, err_msg=c)
    assert ref.close.gt(ref.open).all(), "GG signal must be green"
    assert np.array_equal(d.capped.astype(bool), capped(ref, job["ratio"]))
    d["order_bar"] = d.time.dt.floor("30min")
    assert d.order_bar.is_unique
    minute = d.order_bar.dt.hour * 60 + d.order_bar.dt.minute
    assert not minute.isin(BLOCKED[job["open_hour"]]).any(), "Decision inside a closed entry window"
    return d


def validate_simulation(q, f, native, job):
    # A previous session's last candle that becomes the next session's signal is never capped.
    use = capped(f, job["ratio"]) & f.session.shift(-1).eq(f.session)
    keys = f.bar_time.to_numpy(dtype="datetime64[s]").astype(np.int64) // 1800
    skips = set(keys[use.to_numpy()].tolist()) if job["ratio"] else None
    sim, rejected = engine.simulate_m30_ea(q.b, cutoffs=engine.load_cutoffs(), signal="green",
                                           signal_skips=skips, blocked_minutes=BLOCKED[job["open_hour"]])
    sim["entry_minute"] = pd.to_datetime(sim.entry_time).dt.floor("min")
    # The source's first few bars precede MT5's history warmup. All later trades must match.
    later = sim.loc[sim.entry_minute >= native.entry_time.min().floor("min")].reset_index(drop=True)
    assert len(later) == len(native), (job["tag"], len(later), len(native))
    assert np.array_equal(later.entry_minute, native.entry_time.dt.floor("min"))
    assert np.array_equal(pd.to_datetime(later.exit_time).dt.floor("min"), native.exit_time.dt.floor("min"))
    for a, b in (("requested", "requested_price"), ("sl", "original_sl"), ("fill", "fill_price"), ("exit_price", "exit_price")):
        np.testing.assert_allclose(later[a], native[b], rtol=0, atol=1e-7, err_msg=a)
    assert np.array_equal(pd.to_datetime(later.submitted).dt.floor("30min"), native.submitted.dt.floor("30min"))
    return dict(trades=len(later), extra_before_tester_start=len(sim) - len(later), rejected_orders=rejected,
                capped_slots=0 if skips is None else len(skips))


def metrics(p):
    net = p.net_dollars
    loss = -net[net < 0].sum()
    sessions = p.groupby("session").net_dollars.sum()
    return dict(trades=len(p), net_dollars=float(net.sum()), mean_net_R=float(p.net_r.mean()),
                mean_gross_R=float(p.gross_r.mean()), win_pct=float(100 * (net > 0).mean()),
                profit_factor=float(net[net > 0].sum() / loss) if loss else float("nan"),
                median_risk_dollars=float(p.initial_risk_dollars.median()),
                max_risk_dollars=float(p.initial_risk_dollars.max()),
                risk_ge_500=int((p.initial_risk_dollars >= 500).sum()),
                worst_trade=float(net.min()), worst_session_net=float(sessions.min()),
                sessions_le_minus500=int((sessions <= -500).sum()),
                stress1_net=float((net - 1).sum()), stress2_net=float((net - 2).sum()),
                stress1_mean_R=float(((net - 1) / p.initial_risk_dollars).mean()),
                stress2_mean_R=float(((net - 2) / p.initial_risk_dollars).mean()))


def decompose(cap, base, ratio):
    """Split the cap run's profit change into control trades that vanish and trades that only exist with the cap."""
    j = cap.merge(base, on=KEY, how="outer", suffixes=("_cap", "_base"), indicator=True)
    both = j.loc[j._merge.eq("both")]
    # The same order filled at the same moment is the same trade in both runs.
    np.testing.assert_allclose(both.net_dollars_cap, both.net_dollars_base, rtol=0, atol=1e-7)
    gone = j.loc[j._merge.eq("right_only")]
    new = j.loc[j._merge.eq("left_only")]
    was_capped = gone.prior_count_base.ge(5) & gone.median_base.gt(0) & (gone.ratio_base + 1e-12 >= ratio)
    rows = []
    for period, (start, end) in PERIODS.items():
        g = gone.loc[gone.session_base.ge(start) & gone.session_base.lt(end)]
        gc = g.loc[was_capped.loc[g.index]]
        go = g.loc[~was_capped.loc[g.index]]
        a = new.loc[new.session_cap.ge(start) & new.session_cap.lt(end)]
        c = cap.loc[cap.session.ge(start) & cap.session.lt(end)]
        b = base.loc[base.session.ge(start) & base.session.lt(end)]
        change = float(c.net_dollars.sum() - b.net_dollars.sum())
        parts = float(a.net_dollars_cap.sum() - g.net_dollars_base.sum())
        assert abs(change - parts) < 1e-6, (period, change, parts)
        rows.append(dict(period=period, net_change=change,
                         capped_trades_removed=len(gc), capped_trades_net=float(gc.net_dollars_base.sum()),
                         capped_trades_gross_R=float(gc.gross_r_base.mean()) if len(gc) else float("nan"),
                         capped_median_risk=float(gc.initial_risk_dollars_base.median()) if len(gc) else float("nan"),
                         other_trades_removed=len(go), other_trades_net=float(go.net_dollars_base.sum()),
                         new_trades=len(a), new_trades_net=float(a.net_dollars_cap.sum()),
                         new_trades_gross_R=float(a.gross_r_cap.mean()) if len(a) else float("nan"),
                         new_median_risk=float(a.initial_risk_dollars_cap.median()) if len(a) else float("nan")))
    return rows


def main():
    manifest = json.loads((RUN / "manifest.json").read_text())
    assert digest(DOC / "PROTOCOL.md") == manifest["protocol_sha256"]
    for n, h in manifest["prepared_sha256"].items():
        assert digest(RUN / n) == h, n
    q = load_quote_index()  # checks every cached OHLC against the original raw minute file
    f = features(pd.DataFrame(dict(bar_time=pd.to_datetime(q.slots * 1800, unit="s"),
                                   open=q.ohlc[:, 0], high=q.ohlc[:, 1], low=q.ohlc[:, 2], close=q.ohlc[:, 3])))
    print(f"Raw minutes and {len(f):,} M30 features checked.", flush=True)
    rows, checks, ledgers = [], [], {}
    scopes = {**PERIODS, **{str(y): (f"{y}-01-01", min(f"{y+1}-01-01", "2026-10-01")) for y in range(2010, 2027)}}
    for job in manifest["jobs"]:
        tag, arm, ratio = job["tag"], job["arm"], job["ratio"]
        done = json.loads((RUN / (tag + ".completed.json")).read_text())
        for n, h in done["outputs"].items():
            assert digest(RUN / n) == h, n
        identical = None
        if not ratio:
            identical = (RUN / job["outputs"][0]).read_bytes() == ARMS[arm][1].read_bytes()
            assert identical, f"{tag}: cap-off control differs from {ARMS[arm][1].name}"
        audit = ensure_audited(RUN, job, dict(symbol=manifest["symbol"], grid_points=TICK), 2)
        d = check_decisions(job, f)
        n = economics(parse_report(RUN / (tag + ".htm"), manifest["symbol"]), INSTRUMENTS["NQ"])
        simcheck = validate_simulation(q, f, n, job)
        print(tag, "full minute replay matches", len(n), "native trades", flush=True)
        a = pd.read_csv(audit, sep="\t", encoding="utf-16").set_index("ticket").loc[n.ticket]
        np.testing.assert_allclose(a.trade_profit, n.trade_profit, rtol=0, atol=1e-7)
        np.testing.assert_allclose(n.trade_profit, (n.exit_price - n.fill_price) * 2, rtol=0, atol=1e-7)
        accepted = d.set_index("order_bar").reindex(n.submitted.dt.floor("30min")).reset_index(drop=True)
        assert accepted.signal_bar.notna().all()
        assert accepted.capped.eq(0).all(), "A capped signal produced an order"
        np.testing.assert_allclose(n.requested_price, accepted.high, rtol=0, atol=1e-8)
        np.testing.assert_allclose(n.original_sl, accepted.low, rtol=0, atol=1e-8)
        for c in ("signal_bar", "high", "low", "prior_count", "median", "ratio"):
            n[c] = accepted[c].to_numpy()
        data = np.memmap(RUN / f"window_equity_{tag}.bin", dtype=DTYPE, mode="r")
        assert np.all(np.diff(data["time"]) >= 0)
        stat = pd.read_csv(RUN / job["outputs"][1], sep="\t", encoding="utf-16").iloc[0]
        gross_dd = maxdd(data["equity"])
        assert abs(gross_dd - stat.equity_dd) < 1e-6, (tag, gross_dd, stat.equity_dd)
        assert abs(data["balance"][-1] - 500000 - n.trade_profit.sum()) < 1e-6
        assert abs(data["equity"][-1] - data["balance"][-1]) < 1e-6
        exits = np.sort(n.exit_time.to_numpy().astype("datetime64[s]").astype(np.int64))
        for period, (start, end) in scopes.items():
            p = n.loc[n.session.ge(start) & n.session.lt(end)]
            dp = d.loc[d.order_bar.ge(start) & d.order_bar.lt(end)]
            row = dict(arm=arm, threshold=ratio, period=period, decisions=len(dp), capped_signals=int(dp.capped.sum()),
                       **metrics(p), **equity_metrics(data, start, end, exits))
            row["net_per_equity_dd"] = row["net_dollars"] / row["sampled_equity_dd"]
            rows.append(row)
        n.to_csv(RUN / (tag + "_trades.csv"), index=False)
        ledgers[arm, ratio] = n
        checks.append(dict(tag=tag, arm=arm, threshold=ratio, decisions=len(d), capped_decisions=int(d.capped.sum()),
                           fills=len(n), native_gross_equity_dd=gross_dd, control_byte_identical=identical,
                           report_sha256=digest(RUN / (tag + ".htm")), minute_replay=simcheck))
        del data
    summary = pd.DataFrame(rows)
    summary.to_csv(RUN / "summary.csv", index=False)
    parts = []
    for (arm, ratio), n in ledgers.items():
        if ratio:
            parts += [dict(arm=arm, threshold=ratio, **r) for r in decompose(n, ledgers[arm, 0.0], ratio)]
    pd.DataFrame(parts).to_csv(RUN / "decomposition.csv", index=False)
    result = dict(all_passed=True, jobs=checks, source_sha256=digest(engine.MINUTES),
                  code_sha256=digest(__file__), simulator_sha256=digest(engine.__file__),
                  summary_sha256=digest(RUN / "summary.csv"), decomposition_sha256=digest(RUN / "decomposition.csv"),
                  raw_minutes=len(q.b["o"]), m30_bars=len(f))
    (RUN / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(summary.loc[summary.period.isin(PERIODS), ["arm", "threshold", "period", "trades", "capped_signals",
          "net_dollars", "mean_net_R", "sampled_equity_dd", "net_per_equity_dd", "max_risk_dollars", "worst_trade"]].to_string(index=False))


if __name__ == "__main__":
    main()
