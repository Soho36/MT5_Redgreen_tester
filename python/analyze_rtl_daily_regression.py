"""Check the native D1 decisions against M30 history and reconcile both trade paths."""
import json

import numpy as np
import pandas as pd

from analyze_rtl_regression_slope import COST_CENTS, END, PERIODS, SYMBOL, metrics
from analyze_rtl_vwap_cross import parse_report
from prepare_rtl_daily_regression import PREFIX, ROOT, RUN, M30_RUN
from prepare_rtl_regression_slope import BASE, CONTROL, sha


def verify_arm(arm, bars, sessions):
    tag = PREFIX + arm
    checksums = json.loads((RUN / (tag + ".completed.json")).read_text())["outputs"]
    for name, digest in checksums.items():
        assert sha(RUN / name) == digest
    fills = RUN / f"runband_{tag}_1.00.csv"
    if arm == "off":
        assert sha(fills) == sha(BASE / f"runband_{CONTROL}_1.00.csv")
    ledger = pd.read_csv(fills, encoding="utf-16", sep="\t").set_index("ticket")
    trades = parse_report(RUN / (tag + ".htm"), SYMBOL).set_index("ticket")
    assert ledger.index.equals(trades.index)
    for col in ("entry_time", "exit_time"):
        np.testing.assert_array_equal(pd.to_datetime(ledger[col], format="%Y.%m.%d %H:%M:%S"), trades[col])
    np.testing.assert_array_equal(trades.trade_profit, ledger.trade_profit)
    np.testing.assert_array_equal(trades.trade_profit, 2 * (trades.exit_price - trades.fill_price))
    stats = pd.read_csv(RUN / f"runband_{tag}_1.00_stats.csv", sep="\t", encoding="utf-16").iloc[0]
    assert len(trades) == stats.trades and trades.trade_profit.sum() == stats.net_profit

    d = pd.read_csv(RUN / f"decisions_{tag}.tsv", sep="\t")
    d.index = pd.to_datetime(d.bar, unit="s")
    assert d.index.is_unique and d.index.is_monotonic_increasing
    d = d.loc[d.index < END].copy()
    day = d.index.normalize()
    assert day.isin(sessions.index).all()
    prior = sessions.loc[day]
    np.testing.assert_array_equal(pd.to_datetime(d.last_daily, unit="s"), prior.last_daily)
    known = prior.numerator.notna().to_numpy()
    np.testing.assert_array_equal(d.bars.eq(5), known)
    np.testing.assert_array_equal(d.numerator, prior.numerator.fillna(0))
    expected = prior.numerator.gt(0).to_numpy()
    np.testing.assert_array_equal(d.allowed, expected | (arm == "off"))
    signal = pd.to_datetime(d.signal, unit="s")
    idx = bars.index.searchsorted(d.index) - 1
    assert (idx >= 0).all()
    signal_bars = bars.iloc[idx]
    np.testing.assert_array_equal(signal_bars.index, signal)
    assert (signal_bars.close < signal_bars.open).all()
    trades = trades.loc[trades.submitted < END].copy()
    accepted = d.loc[trades.submitted.dt.floor("30min")]
    assert accepted.allowed.eq(1).all()
    source = bars.loc[pd.to_datetime(accepted.signal, unit="s")]
    np.testing.assert_array_equal(trades.requested_price, source.high)
    np.testing.assert_array_equal(trades.original_sl, source.low)
    trades["daily_state"] = np.select(
        [accepted.bars.ne(5), accepted.numerator.gt(0), accepted.numerator.lt(0)],
        ["unavailable", "up", "down"], default="flat")
    trades["net_cents"] = (trades.trade_profit * 100).round().astype(int) - COST_CENTS
    trades = trades.set_index("submitted").sort_index()
    assert trades.index.is_unique and trades.exit_time.is_monotonic_increasing
    counts = dict(ledger_rows=len(ledger), reported_trades=len(trades), candidates=len(d),
                  blocked=int(d.allowed.eq(0).sum()), insufficient_history=int((~known).sum()),
                  flat=int((known & d.numerator.eq(0)).sum()))
    return trades, counts


def main():
    bars = pd.read_csv(ROOT / "Reports/rtl_vwap_cross_20261027/features_NQ.csv",
                       usecols=["bar_time","open","high","low","close"], parse_dates=["bar_time"]).set_index("bar_time")
    assert bars.index.is_unique and bars.index.is_monotonic_increasing
    daily_close = bars.close.groupby(bars.index.normalize()).last()
    # At the start of day t, the newest permissible close is t-1.
    c = daily_close.shift(1)
    sessions = pd.DataFrame({"last_daily": daily_close.index.to_series().shift(1),
                             "numerator": 2*(c-c.shift(4)) + (c.shift(1)-c.shift(3))})
    off, off_checks = verify_arm("off", bars, sessions)
    on, on_checks = verify_arm("on", bars, sessions)
    common = off.index.intersection(on.index)
    cols = ["entry_time", "exit_time", "requested_price", "original_sl", "fill_price", "exit_price", "net_cents"]
    pd.testing.assert_frame_equal(off.loc[common, cols], on.loc[common, cols])
    assert on.daily_state.eq("up").all()
    groups = {"shared": off.loc[common], "blocked_down": off.loc[off.daily_state.eq("down")],
              "blocked_flat": off.loc[off.daily_state.eq("flat")],
              "blocked_warmup": off.loc[off.daily_state.eq("unavailable")],
              "displaced_up": off.loc[off.daily_state.eq("up") & ~off.index.isin(common)],
              "newly_filled": on.loc[~on.index.isin(common)]}
    prior = pd.read_csv(M30_RUN / "summary.csv").set_index(["period", "arm"])
    rows, effects = [], []
    for era, (start, stop) in PERIODS.items():
        def part(f):
            return f.loc[(f.index >= pd.Timestamp(start)) & (f.index < pd.Timestamp(stop))]
        for name, f in (("baseline", off), ("D1_5", on)):
            rows.append(dict(period=era, arm=name, **metrics(part(f))))
            if name == "baseline":
                for key, val in metrics(part(f)).items():
                    np.testing.assert_allclose(val, prior.loc[(era, name), key], rtol=0, atol=1e-10)
        rows.append(dict(period=era, arm="M30_7", **prior.loc[(era, "slope_up")].to_dict()))
        totals = {}
        for name, f in groups.items():
            group = part(f)
            totals[name] = group.net_cents.sum()
            effects.append(dict(period=era, group=name, trades=len(group), net=totals[name]/100))
        assert sum(totals.values())-totals["newly_filled"] == part(off).net_cents.sum()
        assert totals["shared"]+totals["newly_filled"] == part(on).net_cents.sum()
    summary = pd.DataFrame(rows)
    summary["trades"] = summary.trades.astype(int)
    summary.to_csv(RUN / "summary.csv", index=False)
    pd.DataFrame(effects).to_csv(RUN / "attribution.csv", index=False)
    for arm, f in (("off", off), ("on", on)):
        f.to_csv(RUN / (arm + "_verified_trades.csv"))
    checks = dict(off=off_checks, on=on_checks, baseline_matches_archive=True)
    (RUN / "verification.json").write_text(json.dumps(checks, indent=2))
    print(summary.to_string(index=False), pd.DataFrame(effects).to_string(index=False), checks, sep="\n")


if __name__ == "__main__":
    main()
