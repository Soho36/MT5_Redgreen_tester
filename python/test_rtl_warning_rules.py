"""Focused state-machine and causality tests for the warning-based skip rules."""
import unittest

import numpy as np
import pandas as pd

import analyze_rtl_downtrend_oracle as oracle
from analyze_rtl_warning_rules import build_rules, rule_a, rule_b


def flags(length, *on):
    out = np.zeros(length, dtype=bool)
    out[list(on)] = True
    return out


class RuleATests(unittest.TestCase):
    def test_timeout_resumes_after_m_skipped_sessions(self):
        mask, periods = rule_a(flags(10, 2), flags(10), 3)
        self.assertEqual(list(np.flatnonzero(mask)), [3, 4, 5])
        self.assertEqual(periods, [dict(stop_close=2, resume_close=5, skipped=3, reason='timeout')])

    def test_bounce_resumes_next_session(self):
        mask, periods = rule_a(flags(10, 2), flags(10, 4), 20)
        self.assertEqual(list(np.flatnonzero(mask)), [3, 4])
        self.assertEqual(periods[0]['reason'], 'bounce')

    def test_signals_of_other_kind_ignored_within_state(self):
        mask, _ = rule_a(flags(12, 2, 3, 8), flags(12, 1, 5), 20)
        self.assertEqual(list(np.flatnonzero(mask)), [3, 4, 5, 9, 10, 11])

    def test_future_signals_cannot_change_past_mask(self):
        rng = np.random.default_rng(11)
        stop, bounce = rng.random(300) < .08, rng.random(300) < .08
        base, _ = rule_a(stop, bounce, 20)
        for k in range(10, 290, 23):
            changed_stop, changed_bounce = stop.copy(), bounce.copy()
            changed_stop[k:] = rng.random(300-k) < .3
            changed_bounce[k:] = rng.random(300-k) < .3
            np.testing.assert_array_equal(rule_a(changed_stop, changed_bounce, 20)[0][:k+1], base[:k+1])


class RuleBTests(unittest.TestCase):
    segment = dict(peak=3, stop_confirm=6, trough=8, resume_confirm=11, censored=False)

    def test_bounce_on_confirmation_close_skips_nothing(self):
        mask, periods = rule_b([self.segment], flags(15, 6), 15)
        self.assertFalse(mask.any())
        self.assertEqual(periods[0]['skipped'], 0)

    def test_first_bounce_after_confirmation_resumes(self):
        mask, _ = rule_b([self.segment], flags(15, 2, 8, 9), 15)
        self.assertEqual(list(np.flatnonzero(mask)), [7, 8])

    def test_without_bounce_matches_live_zigzag(self):
        mask, periods = rule_b([self.segment], flags(15, 12), 15)
        np.testing.assert_array_equal(mask, oracle.skip_mask([self.segment], 15, 'live_zigzag'))
        self.assertEqual(periods[0]['reason'], 'zigzag_rebound')

    def test_censored_final_fall_runs_to_end(self):
        censored = [dict(peak=3, stop_confirm=6, trough=9, resume_confirm=None, censored=True)]
        mask, periods = rule_b(censored, flags(12), 12)
        self.assertEqual(list(np.flatnonzero(mask)), [7, 8, 9, 10, 11])
        self.assertEqual(periods[0]['reason'], 'data_end')

    def test_full_pipeline_ignores_future_closes(self):
        rng = np.random.default_rng(13)
        closes = 100*np.exp(np.cumsum(rng.normal(0, .015, 400)))
        cutoffs = pd.DataFrame(dict(predictor=['rise_5', 'rise_10', 'rise_20', 'zscore_5', 'zscore_10', 'zscore_20'],
                                    stop_cutoff=[.03, .04, .06, 1.2, 1.2, 1.2],
                                    resume_cutoff=[-.025, -.035, -.05, -1.2, -1.2, -1.2]))
        base, _ = build_rules(closes, cutoffs, len(closes))
        for k in (60, 150, 290):
            changed = closes.copy()
            changed[k+1:] *= np.exp(np.cumsum(rng.normal(0, .03, len(closes)-k-1)))
            other, _ = build_rules(changed, cutoffs, len(closes))
            for rule in base:
                np.testing.assert_array_equal(other[rule][:k+2], base[rule][:k+2], err_msg=f'{rule} at {k}')


if __name__ == '__main__':
    unittest.main()
