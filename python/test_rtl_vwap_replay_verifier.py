"""Causal boundary cases for the independent full-replay decision audit."""
import unittest
import numpy as np
import pandas as pd

from verify_rtl_vwap_replay import (candidate_lookup,independent_partition,net_equity,DTYPE,
                                   closed_episodes,drawdown_episodes,complete_deal_pairs)


class ReplayAuditBoundaries(unittest.TestCase):
    def setUp(self):
        self.day=int(pd.Timestamp('2020-01-02').timestamp())
        self.frame=pd.DataFrame(dict(available_epoch=[self.day+5400,self.day+7200],
            session_epoch=[self.day,self.day],bar_epoch=[self.day+3600,self.day+5400],
            close=[98.,98.],vwap=[100.,200.],a20=[2.,2.],known=[1,1]))

    def test_equality_allows_and_exact_availability_is_known(self):
        times=np.array([self.day+5400]*2)*1000
        _,known,blocked=candidate_lookup(self.frame,times,[98.,97.75],True)
        np.testing.assert_array_equal(known,[True,True])
        np.testing.assert_array_equal(blocked,[False,True])

    def test_before_first_feature_and_next_session_are_unknown(self):
        times=np.array([self.day+5399,self.day+86400+3600])*1000
        _,known,blocked=candidate_lookup(self.frame,times,[1.,1.],True)
        self.assertFalse(known.any())
        self.assertFalse(blocked.any())

    def test_future_feature_changes_do_not_change_current_decision(self):
        times=np.array([self.day+6000])*1000
        first=candidate_lookup(self.frame,times,[97.75],True)
        changed=self.frame.copy()
        changed.loc[1,['vwap','a20']]=[100000.,0.00001]
        second=candidate_lookup(changed,times,[97.75],True)
        for a,b in zip(first,second):
            np.testing.assert_array_equal(a,b)

    def test_gate_off_preserves_unfavorable_candidate(self):
        times=np.array([self.day+5400])*1000
        _,known,blocked=candidate_lookup(self.frame,times,[97.75],False)
        self.assertTrue(known[0])
        self.assertFalse(blocked[0])

    def test_partition_distinguishes_new_removed_and_changed_execution(self):
        times=pd.date_range('2020-01-02 01:00',periods=4,freq='h')
        f=pd.DataFrame(dict(submitted=times,requested_price=100.,original_sl=99.,
            entry_time=times,exit_time=times+pd.Timedelta(minutes=10),fill_price=100.,
            exit_price=[101.,99.,102.,100.],trade_profit=[2.,-2.,4.,0.],
            net_dollars=[.95,-3.05,2.95,-1.05],net_r=[.475,-1.525,1.475,-.525]))
        left=f.iloc[:3].copy()
        right=f.iloc[[0,2,3]].copy()
        right.loc[2,['exit_price','trade_profit','net_dollars','net_r']]=[103.,6.,4.95,2.475]
        groups,_=independent_partition(left,right)
        self.assertEqual({k:v['matched_candidates'] for k,v in groups.items()},
                         dict(unchanged=1,execution_changed=1,removed=1,new=1))
        self.assertAlmostEqual(sum(v['net_delta'] for v in groups.values()),4.)

    def test_sampled_equity_cost_timing_and_unfinished_duration(self):
        start=pd.Timestamp('2020-01-02')
        t0=int(start.value//1000000)
        entry=t0+3600000
        raw=np.array([(entry,500000.,500000.),(entry+60000,500000.,500004.),
                      (entry+120000,500001.,500001.)],dtype=DTYPE)
        trades=pd.DataFrame(dict(entry_time_msc=[entry],exit_time_msc=[entry+120000],trade_profit=[1.]))
        result,peak,trough=net_equity(raw,trades,start,start+pd.Timedelta(days=1),1.05)
        self.assertAlmostEqual(result['sampled_open_equity_dd'],3.)
        self.assertAlmostEqual(result['net_endpoint'],-.05)
        self.assertAlmostEqual(result['sampled_open_equity_dd_duration_days'],(86400000-1-3660000)/86400000.)
        self.assertEqual(peak,'2020-01-02 01:01:00')
        self.assertEqual(trough,'2020-01-02 01:02:00')

    def test_closed_drawdown_includes_sparse_recovery_time(self):
        times=pd.to_datetime(['2020-01-02','2020-01-03','2020-01-10'])
        depth,duration=closed_episodes([10.,-5.,5.],times,'2020-01-11')
        self.assertEqual(depth,5.)
        self.assertEqual(duration,8.)

    def test_first_loss_starts_at_first_trade_and_tied_peak_resets(self):
        times=pd.to_datetime(['2020-01-02','2020-01-03','2020-01-10','2020-01-11'])
        self.assertEqual(closed_episodes([-5.],[times[0]],'2020-01-05'),(5.,3.))
        self.assertEqual(drawdown_episodes([10.,10.,5.,10.],times),(5.,8.))

    def test_fast_complete_trade_and_missing_or_duplicate_deals(self):
        deals=pd.DataFrame(dict(deal=[1,2],type=[0,1],entry=[0,1],
                                position_id=[10,10],time_msc=[1000,1000]))
        entry,exit_=complete_deal_pairs(deals)
        self.assertEqual(len(entry),1)
        self.assertEqual(exit_.iloc[0].time_msc,entry.iloc[0].time_msc)
        with self.assertRaises(AssertionError):
            complete_deal_pairs(deals.iloc[:1])
        with self.assertRaises(AssertionError):
            complete_deal_pairs(pd.concat([deals,deals]))
        changed=deals.copy()
        changed.loc[1,'position_id']=11
        with self.assertRaises(AssertionError):
            complete_deal_pairs(changed)


if __name__=='__main__':
    unittest.main()
