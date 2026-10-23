"""Boundary and causality tests for the frozen RTL regime study.

Run: .\\venv\\Scripts\\python.exe -m unittest discover -s python -p test_rtl_market_regimes.py -v
Synthetic paths test information boundaries; independent audits test ledger errors.
"""
from __future__ import annotations

import math
import unittest

import numpy as np
import pandas as pd

from analyze_rtl_market_regimes import build_features
from verify_rtl_market_regimes import (
    CAUSAL_COLUMNS, checked_ledger, full_year_negative_gate,
    independent_metrics, linear_percentile, reference_labels,
)


def prices(count=620, seed=1985):
    rng = np.random.default_rng(seed)
    returns = rng.normal(.0003, .008, count)
    return pd.Series(100 * np.exp(np.cumsum(returns)),
                     index=pd.bdate_range("2014-01-01", periods=count), name="close")


class FeatureCausalityTests(unittest.TestCase):
    def assert_matches_independent(self, closes, switches=()):
        production = build_features(closes, switches)
        independent = reference_labels(closes, switches)
        for column in ("trend", "group", "group_p70", "group_p80", "group_roll_robust"):
            pd.testing.assert_series_equal(production[column], independent[column], check_names=False, check_freq=False)
        for column in ("previous_close", "sma50", "sma200", "volatility_prior",
                       "volatility_threshold_p70", "volatility_threshold_p75", "volatility_threshold_p80",
                       "volatility_robust_prior", "volatility_robust_threshold"):
            np.testing.assert_allclose(production[column], independent[column], rtol=1e-10, atol=1e-12,
                                       equal_nan=True, err_msg=column)
        return production

    def test_random_roll_path_matches_literal_past_arrays(self):
        closes = prices()
        switches = closes.index[[80, 140, 201, 265, 331, 399, 472, 529]]
        self.assert_matches_independent(closes, switches)

    def test_current_and_future_prices_cannot_change_decision_labels(self):
        closes = prices(520)
        original = build_features(closes)
        for cut in (200, 272, 273, 350, 519):
            changed = closes.copy()
            changed.iloc[cut:] *= np.linspace(1.5, 4.5, len(changed) - cut)
            altered = build_features(changed)
            pd.testing.assert_frame_equal(original[CAUSAL_COLUMNS].iloc[:cut + 1],
                                          altered[CAUSAL_COLUMNS].iloc[:cut + 1], check_exact=True)

    def test_threshold_excludes_the_volatility_being_classified(self):
        closes = prices(400)
        d = 330
        original = build_features(closes)
        changed = closes.copy()
        changed.iloc[d - 1] *= 1.8
        altered = build_features(changed)
        self.assertNotAlmostEqual(original.volatility_prior.iloc[d], altered.volatility_prior.iloc[d])
        for column in ("volatility_threshold_p70", "volatility_threshold_p75",
                       "volatility_threshold_p80", "volatility_robust_threshold"):
            self.assertEqual(original[column].iloc[d], altered[column].iloc[d], column)
        returns = np.log(closes / closes.shift())
        vols = returns.rolling(20, min_periods=20).std(ddof=1)
        expected = linear_percentile(vols.iloc[d - 253:d - 1], .75)
        self.assertAlmostEqual(original.volatility_threshold_p75.iloc[d], expected, places=12)

    def test_first_eligible_day_requires_200_closes_and_252_prior_vols(self):
        result = self.assert_matches_independent(prices(300))
        self.assertEqual(result.trend.iloc[199], "warmup")
        self.assertNotEqual(result.trend.iloc[200], "warmup")
        self.assertTrue(result.group.iloc[:273].eq("warmup").all())
        self.assertNotEqual(result.group.iloc[273], "warmup")
        self.assertTrue(math.isnan(result.volatility_threshold_p75.iloc[272]))
        self.assertTrue(math.isfinite(result.volatility_threshold_p75.iloc[273]))

    def test_equality_is_neutral_trend_and_normal_volatility(self):
        closes = pd.Series(100., index=pd.bdate_range("2015-01-01", periods=300))
        result = self.assert_matches_independent(closes)
        self.assertEqual(result.trend.iloc[-1], "neutral")
        self.assertEqual(result.group.iloc[-1], "neutral_normal")
        self.assertEqual(result.volatility_prior.iloc[-1], 0.)
        self.assertEqual(result.volatility_threshold_p75.iloc[-1], 0.)

    def test_strict_trend_sides(self):
        index = pd.bdate_range("2015-01-01", periods=300)
        increasing = pd.Series(np.linspace(100, 300, 300), index=index)
        decreasing = pd.Series(np.linspace(300, 100, 300), index=index)
        self.assertEqual(self.assert_matches_independent(increasing).trend.iloc[-1], "bull")
        self.assertEqual(self.assert_matches_independent(decreasing).trend.iloc[-1], "bear")

    def test_roll_robust_has_full_20_session_window_and_15_valid_return_minimum(self):
        closes = prices(400)
        t = 330
        five = closes.index[t - 4:t + 1]
        six = closes.index[t - 5:t + 1]
        allowed = self.assert_matches_independent(closes, five)
        missing = self.assert_matches_independent(closes, six)
        self.assertTrue(math.isfinite(allowed.volatility_robust20.iloc[t]))
        self.assertTrue(math.isnan(missing.volatility_robust20.iloc[t]))
        self.assertEqual(missing.group_roll_robust.iloc[t + 1], "warmup")
        # The classified raw series and trend are not roll-adjusted.
        pd.testing.assert_series_equal(allowed.group, missing.group)
        pd.testing.assert_series_equal(allowed.trend, missing.trend)
        # A single missing historical robust SD invalidates the full threshold.
        self.assertTrue(math.isnan(missing.volatility_robust_threshold.iloc[t + 2]))

    def test_missing_sessions_are_not_forward_filled(self):
        closes = prices(360).drop(prices(360).index[[1, 4, 82, 155]])
        result = self.assert_matches_independent(closes)
        self.assertTrue(result.index.equals(closes.index))
        self.assertEqual(result.previous_date.iloc[5], closes.index[4])


