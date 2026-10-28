"""Tests for the VWAP EA's label files (export_stock_mt5.label_frame, read by rtl_session_vwap.mqh)."""
import unittest

import numpy as np
import pandas as pd

import analyze_rtl_vwap_stocks as st
import export_stock_mt5 as ex


def two_sessions():
    """Two New York sessions of 1-minute bars, 04:00-11:59 (16 M30 bars each), a wavy decline with volume
    rising each minute, so late bars close far below their session's VWAP."""
    t = pd.concat([pd.Series(pd.date_range(f'2020-01-0{d} 04:00', periods=480, freq='min')) for d in (2, 3)],
                  ignore_index=True)
    i = np.arange(len(t))
    close = 100 + np.sin(i / 7.0) - i * 0.03
    return pd.DataFrame(dict(t=t, open=close + 0.05, high=close + 0.3, low=close - 0.3, close=close,
                             volume=100.0 + i))


class LabelFileTests(unittest.TestCase):
    def setUp(self):
        _, self.features = st.features_for(two_sessions())
        self.out, self.far = ex.label_frame(self.features)

    def test_columns_and_times_are_what_the_ea_reads(self):
        # The EA checks the header in this order and these time identities row by row.
        self.assertEqual(list(self.out.columns),
                         ['available_epoch', 'session_epoch', 'bar_epoch', 'close', 'vwap', 'a20', 'known'])
        first = pd.Timestamp('2020-01-02 04:00')
        self.assertEqual(self.out.bar_epoch.iloc[0], int((first - pd.Timestamp('1970-01-01')).total_seconds()))
        self.assertTrue((self.out.available_epoch == self.out.bar_epoch + 1800).all())
        self.assertTrue((np.diff(self.out.available_epoch) > 0).all())
        self.assertEqual(self.out.session_epoch.nunique(), 2)

    def test_known_needs_twenty_true_ranges_and_unknown_rows_carry_zeros(self):
        # 16 bars per session; A20 needs 21 bars, so only bars 21-32 (the second session's last 12) are known.
        self.assertEqual(len(self.out), 32)
        self.assertEqual(self.out.known.tolist(), [0] * 20 + [1] * 12)
        unknown = self.out.known.eq(0)
        self.assertTrue((self.out.loc[unknown, ['vwap', 'a20']] == 0).all().all())
        self.assertTrue((self.out.loc[~unknown, ['vwap', 'a20']] > 0).all().all())

    def test_gate_rule_equals_far_below_label(self):
        k = self.out.known.eq(1)
        gate = (self.out.close < self.out.vwap - self.out.a20) & k
        self.assertEqual(int(gate.sum()), self.far)
        self.assertTrue(gate.equals(self.features.distance.eq('far_below') & k))
        self.assertGreater(self.far, 0)


if __name__ == '__main__':
    unittest.main()
