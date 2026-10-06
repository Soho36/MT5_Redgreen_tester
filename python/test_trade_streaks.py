"""Sequence tests that catch future-looking states and invalid stop timing."""
import unittest

import numpy as np

from analyze_trade_streaks import holm, run_summary, states, stop_mask


class StreakTests(unittest.TestCase):
    def test_preceding_state_and_zero_reset(self):
        net = [1, 2, -1, -2, 0, 1]
        before, after = states(net, [0]*6)
        np.testing.assert_array_equal(before, [0, 1, 2, -1, -2, 0])
        np.testing.assert_array_equal(after, [1, 2, -1, -2, 0, 1])

    def test_daily_reset_and_global_carry(self):
        net, day = [1, 1, 1, -1], [0, 0, 1, 1]
        np.testing.assert_array_equal(states(net, day, True)[0], [0, 1, 0, 1])
        np.testing.assert_array_equal(states(net, day, False)[0], [0, 1, 2, 3])

    def test_future_outcomes_do_not_change_state(self):
        a = states([1, 1, -1, 3], [0]*4)[0]
        b = states([1, 1, 1, -30], [0]*4)[0]
        np.testing.assert_array_equal(a[:3], b[:3])

    def test_keep_trigger_and_resume_next_session(self):
        take, triggers = stop_mask([1, 1, -9, 1, 1, 1, -9], [0, 0, 0, 1, 1, 1, 1], 1, 2)
        np.testing.assert_array_equal(take, [True, True, False, True, True, False, False])
        self.assertEqual(triggers, [1, 4])

    def test_first_trigger_only_even_if_later_streak(self):
        take, triggers = stop_mask([-1, -1, 20, -1, -1], [0]*5, -1, 2)
        self.assertEqual(triggers, [1])
        np.testing.assert_array_equal(take, [True, True, False, False, False])

    def test_terminal_run_count_not_future_selected(self):
        result = run_summary([1]*5 + [-1]*3 + [1], [0]*9, True)
        self.assertEqual(result, dict(runs=3, longest_win=5, longest_loss=3, win_runs_ge5=1, loss_runs_ge3=1))
        self.assertEqual(run_summary([1]*6, [0]*3+[1]*3, True)['longest_win'], 3)

    def test_holm_adjustment_missing(self):
        np.testing.assert_allclose(holm([.01, .04, .03, np.nan]), [.03, .06, .06, np.nan])


if __name__ == '__main__':
    unittest.main()
