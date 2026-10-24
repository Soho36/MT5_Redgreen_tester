"""Focused zigzag, delay, causality and roll tests for the downtrend crystal ball."""
import unittest

import numpy as np
import pandas as pd

from analyze_rtl_downtrend_oracle import roll_adjusted_closes, shift_controls, skip_mask, zigzag


class ZigzagTests(unittest.TestCase):
    def test_simple_pivots_and_confirmations(self):
        closes = [100, 102, 104, 101, 99, 98, 100, 103, 105, 102]
        self.assertEqual(zigzag(closes, .05), [dict(peak=2, stop_confirm=5, trough=5, resume_confirm=7, censored=False)])

    def test_exact_threshold_confirms(self):
        self.assertEqual(zigzag([100, 50], .5)[0]['stop_confirm'], 1)
        segments = zigzag([100, 50, 75], .5)
        self.assertEqual(segments[0]['resume_confirm'], 2)
        self.assertEqual(zigzag([100, 50.01], .5), [])

    def test_ties_move_extremes_later(self):
        self.assertEqual(zigzag([100, 50, 60, 50, 80], .5)[0]['trough'], 3)
        segment = zigzag([100, 150, 140, 150, 70], .5)[0]
        self.assertEqual(segment['peak'], 3)

    def test_tentative_final_leg_is_censored(self):
        segment = zigzag([100, 150, 140, 150, 70], .5)[0]
        self.assertTrue(segment['censored'])
        self.assertIsNone(segment['resume_confirm'])
        self.assertEqual(segment['trough'], 4)

    def test_undecided_start_can_confirm_rise_first(self):
        segments = zigzag([100, 90, 140, 60], .5)
        self.assertEqual([(s['peak'], s['trough']) for s in segments], [(2, 3)])


class MaskTests(unittest.TestCase):
    segments = [dict(peak=2, stop_confirm=5, trough=5, resume_confirm=7, censored=False)]

    def test_oracle_delays_shift_stop_and_resume(self):
        self.assertEqual(list(np.flatnonzero(skip_mask(self.segments, 10, 'oracle_d0'))), [3, 4, 5])
        self.assertEqual(list(np.flatnonzero(skip_mask(self.segments, 10, 'oracle_d2'))), [5, 6, 7])
        self.assertEqual(list(np.flatnonzero(skip_mask(self.segments, 10, 'oracle_d5'))), [8, 9])
        self.assertFalse(skip_mask(self.segments, 10, 'oracle_d20').any())

    def test_live_rule_skips_after_confirmation_through_rebound(self):
        self.assertEqual(list(np.flatnonzero(skip_mask(self.segments, 10, 'live_zigzag'))), [6, 7])
        censored = [dict(peak=2, stop_confirm=5, trough=8, resume_confirm=None, censored=True)]
        self.assertEqual(list(np.flatnonzero(skip_mask(censored, 10, 'live_zigzag'))), [6, 7, 8, 9])

    def test_live_rule_ignores_future_closes(self):
        rng = np.random.default_rng(7)
        closes = 100*np.exp(np.cumsum(rng.normal(0, .015, 600)))
        base = skip_mask(zigzag(closes, .03), len(closes), 'live_zigzag')
        changed_oracle = False
        for k in range(20, 590, 37):
            future = closes.copy()
            future[k+1:] *= np.exp(np.cumsum(rng.normal(0, .02, len(closes)-k-1)))
            np.testing.assert_array_equal(skip_mask(zigzag(future, .03), len(closes), 'live_zigzag')[:k+2], base[:k+2])
            oracle = skip_mask(zigzag(future, .03), len(closes), 'oracle_d0')[:k+1]
            changed_oracle |= not np.array_equal(oracle, skip_mask(zigzag(closes, .03), len(closes), 'oracle_d0')[:k+1])
        self.assertTrue(changed_oracle, 'hindsight rule should depend on later closes')


class ControlTests(unittest.TestCase):
    def test_roll_adjustment_removes_only_switch_gap(self):
        index = pd.date_range('2020-01-01', periods=6, freq='D')
        daily = pd.DataFrame(dict(open=[10, 11, 12, 15, 14, 15.], close=[11, 12, 13, 14, 15, 16.]), index=index)
        adjusted = roll_adjusted_closes(daily, [index[3]])
        raw_returns, new_returns = daily.close.pct_change(), adjusted.pct_change()
        for position in (1, 2, 4, 5):
            self.assertAlmostEqual(new_returns.iloc[position], raw_returns.iloc[position])
        self.assertAlmostEqual(new_returns.iloc[3], 14/15-1)
        np.testing.assert_allclose(adjusted.iloc[3:], daily.close.iloc[3:])

    def test_shift_controls_match_brute_force(self):
        pnl = np.array([5., -3., 2., -8., 4., 1.])
        hours = np.array([1., 2., 1., 3., 1., 1.])
        mask = np.array([False, True, True, False, False, False])
        kept = pnl*~mask
        result, nets = shift_controls(pnl, hours, mask, kept.sum(), 3.)
        for k in range(len(pnl)):
            self.assertAlmostEqual(nets[k], (pnl*~np.roll(mask, k)).sum())
        self.assertEqual(result['shifts'], 6)
        self.assertGreaterEqual(result['share_shifts_net_at_least_rule'], 1/6)


if __name__ == '__main__':
    unittest.main()
