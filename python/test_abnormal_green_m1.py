"""Causality, gap fills and intraminute ambiguity regression tests."""
import unittest
import numpy as np
from abnormal_green_m1 import detect, simulate, metrics


def bars(n=25):
    return dict(date=np.full(n,20260102),day=np.full(n,20455),minute=np.arange(60,60+n),
                o=np.full(n,100.),h=np.full(n,100.5),l=np.full(n,99.5),c=np.full(n,100.))


def put(b,i,o,h,l,c):
    for k,v in zip('ohlc',(o,h,l,c)):b[k][i]=v


def fixture(n=25):
    b=bars(n);put(b,20,100,110,100,109)
    return b


class AbnormalGreenTests(unittest.TestCase):
    def test_exact_threshold_and_no_signal_or_future_in_reference(self):
        b=fixture();s=detect(b)
        self.assertEqual(s['index'].tolist(),[20]);self.assertEqual(s.iloc[0].ratio,10.)
        put(b,21,1,10000,1,9999)
        self.assertEqual(detect(b).iloc[0].prior20_mean,1.)

    def test_red_doji_and_zero_reference_not_signals(self):
        b=fixture();b['c'][20]=b['o'][20]
        self.assertTrue(detect(b).empty)
        b['c'][20]=99;self.assertTrue(detect(b).empty)
        b=fixture();b['h'][:20]=b['l'][:20]=100
        self.assertTrue(detect(b).empty)

    def test_gap_and_session_reference_excluded_but_logged(self):
        b=fixture();b['minute'][10:]+=2
        self.assertEqual(detect(b).iloc[0].eligibility,'nonconsecutive_reference')
        b=fixture();b['date'][:10]=20260101
        self.assertEqual(detect(b).iloc[0].eligibility,'nonconsecutive_reference')

    def test_missing_next_minute_and_cutoff(self):
        b=fixture();b['minute'][21:]+=1
        self.assertEqual(detect(b).iloc[0].eligibility,'missing_next_minute')
        b=fixture()
        self.assertEqual(detect(b,cutoffs={20260102:81}).iloc[0].eligibility,'outside_entry_session')

    def test_post_close_entry_and_fixed_one_r_target(self):
        b=fixture();put(b,21,109,121,108,120)
        tr,_=simulate(b,detect(b))
        self.assertEqual(len(tr),1);r=tr.iloc[0]
        self.assertEqual(r.entry_index,21);self.assertEqual(r.entry_price,110)
        self.assertEqual(r.sl,99.75);self.assertEqual(r.tp,120.25)
        self.assertEqual(r.reason,'tp');self.assertAlmostEqual(r.net,19.45)

    def test_entry_gap_pays_worse_open_and_resets_target(self):
        b=fixture();put(b,21,112,126,111,124)
        tr,_=simulate(b,detect(b));r=tr.iloc[0]
        self.assertEqual(r.entry_price,112);self.assertEqual(r.tp,124.25)
        self.assertTrue(r.gap_entry);self.assertEqual(r.reason,'tp')

    def test_stop_gap_can_lose_more_than_one_r(self):
        b=fixture();put(b,21,109,111,108,110);put(b,22,95,98,94,96)
        tr,_=simulate(b,detect(b));r=tr.iloc[0]
        self.assertEqual(r.exit_price,95);self.assertEqual(r.reason,'sl')
        self.assertLess(r.net_r,-1);self.assertEqual(r.entry_index,21)

    def test_entry_stop_ambiguity_changes_result(self):
        b=fixture();put(b,21,109,111,99,110);put(b,22,110,121,109,120)
        lo,_=simulate(b,detect(b),mode='low_first')
        hi,_=simulate(b,detect(b),mode='high_first')
        self.assertEqual(lo.iloc[0].reason,'tp');self.assertEqual(hi.iloc[0].reason,'sl')
        self.assertTrue(lo.iloc[0].entry_overlap)

    def test_pending_survives_ordinary_candle_and_low_touch(self):
        b=fixture();put(b,21,105,109,99,103);put(b,22,103,121,102,120)
        tr,states=simulate(b,detect(b));self.assertEqual(tr.iloc[0].entry_index,22)
        self.assertEqual(states[20],'filled');self.assertEqual(tr.iloc[0].wait_minutes,2)

    def test_cutoff_cancels_and_flattens_before_open_fill(self):
        b=fixture();put(b,21,109,111,108,110);put(b,22,113,121,112,120)
        tr,_=simulate(b,detect(b),cutoffs={20260102:82})
        self.assertEqual(tr.iloc[0].reason,'flatten');self.assertEqual(tr.iloc[0].exit_price,113)
        tr,states=simulate(b,detect(b),cutoffs={20260102:81})
        self.assertTrue(tr.empty);self.assertEqual(states[20],'expired_session')

    def test_busy_signal_not_queued(self):
        b=fixture(45)
        for i in range(21,45):put(b,i,110,110.5,109.5,110)
        put(b,21,109,111,108,110)
        put(b,41,100,115,100,110)
        put(b,42,110,121,109,120)
        tr,states=simulate(b,detect(b))
        self.assertEqual(states[41],'busy');self.assertEqual(len(tr),1)
        self.assertEqual(tr.iloc[0].signal_index,20)

    def test_new_abnormal_signal_replaces_pending(self):
        b=fixture(45)
        for i in range(21,45):put(b,i,105,105.5,104.5,105)
        put(b,41,101,109,99,108)
        put(b,42,108,120,107,119)
        tr,states=simulate(b,detect(b))
        self.assertEqual(states[20],'replaced');self.assertEqual(states[41],'filled')
        self.assertEqual(len(tr),1);self.assertEqual(tr.iloc[0].entry_price,109)

    def test_no_candidates_and_end_mark(self):
        b=bars();tr,_=simulate(b,detect(b));self.assertEqual(metrics(tr)['trades'],0)
        b=fixture(22);put(b,21,109,111,108,110)
        tr,_=simulate(b,detect(b));self.assertEqual(tr.iloc[0].reason,'end_of_data')
        self.assertGreaterEqual(metrics(tr)['path_equity_dd'],metrics(tr)['closed_dd'])


if __name__=='__main__':unittest.main()
