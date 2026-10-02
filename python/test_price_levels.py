"""Adversarial timing/roll tests for price-level research."""

import unittest

import numpy as np
import pandas as pd

from analyze_price_levels import build_level_maps, distance_bin, masks


def make_bars(times, highs, lows):
    return pd.DataFrame(dict(open=lows, high=highs, low=lows, close=highs), index=pd.to_datetime(times))


def make_rolls(dates=("2026-01-01",), ids=(100,)):
    return pd.DataFrame(dict(date=dates, instrument_id=ids))


class LevelTests(unittest.TestCase):
    def test_current_excludes_signal_future_and_equal_retests_do_not_reset_age(self):
        bars = make_bars([f"2026-01-05 {t}" for t in ("01:00", "01:30", "02:00", "02:30")],
                         [110, 110, 999, 1000], [100, 100, 1, 0])
        result = build_level_maps(bars, make_rolls())["current_session"]
        self.assertEqual(result.iloc[0].status, "no_prior_session_bar")
        self.assertEqual(result.iloc[2].high, 110)
        self.assertEqual(result.iloc[2].low, 100)
        self.assertEqual(result.iloc[2].high_time, bars.index[0])
        self.assertEqual(result.iloc[2].low_time, bars.index[0])
        changed = bars.copy()
        changed.iloc[2:, changed.columns.get_loc("high")] = 5000
        changed.iloc[2:, changed.columns.get_loc("low")] = -5000
        after = build_level_maps(changed, make_rolls())["current_session"]
        pd.testing.assert_series_equal(result.iloc[2], after.iloc[2])

    def test_previous_available_session_skips_weekend_and_holiday(self):
        bars = make_bars(["2026-01-02 01:00", "2026-01-02 19:30", "2026-01-06 01:00"],
                         [110, 120, 900], [100, 95, 0])
        row = build_level_maps(bars, make_rolls())["previous_session"].iloc[-1]
        self.assertEqual(row.high, 120)
        self.assertEqual(row.low, 95)
        self.assertEqual(row.high_age_sessions, 1)
        self.assertEqual(row.source_end, pd.Timestamp("2026-01-02 19:30"))

    def test_previous_week_is_calendar_week_not_last_five_sessions(self):
        bars = make_bars(["2026-01-02 01:00", "2026-01-05 01:00", "2026-01-09 01:00",
                          "2026-01-12 01:00", "2026-01-13 01:00"],
                         [999, 110, 120, 130, 140], [1, 100, 90, 80, 70])
        maps = build_level_maps(bars, make_rolls())
        for idx in (-2, -1):
            row = maps["previous_week"].iloc[idx]
            self.assertEqual(row.high, 120)
            self.assertEqual(row.low, 90)
        self.assertEqual(maps["previous_session"].iloc[-1].high, 130)

    def test_roll_excludes_entire_mixed_week_and_old_session(self):
        bars = make_bars(["2026-01-05 01:00", "2026-01-06 01:00", "2026-01-06 01:30",
                          "2026-01-09 01:00", "2026-01-12 01:00"],
                         [110, 210, 220, 230, 240], [100, 200, 190, 180, 170])
        rolls = make_rolls(("2026-01-01", "2026-01-06"), (100, 200))
        maps = build_level_maps(bars, rolls)
        self.assertEqual(maps["previous_session"].iloc[1].status, "contract_roll")
        self.assertEqual(maps["current_session"].iloc[2].status, "eligible")
        self.assertEqual(maps["previous_session"].iloc[-1].status, "eligible")
        self.assertEqual(maps["previous_week"].iloc[-1].status, "contract_roll")

    def test_distance_boundaries_and_missing_not_unlimited_room(self):
        d = np.array([-1, 0, .25, .5, .75, 1, 2, np.nan])
        self.assertEqual(distance_bin(d).tolist(), ["below_0", "exact_0", "0_to_0.5", "0_to_0.5",
                                                   "0.5_to_1", "0.5_to_1", "above_1", "unavailable"])
        bad, control = masks(pd.DataFrame(dict(room=d)), "room", 1)
        self.assertEqual(np.where(bad)[0].tolist(), [2, 3, 4, 5])
        self.assertEqual(np.where(control)[0].tolist(), [6])
        far, near = masks(pd.DataFrame(dict(support=d)), "support", .5)
        self.assertEqual(np.where(far)[0].tolist(), [4, 5, 6])
        self.assertEqual(np.where(near)[0].tolist(), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
