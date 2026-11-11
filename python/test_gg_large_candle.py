"""Session isolation, threshold boundaries, tick rounding and tightened-exit behavior."""
import unittest
import numpy as np
import pandas as pd
from analyze_gg_large_candle import features,stops
from test_rtl_weekly_engine import make
import rtl_weekly_engine as e


def frame(widths, start="2024-01-01 01:00"):
    return pd.DataFrame(dict(bar_time=pd.date_range(start,periods=len(widths),freq="30min"),
                             open=100.,high=100+np.array(widths),low=100.,close=101.))


class LargeCandle(unittest.TestCase):
    def test_signal_and_future_excluded(self):
        f=features(frame([2,2,2,2,2,6,1000]))
        self.assertEqual(f.iloc[5]["median"],2)
        self.assertTrue(stops(f,3)[0].iloc[5])
        self.assertEqual(f.iloc[6]["median"],2)

    def test_session_reset_and_five_prior_required(self):
        raw=pd.concat([frame([2]*6),frame([20,20,20,20,60,60],"2024-01-02 01:00")],ignore_index=True)
        f=features(raw)
        self.assertEqual(f.iloc[6].prior_count,0)
        flags,_=stops(f,3)
        self.assertFalse(flags.iloc[-2])
        self.assertTrue(flags.iloc[-1])
        self.assertEqual(f.iloc[-1]["median"],20)

    def test_threshold_is_lower_bound(self):
        f=features(frame([4]*5+[11.5,12,16]))
        flags,_=stops(f,3)
        self.assertEqual(flags.iloc[-3:].tolist(),[False,True,True])

    def test_median_resists_one_prior_outlier(self):
        f=features(frame([2,2,100,2,2,6]))
        self.assertEqual(f.iloc[-1]["median"],2)

    def test_even_median_and_zero_ranges(self):
        f=features(frame([0,2,4,6,20]))
        self.assertEqual(f.iloc[-1]["median"],3)
        z=features(frame([0]*5+[10]))
        self.assertFalse(stops(z,3)[0].iloc[-1])

    def test_tick_tie_rounds_up_and_off_is_identical(self):
        f=features(frame([.25]*5+[.75]))
        _,sl=stops(f,3)
        self.assertEqual(sl[-1],100.5)
        np.testing.assert_array_equal(stops(f,0)[1],f.low)

    def test_midnight_bars_excluded_from_reference(self):
        f=features(frame([100,100,2,2,2,2,2,6],start="2024-01-01 00:00"))
        self.assertEqual(f.iloc[-1].prior_count,5)
        self.assertEqual(f.iloc[-1]["median"],2)

    def test_tight_stop_scales_close_target(self):
        bars=make({0:[(60,102,110,100,108),(90,105,117,104,116),(120,116,117,115,116)]})
        slot=int(bars["day"][0]*48+2)
        tight=e.simulate_m30_ea(bars,signal="green",signal_stops={slot:105})[0].iloc[0]
        base=e.simulate_m30_ea(bars,signal="green")[0].iloc[0]
        self.assertEqual((tight.sl,tight.exit_price,tight.reason),(105,116,"target"))
        self.assertEqual(base.reason,"end_of_data")

    def test_pre_entry_low_does_not_stop_trade(self):
        bars=make({0:[(60,102,110,100,108),(90,106,113,101,112),(91,112,113,104,111)]})
        slot=int(bars["day"][0]*48+2)
        t=e.simulate_m30_ea(bars,signal="green",signal_stops={slot:105})[0].iloc[0]
        self.assertEqual((str(t.entry_time),str(t.exit_time),t.exit_price),
                         ("2024-01-01 01:30:40","2024-01-01 01:31:40",105))

    def test_invalid_stop_rejected(self):
        bars=make({0:[(60,102,110,100,108),(90,105,113,104,112)]})
        slot=int(bars["day"][0]*48+2)
        for stop in (99,110,np.nan,np.inf):
            with self.subTest(stop=stop),self.assertRaises(ValueError):
                e.simulate_m30_ea(bars,signal="green",signal_stops={slot:stop})


if __name__=="__main__":unittest.main()

