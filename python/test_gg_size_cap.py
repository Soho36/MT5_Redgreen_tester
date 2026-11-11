"""Size-cap flag boundaries and the simulator's rejected-signal and closed-window behaviour."""
import unittest
import numpy as np
import pandas as pd
from analyze_gg_large_candle import features
from analyze_gg_size_cap import capped
from test_rtl_weekly_engine import make
import rtl_weekly_engine as e


def frame(widths, start="2024-01-01 01:00"):
    return pd.DataFrame(dict(bar_time=pd.date_range(start, periods=len(widths), freq="30min"),
                             open=100., high=100 + np.array(widths), low=100., close=101.))


FIRST = [(60, 102, 110, 100, 108), (90, 105, 117, 104, 116), (120, 116, 117, 115, 116)]
PENDING = [(60, 102, 110, 100, 108), (90, 108, 109, 107, 108.5), (120, 108.5, 108.8, 108.2, 108.6),
           (121, 108.6, 111, 108.5, 110.5)]


class SizeCap(unittest.TestCase):
    def test_threshold_is_lower_bound_and_off_is_empty(self):
        f = features(frame([4] * 5 + [19.5, 20, 30]))
        self.assertEqual(capped(f, 5).iloc[-3:].tolist(), [False, True, True])
        self.assertFalse(capped(f, 0).any())

    def test_five_prior_bars_and_session_reset(self):
        raw = pd.concat([frame([2] * 6), frame([20, 20, 20, 20, 200, 200], "2024-01-02 01:00")], ignore_index=True)
        flags = capped(features(raw), 5)
        self.assertFalse(flags.iloc[-2])   # only four earlier bars in the new session
        self.assertTrue(flags.iloc[-1])    # five earlier bars, median 20

    def test_zero_median_never_caps(self):
        self.assertFalse(capped(features(frame([0] * 5 + [10])), 5).iloc[-1])

    def test_invalid_ratio_rejected(self):
        f = features(frame([2] * 6))
        for ratio in (-1, 0.5, 1, np.nan, np.inf):
            with self.subTest(ratio=ratio), self.assertRaises(ValueError):
                capped(f, ratio)

    def test_capped_signal_places_no_order(self):
        bars = make({0: FIRST})
        slot = int(bars["day"][0] * 48 + 2)
        base = e.simulate_m30_ea(bars, signal="green")[0]
        cap = e.simulate_m30_ea(bars, signal="green", signal_skips={slot})[0]
        self.assertEqual((base.iloc[0].requested, str(base.iloc[0].submitted)), (110, "2024-01-01 01:30:00"))
        self.assertEqual(len(cap), 1)
        self.assertEqual((cap.iloc[0].requested, cap.iloc[0].sl, str(cap.iloc[0].submitted)),
                         (117, 104, "2024-01-01 02:00:00"))

    def test_capped_signal_cancels_the_pending_order(self):
        bars = make({0: PENDING})
        slot = int(bars["day"][0] * 48 + 3)
        base = e.simulate_m30_ea(bars, signal="green")[0]
        self.assertEqual((len(base), base.iloc[0].requested), (1, 109))
        self.assertEqual(len(e.simulate_m30_ea(bars, signal="green", signal_skips={slot})[0]), 0)

    def test_closed_window_cancels_and_places_nothing(self):
        bars = make({0: PENDING})
        self.assertEqual(len(e.simulate_m30_ea(bars, signal="green", blocked_minutes=(120,))[0]), 0)
        late = e.simulate_m30_ea(make({0: FIRST}), signal="green", blocked_minutes=(90,))[0]
        self.assertEqual((len(late), late.iloc[0].requested), (1, 117))

    def test_defaults_leave_the_engine_unchanged(self):
        bars = make({0: FIRST})
        a = e.simulate_m30_ea(bars, signal="green")[0]
        b = e.simulate_m30_ea(bars, signal="green", signal_skips=set(), blocked_minutes=())[0]
        pd.testing.assert_frame_equal(a, b)


if __name__ == "__main__":
    unittest.main()
