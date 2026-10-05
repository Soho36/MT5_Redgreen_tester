import unittest

from level_visit import swing_lows
from test_level_visit import make_bars
from test_trendline_support import scenario
from trendline_breakdown import bar_signal, choose_broken, line_states


def signal(b, t, **kw):
    return bar_signal(b, t, swing_lows(b.low.to_numpy(), b.contract.to_numpy(), kw.pop("n", 5)), **kw)


def set_bar(b, k, opn, high, low, close):
    for col, value in (("open", opn), ("high", high), ("low", low), ("close", close)):
        b.iloc[k, b.columns.get_loc(col)] = value


def rebuilt(b):
    """Recompute contract, sessions and A after editing bars."""
    return make_bars(b.low.to_numpy(), b.high.to_numpy(), b.close.to_numpy(), b.open.to_numpy(), per_day=30)


def breakdown(s=150, below=1.0, red=True, **kw):
    """scenario() (bars 8 above the line 100 + 0.2 (k - 40), anchors 40 and 100, A = 4, departed at bar 102)
    with bar s closing `below` points under the line."""
    b, line = scenario(**kw)
    v = line[s]
    close = v - below
    set_bar(b, s, close + 3 if red else close - 1, v + 5, close - 2, close)
    return rebuilt(b), line


class BreakdownSignalTest(unittest.TestCase):
    def test_red_close_below_the_line_gives_a_sell_stop_at_its_low(self):
        b, line = breakdown()
        status, info = signal(b, 151)
        self.assertEqual(status, "order")
        self.assertEqual((info["anchor1"], info["anchor2"]), (40, 100))
        self.assertAlmostEqual(info["line"], line[150])
        self.assertEqual((info["entry"], info["stop"]), (b.low.iloc[150], b.high.iloc[150]))
        self.assertEqual((info["lines_armed"], info["lines_live"], info["lines_broken"]), (1, 1, 1))
        self.assertEqual(info["bars_since_departure"], 150 - 102)
        self.assertAlmostEqual(info["depth_a"], 1.0 / 4)
        self.assertTrue(info["opens_above"])

    def test_close_on_the_line_is_not_a_break(self):
        self.assertEqual(signal(breakdown(below=0.0)[0], 151)[0], "no_break")

    def test_green_break_gives_no_trade_and_spends_the_line(self):
        b, _ = breakdown(red=False)
        status, info = signal(b, 151)
        self.assertEqual(status, "not_red")
        self.assertFalse(info["s_red"])
        b, line = breakdown(s=150, red=False)
        v = line[154]
        set_bar(b, 154, v, v + 5, v - 4, v - 2)  # a later red break (before bar 150's low is a known pivot)
        b = rebuilt(b)
        status, info = signal(b, 155)
        self.assertEqual(status, "no_break")
        self.assertEqual((info["lines_armed"], info["lines_live"]), (1, 0))  # still Q14-intact, but spent

    def test_close_below_before_the_first_departure_does_not_spend(self):
        b, line = breakdown()
        b.iloc[101, b.columns.get_loc("close")] = line[101] - 1  # departure is bar 102
        self.assertEqual(signal(b, 151)[0], "order")
        b, line = breakdown()
        b.iloc[110, b.columns.get_loc("close")] = line[110] - 1  # after the departure: spent
        self.assertEqual(signal(b, 151)[0], "no_break")

    def test_s1_needs_a_close_more_than_d_below(self):
        self.assertEqual(signal(breakdown(below=1.0)[0], 151, depth_a=0.5)[0], "no_break")
        self.assertEqual(signal(breakdown(below=2.0)[0], 151, depth_a=0.5)[0], "no_break")  # exactly D
        self.assertEqual(signal(breakdown(below=3.0)[0], 151, depth_a=0.5)[0], "order")
        b, line = breakdown(below=3.0)
        b.iloc[110, b.columns.get_loc("close")] = line[110] - 1  # within D: spends the primary, not S1
        self.assertEqual(signal(b, 151)[0], "no_break")
        self.assertEqual(signal(b, 151, depth_a=0.5)[0], "order")

    def test_gap_through_the_entry_places_no_order(self):
        b, _ = breakdown()
        entry = b.low.iloc[150]
        self.assertEqual(signal(b, 151, bid=entry)[0], "gap_below")
        self.assertEqual(signal(b, 151, bid=entry - 1)[0], "gap_below")
        self.assertEqual(signal(b, 151, bid=entry + 0.25)[0], "order")
        self.assertEqual(signal(b, 151)[0], "order")  # default bid = open(t)

    def test_uses_bars_up_to_s_only(self):
        b, _ = breakdown()
        before = signal(b, 151, bid=200.0)
        for col in ("open", "high", "low", "close"):
            b.iloc[151:, b.columns.get_loc(col)] = -1e6
        self.assertEqual(signal(b, 151, bid=200.0), before)

    def test_line_is_evaluated_at_the_open_of_s(self):
        # Pivot 100 is known once bar 105 has closed, i.e. at the open of s = 106 (t = 107).
        b, line = breakdown(s=106, below=0.5)
        b.iloc[106, b.columns.get_loc("low")] = b.low.iloc[100] + 0.25  # keep pivot 100 a swing low
        self.assertEqual(signal(b, 107, sessions=3)[0], "order")
        b, line = breakdown(s=105, below=0.5)
        b.iloc[105, b.columns.get_loc("low")] = b.low.iloc[100] + 0.25
        self.assertEqual(signal(b, 106, sessions=3)[0], "no_line")

    def test_a_spent_line_stays_spent_when_a_grows(self):
        # Bars 3 above the line, shallow anchor Vs (closes <= V + 6, departed with A = 4). Break at 150. Wide bars 151-164 raise A(165)
        # to about 8 and close >= V + A, so judged at 165 alone the first departure moves to 151, after the break:
        # the line looks live again. It must stay spent.
        b, line = breakdown(s=150, below=1.0, offset=3.0, v=0.8)
        self.assertEqual(signal(b, 151)[0], "order")  # the first break signals
        for k in range(151, 165):
            set_bar(b, k, line[k] + 13, line[k] + 14, line[k] + 6, line[k] + 12)
        v = line[165]
        set_bar(b, 165, v + 4, v + 5, v - 4, v - 2)
        b = rebuilt(b)
        piv = swing_lows(b.low.to_numpy(), b.contract.to_numpy(), 5)
        reason, a, _, lines = line_states(b, 165, piv)
        self.assertGreater(a, 5)
        self.assertEqual([(x["i"], x["j"], x["live"], x["breaks"], x["departure"]) for x in lines],
                         [(40, 100, True, True, 151)])
        status, info = signal(b, 166)
        self.assertEqual(status, "no_break")
        self.assertEqual((info["lines_armed"], info["lines_live"], info["lines_broken"]), (1, 0, 0))

    def test_highest_broken_line_is_reported(self):
        lines = [dict(i=1, j=20, value=100.0), dict(i=5, j=30, value=104.0), dict(i=2, j=25, value=104.0)]
        self.assertEqual((choose_broken(lines)["i"], choose_broken(lines)["j"]), (5, 30))
        ties = [dict(i=1, j=30, value=100.0), dict(i=3, j=30, value=100.0)]
        self.assertEqual(choose_broken(ties)["i"], 3)

    def test_window_and_roll(self):
        b, _ = breakdown()
        self.assertEqual(signal(b, 30)[0], "missing_history")
        self.assertEqual(signal(b, 151, sessions=2)[0], "no_line")  # anchor 40 left the window
        # Roll between s and t: bar 180 opens day 6 in contract 2, s = 179 is the last bar of contract 1.
        rolled = make_bars(b.low.to_numpy(), b.high.to_numpy(), b.close.to_numpy(), b.open.to_numpy(),
                           per_day=30, roll_day=6)
        status, info = signal(rolled, 180)
        self.assertEqual(status, "contract_roll")
        self.assertFalse(info["same_contract"])
        self.assertTrue(signal(rolled, 179)[1]["same_contract"])


if __name__ == "__main__":
    unittest.main()
