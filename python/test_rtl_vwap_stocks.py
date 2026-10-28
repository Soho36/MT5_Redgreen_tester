"""Focused tests for the RTL VWAP stock test: splits, session, cutoff, gap fills, signal bars, cells."""
import unittest

import numpy as np
import pandas as pd

import analyze_rtl_vwap_cross as cx
import analyze_rtl_vwap_stocks as st
import build_rtl_vwap_features as vw
import rtl_stock_engine as engine


def minutes(rows):
    """rows: (timestamp, open, high, low, close); volume 100."""
    t, o, h, l, c = zip(*rows)
    return pd.DataFrame(dict(t=pd.to_datetime(t), open=o, high=h, low=l, close=c, volume=100.0))


def run(frame, fills, cutoffs=None):
    bars = engine.minute_arrays(frame.t, frame.open, frame.high, frame.low, frame.close)
    trades, _ = engine.simulate(bars, cutoffs or {}, st.CUTOFF, fills=fills, first_order_minute=0)
    return trades


class StockTests(unittest.TestCase):
    def test_split_adjustment_divides_prices_and_multiplies_volume(self):
        # NVDA split 4:1 on 2021-07-20 and 10:1 on 2024-06-10: both earlier prices go to today's basis.
        g = minutes([('2021-07-19 15:59', 800, 800, 800, 800), ('2021-07-20 04:00', 200, 200, 200, 200),
                     ('2024-06-10 04:00', 20, 20, 20, 20)])
        a = st.adjust_splits('NVDA', g)
        np.testing.assert_allclose(a.close, [20, 20, 20])
        np.testing.assert_allclose(a.volume, [4000, 1000, 100])
        day = minutes([('2020-01-02 04:00', 10, 11, 9, 10), ('2020-01-02 04:01', 20, 21, 19, 20)])
        scaled = day.assign(**{k: day[k]/4 for k in ('open', 'high', 'low', 'close')}, volume=day.volume*4)
        v1 = st.features_for(day)[1].vwap.iloc[-1]
        v2 = st.features_for(scaled)[1].vwap.iloc[-1]
        self.assertAlmostEqual(v1/4, v2)

    def test_session_window_and_early_close(self):
        g = pd.DataFrame(dict(t=pd.to_datetime(['2020-01-02 03:59', '2020-01-02 04:00', '2020-01-02 09:30', '2020-01-02 15:59',
                                                '2020-01-02 16:00', '2020-01-02 19:59', '2019-11-29 12:59', '2019-11-29 13:00']),
                              open=1., high=1., low=1., close=1., volume=1.))
        kept = st.session_minutes(g.sort_values('t'), st.SESSION_START)
        self.assertEqual(list(kept.t.dt.strftime('%Y-%m-%d %H:%M')),
                         ['2019-11-29 12:59', '2020-01-02 04:00', '2020-01-02 09:30', '2020-01-02 15:59'])
        rth = st.session_minutes(g.sort_values('t'), st.RTH_START)
        self.assertEqual(list(rth.t.dt.strftime('%H:%M')), ['12:59', '09:30', '15:59'])

    def test_gap_aware_entry_and_stop(self):
        g = minutes([('2020-01-02 04:00', 10, 10.5, 9.5, 9.6),     # red signal bar
                     ('2020-01-02 04:30', 10, 10.2, 9.9, 10.1),    # order placed at 10.5, stop 9.5
                     ('2020-01-02 04:31', 11, 11.2, 10.9, 11.1),   # opens above the level
                     ('2020-01-02 04:32', 9, 9.1, 8.9, 9.0)])      # opens below the stop
        gap, mt5 = run(g, 'gap'), run(g, 'mt5')
        self.assertEqual((gap.fill.iloc[0], gap.exit_price.iloc[0]), (11.0, 9.0))
        self.assertEqual((mt5.fill.iloc[0], mt5.exit_price.iloc[0]), (10.5, 9.5))
        self.assertEqual(gap.reason.iloc[0], 'sl')

    def test_cutoff_flattens_and_blocks_orders(self):
        for day, cut in (('2020-01-02', '15:30'), ('2019-11-29', '12:30')):
            hour = int(cut[:2])-1
            g = minutes([(f'{day} {hour:02d}:30', 10, 10.5, 9.5, 9.6), (f'{day} {hour+1:02d}:00', 10, 10.2, 9.9, 10.1),
                         (f'{day} {hour+1:02d}:01', 10.4, 10.6, 10.3, 10.5), (f'{day} {cut}', 10.4, 10.45, 10.35, 10.4),
                         (f'{day} {cut[:3]}31', 10.3, 11, 10, 10.1)])
            trades = run(g, 'gap', st.cutoffs())
            self.assertEqual(len(trades), 1)
            self.assertEqual(trades.reason.iloc[0], 'flatten')
            self.assertEqual(pd.Timestamp(trades.exit_time.iloc[0]).strftime('%H:%M'), cut)

    def test_signal_bars_match_labelled_bars(self):
        rng = np.random.default_rng(1)
        rows, price = [], 100.
        for day in ('2020-01-02', '2020-01-03'):
            for minute in range(240, 960):
                o = price; price = max(1., price+rng.normal(0, .3))
                rows.append((pd.Timestamp(day)+pd.Timedelta(minutes=minute), o, max(o, price)+.05, min(o, price)-.05, price))
        g = minutes(rows)
        trades = st.economics(run(g, 'gap'), 'TEST')
        labelled = st.label(trades, st.features_for(g)[1])
        self.assertGreater(len(labelled), 5)
        self.assertEqual(cx.signal_bar_check(labelled)['mismatches'], 0)

    def test_cells_and_drawdown_rows(self):
        np.testing.assert_allclose(st.maxdd_rows(np.array([[1., -2., 3., -4.], [1., 1., 1., 1.]])), [4., 0.])
        frame = pd.DataFrame(dict(symbol=['A']*20+['B']*20, era=(['2018-19']*10+['2020-26']*10)*2, ticket=np.arange(40),
                                  submitted=pd.date_range('2020-01-02', periods=40, freq='h'),
                                  initial_risk_dollars=np.r_[np.arange(20.), np.arange(20.)]))
        s, e, cells, month_cells, months, tertile = st.label_cells(frame, ['A', 'B'])
        self.assertEqual(len(np.unique(cells)), 40)
        self.assertEqual(sorted(np.unique(s*20+e*10)), [0, 10, 20, 30])
        self.assertTrue((pd.Series(month_cells).groupby(frame.symbol.to_numpy()).nunique() >= 1).all())


if __name__ == '__main__':
    unittest.main()
