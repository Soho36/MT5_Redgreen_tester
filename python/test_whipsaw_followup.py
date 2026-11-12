"""Tests for the follow-up's information boundaries and numerical comparisons."""
import unittest

import numpy as np
import pandas as pd

import analyze_whipsaw_followup as study
import whipsaw_days as wd
import whipsaw_followup_features as features


def toy_frame():
    rng = np.random.default_rng(23)
    dates = pd.bdate_range('2014-01-01', periods=1000)
    frame = pd.DataFrame(index=dates)
    for column in ('range_ratio', 'rv1', 'rv1_prior5', 'rv1_prior20',
                   'rv5m', 'rv5m_prior5', 'rv5m_prior20', 'recent5'):
        frame[column] = rng.uniform(.2, 2, len(frame))
    frame['signed_body'] = rng.normal(0, .4, len(frame))
    for column in ('news', 'next_news', 'roll_day', 'whipsaw',
                   'whipsaw_bounded', 'whipsaw_expanding', 'whipsaw_failed_both'):
        frame[column] = rng.random(len(frame)) < .1
    frame['abs_move_1'] = .1 + .4 * frame.rv1 + .2 * frame.whipsaw + rng.uniform(0, .1, len(frame))
    frame['next_session'] = pd.Series(dates, index=dates).shift(-1)
    frame['year'] = dates.year
    return frame


class Volatility(unittest.TestCase):
    def test_minute_and_five_minute_session_boundaries(self):
        minute = dict(day=np.array([1, 1, 1, 2]), minute=np.array([60, 61, 65, 60]),
                      o=np.array([100., 101., 99., 1000.]), c=np.array([101., 99., 100., 1001.]))
        got = features.minute_measures(minute)
        np.testing.assert_allclose(got.rv1_points, [np.sqrt(6), 1])
        np.testing.assert_allclose(got.rv5m_points, [np.sqrt(2), 1])

    def test_unsorted_minutes_rejected(self):
        with self.assertRaises(ValueError):
            features.minute_measures(dict(day=np.array([1, 1]), minute=np.array([61, 60]),
                                          o=np.array([1., 1.]), c=np.array([1., 1.])))

    def test_history_excludes_today_and_uses_kept_sessions(self):
        dates = pd.bdate_range('2024-01-01', periods=30)
        table = pd.DataFrame(dict(open=100., high=101., low=99., close=100.), index=dates)
        daily = pd.DataFrame(dict(rv1_points=np.arange(1., 31.), rv5m_points=np.arange(1., 31.)), index=dates)
        kept = table.drop(index=dates[10])
        panel = kept.iloc[21:].assign(atr20=2.)
        before = features.add_volatility(panel, kept, daily)
        day = panel.index[0]
        previous = daily.reindex(kept.index).loc[:day].iloc[:-1].tail(5).rv1_points.mean() / 2
        self.assertEqual(before.at[day, 'rv1_prior5'], previous)
        daily.at[day, 'rv1_points'] = 1000
        after = features.add_volatility(panel, kept, daily)
        self.assertEqual(before.at[day, 'rv1_prior20'], after.at[day, 'rv1_prior20'])
        self.assertEqual(before.at[day, 'rv1_prior5'], after.at[day, 'rv1_prior5'])
        self.assertEqual(after.at[day, 'rv1'], 500)


class Geometry(unittest.TestCase):
    def test_bounded_expanding_and_drifting_are_distinct(self):
        cases = [([100, 110, 100, 110], 'bounded'),
                 ([100, 110, 98, 113], 'expanding'),
                 ([100, 110, 102, 114], 'other'),
                 ([100, 110, 100], 'not_whipsaw')]
        for path, expected in cases:
            with self.subTest(path=path):
                points, confirmation = features.swing_trace(path, 7.5)
                self.assertEqual(features.geometry(points, 10), expected)
                self.assertEqual(len(confirmation), wd.count_swings(path, 7.5))

    def test_confirmation_not_backdated_to_pivot(self):
        points, confirmation = features.swing_trace([100, 107.5, 112, 104.5, 100, 107.5], 7.5)
        self.assertEqual(confirmation, [1, 3, 5])
        self.assertEqual([p[0] for p in points], [0, 2, 4, 5])

    def test_future_prices_do_not_change_existing_confirmation(self):
        prefix = [100, 108, 99, 108]
        _, first = features.swing_trace(prefix, 7.5)
        _, extended = features.swing_trace(prefix + [120, 100, 130], 7.5)
        self.assertEqual(first, extended[:len(first)])

    def test_trace_matches_original_on_random_paths(self):
        rng = np.random.default_rng(4)
        for _ in range(100):
            path = np.cumsum(rng.normal(size=100))
            _, at = features.swing_trace(path, 2.)
            self.assertEqual(len(at), wd.count_swings(path, 2.))

    def test_final_endpoint_is_observed_without_future_confirmation(self):
        points, at = features.swing_trace([100, 110, 98, 113, 116], 7.5)
        self.assertEqual(len(at), 3)
        self.assertEqual(points[-1], (4, 116, 'high'))
        self.assertEqual(features.geometry(points, 10), 'expanding')

    def test_both_directions_work(self):
        points, _ = features.swing_trace([110, 100, 113, 97], 7.5)
        self.assertEqual(features.geometry(points, 10), 'expanding')


