"""Boundary/causality tests for buy-stop midpoint RTL, not profitability tests."""
import unittest
import pandas as pd
from test_rtl_sell_limit_fade import bars, at, RED
from rtl_midpoint import midpoint, simulate, economics

class MidpointTests(unittest.TestCase):
    def test_midpoint_includes_wicks_and_rounds_half_ticks_up(self):
        self.assertEqual(midpoint(101, 99), 100)
        self.assertEqual(midpoint(101.25, 99), 100.25)

    def test_enters_before_high_and_keeps_low_stop(self):
        t = simulate(bars(RED + [('10:30', 99.5, 100.25, 99.25, 100), ('10:31', 100, 100, 98.75, 99)]))[0].iloc[0]
        self.assertEqual((t.requested, t.fill, t.sl, t.exit_price, t.reason), (100, 100, 99, 99, 'sl'))
        self.assertEqual(t.entry_time, at('10:30:40'))

    def test_close_at_low_does_not_invalidate_a_future_buy_stop(self):
        t = simulate(bars([('10:00', 100.5, 101, 99, 99), ('10:30', 99, 100.25, 99, 100)]))[0]
        self.assertEqual(len(t), 1)
        self.assertEqual(t.fill.iloc[0], 100)

    def test_midpoint_at_or_below_ask_is_skipped_no_limit(self):
        for opening in (99.75, 100, 100.25):
            t, skipped = simulate(bars(RED + [('10:30', opening, 101, 99.5, 100.5)]))
            self.assertEqual((len(t), skipped), (0, 1))

    def test_high_touch_alone_does_not_exit(self):
        t = simulate(bars(RED + [('10:30', 99.5, 101.5, 99.5, 100.5), ('11:00', 100.5, 100.5, 100, 100)]))[0].iloc[0]
        self.assertEqual(t.reason, 'end_of_data')

    def test_close_at_new_one_r_exits_next_bar(self):
        t = simulate(bars(RED + [('10:30', 99.5, 101.5, 99.5, 101), ('11:00', 101.25, 101.5, 101, 101.25)]))[0].iloc[0]
        self.assertEqual((t.reason, t.exit_price, t.exit_time), ('target', 101.25, at('11:00:00')))
        self.assertEqual(economics(pd.DataFrame([t]), short=False).gross_r.iloc[0], 1.25)

    def test_rounded_entry_recalculates_target(self):
        red = [('10:00', 100.5, 101.25, 99, 99.5)]
        t = simulate(bars(red + [('10:30', 99.5, 101.5, 99.5, 101.25), ('11:00', 101.25, 101.5, 101, 101.5), ('11:30', 101.75, 102, 101.75, 102)]))[0].iloc[0]
        self.assertEqual((t.fill, t.sl, t.reason, t.exit_time), (100.25, 99, 'target', at('11:30:00')))

    def test_rejected_red_replaces_pending_order(self):
        rows = RED + [('10:30', 99.5, 99.5, 99.25, 99.25), ('11:00', 99.75, 100.25, 99.75, 100)]
        self.assertEqual(len(simulate(bars(rows))[0]), 0)

    def test_green_preserves_pending_order(self):
        rows = RED + [('10:30', 99.5, 99.75, 99.5, 99.75), ('11:00', 99.75, 100.25, 99.75, 100)]
        t = simulate(bars(rows))[0].iloc[0]
        self.assertEqual((t.requested, t.submitted), (100, at('10:30:00')))

    def test_early_close_flattens_and_cancels(self):
        rows = RED + [('10:30', 99.5, 100.25, 99.5, 100), ('11:00', 100.5, 102, 100, 102)]
        t = simulate(bars(rows), {20200102: 660})[0].iloc[0]
        self.assertEqual((t.reason, t.exit_price), ('flatten', 100.5))
        rows = RED + [('10:30', 99.5, 99.75, 99.5, 99.75), ('11:00', 99.75, 102, 99.75, 102)]
        self.assertEqual(len(simulate(bars(rows), {20200102: 660})[0]), 0)

if __name__ == '__main__':
    unittest.main()
