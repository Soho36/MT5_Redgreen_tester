import unittest

import numpy as np
import pandas as pd

from reclaim_speed import signal_path, barrier_path, endpoint_metrics, match_pairs
from analyze_reclaim_speed import lagged_scale


class MinutePathTests(unittest.TestCase):
    def test_same_minute_recovery_is_one_minute(self):
        p = np.array([[11, 12, 10, 11], [11, 12, 9, 11]], dtype=float)
        result = signal_path(p, 10)
        self.assertEqual(result['breach_minute'], 1)
        self.assertEqual(result['recovery_delay'], 1)

    def test_slow_recovery_equal_close_and_recrossing(self):
        closes = [9, 9, 10, 9, 10, 11, 10, 9, 11]
        p = np.array([[11, 12, 8, c] for c in closes], dtype=float)
        result = signal_path(p, 10)
        self.assertEqual(result['recovery_delay'], 6)
        self.assertEqual(result['below_closes'], 4)
        self.assertEqual(result['recrossings'], 1)

    def test_unrecovered_and_transient_recovery_are_distinct(self):
        p = np.array([[11, 12, 9, 10], [10, 11, 8, 9]], dtype=float)
        self.assertTrue(np.isnan(signal_path(p, 10)['recovery_delay']))
        p[0, 3] = 11
        self.assertEqual(signal_path(p, 10)['recovery_delay'], 1)

    def test_first_barrier_and_both_hits(self):
        up_first = np.array([[10, 12, 10, 11], [11, 11, 8, 9]], dtype=float)
        a = barrier_path(up_first, 10, 4)
        b = barrier_path(up_first[::-1], 10, 4)
        self.assertEqual(a['hit_both'], 1)
        self.assertEqual(a['first_up'], 1)
        self.assertEqual(b['first_down'], 1)

    def test_same_minute_ambiguity_and_observed_open(self):
        p = np.array([[10, 13, 7, 11]], dtype=float)
        self.assertEqual(barrier_path(p, 10, 4)['first_ambiguous'], 1)
        p[0, 0] = 12
        self.assertEqual(barrier_path(p, 10, 4)['first_up'], 1)
        p[0, 0] = 8
        self.assertEqual(barrier_path(p, 10, 4)['first_down'], 1)

    def test_neither_and_endpoint_missing_values(self):
        self.assertEqual(barrier_path(np.array([[10, 11, 9, 10]]), 10, 4)['hit_neither'], 1)
        result = endpoint_metrics([.5, -.5, 0, np.nan])
        np.testing.assert_equal(result['balance'], [1, -1, 0, np.nan])
        np.testing.assert_equal(result['tails'], [1, 1, 0, np.nan])
        invalid = endpoint_metrics([np.inf, -np.inf])
        self.assertTrue(np.isnan(invalid['return_']).all())
        self.assertTrue(np.isnan(invalid['up']).all())


class DesignTests(unittest.TestCase):
    def test_lagged_volatility_excludes_signal_and_resets_at_roll(self):
        ix = pd.date_range('2020-01-01', periods=35, freq='30min')
        bars = pd.DataFrame({'open': 10., 'high': 11., 'low': 9., 'close': 10.}, index=ix)
        rolls = pd.DataFrame({'date': [ix[0], ix[18]], 'instrument_id': [1, 2]})
        original = lagged_scale(bars, rolls)
        self.assertTrue(original.iloc[:14].isna().all())
        self.assertEqual(original.iloc[14], 2)
        self.assertTrue(original.iloc[18:32].isna().all())
        self.assertEqual(original.iloc[32], 2)
        bars.iloc[15, bars.columns.get_loc('high')] = 100
        changed = lagged_scale(bars, rolls)
        pd.testing.assert_series_equal(changed.iloc[:16], original.iloc[:16])
        self.assertGreater(changed.iloc[16], original.iloc[16])

    def test_matching_calipers_years_and_no_replacement(self):
        a = pd.DataFrame(dict(year=[2020]*3, log_depth_a=[0, .1, 0], log_a=[0]*3,
                              log_range_a=[0]*3, breach_minute=[1]*3, clock_minutes=[600, 600, 900]))
        b = pd.DataFrame(dict(year=[2020, 2021, 2020], log_depth_a=[0, 0, 0], log_a=[0, 0, 2],
                              log_range_a=[0]*3, breach_minute=[1]*3, clock_minutes=[600]*3))
        self.assertEqual(match_pairs(a, b), [(0, 0, 0.)])
        a['future_return'] = [100, 0, -100]
        b['future_return'] = [-100, 100, 0]
        self.assertEqual(match_pairs(a, b), [(0, 0, 0.)])


if __name__ == '__main__':
    unittest.main()