class RiskAndLedgerTests(unittest.TestCase):
    @staticmethod
    def sources():
        raw = pd.DataFrame([
            {"ticket": 1, "entry_time": "2020-01-02 02:01:00", "exit_time": "2020-01-02 02:03:00",
             "trade_profit": 10., "candle_range": 5.},
            {"ticket": 2, "entry_time": "2020-01-03 02:01:00", "exit_time": "2020-01-03 02:04:00",
             "trade_profit": -20., "candle_range": 10.},
        ])
        html = pd.DataFrame([
            {"ticket": 1, "submitted": "2020-01-02 02:00:00", "entry_time": "2020-01-02 02:01:00",
             "exit_time": "2020-01-02 02:03:00", "trade_profit": 10.,
             "requested_price": 100., "original_sl": 95., "fill_price": 101.},
            {"ticket": 2, "submitted": "2020-01-03 02:00:00", "entry_time": "2020-01-03 02:01:00",
             "exit_time": "2020-01-03 02:04:00", "trade_profit": -20.,
             "requested_price": 110., "original_sl": 100., "fill_price": 110.},
        ])
        for column in ("submitted", "entry_time", "exit_time"):
            html[column] = pd.to_datetime(html[column])
        return raw, html

    def test_initial_r_uses_requested_price_not_realized_slippage(self):
        raw, html = self.sources()
        ledger = checked_ledger(raw, html)
        self.assertEqual(ledger.initial_risk_dollars.iloc[0], 10.)
        self.assertEqual(ledger.fill_risk_dollars.iloc[0], 12.)
        self.assertAlmostEqual(ledger.net_r.iloc[0], .895)
        self.assertAlmostEqual(ledger.net_dollars.iloc[0], 8.95)
        self.assertAlmostEqual(ledger.stress2_net_r.iloc[0], .695)

    def test_wrong_order_join_is_rejected(self):
        raw, html = self.sources()
        html.loc[1, "ticket"] = 99
        with self.assertRaisesRegex(AssertionError, "ticket coverage"):
            checked_ledger(raw, html)

    def test_retroactive_submission_is_rejected(self):
        raw, html = self.sources()
        html.loc[0, "submitted"] = pd.Timestamp("2020-01-02 02:02:00")
        with self.assertRaisesRegex(AssertionError, "submission after entry"):
            checked_ledger(raw, html)

    def test_cross_date_pending_order_is_rejected(self):
        raw, html = self.sources()
        html.loc[0, "submitted"] = pd.Timestamp("2020-01-01 23:00:00")
        with self.assertRaisesRegex(AssertionError, "cross-date pending"):
            checked_ledger(raw, html)

    def test_initial_risk_candle_mismatch_is_rejected(self):
        raw, html = self.sources()
        raw.loc[0, "candle_range"] = 6.
        with self.assertRaisesRegex(AssertionError, "candle-range initial risk"):
            checked_ledger(raw, html)

    def test_calendar_includes_zero_group_days(self):
        raw, html = self.sources()
        ledger = checked_ledger(raw, html)
        calendar = pd.bdate_range("2020-01-02", periods=40)
        metrics = independent_metrics(ledger, calendar)
        self.assertEqual(metrics["eligible_sessions"], 40)
        self.assertEqual(metrics["active_sessions"], 2)
        self.assertAlmostEqual(metrics["mean_worst5pct_sessions"], -21.05 / 2)
        self.assertAlmostEqual(metrics["daily_close_dd"], 21.05)
        self.assertEqual(metrics["daily_dd_duration_days"], (calendar[-1] - calendar[0]).days)

    def test_partial_2026_cannot_satisfy_annual_gate(self):
        rows = [{"year": year, "trades": 30, "net_dollars": -1.}
                for year in (2016, 2017, 2018, 2019, 2026)]
        self.assertFalse(full_year_negative_gate(rows))
        rows.append({"year": 2020, "trades": 30, "net_dollars": 1.})
        self.assertTrue(full_year_negative_gate(rows))
        rows[0]["trades"] = 29
        self.assertFalse(full_year_negative_gate(rows))

    def test_annual_gate_requires_at_least_sixty_percent_negative(self):
        rows = [{"year": 2016 + i, "trades": 40, "net_dollars": -1. if i < 3 else 1.}
                for i in range(5)]
        self.assertTrue(full_year_negative_gate(rows))
        rows[2]["net_dollars"] = 0.
        self.assertFalse(full_year_negative_gate(rows))


if __name__ == "__main__":
    unittest.main()

