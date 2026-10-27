"""Focused tests for the cross-instrument VWAP test helpers."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_rtl_vwap_cross as cross
from build_rtl_vwap_features import build_features, label_trades


def trades(risk, submitted=None, era=None):
    n = len(risk)
    submitted = pd.date_range('2020-01-02 02:00', periods=n, freq='30min') if submitted is None else pd.to_datetime(submitted)
    return pd.DataFrame(dict(ticket=np.arange(n), submitted=submitted, initial_risk_dollars=np.asarray(risk, float),
                             era=era if era is not None else ['e']*n))


class CrossTests(unittest.TestCase):
    def test_equal_count_groups_break_ties_by_time(self):
        frame = trades([5, 5, 5, 5, 1, 9, 9])
        groups = cross.rank_groups(frame, 3)
        self.assertEqual(sorted(np.bincount(groups)), [2, 2, 3])
        self.assertEqual(groups[4], 0)
        self.assertLessEqual(groups[0], groups[3])

    def test_contrast_weights_far_counts_and_skips_one_sided_cells(self):
        r = np.array([-1., -1., 1., 0., 0., 2., 5.])
        far = np.array([True, True, False, True, False, False, True])
        cells = np.array([0, 0, 0, 1, 1, 1, 2])
        estimate, table = cross.contrast(r, far, cells)
        self.assertAlmostEqual(estimate, (2*(-1-1)+1*(0-1))/3)
        self.assertFalse(table.set_index('cell').loc[2, 'used'])

    def test_bootstrap_of_identical_weeks_returns_the_estimate(self):
        r = np.tile([-1., 1., 0., 2.], 8)
        far = np.tile([True, False, True, False], 8)
        cells = np.tile([0, 0, 1, 1], 8)
        weeks = np.repeat(np.arange(8), 4)
        values, left_out, starts = cross.contrast_bootstrap(r, far, cells, weeks, 8, np.random.default_rng(1))
        estimate, _ = cross.contrast(r, far, cells)
        np.testing.assert_allclose(values, estimate)
        self.assertEqual(left_out.max(), 0)
        self.assertEqual(starts.shape, (cross.BOOT_DRAWS, 2))

    def test_cell_placebo_counts_shortfall_and_never_far(self):
        far = np.array([True, False, False, True, True, False, False, False])
        cells = np.array([0, 0, 0, 1, 1, 1, 2, 2])
        masks, shortfall = cross.cell_placebo(far, cells, np.random.default_rng(2))
        self.assertEqual(shortfall, 1)
        self.assertFalse((masks & far).any())
        np.testing.assert_array_equal(masks[:, cells == 0].sum(axis=1), 1)
        np.testing.assert_array_equal(masks[:, cells == 1].sum(axis=1), 1)
        np.testing.assert_array_equal(masks[:, cells == 2].sum(axis=1), 0)

    def test_rolled_placebo_rotates_each_month(self):
        far = np.array([True, True, False, False, False, True, False])
        months = np.array(['2020-01']*4+['2020-02']*3)
        masks, offsets = cross.rolled_placebo(far, months, np.random.default_rng(3))
        for d in range(20):
            np.testing.assert_array_equal(masks[d, :4], np.roll(far[:4], offsets[d, 0]))
            np.testing.assert_array_equal(masks[d, 4:], np.roll(far[4:], offsets[d, 1]))
        np.testing.assert_array_equal(masks.sum(axis=1), far.sum())

    def test_largest_risk_per_era(self):
        frame = trades([1, 9, 5, 7, 2, 8], era=['a', 'a', 'a', 'b', 'b', 'b'])
        far = np.array([True, False, False, True, True, False])
        np.testing.assert_array_equal(cross.largest_risk(frame, far), [False, True, False, True, False, True])

    def test_period_stats_match_direct_computation(self):
        pnl, risk = np.array([1., -2., 3., -4.]), np.array([1., 2., 3., 4.])
        day = np.array([0, 0, 1, 2])
        masks = np.array([[False, True, False, False]])
        stats = cross.period_stats(masks, pnl, risk, np.ones(4, bool), day, 3)[0]
        np.testing.assert_allclose(stats, [0., 4., 0.8])

    def test_signal_bar_check_rejects_wrong_bar(self):
        frame = pd.DataFrame(dict(ticket=[1, 2], submitted=pd.to_datetime(['2020-01-02 02:00']*2),
                                  session=pd.to_datetime(['2020-01-02']*2), requested_price=[10., 10.],
                                  original_sl=[8., 8.], high=[10., 10.], low=[8., 8.], open=[9.5, 9.5], close=[9., 9.]))
        self.assertEqual(cross.signal_bar_check(frame)['mismatches'], 0)
        frame.loc[1, 'close'] = 9.6
        with self.assertRaises(AssertionError):
            cross.signal_bar_check(frame)

    def test_session_reset_and_availability_boundary(self):
        t = pd.to_datetime(['2020-01-02 01:00', '2020-01-02 01:30'])
        bars = pd.DataFrame(dict(bar_time=t, open=[10., 20.], high=[11., 21.], low=[9., 19.], close=[10., 20.],
                                 volume=[1., 1.], pv_hlc3=[10., 20.], pv_close=[10., 20.], switch_bar=False))
        features = build_features(bars, 'full_hlc3')
        frame = pd.DataFrame(dict(submitted=pd.to_datetime(['2020-01-02 01:59:59', '2020-01-02 02:00:00', '2020-01-03 01:00:00']),
                                  ticket=[1, 2, 3]))
        joined = label_trades(frame, features)
        self.assertEqual(list(joined.bar_time), [t[0], t[1], t[1]])
        self.assertEqual(joined.unknown_reason.iloc[2], 'session_reset')
        nq = features[['available_at', 'feature_session', 'z', 'distance']].assign(z=[-2., -2.], distance=['far_below']*2)
        labels = cross.comovement_labels(frame, nq)
        self.assertEqual(list(labels), ['far_below', 'far_below', 'unknown'])

    def test_cross_date_needs_an_early_session_end(self):
        bars = pd.DataFrame(dict(bar_time=pd.to_datetime(['2020-06-30 17:00', '2020-07-01 03:00']),
                                 first_minute=pd.to_datetime(['2020-06-30 17:00', '2020-07-01 03:00']),
                                 last_minute=pd.to_datetime(['2020-06-30 17:10', '2020-07-01 03:29'])))
        report = pd.DataFrame(dict(ticket=[1], submitted=pd.to_datetime(['2020-06-30 17:00']),
                                   entry_time=pd.to_datetime(['2020-06-30 17:05:40']),
                                   exit_time=pd.to_datetime(['2020-07-01 03:00:00'])))
        self.assertTrue(cross.explain_cross_date(report, bars)[0]['explained'])
        bars.loc[0, 'last_minute'] = pd.Timestamp('2020-06-30 23:59')
        with self.assertRaises(AssertionError):
            cross.explain_cross_date(report, bars)

    def test_report_parser_pairs_orders_and_deals(self):
        row = lambda *cells: '<tr>'+''.join(f'<td>{c}</td>' for c in cells)+'</tr>\n'
        text = ('<div>Orders</div>\n'
                + row('2020.01.02 02:00:00', 5, 'SYM', 'buy stop', '1 / 1', '10.5', '9.5', '', '2020.01.02 02:10:00', 'filled', '')
                + row('2020.01.02 02:30:00', 6, 'SYM', 'sell', '1 / 1', '', '', '', '2020.01.02 02:30:00', 'filled', '')
                + '<div>Deals</div>\n'
                + row('2020.01.02 02:10:00', 2, 'SYM', 'buy', 'in', 1, '10.5', 5, 0, 0, 0, 100000, '')
                + row('2020.01.02 02:30:00', 3, 'SYM', 'sell', 'out', 1, '11.25', 6, 0, 0, '1.50', 100001.5, 'exit'))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'report.htm'
            path.write_text(text.replace('<div>Orders</div>', '<td>>Orders<</td>').replace('<div>Deals</div>', '<td>>Deals<</td>'),
                            encoding='utf-16')
            parsed = cross.parse_report(path, 'SYM')
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed.ticket.iloc[0], 5)
        self.assertEqual(parsed.trade_profit.iloc[0], 1.5)
        self.assertEqual(parsed.requested_price.iloc[0], 10.5)


if __name__ == '__main__':
    unittest.main()
