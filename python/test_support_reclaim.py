import unittest

import numpy as np

from level_visit import swing_lows
from support_reclaim import bar_signal, level_states
from test_level_visit import make_bars


def scenario(base=110.0, extra_pivot=None, bars=None, roll_day=None):
    """Bars 4 points tall around `base` (A = 4, D = 2), a V-shaped swing low at bar 40 with L = 100, an optional
    second V at bar 80, and per-bar overrides {k: (open, high, low, close)}."""
    n = 200
    low = np.full(n, base)
    for c, L in [(40, 100.0)] + ([extra_pivot] if extra_pivot else []):
        for m in range(-5, 6):
            low[c + m] = min(low[c + m], L + 2 * abs(m))
    high, close, opn = low + 4, low + 2, low + 3
    for k, (o, h, l, c) in (bars or {}).items():
        opn[k], high[k], low[k], close[k] = o, h, l, c
    return make_bars(low, high, close, opn, per_day=30, roll_day=roll_day)


def signal(b, t, **kw):
    return bar_signal(b, t, swing_lows(b.low.to_numpy(), b.contract.to_numpy(), 5), **kw)


BREAK = {150: (104.0, 105.0, 97.0, 99.0), 151: (99.5, 100.5, 98.5, 99.75)}


class ReclaimSignalTest(unittest.TestCase):
    def test_breakdown_gives_a_buy_stop_at_the_level(self):
        status, info = signal(scenario(bars=BREAK), 151)
        self.assertEqual(status, "order")
        self.assertEqual((info["level"], info["key"], info["entry"], info["stop"], info["risk"]), (100, 40, 100, 97, 3))
        self.assertAlmostEqual(info["depth_a"], 0.25)

    def test_needs_a_fresh_break(self):
        opened_below = {150: (99.5, 100.5, 97.0, 99.0), 151: BREAK[151]}
        self.assertEqual(signal(scenario(bars=opened_below), 151)[0], "no_break")
        on_level = {150: (104.0, 105.0, 99.0, 100.0), 151: BREAK[151]}
        self.assertEqual(signal(scenario(bars=on_level), 151)[0], "no_break")

    def test_s1_needs_a_close_more_than_d_below(self):
        self.assertEqual(signal(scenario(bars=BREAK), 151, depth_a=0.5)[0], "no_break")  # close 99 > L - D = 98
        deep = {150: (104.0, 105.0, 96.0, 97.5), 151: (97.5, 98.5, 97.0, 98.0)}
        self.assertEqual(signal(scenario(bars=deep), 151, depth_a=0.5)[0], "order")

    def test_minimum_risk(self):
        at_floor = {150: (104.0, 105.0, 99.0, 99.25), 151: BREAK[151]}  # R = 1.0 = 0.25 x A
        self.assertEqual(signal(scenario(bars=at_floor), 151)[0], "order")
        below = {150: (104.0, 105.0, 99.25, 99.5), 151: BREAK[151]}    # R = 0.75
        status, info = signal(scenario(bars=below), 151)
        self.assertEqual(status, "min_risk")
        self.assertAlmostEqual(info["risk_a"], 0.1875)

    def test_gap_back_above_the_level(self):
        b = scenario(bars=BREAK)
        self.assertEqual(signal(b, 151, ask=100.0)[0], "gap_above")
        self.assertEqual(signal(b, 151, ask=99.75)[0], "order")
        self.assertEqual(signal(b, 151)[0], "order")  # default ask = open(t) + 1 tick = 99.75

    def test_one_signal_per_level(self):
        bars = dict(BREAK)
        bars.update({k: (103.0, 106.0, 102.0, 104.0) for k in range(152, 160)})
        bars[160] = (104.0, 105.0, 97.0, 99.0)
        bars[161] = BREAK[151]
        b = scenario(bars=bars)
        self.assertEqual(signal(b, 161)[0], "no_break")
        piv = swing_lows(b.low.to_numpy(), b.contract.to_numpy(), 5)
        # Judged at 160 alone the level is still intact (close 99 > L - D) and broken again: spending stops it.
        self.assertTrue([x for x in level_states(b, 160, piv)[3] if x["key"] == 40][0]["breaks"])

    def test_level_must_be_intact_and_departed(self):
        broken = dict(BREAK)
        broken[120] = (100.0, 101.0, 96.0, 97.0)  # close more than D below L before s
        broken[121] = (97.0, 112.0, 97.0, 111.0)
        b = scenario(bars=broken)
        piv = swing_lows(b.low.to_numpy(), b.contract.to_numpy(), 5)
        self.assertFalse([x for x in level_states(b, 150, piv)[3] if x["key"] == 40][0]["live"])
        self.assertEqual(signal(b, 151)[0], "no_break")  # only the new level from bar 120's low is live
        self.assertEqual(signal(scenario(base=101.0, bars=BREAK), 151)[0], "no_level")  # never 1 x A above

    def test_lowest_of_several_broken_levels(self):
        bars = {150: (106.0, 107.0, 97.0, 99.0), 151: BREAK[151]}
        status, info = signal(scenario(extra_pivot=(80, 103.0), bars=bars), 151)
        self.assertEqual((status, info["levels_broken"], info["level"], info["key"]), ("order", 2, 100, 40))

    def test_roll_between_s_and_t(self):
        bars = {179: BREAK[150], 180: BREAK[151]}  # bar 180 opens day 6 in contract 2
        status, info = signal(scenario(bars=bars, roll_day=6), 180)
        self.assertEqual(status, "contract_roll")
        self.assertFalse(info["same_contract"])


if __name__ == "__main__":
    unittest.main()
