"""Economic invariants for the frozen RTL VWAP omission study."""
from unittest import TestCase, main
from unittest.mock import patch

import numpy as np
import pandas as pd

import analyze_rtl_vwap as study


def sample():
    calendar = pd.date_range('2020-01-01', '2020-03-31', freq='B')
    n = 48
    submitted = pd.DatetimeIndex([calendar[i//4]+pd.Timedelta(minutes=[540, 989, 990, 1200][i % 4]) for i in range(n)])
    frame = pd.DataFrame(dict(ticket=np.arange(n), submitted=submitted,
        entry_time=submitted+pd.Timedelta(minutes=1), exit_time=submitted+pd.Timedelta(minutes=11),
        session=submitted.normalize(), net_dollars=np.tile([-4., 2., 3., -1.], 12),
        initial_risk_dollars=np.arange(n) % 9+10., holding_minutes=10.,
        side=np.tile(['below', 'above', 'below', 'above'], 12),
        distance=np.tile(['far_below', 'above', 'below', 'far_above'], 12),
        churn=np.tile(['churn', 'orderly', 'unknown', 'orderly'], 12),
        churn4=np.tile(['churn', 'orderly', 'churn', 'orderly'], 12),
        event=np.tile(['loss', 'reclaim', 'same_side', 'unknown'], 12)))
    frame['week_start'] = frame.session-pd.to_timedelta(frame.session.dt.dayofweek, unit='D')
    frame['trade_profit'] = frame.net_dollars+1.05
    frame['gross_r'] = frame.trade_profit/frame.initial_risk_dollars
    frame['net_r'] = frame.net_dollars/frame.initial_risk_dollars
    frame['commission_r'] = 1.05/frame.initial_risk_dollars
    frame['fill_risk_dollars'] = frame.initial_risk_dollars
    for stress in (1, 2):
        frame[f'stress{stress}_net_dollars'] = frame.net_dollars-stress
        frame[f'stress{stress}_net_r'] = frame[f'stress{stress}_net_dollars']/frame.initial_risk_dollars
    return frame, calendar


class VwapEconomicsTests(TestCase):
    def setUp(self):
        self.trades, self.calendar = sample()

    def test_unknown_retained_by_every_policy(self):
        unknown = self.trades.iloc[:1].copy()
        for column in study.PARTITIONS:
            unknown[column] = 'unknown'
        for policy in study.POLICIES:
            self.assertFalse(study.skip_mask(unknown, policy).any(), policy)

    def test_partition_and_omission_reconcile_including_losses_and_costs(self):
        rows = pd.DataFrame(study.partition_rows(self.trades, self.calendar))
        for dimension in study.PARTITIONS:
            part = rows.loc[rows.dimension.eq(dimension)]
            self.assertEqual(part.trades.sum(), len(self.trades))
            self.assertAlmostEqual(part.net_dollars.sum(), self.trades.net_dollars.sum())
        for policy in study.POLICIES:
            rows, curves = study.policy_comparison(self.trades, self.calendar, policy)
            baseline, retained, static = rows
            self.assertEqual(len(curves), 3*len(self.calendar))
            self.assertAlmostEqual(retained['net_dollars']+retained['skipped_net_dollars'], baseline['net_dollars'])
            self.assertAlmostEqual(retained['profits_missed']-retained['losses_avoided'], retained['skipped_net_dollars'])
            fraction = retained['retained_holding_fraction']
            self.assertAlmostEqual(static['net_dollars'], baseline['net_dollars']*fraction)
            self.assertAlmostEqual(static['stress1_net_dollars'], baseline['stress1_net_dollars']*fraction)
            self.assertAlmostEqual(static['daily_close_dd'], baseline['daily_close_dd']*fraction)

    def test_overlapping_groups_bootstrap_shares_total_and_includes_empty_weeks(self):
        with patch.object(study, 'DRAWS', 100):
            rows, draws, metadata = study.bootstrap(self.trades, self.calendar, np.random.default_rng(20261025))
        self.assertEqual(len(draws), 400)
        self.assertEqual(metadata['calendar_weeks'], 14)
        self.assertLess(self.trades.week_start.nunique(), metadata['calendar_weeks'])
        self.assertEqual(metadata['blocks_per_draw'], 4)
        self.assertEqual(metadata['trimmed_weeks'], 14)
        totals = draws.assign(total_count=draws.selected_trades+draws.complement_trades,
                              total_r=draws.selected_net_r+draws.complement_net_r)
        for _, group in totals.groupby('draw'):
            self.assertEqual(group.total_count.nunique(), 1)
            np.testing.assert_allclose(group.total_r, group.total_r.iloc[0], atol=1e-12)
        # far_below is a subset of below; groups are not a partition.
        wide = draws.pivot(index='draw', columns='policy', values='selected_trades')
        self.assertTrue((wide.skip_far_below <= wide.skip_below).all())
        self.assertTrue((wide.skip_far_below > 0).any())
        self.assertTrue((wide.skip_below > wide.skip_far_below).any())

    def test_zero_shift_identity_and_each_shift_own_static_exposure(self):
        for policy in study.PRIMARY_POLICIES:
            draws, summary = study.placement(self.trades, self.calendar, policy, [0, 1, 2])
            for column in ('net_dollars', 'daily_close_dd', 'holding_hours',
                           'profit_advantage_vs_static', 'dd_advantage_vs_static'):
                self.assertAlmostEqual(draws.iloc[0][column], summary[f'actual_{column}'])
            np.testing.assert_allclose(draws.profit_advantage_vs_static,
                                       draws.net_dollars-draws.static_holding_net_dollars)
            np.testing.assert_allclose(draws.dd_advantage_vs_static,
                                       draws.static_holding_daily_close_dd-draws.daily_close_dd)

    def test_submission_time_boundaries_and_confound_counts(self):
        rows, summary = study.confounds(self.trades, 'skip_below')
        frame = pd.DataFrame(rows)
        self.assertEqual(frame.selected_trades.sum(), int(study.skip_mask(self.trades, 'skip_below').sum()))
        self.assertEqual(frame.complement_trades.sum()+frame.selected_trades.sum(), len(self.trades))
        self.assertEqual(set(frame.time_block), {'09:00-16:29', '16:30-19:59', '20:00+'})
        time_counts = (frame.selected_trades+frame.complement_trades).groupby(frame.time_block).sum().to_dict()
        self.assertEqual(time_counts, {'09:00-16:29': 24, '16:30-19:59': 12, '20:00+': 12})
        self.assertGreaterEqual(summary['supported_selected_share'], 0.)
        self.assertLessEqual(summary['supported_selected_share'], 1.)


if __name__ == '__main__':
    main()
