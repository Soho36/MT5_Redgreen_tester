import unittest

import numpy as np

from level_resistance import classify, mirror, swing_highs
from test_level_visit import make_bars


def scenario(signal_high=121.0, dip_close=None, depart=True):
    """Quiet bars with highs at 100, an inverted-V swing high at 120 (bar 60), a decline, then
    signal bar 180 (red) rising into the level from below with the given high."""
    n = 200
    high = np.full(n, 100. if depart else 119.5)  # without departure, closes stay within A of the level
    high[55:66] = [110, 112, 114, 116, 118, 120, 118, 116, 114, 112, 110]
    if not depart:
        high[55:66] = np.maximum(high[55:66], 119.5)
        high[60] = 120
    low, close = high - 2, high - 1
    if dip_close is not None:
        close[150] = dip_close
    high[180] = signal_high
    low[180], close[180] = signal_high - 6, signal_high - 5
    opn = close + 0.5
    opn[180] = signal_high - 1  # red signal: open above its close
    b = make_bars(low, high, close, opn=opn, per_day=30)
    return b, mirror(b)


def run(m, s, n=5, sessions=5):
    return classify(m, s, n=n, sessions=sessions, pivots=swing_highs(-m.low.to_numpy(), m.contract.to_numpy(), n))


class BreakoutLevelTest(unittest.TestCase):
    def test_breakout_test_from_below(self):
        b, m = scenario()
        group, info = run(m, 180)
        self.assertEqual(group, "breakout_test")
        self.assertEqual(info["level"], 120)
        self.assertTrue(info["wick_reaches"])
        self.assertAlmostEqual(info["poke_a"], 1 / b.atr.iloc[180])

    def test_close_above_breaks_the_level(self):
        _, m = scenario(dip_close=125)
        self.assertEqual(run(m, 180)[0], "broken_upward_contact")

    def test_false_breakout_within_d_does_not_break(self):
        b, _ = scenario()
        d = 0.5 * b.atr.iloc[180]
        _, m = scenario(dip_close=120 + d * 0.9)
        self.assertEqual(run(m, 180)[0], "breakout_test")

    def test_not_departed(self):
        _, m = scenario(depart=False)
        self.assertEqual(run(m, 180)[0], "not_departed_contact")

    def test_poke_through_and_boundaries(self):
        b, m = scenario()
        d = 0.5 * b.atr.iloc[180]
        col = m.columns.get_loc("low")  # mirrored low = -high
        for high, group in ((120 + d, "breakout_test"), (120 + d + 0.01, "poke_through"),
                            (120 - d, "breakout_test"), (120 - d - 0.01, "no_contact")):
            m.iloc[180, col] = -high
            self.assertEqual(run(m, 180)[0], group, high)

    def test_confirmation_timing(self):
        _, m = scenario()
        self.assertEqual(run(m, 65, sessions=1)[1].get("known_pivots", 0), 0)
        self.assertGreaterEqual(run(m, 66, sessions=1)[1].get("known_pivots", 0), 1)

    def test_merged_level_uses_highest_member(self):
        b, _ = scenario()
        h = b.high.to_numpy().copy()
        h[95:106] = [110, 112, 114, 116, 118, 119.5, 118, 116, 114, 112, 110]  # second swing high within D
        b2 = make_bars(h - 2, h, h - 1, opn=h - 0.5, per_day=30)
        b2.iloc[180] = b.iloc[180]
        group, info = run(mirror(b2), 180)
        self.assertEqual(info["level"], 120)
        self.assertEqual(info["members"], 2)


if __name__ == "__main__":
    unittest.main()
