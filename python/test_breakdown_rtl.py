import unittest

import numpy as np

from analyze_breakdown_rtl import assign_groups


class GroupTest(unittest.TestCase):
    def setUp(self):
        self.contract = np.ones(40, int)

    def groups(self, break_at, s, contract=None):
        breaks = np.zeros(40, bool)
        breaks[list(break_at)] = True
        return assign_groups(breaks, self.contract if contract is None else contract, s).tolist()

    def test_signal_bar_itself_breaks_is_a(self):
        self.assertEqual(self.groups([20], [20]), ["A"])
        self.assertEqual(self.groups([15, 20], [20]), ["A"])  # A wins over an earlier break

    def test_window_edges(self):
        self.assertEqual(self.groups([19], [20]), ["B"])      # 1 bar before
        self.assertEqual(self.groups([10], [20]), ["B"])      # 10 bars before
        self.assertEqual(self.groups([9], [20]), ["other"])   # 11 bars before
        self.assertEqual(self.groups([21], [20]), ["other"])  # after the signal

    def test_same_contract_only(self):
        contract = np.r_[np.ones(18, int), np.full(22, 2)]
        self.assertEqual(self.groups([17], [20], contract), ["other"])  # break in the previous contract
        self.assertEqual(self.groups([18], [20], contract), ["B"])

    def test_start_of_history(self):
        self.assertEqual(self.groups([0], [3]), ["B"])
        self.assertEqual(self.groups([], [0]), ["other"])


if __name__ == "__main__":
    unittest.main()
