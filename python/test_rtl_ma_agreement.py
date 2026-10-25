"""Focused boundary and causality checks for the frozen MA study."""
import unittest

import numpy as np
import pandas as pd

import analyze_rtl_ma_features as features
import analyze_rtl_ma_agreement as economics


def bars(count=260, close=None):
    close = np.arange(count, dtype=float)+100 if close is None else np.asarray(close, float)
    times = pd.date_range('2015-01-02 01:00', periods=len(close), freq='30min')
    return pd.DataFrame(dict(bar_time=times, available_at=times+pd.Timedelta(minutes=30),
        open=close, high=close+1, low=close-1, close=close, switch_bar=False))


def panel(states, valid=None, times=None):
    n = len(states)
    times = pd.date_range('2018-01-02 01:30', periods=n, freq='30min') if times is None else pd.to_datetime(times)
    return pd.DataFrame(dict(variant='primary', row_index=np.arange(n),
        bar_time=times-pd.Timedelta(minutes=30), available_at=times,
        close=np.arange(n, dtype=float)+100, a20=2., state=states,
        valid=True if valid is None else valid, roll_clean=True))


def labels(frame):
    states, episodes = features.build_state_episodes(frame)
    states, spells = features.add_nonup_spells(states)
    return states, episodes, spells


def trade(time, entry=None, exit=None, ticket=1):
    time = pd.Timestamp(time)
    return dict(ticket=ticket, submitted=time,
        entry_time=time+pd.Timedelta(minutes=1) if entry is None else pd.Timestamp(entry),
        exit_time=time+pd.Timedelta(minutes=10) if exit is None else pd.Timestamp(exit))


