"""Frozen RTL VWAP attribution and omission controls; not a strategy replay."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_rtl_market_regimes as prior

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_vwap_20261025'
PROTOCOL = ROOT / 'docs/baseline/rtl-vwap/PROTOCOL.md'
PROTOCOL_SHA256 = 'a75e57ab36fe49fb63f3664f847cb8ba52ac651a109a76c3cc220c0344eb0314'
VARIANTS = ('full_hlc3', 'full_close', 'cash_hlc3')
PARTITIONS = {
    'side': ('above', 'below', 'at', 'unknown'),
    'distance': ('far_below', 'below', 'at', 'above', 'far_above', 'unknown'),
    'event': ('reclaim', 'loss', 'same_side', 'unknown'),
    'churn': ('churn', 'orderly', 'unknown'),
    'churn4': ('churn', 'orderly', 'unknown'),
}
PRIMARY_POLICIES = ('skip_below', 'skip_far_above', 'skip_far_below', 'skip_churn')
POLICIES = (*PRIMARY_POLICIES, 'skip_churn4')
ERAS = prior.ERAS
DRAWS, SHIFTS = 5000, 1000


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def dates(frame, columns):
    for column in columns:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], format='ISO8601')
    return frame


def metrics(trades, calendar):
    result = prior.metrics(trades, calendar)
    result.update(winners=int(trades.net_dollars.gt(0).sum()),
                  losers=int(trades.net_dollars.lt(0).sum()),
                  positive_net_dollars=float(trades.net_dollars.clip(lower=0).sum()),
                  loss_dollars=float(-trades.net_dollars.clip(upper=0).sum()),
                  gross_r_total=float(trades.gross_r.sum()),
                  net_r_total=float(trades.net_r.sum()),
                  planned_risk_total=float(trades.initial_risk_dollars.sum()),
                  adequate_coverage=bool(len(trades) >= 200 and trades.week_start.nunique() >= 30))
    # Closed equity at exit timestamps, with initial flat equity at calendar start.
    order = trades.sort_values(['exit_time', 'entry_time', 'ticket'], kind='stable')
    peak, equity, duration = 0., 0., 0.
    peak_time = pd.Timestamp(calendar[0])
    for row in order.itertuples():
        equity += float(row.net_dollars)
        if equity >= peak-1e-9:
            peak, peak_time = max(peak, equity), row.exit_time
        else:
            duration = max(duration, (row.exit_time-peak_time).total_seconds()/86400)
    if equity < peak-1e-9:
        duration = max(duration, (pd.Timestamp(calendar[-1])+pd.Timedelta(days=1)-peak_time).total_seconds()/86400)
    result['closed_trade_dd_duration_days'] = float(duration)
    result['net_over_daily_dd'] = result['net_dollars']/result['daily_close_dd'] if result['daily_close_dd'] else np.nan
    return result


def skip_mask(trades, policy):
    mapping = {'skip_below': ('side', 'below'), 'skip_far_above': ('distance', 'far_above'),
               'skip_far_below': ('distance', 'far_below'), 'skip_churn': ('churn', 'churn'),
               'skip_churn4': ('churn4', 'churn')}
    column, label = mapping[policy]
    return trades[column].eq(label).to_numpy()


def max_dd(pnl):
    equity = np.r_[0., np.asarray(pnl).cumsum()]
    return float((np.maximum.accumulate(equity)-equity).max())


def daily_curve(trades, calendar):
    return trades.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.)


def policy_comparison(trades, calendar, policy, with_sessions=True):
    mask = skip_mask(trades, policy)
    retained, omitted = trades.loc[~mask], trades.loc[mask]
    holding_fraction = float(retained.holding_minutes.sum()/trades.holding_minutes.sum()) if len(trades) else 0.
    fractions = dict(skipped_trades=int(mask.sum()), skipped_active_weeks=int(omitted.week_start.nunique()),
                     skipped_net_dollars=float(omitted.net_dollars.sum()),
                     skipped_net_mean_r=float(omitted.net_r.mean()),
                     losses_avoided=float(-omitted.net_dollars.clip(upper=0).sum()),
                     profits_missed=float(omitted.net_dollars.clip(lower=0).sum()),
                     retained_trade_fraction=float(len(retained)/len(trades)) if len(trades) else np.nan,
                     retained_holding_fraction=holding_fraction,
                     retained_planned_risk_fraction=float(retained.initial_risk_dollars.sum()/trades.initial_risk_dollars.sum()) if len(trades) else np.nan)
    scaled = trades.copy()
    # Scale both PnL and commission dollars; R stays invariant for positive scale.
    # Fractional contracts and scaled holding are diagnostic exposure equivalents.
    for column in ('net_dollars', 'trade_profit', 'initial_risk_dollars', 'fill_risk_dollars',
                   'stress1_net_dollars', 'stress2_net_dollars', 'holding_minutes'):
        scaled[column] *= holding_fraction
    if holding_fraction == 0:
        for column in ('gross_r', 'net_r', 'commission_r', 'stress1_net_r', 'stress2_net_r'):
            scaled[column] = np.nan
    rows, sessions = [], []
    for curve, frame in (('baseline', trades), ('retained', retained), ('static_holding_scaled', scaled)):
        rows.append(dict(curve=curve, **metrics(frame, calendar), **fractions,
                         pnl_scale=holding_fraction if curve == 'static_holding_scaled' else 1.))
        if with_sessions:
            sessions.extend(dict(curve=curve, session=date, net_dollars=float(pnl))
                            for date, pnl in daily_curve(frame, calendar).items())
    assert np.isclose(retained.net_dollars.sum()+omitted.net_dollars.sum(), trades.net_dollars.sum(), atol=1e-8)
    assert np.isclose(fractions['profits_missed']-fractions['losses_avoided'], fractions['skipped_net_dollars'], atol=1e-8)
    return rows, sessions


def partition_rows(trades, calendar):
    rows = [dict(dimension='all', category='all', **metrics(trades, calendar))]
    for dimension, categories in PARTITIONS.items():
        assert trades[dimension].isin(categories).all(), dimension
        counts, dollars, net_r = 0, 0., 0.
        for category in categories:
            part = trades.loc[trades[dimension].eq(category)]
            rows.append(dict(dimension=dimension, category=category, **metrics(part, calendar)))
            counts += len(part)
            dollars += part.net_dollars.sum()
            net_r += part.net_r.sum()
        assert counts == len(trades)
        assert np.isclose(dollars, trades.net_dollars.sum(), atol=1e-8)
        assert np.isclose(net_r, trades.net_r.sum(), atol=1e-10)
    return rows


def bootstrap(trades, calendar, rng):
    first = calendar[0]-pd.Timedelta(days=calendar[0].dayofweek)
    last = calendar[-1]-pd.Timedelta(days=calendar[-1].dayofweek)
    weeks = pd.date_range(first, last, freq='7D')
    weekly = [trades.groupby('week_start').net_r.agg(['sum', 'count']).reindex(weeks, fill_value=0.).to_numpy()]
    for policy in PRIMARY_POLICIES:
        weekly.append(trades.loc[skip_mask(trades, policy)].groupby('week_start').net_r.agg(['sum', 'count']).reindex(weeks, fill_value=0.).to_numpy())
    data = np.stack(weekly, axis=1)
    assert data[:, 0, 1].sum() == len(trades)
    starts = rng.integers(0, len(weeks), size=(DRAWS, math.ceil(len(weeks)/4)))
    indices = ((starts[:, :, None]+np.arange(4)) % len(weeks)).reshape(DRAWS, -1)[:, :len(weeks)]
    samples = np.empty((DRAWS, 1+len(PRIMARY_POLICIES), 2))
    for offset in range(0, DRAWS, 100):
        samples[offset:offset+100] = data[indices[offset:offset+100]].sum(axis=1)
    rows, draws = [], []
    for j, policy in enumerate(PRIMARY_POLICIES, start=1):
        numerator, count = samples[:, j, 0], samples[:, j, 1]
        other_sum, other_count = samples[:, 0, 0]-numerator, samples[:, 0, 1]-count
        means = np.divide(numerator, count, out=np.full(DRAWS, np.nan), where=count > 0)
        other_means = np.divide(other_sum, other_count, out=np.full(DRAWS, np.nan), where=other_count > 0)
        differences = means-other_means
        mask = skip_mask(trades, policy)
        chosen, other = trades.loc[mask], trades.loc[~mask]
        row = dict(policy=policy, trades=len(chosen), active_weeks=int(chosen.week_start.nunique()),
                   net_mean_r=float(chosen.net_r.mean()), complement_trades=len(other),
                   complement_net_mean_r=float(other.net_r.mean()),
                   difference_net_r=float(chosen.net_r.mean()-other.net_r.mean()),
                   valid_mean_draws=int(np.isfinite(means).sum()),
                   valid_difference_draws=int(np.isfinite(differences).sum()))
        for name, values in (('mean_net_r', means), ('difference_net_r', differences)):
            finite = values[np.isfinite(values)]
            for suffix, alpha in (('95', .05), ('98_75', .05/4)):
                low, high = np.quantile(finite, [alpha/2, 1-alpha/2], method='linear') if len(finite) else (np.nan, np.nan)
                row[f'{name}_ci{suffix}_low'] = float(low)
                row[f'{name}_ci{suffix}_high'] = float(high)
        rows.append(row)
        draws.append(pd.DataFrame(dict(policy=policy, draw=np.arange(DRAWS), selected_net_r=numerator,
            selected_trades=count.astype(int), complement_net_r=other_sum, complement_trades=other_count.astype(int),
            mean_net_r=means, difference_net_r=differences)))
    metadata = dict(draws=DRAWS, calendar_weeks=len(weeks), block_weeks=4, circular=True,
                    blocks_per_draw=math.ceil(len(weeks)/4), trimmed_weeks=len(weeks),
                    paired_across_policies=True, adjustment='Four primary omitted-subset comparisons per era only; not all prior research')
    return rows, pd.concat(draws, ignore_index=True), metadata


def confounds(trades, policy):
    frame = trades.copy()
    minute = frame.submitted.dt.hour*60+frame.submitted.dt.minute
    assert minute.ge(60).all()
    frame['time_block'] = pd.cut(minute, [59, 539, 989, 1199, 1440],
                                labels=['01:00-08:59', '09:00-16:29', '16:30-19:59', '20:00+'])
    q1, q2 = frame.initial_risk_dollars.quantile([1/3, 2/3]).to_numpy()
    frame['risk_tertile'] = np.where(frame.initial_risk_dollars.le(q1), 'low',
                                   np.where(frame.initial_risk_dollars.le(q2), 'middle', 'high'))
    frame['selected'] = skip_mask(frame, policy)
    rows, weighted_sum, supported_count = [], 0., 0
    for (time_block, risk_tertile), part in frame.groupby(['time_block', 'risk_tertile'], observed=True, sort=True):
        selected, other = part.loc[part.selected], part.loc[~part.selected]
        supported = bool(len(selected) and len(other))
        difference = float(selected.net_r.mean()-other.net_r.mean())
        if supported:
            weighted_sum += len(selected)*difference
            supported_count += len(selected)
        rows.append(dict(policy=policy, time_block=str(time_block), risk_tertile=str(risk_tertile),
                         selected_trades=len(selected), complement_trades=len(other),
                         selected_net_r_sum=float(selected.net_r.sum()), complement_net_r_sum=float(other.net_r.sum()),
                         selected_net_mean_r=float(selected.net_r.mean()), complement_net_mean_r=float(other.net_r.mean()),
                         difference_net_r=difference, common_support=supported))
    total = int(frame.selected.sum())
    summary = dict(policy=policy, risk_tertile_q1=float(q1), risk_tertile_q2=float(q2), selected_trades=total,
                   supported_selected_trades=supported_count,
                   supported_selected_share=float(supported_count/total) if total else np.nan,
                   subset_count_weighted_difference_net_r=float(weighted_sum/supported_count) if supported_count else np.nan,
                   unadjusted_difference_net_r=float(frame.loc[frame.selected].net_r.mean()-frame.loc[~frame.selected].net_r.mean()))
    return rows, summary


def placement(trades, calendar, policy, offsets):
    # Submission order is the causal order of these omission decisions.
    trades = trades.sort_values(['submitted', 'ticket'], kind='stable')
    skip = skip_mask(trades, policy)
    pnl, hours = trades.net_dollars.to_numpy(), trades.holding_minutes.to_numpy()/60
    day_ids = calendar.get_indexer(trades.session)
    assert (day_ids >= 0).all()
    baseline_net, baseline_hours = float(pnl.sum()), float(hours.sum())
    baseline_dd = max_dd(daily_curve(trades, calendar))

    def evaluate(keep):
        net, holding = float(pnl[keep].sum()), float(hours[keep].sum())
        dd = max_dd(np.bincount(day_ids[keep], weights=pnl[keep], minlength=len(calendar)))
        fraction = holding/baseline_hours
        static_net, static_dd = baseline_net*fraction, baseline_dd*fraction
        return dict(retained_trades=int(keep.sum()), net_dollars=net, daily_close_dd=dd, holding_hours=holding,
                    holding_fraction=fraction, static_holding_net_dollars=static_net, static_holding_daily_close_dd=static_dd,
                    profit_advantage_vs_static=net-static_net, dd_advantage_vs_static=static_dd-dd)

    actual = evaluate(~skip)
    frame = pd.DataFrame(dict(draw=draw, offset=int(offset), **evaluate(~np.roll(skip, int(offset))))
                         for draw, offset in enumerate(offsets))
    summary = dict(draws=len(frame), **{f'actual_{name}': value for name, value in actual.items()})
    for column in ('profit_advantage_vs_static', 'dd_advantage_vs_static'):
        # Larger is favorable for both advantages. Ties reported separately.
        summary[f'fraction_shifts_beaten_{column}'] = float(frame[column].lt(actual[column]).mean())
        summary[f'fraction_shifts_tied_{column}'] = float(np.isclose(frame[column], actual[column], rtol=0, atol=1e-8).mean())
    for column in ('net_dollars', 'daily_close_dd', 'profit_advantage_vs_static', 'dd_advantage_vs_static'):
        for quantile in (.025, .5, .975):
            summary[f'{column}_q{int(quantile*1000)}'] = float(frame[column].quantile(quantile))
    return frame, summary


def load_inputs():
    assert digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol changed'
    trades = dates(pd.read_csv(OUT/'trades.csv'), ['submitted', 'entry_time', 'exit_time', 'session',
                                                 'week_start', 'available_at', 'bar_time'])
    assert trades.groupby('variant').size().to_dict() == {name: 16668 for name in VARIANTS}
    assert not trades.duplicated(['variant', 'ticket']).any()
    assert trades.roll_clean.isin([True, False]).all()
    observed_dates = []
    for variant in VARIANTS:
        features = dates(pd.read_csv(OUT/f'features_{variant}.csv', usecols=['bar_time']), ['bar_time'])
        observed_dates.append(pd.DatetimeIndex(features.bar_time.dt.normalize().unique()).sort_values())
        part = trades.loc[trades.variant.eq(variant)]
        assert part.groupby('era').size().to_dict() == {'2016-19': 6167, '2020-26': 10501}
        assert np.isclose(part.loc[part.era.eq('2016-19'), 'net_dollars'].sum(), 4416.65, atol=1e-8)
        assert np.isclose(part.loc[part.era.eq('2020-26'), 'net_dollars'].sum(), 38399.95, atol=1e-8)
        assert np.allclose(part.net_dollars, part.trade_profit-1.05, atol=1e-10, rtol=0)
        assert np.allclose(part.net_r, part.net_dollars/part.initial_risk_dollars, atol=1e-12, rtol=0)
        assert part.loc[part.available_at.notna(), 'available_at'].le(part.loc[part.available_at.notna(), 'submitted']).all()
        assert part.loc[part.vwap.notna(), 'bar_time'].dt.normalize().eq(part.loc[part.vwap.notna(), 'session']).all()
        for column, labels in PARTITIONS.items():
            assert part[column].isin(labels).all(), (variant, column)
    for calendar in observed_dates[1:]:
        assert calendar.equals(observed_dates[0]), 'Variant observed calendars differ'
    return trades, observed_dates[0]


def main():
    trades, calendar_all = load_inputs()
    summary_rows, yearly, rolls, common, policies, roll_policies, sessions, availability = [], [], [], [], [], [], [], []
    uncertainty, boot_draws, shifts, shift_summaries, strata, confound_summaries = [], [], [], [], [], []
    bootstrap_metadata = {}
    boot_rng, placement_rng = np.random.default_rng(20261025), np.random.default_rng(20261026)
    for era, (start, stop) in ERAS.items():
        calendar = calendar_all[(calendar_all >= start) & (calendar_all < stop)]
        era_trades = trades.loc[trades.era.eq(era)]
        available_tickets = {}
        for variant in ('full_hlc3', 'cash_hlc3'):
            part = era_trades.loc[era_trades.variant.eq(variant)]
            available_tickets[variant] = set(part.loc[part.vwap.notna(), 'ticket'])
        common_tickets = available_tickets['full_hlc3'] & available_tickets['cash_hlc3']
        for variant in VARIANTS:
            part = era_trades.loc[era_trades.variant.eq(variant)].copy()
            assert part.session.isin(calendar).all()
            summary_rows.extend(dict(variant=variant, era=era, **row) for row in partition_rows(part, calendar))
            clean = part.loc[part.roll_clean]
            rolls.extend(dict(variant=variant, era=era, **row) for row in partition_rows(clean, calendar))
            availability.append(dict(variant=variant, era=era, baseline_trades=len(part), vwap_available_trades=int(part.vwap.notna().sum()),
                vwap_available_fraction=float(part.vwap.notna().mean()), roll_clean_trades=len(clean),
                common_full_cash_available_trades=len(common_tickets), common_full_cash_available_fraction=len(common_tickets)/len(part)))
            if variant in available_tickets:
                selected = part.loc[part.ticket.isin(common_tickets)]
                common.extend(dict(variant=variant, era=era, **row) for row in partition_rows(selected, calendar))
            for year in sorted(part.year.unique()):
                annual = part.loc[part.year.eq(year)]
                yearly.extend(dict(variant=variant, era=era, year=int(year), partial=bool(year == 2026), **row)
                              for row in partition_rows(annual, calendar[calendar.year == year]))
            for policy in POLICIES:
                rows, curves = policy_comparison(part, calendar, policy)
                policies.extend(dict(variant=variant, era=era, policy=policy, **row) for row in rows)
                sessions.extend(dict(variant=variant, era=era, policy=policy, **row) for row in curves)
                rows, _ = policy_comparison(clean, calendar, policy, with_sessions=False)
                roll_policies.extend(dict(variant=variant, era=era, policy=policy, **row) for row in rows)
            if variant != 'full_hlc3':
                continue
            rows, draw_frame, metadata = bootstrap(part, calendar, boot_rng)
            uncertainty.extend(dict(era=era, **row) for row in rows)
            draw_frame.insert(0, 'era', era)
            boot_draws.append(draw_frame)
            bootstrap_metadata[era] = metadata
            offsets = placement_rng.integers(0, len(part), size=SHIFTS)
            for policy in PRIMARY_POLICIES:
                draws, summary = placement(part, calendar, policy, offsets)
                draws.insert(0, 'policy', policy)
                draws.insert(0, 'era', era)
                shifts.append(draws)
                shift_summaries.append(dict(era=era, policy=policy, **summary))
                rows, summary = confounds(part, policy)
                strata.extend(dict(era=era, **row) for row in rows)
                confound_summaries.append(dict(era=era, **summary))
        print(f'Completed {era}: frozen variants, partitions, controls.', flush=True)
    policy_frame = pd.DataFrame(policies)
    screen = []
    for policy in PRIMARY_POLICIES:
        row, passed = dict(policy=policy), True
        for era in ERAS:
            group = policy_frame.loc[policy_frame.variant.eq('full_hlc3') & policy_frame.policy.eq(policy)
                                     & policy_frame.era.eq(era)].set_index('curve')
            retained, baseline, static = (group.loc[key] for key in ('retained', 'baseline', 'static_holding_scaled'))
            qualifies = bool(retained.skipped_net_dollars < 0 and retained.skipped_net_mean_r < 0
                and retained.skipped_trades >= 200 and retained.skipped_active_weeks >= 30
                and retained.daily_close_dd < baseline.daily_close_dd)
            row[f'{era}_negative_edge_core_passes'] = qualifies
            row[f'{era}_profit_delta'] = float(retained.net_dollars-baseline.net_dollars)
            row[f'{era}_daily_dd_reduction'] = float(baseline.daily_close_dd-retained.daily_close_dd)
            row[f'{era}_profit_advantage_vs_static'] = float(retained.net_dollars-static.net_dollars)
            row[f'{era}_daily_dd_advantage_vs_static'] = float(static.daily_close_dd-retained.daily_close_dd)
            passed &= qualifies
        row['negative_edge_core_both_eras'] = passed
        row['sensitivity_confound_interpretation_required'] = True
        row['adoption_authorized'] = False
        screen.append(row)
    outputs = {'summaries.csv': pd.DataFrame(summary_rows), 'yearly.csv': pd.DataFrame(yearly),
               'roll_summary.csv': pd.DataFrame(rolls), 'common_anchor_summary.csv': pd.DataFrame(common),
               'availability.csv': pd.DataFrame(availability), 'policies.csv': policy_frame,
               'roll_policies.csv': pd.DataFrame(roll_policies), 'policy_sessions.csv': pd.DataFrame(sessions),
               'uncertainty.csv': pd.DataFrame(uncertainty), 'bootstrap_draws.csv': pd.concat(boot_draws, ignore_index=True),
               'placement_draws.csv': pd.concat(shifts, ignore_index=True), 'placement_summary.csv': pd.DataFrame(shift_summaries),
               'confound_strata.csv': pd.DataFrame(strata), 'confound_summary.csv': pd.DataFrame(confound_summaries),
               'screen.csv': pd.DataFrame(screen)}
    for name, frame in outputs.items():
        frame.to_csv(OUT/name, index=False, float_format='%.15g')
    assert digest(PROTOCOL) == PROTOCOL_SHA256
    audit = dict(all_passed=True, primary_trades=16668, labelled_variant_rows=len(trades),
                 variants=list(VARIANTS), output_rows={name: len(frame) for name, frame in outputs.items()},
                 partitions_reconciled=True, source_baseline_economics_reconciled=True, bootstrap=bootstrap_metadata,
                 bootstrap_seed=20261025,
                 placement=dict(draws=SHIFTS, seed=20261026, offsets_shared_across_policies=True,
                                ranking='Actual minus own same-holding static baseline; larger is favorable for profit and DD advantages',
                                limitation='Circular trade-order shifts; not calendar duration, time-of-day or volatility matching'),
                 full_strategy_replay=False, strategy_changed=False)
    save_json(OUT/'economics_audit.json', audit)
    inputs = ['trades.csv', *(f'features_{variant}.csv' for variant in VARIANTS)]
    if (OUT/'feature_provenance.json').exists():
        inputs.append('feature_provenance.json')
    save_json(OUT/'economics_provenance.json', dict(study='RTL session VWAP attribution', protocol_sha256=PROTOCOL_SHA256,
        inputs_sha256={name: digest(OUT/name) for name in inputs}, program_sha256=digest(Path(__file__)),
        prior_metrics_program_sha256=digest(Path(prior.__file__)),
        outputs_sha256={name: digest(OUT/name) for name in [*outputs, 'economics_audit.json']},
        software=dict(numpy=np.__version__, pandas=pd.__version__), exploratory_only=True))
    print(policy_frame.loc[policy_frame.variant.eq('full_hlc3') & policy_frame.curve.eq('retained'),
          ['era', 'policy', 'trades', 'net_dollars', 'daily_close_dd', 'skipped_net_mean_r']].to_string(index=False))
    print(outputs['screen.csv'].to_string(index=False))
    print('Saved frozen VWAP economics and controls.', flush=True)


if __name__ == '__main__':
    main()
