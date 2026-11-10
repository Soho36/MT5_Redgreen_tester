"""Boundary and aggregation checks for cash-open attribution."""
import unittest
import pandas as pd
from analyze_rtl_open_halves import half, origin, stats

class AttributionTests(unittest.TestCase):
    def test_half_open_boundaries(self):
        t = pd.Series(pd.to_datetime(['2020-01-02 15:59:59','2020-01-02 16:00:00','2020-01-02 16:29:59',
                                     '2020-01-02 16:30:00','2020-01-02 16:59:59','2020-01-02 17:00:00']))
        self.assertEqual(list(half(t)), ['15:30','16:00','16:00','16:30','16:30','17:00'])
        self.assertEqual(list(origin(t,t.dt.normalize())),
                         ['before 16:00','16:00-16:30','16:00-16:30','16:30-17:00','16:30-17:00','17:00+'])

    def test_previous_date_is_not_same_day_origin(self):
        t = pd.Series(pd.to_datetime(['2020-01-01 17:30']))
        dates = pd.Series(pd.to_datetime(['2020-01-02']))
        self.assertEqual(origin(t,dates).iloc[0], 'prior date')

    def test_gross_net_and_stop_reason_are_separate(self):
        t = pd.DataFrame(dict(trade_profit=[20.,-10.,-2.],net_dollars=[18.95,-11.05,-3.05],
                             gross_r=[2.,-1.,-.2],net_r=[1.895,-1.105,-.305],stop=[False,True,False]))
        out=stats(t)
        self.assertEqual(out['gross_profit'],20)
        self.assertEqual(out['gross_loss'],12)
        self.assertAlmostEqual(out['net'],4.85)
        self.assertEqual(out['stops'],1)
        self.assertEqual(out['wins'],1)

if __name__ == '__main__':
    unittest.main()

