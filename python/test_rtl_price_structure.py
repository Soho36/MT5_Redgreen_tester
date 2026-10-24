"""Focused mathematical and causal tests for the frozen structure study."""
import unittest

import numpy as np
import pandas as pd

from analyze_rtl_price_structure import build_features, classify_features, label_trades


def bars(close, *, opening=None, high=None, low=None, index=None):
    close = np.asarray(close, dtype=float)
    opening = close.copy() if opening is None else np.asarray(opening, dtype=float)
    high = np.maximum(opening, close) + 1 if high is None else np.asarray(high, dtype=float)
    low = np.minimum(opening, close) - 1 if low is None else np.asarray(low, dtype=float)
    if index is None:
        index = pd.date_range("2018-01-02 01:00", periods=len(close), freq="30min")
    return pd.DataFrame(dict(open=opening, high=high, low=low, close=close), index=index)


class StructureTests(unittest.TestCase):
    def test_identical_flat_bars_have_no_wicks(self):
        frame = bars([10]*6, high=[10]*6, low=[10]*6)
        result = build_features(frame, 3)
        self.assertFalse(result.valid.iloc[:3].any())
        self.assertTrue(result.valid.iloc[3:].all())
        np.testing.assert_array_equal(result.efficiency.iloc[3:], 0.)
        np.testing.assert_array_equal(result.overlap.iloc[3:], 1.)
        np.testing.assert_array_equal(result.wick.iloc[3:], 0.)
        np.testing.assert_array_equal(result.wick80_fraction.iloc[3:], 0.)

    def test_straight_nonoverlapping_progress(self):
        frame = bars([10, 11, 12, 13, 14], opening=[9, 10, 11, 12, 13],
                     high=[10, 11, 12, 13, 14], low=[9, 10, 11, 12, 13])
        result = build_features(frame, 3).iloc[-1]
        self.assertEqual(result.efficiency, 1.)
        self.assertEqual(result.overlap, 0.)
        self.assertEqual(result.wick, 0.)

    def test_alternating_closes_have_little_progress(self):
        frame = bars([10, 12, 10, 12, 10], opening=[12, 10, 12, 10, 12],
                     high=[13]*5, low=[9]*5)
        result = build_features(frame, 4).iloc[-1]
        self.assertEqual(result.efficiency, 0.)
        self.assertEqual(result.overlap, 1.)
        self.assertEqual(result.wick, .5)
        self.assertEqual(result.wick80_fraction, 0.)

    def test_efficiency_needs_starting_close_outside_n_candles(self):
        frame = bars([100, 110, 105, 106])
        result = build_features(frame, 3)
        self.assertFalse(result.valid.iloc[2])
        self.assertAlmostEqual(result.efficiency.iloc[3], 6 / 16)

    def test_overlap_uses_internal_n_minus_one_pairs(self):
        frame = bars([100, 1, 2, 3], high=[101, 2, 4, 4], low=[99, 0, 1, 2])
        result = build_features(frame, 3).iloc[-1]
        self.assertAlmostEqual(result.overlap, (1/4 + 2/3) / 2)

    def test_persistent_wick_fraction_and_zero_bar(self):
        frame = bars([5, 5, 5, 6], opening=[5, 5, 5, 5],
                     high=[5, 10, 5, 10], low=[5, 0, 5, 0])
        result = build_features(frame, 3).iloc[-1]
        self.assertAlmostEqual(result.wick, (1 + 0 + .9) / 3)
        self.assertAlmostEqual(result.wick80_fraction, 2/3)

    def test_cutoff_equality_is_in_candidate_and_high_wick(self):
        frame = bars([10, 12, 10, 12, 10], high=[13]*5, low=[9]*5)
        f = build_features(frame, 4)
        cuts = dict(efficiency_low=float(f.efficiency.iloc[-1]),
                    overlap_high=float(f.overlap.iloc[-1]), wick_high=float(f.wick.iloc[-1]))
        result = classify_features(f, cuts)
        self.assertEqual(result.group.iloc[-1], "low_eff_high_overlap")
        self.assertTrue(result.high_wick.iloc[-1])

    def test_roll_flag_is_first_observed_bar_not_whole_date(self):
        frame = bars(np.arange(12)+10)
        f = build_features(frame, 3, [frame.index[0]])
        self.assertFalse(f.roll_clean.iloc[3])
        self.assertTrue(f.roll_clean.iloc[4])

    def test_roll_flag_includes_extra_starting_close(self):
        index = pd.to_datetime(["2018-01-02 23:00", "2018-01-02 23:30", "2018-01-03 01:00",
                                "2018-01-03 01:30", "2018-01-03 02:00", "2018-01-03 02:30",
                                "2018-01-03 03:00"])
        f = build_features(bars(np.arange(7)+10, index=index), 3, [index[2]])
        self.assertFalse(f.roll_clean.iloc[5])
        self.assertTrue(f.roll_clean.iloc[6])

    def test_future_candles_cannot_change_past_features(self):
        frame = bars(100 + np.sin(np.arange(60)) * 3 + np.arange(60) / 4)
        before = build_features(frame, 10)
        frame.iloc[35:] *= np.linspace(1.3, 2., 25)[:, None]
        after = build_features(frame, 10)
        pd.testing.assert_frame_equal(before.iloc[:35], after.iloc[:35], check_exact=True)

    def test_m30_completion_boundary_and_gap_asof(self):
        index = pd.to_datetime(["2018-01-02 21:30", "2018-01-02 22:00", "2018-01-02 22:30",
                                "2018-01-02 23:00", "2018-01-02 23:30", "2018-01-03 01:00"])
        frame = bars([10, 11, 12, 13, 14, 15], index=index)
        f = classify_features(build_features(frame, 3),
                              dict(efficiency_low=.2, overlap_high=.8, wick_high=.8))
        decisions = pd.DataFrame({"submitted": pd.to_datetime(["2018-01-03 01:29:59", "2018-01-03 01:30:00",
                                                               "2018-01-03 01:31:01"])})
        result = label_trades(decisions, f, "m30", 3)
        expected = [index[4], index[5], index[5]]
        self.assertEqual(list(pd.to_datetime(result.m30_3_last_bar_time)), expected)

    def test_daily_uses_strictly_previous_observed_date(self):
        index = pd.to_datetime(["2018-01-02", "2018-01-03", "2018-01-04", "2018-01-05", "2018-01-08"])
        frame = bars([10, 11, 12, 13, 14], index=index)
        f = classify_features(build_features(frame, 3, timeframe="d1"),
                              dict(efficiency_low=.2, overlap_high=.8, wick_high=.8))
        decisions = pd.DataFrame({"submitted": pd.to_datetime(["2018-01-08 01:00", "2018-01-08 23:59", "2018-01-09 01:00"])})
        result = label_trades(decisions, f, "d1", 3)
        self.assertEqual(list(pd.to_datetime(result.d1_3_last_bar_time)), [index[3], index[3], index[4]])


if __name__ == "__main__":
    unittest.main()
