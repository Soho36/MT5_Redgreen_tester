"""Frozen RTL MA-agreement economics and controls; ledger omission only."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_rtl_market_regimes as prior

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_ma_agreement_20261024'
PROTOCOL = ROOT / 'docs/baseline/rtl-ma-agreement/PROTOCOL.md'
PROTOCOL_SHA256 = '5241d5d396f03887c2139af0322a9a891980ef74b30b4b5d890947c5dd6e36ab'
VARIANTS = ('primary', 'loose', 'strict', 'zero_band', 'dense')
STATES = ('up', 'down', 'mixed')
POLICIES = ('skip_mixed', 'skip_down', 'only_up')
ERAS = prior.ERAS
DRAWS, SHIFTS = 10000, 2000


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def dates(frame, names):
    for name in names:
        if name in frame:
            frame[name] = pd.to_datetime(frame[name], format='ISO8601')
    return frame


def metrics(trades, calendar):
    result = prior.metrics(trades, calendar)
    result.update(winners=int(trades.net_dollars.gt(0).sum()),
                  losers=int(trades.net_dollars.lt(0).sum()),
                  positive_net_dollars=float(trades.net_dollars.clip(lower=0).sum()),
                  loss_dollars=float(-trades.net_dollars.clip(upper=0).sum()),
                  net_r_total=float(trades.net_r.sum()),
                  planned_risk_total=float(trades.initial_risk_dollars.sum()),
                  active_episodes=int(trades.episode_id.nunique()),
                  adequate_coverage=bool(len(trades) >= 200 and trades.week_start.nunique() >= 30))
    return result


def skip_mask(trades, policy):
    if policy == 'skip_mixed':
        return trades.state.eq('mixed').to_numpy()
    if policy == 'skip_down':
        return trades.state.eq('down').to_numpy()
    if policy == 'only_up':
        return trades.state.ne('up').to_numpy()
    raise ValueError(policy)


def max_dd(pnl):
    equity = np.r_[0., np.asarray(pnl).cumsum()]
    return float((np.maximum.accumulate(equity)-equity).max())


def daily_curve(trades, calendar):
    return trades.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.)


def policy_comparison(trades, calendar, policy):
    omitted_mask = skip_mask(trades, policy)
    retained, omitted = trades.loc[~omitted_mask], trades.loc[omitted_mask]
    fraction = float(retained.holding_minutes.sum()/trades.holding_minutes.sum())
    fractions = dict(skipped_trades=int(omitted_mask.sum()),
                     skipped_active_weeks=int(omitted.week_start.nunique()),
                     skipped_net_dollars=float(omitted.net_dollars.sum()),
                     skipped_net_mean_r=float(omitted.net_r.mean()),
                     losses_avoided=float(-omitted.net_dollars.clip(upper=0).sum()),
                     profits_missed=float(omitted.net_dollars.clip(lower=0).sum()),
                     retained_trade_fraction=float(len(retained)/len(trades)),
                     retained_holding_fraction=fraction,
                     retained_planned_risk_fraction=float(retained.initial_risk_dollars.sum()/trades.initial_risk_dollars.sum()))
    scaled = trades.copy()
    # Same-holding fractional sizing is a comparator, not a one-contract rule.
    for column in ('net_dollars', 'trade_profit', 'initial_risk_dollars', 'fill_risk_dollars',
                   'stress1_net_dollars', 'stress2_net_dollars', 'holding_minutes'):
        scaled[column] *= fraction
    rows, sessions = [], []
    for curve, frame in (('baseline', trades), ('retained', retained), ('static_holding_scaled', scaled)):
        rows.append(dict(curve=curve, **metrics(frame, calendar), **fractions,
                         pnl_scale=fraction if curve == 'static_holding_scaled' else 1.))
        sessions.extend(dict(curve=curve, session=date, net_dollars=float(pnl))
                        for date, pnl in daily_curve(frame, calendar).items())
    assert np.isclose(retained.net_dollars.sum()+omitted.net_dollars.sum(), trades.net_dollars.sum(), atol=1e-8)
    assert np.isclose(fractions['profits_missed']-fractions['losses_avoided'], fractions['skipped_net_dollars'], atol=1e-8)
    return rows, sessions


def bootstrap(trades, calendar, rng):
    first = calendar[0]-pd.Timedelta(days=calendar[0].dayofweek)
    last = calendar[-1]-pd.Timedelta(days=calendar[-1].dayofweek)
    weeks = pd.date_range(first, last, freq='7D')
    selected = []
    for state in STATES:
        values = trades.loc[trades.state.eq(state)].groupby('week_start').net_r.agg(['sum', 'count'])
        selected.append(values.reindex(weeks, fill_value=0.).to_numpy())
    data = np.stack(selected, axis=1)
    assert data[:, :, 1].sum() == len(trades)
    starts = rng.integers(0, len(weeks), size=(DRAWS, math.ceil(len(weeks)/4)))
    indices = ((starts[:, :, None]+np.arange(4)) % len(weeks)).reshape(DRAWS, -1)[:, :len(weeks)]
    sums = np.empty((DRAWS, len(STATES), 2))
    for offset in range(0, DRAWS, 100):
        sums[offset:offset+100] = data[indices[offset:offset+100]].sum(axis=1)
    total = sums.sum(axis=1)
    rows, draws = [], []
    for j, state in enumerate(STATES):
        numerator, count = sums[:, j, 0], sums[:, j, 1]
        other_sum, other_count = total[:, 0]-numerator, total[:, 1]-count
        means = np.divide(numerator, count, out=np.full(DRAWS, np.nan), where=count > 0)
        other_means = np.divide(other_sum, other_count, out=np.full(DRAWS, np.nan), where=other_count > 0)
        differences = means-other_means
        chosen, other = trades.loc[trades.state.eq(state)], trades.loc[trades.state.ne(state)]
        row = dict(group=state, trades=len(chosen), active_weeks=int(chosen.week_start.nunique()),
                   net_mean_r=float(chosen.net_r.mean()), complement_trades=len(other),
                   complement_net_mean_r=float(other.net_r.mean()),
                   difference_net_r=float(chosen.net_r.mean()-other.net_r.mean()),
                   valid_mean_draws=int(np.isfinite(means).sum()),
                   valid_difference_draws=int(np.isfinite(differences).sum()))
        for name, values in (('mean_net_r', means), ('difference_net_r', differences)):
            finite = values[np.isfinite(values)]
            for suffix, alpha in (('95', .05), ('98_33', .05/3)):
                low, high = np.quantile(finite, [alpha/2, 1-alpha/2], method='linear') if len(finite) else (np.nan, np.nan)
                row[f'{name}_ci{suffix}_low'] = float(low)
                row[f'{name}_ci{suffix}_high'] = float(high)
        rows.append(row)
        draws.append(pd.DataFrame(dict(group=state, draw=np.arange(DRAWS), selected_net_r=numerator,
            selected_trades=count.astype(int), complement_net_r=other_sum, complement_trades=other_count.astype(int),
            mean_net_r=means, difference_net_r=differences)))
    metadata = dict(draws=DRAWS, calendar_weeks=len(weeks), block_weeks=4, circular=True,
                    blocks_per_draw=math.ceil(len(weeks)/4), trimmed_weeks=len(weeks),
                    adjustment='Three primary state comparisons per era only; not all prior research')
    return rows, pd.concat(draws, ignore_index=True), metadata


def placement(trades, calendar, policy, offsets):
    trades = trades.sort_values(['entry_time', 'ticket'], kind='stable')
    skip = skip_mask(trades, policy)
    pnl, hours = trades.net_dollars.to_numpy(), trades.holding_minutes.to_numpy()/60
    day_ids = calendar.get_indexer(trades.session)
    assert (day_ids >= 0).all()
    actual = trades.loc[~skip]
    actual_net = float(actual.net_dollars.sum())
    actual_dd = max_dd(daily_curve(actual, calendar))
    actual_hours = float(actual.holding_minutes.sum()/60)
    rows = []
    for draw, offset in enumerate(offsets):
        keep = ~np.roll(skip, int(offset))
        kept_net, kept_hours = float(pnl[keep].sum()), float(hours[keep].sum())
        daily = np.bincount(day_ids[keep], weights=pnl[keep], minlength=len(calendar))
        dd = max_dd(daily)
        scale = actual_hours/kept_hours if kept_hours else np.nan
        rows.append(dict(draw=draw, offset=int(offset), retained_trades=int(keep.sum()),
                         net_dollars=kept_net, daily_close_dd=dd, holding_hours=kept_hours,
                         exposure_scale=float(scale), exposure_scaled_net_dollars=float(kept_net*scale),
                         exposure_scaled_daily_close_dd=float(dd*scale)))
    frame = pd.DataFrame(rows)
    summary = dict(draws=len(frame), actual_retained_net_dollars=actual_net, actual_daily_close_dd=actual_dd,
                   actual_holding_hours=actual_hours,
                   fraction_shifts_beaten_net=float(frame.net_dollars.lt(actual_net).mean()),
                   fraction_shifts_beaten_dd=float(frame.daily_close_dd.gt(actual_dd).mean()),
                   fraction_scaled_shifts_beaten_net=float(frame.exposure_scaled_net_dollars.lt(actual_net).mean()),
                   fraction_scaled_shifts_beaten_dd=float(frame.exposure_scaled_daily_close_dd.gt(actual_dd).mean()))
    for column in ('net_dollars', 'daily_close_dd', 'exposure_scaled_net_dollars', 'exposure_scaled_daily_close_dd'):
        for quantile in (.025, .5, .975):
            summary[f'{column}_q{int(quantile*1000)}'] = float(frame[column].quantile(quantile))
    return frame, summary


def load_inputs():
    assert digest(PROTOCOL) == PROTOCOL_SHA256
    feature_provenance = json.loads((OUT/'feature_provenance.json').read_text(encoding='utf-8'))
    recorded = feature_provenance['outputs_sha256']
    for name, expected in recorded.items():
        assert digest(OUT/name) == expected, name
    trades = dates(pd.read_csv(OUT/'trades.csv'), ['submitted', 'entry_time', 'exit_time', 'session',
        'week_start', 'available_at', 'bar_time', 'episode_start', 'next_up_at'])
    features = dates(pd.read_csv(OUT/'features.csv', usecols=['bar_time', 'available_at']), ['bar_time', 'available_at'])
    assert trades.groupby('variant').size().to_dict() == {name: 16668 for name in VARIANTS}
    assert not trades.duplicated(['variant', 'ticket']).any()
    assert trades.valid.all() and trades.state.isin(STATES).all()
    assert trades.available_at.le(trades.submitted).all()
    for variant in VARIANTS:
        part = trades.loc[trades.variant.eq(variant)]
        assert part.groupby('era').size().to_dict() == {'2016-19': 6167, '2020-26': 10501}
        assert np.isclose(part.loc[part.era.eq('2016-19'), 'net_dollars'].sum(), 4416.65, atol=1e-8)
        assert np.isclose(part.loc[part.era.eq('2020-26'), 'net_dollars'].sum(), 38399.95, atol=1e-8)
        assert np.allclose(part.net_dollars, part.trade_profit-1.05, atol=1e-10, rtol=0)
        assert np.allclose(part.net_r, part.net_dollars/part.initial_risk_dollars, atol=1e-12, rtol=0)
    return trades, pd.DatetimeIndex(features.bar_time.dt.normalize().unique()).sort_values()


def main():
    trades, calendar_all = load_inputs()
    summary_rows, yearly, rolls, policies, sessions, uncertainty = [], [], [], [], [], []
    boot_draws, shifts, shift_summaries, bootstrap_metadata = [], [], [], {}
    boot_rng, placement_rng = np.random.default_rng(20261024), np.random.default_rng(20261025)
    for era, (start, stop) in ERAS.items():
        calendar = calendar_all[(calendar_all >= start) & (calendar_all < stop)]
        for variant in VARIANTS:
            part = trades.loc[trades.era.eq(era) & trades.variant.eq(variant)].copy()
            assert part.session.isin(calendar).all()
            for state in ('all', *STATES):
                selected = part if state == 'all' else part.loc[part.state.eq(state)]
                summary_rows.append(dict(variant=variant, era=era, dimension='state', category=state,
                                         **metrics(selected, calendar)))
                clean = selected.loc[selected.roll_clean]
                rolls.append(dict(variant=variant, era=era, state=state, **metrics(clean, calendar)))
                for year in sorted(part.year.unique()):
                    annual = selected.loc[selected.year.eq(year)]
                    yearly.append(dict(variant=variant, era=era, year=int(year), partial=bool(year == 2026),
                                       state=state, **metrics(annual, calendar[calendar.year == year])))
            for policy in POLICIES:
                rows, curves = policy_comparison(part, calendar, policy)
                policies.extend(dict(variant=variant, era=era, policy=policy, **row) for row in rows)
                sessions.extend(dict(variant=variant, era=era, policy=policy, **row) for row in curves)
            if variant != 'primary':
                continue
            part['context_state'] = part.context+'|'+part.state
            part['state_age'] = part.state+'|'+part.age_bin
            part['firstup_timing_state'] = part.firstup_timing+'|'+part.state
            # Causal age is reported with the state immediately preceding up.
            part['up_reentry_age_detail'] = np.where(part.state.eq('up'),
                part.prior_state.astype(str)+'|'+part.up_reentry_age.astype(str), 'not_up')
            dimensions = {'context': 'context', 'context_state': 'context_state', 'state_age': 'state_age',
                          'fill_state': 'fill_state', 'exit_state': 'exit_state',
                          'firstup_timing_state': 'firstup_timing_state',
                          'up_reentry_age': 'up_reentry_age_detail'}
            for dimension, column in dimensions.items():
                counts, dollars, net_r = 0, 0., 0.
                for category, selected in part.groupby(column, dropna=False, sort=True):
                    summary_rows.append(dict(variant=variant, era=era, dimension=dimension, category=str(category),
                                             **metrics(selected, calendar)))
                    counts += len(selected)
                    dollars += selected.net_dollars.sum()
                    net_r += selected.net_r.sum()
                assert counts == len(part)
                assert np.isclose(dollars, part.net_dollars.sum(), atol=1e-8)
                assert np.isclose(net_r, part.net_r.sum(), atol=1e-10)
            rows, draw_frame, meta = bootstrap(part, calendar, boot_rng)
            uncertainty.extend(dict(era=era, **row) for row in rows)
            draw_frame.insert(0, 'era', era)
            boot_draws.append(draw_frame)
            bootstrap_metadata[era] = meta
            offsets = placement_rng.integers(0, len(part), size=SHIFTS)
            for policy in POLICIES:
                draws, summary = placement(part, calendar, policy, offsets)
                draws.insert(0, 'policy', policy)
                draws.insert(0, 'era', era)
                shifts.append(draws)
                shift_summaries.append(dict(era=era, policy=policy, **summary))
        print(f'Completed {era}: all frozen variants, policies and primary controls.', flush=True)
    policy_frame = pd.DataFrame(policies)
    screen = []
    for policy in POLICIES:
        row = dict(policy=policy)
        passed = True
        for era in ERAS:
            group = policy_frame.loc[policy_frame.variant.eq('primary') & policy_frame.policy.eq(policy)
                                     & policy_frame.era.eq(era)].set_index('curve')
            retained, baseline = group.loc['retained'], group.loc['baseline']
            qualifies = bool(retained.skipped_net_dollars < 0 and retained.skipped_net_mean_r < 0
                and retained.skipped_trades >= 200 and retained.skipped_active_weeks >= 30
                and retained.daily_close_dd < baseline.daily_close_dd)
            row[f'{era}_passes'] = qualifies
            passed &= qualifies
        row['warrants_followup_replay'] = passed
        screen.append(row)
    outputs = {'summaries.csv': pd.DataFrame(summary_rows), 'yearly.csv': pd.DataFrame(yearly),
               'roll_summary.csv': pd.DataFrame(rolls), 'policies.csv': policy_frame,
               'policy_sessions.csv': pd.DataFrame(sessions), 'uncertainty.csv': pd.DataFrame(uncertainty),
               'bootstrap_draws.csv': pd.concat(boot_draws, ignore_index=True),
               'placement_draws.csv': pd.concat(shifts, ignore_index=True),
               'placement_summary.csv': pd.DataFrame(shift_summaries), 'screen.csv': pd.DataFrame(screen)}
    for name, frame in outputs.items():
        frame.to_csv(OUT/name, index=False, float_format='%.15g')
    assert digest(PROTOCOL) == PROTOCOL_SHA256
    audit = dict(all_passed=True, primary_trades=16668, labelled_variant_rows=len(trades),
                 variants=list(VARIANTS), summary_rows=len(summary_rows), yearly_rows=len(yearly),
                 roll_summary_rows=len(rolls), policy_rows=len(policy_frame),
                 primary_uncertainty_rows=len(uncertainty), bootstrap_draw_rows=sum(map(len, boot_draws)),
                 placement_draw_rows=sum(map(len, shifts)), partitions_reconciled=True,
                 source_baseline_economics_reconciled=True, bootstrap=bootstrap_metadata,
                 placement=dict(draws=SHIFTS, seed=20261025, offsets_shared_across_policies=True,
                                limitation='Circular trade-order shifts; not calendar or volatility matching'),
                 full_strategy_replay=False, strategy_changed=False)
    save_json(OUT/'audit.json', audit)
    save_json(OUT/'provenance.json', dict(study='RTL MA slope agreement', protocol_sha256=PROTOCOL_SHA256,
        inputs_sha256={name: digest(OUT/name) for name in ['feature_provenance.json', 'features.csv', 'trades.csv']},
        program_sha256=digest(Path(__file__)), prior_metrics_program_sha256=digest(Path(prior.__file__)),
        outputs_sha256={name: digest(OUT/name) for name in [*outputs, 'audit.json']},
        software=dict(numpy=np.__version__, pandas=pd.__version__), exploratory_only=True))
    print(outputs['summaries.csv'].loc[lambda f: f.variant.eq('primary') & f.dimension.eq('state'),
          ['era', 'category', 'trades', 'net_dollars', 'net_mean_r', 'daily_close_dd']].to_string(index=False))
    print(outputs['screen.csv'].to_string(index=False))
    print('Saved frozen MA economics and controls.', flush=True)


if __name__ == '__main__':
    main()
