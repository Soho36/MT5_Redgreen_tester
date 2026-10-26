"""Flatten/reopen rules of the weekly RTL simulator on small synthetic weeks."""
import unittest

import numpy as np

import rtl_weekly_engine as e

DAY0 = np.datetime64('2024-01-01', 'D')   # a Monday


def make(sessions):
    """sessions: {day offset: [(minute, o, h, l, c), ...]} -> bars dict."""
    rows = [(d, m, *ohlc) for d in sorted(sessions) for m, *ohlc in sessions[d]]
    days = [DAY0 + np.timedelta64(d, 'D') for d, *_ in rows]
    day = np.array([x.astype(np.int64) for x in days])
    date = np.array([int(str(x).replace('-', '')) for x in days])
    arr = np.array([r[2:] for r in rows], float)
    return {'date': date, 'day': day, 'minute': np.array([r[1] for r in rows]),
            'o': arr[:, 0], 'h': arr[:, 1], 'l': arr[:, 2], 'c': arr[:, 3]}


def flat_session(price, low=None, high=None):
    """A quiet session at `price`: 01:00, 12:00, 23:30 cutoff bar and 23:50."""
    low, high = price if low is None else low, price if high is None else high
    return [(60, price, price, price, price), (720, price, high, low, price),
            (1410, price, price, price, price), (1430, price, price, price, price)]


def red_week(sessions, start=0):
    """Week at `start`: opens 110, high 120, low 100, closes 105 (red)."""
    sessions[start] = [(60, 110, 120, 110, 115), (1410, 115, 115, 115, 115)]
    sessions[start + 4] = [(60, 115, 115, 100, 105), (1410, 105, 105, 105, 105)]


def run(sessions, mode='flat', **kw):
    b = make(sessions)
    return e.simulate_weekly(b, b['o'], b['h'], b['l'], b['c'], np.ones(len(b['o'])), mode=mode, **kw)


class FlattenReopen(unittest.TestCase):
    def test_fill_flatten_reopen_then_stop(self):
        s = {}
        red_week(s)
        s[7] = [(60, 110, 110, 110, 110), (600, 110, 125, 110, 124), (1410, 126, 126, 126, 126), (1440 - 5, 90, 90, 90, 90)]
        s[8] = [(60, 122, 122, 122, 122), (600, 122, 122, 99, 99), (1410, 99, 99, 99, 99)]
        trades, pieces, _ = run(s)
        self.assertEqual(len(trades), 1)
        t = trades.iloc[0]
        self.assertEqual((t.fill, t.sl, t.reason, t.pieces), (120, 100, 'sl', 2))
        self.assertEqual(list(pieces.reason), ['flatten', 'sl'])
        self.assertEqual(list(pieces.entry_price), [120, 122])        # reopened at the next open
        self.assertEqual(list(pieces.exit_price), [126, 100])         # 23:30 open; the 23:55 dip is ignored
        self.assertAlmostEqual(t.gross, ((126 - 120) + (100 - 122)) * e.POINT_VALUE)
        self.assertAlmostEqual(t.risk_dollars, 20 * e.POINT_VALUE)

    def test_gap_below_stop_while_flat_ends_trade_without_loss_piece(self):
        s = {}
        red_week(s)
        s[7] = [(60, 110, 121, 110, 121), (1410, 121, 121, 121, 121)]
        s[8] = flat_session(95)
        trades, pieces, counts = run(s)
        self.assertEqual(trades.iloc[0].reason, 'gap_stop')
        self.assertEqual(len(pieces), 1)
        self.assertEqual(counts['gap_stops'], 1)

    def test_breakout_while_flat_fills_at_next_open(self):
        s = {}
        red_week(s)
        s[7] = flat_session(110)
        s[8] = flat_session(130)
        trades, pieces, counts = run(s)
        t = trades.iloc[0]
        self.assertTrue(t.flat_fill)
        self.assertEqual((t.fill, counts['flat_fills']), (130, 1))
        self.assertAlmostEqual(t.risk_dollars, 30 * e.POINT_VALUE)

    def test_weekly_close_target_stops_reopening_and_blocks_that_week(self):
        s = {}
        red_week(s)
        s[7] = [(60, 110, 121, 110, 121), (1410, 121, 121, 121, 121)]
        s[11] = [(60, 150, 150, 150, 150), (1410, 150, 150, 150, 150)]      # week closes >= 120 + 20
        red_week(s, 14)                                                       # opens and closes lower: red
        trades, pieces, counts = run(s)
        self.assertEqual(trades.iloc[0].reason, 'target')
        self.assertEqual(trades.iloc[0].pieces, 2)
        self.assertFalse((pieces.entry_time >= DAY0 + np.timedelta64(14, 'D')).any())             # not reopened on day 14

    def test_rejected_when_week_opens_above_signal_high(self):
        s = {}
        red_week(s)
        s[7] = flat_session(125)
        trades, _, counts = run(s)
        self.assertEqual((len(trades), counts['rejected']), (0, 1))

    def test_green_week_keeps_pending_and_red_week_replaces_it(self):
        s = {}
        red_week(s)
        s[7] = [(60, 110, 110, 108, 109), (1410, 112, 112, 112, 112)]       # green week below 120
        s[14] = flat_session(110, high=121)                                  # old order (120) still live
        trades, _, _ = run(s)
        self.assertEqual((trades.iloc[0].requested, trades.iloc[0].fill), (120, 120))
        s[11] = [(60, 108, 108, 104, 104), (1410, 104, 104, 104, 104)]       # now week 7 is red: high 112
        trades, _, _ = run(s)
        self.assertEqual(trades.iloc[0].requested, 112)

    def test_hold_mode_keeps_position_overnight(self):
        s = {}
        red_week(s)
        s[7] = [(60, 110, 121, 110, 121), (1410, 121, 121, 121, 121), (1435, 101, 101, 99, 99)]
        s[8] = flat_session(122)
        trades, pieces, _ = run(s, mode='hold')
        self.assertEqual(trades.iloc[0].reason, 'sl')                       # the 23:55 dip counts when held
        self.assertAlmostEqual(trades.iloc[0].gross, -20 * e.POINT_VALUE)


