"""Availability and aggregation regressions for session VWAP research."""
import unittest

import numpy as np
import pandas as pd

from build_rtl_vwap_features import aggregate_chunk, build_features, label_trades


def bars(times, close, vwap=None):
    n = len(times)
    c = np.asarray(close, dtype=float)
    # Make cumulative PV/volume exactly the requested constant reference.
    p = c if vwap is None else np.full(n, vwap, dtype=float)
    return pd.DataFrame(dict(bar_time=pd.to_datetime(times), open=c, high=c+1,
                             low=c-1, close=c, volume=np.ones(n), pv_hlc3=p,
                             pv_close=p, switch_bar=False))


class VwapTests(unittest.TestCase):
    def test_minute_weighting_and_invalid_volume(self):
        raw = pd.DataFrame({'<DATE>':['2020.01.02']*2, '<TIME>':['01:00:00','01:01:00'],
            '<OPEN>':[10.,20.], '<HIGH>':[10.,20.], '<LOW>':[10.,20.],
            '<CLOSE>':[10.,20.], '<VOL>':[1,9], '<TICKVOL>':[1,9]})
        agg, _, _ = aggregate_chunk(raw)
        self.assertEqual(agg.pv_hlc3.iloc[0]/agg.volume.iloc[0], 19.)
        raw.loc[0, '<VOL>'] = 0
        with self.assertRaises(ValueError):
            aggregate_chunk(raw)

    def test_reset_over_weekend(self):
        b = bars(['2020-01-03 23:00','2020-01-06 01:00'], [10.,100.])
        f = build_features(b, 'full_hlc3')
        np.testing.assert_array_equal(f.vwap, [10.,100.])
        self.assertEqual(f.event.iloc[-1], 'unknown')
        self.assertEqual(f.churn.iloc[-1], 'unknown')

    def test_cash_does_not_carry_overnight(self):
        b = bars(['2020-01-02 16:30','2020-01-03 16:00','2020-01-03 16:30'], [10.,100.,200.])
        f = build_features(b, 'cash_hlc3')
        self.assertTrue(np.isnan(f.vwap.iloc[1]))
        self.assertEqual(f.vwap.iloc[2], 200.)
        self.assertEqual(f.anchor_age.iloc[2], 1)
        self.assertEqual(f.event.iloc[2], 'unknown')

    def test_crossings_require_seven_endpoints_and_zeros_do_not_count(self):
        t = pd.date_range('2020-01-02 01:00', periods=7, freq='30min')
        b = bars(t, [9,11,9,11,9,11,9], 10)
        f = build_features(b, 'full_hlc3')
        self.assertEqual(f.churn.iloc[5], 'unknown')
        self.assertEqual(f.crossings6.iloc[6], 6)
        self.assertEqual(f.churn.iloc[6], 'churn')
        b = bars(t, [9,10,11,10,9,10,11], 10)
        f = build_features(b, 'full_hlc3')
        self.assertEqual(f.crossings6.iloc[6], 0)
        self.assertEqual(f.event.iloc[2], 'reclaim')

    def test_no_future_price_or_volume_changes_earlier_features(self):
        t = pd.date_range('2020-01-02 01:00', periods=40, freq='30min')
        b = bars(t, np.arange(40.)+100)
        before = build_features(b, 'full_hlc3')
        b.loc[30:, ['open','high','low','close','pv_hlc3','pv_close','volume']] *= 1000
        after = build_features(b, 'full_hlc3')
        pd.testing.assert_frame_equal(before.iloc[:30], after.iloc[:30])

    def test_exact_availability_and_stale_session_rejection(self):
        b = bars(['2020-01-02 01:00','2020-01-02 01:30'], [10.,20.])
        f = build_features(b, 'full_hlc3')
        trades = pd.DataFrame({'submitted':pd.to_datetime(['2020-01-02 01:59:59','2020-01-02 02:00'], format='ISO8601'), 'ticket':[1,2]})
        joined = label_trades(trades, f)
        self.assertEqual(joined.vwap.iloc[0], 10.)
        self.assertEqual(joined.vwap.iloc[1], 15.)
        trades.loc[1, 'submitted'] = pd.Timestamp('2020-01-03 01:00')
        stale = label_trades(trades, f).iloc[1]
        self.assertTrue(np.isnan(stale.vwap))
        self.assertEqual(stale.side, 'unknown')
        self.assertEqual(stale.unknown_reason, 'session_reset')

    def test_extension_boundaries_and_zero_atr(self):
        t = pd.date_range('2020-01-02 01:00', periods=30, freq='30min')
        b = bars(t, np.full(30, 10.), 8.)
        f = build_features(b, 'full_hlc3')
        self.assertEqual(f.z.iloc[-1], 1.)
        self.assertEqual(f.distance.iloc[-1], 'above')
        b['pv_hlc3'] = 12.
        f = build_features(b, 'full_hlc3')
        self.assertEqual(f.z.iloc[-1], -1.)
        self.assertEqual(f.distance.iloc[-1], 'below')
        b['high'] = b['low'] = b.close
        f = build_features(b, 'full_hlc3')
        self.assertEqual(f.distance.iloc[-1], 'unknown')

    def test_full_session_volume_scaling_cancels(self):
        t = pd.date_range('2020-01-02 01:00', periods=30, freq='30min')
        b = bars(t, np.arange(30.)+100)
        before = build_features(b, 'full_hlc3')
        b[['volume','pv_hlc3','pv_close']] *= 2
        after = build_features(b, 'full_hlc3')
        np.testing.assert_allclose(before.vwap, after.vwap)


if __name__ == '__main__':
    unittest.main()
