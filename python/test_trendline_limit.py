import unittest

import numpy as np

from level_visit import swing_lows
from test_level_visit import make_bars
from test_trendline_support import scenario
from trendline_limit import bar_order, choose_line, floor_tick


def order(b, t, **kw):
    return bar_order(b, t, swing_lows(b.low.to_numpy(), b.contract.to_numpy(), kw.pop("n", 5)), **kw)


class OrderPriceTest(unittest.TestCase):
    def test_limit_and_stop_at_the_line(self):
        b, line = scenario()  # bars 8 above the line 100 + 0.2 (k - 40), anchors 40 and 100
        status, info = order(b, 170)
        self.assertEqual(status, "order")
        self.assertEqual((info["anchor1"], info["anchor2"]), (40, 100))
        self.assertAlmostEqual(info["line"], line[170])
        self.assertEqual(info["limit"], floor_tick(line[170]))
        self.assertEqual(info["stop"], floor_tick(info["limit"] - 0.5 * b.atr.iloc[170]))
        self.assertAlmostEqual(info["delta"], (b.open.iloc[170] - line[170]) / b.atr.iloc[170])

    def test_rounding_down_to_tick(self):
        self.assertEqual(floor_tick(126.24), 126.0)
        self.assertEqual(floor_tick(126.25), 126.25)  # exactly on a tick stays there
        self.assertEqual(floor_tick(126.2499999999), 126.25)  # float noise below a tick is absorbed

    def test_line_rises_with_the_bar(self):
        b, line = scenario()
        prices = [order(b, t)[1]["line"] for t in (150, 151, 152)]
        self.assertAlmostEqual(prices[1] - prices[0], 0.2)
        self.assertAlmostEqual(prices[2] - prices[1], 0.2)

    def test_price_must_be_above_the_line(self):
        b, line = scenario()
        self.assertEqual(order(b, 170, ask=line[170] + 0.01)[0], "order")
        self.assertEqual(order(b, 170, ask=line[170])[0], "above_price")  # strictly below the ask
        self.assertEqual(order(b, 170, ask=line[170] - 1)[0], "above_price")

    def test_uses_closed_bars_only(self):
        b, _ = scenario()
        before = order(b, 170)
        col = b.columns.get_loc("close")
        b.iloc[170, col] = -1e6  # bar t itself (and later bars) must not matter
        b.iloc[171:, col] = -1e6
        self.assertEqual(order(b, 170), before)

    def test_anchor_needs_confirmation(self):
        b, _ = scenario()
        self.assertEqual(order(b, 105, sessions=3)[0], "no_line")  # pivot 100 needs bar 105 closed
        self.assertEqual(order(b, 106, sessions=3)[0], "order")

    def test_broken_and_not_departed_lines_get_no_order(self):
        self.assertEqual(order(scenario(broken_at=150)[0], 170)[0], "no_line")
        self.assertEqual(order(scenario(broken_at=150)[0], 150)[0], "order")  # the break is bar 150's close
        self.assertEqual(order(scenario(offset=0.5, v=0.3)[0], 170)[0], "no_line")

    def test_nearest_line_below_price(self):
        lines = [dict(i=1, j=20, value=100.0), dict(i=5, j=30, value=104.0), dict(i=2, j=25, value=110.0)]
        self.assertEqual(choose_line(lines, 108)["value"], 104.0)
        self.assertEqual(choose_line(lines, 111)["value"], 110.0)
        self.assertIsNone(choose_line(lines, 100))
        ties = [dict(i=1, j=20, value=100.0), dict(i=3, j=20, value=100.0), dict(i=0, j=30, value=100.0)]
        self.assertEqual((choose_line(ties, 101)["i"], choose_line(ties, 101)["j"]), (0, 30))
        ties = ties[:2]
        self.assertEqual(choose_line(ties, 101)["i"], 3)

    def test_window_and_roll(self):
        b, _ = scenario()
        self.assertEqual(order(b, 30)[0], "missing_history")
        self.assertEqual(order(b, 170, sessions=2)[0], "no_line")  # anchor 40 left the window
        rolled = make_bars(b.low.to_numpy(), b.high.to_numpy(), b.close.to_numpy(), b.open.to_numpy(),
                           per_day=30, roll_day=3)
        self.assertEqual(order(rolled, 170)[0], "contract_roll")


if __name__ == "__main__":
    unittest.main()
