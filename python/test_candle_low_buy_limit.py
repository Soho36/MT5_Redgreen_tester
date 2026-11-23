"""Causal order lifecycle and price-side tests for candle-low limits."""
import unittest
from test_rtl_sell_limit_fade import bars, at
from candle_low_buy_limit import simulate


class CandleLowTests(unittest.TestCase):
    def test_every_colour_and_exact_geometry(self):
        for close in (99.5,100,100.5):
            with self.subTest(close=close):
                t=simulate(bars([('10:00',100,101,99,close),
                    ('10:30',100,100,98.75,99.5),('10:31',100,101,100,101)]))[0].iloc[0]
                self.assertEqual((t.requested,t.fill,t.sl,t.tp),(99,99,97,101))
                self.assertEqual((t.reason,t.exit_price),('tp',101))
                self.assertEqual(t.submitted,at('10:30:00'))

    def test_single_tick_fill_has_no_phantom_second_quote(self):
        data=bars([('10:00',100,100.25,100,100),('10:30',100,100.25,100,100),
                   ('10:31',99.75,99.75,99.75,99.75),('10:32',100,100.25,100,100.25)])
        import numpy as np
        data['ticks']=np.array([10,10,1,3])
        t=simulate(data)[0].iloc[0]
        self.assertEqual((t.fill,t.sl,t.tp),(100,99.75,100.25))
        self.assertEqual(t.reason,'tp')

    def test_bid_touch_does_not_fill_buy_limit(self):
        rows=[('10:00',100,101,99,100),('10:30',100,100,99,100)]
        self.assertTrue(simulate(bars(rows))[0].empty)

    def test_stop_is_one_full_range_below_low(self):
        rows=[('10:00',100,101,99,100),('10:30',100,100,98.75,99.5),
              ('10:31',99.5,99.5,96.5,97)]
        t=simulate(bars(rows))[0].iloc[0]
        self.assertEqual((t.reason,t.exit_price),('sl',97))

    def test_new_green_candle_replaces_pending(self):
        rows=[('10:00',100,101,99,99.5),('10:30',100.5,102,100,101),
              ('11:00',101,101,99.75,100.5)]
        t=simulate(bars(rows))[0].iloc[0]
        self.assertEqual((t.requested,t.sl,t.tp),(100,98,102))
        self.assertEqual(t.submitted,at('11:00:00'))

    def test_opening_tick_can_fill_old_order_before_replacement(self):
        rows=[('10:00',100,101,99,99.5),('10:30',100.5,102,100,101),
              ('11:00',98.5,100,98.5,99)]
        t=simulate(bars(rows))[0].iloc[0]
        self.assertEqual((t.requested,t.submitted,t.entry_time),(99,at('10:30:00'),at('11:00:00')))

    def test_zero_range_cancels_pending(self):
        rows=[('10:00',100,101,99,100),('10:30',100,100,100,100),
              ('11:00',100,100,98.75,99)]
        self.assertTrue(simulate(bars(rows))[0].empty)

    def test_gap_below_low_does_not_submit_market_order(self):
        rows=[('10:00',100,101,99,100),('10:30',98,100,98,99)]
        t,skips=simulate(bars(rows))
        self.assertTrue(t.empty)
        self.assertEqual(skips,1)

    def test_early_session_close_and_single_position(self):
        rows=[('10:00',100,101,99,100),('10:30',100,100,98.75,99.5),
              ('11:00',99.5,100,98.75,99.5),('11:30',100,100,99.75,100)]
        t=simulate(bars(rows),{20200102:690})[0]
        self.assertEqual(len(t),1)
        self.assertEqual((t.iloc[0].reason,t.iloc[0].exit_price),('flatten',100))
        self.assertEqual(t.iloc[0].submitted,at('10:30:00'))

    def test_penetration_sensitivity_on_entry_and_target(self):
        rows=[('10:00',100,101,99,100),('10:30',100,100,98.75,99.5)]
        self.assertEqual(len(simulate(bars(rows))[0]),1)
        self.assertTrue(simulate(bars(rows),through=.25)[0].empty)
        rows=[('10:00',100,101,99,100),('10:30',100,100,98.5,99.5),
              ('10:31',100,101,100,100.5)]
        self.assertEqual(simulate(bars(rows))[0].iloc[0].reason,'tp')
        self.assertEqual(simulate(bars(rows),through=.25)[0].iloc[0].reason,'end_of_data')


if __name__=='__main__': unittest.main()
