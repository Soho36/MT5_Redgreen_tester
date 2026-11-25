"""Reconcile both native GG runs to the tester and compare the historical periods."""
import json

import numpy as np
import pandas as pd

import analyze_gg_vwap as gg
import analyze_rtl_vwap_cross as cx
from audit_granularity_ledgers import digest, reconcile_totals
from prepare_gg_close_entry import BASE, OLD_TAG, RUN
from verify_gg_vwap_ea import PERIODS, metrics


def main():
    periods = dict(PERIODS, full=("2010-01-01", "2026-10-01"))
    features = gg.load_features().sort_values("bar_time")
    # At the decision bar's first quote, index 1 is the previous observed M30 bar.
    previous = features[["open", "low", "high", "close"]].shift().add_prefix("signal_")
    bars = features[["bar_time", "first_minute", "open"]].join(previous).set_index("bar_time")
    calendar = gg.nq_calendar()
    results, verification = [], {}
    for mode in ("high", "close"):
        tag = f"gg_entry_20261125_{mode}"
        ledger = RUN / f"runband_{tag}_1.00.csv"
        if mode == "high":
            assert digest(ledger) == gg.FROZEN[BASE / f"runband_{OLD_TAG}_1.00.csv"]
        completed = json.loads((RUN / f"{tag}.completed.json").read_text())
        for filename, expected in completed["outputs"].items():
            assert digest(RUN / filename) == expected
        data = cx.parse_report(RUN / f"{tag}.htm", gg.SPEC["symbol"],
                               entry_type="buy" if mode == "close" else "buy stop")
        reconcile_totals(data, RUN / f"runband_{tag}_1.00_stats.csv", tag)
        np.testing.assert_allclose(data.trade_profit, (data.exit_price - data.fill_price) * 2, rtol=0, atol=1e-8)
        data = cx.economics(data, gg.SPEC)
        data = data[data.session < "2026-10-01"].copy()
        matched = data.join(bars, on=data.submitted.dt.floor("30min"))
        assert matched.signal_close.gt(matched.signal_open).all()
        assert matched.original_sl.eq(matched.signal_low).all()
        if mode == "close":
            assert matched.entry_time.eq(matched.submitted).all()
            assert matched.entry_time.dt.floor("min").eq(matched.first_minute).all()
            assert matched.fill_price.eq(matched.requested_price).all()
            assert matched.fill_price.eq(matched.open + 0.25).all()
            delta = matched.fill_price - matched.signal_close
            verification["close_fill_minus_signal_close_points"] = dict(
                exact=int(delta.eq(0).sum()), count=len(delta), mean=float(delta.mean()),
                median=float(delta.median()), mean_absolute=float(delta.abs().mean()))
        else:
            assert matched.requested_price.eq(matched.signal_high).all()
        for name, (start, end) in periods.items():
            sample = data[data.session.ge(start) & data.session.lt(end)]
            stats = metrics(sample, calendar[(calendar >= start) & (calendar < end)])
            if mode == "high" and name in gg.PUBLISHED:
                n, net = gg.PUBLISHED[name]
                assert len(sample) == n and abs(stats["net_dollars"] - net) < 0.005
            results.append(dict(period=name, entry=mode, **stats, gross=sample.trade_profit.sum(),
                                win_pct=100 * sample.net_dollars.gt(0).mean()))
    frame = pd.DataFrame(results)
    frame.to_csv(RUN / "comparison.csv", index=False)
    (RUN / "verification.json").write_text(json.dumps(verification, indent=2))
    print(frame.round(3).to_string(index=False))
    print(json.dumps(verification))


if __name__ == "__main__":
    main()