class BreaksAndTiming(unittest.TestCase):
    def test_buffer_and_return_at_boundary(self):
        self.assertIsNone(features.failed_boundary([100.4], [99], [99], 100, 10, 'high'))
        self.assertEqual(features.failed_boundary([100.5], [99], [100], 100, 10, 'high'), 0)
        self.assertEqual(features.failed_boundary([101], [99.5], [100], 100, 10, 'low'), 0)

    def test_four_closes_includes_breach_bar(self):
        self.assertEqual(features.failed_boundary([102] * 5, [99] * 5, [101, 101, 101, 100, 99],
                                                 100, 10, 'high'), 3)
        self.assertIsNone(features.failed_boundary([102] * 5, [99] * 5, [101, 101, 101, 101, 99],
                                                  100, 10, 'high'))

    def test_later_retry_cannot_rescue_first_expired_breach(self):
        self.assertIsNone(features.failed_boundary([102] * 7, [99] * 7,
                                                  [101, 101, 101, 101, 101, 99, 99], 100, 10, 'high'))

    def test_remaining_outcome_excludes_recognition_bar(self):
        dates = pd.date_range('2024-01-02 01:00', periods=3, freq='30min')
        bars = pd.DataFrame(dict(bar_time=dates, open=[100., 105., 110.], high=[200., 300., 113.],
                                 low=[0., -100., 109.], close=[105., 110., 112.]))
        day = dates[0].normalize()
        panel = pd.DataFrame(dict(detected_bar=[1.], atr20=[2.]), index=[day])
        got = features.add_remaining_outcomes(panel, bars)
        self.assertEqual(got.at[day, 'remaining_abs_move'], 1.)
        self.assertEqual(got.at[day, 'remaining_range'], 2.)
        panel['detected_bar'] = 2
        got = features.add_remaining_outcomes(panel, bars)
        self.assertTrue(np.isnan(got.at[day, 'remaining_abs_move']))


class Forecasts(unittest.TestCase):
    def test_year_boundary_purges_unavailable_outcome(self):
        frame = pd.DataFrame(dict(next_session=pd.to_datetime(['2015-12-31', '2016-01-04', '2016-01-05']),
                                  abs_move_1=[1., 2., 3.]),
                             index=pd.to_datetime(['2015-12-30', '2015-12-31', '2016-01-04']))
        self.assertEqual(study.training_mask(frame, 2016).tolist(), [True, False, False])

    def test_ridge_matches_augmented_least_squares(self):
        rng = np.random.default_rng(5)
        x, y, new = rng.normal(size=(40, 4)), rng.uniform(1, 3, 40), rng.normal(size=(7, 4))
        predicted, _, _, mean, scale = study.fit_predict(x, y, new)
        design = np.c_[np.ones(len(x)), (x - mean) / scale]
        penalty = np.c_[np.zeros(4), np.sqrt(study.ALPHA) * np.eye(4)]
        beta = np.linalg.lstsq(np.vstack([design, penalty]), np.r_[y, np.zeros(4)], rcond=None)[0]
        expected = np.maximum(np.c_[np.ones(len(new)), (new - mean) / scale] @ beta, 0)
        np.testing.assert_allclose(predicted, expected, atol=1e-12)

    def test_test_rows_cannot_affect_scaling_or_other_predictions(self):
        x = np.arange(30.).reshape(10, 3)
        y = np.arange(10.) + 1
        a = study.fit_predict(x, y, np.array([[1., 2., 3.]]))
        b = study.fit_predict(x, y, np.array([[1., 2., 3.], [1e9, -1e9, 1e9]]))
        self.assertAlmostEqual(a[0][0], b[0][0])
        np.testing.assert_equal(a[3], b[3])
        np.testing.assert_equal(a[4], b[4])

    def test_future_features_and_targets_leave_earlier_forecasts_unchanged(self):
        frame = toy_frame()
        before, _, folds = study.forecasts(frame, years=[2016])
        frame.loc[frame.index >= '2017-01-01', 'rv1'] = 1000
        frame.loc[frame.index >= '2017-01-01', 'abs_move_1'] = 1000
        after, _, _ = study.forecasts(frame, years=[2016])
        np.testing.assert_array_equal(before.filter(like='pred_'), after.filter(like='pred_'))
        self.assertLess(pd.Timestamp(folds.last_train_outcome.iloc[0]), pd.Timestamp('2016-01-01'))

    def test_model_nesting_keeps_baseline_columns_identical(self):
        frame = toy_frame()
        a, b = study.design_matrix(frame, 'baseline'), study.design_matrix(frame, 'whipsaw')
        pd.testing.assert_frame_equal(a, b[a.columns])
        self.assertEqual(list(b.columns.difference(a.columns)), ['whipsaw'])

    def test_month_interval_matches_explicit_month_repetition(self):
        dates = pd.to_datetime(['2020-01-02', '2020-01-03', '2020-02-04', '2020-03-01'])
        values = np.array([1., 3., 10., np.nan])
        mean, lo, hi, failed = study.paired_interval(values, dates, draws=200, seed=7)
        weights = np.random.default_rng(7).multinomial(3, [1/3] * 3, size=200)
        samples = []
        for a, b, c in weights:
            repeated = [1., 3.] * a + [10.] * b
            samples.append(np.mean(repeated) if repeated else np.nan)
        self.assertEqual(mean, 14 / 3)
        np.testing.assert_allclose([lo, hi], np.nanpercentile(samples, [2.5, 97.5]))
        self.assertEqual(failed, int(np.isnan(samples).sum()))

    def test_identical_predictions_have_zero_paired_gain(self):
        frame = toy_frame().iloc[:50]
        frame['pred_baseline'] = .5
        frame['pred_whipsaw'] = .5
        row = study.score(frame, 'baseline', 'whipsaw')
        self.assertEqual([row[k] for k in ('mse_gain', 'mse_gain_lo', 'mse_gain_hi')], [0, 0, 0])


if __name__ == '__main__':
    unittest.main()

