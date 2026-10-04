import unittest

import numpy as np

from test_level_visit import make_bars
from trendline_resistance import classify, classify_contact, mirror, swing_highs


def scenario(offset=8.0, signal_offset=1.0, broken_at=None, n=200, v=1.5):
    """Bars sit `offset` below a falling line 200 - 0.2 * (k - 40), with inverted-V swing highs
    touching it at bars 40 and 100 (the anchors). Signal bar 180 (red) has high = line + signal_offset."""
    k = np.arange(n, dtype=float)
    line = 200 - 0.2 * (k - 40)
    high = line - offset
    for c in (40, 100):
        for m in range(-5, 6):
            high[c + m] = line[c + m] - v * abs(m)
    low, close = high - 4, high - 2
    if broken_at is not None:
        close[broken_at] = line[broken_at] + 5
    high[180] = line[180] + signal_offset
    low[180], close[180] = high[180] - 6, high[180] - 5
    b = make_bars(low, high, close, opn=high - 0.5, per_day=30)
    return b, mirror(b), line


def run(m, s, **kw):
    n = kw.pop("n", 5)
    return classify(m, s, n=n, pivots=swing_highs(-m.low.to_numpy(), m.contract.to_numpy(), n), **kw)


class ResistanceTest(unittest.TestCase):
    def test_mirror_keeps_atr_and_swaps_extremes(self):
        b, m, _ = scenario()
        self.assertTrue(np.allclose(m.high, -b.low) and np.allclose(m.low, -b.high))
        self.assertTrue(np.allclose(m.atr.dropna(), b.atr.dropna()))

    def test_swing_highs(self):
        b, _, _ = scenario()
        self.assertEqual(swing_highs(b.high.to_numpy(), b.contract.to_numpy(), 5)[:2].tolist(), [40, 100])

    def test_resistance_test_from_below(self):
        b, m, line = scenario()
        group, info = run(m, 180)
        self.assertEqual(group, "resistance_test")
        self.assertEqual((info["anchor1"], info["anchor2"]), (40, 100))
        self.assertAlmostEqual(info["line"], line[180])
        self.assertLess(info["slope_a"], 0)
        self.assertTrue(info["wick_reaches"])
        self.assertAlmostEqual(info["poke_a"], 1.0 / b.atr.iloc[180])

    def test_close_above_breaks(self):
        _, m, _ = scenario(broken_at=150)
        self.assertEqual(run(m, 180)[0], "broken_contact")
        self.assertEqual(classify_contact(m, 180), "no_contact")

    def test_not_departed(self):
        _, m, _ = scenario(offset=0.5, v=0.3)
        self.assertEqual(run(m, 180)[0], "not_departed_contact")

    def test_poke_through_and_boundaries(self):
        b, m, line = scenario()
        d = 0.5 * b.atr.iloc[180]
        for high, group in ((line[180] + d, "resistance_test"), (line[180] + d + 0.01, "poke_through"),
                            (line[180] - d, "resistance_test"), (line[180] - d - 0.01, "no_contact")):
            m.iloc[180, m.columns.get_loc("low")] = -high
            self.assertEqual(run(m, 180)[0], group, high)

    def test_min_slope_and_rising_lines_ignored(self):
        b, m, _ = scenario()
        slope_a = 0.2 / b.atr.iloc[180]
        self.assertEqual(run(m, 180, min_slope=slope_a * 1.01)[0], "no_contact")
        # A rising line through higher highs is not resistance.
        b2, m2, _ = scenario()
        h = m2.columns.get_loc("low")
        m2.iloc[100, h] = m2.iloc[40, h] - 30  # anchor 2 now higher than anchor 1
        self.assertEqual(run(m2, 180)[0], "no_contact")


if __name__ == "__main__":
    unittest.main()
