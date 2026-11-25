"""Audit both native runs and compare them with the archived ungated GG replay."""
import json

import numpy as np
import pandas as pd

import analyze_gg_vwap as gg
import verify_gg_vwap_ea as old
from replay_gg_open_vwap import PREFIX, RUN, sha256


def check_decisions(tag, column, features, trades):
    log = pd.read_csv(RUN / f"vwap_decisions_{tag}.csv", sep="\t", encoding="cp1252")
    for col in ("signal_bar", "time"):
        log[col] = pd.to_datetime(log[col], format="%Y.%m.%d %H:%M:%S")
    assert features.bar_time.is_unique and log.time.is_unique
    d = log.merge(features, left_on="signal_bar", right_on="bar_time", how="left",
                  validate="many_to_one", suffixes=("_ea", ""))
    inside = d.signal_bar <= features.bar_time.max()
    assert d.loc[inside, "available_at"].le(d.loc[inside, "time"]).all()
    assert d.loc[inside, "open"].eq(d.loc[inside, "signal_open"]).all()
    assert d.loc[inside, "close"].eq(d.loc[inside, "signal_close"]).all()
    assert (d.signal_open < d.signal_close).all()
    known = (d.feature_session.eq(d.time.dt.normalize()) & d.vwap_available.eq(True)
             & d.vwap.notna() & d.a20.gt(0))
    blocked = known & d[column].lt(d.vwap - d.a20)
    assert d.known.eq(known).all() and d.blocked.eq(blocked).all()
    for name in ("vwap", "a20"):
        np.testing.assert_allclose(d.loc[known, name + "_ea"], d.loc[known, name], rtol=0, atol=1e-7)
    # MT5 records actual submission to the second. The EA logs the M30 bar's start.
    submissions = trades.submitted.dt.floor("30min")
    allowed = d.loc[~blocked].set_index("time").reindex(submissions)
    assert allowed.signal_bar.notna().all()
    assert np.array_equal(allowed.high.to_numpy(), trades.requested_price.to_numpy())
    assert np.array_equal(allowed.low.to_numpy(), trades.original_sl.to_numpy())
    return dict(candidates=len(d), known=int(known.sum()), blocked=int(blocked.sum()),
                candidates_after_labels=int((~inside).sum()), verified_fills=len(trades))


def main():
    for path in (gg.CROSS / "features_NQ.csv", gg.CROSS / "calendars.csv"):
        assert sha256(path) == gg.FROZEN[path]
    assert json.loads((old.RUN / "verification.json").read_text())["passed"]
    close_ledger = RUN / f"rtlvwap_{PREFIX}close_1.00.csv"
    assert sha256(close_ledger) == sha256(old.RUN / "rtlvwap_ggvwap_20261030_on_1.00.csv")
    base = old.trades_of(old.RUN / "ggvwap_20261030_off.htm", gg.SPEC)
    curves = {"baseline": base}
    features = gg.load_features()
    checks = {"close_ledger_identical": True}
    for variant in ("open", "close"):
        tag = PREFIX + variant
        curves[variant] = old.trades_of(RUN / f"{tag}.htm", gg.SPEC)
        checks[variant] = check_decisions(tag, variant, features, curves[variant])
    cal = gg.nq_calendar()
    periods = dict(old.PERIODS, full=("2010-01-01", "2026-10-01"),
                   YTD2026=("2026-01-01", "2026-10-01"))
    rows = []
    for period, (start, end) in periods.items():
        for policy, t in curves.items():
            sample = t[t.session.ge(start) & t.session.lt(end)]
            metrics = old.metrics(sample, cal[(cal >= start) & (cal < end)])
            rows.append(dict(period=period, policy=policy, **metrics))
    result = pd.DataFrame(rows)
    result.to_csv(RUN / "comparison.csv", index=False)
    (RUN / "verification.json").write_text(json.dumps(checks, indent=2))
    print(result.to_string(index=False))
    print(json.dumps(checks))


if __name__ == "__main__":
    main()