class MaTests(unittest.TestCase):
    def test_exact_deadband_edges_are_flat_without_tolerance(self):
        value = np.array([-.2, np.nextafter(-.2, -np.inf), .2,
                          np.nextafter(.2, np.inf), 0.])
        np.testing.assert_array_equal(features.votes(value, .2), [0, -1, 0, 1, 0])

    def test_zero_deadband_retains_exact_zero_flat(self):
        np.testing.assert_array_equal(features.votes(np.array([0., -0., -1e-300, 1e-300]), 0.), [0, 0, -1, 1])

    def test_common_history_is_201_observed_closes_and_literal_slope(self):
        f, _ = features.compute_features(bars())
        self.assertFalse(f.valid.iloc[:200].any())
        self.assertTrue(f.valid.iloc[200:].all())
        self.assertEqual(f.history_start.iloc[200], f.bar_time.iloc[0])
        for length in features.DENSE:
            literal = f.close.rolling(length).mean().diff()/f.a20
            np.testing.assert_allclose(f.loc[f.valid, f'z_{length}'], literal[f.valid])

    def test_true_range_includes_previous_close_and_first_is_invalid(self):
        b = bars()
        b.loc[201, ['open', 'high', 'low', 'close']] = [500., 502., 499., 501.]
        f, _ = features.compute_features(b)
        self.assertTrue(pd.isna(f.TR.iloc[0]))
        self.assertEqual(f.TR.iloc[201], 202.)
        self.assertAlmostEqual(f.a20.iloc[201], f.TR.iloc[182:202].sum()/20)

    def test_zero_true_range_invalid_and_missing_close_breaks_history(self):
        b = bars(480)
        b.loc[240:270, ['open', 'high', 'low', 'close']] = 100.
        f, _ = features.compute_features(b)
        self.assertFalse(f.valid.iloc[261])
        self.assertTrue(f.z_5.iloc[261:].isna().iloc[:10].all())
        b = bars(480)
        b.loc[220, 'close'] = np.nan
        f, _ = features.compute_features(b)
        self.assertFalse(f.valid.iloc[220:421].any())
        self.assertTrue(f.valid.iloc[421])

    def test_roll_mask_includes_all_201_consumed_rows(self):
        b = bars(450)
        b.loc[210, 'switch_bar'] = True
        f, _ = features.compute_features(b)
        self.assertTrue(f.roll_clean.iloc[209])
        self.assertFalse(f.roll_clean.iloc[210:411].any())
        self.assertTrue(f.roll_clean.iloc[411])

    def test_calibration_excludes_post2016_and_weights_price_rows(self):
        b = bars(460)
        b.loc[300:, 'bar_time'] += pd.Timedelta(days=366)
        b.loc[300:, 'available_at'] += pd.Timedelta(days=366)
        f, cut = features.compute_features(b)
        self.assertTrue(cut.calibration_observations.eq(100).all())
        for row in cut.itertuples():
            self.assertEqual(row.cutoff, np.quantile(np.abs(f.loc[200:299, f'z_{row.L}']), .2))
        changed = b.copy()
        changed.loc[300:, ['open', 'high', 'low', 'close']] += 999999.
        _, second = features.compute_features(changed)
        pd.testing.assert_frame_equal(cut, second)

    def test_short_down_long_up_can_coexist_with_clear_up(self):
        f, cuts = features.compute_features(bars())
        f = f.iloc[[-1]].copy()
        cuts.cutoff = .1
        for length in features.DENSE:
            f[f'z_{length}'] = 1.
        f['z_5'], f['z_10'] = -1., -1.
        s = features.classify(f, cuts, 'primary').iloc[0]
        self.assertEqual(s.state, 'up')
        self.assertEqual(s.up_votes, 5)
        self.assertEqual(s.short_direction, 'down')
        self.assertEqual(s.long_direction, 'up')

    def test_frozen_variants_thresholds_invalid_rows_never_vote(self):
        f, cuts = features.compute_features(bars())
        f = f.iloc[[0, -1]].copy()
        cuts.cutoff = .1
        for length in features.DENSE:
            f[f'z_{length}'] = 0.
        for length in features.PRIMARY[:4]:
            f[f'z_{length}'] = 1.
        self.assertEqual(features.classify(f, cuts, 'loose').state.iloc[1], 'up')
        self.assertEqual(features.classify(f, cuts, 'primary').state.iloc[1], 'mixed')
        for name in features.VARIANTS:
            invalid = features.classify(f, cuts, name).iloc[0]
            self.assertEqual(invalid.state, 'unknown')
            self.assertEqual(invalid.up_votes+invalid.down_votes+invalid.flat_votes, 0)

    def test_observed_gaps_and_year_boundaries_do_not_reset_state_age(self):
        frame = panel(['down', 'up', 'up', 'mixed'], times=[
            '2019-12-31 23:00', '2019-12-31 23:30', '2020-01-02 01:30', '2020-01-02 02:00'])
        states, episodes, _ = labels(frame)
        self.assertEqual(list(states.state_age), [1, 1, 2, 1])
        self.assertEqual(list(episodes.observations), [1, 2, 1])
        self.assertEqual(list(states.up_reentry_age), ['unknown', '1', '2-3', 'unknown'])

    def test_invalid_break_censors_and_restarts_episodes_and_spells(self):
        frame = panel(['up', 'down', 'unknown', 'mixed', 'up', 'up'], [True, True, False, True, True, True])
        states, episodes, spells = labels(frame)
        self.assertEqual(list(states.episode_id), [1, 2, 0, 3, 4, 4])
        self.assertEqual(list(episodes.left_censored), [True, False, True, False])
        self.assertEqual(list(episodes.right_censored), [False, True, False, True])
        self.assertEqual(list(spells.left_censored), [False, True])
        self.assertEqual(list(spells.right_censored), [True, False])
        self.assertTrue(pd.isna(spells.first_up.iloc[0]))
        self.assertEqual(spells.first_up.iloc[1], frame.available_at.iloc[4])

    def test_nonup_spells_join_alternating_down_mixed_and_keep_empty_trade_spells(self):
        frame = panel(['up', 'down', 'mixed', 'down', 'up', 'mixed', 'up'])
        states, _, spells = labels(frame)
        self.assertEqual(list(states.nonup_id), [0, 1, 1, 1, 0, 2, 0])
        self.assertEqual(list(spells.observations), [3, 1])
        self.assertEqual(list(states.first_up), [False, False, False, False, True, False, True])
        self.assertEqual(list(states.next_up_delay_bars.iloc[1:4]), [3., 2., 1.])
        self.assertEqual(len(spells), 2)  # Inventory does not need any trades.

    def test_exact_availability_and_unobserved_time_gaps(self):
        frame = panel(['up', 'down', 'up'], times=['2018-01-05 22:00', '2018-01-05 22:30', '2018-01-08 01:30'])
        states, _, _ = labels(frame)
        query = pd.DataFrame({'entry_time': pd.to_datetime(['2018-01-05 21:59:59', '2018-01-05 22:29:59',
            '2018-01-05 22:30', '2018-01-07 12:00', '2018-01-08 01:30', '2026-10-01'], format='mixed')})
        event = features.endpoint_state(query, states, 'entry_time')
        self.assertEqual(list(event.event_state), ['unknown', 'up', 'down', 'down', 'up', 'unknown'])

    def test_firstup_exact_fill_exit_and_right_censoring(self):
        frame = panel(['up', 'down', 'mixed', 'up', 'mixed'])
        states, _, _ = labels(frame)
        a = frame.available_at
        trades = pd.DataFrame([
            trade(a.iloc[0], ticket=1),
            trade(a.iloc[1], entry=a.iloc[3], exit=a.iloc[3]+pd.Timedelta(minutes=10), ticket=2),
            trade(a.iloc[1], exit=a.iloc[3], ticket=3),
            trade(a.iloc[1], ticket=4), trade(a.iloc[4], ticket=5)])
        result = features.join_trades(trades, states, states).set_index('ticket')
        self.assertEqual(list(result.loc[[1, 2, 3, 4, 5], 'firstup_timing']),
            ['already_up', 'up_by_fill', 'up_during_trade', 'up_after_exit', 'no_observed_up'])
        self.assertEqual(result.loc[2, 'fill_state'], 'up')
        self.assertEqual(result.loc[3, 'exit_state'], 'up')

    def test_delay_from_actual_submission_differs_from_feature_delay(self):
        frame = panel(['up', 'down', 'mixed', 'up'])
        states, _, _ = labels(frame)
        result = features.join_trades(pd.DataFrame([trade(frame.available_at.iloc[1]+pd.Timedelta(minutes=7))]), states, states)
        self.assertEqual(result.next_up_delay_from_feature_minutes.iloc[0], 60.)
        self.assertEqual(result.next_up_delay_minutes.iloc[0], 53.)
        self.assertEqual(result.next_up_move_atr.iloc[0], 1.)

    def test_future_price_changes_leave_earlier_causal_fields_unchanged(self):
        b = bars(530)
        b.loc[300:, ['bar_time', 'available_at']] += pd.Timedelta(days=366)
        f, c = features.compute_features(b)
        s, _, _ = labels(features.classify(f, c, 'primary'))
        changed = b.copy()
        changed.loc[430:, ['open', 'high', 'low', 'close']] -= 10000.
        f2, c2 = features.compute_features(changed)
        s2, _, _ = labels(features.classify(f2, c2, 'primary'))
        pd.testing.assert_frame_equal(c, c2)
        causal = ['row_index', 'available_at', 'close', 'a20', 'history_start', 'valid', 'roll_clean',
            'up_votes', 'down_votes', 'flat_votes', 'breadth', 'state', 'context', 'episode_id',
            'state_age', 'age_bin', 'episode_start', 'prior_state', 'up_reentry_age']
        pd.testing.assert_frame_equal(s.loc[:429, causal], s2.loc[:429, causal], check_exact=True)

    def test_policy_decisions_use_submission_state_only(self):
        trades = pd.DataFrame({'state': ['mixed', 'down', 'up'], 'fill_state': ['up', 'up', 'down']})
        np.testing.assert_array_equal(economics.skip_mask(trades, 'skip_mixed'), [True, False, False])
        np.testing.assert_array_equal(economics.skip_mask(trades, 'skip_down'), [False, True, False])
        np.testing.assert_array_equal(economics.skip_mask(trades, 'only_up'), [True, True, False])

    def test_drawdown_includes_initial_zero_and_empty_dates(self):
        self.assertEqual(economics.max_dd([-4., 0., 1., -3., 10.]), 6.)
        self.assertEqual(economics.max_dd([]), 0.)


if __name__ == '__main__':
    unittest.main()
