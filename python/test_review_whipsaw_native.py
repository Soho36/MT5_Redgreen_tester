"""Review helpers: drawdown along full session paths, scaled envelopes, month resampling."""
import unittest

import numpy as np
import pandas as pd

import review_whipsaw_native as review


def brute_drawdown(values):
    values = np.r_[0.0, values]
    return max(values[:i + 1].max() - values[i] for i in range(len(values)))


class ReviewHelpers(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(3)
        self.dates = pd.date_range('2024-01-01', periods=40)
        self.paths = {d: np.cumsum(rng.normal(0, 10, rng.integers(1, 30))) for d in self.dates[::2]}   # every other day idle

    def test_path_drawdown_equals_brute_force_over_the_joined_path(self):
        level, joined = 0.0, []
        for d in self.dates:
            piece = self.paths.get(d, np.zeros(1))
            joined.extend(level + piece)
            level += piece[-1]
        got = review.path_drawdown(self.paths.get(d, np.zeros(1)) for d in self.dates)
        self.assertAlmostEqual(got, brute_drawdown(np.array(joined)), places=9)

    def test_scaled_envelopes_equal_scaled_full_paths(self):
        env = review.envelopes(self.paths, self.dates)
        self.assertAlmostEqual(env.net.sum(), sum(p[-1] for p in self.paths.values()))
        multiple = np.where(np.arange(len(self.dates)) % 4 == 0, 2, 1)      # two contracts on some active days
        direct = review.path_drawdown(self.paths.get(d, np.zeros(1)) * m for d, m in zip(self.dates, multiple))
        self.assertAlmostEqual(review.scaled_drawdown(env, multiple)[0], direct, places=9)
        both = review.scaled_drawdown(env, np.vstack([np.ones(len(env)), multiple]))
        self.assertAlmostEqual(both[0], review.path_drawdown(self.paths.get(d, np.zeros(1)) for d in self.dates), places=9)
        self.assertAlmostEqual(both[1], direct, places=9)

    def test_month_interval_redraws_whole_months(self):
        dates = pd.date_range('2024-01-01', periods=120)
        self.assertTrue(np.allclose(review.month_interval(np.full(120, 2.5), dates), [2.5, 2.5]))
        low, high = review.month_interval(np.where(dates.month == 1, 31.0, 0.0), dates)   # all profit in one month
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 31 * 31 / 120)

    def test_inside_uses_half_open_eras(self):
        dates = pd.to_datetime(['2015-12-31', '2016-01-01', '2019-12-31', '2020-01-01', '2026-09-30', '2026-10-01'])
        self.assertEqual(review.inside(dates, '2016-19').tolist(), [False, True, True, False, False, False])
        self.assertEqual(review.inside(dates, '2016-26').tolist(), [False, True, True, True, True, False])
        self.assertEqual(review.inside(dates, ('2018-01-01', '2026-10-01')).tolist(), [False, False, True, True, True, False])


if __name__ == '__main__':
    unittest.main()
