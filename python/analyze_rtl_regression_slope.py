"""Independently verify native regression decisions, classify trades, and measure drawdown."""
import json
import numpy as np
import pandas as pd

from analyze_rtl_vwap_cross import parse_report
from prepare_rtl_regression_slope import BASE, CONTROL, PREFIX, ROOT, RUN, sha

END = pd.Timestamp("2026-10-01")
SYMBOL = "MNQcontDTBNT20102026_2"
COST_CENTS = 105
PERIODS = {
    "2010-15": ("2010", "2016"), "2016-19": ("2016", "2020"),
    "2020-Sep26": ("2020", END), "2016-Sep26": ("2016", END), "all": ("2010", END)
}


def verified_trades(arm, prices):
    tag = PREFIX + arm
    completion = json.loads((RUN / (tag + ".completed.json")).read_text())
    for name, digest in completion["outputs"].items():
        assert sha(RUN / name) == digest
    path = RUN / f"runband_{tag}_1.00.csv"
    if arm == "off":
        assert sha(path) == sha(BASE / f"runband_{CONTROL}_1.00.csv")
    ledger = pd.read_csv(path, encoding="utf-16", sep="\t").set_index("ticket")
    trades = parse_report(RUN / (tag + ".htm"), SYMBOL).set_index("ticket")
    assert trades.index.equals(ledger.index)
    np.testing.assert_array_equal(trades.trade_profit, ledger.trade_profit)
    np.testing.assert_array_equal(trades.trade_profit, 2 * (trades.exit_price - trades.fill_price))
    for col in ("entry_time", "exit_time"):
        np.testing.assert_array_equal(trades[col], pd.to_datetime(ledger[col], format="%Y.%m.%d %H:%M:%S"))
    summary = pd.read_csv(RUN / f"runband_{tag}_1.00_stats.csv", encoding="utf-16", sep="\t").iloc[0]
    assert len(trades) == summary.trades and trades.trade_profit.sum() == summary.net_profit
    decisions = pd.read_csv(RUN / f"decisions_{tag}.tsv", sep="\t")
    decisions.index = pd.to_datetime(decisions.bar, unit="s")
    decisions["signal"] = pd.to_datetime(decisions.signal, unit="s")
    assert decisions.index.is_unique and decisions.index.is_monotonic_increasing
    decisions = decisions.loc[decisions.index < END]
    signal_rows = prices.index.searchsorted(decisions.index, side="left") - 1
    assert (signal_rows >= 0).all()
    ref = prices.iloc[signal_rows]
    np.testing.assert_array_equal(ref.index, decisions.signal)
    np.testing.assert_allclose(ref.slope * 28, decisions.numerator, rtol=0, atol=1e-9)
    assert decisions.bars.eq(7).all() and ref.close.lt(ref.open).all()
    np.testing.assert_array_equal(decisions.allowed, (ref.slope.gt(0) | (arm == "off")).astype(int))
    trades = trades.loc[trades.submitted < END].copy()
    context = decisions.loc[trades.submitted.dt.floor("30min")]
    assert context.allowed.eq(1).all()
    signal = prices.loc[context.signal]
    np.testing.assert_array_equal(signal.high, trades.requested_price)
    np.testing.assert_array_equal(signal.low, trades.original_sl)
    trades["slope_numerator"] = context.numerator.to_numpy()
    trades["net_cents"] = (trades.trade_profit * 100).round().astype(int) - COST_CENTS
    trades = trades.set_index("submitted").sort_index()
    assert trades.index.is_unique and trades.exit_time.is_monotonic_increasing
    return trades, dict(trades_verified=len(ledger), decisions_verified=len(decisions),
                        exact_flat=int(ref.slope.eq(0).sum()), blocked=int(decisions.allowed.eq(0).sum()))


def metrics(frame):
    net = frame.net_cents.to_numpy()
    equity = np.r_[0, net.cumsum()]
    dd = (np.maximum.accumulate(equity) - equity).max()
    return dict(trades=len(net), net=net.sum()/100, closed_dd=dd/100,
                profit_factor=net[net > 0].sum() / -net[net < 0].sum() if any(net < 0) else None)


def main():
    prices = pd.read_csv(ROOT / "Reports/rtl_vwap_cross_20261027/features_NQ.csv",
                         usecols=["bar_time", "open", "high", "low", "close"], parse_dates=["bar_time"]).set_index("bar_time")
    assert prices.index.is_monotonic_increasing and prices.index.is_unique
    # Equivalent OLS slope via paired differences, independent of the EA loop.
    c = prices.close
    prices["slope"] = (3*(c-c.shift(6)) + 2*(c.shift(1)-c.shift(5)) + c.shift(2)-c.shift(4))/28
    off, off_checks = verified_trades("off", prices)
    on, on_checks = verified_trades("on", prices)
    common = off.index.intersection(on.index)
    cols = ["entry_time", "exit_time", "fill_price", "exit_price", "net_cents"]
    pd.testing.assert_frame_equal(off.loc[common, cols], on.loc[common, cols])
    cohorts = {"shared": off.loc[common], "blocked_baseline": off.loc[off.slope_numerator.le(0)],
               "displaced_up_baseline": off.loc[off.slope_numerator.gt(0) & ~off.index.isin(on.index)],
               "newly_filled": on.loc[~on.index.isin(off.index)]}
    rows, effects = [], []
    for era, (start, end) in PERIODS.items():
        def part(f):
            return f.loc[(f.index >= pd.Timestamp(start)) & (f.index < pd.Timestamp(end))]
        for arm, frame in (("baseline", off), ("slope_up", on)):
            rows.append(dict(period=era, arm=arm, **metrics(part(frame))))
        for name, frame in cohorts.items():
            sub = part(frame)
            effects.append(dict(period=era, group=name, trades=len(sub), net=sub.net_cents.sum()/100))
        left = sum(part(cohorts[k]).net_cents.sum() for k in ("shared", "blocked_baseline", "displaced_up_baseline"))
        right = sum(part(cohorts[k]).net_cents.sum() for k in ("shared", "newly_filled"))
        assert left == part(off).net_cents.sum() and right == part(on).net_cents.sum()
    for arm, frame in (("off", off), ("on", on)):
        frame.to_csv(RUN / (arm + "_verified_trades.csv"))
    stats = pd.DataFrame(rows)
    attribution = pd.DataFrame(effects)
    stats.to_csv(RUN / "summary.csv", index=False)
    attribution.to_csv(RUN / "attribution.csv", index=False)
    checks = dict(off=off_checks, on=on_checks, control_ledger_sha256=sha(BASE / f"runband_{CONTROL}_1.00.csv"))
    (RUN / "verification.json").write_text(json.dumps(checks, indent=2))
    print(stats.to_string(index=False), attribution.to_string(index=False), checks, sep="\n")


if __name__ == "__main__":
    main()
