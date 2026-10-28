"""Hybrid exit behavior on synthetic minute paths; initial risk is 10 points."""
import unittest
import numpy as np
import rtl_weekly_engine as e
from test_rtl_weekly_engine import make


def run(rows, tp=2.0, **kw):
    # Completed red 01:00 candle: buy stop 110, stop 100, signal close 102.
    bars = make({0: [(60, 108, 110, 100, 102), *rows]})
    return e.simulate_m30_ea(bars, intrabar_rr=tp, **kw)[0]


class IntrabarTakeProfit(unittest.TestCase):
    def test_pending_fill_tick_does_not_execute_its_new_tp(self):
        # MT5 processes attached exits before pending entries on each quote.
        t = run([(90, 105, 131, 104, 106), (91, 106, 108, 99, 101)]).iloc[0]
        self.assertEqual((t.exit_price, t.reason), (100, 'sl'))

    def test_entry_minute_tp_can_execute_on_next_quote(self):
        t = run([(90, 105, 135, 104, 131)]).iloc[0]
        self.assertEqual((t.fill, t.sl, t.exit_price, t.reason), (110, 100, 130, 'intrabar_tp'))
        self.assertEqual(str(t.exit_time), '2024-01-01 01:30:59')

    def test_later_minute_wick_is_not_skipped_by_fast_path(self):
        t = run([(90, 105, 112, 104, 111), (91, 111, 135, 105, 106)]).iloc[0]
        self.assertEqual((t.exit_price, t.reason), (130, 'intrabar_tp'))
        self.assertEqual(str(t.exit_time), '2024-01-01 01:31:20')

    def test_close_1r_still_exits_before_2r_is_reached(self):
        t = run([(90, 105, 122, 104, 121), (120, 119, 129, 118, 125)]).iloc[0]
        self.assertEqual((t.exit_price, t.reason), (119, 'target'))

    def test_disabled_keeps_wick_open_and_then_stops(self):
        t = run([(90, 105, 135, 104, 106), (91, 106, 108, 99, 101)], tp=None).iloc[0]
        self.assertEqual((t.exit_price, t.reason), (100, 'sl'))

    def test_pre_entry_low_cannot_stop_later_fill(self):
        t = run([(90, 105, 131, 99, 130)]).iloc[0]  # rising minute: low first, then entry/TP
        self.assertEqual((t.exit_price, t.reason), (130, 'intrabar_tp'))

    def test_stop_precedes_later_target_in_falling_minute_path(self):
        t = run([(90, 105, 112, 104, 111), (91, 111, 115, 99, 112), (92, 112, 135, 111, 130)]).iloc[0]
        self.assertEqual((t.exit_price, t.reason), (100, 'sl'))

    def test_flatten_still_runs_before_candle_close_exit(self):
        t = run([(90, 105, 112, 104, 111), (1410, 115, 125, 114, 120)]).iloc[0]
        self.assertEqual((t.exit_price, t.reason), (115, 'flatten'))

    def test_broker_target_at_bar_open_precedes_ea_callback(self):
        t = run([(90, 105, 122, 104, 121), (120, 134, 135, 133, 134)]).iloc[0]
        self.assertEqual((t.exit_price, t.reason), (130, 'intrabar_tp'))

    def test_fractional_target_is_configurable(self):
        t = run([(90, 105, 116, 104, 115)], tp=0.5).iloc[0]
        self.assertEqual((t.exit_price, t.reason), (115, 'intrabar_tp'))

    def test_invalid_targets_rejected(self):
        for target in (0, -1, np.nan, np.inf):
            with self.subTest(target=target), self.assertRaises(ValueError):
                run([], tp=target)


if __name__ == '__main__':
    unittest.main()
