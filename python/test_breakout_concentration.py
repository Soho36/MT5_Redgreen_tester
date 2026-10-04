import unittest

import pandas as pd

from analyze_breakout_concentration import level_event


class LevelEventTest(unittest.TestCase):
    def test_same_level_and_member_is_one_event(self):
        level = pd.Series([21000.25, 21000.25, 21000.25, None])
        t0 = pd.Series(pd.to_datetime(["2025-01-06 10:00", "2025-01-06 10:00", "2025-01-07 09:30", "2025-01-06 10:00"]))
        e = level_event(level, t0)
        self.assertEqual(e.iloc[0], e.iloc[1])
        self.assertNotEqual(e.iloc[0], e.iloc[2])   # a new latest member makes a new event
        self.assertTrue(pd.isna(e.iloc[3]))


if __name__ == "__main__":
    unittest.main()
