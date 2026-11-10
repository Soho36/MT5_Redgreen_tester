"""Boundary, clock, quote ordering, and changed-state checks."""
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from build_news_windows import timed_record,merge_windows,window_ids
from rtl_news_window_engine import simulate
from analyze_rtl_news_days import session_envelopes,DTYPE

def fixture(fill_before=True,boundary_gap=False):
    day=int(np.datetime64('2016-01-04','D').astype(int))
    bars=dict(day=np.full(6,day),date=np.full(6,20160104),minute=np.array([60,90,104,105,120,1410]),
              o=np.array([100,99,99,103 if boundary_gap else 101,102,103],float),
              h=np.array([102,100,103 if fill_before else 100,104,104,104],float),
              l=np.array([98,99,99,100,101,102],float),c=np.array([99,99,101,102,103,103],float))
    windows=pd.DataFrame({'start':pd.to_datetime(['2016-01-04 01:45']),'end':pd.to_datetime(['2016-01-04 02:15'])})
    return bars,windows

class WindowTests(unittest.TestCase):
    def test_stressed_fee_at_unobserved_zero_profit_exit(self):
        raw=np.array([(int(pd.Timestamp('2016-01-04 01:00').timestamp()),500000.,500000.,0),
                      (int(pd.Timestamp('2016-01-05 01:00').timestamp()),500000.,500000.,0)],dtype=DTYPE)
        trades=pd.DataFrame(dict(exit_time=[pd.Timestamp('2016-01-04 23:30')],
            session=[pd.Timestamp('2016-01-04')],net_dollars=[-2.05],trade_profit=[0.]))
        with patch('analyze_rtl_news_days.np.memmap',return_value=raw),patch('analyze_rtl_news_days.PERIODS',{'test':('2016-01-01','2017-01-01')}):
            daily=session_envelopes('unused',trades,pd.date_range('2016-01-04',periods=2),cost=2.05)
        self.assertAlmostEqual(daily.net.iloc[0],-2.05)
        self.assertAlmostEqual(daily.net.iloc[1],0.)

    def test_clock_us_dst_not_europe(self):
        for date,utc in [('2024-03-08','13:30'),('2024-03-11','12:30'),('2024-10-28','12:30'),('2024-11-04','13:30')]:
            row=timed_record(date,'CPI','08:30','url','test','test')
            self.assertIn('15:30:00',row['research_time'])
            self.assertIn(utc,row['event_utc'])

    def test_merge_touching_and_older_gap(self):
        events=pd.DataFrame({'research_time':pd.to_datetime(['2012-01-25 19:30','2012-01-25 21:15','2024-01-31 21:00','2024-01-31 21:30']),
                             'event':['FOMC','PRESS','FOMC','PRESS']})
        w=merge_windows(events)
        self.assertEqual(len(w),3)
        self.assertEqual(w.iloc[1].start-w.iloc[0].end,pd.Timedelta(minutes=45))
        self.assertEqual(w.iloc[2].end-w.iloc[2].start,pd.Timedelta(minutes=90))
        touching=events.iloc[2:].copy();touching.iloc[1,0]=pd.Timestamp('2024-01-31 22:00')
        self.assertEqual(len(merge_windows(touching)),1)

    def test_half_open_and_empty(self):
        _,w=fixture()
        times=pd.to_datetime(['2016-01-04 01:44:59','2016-01-04 01:45:00','2016-01-04 02:14:59','2016-01-04 02:15:00'])
        self.assertEqual(window_ids(times,w).tolist(),[-1,0,0,-1])
        self.assertEqual(window_ids(times,w.iloc[:0]).tolist(),[-1]*4)

    def test_existing_position_flattened_at_quarter_hour_only_in_flat_mode(self):
        b,w=fixture()
        entry,_=simulate(b,w,1);flat,_=simulate(b,w,2)
        self.assertEqual(len(entry),1);self.assertEqual(len(flat),1)
        self.assertEqual(entry.iloc[0].reason,'flatten')
        self.assertEqual(flat.iloc[0].reason,'news')
        self.assertEqual(flat.iloc[0].exit_time,pd.Timestamp('2016-01-04 01:45'))
        self.assertEqual(flat.iloc[0].exit_price,101)

    def test_cancel_prevents_later_fill_and_boundary_fill_precedes_callback(self):
        b,w=fixture(False)
        base,_=simulate(b,w,0);filtered,_=simulate(b,w,1)
        self.assertEqual(len(base),1);self.assertEqual(len(filtered),0)
        b,w=fixture(False,True)
        flat,_=simulate(b,w,2)
        self.assertEqual(len(flat),1)
        self.assertEqual(flat.iloc[0].entry_time,flat.iloc[0].exit_time)
        self.assertEqual(flat.iloc[0].exit_price,103)

if __name__=='__main__':unittest.main()
