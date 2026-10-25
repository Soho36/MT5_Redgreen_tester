"""Focused tests for the weekly signal gate."""
import unittest

import numpy as np
import pandas as pd

from analyze_rtl_weekly_gate import (gate_off, last_completed_bar, roll_adjust, shift_nets, signals,
                                     weekly_bars)


def m30(days, bars_per_day=2, start='2018-01-01'):
    """Synthetic M30 frame from per-bar (open, high, low, close) tuples, two bars per weekday."""
    sessions = pd.bdate_range(start, periods=len(days)//bars_per_day)
    times = [d+pd.Timedelta(hours=1, minutes=30*k) for d in sessions for k in range(bars_per_day)]
    frame = pd.DataFrame(days, columns=['open', 'high', 'low', 'close'])
    frame.insert(0, 'bar_time', pd.to_datetime(times))
    return frame


def week(open_, close, high=None, low=None):
    """Ten bars (one week): drifts from open to close inside [low, high]."""
    path = np.linspace(open_, close, 11)
    bars = [(path[i], max(path[i], path[i+1]), min(path[i], path[i+1]), path[i+1]) for i in range(10)]
    if high is not None:
        o, h, lo, c = bars[4]
        bars[4] = (o, high, lo, c)
    if low is not None:
        o, h, lo, c = bars[6]
        bars[6] = (o, h, low, c)
    return bars


class WeeklyTests(unittest.TestCase):
    def test_weeks_and_colours(self):
        frame = m30(week(100, 110) + week(110, 105) + week(105, 105))
        weeks = weekly_bars(frame)
        self.assertEqual(list(weeks.colour), ['green', 'red', 'doji'])
        self.assertEqual(list(weeks.first_bar), [0, 10, 20])
        self.assertEqual(weeks.high.iloc[0], 110)

    def test_touch_uses_first_crossing_bar(self):
        frame = m30(week(100, 110) + week(110, 112, low=99))
        events = signals(frame, weekly_bars(frame), 'touch')
        self.assertEqual(events, [(16, 'sell', 1)])

    def test_week_close_and_close_confirmed_timing(self):
        frame = m30(week(100, 110) + week(110, 112, low=99) + week(112, 98))
        weeks = weekly_bars(frame)
        self.assertEqual(signals(frame, weeks, 'week_close')[0], (19, 'sell', 1))
        self.assertEqual(signals(frame, weeks, 'close_confirmed'), [(29, 'sell', 2)])

    def test_doji_week_gives_no_signal(self):
        frame = m30(week(100, 100, high=104, low=96) + week(100, 90, low=80))
        self.assertEqual(signals(frame, weekly_bars(frame), 'touch'), [])

    def test_gate_states_ignore_repeated_signals(self):
        off = gate_off([(3, 'sell', 1), (6, 'sell', 2), (9, 'buy', 3), (12, 'buy', 4)], 15)
        self.assertEqual(list(np.flatnonzero(off)), [3, 4, 5, 6, 7, 8])

    def test_future_prices_cannot_change_past_states(self):
        rng = np.random.default_rng(17)
        closes = 100*np.exp(np.cumsum(rng.normal(0, .004, 400)))
        opens = np.r_[100, closes[:-1]]
        noise = np.abs(rng.normal(0, .002, 400))*closes
        bars = list(zip(opens, np.maximum(opens, closes)+noise, np.minimum(opens, closes)-noise, closes))
        frame = m30(bars)
        weeks = weekly_bars(frame)
        base = gate_off(signals(frame, weeks, 'touch'), len(frame))
        for k in (95, 201, 333):
            changed = frame.copy()
            changed.loc[k+1:, ['open', 'high', 'low', 'close']] *= 1.07
            other = gate_off(signals(changed, weekly_bars(changed), 'touch'), len(frame))
            np.testing.assert_array_equal(other[:k+1], base[:k+1])


class MechanicsTests(unittest.TestCase):
    def test_roll_adjustment_removes_only_the_switch_move(self):
        frame = m30(week(100, 110) + week(112, 120))
        frame.loc[10:, ['open', 'high', 'low', 'close']] += 2
        adjusted = roll_adjust(frame, [frame.bar_time[10].normalize()])
        self.assertAlmostEqual(adjusted.open[10], adjusted.close[9])
        raw_returns = frame.close.pct_change().drop(10)
        np.testing.assert_allclose(adjusted.close.pct_change().drop(10).iloc[1:], raw_returns.iloc[1:])

    def test_last_completed_bar_at_and_after_close(self):
        times = pd.to_datetime(['2018-01-02 01:00', '2018-01-02 01:30', '2018-01-02 02:00'])
        submitted = pd.to_datetime(['2018-01-02 02:00:00', '2018-01-02 02:00:01', '2018-01-02 01:59:59'])
        self.assertEqual(list(last_completed_bar(pd.Series(times), submitted)), [1, 1, 0])

    def test_shift_nets_match_direct_sums(self):
        rng = np.random.default_rng(23)
        pnl = rng.normal(0, 10, 37)
        off = rng.random(37) < .3
        nets = shift_nets(pnl, off)
        for k in range(37):
            self.assertAlmostEqual(nets[k], (pnl*~np.roll(off, k)).sum())


if __name__ == '__main__':
    unittest.main()
