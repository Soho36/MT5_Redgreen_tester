"""Boundary cases for slope availability and strict direction, without trading outcomes."""
import unittest

import numpy as np
import pandas as pd

from analyze_rtl_vwap_slope import slope_features


class SlopeTests(unittest.TestCase):
    def frame(self):
        times = pd.to_datetime(['2020-01-02 01:00', '2020-01-02 01:30', '2020-01-02 02:00',
                                '2020-01-02 02:30', '2020-01-03 01:00', '2020-01-03 02:00'])
        return pd.DataFrame(dict(bar_time=times, feature_session=times.normalize(), vwap=[100, 101, 100, 100, 90, 92],
                                 vwap_available=True, cum_volume=[10, 20, 30, 40, 10, 20], a20=np.nan))

    def test_up_down_flat_reset_gap_without_a20(self):
        s = slope_features(self.frame())
        self.assertEqual(s.slope_state.tolist(), ['unknown', 'up', 'down', 'flat', 'unknown', 'unknown'])
        self.assertEqual(s.slope_reason.tolist(), ['session_start', '', '', '', 'session_start', 'time_gap'])
        self.assertEqual(s.slope_delta.iloc[1:4].tolist(), [1., -1., 0.])
        self.assertTrue(s.slope_per_a20.isna().all())

    def test_missing_volume_and_unavailable_reference(self):
        f = self.frame()
        f.loc[1, 'cum_volume'] = 10
        f.loc[2, 'vwap'] = np.nan
        s = slope_features(f)
        self.assertEqual(s.slope_reason.iloc[1], 'no_added_volume')
        self.assertEqual(s.slope_state.iloc[2:4].tolist(), ['unknown', 'unknown'])

    def test_future_rows_do_not_change_past_slope(self):
        f = self.frame()
        before = slope_features(f.iloc[:3])
        f.loc[3:, 'vwap'] = 99999
        pd.testing.assert_frame_equal(before, slope_features(f).iloc[:3])


if __name__ == '__main__':
    unittest.main()
