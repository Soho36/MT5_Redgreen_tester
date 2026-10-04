import unittest

import numpy as np

from test_level_visit import make_bars
from trendline_support import candidate_pairs, classify, classify_contact, line_state, line_value


def scenario(offset=8.0, signal_offset=-1.0, broken_at=None, n=200, v=1.5):
    """Bars sit `offset` above a rising line 100 + 0.2 * (k - 40), with V-shaped swing lows
    touching it at bars 40 and 100 (the anchors). Signal bar 180 has low = line + signal_offset."""
    k = np.arange(n, dtype=float)
    line = 100 + 0.2 * (k - 40)
    low = line + offset
    for c in (40, 100):
        for m in range(-5, 6):
            low[c + m] = line[c + m] + v * abs(m)
    high, close = low + 4, low + 2
    if broken_at is not None:
        close[broken_at] = line[broken_at] - 5
    low[180] = line[180] + signal_offset
    high[180], close[180] = low[180] + 6, low[180] + 1
    return make_bars(low, high, close, opn=high - 0.5, per_day=30), line


class GeometryTest(unittest.TestCase):
    def test_line_value_is_bar_indexed(self):
        low = np.array([100., 0, 0, 0, 104])
        self.assertEqual(line_value(0, 4, low, 10), 110)

    def test_pairs_are_consecutive_higher_lows(self):
        low = np.full(40, 200.)
        low[[0, 12, 20, 33]] = [100, 110, 115, 105]
        # 12 pairs with 0; 20 with 12 (latest lower); 33 skips 12 and 20 (both higher) and pairs with 0
        i, j = candidate_pairs([0, 12, 20, 33], low, min_sep=5)
        self.assertEqual(list(zip(i.tolist(), j.tolist())), [(0, 12), (12, 20), (0, 33)])
        # too close to its latest lower low: dropped, never paired with an older low instead
        i, j = candidate_pairs([0, 12, 20, 33], low, min_sep=10)
        self.assertEqual(list(zip(i.tolist(), j.tolist())), [(0, 12), (0, 33)])

    def test_line_must_underlie_lows_between_anchors(self):
        low = np.full(30, 120.)
        low[0], low[10] = 100, 110
        close = low + 1
        self.assertTrue(line_state(0, 10, 29, low, close, a=4, d=2)[0])
        low[5] = 105 - 2.01  # more than D below the line value 105
        self.assertFalse(line_state(0, 10, 29, low, close, a=4, d=2)[0])
        low[5] = 105 - 2.0
        self.assertTrue(line_state(0, 10, 29, low, close, a=4, d=2)[0])

    def test_state_uses_pre_signal_closes_and_counts_retests(self):
        low = np.full(30, 140.)
        low[0], low[10] = 100, 110  # line = 100 + k
        low[15:17], low[20] = [115, 116], 120  # one two-bar retest, then another retest
        close = low + 1
        self.assertEqual(line_state(0, 10, 29, low, close, a=4, d=2), (True, False, True, 2))
        low[11:13], close[11:13] = [111, 112], [112, 113]  # still on the line after anchor 2: not a retest
        self.assertEqual(line_state(0, 10, 29, low, close, a=4, d=2)[3], 2)
        low[17:20], close[17:20] = [117, 118, 119], [118, 119, 120]  # never A above between visits: one retest
        self.assertEqual(line_state(0, 10, 29, low, close, a=4, d=2)[3], 1)
        close[28] = 128 - 2.01
        self.assertEqual(line_state(0, 10, 29, low, close, a=4, d=2)[1], True)
        self.assertEqual(line_state(0, 10, 28, low, close, a=4, d=2)[1], False)


class ClassifyTest(unittest.TestCase):
    def test_support_revisit_of_rising_line(self):
        b, line = scenario()
        group, info = classify(b, 180)
        self.assertEqual(group, "trendline_support")
        self.assertEqual((info["anchor1"], info["anchor2"]), (40, 100))
        self.assertAlmostEqual(info["line"], line[180])
        self.assertTrue(info["wick_reaches"])

    def test_anchor_needs_confirmation(self):
        b, _ = scenario()
        self.assertEqual(classify(b, 105, sessions=3)[1].get("known_pivots"), 1)  # pivot 100 needs bar 105 closed
        self.assertEqual(classify(b, 106, sessions=3)[1].get("known_pivots"), 2)

    def test_broken_line_is_not_support(self):
        b, _ = scenario(broken_at=150)
        self.assertEqual(classify(b, 180)[0], "broken_contact")
        self.assertEqual(classify_contact(b, 180), "no_contact")  # broken lines are not broad contact
        b, _ = scenario(offset=0.5, v=0.3)
        self.assertEqual(classify_contact(b, 180), "contact")  # unbroken, not departed: still broad contact

    def test_not_departed(self):
        b, _ = scenario(offset=0.5, v=0.3)  # closes never reach line + A
        self.assertEqual(classify(b, 180)[0], "not_departed_contact")

    def test_slice_through_and_boundaries(self):
        b, line = scenario()
        d = 0.5 * b.atr.iloc[180]
        col = b.columns.get_loc("low")
        for low, group in ((line[180] - d, "trendline_support"), (line[180] - d - 0.01, "slice_through"),
                           (line[180] + d, "trendline_support"), (line[180] + d + 0.01, "no_contact")):
            b.iloc[180, col] = low
            self.assertEqual(classify(b, 180)[0], group, low)

    def test_min_separation(self):
        b, _ = scenario()
        self.assertEqual(classify(b, 180, min_sep=61)[0], "no_contact")
        self.assertEqual(classify(b, 180, min_sep=60)[0], "trendline_support")

    def test_min_slope(self):
        b, _ = scenario()  # line rises 0.2 per bar
        slope_a = 0.2 / b.atr.iloc[180]
        self.assertEqual(classify(b, 180, min_slope=slope_a * 0.99)[0], "trendline_support")
        self.assertEqual(classify(b, 180, min_slope=slope_a * 1.01)[0], "no_contact")

    def test_window_and_roll(self):
        b, _ = scenario()
        self.assertEqual(classify(b, 30)[0], "missing_history")
        self.assertEqual(classify(b, 180, sessions=2)[0], "no_contact")  # anchor 40 left the window
        rolled = make_bars(b.low.to_numpy(), b.high.to_numpy(), b.close.to_numpy(), b.open.to_numpy(),
                           per_day=30, roll_day=3)
        self.assertEqual(classify(rolled, 180)[0], "contract_roll")


if __name__ == "__main__":
    unittest.main()
