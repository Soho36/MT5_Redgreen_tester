"""Focused tests for causal activation, expiry and post-activation sell-stop fills."""
import unittest
import pandas as pd

from test_rtl_weekly_engine import make
from verify_rtl_failed_breakout_short import QuoteIndex, audit_event_rows, epoch

BASE = pd.Timestamp('2024-01-01 01:00:00')
WATCH = BASE + pd.Timedelta(minutes=30)


def quotes(rows):
    return QuoteIndex(make({0: [(60, 108, 110, 100, 102), *rows]}))


def events(terminal, when, bid, order=0, retcode=0):
    return pd.DataFrame([
        dict(time=WATCH, event='watch', signal_bar=BASE, watch_bar=WATCH,
             signal_high=110., signal_low=100., bid=105., retcode=0, order=0),
        dict(time=pd.Timestamp(when), event=terminal, signal_bar=BASE, watch_bar=WATCH,
             signal_high=110., signal_low=100., bid=bid, retcode=retcode, order=order)])


def orders(when=None, finish=None, state='filled'):
    if when is None:
        return pd.DataFrame(columns=['order', 'submitted', 'low', 'high', 'finished', 'state'])
    return pd.DataFrame([dict(order=7, submitted=pd.Timestamp(when), low=100., high=110.,
                              finished=pd.Timestamp(finish), state=state)])


class FailedBreakoutChronology(unittest.TestCase):
    def test_flat_activation_preserves_native_first_quote_second(self):
        bars = make({0: [(60, 108, 110, 100, 102), (90, 111, 111, 111, 111)]})
        for volume, second in [(1, 30), (6, 1)]:
            bars['tick_volume'] = [10, volume]
            result = QuoteIndex(bars).first_above(epoch(WATCH), 110)
            self.assertEqual(result, (epoch(WATCH) + second, 111))

    def test_three_quote_shadow_breaks_high_before_close(self):
        bars = make({0: [(60, 108, 110, 100, 102), (90, 110, 111, 110, 110)]})
        bars['tick_volume'] = [10, 3]
        self.assertEqual(QuoteIndex(bars).first_above(epoch(WATCH), 110),
                         (epoch(WATCH) + 30, 111))

    def test_touch_is_not_breakout(self):
        q = quotes([(90, 105, 110, 99, 104)])
        self.assertIsNone(q.first_above(epoch(WATCH), 110))

    def test_high_then_low_can_fill_same_minute(self):
        q = quotes([(90, 105, 111, 99, 101)])
        d = events('armed', '2024-01-01 01:30:20', 111, 7, 10008)
        result = audit_event_rows(d, q, orders('2024-01-01 01:30:20', '2024-01-01 01:30:40'))
        self.assertEqual(result['filled_orders'], 1)

    def test_low_before_high_cannot_retroactively_fill(self):
        q = quotes([(90, 105, 111, 99, 108), (91, 108, 109, 98, 107)])
        d = events('armed', '2024-01-01 01:30:40', 111, 7, 10008)
        result = audit_event_rows(d, q, orders('2024-01-01 01:30:40', '2024-01-01 01:31:40'))
        self.assertEqual(result['low_before_high_watches'], 1)
        with self.assertRaises(AssertionError):
            audit_event_rows(d, q, orders('2024-01-01 01:30:40', '2024-01-01 01:30:20'))

    def test_later_candle_high_does_not_arm_expired_watch(self):
        q = quotes([(90, 105, 109, 101, 108), (120, 108, 115, 99, 100)])
        d = events('expired', '2024-01-01 02:00:00', 108)
        result = audit_event_rows(d, q, orders())
        self.assertEqual(result['event_counts']['expired'], 1)
        d.loc[1, ['event', 'time', 'bid', 'retcode', 'order']] = [
            'armed', pd.Timestamp('2024-01-01 02:00:20'), 115, 10008, 7]
        with self.assertRaises(AssertionError):
            audit_event_rows(d, q, orders('2024-01-01 02:00:20', '2024-01-01 02:00:40'))

    def test_armed_pending_may_fill_in_later_candle(self):
        q = quotes([(90, 105, 111, 101, 108), (120, 108, 109, 99, 100)])
        d = events('armed', '2024-01-01 01:30:40', 111, 7, 10008)
        result = audit_event_rows(d, q, orders('2024-01-01 01:30:40', '2024-01-01 02:00:40'))
        self.assertEqual(result['filled_after_activation_candle'], 1)

    def test_gap_above_high_qualifies_at_first_quote(self):
        q = quotes([(90, 112, 113, 101, 108)])
        self.assertEqual(q.first_above(epoch(WATCH), 110), (epoch(WATCH), 112))

    def test_expiry_cannot_hide_earlier_high_break(self):
        q = quotes([(90, 105, 111, 101, 108), (120, 108, 109, 99, 100)])
        with self.assertRaises(AssertionError):
            audit_event_rows(events('expired', '2024-01-01 02:00:00', 108), q, orders())

    def test_stop_must_remain_at_original_signal_high(self):
        q = quotes([(90, 105, 111, 99, 101)])
        d = events('armed', '2024-01-01 01:30:20', 111, 7, 10008)
        actual = orders('2024-01-01 01:30:20', '2024-01-01 01:30:40')
        actual.loc[0, 'high'] = 111
        with self.assertRaises(AssertionError):
            audit_event_rows(d, q, actual)

    def test_repeated_activation_is_rejected(self):
        q = quotes([(90, 105, 111, 99, 101)])
        d = events('armed', '2024-01-01 01:30:20', 111, 7, 10008)
        d = pd.concat([d, d.iloc[[1]]], ignore_index=True)
        with self.assertRaises(AssertionError):
            audit_event_rows(d, q, orders('2024-01-01 01:30:20', '2024-01-01 01:30:40'))

    def test_first_break_cannot_be_delayed(self):
        q = quotes([(90, 105, 112, 101, 111), (91, 111, 113, 99, 100)])
        with self.assertRaises(AssertionError):
            audit_event_rows(events('armed', '2024-01-01 01:31:00', 111, 7, 10008), q,
                             orders('2024-01-01 01:31:00', '2024-01-01 01:31:40'))


if __name__ == '__main__':
    unittest.main()
