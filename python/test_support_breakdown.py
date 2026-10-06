import unittest

import pandas as pd

from analyze_support_breakdown import census_green

PERIODS = {"p": ("2021-01-04", "2021-01-07")}


def frame(colours, start="2021-01-04 00:30", step="30min"):
    """Bars with the given colours: 'g' green, 'r' red, 'd' doji. Range 2 unless 'z' (zero-range green)."""
    rows = []
    for c in colours:
        o = 100.0
        close = {"g": 101.0, "r": 99.0, "d": 100.0, "z": 100.0}[c]
        hi, lo = (100.0, 100.0) if c == "z" else (102.0, 98.0)
        rows.append(dict(open=o, high=hi, low=lo, close=close))
    return pd.DataFrame(rows, index=pd.date_range(start, periods=len(colours), freq=step))


class CensusTest(unittest.TestCase):
    def test_green_run_counts_and_cap(self):
        b = frame("rggggrg")  # bars 01:00 ... ; runs 1,2,3,4 then red then 1
        c = census_green(b, {}, PERIODS)
        self.assertEqual(c.green_run.tolist(), [1, 2, 3])  # run 4 excluded; the last bar has no next bar
        self.assertNotIn(pd.Timestamp("2021-01-04 02:30"), set(c.signal_time))

    def test_doji_and_red_reset_the_run(self):
        c = census_green(frame("ggdgg" + "r"), {}, PERIODS)
        self.assertEqual(c.green_run.tolist(), [1, 2, 1, 2])

    def test_zero_range_is_not_a_signal(self):
        c = census_green(frame("gzgr"), {}, PERIODS)
        self.assertEqual(c.signal_time.dt.strftime("%H:%M").tolist(), ["00:30", "01:30"])

    def test_submission_window(self):
        # Signal at 00:00 submits at 00:30 (before 01:00): excluded; 00:30 submits at 01:00: included.
        c = census_green(frame("ggr", start="2021-01-04 00:00"), {}, PERIODS)
        self.assertEqual(c.signal_time.dt.strftime("%H:%M").tolist(), ["00:30"])
        late = frame("gggr", start="2021-01-04 22:30")  # submissions 23:00, 23:30, 00:00
        c = census_green(late, {}, PERIODS)
        self.assertEqual(c.signal_time.dt.strftime("%H:%M").tolist(), ["22:30"])
        c = census_green(late, {"20210104": 23 * 60}, PERIODS)  # early close at 23:00
        self.assertEqual(len(c), 0)

    def test_period_split_by_submission(self):
        b = frame("gr", start="2021-01-06 23:00")  # submits 23:30 on the 6th: inside; but 23:30 is the cutoff
        self.assertEqual(len(census_green(b, {}, PERIODS)), 0)
        b = frame("gr", start="2021-01-06 22:30")
        c = census_green(b, {}, PERIODS)
        self.assertEqual((len(c), c.period.iloc[0], int(c.year.iloc[0])), (1, "p", 2021))


if __name__ == "__main__":
    unittest.main()
