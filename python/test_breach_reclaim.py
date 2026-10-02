"""Classification and post-signal timing invariants for Q8."""

import unittest
import numpy as np
import pandas as pd

from analyze_breach_reclaim import classify, forward_response


class BreachTests(unittest.TestCase):
    def test_groups_equality_and_already_below(self):
        f = pd.DataFrame(dict(status=["eligible"] * 6 + ["contract_roll"], low=[100] * 7,
                             signal_open=[105, 105, 105, 105, 105, 99, 105],
                             signal_low=[101, 100, 99.75, 99, 99, 95, 99],
                             signal_close=[102, 102, 101, 99.5, 100, 98, 101]))
        self.assertEqual(classify(f).tolist(), ["no_contact", "touch_only", "breach_reclaim", "breach_unrecovered",
                                               "breach_exact_close", "opened_at_or_below", "unavailable"])
        f.loc[5, "signal_open"] = 100
        self.assertEqual(classify(f)[5], "opened_at_or_below")

    def fixture(self):
        times = pd.date_range("2026-01-05 01:00", periods=8, freq="30min")
        bars = pd.DataFrame(dict(open=[100] * 8, high=[999, 102, 103, 106, 107, 108, 109, 110],
                                 low=[-999, 99, 98, 97, 96, 95, 94, 93], close=[100, 102, 101, 104, 102, 99, 98, 97]), index=times)
        events = pd.DataFrame(dict(event_id=["a"], signal_time=[times[0]], submission_time=[times[1]],
                                  signal_close=[100.], candle_range=[8.]))
        ends = pd.Series([times[-1] + pd.Timedelta(minutes=30)], index=[times[0].normalize()])
        return bars, events, ends

    def test_forward_excludes_signal_and_uses_correct_endpoint(self):
        bars, events, ends = self.fixture()
        result = forward_response(events, bars, ends, 3).iloc[0]
        self.assertEqual(result.response_status, "eligible")
        self.assertEqual(result.forward_r, .5)
        self.assertEqual(result.up_half_r, 1)
        self.assertEqual(result.up_excursion_r, .75)
        self.assertEqual(result.down_excursion_r, -.375)
        later = bars.copy()
        later.iloc[4:, :] = 9999
        pd.testing.assert_frame_equal(forward_response(events, bars, ends, 3), forward_response(events, later, ends, 3))

    def test_future_bar_gap_is_not_bridged(self):
        bars, events, ends = self.fixture()
        result = forward_response(events, bars.drop(bars.index[2]), ends, 3).iloc[0]
        self.assertEqual(result.response_status, "missing_bar")
        self.assertTrue(np.isnan(result.forward_r))

    def test_early_partial_bar_and_late_submission_excluded(self):
        bars, events, ends = self.fixture()
        ends.iloc[0] = pd.Timestamp("2026-01-05 02:45")
        result = forward_response(events, bars, ends, 3).iloc[0]
        self.assertEqual(result.response_status, "session_end")
        events.loc[0, "submission_time"] = pd.Timestamp("2026-01-05 03:00")
        self.assertEqual(forward_response(events, bars, ends, 1).iloc[0].response_status, "delayed_submission")

    def test_no_overnight_or_end_of_data_extension(self):
        bars, events, ends = self.fixture()
        events.loc[0, "signal_time"] = bars.index[-2]
        events.loc[0, "submission_time"] = bars.index[-1]
        result = forward_response(events, bars, ends, 3).iloc[0]
        self.assertEqual(result.response_status, "end_of_data")
        self.assertTrue(np.isnan(result.up_half_r))


if __name__ == "__main__":
    unittest.main()
