"""Whipsaw-day study: zigzag, ATR20 look-back, flags, outcomes, both comparisons, month resampling."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_whipsaw_days as study
import review_whipsaw_days as review
import whipsaw_days as wd
from prepare_whipsaw_days import FREEZE, frozen_texts


def session(day, prices):
    """M30 bars from 01:00 of `day`; prices are (open, high, low, close) rows."""
    frame = pd.DataFrame(prices, columns=['open', 'high', 'low', 'close'], dtype=float)
    frame.insert(0, 'bar_time', pd.date_range(f'{day} 01:00', periods=len(frame), freq='30min'))
    return frame


def quiet(day, width, bars=20, level=100.0):
    """A session whose range is exactly `width` around `level`, opening and closing at `level`."""
    rows = [(level, level + width / 2, level - width / 2, level)] + [(level, level, level, level)] * (bars - 1)
    return session(day, rows)


def calendar(count, start='2024-01-01'):
    return [str(day.date()) for day in pd.bdate_range(start, periods=count)]


def swings_by_scan(path, threshold):
    """The zigzag definition written as repeated searches for the next reversal."""
    p = np.asarray(path, float)
    up = np.flatnonzero(p - np.minimum.accumulate(p) >= threshold)
    down = np.flatnonzero(np.maximum.accumulate(p) - p >= threshold)
    if not len(up) and not len(down):
        return 0
    first_up = up[0] if len(up) else len(p)
    first_down = down[0] if len(down) else len(p)
    at, direction, count = (first_up, 1, 1) if first_up < first_down else (first_down, -1, 1)
    while True:
        rest = p[at:]
        drop = np.maximum.accumulate(rest) - rest if direction == 1 else rest - np.minimum.accumulate(rest)
        hit = np.flatnonzero(drop >= threshold)
        if not len(hit):
            return count
        at, direction, count = at + hit[0], -direction, count + 1


class Zigzag(unittest.TestCase):
    def test_bar_path_order(self):
        path = wd.bar_path([10, 10, 10], [12, 12, 12], [9, 9, 9], [11, 9.5, 10])
        self.assertEqual(path.tolist(), [10, 9, 12, 11,      # up bar: open, low, high, close
                                         10, 12, 9, 9.5,     # down bar: open, high, low, close
                                         10, 9, 12, 10])     # closes at its open: walked as an up bar

    def test_shapes(self):
        self.assertEqual(wd.count_swings([100, 100.5, 99.6, 100.4], 1), 0)        # never a full threshold
        self.assertEqual(wd.count_swings([100, 101, 103, 106], 1), 1)             # one-way day
        self.assertEqual(wd.count_swings([100, 103, 101.5, 104, 102.9], 2), 1)    # pullbacks below threshold
        self.assertEqual(wd.count_swings([100, 102, 100], 2), 2)                  # V shape
        self.assertEqual(wd.count_swings([100, 101, 100, 101], 1), 3)             # up, down, up: exactly the threshold
        self.assertEqual(wd.count_swings([100, 101, 100.01, 101], 1), 1)          # reversal one cent short

    def test_first_swing_starts_at_the_running_extreme_not_the_open(self):
        self.assertEqual(wd.count_swings([100, 99.5, 100.6], 1), 1)   # 1.1 off the low, only 0.6 above the open
        self.assertEqual(wd.count_swings([100, 100.5, 99.4], 1), 1)

    def test_later_swings_are_measured_from_the_swing_extreme(self):
        # up swing confirmed at 101, runs to 105; a fall to 104.1 is not a reversal, a fall to 104 is
        self.assertEqual(wd.count_swings([100, 101, 105, 104.1], 1), 1)
        self.assertEqual(wd.count_swings([100, 101, 105, 104], 1), 2)

    def test_threshold_must_be_positive(self):
        for bad in (0, -1, np.nan):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                wd.count_swings([1, 2, 3], bad)

    def test_matches_independent_scan_on_random_paths(self):
        rng = np.random.default_rng(7)
        for _ in range(300):
            path = 100 + np.cumsum(rng.normal(0, 1, rng.integers(5, 200)).round(2))
            threshold = float(rng.choice([0.5, 1, 2, 3.5, 6]))
            self.assertEqual(wd.count_swings(path, threshold), swings_by_scan(path, threshold))


class EventPanel(unittest.TestCase):
    def setUp(self):
        self.days = calendar(26)
        self.widths = [2.0 + 0.1 * i for i in range(26)]

    def bars(self, widths=None, replace=None):
        parts = [quiet(day, width) for day, width in zip(self.days, widths or self.widths)]
        for index, frame in (replace or {}).items():
            parts[index] = frame
        return pd.concat(parts, ignore_index=True)

    def test_atr20_is_the_mean_true_range_of_the_twenty_previous_sessions(self):
        panel = wd.event_panel(self.bars())
        # the first session has no true range, so the first ATR20 belongs to session 21 (0-based)
        self.assertEqual([str(d.date()) for d in panel.index], self.days[21:])
        for row, index in zip(panel.itertuples(), range(21, 26)):
            self.assertAlmostEqual(row.atr20, np.mean(self.widths[index - 20:index]), places=12)
            self.assertAlmostEqual(row.range_ratio, self.widths[index] / row.atr20, places=12)

    def test_true_range_reaches_to_the_previous_close(self):
        gapped = quiet(self.days[10], 2.0, level=110.0)      # opens 10 above the previous close of 100
        panel = wd.event_panel(self.bars(replace={10: gapped}))
        widths = list(self.widths)
        widths[10] = 11.0                           # high 111 down to the previous close 100
        widths[11] = 10 + self.widths[11] / 2       # low of session 11 up to the previous close 110
        self.assertAlmostEqual(panel.atr20.iloc[0], np.mean(widths[1:21]), places=12)

    def test_a_session_does_not_enter_its_own_atr20(self):
        base = wd.event_panel(self.bars())
        widths = list(self.widths)
        widths[22] = 50.0
        changed = wd.event_panel(self.bars(widths))
        self.assertEqual(changed.atr20.iloc[1], base.atr20.iloc[1])        # session 22 itself: unchanged
        self.assertGreater(changed.atr20.iloc[2], base.atr20.iloc[2])      # session 23: now includes it
        self.assertEqual(changed.atr20.iloc[0], base.atr20.iloc[0])        # session 21: earlier, unchanged

    def test_short_sessions_are_dropped_before_anything_else(self):
        short = quiet(self.days[15], 80.0, bars=wd.MIN_BARS - 1)
        panel = wd.event_panel(self.bars(replace={15: short}))
        kept = [w for i, w in enumerate(self.widths) if i != 15]
        self.assertNotIn(pd.Timestamp(self.days[15]), panel.index)
        self.assertEqual(str(panel.index[0].date()), self.days[22])        # one session later: 20 kept ones needed
        self.assertAlmostEqual(panel.atr20.iloc[0], np.mean(kept[1:21]), places=12)

    def test_whipsaw_flags_follow_the_swing_counts(self):
        atr = np.mean(self.widths[1:21])            # ATR20 of session 21
        step = 0.8 * atr                            # one swing: more than 0.75 and 0.5, less than 1.0 x ATR20
        rows = [(100, 100, 100, 100)] * 17 + [(100, 100 + step, 100, 100 + step),      # up
                                              (100 + step, 100 + step, 100, 100),      # down
                                              (100, 100 + step, 100, 100 + step)]      # up
        panel = wd.event_panel(self.bars(replace={21: session(self.days[21], rows)}))
        first = panel.iloc[0]
        self.assertEqual((first.swings_whipsaw, first.swings_looser, first.swings_stricter), (3, 3, 0))
        self.assertTrue(first.whipsaw)              # 3 swings of 0.75 x ATR20
        self.assertFalse(first.looser)              # the looser neighbour needs 4 swings
        self.assertFalse(first.stricter)            # no swing reaches 1.0 x ATR20
        self.assertFalse(panel.whipsaw.iloc[1:].any())

    def test_outside_day_must_close_back_inside(self):
        def day(close, high=106.0, low=94.0):
            return session(self.days[22], [(100, high, low, close)] + [(close, close, close, close)] * 19)
        previous = self.widths[21] / 2              # the previous session spans 100 +/- this
        cases = [(day(100.0), True), (day(100 + previous), True), (day(100 - previous), True),   # ends included
                 (day(100 + previous + .25), False), (day(100 - previous - .25), False),         # closes outside
                 (day(100.0, low=100 - previous), False), (day(100.0, high=100 + previous), False)]  # one end only
        for index, (bars, expected) in enumerate(cases):
            with self.subTest(case=index):
                panel = wd.event_panel(self.bars(replace={22: bars}))
                self.assertEqual(bool(panel[wd.OUTSIDE].iloc[1]), expected)

    def test_size_groups_are_equal_count(self):
        groups = wd.size_groups(np.random.default_rng(1).normal(size=1003))
        self.assertEqual(sorted(np.bincount(groups).tolist()), [100] * 7 + [101] * 3)
        self.assertEqual(wd.size_groups([5, 1, 3, 2, 4], groups=5).tolist(), [4, 0, 2, 1, 3])

    @unittest.skipUnless(wd.READY_M30.exists(), 'saved M30 bars not available')
    def test_handed_over_counts_reproduce(self):
        self.assertEqual(wd.counts(wd.event_panel(wd.read_m30())), wd.EXPECTED_COUNTS)

    @unittest.skipUnless(FREEZE.exists(), 'study not frozen')
    def test_protocol_and_event_code_match_the_freeze(self):
        freeze = json.loads(FREEZE.read_text(encoding='utf-8'))
        for key, value in frozen_texts().items():
            self.assertEqual(freeze[key], value, key)


def toy_table(rows, dates):
    table = pd.DataFrame(rows, columns=['open', 'high', 'low', 'close'], index=pd.DatetimeIndex(dates), dtype=float)
    table['bars'] = 46
    return table


class Outcomes(unittest.TestCase):
    ROWS = [(100, 101, 99, 100), (100, 104, 99, 103), (103, 104, 100, 101),
            (111, 112, 108, 109), (109, 110, 107, 108), (108, 109, 108, 109)]

    def panel(self, table):
        return table.assign(atr20=2.0, position=np.arange(len(table)))

    def test_next_session_and_next_three_with_a_roll_inside(self):
        table = toy_table(self.ROWS, calendar(6))
        out = study.add_outcomes(self.panel(table), table, rolls=[table.index[3]])   # jump of +10 into session 3
        first = out.iloc[0]
        self.assertEqual((first.abs_move_1, first.range_1, first.trend_1, first.signed_1), (1.5, 2.5, 1.0, 1.5))
        self.assertEqual((first.abs_move_3, first.range_3, first.trend_3, first.signed_3), (0.5, 3.0, 0.0, -0.5))
        second = out.iloc[1]        # sessions 2, 3, 4: the roll is in the middle
        self.assertEqual((second.abs_move_3, second.range_3, second.trend_3, second.signed_3), (2.5, 3.5, 1.0, -2.5))
        third = out.iloc[2]         # the roll session opens the window: nothing to take out
        self.assertEqual((third.abs_move_3, third.range_3, third.signed_3), (1.0, 2.5, -1.0))
        self.assertEqual(out.next_session.iloc[0], table.index[1])

    def test_without_roll_dates_the_jump_stays(self):
        table = toy_table(self.ROWS, calendar(6))
        out = study.add_outcomes(self.panel(table), table)
        self.assertEqual((out.abs_move_3.iloc[0], out.range_3.iloc[0]), (4.5, 6.5))

    def test_missing_later_sessions_give_no_outcome(self):
        table = toy_table(self.ROWS, calendar(6))
        out = study.add_outcomes(self.panel(table), table)
        self.assertTrue(np.isnan(out.abs_move_3.iloc[3:]).all() and not np.isnan(out.abs_move_3.iloc[:3]).any())
        self.assertTrue(np.isnan(out.abs_move_1.iloc[5]) and np.isnan(out.trend_1.iloc[5]))
        self.assertFalse(np.isnan(out.abs_move_1.iloc[:5]).any())
        self.assertTrue(pd.isna(out.next_session.iloc[5]))

    def test_sessions_from_the_end_date_are_not_outcomes(self):
        table = toy_table(self.ROWS, ['2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30', '2026-10-01', '2026-10-02'])
        out = study.add_outcomes(self.panel(table), table)
        self.assertFalse(np.isnan(out.abs_move_1.iloc[2]))       # 09-29 -> 09-30
        self.assertTrue(np.isnan(out.abs_move_1.iloc[3]))        # 09-30 -> 10-01 is outside the sample
        self.assertTrue(np.isnan(out.abs_move_3.iloc[1]))        # 09-28 would need 10-01

    def test_an_event_session_does_not_enter_its_own_outcomes(self):
        table = toy_table(self.ROWS, calendar(6))
        changed = toy_table([(50, 500, 5, 400)] + self.ROWS[1:], calendar(6))
        a = study.add_outcomes(self.panel(table), table).iloc[0]
        b = study.add_outcomes(self.panel(changed), changed).iloc[0]
        for column in study.MARKET:
            self.assertEqual(a[column], b[column], column)

    def test_news_free_drops_news_sessions_and_the_sessions_before_them(self):
        table = toy_table(self.ROWS, calendar(6))
        out = study.add_news(study.add_outcomes(self.panel(table), table), pd.DatetimeIndex([table.index[2]]))
        self.assertEqual(out.news.tolist(), [False, False, True, False, False, False])
        self.assertEqual(out.next_news.tolist(), [False, True, False, False, False, False])
        self.assertEqual(out.news_free.tolist(), [True, False, False, True, True, True])

    def test_ledger_results_of_the_next_session(self):
        table = toy_table(self.ROWS, calendar(6, '2015-12-29'))    # 12-29, 12-30, 12-31, 01-01, 01-04, 01-05
        panel = study.add_outcomes(self.panel(table), table)
        trades = pd.DataFrame(dict(
            session=['2016-01-04', '2016-01-04', '2016-01-05', '2016-01-05', '2015-12-31'],
            net_dollars=[10.0, -4.0, 7.0, 100.0, 55.0], net_r=[1.0, -1.2, 0.5, 9.0, 3.0],
            era=['2016-19'] * 3 + ['endpoint', '2010-15'], sample=['primary'] * 3 + ['excluded', 'secondary']))
        with tempfile.TemporaryDirectory() as folder:
            path, thinner = Path(folder) / 'ledger.csv', Path(folder) / 'thinner.csv'
            trades.to_csv(path, index=False)
            trades.loc[trades.session.ne('2016-01-04')].to_csv(thinner, index=False)
            out = study.add_ledgers(panel, {'gg': path}, published=None)
            quiet_day = study.add_ledgers(panel, {'gg': thinner}, published=None)
        self.assertTrue(np.isnan(out.gg_net.iloc[:3]).all())         # event sessions before 2016
        self.assertAlmostEqual(out.gg_net.iloc[3], 6.0)              # 01-01 -> 01-04: 10 - 4
        self.assertAlmostEqual(out.gg_r.iloc[3], -0.2)
        self.assertAlmostEqual(out.gg_net.iloc[4], 7.0)              # only the primary row of 01-05
        self.assertTrue(np.isnan(out.gg_net.iloc[5]))                # no next session
        self.assertEqual(quiet_day.gg_net.iloc[3], 0.0)              # the strategy did not trade: zero, not missing


def toy_sessions(rows):
    frame = pd.DataFrame(rows, columns=['year', 'size_group', 'whipsaw', 'y', 'range_ratio', 'month'])
    frame['whipsaw'] = frame.whipsaw.astype(bool)
    return frame


class Comparisons(unittest.TestCase):
    def one(self, frame, draws=20, seed=3):
        months = int(frame.month.max()) + 1
        weights = study.month_weights(months, draws, seed)
        return (*study.compare(frame, 'whipsaw', 'y', frame.month.to_numpy(), weights), weights)

    def test_matched_difference_by_hand(self):
        frame = toy_sessions([
            (2020, 0, 1, 2, 1, 0), (2020, 0, 1, 4, 1, 1), (2020, 0, 0, 1, 1, 0), (2020, 0, 0, 1, 1, 1), (2020, 0, 0, 1, 1, 2),
            (2020, 1, 1, 5, 2, 0), (2020, 1, 0, 3, 2, 1), (2020, 1, 0, 5, 2, 2),
            (2021, 0, 1, 7, 1, 3),                              # an event session with no control: left out
            (2021, 1, 0, 9, 2, 3), (2021, 1, 0, 9, 2, 4),       # controls with no event session: unused
            (2020, 0, 1, np.nan, 1, 0)])                        # no outcome: ignored
        row, _, _ = self.one(frame)
        self.assertAlmostEqual(row['matched_diff'], (2 * (3 - 1) + 1 * (5 - 4)) / 3)
        self.assertEqual((row['sessions'], row['events'], row['events_used'], row['controls_used']), (11, 4, 3, 5))
        self.assertAlmostEqual(row['event_mean'], 11 / 3)
        self.assertAlmostEqual(row['control_mean'], 2.0)
        self.assertAlmostEqual(row['all_events_mean'], 4.5)
        self.assertAlmostEqual(row['other_sessions_mean'], 29 / 7)
        self.assertAlmostEqual(row['matched_diff'], study.matched_plain(frame, 'whipsaw', 'y'))

    def synthetic(self, effect, noise, seed=5, sessions=1500):
        rng = np.random.default_rng(seed)
        year = rng.integers(2016, 2020, sessions)
        size = rng.gamma(4, .3, sessions)
        group = wd.size_groups(size, 5)
        flag = rng.random(sessions) < np.clip(.25 * size - .1, 0, .9)      # larger days are events more often
        level = rng.normal(0, 1, (4, 5))[year - 2016, group]
        y = level + .3 * size + effect * flag + noise * rng.normal(size=sessions)
        month = (year - 2016) * 12 + rng.integers(0, 12, sessions)
        return pd.DataFrame(dict(year=year, size_group=group, whipsaw=flag, y=y, range_ratio=size, month=month))

    def test_size_correction_recovers_a_planted_effect_that_matching_overstates(self):
        frame = self.synthetic(effect=.2, noise=0)
        row, _, _ = self.one(frame)
        self.assertGreater(row['event_size'], row['control_size'])      # events stay larger inside their groups
        self.assertGreater(row['matched_diff'], .2 + .005)              # so the matched difference is tilted up
        self.assertAlmostEqual(row['corrected_diff'], .2, places=9)
        self.assertAlmostEqual(row['size_slope'], .3, places=9)

    def test_no_planted_effect_gives_zero_after_size_correction(self):
        row, _, _ = self.one(self.synthetic(effect=0, noise=0))
        self.assertGreater(row['matched_diff'], .005)                   # size alone looks like an effect
        self.assertAlmostEqual(row['corrected_diff'], 0, places=9)

    def test_fast_versions_equal_the_plain_ones(self):
        frame = self.synthetic(effect=.1, noise=.5)
        frame.loc[::17, 'y'] = np.nan
        row, _, _ = self.one(frame)
        self.assertAlmostEqual(row['matched_diff'], study.matched_plain(frame, 'whipsaw', 'y'), places=10)
        self.assertAlmostEqual(row['corrected_diff'], study.corrected_plain(frame, 'whipsaw', 'y'), places=9)

    def test_month_resampling_redraws_whole_months(self):
        frame = self.synthetic(effect=.1, noise=.5, sessions=600)
        frame['month'] = pd.factorize(frame.month, sort=True)[0]
        row, resampled, weights = self.one(frame, draws=12)
        months = int(frame.month.max()) + 1
        self.assertEqual(weights.shape, (12, months))
        self.assertTrue((weights.sum(1) == months).all())               # as many months as the sample has
        self.assertTrue(np.array_equal(weights, study.month_weights(months, 12, 3)))    # same seed, same draws
        self.assertFalse(np.array_equal(weights, study.month_weights(months, 12, 4)))
        for draw in range(12):                                          # each draw = whole months repeated
            parts = [frame.loc[frame.month.eq(m)] for m in range(months) for _ in range(weights[draw, m])]
            again = pd.concat(parts, ignore_index=True)
            self.assertAlmostEqual(resampled['matched'][draw], study.matched_plain(again, 'whipsaw', 'y'), places=9)
            self.assertAlmostEqual(resampled['corrected'][draw], study.corrected_plain(again, 'whipsaw', 'y'), places=8)
        low, high = study.interval(resampled['matched'])
        self.assertEqual((row['matched_lo'], row['matched_hi']), (low, high))
        self.assertLessEqual(low, high)


class Reading(unittest.TestCase):
    def summary(self):
        values = {('2016-19', 'whipsaw'): .05, ('2020-26', 'whipsaw'): .04, ('2016-26', 'whipsaw'): .045,
                  ('2016-26', 'looser'): .02, ('2016-26', 'stricter'): .03}
        rows = [dict(sample=sample, variant=variant, event=event, outcome=study.PRIMARY, matched_diff=value,
                     matched_lo=value - .03, corrected_diff=value - .01, corrected_lo=value - .04)
                for (sample, event), value in values.items() for variant in study.VARIANTS]
        return pd.DataFrame(rows)

    def summary_with(self, key, value):
        frame = self.summary()
        sample, event, variant, column = key
        frame.loc[frame['sample'].eq(sample) & frame.event.eq(event) & frame.variant.eq(variant), column] = value
        return frame

    def test_all_four_conditions_give_supported(self):
        result = study.reading(self.summary())
        self.assertTrue(result['supported'] and all(result['conditions'].values()))
        self.assertEqual(result['verdict'], 'supported')

    def test_each_condition_can_fail_alone(self):
        cases = {'1_matched_above_zero_in_both_eras': ('2016-19', 'whipsaw', 'all', 'matched_diff'),
                 '2_pooled_matched_interval_above_zero': ('2016-26', 'whipsaw', 'all', 'matched_lo'),
                 '3_pooled_size_corrected_interval_above_zero': ('2016-26', 'whipsaw', 'all', 'corrected_lo'),
                 '4_both_neighbours_above_zero_pooled': ('2016-26', 'stricter', 'all', 'matched_diff')}
        for name, key in cases.items():
            with self.subTest(name=name):
                result = study.reading(self.summary_with(key, -.001))
                failed = [k for k, passed in result['conditions'].items() if not passed]
                self.assertEqual(failed, [name])
                self.assertEqual(result['verdict'], 'not supported')

    def test_other_instruments_are_judged_without_the_neighbours(self):
        frame = self.summary_with(('2016-26', 'stricter', 'all', 'matched_diff'), -.5)
        self.assertEqual(study.reading(frame)['verdict'], 'not supported')
        result = study.reading(frame, neighbours=False)
        self.assertEqual(len(result['conditions']), 3)
        self.assertEqual(result['verdict'], 'supported')

    def test_news_free_run_cannot_rescue_and_can_qualify(self):
        qualified = study.reading(self.summary_with(('2016-26', 'whipsaw', 'news_free', 'matched_diff'), -.01))
        self.assertTrue(qualified['supported'])
        self.assertEqual(qualified['verdict'], 'supported, but an effect of scheduled news')
        failed = self.summary_with(('2016-26', 'whipsaw', 'all', 'matched_lo'), -.01)
        failed.loc[failed.variant.eq('news_free'), ['matched_diff', 'matched_lo', 'corrected_lo']] = 1.0
        self.assertEqual(study.reading(failed)['verdict'], 'not supported')


class Review(unittest.TestCase):
    """The checks made after the result (review_whipsaw_days.py)."""

    def test_movement_inside_a_session(self):
        bars = pd.concat([session('2024-01-01', [(100, 104, 99, 103), (103, 103, 99, 99), (99, 99, 99, 99)]),
                          session('2024-01-02', [(50, 56, 50, 56), (56, 56, 48, 48)])], ignore_index=True)
        inside = review.movement_inside(bars)
        self.assertAlmostEqual(inside.iloc[0], np.sqrt(3 ** 2 + 4 ** 2 + 0 ** 2))      # 100 -> 103 -> 99 -> 99
        self.assertAlmostEqual(inside.iloc[1], np.sqrt(6 ** 2 + 8 ** 2))               # starts again at its own open

    def test_flag_coefficient_equals_least_squares_with_cell_dummies(self):
        rng = np.random.default_rng(11)
        n = 400
        cell = rng.integers(0, 6, n)
        flag, size, extra = (rng.random(n) < .3).astype(float), rng.gamma(4, .3, n), rng.normal(size=n)
        y = .2 * flag + .3 * size - .4 * extra + cell + rng.normal(size=n)
        weight = rng.integers(0, 4, n).astype(float)        # how often each session is drawn; zero allowed
        design = np.column_stack([flag, size, extra, np.eye(6)[cell]])
        root = np.sqrt(weight)[:, None]
        expected = np.linalg.lstsq(design * root, y * root[:, 0], rcond=None)[0][0]
        self.assertAlmostEqual(review.flag_coefficient(y, [flag, size, extra], cell, weight), expected, places=10)
        exact = review.flag_coefficient(.2 * flag + .3 * size - .4 * extra + cell, [flag, size, extra], cell, np.ones(n))
        self.assertAlmostEqual(exact, .2, places=10)


if __name__ == '__main__':
    unittest.main()
