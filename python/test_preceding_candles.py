"""Boundary and chronology tests for the two new feature definitions."""

import unittest
import numpy as np

from analyze_preceding_candles import features


def bars(close, opening=None, low=None):
    c = np.array([close], dtype=float)
    o = np.array([opening], dtype=float) if opening is not None else c + 1
    return dict(C=c, O=o, H=np.maximum(o, c) + 1,
                L=np.array([low], dtype=float) if low is not None else np.minimum(o, c) - 1)


class PrecedingCandlesTests(unittest.TestCase):
    def test_chronological_direction_and_signal_exclusion(self):
        # Newest first; preceding closes fell from 6 to 2.
        d = bars([100, 2, 3, 4, 5, 6])
        red, down, flag, _, valid = features(d, 5)
        self.assertEqual(red[0], 1)
        self.assertEqual(down[0], 1)
        self.assertTrue(flag[0] and valid[0])
        d["C"][0, 0] = -100  # Changing the signal cannot change preceding shares.
        self.assertEqual(features(d, 5)[1][0], 1)

    def test_doji_equal_closes_and_threshold(self):
        d = bars([0, 1, 1, 2, 3, 4], [1, 2, 1, 3, 3, 5])
        red, down, flag, _, _ = features(d, 5)
        self.assertEqual(red[0], .6)
        self.assertEqual(down[0], .75)
        self.assertTrue(flag[0])

    def test_recovery_and_equality(self):
        d = bars([10, 12, 12, 12, 12, 12], low=[9, 10, 11, 11, 11, 11])
        self.assertEqual(features(d, 5)[3][0], 1)  # Close on old low is not recovery.
        d["C"][0, 0] = 10.25
        self.assertEqual(features(d, 5)[3][0], 2)
        d["L"][0, 0] = 10
        self.assertEqual(features(d, 5)[3][0], 0)  # Equal low is not a breach.

    def test_longer_context_can_change_classification(self):
        d = bars([10.5] + [12] * 10, low=[9] + [10] * 5 + [8] * 5)
        self.assertEqual(features(d, 5)[3][0], 2)
        self.assertEqual(features(d, 10)[3][0], 0)

    def test_extra_logged_bars_do_not_change_short_window(self):
        d = bars([10] + [12] * 50)
        before = features(d, 5)
        for key in "OHLC":
            d[key][:, 6:] = -999
        after = features(d, 5)
        for a, b in zip(before, after):
            np.testing.assert_array_equal(a, b)

    def test_missing_history_is_explicit(self):
        with self.assertRaises(ValueError):
            features(bars([1, 2, 3]), 5)
        d = bars([1, 2, 3, 4, 5, 6])
        d["C"][0, 2] = np.nan
        self.assertFalse(features(d, 5)[4][0])


if __name__ == "__main__":
    unittest.main()
