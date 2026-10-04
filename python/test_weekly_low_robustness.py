import unittest

import numpy as np
import pandas as pd

from analyze_weekly_low_robustness import (bootstrap_weeks, concentration, identify_events,
                                         metrics, omit_time, trimmed_mean)


class WeeklyRobustnessTest(unittest.TestCase):
    def test_events_use_source_week_and_contract_not_price(self):
        f = pd.DataFrame(dict(signal_time=pd.to_datetime(["2021-01-04", "2021-01-08", "2021-01-11", "2021-01-04"]),
                              source_start=pd.to_datetime(["2020-12-28", "2020-12-28", "2021-01-04", "2020-12-28"]),
                              source_end=pd.to_datetime(["2020-12-31", "2020-12-31", "2021-01-08", "2020-12-31"]),
                              signal_contract=[1, 1, 1, 2], status="eligible", level=100))
        out = identify_events(f)
        self.assertEqual(out.weekly_event.iloc[0], out.weekly_event.iloc[1])
        self.assertNotEqual(out.weekly_event.iloc[0], out.weekly_event.iloc[2])
        self.assertNotEqual(out.weekly_event.iloc[0], out.weekly_event.iloc[3])
        self.assertEqual(out.active_week.iloc[1], pd.Timestamp("2021-01-04"))

    def test_future_or_nonprevious_source_rejected(self):
        f = pd.DataFrame(dict(signal_time=pd.to_datetime(["2021-01-04"]),
                              source_start=pd.to_datetime(["2021-01-04"]),
                              source_end=pd.to_datetime(["2021-01-08"]), signal_contract=[1], status="eligible"))
        with self.assertRaises(AssertionError):
            identify_events(f)

    def test_unavailable_has_no_level_event(self):
        f = pd.DataFrame(dict(signal_time=pd.to_datetime(["2021-01-04"]),
                              source_start=pd.to_datetime([None]), source_end=pd.to_datetime([None]),
                              signal_contract=[1], status="missing_history"))
        self.assertTrue(identify_events(f).weekly_event.isna().all())

    def test_trim_is_symmetric_and_floor_based(self):
        self.assertEqual(trimmed_mean([-100, 1, 2, 3, 1000], .2), 2)
        self.assertEqual(trimmed_mean([1, 2, 3], .1), 2)

    def test_omit_removes_calendar_unit_from_both_groups(self):
        a = pd.DataFrame(dict(year=[2020, 2021], net=[100, -1], net_r=[10, -1]))
        b = pd.DataFrame(dict(year=[2020, 2021], net=[-100, 2], net_r=[-10, 2]))
        out = omit_time(a, b, "year", 2020)
        self.assertEqual(out["candidate"]["fills"], 1)
        self.assertEqual(out["complement"]["fills"], 1)
        self.assertEqual(out["mean_r_difference"], -3)

    def test_weekly_bootstrap_preserves_whole_clusters(self):
        # The populations are identical in each week; paired draws must give zero.
        a = pd.DataFrame(dict(active_week=pd.to_datetime(["2021-01-04"]*2+["2021-01-11"]*2),
                              net=[10., -5., 1., -9.], net_r=[1., -.5, .1, -.9]))
        result = bootstrap_weeks(a, a.copy(), "2021-01-04", "2021-01-25", repeats=100)
        self.assertEqual(result["calendar_weeks"], 3)  # empty third week retained
        for metric in ("pf", "mean_r"):
            self.assertEqual(result[metric]["lower"], 0)
            self.assertEqual(result[metric]["upper"], 0)

    def test_net_share_can_exceed_one_and_removal_keeps_rest(self):
        a = pd.DataFrame(dict(event_id=["a", "b"], weekly_event=["w1", "w2"],
                              net=[10., -9.], net_r=[1., -.9], excess_r=[.9, -1.]))
        b = pd.DataFrame(dict(net=[1., -1.], net_r=[.1, -.1]))
        e = pd.DataFrame(dict(weekly_event=["w1", "w2"], net=[10., -9.], sum_r=[1., -.9]))
        out = concentration(a, b, e, "test")[0]
        self.assertEqual(out["share_total_net"], 10)
        self.assertEqual(out["share_gross_positive"], 1)
        self.assertEqual(out["remainder"]["candidate"]["fills"], 1)
        self.assertEqual(out["remainder"]["complement"], metrics(b))


if __name__ == "__main__":
    unittest.main()
