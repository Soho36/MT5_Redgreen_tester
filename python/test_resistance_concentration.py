import unittest

import pandas as pd

from analyze_resistance_concentration import concentration, line_ids, week_frame
from analyze_weekly_low_robustness import metrics


def frame(signal_times, a1, a2):
    return pd.DataFrame(dict(signal_time=pd.to_datetime(signal_times), anchor1=a1, anchor2=a2))


TIMES = pd.Series(pd.date_range("2021-01-04 01:00", periods=10, freq="30min"))


class LineEventTest(unittest.TestCase):
    def test_same_anchors_same_event_across_weeks(self):
        f = line_ids(frame(["2021-01-08 10:00", "2021-01-11 10:00", "2021-01-08 11:00", "2021-01-08 12:00"],
                           [0, 0, 1, None], [5, 5, 5, None]), TIMES)
        self.assertEqual(f.line_event.iloc[0], f.line_event.iloc[1])
        self.assertNotEqual(f.line_event.iloc[0], f.line_event.iloc[2])
        self.assertTrue(pd.isna(f.line_event.iloc[3]))
        self.assertNotEqual(f.active_week.iloc[0], f.active_week.iloc[1])  # one line, two calendar weeks

    def test_anchor_after_signal_rejected(self):
        with self.assertRaises(AssertionError):
            line_ids(frame(["2021-01-04 02:00"], [0], [5]), TIMES)  # anchor 2 = 03:30, after the signal


class ConcentrationTest(unittest.TestCase):
    def test_week_units_removed_whole_and_complement_fixed(self):
        a = pd.DataFrame(dict(event_id=list("abc"), active_week=pd.to_datetime(["2021-01-04"] * 2 + ["2021-01-11"]),
                              net=[10., 5., -3.], net_r=[1., .5, -.3], excess_r=[1., .5, -.3]))
        b = pd.DataFrame(dict(net=[1., -2.], net_r=[.1, -.2]))
        w = week_frame(a)
        self.assertEqual(w.net.tolist(), [15., -3.])
        out = concentration(a, b, w, "active_week", ("net",), (1,), "calendar_week", "test")[0]
        self.assertEqual(out["removed_trades"], 2)
        self.assertEqual(out["share_total_net"], 15 / 12)
        self.assertEqual(out["remainder"]["candidate"]["fills"], 1)
        self.assertEqual(out["remainder"]["complement"], metrics(b))


if __name__ == "__main__":
    unittest.main()