class GreenSignal(unittest.TestCase):
    def test_gg_arms_on_a_green_week_and_a_red_week_keeps_its_order(self):
        s = {0: [(60, 100, 120, 95, 110), (1410, 110, 110, 110, 110)],     # green: high 120, low 95
             4: [(60, 110, 118, 110, 118), (1410, 118, 118, 118, 118)]}
        red_week(s, 7)                                                     # red week below 120
        s[14] = flat_session(110, high=121)
        self.assertEqual(len(run(s)[0]), 1)                                 # RTL: red week 7, high 120
        t = run(s, signal='green')[0].iloc[0]
        self.assertEqual((t.requested, t.sl, t.fill), (120, 95, 120))      # GG: week 0's order survived week 7
        self.assertEqual(t.signal_week, np.datetime64('2024-01-01'))


class MarketControls(unittest.TestCase):
    def green_week(self, s):
        s[0] = [(60, 100, 120, 95, 110), (1410, 110, 110, 110, 110)]
        s[4] = [(60, 110, 118, 110, 118), (1410, 118, 118, 118, 118)]

    def test_plain_long_buys_every_week_open_one_range_below(self):
        s = {}
        self.green_week(s)
        s[7] = flat_session(118)
        trades, pieces, _ = run(s, control='plain', spread=0.01)
        t = trades.iloc[0]
        self.assertAlmostEqual(t.fill, 118.01)
        self.assertAlmostEqual(t.sl, 118.01 - 25)
        self.assertEqual(pieces.iloc[0].entry_time, np.datetime64('2024-01-08T01:00:00'))

    def test_red_market_needs_a_red_week_and_an_open_above_its_low(self):
        s = {}
        self.green_week(s)
        s[7] = flat_session(118)
        self.assertEqual(len(run(s, control='signal_market')[0]), 0)
        s = {}
        red_week(s)
        s[7] = flat_session(106)
        t = run(s, control='signal_market')[0].iloc[0]
        self.assertEqual((t.fill, t.sl, t.requested), (106, 100, 106))
        s[7] = flat_session(99)
        trades, _, counts = run(s, control='signal_market')
        self.assertEqual((len(trades), counts['rejected']), (0, 1))

    def test_plain_long_stopped_next_minute_in_hold_mode(self):
        s = {}
        self.green_week(s)
        s[7] = [(60, 118, 118, 118, 118), (61, 118, 118, 90, 90)]
        trades, _, _ = run(s, mode='hold', fills='mt5', control='plain')
        self.assertEqual((trades.iloc[0].reason, trades.iloc[0].gross), ('sl', -25 * e.POINT_VALUE))


class Basis(unittest.TestCase):
    def test_roll_factor_removes_switch_gap(self):
        b = make({0: flat_session(100), 1: flat_session(110)})
        f = e.roll_factor(b, [int(str(DAY0 + np.timedelta64(1, 'D')).replace('-', ''))])
        adj = b['o'] * f
        self.assertAlmostEqual(adj[4], b['c'][3] * f[3])
        self.assertTrue(np.allclose(f[4:], 1) and np.allclose(f[:4], 1.1))

    def test_flat_pieces_are_raw_dollars_on_adjusted_levels(self):
        s = {}
        red_week(s)
        s[7] = [(60, 110, 125, 110, 124), (1410, 126, 126, 126, 126)]
        b = make(s)
        fac = np.full(len(b['o']), 0.5)
        _, pieces, _ = e.simulate_weekly(b, b['o'] * .5, b['h'] * .5, b['l'] * .5, b['c'] * .5, fac)
        self.assertAlmostEqual(pieces.gross.sum(), (126 - 120) * e.POINT_VALUE)


if __name__ == '__main__':
    unittest.main()
