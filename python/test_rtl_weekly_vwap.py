import unittest
import numpy as np
import pandas as pd
from analyze_rtl_weekly_vwap import week, weekly_decisions

class WeeklyVwapBoundaries(unittest.TestCase):
    def test_week_boundary_unknown_equality_and_threshold(self):
        submitted=pd.Series(pd.to_datetime(['2020-01-06 01:00','2020-01-06 01:30',
                                           '2020-01-06 02:00','2020-01-07 01:00']))
        feature_weeks=pd.Series(pd.to_datetime(['2019-12-30','2020-01-06','2020-01-06','2020-01-06']))
        known,skip=weekly_decisions(submitted,feature_weeks,pd.Series([1.,98.,97.75,97.75]),
                                    pd.Series([100.]*4),pd.Series([2.]*4))
        np.testing.assert_array_equal(known,[False,True,True,True])
        np.testing.assert_array_equal(skip,[False,False,True,True])

    def test_unavailable_a20_and_same_week_previous_day(self):
        s=pd.Series(pd.to_datetime(['2020-01-07 01:00','2020-01-07 01:00']))
        w=week(pd.Series(pd.to_datetime(['2020-01-06 23:00']*2)))
        known,skip=weekly_decisions(s,w,pd.Series([90.,90.]),pd.Series([100.,100.]),pd.Series([np.nan,1.]))
        np.testing.assert_array_equal(known,[False,True])
        np.testing.assert_array_equal(skip,[False,True])

if __name__=='__main__': unittest.main()
