import unittest
import pandas as pd
from abnormal_green_m1_wicks import shape_gate
from abnormal_green_m1 import detect, simulate
from test_abnormal_green_m1 import fixture, put


class WickGateTests(unittest.TestCase):
    def test_exact_eighty_percent_and_both_wicks(self):
        b = fixture()
        put(b, 20, 101, 110, 100, 109)
        s = detect(b)
        g = shape_gate(s, .8)
        self.assertEqual(g.iloc[0].eligibility, 'eligible')
        self.assertAlmostEqual(g.iloc[0].body_fraction, .8)
        self.assertAlmostEqual(g.iloc[0].upper_wick_fraction, .1)
        self.assertAlmostEqual(g.iloc[0].lower_wick_fraction, .1)
        self.assertEqual(shape_gate(s, .80001).iloc[0].eligibility, 'long_wicks')

    def test_no_mutation_or_readmission_of_excluded_signals(self):
        b = fixture()
        b['minute'][10:] += 2
        s = detect(b)
        before = s.copy(deep=True)
        g = shape_gate(s, .8)
        self.assertEqual(g.iloc[0].eligibility, 'nonconsecutive_reference')
        pd.testing.assert_frame_equal(s, before)

    def test_wickless_and_bad_threshold(self):
        b = fixture()
        put(b, 20, 100, 110, 100, 110)
        self.assertEqual(shape_gate(detect(b), 1).iloc[0].eligibility, 'eligible')
        with self.assertRaises(ValueError):
            shape_gate(detect(b), 1.1)

    def test_long_wick_signal_does_not_replace_qualifying_pending(self):
        b = fixture(45)
        for i in range(21, 45):
            put(b, i, 105, 105.5, 104.5, 105)
        put(b, 41, 101, 109, 99, 108)
        put(b, 42, 108, 121, 107, 120)
        signals = shape_gate(detect(b), .8)
        self.assertEqual(signals.loc[signals['index'].eq(41), 'eligibility'].iloc[0], 'long_wicks')
        tr, states = simulate(b, signals)
        self.assertEqual(states[20], 'filled')
        self.assertEqual(len(tr), 1)
        self.assertEqual(tr.iloc[0].signal_index, 20)
        self.assertEqual(tr.iloc[0].entry_price, 110)


if __name__ == '__main__':
    unittest.main()
