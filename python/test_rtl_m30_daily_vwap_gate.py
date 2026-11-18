import unittest
import numpy as np
import pandas as pd
from rtl_m30_daily_vwap_gate import events_from_features
from rtl_weekly_opposite_gate import halt_windows
from build_news_windows import window_ids

def fixture(closes,dates=None,known=None):
    dates=pd.to_datetime(dates) if dates else pd.date_range('2020-01-27',periods=len(closes),freq='B')
    f=pd.DataFrame(dict(close=closes,vwap=100.,a20=1.,known=known if known is not None else True),index=dates)
    b=dict(day=dates.to_numpy(dtype='datetime64[D]').astype('int64'),minute=np.full(len(dates),60))
    return f,b

class RegimeTests(unittest.TestCase):
    def test_below_halts_above_resumes_equality_keeps_state(self):
        f,b=fixture([98,99,100,99,98,100,100])
        self.assertEqual(events_from_features(f,b).enabled.tolist(),[0,0,1,1,0,1])

    def test_month_reset_does_not_clear_halt(self):
        f,b=fixture([98,99,100,100],['2020-01-31','2020-02-03','2020-02-04','2020-02-05'])
        e=events_from_features(f,b)
        self.assertEqual(e.enabled.tolist(),[0,0,1])
        self.assertEqual(e.effective.iloc[0],pd.Timestamp('2020-02-03 01:00'))

    def test_colour_not_required(self):
        f,b=fixture([98,100,100]);f['open']=[97,101,100] # green halt, red resume
        self.assertEqual(events_from_features(f,b).enabled.tolist(),[0,1])

    def test_unknown_preserves_state(self):
        f,b=fixture([98,98,100,100,100],known=[False,True,False,True,True])
        self.assertEqual(events_from_features(f,b).enabled.tolist(),[1,0,0,1])

    def test_no_unfinished_day_or_future_label(self):
        f,b=fixture([98,100,98]);e=events_from_features(f,b)
        f.iloc[-1,f.columns.get_loc('close')]=1000
        pd.testing.assert_frame_equal(e,events_from_features(f,b))
        windows=halt_windows(e,'2020-02-01');at=e.effective.iloc[0]
        self.assertEqual(window_ids([at-pd.Timedelta(seconds=1),at,e.effective.iloc[1]],windows).tolist(),[-1,0,-1])

if __name__=='__main__':unittest.main()
