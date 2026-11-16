"""Order, stop, target and flatten rules of the mirrored-RTL sell-limit replay."""
import unittest

import numpy as np
import pandas as pd

import rtl_weekly_engine as e
from rtl_sell_limit_fade import economics, simulate_fade

DAY = int(np.datetime64('2020-01-02', 'D').astype(np.int64))


def bars(rows):
    """Minute rows (HH:MM, open, high, low, close) of one session."""
    out = dict(date=np.full(len(rows), 20200102), day=np.full(len(rows), DAY),
               minute=np.array([int(r[0][:2]) * 60 + int(r[0][3:]) for r in rows]))
    for j, key in enumerate('ohlc', start=1):
        out[key] = np.array([r[j] for r in rows], float)
    return out


def at(text):
    return pd.Timestamp('2020-01-02 ' + text)


# A red 10:00 candle: open 100, high 101, low 99, close 99.5. Order placed at 10:30, filled at 10:31.
RED = [('10:00', 100, 101, 99.5, 100), ('10:29', 100, 100, 99, 99.5)]
FILL = [('10:30', 99.5, 99.75, 99.5, 99.75), ('10:31', 100, 101.5, 100, 101.25)]


class SellLimitFadeTests(unittest.TestCase):
    def test_fills_at_the_red_high_and_stops_one_range_above(self):
        trades, rejected = simulate_fade(bars(RED + FILL + [('10:32', 101.25, 103.25, 101.25, 103)]))
        self.assertEqual((len(trades), rejected), (1, 0))
        t = trades.iloc[0]
        self.assertEqual((t.requested, t.fill, t.sl), (101, 101, 103))
        self.assertEqual(pd.Timestamp(t.submitted), at('10:30:00'))
        self.assertEqual(pd.Timestamp(t.entry_time), at('10:31:40'))     # rising minute: the high is the third quote
        self.assertEqual((t.reason, t.exit_price), ('sl', 103))
        self.assertEqual(pd.Timestamp(t.exit_time), at('10:32:40'))
        self.assertEqual(economics(trades).gross.iloc[0], -4.0)          # one range of 2 points on one MNQ

    def test_same_entry_as_the_rtl_buy_stop(self):
        data = bars(RED + FILL + [('10:32', 101.25, 103.25, 101.25, 103)])
        long, _ = e.simulate_m30_ea(data)
        short, _ = simulate_fade(data)
        self.assertEqual((long.entry_time.iloc[0], long.fill.iloc[0]), (short.entry_time.iloc[0], short.fill.iloc[0]))
        self.assertEqual(long.sl.iloc[0], 99)                            # RTL's stop: the low, one range below

    def test_bar_close_exit_needs_a_close_at_or_below_the_low(self):
        touched = RED + FILL + [('10:40', 101, 101, 98.5, 100), ('11:00', 100, 100, 99.75, 99.75)]
        trades, _ = simulate_fade(bars(touched))
        self.assertEqual(trades.reason.iloc[0], 'end_of_data')           # the low was touched, the bar closed above it
        closed = RED + FILL + [('10:40', 101, 101, 98.5, 98.75), ('11:00', 98.5, 98.5, 98.25, 98.25)]
        t = simulate_fade(bars(closed))[0].iloc[0]
        self.assertEqual((t.reason, t.exit_price), ('target', 98.75))    # next bar's open 98.5 plus one tick
        self.assertEqual(pd.Timestamp(t.exit_time), at('11:00:00'))

    def test_resting_take_profit_fills_at_the_low(self):
        touched = RED + FILL + [('10:40', 101, 101, 98.5, 100), ('11:00', 100, 100, 99.75, 99.75)]
        t = simulate_fade(bars(touched), resting_tp=True)[0].iloc[0]
        self.assertEqual((t.tp, t.reason, t.exit_price), (99, 'tp', 99))
        self.assertEqual(pd.Timestamp(t.exit_time), at('10:40:40'))      # falling minute: the low is the third quote
        late = simulate_fade(bars(touched), resting_tp=True, tp_spread=0.5)[0].iloc[0]
        self.assertEqual(late.reason, 'tp')                              # 98.5 + 0.5 still reaches 99
        none = simulate_fade(bars(touched), resting_tp=True, tp_spread=0.75)[0].iloc[0]
        self.assertEqual(none.reason, 'end_of_data')

    def test_order_at_the_market_is_skipped_or_filled_at_once(self):
        for opening in (101, 101.25):
            data = bars(RED + [('10:30', opening, 102, opening, 102)])
            trades, skipped = simulate_fade(data)
            self.assertEqual((len(trades), skipped), (0, 1))             # the protocol: no order, as for RTL
            t = simulate_fade(data, at_market=True)[0].iloc[0]           # MT5's own handling of the sell limit
            self.assertEqual((t.requested, t.fill, t.sl), (101, opening, 103))
            self.assertEqual(pd.Timestamp(t.entry_time), at('10:30:00'))

    def test_cautious_fill_needs_price_one_tick_through_the_limit(self):
        touch = bars(RED + [('10:30', 99.5, 101, 99.5, 100.5)])
        self.assertEqual(len(simulate_fade(touch)[0]), 1)                # MT5: a touch of 101 fills
        self.assertEqual(len(simulate_fade(touch, through=0.25)[0]), 0)
        traded = simulate_fade(bars(RED + [('10:30', 99.5, 101.25, 99.5, 100.5)]), through=0.25)[0].iloc[0]
        self.assertEqual((traded.fill, traded.sl), (101, 103))           # still filled at the limit price

    def test_new_red_candle_replaces_the_order_and_green_leaves_it(self):
        second_red = [('10:30', 99.5, 100.5, 98.5, 99), ('11:00', 99, 100.75, 99, 100.75)]
        t = simulate_fade(bars(RED + second_red))[0].iloc[0]
        self.assertEqual((t.requested, t.sl), (100.5, 102.5))            # the 10:30 candle's high and its 2-point range
        green = [('10:30', 99.5, 100.5, 99.5, 100.25), ('11:00', 100.25, 101.25, 100.25, 101.25)]
        t = simulate_fade(bars(RED + green))[0].iloc[0]
        self.assertEqual((t.requested, t.sl), (101, 103))                # the 10:00 order was still resting
        self.assertEqual(pd.Timestamp(t.submitted), at('10:30:00'))

    def test_session_flatten_buys_back_one_tick_above_the_open(self):
        late = [('22:30', 100, 101, 99.5, 100), ('22:59', 100, 100, 99, 99.5),
                ('23:00', 99.5, 99.75, 99.5, 99.75), ('23:01', 100, 101.5, 100, 101.25),
                ('23:30', 101.5, 101.5, 101.5, 101.5)]
        t = simulate_fade(bars(late))[0].iloc[0]
        self.assertEqual((t.reason, t.exit_price), ('flatten', 101.75))
        self.assertEqual(pd.Timestamp(t.exit_time), at('23:30:00'))


if __name__ == '__main__':
    unittest.main()
