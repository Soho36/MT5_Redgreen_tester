"""Boundary and causality tests for the frozen episode attribution.

These fixtures exercise executable calculations, never select new thresholds.
Full-data independent reconstruction lives in verify_rtl_flagged_episodes.py.
"""
import unittest

import numpy as np
import pandas as pd

import analyze_rtl_flagged_episodes as study
from analyze_rtl_price_structure import build_features, classify_features


def panel(flags, valid=None, times=None):
    count = len(flags)
    if times is None:
        times = pd.date_range("2018-01-02 01:00", periods=count, freq="30min")
    times = pd.DatetimeIndex(times)
    return pd.DataFrame(dict(bar_time=times, available_at=times + pd.Timedelta(minutes=30),
                             valid=np.ones(count, dtype=bool) if valid is None else valid,
                             low_eff=flags, high_overlap=flags, high_wick=flags,
                             high=np.repeat(110., count), low=np.repeat(90., count)))


def trade_at(submitted, ticket=1, entry_time=None, exit_time=None, **changes):
    submitted = pd.Timestamp(submitted)
    entry_time = pd.Timestamp(entry_time) if entry_time is not None else submitted + pd.Timedelta(minutes=1)
    exit_time = pd.Timestamp(exit_time) if exit_time is not None else submitted + pd.Timedelta(minutes=10)
    data = dict(ticket=ticket, submitted=submitted, entry_time=entry_time, exit_time=exit_time,
                fill_price=100., exit_price=101., requested_price=100., original_sl=95.,
                mae_money=-2., mfe_money=4., trade_profit=2., net_dollars=.95, net_r=.095,
                holding_minutes=(exit_time-entry_time).total_seconds()/60,
                session=submitted.normalize(), week_start=pd.Timestamp("2018-01-01"), era="2016-19")
    data.update(changes)
    return data


def attribute(frame, trades, n=3, flag="m30_main", coverage_end=study.END):
    labelled, inventory = study.build_episodes(frame, study.flag_mask(frame, flag), coverage_end)
    return study.attribute_trades(pd.DataFrame(trades), labelled, inventory, n, coverage_end), labelled, inventory


