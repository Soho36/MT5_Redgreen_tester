"""Meaningful boundary/parser/path checks for whole-session news research."""
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from build_news_calendar import bls_records,fed_records
from analyze_rtl_news_days import envelope_dd,matched_random,event_masks,session_envelopes,DTYPE

class NewsStudyTests(unittest.TestCase):
    def test_publication_date_not_reference_month(self):
        text='December 2019 CPI https://www.bls.gov/news.release/archives/cpi_01142020.htm'
        self.assertEqual(bls_records(text,'fixture')[0]['date'],'2020-01-14')

    def test_emergency_and_cancelled_meeting_excluded(self):
        text='''<h5>March 2 (unscheduled) Meeting - 2020</h5>
        <a href="/newsevents/pressreleases/monetary20200303a.htm">Statement</a>
        <h5>March 17-18 (cancelled) Meeting - 2020</h5>
        <h5>April 28-29 Meeting - 2020</h5>
        <a href="/newsevents/pressreleases/monetary20200429a.htm">Statement</a>'''
        events,excluded=fed_records(text,'fixture')
        self.assertEqual([e['date'] for e in events],['2020-04-29'])
        self.assertEqual(len(excluded),2)

    def test_union_deduplicates_same_session(self):
        dates=pd.date_range('2024-06-11',periods=3)
        events=pd.DataFrame({'date':[dates[1],dates[1]],'event':['CPI','FOMC']})
        self.assertEqual(event_masks(dates,events)['skip_all'].tolist(),[False,True,False])

    def test_envelopes_match_full_paths_for_every_subset(self):
        paths=[np.array([0.,8.,-5.,3.]),np.array([0.,-6.,4.,1.]),np.array([0.,2.,-2.,-1.])]
        rows=[dict(net=p[-1],low=p.min(),high=p.max(),dd=(np.maximum.accumulate(p)-p).max()) for p in paths]
        daily=pd.DataFrame(rows)
        for bits in range(8):
            keep=np.array([bool(bits&(1<<k)) for k in range(3)])
            full=[0.]
            for p,k in zip(paths,keep):
                if k:full.extend((p[1:]+full[-1]).tolist())
            expected=(np.maximum.accumulate(full)-full).max()
            self.assertAlmostEqual(envelope_dd(daily,keep)[0],expected)

    def test_placebo_preserves_stratum_counts_and_zero_trade_days(self):
        dates=pd.date_range('2024-01-01',periods=60,freq='B')
        # Constant P&L by weekday makes any matched draw have exactly same net.
        values=dates.dayofweek.to_numpy(dtype=float)
        daily=pd.DataFrame(dict(net=values,low=np.zeros(len(dates)),high=values,dd=np.zeros(len(dates))),index=dates)
        removed=np.arange(len(dates))%4==0
        draws=matched_random(daily,removed,draws=101)
        np.testing.assert_allclose(draws.net,values[~removed].sum())
        self.assertTrue((draws.equity_dd==0).all())

    def test_zero_profit_close_charges_fee_on_its_own_date(self):
        raw=np.array([(int(pd.Timestamp('2016-01-04 01:00').timestamp()),500000.,500000.,0),
                      (int(pd.Timestamp('2016-01-05 01:00').timestamp()),500000.,500000.,0)],dtype=DTYPE)
        trades=pd.DataFrame(dict(exit_time=[pd.Timestamp('2016-01-04 23:30')],
            session=[pd.Timestamp('2016-01-04')],net_dollars=[-1.05],trade_profit=[0.]))
        with patch('analyze_rtl_news_days.np.memmap',return_value=raw),patch('analyze_rtl_news_days.PERIODS',{'test':('2016-01-01','2017-01-01')}):
            daily=session_envelopes('unused',trades,pd.date_range('2016-01-04',periods=2))
        self.assertAlmostEqual(daily.net.iloc[0],-1.05)
        self.assertAlmostEqual(daily.net.iloc[1],0.)
        self.assertEqual(daily.attrs['virtual_zero_profit_closures'],1)

if __name__=='__main__':unittest.main()
