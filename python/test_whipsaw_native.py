"""Calendar causality and exact whole-session overlay arithmetic."""
import unittest
import numpy as np
import pandas as pd
from prepare_whipsaw_native import event_calendar
from analyze_whipsaw_native import combine_envelopes, interval
from analyze_rtl_news_days import envelope_dd


def envelope(path):
    x = np.r_[0., path]
    return dict(net=x[-1], low=x.min(), high=x.max(), dd=(np.maximum.accumulate(x)-x).max())


class NativeOverlayTests(unittest.TestCase):
    def test_next_sessions_and_overlapping_events(self):
        dates = pd.to_datetime(['2024-01-05','2024-01-08','2024-01-09','2024-01-10','2024-01-11'])
        panel = pd.DataFrame(dict(whipsaw=[True,True,False,False,False],position=np.arange(5)),index=dates)
        pairs = event_calendar(panel,pd.DataFrame(index=dates))
        self.assertTrue((pairs.session > pairs.event).all())
        self.assertEqual(pairs.loc[pairs.horizon.eq(1),'session'].tolist(),[dates[1],dates[2]])
        self.assertEqual(pairs.session.nunique(),4)
        self.assertEqual(len(pairs),6)

    def test_endpoint_excluded(self):
        dates=pd.to_datetime(['2026-09-29','2026-09-30','2026-10-01'])
        panel=pd.DataFrame(dict(whipsaw=[True,True,False],position=np.arange(3)),index=dates)
        pairs=event_calendar(panel,pd.DataFrame(index=dates))
        self.assertEqual(len(pairs),1)

    def test_scaled_and_replaced_envelopes_equal_full_paths(self):
        dates=pd.date_range('2024-01-01',periods=3)
        paths=[np.array([10.,-8.,4.]),np.array([3.,-15.,-2.]),np.array([8.,-5.,9.])]
        base=pd.DataFrame([envelope(p) for p in paths],index=dates)
        selected=base.copy();selected.loc[[dates[0],dates[2]]]=0
        for replace in (False,True):
            alternative=np.array([15.,-25.,5.])
            if replace:selected.loc[dates[1]]=pd.Series(envelope(alternative))
            out=combine_envelopes(base,selected,[dates[1]],replace)
            actual=[];balance=0.
            for i,p in enumerate(paths):
                q=alternative if replace and i==1 else p*(2 if i==1 else 1)
                actual.extend(balance+q);balance+=q[-1]
            x=np.r_[0.,actual]
            self.assertAlmostEqual(envelope_dd(out)[0],(np.maximum.accumulate(x)-x).max())
            self.assertAlmostEqual(out.net.sum(),balance)

    def test_mismatched_selected_path_rejected(self):
        dates=pd.date_range('2024-01-01',periods=1)
        a=pd.DataFrame([envelope([10.,-5.,2.])],index=dates)
        b=a.copy();b['high']=20
        with self.assertRaises(AssertionError):combine_envelopes(a,b,dates)

    def test_zero_overlay_has_zero_interval(self):
        self.assertEqual(interval(np.zeros(90),pd.date_range('2024-01-01',periods=90)),[0.,0.])


if __name__=='__main__':unittest.main()