class EpisodeTests(unittest.TestCase):
    def test_maximal_runs_include_observations_without_trades(self):
        frame = panel([False, True, True, False, True, False])
        labelled, inventory = study.build_episodes(frame, frame.low_eff)
        self.assertEqual(list(labelled.episode_id), [0, 1, 1, 0, 2, 0])
        self.assertEqual(list(labelled.episode_age), [0, 1, 2, 0, 1, 0])
        self.assertEqual(list(inventory.length), [2, 1])
        self.assertEqual(list(inventory.first_clear), [frame.available_at.iloc[3], frame.available_at.iloc[5]])
        self.assertFalse(inventory.left_censored.any())
        self.assertFalse(inventory.right_censored.any())

    def test_invalid_row_breaks_and_censors_both_sides(self):
        frame = panel([False, True, True, True, True, True, False],
                      valid=[True, True, True, False, True, True, True])
        labelled, inventory = study.build_episodes(frame, frame.low_eff)
        self.assertEqual(list(labelled.episode_id), [0, 1, 1, 0, 2, 2, 0])
        self.assertEqual(list(inventory.left_censored), [False, True])
        self.assertEqual(list(inventory.right_censored), [True, False])
        self.assertTrue(pd.isna(inventory.first_clear.iloc[0]))
        self.assertEqual(inventory.observed_end.iloc[0], frame.available_at.iloc[3])

    def test_edge_runs_are_censored_and_endpoint_is_not_fabricated_clear(self):
        frame = panel([True, False, True, True])
        cutoff = frame.available_at.iloc[-1] + pd.Timedelta(hours=4)
        _, inventory = study.build_episodes(frame, frame.low_eff, cutoff)
        self.assertEqual(list(inventory.left_censored), [True, False])
        self.assertEqual(list(inventory.right_censored), [False, True])
        self.assertTrue(pd.isna(inventory.first_clear.iloc[-1]))
        self.assertEqual(inventory.observed_end.iloc[-1], cutoff)
        self.assertEqual(inventory.elapsed_hours.iloc[-1], 4.5)
        self.assertEqual(inventory.observed_span_hours.iloc[-1], .5)

    def test_calendar_gaps_and_era_change_do_not_split_observed_run(self):
        times = pd.to_datetime(["2019-12-31 23:00", "2019-12-31 23:30", "2020-01-02 01:00", "2020-01-02 01:30"])
        frame = panel([False, True, True, False], times=times)
        _, inventory = study.build_episodes(frame, frame.low_eff)
        self.assertEqual(len(inventory), 1)
        self.assertEqual(inventory.length.iloc[0], 2)
        self.assertEqual(inventory.elapsed_hours.iloc[0], 26.)

    def test_no_true_rows_has_empty_episode_inventory(self):
        frame = panel([False]*5)
        labelled, inventory = study.build_episodes(frame, frame.low_eff)
        self.assertTrue(inventory.empty)
        self.assertTrue(labelled.episode_id.eq(0).all())

    def test_short_and_three_part_retrospective_phases(self):
        frame = panel([False, False, False] + [True]*6 + [False, True, False, True, True, False])
        selected = [*range(3, 9), 10, 12, 13]
        trades = [trade_at(frame.available_at.iloc[i], ticket=i) for i in selected]
        result, _, _ = attribute(frame, trades)
        self.assertEqual(list(result.retrospective_phase),
                         ["early", "early", "middle", "middle", "late", "late"] + ["short_episode"]*3)
        self.assertEqual(list(result.causal_age_bin), ["1", "2-3", "2-3", "4-8", "4-8", "4-8", "1", "1", "2-3"])

    def test_censored_phase_overrides_short_and_long_lengths(self):
        frame = panel([False, False, False, True, True, False, True],
                      valid=[True, True, False, True, True, True, True])
        result, _, _ = attribute(frame, [trade_at(frame.available_at.iloc[i], ticket=i) for i in (3, 4, 6)])
        self.assertTrue(result.retrospective_phase.eq("censored").all())
        self.assertTrue(pd.isna(result.fill_at_or_after_clear.iloc[-1]))

    def test_endpoint_availability_equality_invalid_and_later_episode(self):
        frame = panel([False, True, True, False, True, True, False],
                      valid=[True, True, True, True, True, False, True])
        labelled, _ = study.build_episodes(frame, frame.low_eff)
        cutoff = frame.available_at.iloc[-1] + pd.Timedelta(minutes=30)
        queries = [frame.available_at.iloc[0]-pd.Timedelta(seconds=1),
                   frame.available_at.iloc[3]-pd.Timedelta(seconds=1), frame.available_at.iloc[3],
                   frame.available_at.iloc[4], frame.available_at.iloc[5],
                   cutoff-pd.Timedelta(seconds=1), cutoff]
        trades = pd.DataFrame(dict(entry_time=queries, episode_id=[1]*len(queries)), index=[8, 3, 9, 2, 10, 11, 12])
        result = study.endpoint_states(trades, labelled, "entry_time", cutoff)
        self.assertEqual(list(result.state), ["unknown", "same_episode", "unflagged", "later_episode", "unknown", "unflagged", "unknown"])
        self.assertEqual(list(result.index), list(trades.index))

    def test_submission_and_clear_exact_boundary(self):
        frame = panel([False, False, True, True, False, True, False])
        trades = [trade_at(frame.available_at.iloc[2]-pd.Timedelta(seconds=1), ticket=1),
                  trade_at(frame.available_at.iloc[2], ticket=2, entry_time=frame.available_at.iloc[4],
                           exit_time=frame.available_at.iloc[5]),
                  trade_at(frame.available_at.iloc[4], ticket=3)]
        result, _, _ = attribute(frame, trades)
        self.assertEqual(list(result.ticket), [2])
        self.assertEqual(result.fill_episode_state.iloc[0], "unflagged")
        self.assertEqual(result.exit_episode_state.iloc[0], "later_episode")
        self.assertTrue(result.fill_at_or_after_clear.iloc[0])
        self.assertTrue(result.exit_at_or_after_clear.iloc[0])
        self.assertEqual(result.submission_delay_minutes.iloc[0], 60.)

    def test_range_uses_exact_n_candles_and_stays_frozen(self):
        frame = panel([False, False, False, True, True, False])
        frame.high = [900., 110., 105., 106., 1000., 2000.]
        frame.low = [1., 90., 95., 94., 50., 10.]
        result, _, _ = attribute(frame, [trade_at(frame.available_at.iloc[3],
                                                  entry_time=frame.available_at.iloc[4],
                                                  exit_time=frame.available_at.iloc[5])])
        self.assertEqual(result.range_high.iloc[0], 110.)
        self.assertEqual(result.range_low.iloc[0], 90.)
        self.assertEqual(result.range_start.iloc[0], frame.bar_time.iloc[1])
        self.assertEqual(result.headroom_r.iloc[0], 2.)

    def test_equal_boundary_touches_are_contained(self):
        maxima = [110., 110.0001, 110., 111.]
        minima = [90., 90., 89.9999, 89.]
        self.assertEqual(list(study.path_groups(maxima, minima, 110., 90.)),
                         ["contained", "upper_only", "lower_only", "both"])
        self.assertEqual(list(study.endpoint_location([90., 110., 89.99, 110.01], 110., 90.)),
                         ["inside", "inside", "below", "above"])

    def test_logged_negative_mfe_is_not_clamped_to_fill(self):
        frame = panel([False, False, False, True, False])
        frame.high = 99.
        frame.low = 90.
        result, _, _ = attribute(frame, [trade_at(frame.available_at.iloc[3], fill_price=100., exit_price=98.,
                                                  mfe_money=-2., mae_money=-6., trade_profit=-4., net_dollars=-5.05)])
        self.assertEqual(result.sampled_max_price.iloc[0], 99.)
        self.assertEqual(result.sampled_min_price.iloc[0], 97.)
        self.assertEqual(result.path_group.iloc[0], "contained")
        self.assertEqual(result.fill_location.iloc[0], "above")
        self.assertEqual(result.exit_location.iloc[0], "inside")

    def test_exit_outside_logged_envelope_is_rejected(self):
        frame = panel([False, False, False, True, False])
        with self.assertRaises(AssertionError):
            attribute(frame, [trade_at(frame.available_at.iloc[3], exit_price=103., mfe_money=4.)])

    def test_zero_trade_episodes_are_retained(self):
        frame = panel([False, False, False, True, False, True, False])
        result, _, inventory = attribute(frame, [trade_at(frame.available_at.iloc[3])])
        episodes = study.episode_pnl(inventory, result)
        self.assertEqual(list(episodes.trades), [1, 0])
        self.assertEqual(list(episodes.net_dollars), [.95, 0.])

    def test_winning_and_losing_shares_use_separate_denominators(self):
        frame = panel([False, False, False, True, True, False])
        trades = [trade_at(frame.available_at.iloc[3], ticket=1, net_dollars=10.),
                  trade_at(frame.available_at.iloc[4], ticket=2, net_dollars=-4.)]
        result, _, _ = attribute(frame, trades)
        metrics = study.metrics(result.iloc[:1], positive_total=20., loss_total=8.)
        self.assertEqual(metrics["winning_dollars_share"], .5)
        self.assertEqual(metrics["losing_dollars_share"], 0.)
        metrics = study.metrics(result.iloc[1:], positive_total=20., loss_total=8.)
        self.assertEqual(metrics["winning_dollars_share"], 0.)
        self.assertEqual(metrics["losing_dollars_share"], .5)

    def test_future_price_changes_leave_submission_causal_fields_unchanged(self):
        close = np.array([80, 85, 90, 95, 100, 101, 100, 101, 100, 101, 100, 101, 100, 101, 100, 101], dtype=float)
        index = pd.date_range("2018-01-02 01:00", periods=len(close), freq="30min")
        ohlc = pd.DataFrame(dict(open=close, high=close+10, low=close-10, close=close), index=index)
        cutoff = dict(efficiency_low=.4, overlap_high=.8, wick_high=.8)

        def prepare(prices):
            return classify_features(build_features(prices, 4), cutoff).reset_index()

        original = prepare(ohlc)
        changed_prices = ohlc.copy()
        changed_prices.iloc[12:] += np.arange(1, 5)[:, None]*1000
        changed = prepare(changed_prices)
        submitted = original.available_at.iloc[10]
        rows = [trade_at(submitted)]
        before, _, _ = attribute(original, rows, n=4)
        after, _, _ = attribute(changed, rows, n=4)
        self.assertEqual(len(before), 1)
        causal = ["ticket", "submitted", "available_at", "bar_time", "episode_id", "episode_age",
                  "start", "causal_age_bin", "range_high", "range_low", "range_start", "headroom_r"]
        pd.testing.assert_frame_equal(before[causal], after[causal], check_exact=True)
        self.assertNotEqual(before.length.iloc[0], after.length.iloc[0])
        self.assertEqual(before.retrospective_phase.iloc[0], "censored")
        self.assertNotEqual(after.retrospective_phase.iloc[0], "censored")


if __name__ == "__main__":
    unittest.main()
