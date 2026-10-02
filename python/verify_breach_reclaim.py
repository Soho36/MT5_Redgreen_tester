"""Independently verify saved Q8 classifications, windows and table partitions."""

import json
import numpy as np
import pandas as pd

from analyze_breach_reclaim import STUDY, ROOT, GROUPS, BREACHES
from analyze_price_levels import sha256


def main():
    f = pd.read_csv(STUDY / "attempt_features.csv", parse_dates=["signal_time", "submission_time"])
    t = pd.read_csv(STUDY / "trade_features.csv", parse_dates=["signal_time"])
    r = pd.read_csv(STUDY / "forward_responses.csv")
    bars = pd.read_csv(STUDY / "m30_reference.csv", index_col=0, parse_dates=[0])
    old_bars = pd.read_csv(ROOT / "Reports" / "price_levels_20261003" / "m30_reference.csv", index_col=0, parse_dates=[0])
    pd.testing.assert_frame_equal(bars, old_bars, check_names=False)
    for row in f.itertuples():
        if row.status != "eligible":
            expected = "unavailable"
        elif row.signal_open <= row.low:
            expected = "opened_at_or_below"
        elif row.signal_low > row.low:
            expected = "no_contact"
        elif row.signal_low == row.low:
            expected = "touch_only"
        elif row.signal_close > row.low:
            expected = "breach_reclaim"
        elif row.signal_close < row.low:
            expected = "breach_unrecovered"
        else:
            expected = "breach_exact_close"
        assert row.group == expected
        if expected in BREACHES:
            assert row.penetration_ticks == 4 * (row.low - row.signal_low)
            assert np.isclose(row.penetration_r, (row.low - row.signal_low) / row.candle_range)
        else:
            assert np.isnan(row.penetration_ticks) and np.isnan(row.penetration_r)

    original = pd.read_csv(ROOT / "Reports" / "price_levels_20261003" / "features.csv", parse_dates=["signal_time"])
    joined = t.merge(original, on=["source", "signal_time"], suffixes=("", "_old"), validate="one_to_one")
    assert len(joined) == len(original) == len(t)
    for key in ("low", "high", "signal_open", "signal_high", "signal_low", "signal_close", "net", "net_r"):
        assert np.allclose(joined[key], joined[key + "_old"], rtol=0, atol=1e-9, equal_nan=True), key
    assert (joined.status == joined.status_old).all()

    events = f[f.source == "current_session"].set_index("event_id")
    assert events.index.is_unique
    ends_frame = pd.read_csv(STUDY / "session_ends.csv", index_col=0, parse_dates=[0])
    ends = pd.to_datetime(ends_frame.iloc[:, 0])
    checks = 0
    for _, group in r.groupby(["horizon", "response_status"]):
        for row in group.sample(min(100, len(group)), random_state=20261003).itertuples():
            event = events.loc[row.event_id]
            start = event.signal_time + pd.Timedelta(minutes=30)
            endpoint = start + pd.Timedelta(minutes=30 * row.horizon)
            expected_times = pd.date_range(start, periods=row.horizon, freq="30min")
            if not start <= event.submission_time < start + pd.Timedelta(minutes=30):
                reason = "delayed_submission"
            elif bars.index.get_loc(event.signal_time) + row.horizon >= len(bars):
                reason = "end_of_data"
            elif endpoint > ends.loc[event.signal_time.normalize()]:
                reason = "session_end"
            elif not expected_times.isin(bars.index).all():
                reason = "missing_bar"
            else:
                reason = "eligible"
            assert row.response_status == reason
            if reason == "eligible":
                window = bars.loc[expected_times]
                value = (window.close.iloc[-1] - event.signal_close) / event.candle_range
                assert np.isclose(row.forward_r, value)
                assert row.up_half_r == int(value >= .5) and row.up_any == int(value > 0)
                assert np.isclose(row.up_excursion_r, (window.high.max() - event.signal_close) / event.candle_range)
                assert np.isclose(row.down_excursion_r, (window.low.min() - event.signal_close) / event.candle_range)
            else:
                assert np.isnan(row.forward_r) and np.isnan(row.up_half_r)
            checks += 1

    trade_groups = pd.read_csv(STUDY / "trade_groups.csv")
    price_groups = pd.read_csv(STUDY / "price_groups.csv")
    for source in f.source.unique():
        for period in f.period.unique():
            expected = t[(t.source == source) & (t.period == period)]
            grouped = trade_groups[(trade_groups.source == source) & (trade_groups.period == period) &
                                   (trade_groups.population == "source") & (trade_groups.year == "all") & trade_groups.group.isin(GROUPS)]
            assert grouped.n.sum() == len(expected)
            assert np.isclose(grouped.net.sum(), expected.net.sum(), rtol=0, atol=1e-7)
            for horizon in (1, 3, 6):
                grouped = price_groups[(price_groups.source == source) & (price_groups.period == period) &
                                       (price_groups.population == "source") & (price_groups.year == "all") &
                                       (price_groups.horizon == horizon) & price_groups.group.isin(GROUPS)]
                assert grouped.n.sum() == len(f[(f.source == source) & (f.period == period)])

    provenance = json.loads((STUDY / "provenance.json").read_text())
    checked_hashes = 0
    for file in provenance["files"]:
        if file["path"].endswith((".py", "BREACH_RECLAIM_PROTOCOL.md")):
            assert sha256(file["path"]) == file["sha256"], file["path"]
            checked_hashes += 1
    result = dict(classifications_checked=len(f), filled_level_rows_checked=len(t),
                  m30_reference_rows_checked=len(bars), direct_forward_windows_checked=checks,
                  script_protocol_hashes_checked=checked_hashes, partitions_reconcile=True)
    (STUDY / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
