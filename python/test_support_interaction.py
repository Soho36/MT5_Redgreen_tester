import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

from analyze_breach_reclaim import classify
from analyze_support_interaction import membership, census, drawdown_interval


class SupportInteractionTests(unittest.TestCase):
    def test_full_complement_keeps_unavailable_and_already_below(self):
        f = pd.DataFrame(dict(status=['eligible']*6+['missing_history'], low=[10]*7,
                              signal_open=[11, 11, 11, 11, 11, 9, 11],
                              signal_low=[10.5, 10, 9, 9, 9, 8, 9],
                              signal_close=[10.75, 10.5, 10.5, 9.5, 10, 8.5, 9.5]))
        f['group'] = classify(f)
        self.assertEqual(f.group.tolist(), ['no_contact', 'touch_only', 'breach_reclaim',
                                          'breach_unrecovered', 'breach_exact_close', 'opened_at_or_below', 'unavailable'])
        self.assertEqual(np.flatnonzero(membership(f, 'interaction')).tolist(), [1, 2, 3, 4])
        self.assertEqual(np.flatnonzero(membership(f, 'every_other')).tolist(), [0, 5, 6])
        self.assertEqual(np.flatnonzero(membership(f, 'known_other')).tolist(), [0, 5])
        self.assertTrue((membership(f, 'interaction') ^ membership(f, 'every_other')).all())

    def test_drawdown_includes_initial_zero_and_additive_interval(self):
        x = np.array([-3., 1., -4., 9., -2.])
        dd, a, b = drawdown_interval(x)
        self.assertEqual((dd, a, b), (6., 0, 3))
        self.assertEqual(-x[a:b].sum(), dd)
        self.assertEqual(drawdown_interval([-3, 8, -2, -4, 1]), (6., 2, 4))
        self.assertEqual(drawdown_interval([]), (0., 0, 0))

    def test_census_uses_next_available_bar_and_calendar_cutoff(self):
        ix = pd.to_datetime(['2020-01-01 23:00', '2020-01-01 23:30',
                             '2020-01-02 01:00', '2020-01-02 01:30', '2020-01-02 02:00'])
        bars = pd.DataFrame(dict(open=[10]*5, high=[11]*5, low=[8]*5, close=[11, 9, 9, 9, 9]), index=ix)
        cal = SimpleNamespace(read_text=lambda **kw: 'EC_DATE[EC_COUNT] = {20200102}; EC_FLAT_MIN[EC_COUNT] = {90};')
        result = census(bars, cal)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0].signal_time, ix[1])
        self.assertEqual(result.iloc[0].submission_time, ix[2])
        self.assertEqual(result.iloc[0].red_run, 1)
        # No early close: fourth consecutive red is excluded; last bar has no decision bar.
        ordinary = SimpleNamespace(read_text=lambda **kw: 'EC_DATE[EC_COUNT] = {20160101}; EC_FLAT_MIN[EC_COUNT] = {1410};')
        result = census(bars, ordinary)
        self.assertEqual(result.red_run.tolist(), [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
