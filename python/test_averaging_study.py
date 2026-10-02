"""Small hand-calculated accounting examples; MT5 runs test execution itself."""
import unittest

from analyze_averaging_study import summary


class AveragingAccountingTests(unittest.TestCase):
    def test_costs_and_reserved_risk_include_unfilled_orders(self):
        # $100 initial risk, $10 add risk: double stop, recovery, no add fill.
        rows = [dict(base_volume="1", add_volume=str(add), trade_profit=str(gross),
                     initial_risk_money="100", planned_add_risk="10", add_profit=str(add_profit))
                for gross, add, add_profit in [(-110, 1, -10), (290, 1, 190), (100, 0, 0)]]
        result = summary(rows)
        self.assertAlmostEqual(result["net"], 274.75)  # $280 less five contract commissions
        self.assertAlmostEqual(result["equal_risk_net"], 274.75 / 1.1)
        self.assertAlmostEqual(result["add_net"], 177.90)
        self.assertAlmostEqual(result["dd"], 112.10)
        self.assertEqual(result["fills"], 2)
        self.assertEqual(result["add_winners"], 1)

    def test_actual_gap_loss_is_not_clipped_to_planned_risk(self):
        row = dict(base_volume="1", add_volume="1", trade_profit="-150",
                   initial_risk_money="100", planned_add_risk="10", add_profit="-50")
        result = summary([row])
        self.assertAlmostEqual(result["net"], -152.10)
        self.assertAlmostEqual(result["add_net"], -51.05)
        self.assertAlmostEqual(result["avg_planned_r"], -152.10 / 110)


if __name__ == "__main__":
    unittest.main()
