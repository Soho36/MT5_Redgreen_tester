"""Focused mask tests for the early-signal crystal-ball addendum."""
import unittest

import numpy as np

from analyze_rtl_downtrend_early import early_mask
from analyze_rtl_downtrend_oracle import skip_mask


def positions(mask):
    return list(np.flatnonzero(mask))


class EarlyMaskTests(unittest.TestCase):
    segment = dict(peak=6, stop_confirm=8, trough=9, resume_confirm=11, censored=False)

    def test_on_time_reference_matches_first_study(self):
        segments = [self.segment, dict(peak=13, stop_confirm=15, trough=17, resume_confirm=19, censored=False)]
        np.testing.assert_array_equal(early_mask(segments, 20, 'oracle_d0'), skip_mask(segments, 20, 'oracle_d0'))

    def test_symmetric_early_moves_both_ends(self):
        self.assertEqual(positions(early_mask([self.segment], 20, 'oracle_d0')), [7, 8, 9])
        self.assertEqual(positions(early_mask([self.segment], 20, 'early_e2')), [5, 6, 7])

    def test_early_stop_keeps_on_time_resume(self):
        self.assertEqual(positions(early_mask([self.segment], 20, 'early_stop_e3')), [4, 5, 6, 7, 8, 9])

    def test_clipped_at_first_session(self):
        segment = dict(peak=1, stop_confirm=3, trough=4, resume_confirm=6, censored=False)
        self.assertEqual(positions(early_mask([segment], 10, 'early_e5')), [])
        self.assertEqual(positions(early_mask([segment], 10, 'early_e3')), [0, 1])
        self.assertEqual(positions(early_mask([segment], 10, 'early_stop_e5')), [0, 1, 2, 3, 4])

    def test_overlapping_windows_merge(self):
        segments = [dict(peak=2, stop_confirm=4, trough=5, resume_confirm=6, censored=False),
                    dict(peak=7, stop_confirm=9, trough=10, resume_confirm=12, censored=False)]
        mask = early_mask(segments, 15, 'early_stop_e3')
        self.assertEqual(positions(mask), list(range(0, 11)))
        self.assertEqual(mask.sum(), 11)


if __name__ == '__main__':
    unittest.main()
