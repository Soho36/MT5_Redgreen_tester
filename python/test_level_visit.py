import unittest

import numpy as np
import pandas as pd

from level_visit import bar_frame, classify, level_state, merge_levels, swing_lows


def make_bars(low, high=None, close=None, opn=None, per_day=40, roll_day=None):
    low = np.asarray(low, float)
    high = low + 4 if high is None else np.asarray(high, float)
    close = (low + high) / 2 if close is None else np.asarray(close, float)
    opn = close if opn is None else np.asarray(opn, float)
    days = pd.bdate_range("2021-01-04", periods=len(low) // per_day + 2)
    times = [days[i // per_day] + pd.Timedelta(hours=1, minutes=30 * (i % per_day)) for i in range(len(low))]
    rolls = pd.DataFrame(dict(date=[str(days[0].date())], instrument_id=[1]))
    if roll_day is not None:
        rolls = pd.DataFrame(dict(date=[str(days[0].date()), str(days[roll_day].date())], instrument_id=[1, 2]))
    bars = pd.DataFrame(dict(open=opn, high=high, low=low, close=close), index=pd.DatetimeIndex(times))
    return bar_frame(bars, rolls)


class SwingLowTest(unittest.TestCase):
    def test_strict_left_nonstrict_right(self):
        low = np.array([10, 9, 8, 7, 6, 5, 6, 7, 8, 9, 10, 11, 12.])
        self.assertEqual(swing_lows(low, np.ones(13), 3).tolist(), [5])
        low[4] = 5  # equal on the left: the earlier bar wins, the later is not a pivot
        self.assertEqual(swing_lows(low, np.ones(13), 3).tolist(), [4])

    def test_neighbours_must_share_contract(self):
        low = np.array([10, 9, 8, 7, 6, 5, 6, 7, 8, 9, 10.])
        contract = np.array([1] * 7 + [2] * 4)
        self.assertEqual(swing_lows(low, contract, 3).tolist(), [])


class MergeAndStateTest(unittest.TestCase):
    def test_greedy_merge_from_lowest(self):
        low = np.array([100, 100.8, 101.6, 105.])
        levels = merge_levels([0, 1, 2, 3], low, 1.0)
        self.assertEqual([(x["level"], x["members"]) for x in levels],
                         [(100, [0, 1]), (101.6, [2]), (105, [3])])

    def test_false_breakdown_does_not_break(self):
        close = np.array([0, 104, 99.5, 99.2, 0.])  # departs by >= A, then closes within D below
        self.assertEqual(level_state(100, 0, 4, close, a=2, d=1), (False, True))
        close[3] = 98.9  # more than D below
        self.assertEqual(level_state(100, 0, 4, close, a=2, d=1), (True, True))

    def test_signal_close_not_used_for_state(self):
        close = np.array([0, 101, 90.])
        self.assertEqual(level_state(100, 0, 2, close, a=2, d=1), (False, False))


class ClassifyTest(unittest.TestCase):
    def scenario(self, revisit_low=99.0, dip_close=None):
        # Quiet bars at 120, a V-shaped swing low at 100 (bar 60), rally, return.
        n = 200
        low = np.full(n, 120.)
        low[55:66] = [110, 108, 106, 104, 102, 100, 102, 104, 106, 108, 110]
        high, close = low + 2, low + 1
        if dip_close is not None:
            close[150] = dip_close
        low[180] = revisit_low
        high[180], close[180] = revisit_low + 6, revisit_low + 1
        return make_bars(low, high, close, opn=high - 0.5, per_day=30)

    def test_revisit_from_above(self):
        b = self.scenario()
        group, info = classify(b, 180, n=5, sessions=5)
        self.assertEqual(group, "support_revisit")
        self.assertEqual(info["level"], 100)
        self.assertTrue(info["wick_reaches"])

    def test_confirmation_timing(self):
        b = self.scenario()
        group, info = classify(b, 65, n=5, sessions=1)  # pivot 60 confirmed by bar 65 close
        self.assertEqual(info.get("known_pivots", 0), 0)
        group, info = classify(b, 66, n=5, sessions=1)
        self.assertGreaterEqual(info.get("known_pivots", 0), 1)

    def test_broken_level_is_not_support(self):
        b = self.scenario(dip_close=90)
        self.assertEqual(classify(b, 180, n=5, sessions=5)[0], "broken_contact")

    def test_contact_boundary(self):
        b = self.scenario(revisit_low=130)
        d = 0.5 * b.atr.iloc[180]
        b.iloc[180, b.columns.get_loc("low")] = 100 + d
        self.assertEqual(classify(b, 180, n=5, sessions=5)[0], "support_revisit")
        b.iloc[180, b.columns.get_loc("low")] = 100 + d + 0.25
        self.assertEqual(classify(b, 180, n=5, sessions=5)[0], "no_contact")

    def test_deep_slice_is_not_a_revisit(self):
        b = self.scenario(revisit_low=130)
        d = 0.5 * b.atr.iloc[180]
        for low, group in ((100 - d, "support_revisit"), (100 - d - 0.25, "slice_through")):
            b.iloc[180, b.columns.get_loc("low")] = low
            b.iloc[180, b.columns.get_loc("close")] = low + 1
            self.assertEqual(classify(b, 180, n=5, sessions=5)[0], group)

    def test_window_and_roll(self):
        b = self.scenario()
        self.assertEqual(classify(b, 30, n=5, sessions=5)[0], "missing_history")
        rolled = make_bars(b.low.to_numpy(), b.high.to_numpy(), b.close.to_numpy(), b.open.to_numpy(), per_day=30, roll_day=3)
        self.assertEqual(classify(rolled, 180, n=5, sessions=5)[0], "contract_roll")

    def test_atr_is_lagged_and_resets_at_roll(self):
        b = make_bars(np.arange(100.), roll_day=1)
        self.assertTrue(np.isnan(b.atr.iloc[13]))
        self.assertTrue(np.isfinite(b.atr.iloc[14]))
        self.assertTrue(np.isnan(b.atr.iloc[40 + 13]))  # new contract starts on day 1
        b2 = b.copy()
        b2.iloc[30, b2.columns.get_loc("high")] += 50
        b2 = bar_frame(b2[["open", "high", "low", "close"]], pd.DataFrame(dict(date=["2021-01-04"], instrument_id=[1])))
        self.assertEqual(b2.atr.iloc[30], bar_frame(b[["open", "high", "low", "close"]],
                         pd.DataFrame(dict(date=["2021-01-04"], instrument_id=[1]))).atr.iloc[30])


if __name__ == "__main__":
    unittest.main()
