"""Focused tests for the pullback/bounce warning statistics."""
import unittest

import numpy as np
import pandas as pd

from analyze_rtl_pullback_stats import (features, last_known_pivot, leg_masks, legs_table, next_turn_distance,
                                        shift_hit_rates, statistics, timing_classes, turn_targets)

SEGMENTS = [dict(peak=5, stop_confirm=7, trough=8, resume_confirm=10, censored=False),
            dict(peak=12, stop_confirm=13, trough=14, resume_confirm=None, censored=True)]


class TargetTests(unittest.TestCase):
    def test_target_windows_include_the_turn_and_k_sessions_before(self):
        stop, resume = turn_targets(SEGMENTS, 16, 2)
        self.assertEqual(list(np.flatnonzero(stop)), [3, 4, 5, 10, 11, 12])
        self.assertEqual(list(np.flatnonzero(resume)), [6, 7, 8])

    def test_unconfirmed_final_trough_is_not_known(self):
        self.assertEqual(last_known_pivot(SEGMENTS), 12)

    def test_legs_and_timing_classes(self):
        falling, rising = leg_masks(SEGMENTS, 16)
        self.assertEqual(list(np.flatnonzero(falling)), [6, 7, 8, 13, 14])
        self.assertEqual(list(np.flatnonzero(rising)), [9, 10, 11, 12])
        stop, _ = turn_targets(SEGMENTS, 16, 2)
        distance = next_turn_distance([5, 12], 16)
        self.assertEqual(list(distance[:6]), [5, 4, 3, 2, 1, 0])
        classes = timing_classes(stop, falling, distance, 2)
        self.assertEqual(classes[4], 'hit')
        self.assertEqual(classes[7], 'late')
        self.assertEqual(classes[1], 'early')
        self.assertEqual(classes[15], 'false_alarm')


class FeatureTests(unittest.TestCase):
    def test_formulas(self):
        rng = np.random.default_rng(3)
        closes = 100*np.exp(np.cumsum(rng.normal(0, .01, 60)))
        frame = features(closes)
        t = 40
        self.assertAlmostEqual(frame.rise_5[t], closes[t]/closes[t-5]-1)
        vol = np.std(np.diff(np.log(closes))[t-20:t], ddof=1)
        self.assertAlmostEqual(frame.vol[t], vol)
        self.assertAlmostEqual(frame.zscore_10[t], np.log(closes[t]/closes[t-10])/(vol*np.sqrt(10)))
        self.assertTrue(np.isnan(frame.zscore_5[19]))

    def test_future_closes_cannot_change_features(self):
        rng = np.random.default_rng(5)
        closes = 100*np.exp(np.cumsum(rng.normal(0, .01, 80)))
        changed = closes.copy()
        changed[51:] *= 1.3
        pd.testing.assert_frame_equal(features(closes).iloc[:51], features(changed).iloc[:51])


class StatisticTests(unittest.TestCase):
    def test_volatility_matched_base_and_shifts(self):
        target = np.array([1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1], dtype=bool)
        tercile = np.array([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2])
        signal = np.array([1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0], dtype=bool)
        timing = np.where(target, 'hit', 'false_alarm')
        row = statistics(signal, target, tercile, timing)
        self.assertEqual((row['signals'], row['hits']), (3, 3))
        self.assertAlmostEqual(row['base_rate'], 6/12)
        self.assertAlmostEqual(row['vol_matched_base'], (2/4+2/4+2/4)/3)
        rates = shift_hit_rates(signal, target)
        for j in range(12):
            self.assertAlmostEqual(rates[j], (np.roll(signal, j) & target).sum()/3)
        self.assertAlmostEqual(row['timing_hit'], 1.)

    def test_hazard_ages_use_leg_start(self):
        segments = [dict(peak=2, stop_confirm=3, trough=5, resume_confirm=6, censored=False),
                    dict(peak=9, stop_confirm=10, trough=11, resume_confirm=None, censored=True)]
        sessions = pd.date_range('2018-01-01', periods=12, freq='D')
        legs, hazard = legs_table(segments, sessions, 'raw', .02)
        self.assertEqual([(r['leg'], r['length']) for r in legs], [('falling', 3), ('rising', 4)])
        rising = [(r['age'], r['turn_within_2']) for r in hazard if r['leg'] == 'rising']
        self.assertEqual(rising, [(1, False), (2, True), (3, True), (4, True)])


if __name__ == '__main__':
    unittest.main()
