"""Attribute existing RTL structure flags; no new classifier or trading rule.

Frozen episode protocol: historical phases are retrospective, all range and
age fields use only candles completed when the order was submitted.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'Reports/rtl_price_structure_20261024'
RAW_DIR = ROOT / 'Reports/timeframe_baseline_20261015'
STUDY = ROOT / 'Reports/rtl_flagged_episodes_20261024'
PROTOCOL = ROOT / 'docs/baseline/rtl-price-structure/EPISODE_PROTOCOL.md'
PROTOCOL_SHA256 = '541a408b5fdc474dfb22478bd50f75f4dbd011c7e9f3474c30ab497f2cc66b12'
END = pd.Timestamp('2026-10-01')
ERAS = {'2016-19': ('2016-01-01', '2020-01-01'),
        '2020-26': ('2020-01-01', '2026-10-01')}
FLAGS = {'d1_main': ('d1', 'low_eff_high_overlap'),
         'm30_main': ('m30', 'low_eff_high_overlap'),
         'm30_broad_wick': ('m30', 'high_overlap_high_wick'),
         'm30_triple': ('m30', 'low_eff_high_overlap_high_wick')}
WINDOWS = (10, 20, 40)
DIMENSIONS = ('retrospective_phase', 'causal_age_bin', 'path_group',
              'fill_episode_state', 'exit_episode_state', 'fill_location',
              'exit_location', 'phase_x_path')


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def flag_mask(features, flag):
    valid = features.valid
    if flag in ('d1_main', 'm30_main'):
        return valid & features.low_eff & features.high_overlap
    if flag == 'm30_broad_wick':
        return valid & features.high_overlap & features.high_wick
    if flag == 'm30_triple':
        return valid & features.low_eff & features.high_overlap & features.high_wick
    raise ValueError(flag)


def build_episodes(features, mask, coverage_end=END):
    """Consecutive observed valid TRUE bars; invalid rows censor both sides.

    The interval covered by a panel ends at coverage_end. Its last completed
    observation remains available until then (especially for D1 labels).
    """
    rows = features.sort_values('available_at', kind='stable').reset_index(drop=True).copy()
    assert (rows.available_at < coverage_end).all()
    assert rows.available_at.is_unique
    flag = np.array(mask, dtype=bool, copy=True)
    assert len(flag) == len(rows)
    # Callers provide mask in the same already-sorted order as features.
    assert features.available_at.is_monotonic_increasing
    flag &= rows.valid.to_numpy(dtype=bool)
    starts = flag & ~np.r_[False, flag[:-1]]
    ids = np.where(flag, np.cumsum(starts), 0)
    rows['flagged'] = flag
    rows['episode_id'] = ids
    rows['episode_age'] = 0
    inventory = []
    for episode_id, selected in rows.loc[rows.flagged].groupby('episode_id', sort=True):
        first, last = int(selected.index[0]), int(selected.index[-1])
        left_censored = first == 0 or not (rows.loc[first-1, 'valid'] and not flag[first-1])
        right_censored = last+1 == len(rows) or not (rows.loc[last+1, 'valid'] and not flag[last+1])
        first_clear = pd.NaT if right_censored else rows.loc[last+1, 'available_at']
        start = rows.loc[first, 'available_at']
        last_true = rows.loc[last, 'available_at']
        observed_end = (rows.loc[last+1, 'available_at'] if last+1 < len(rows) else coverage_end)
        length = len(selected)
        rows.loc[selected.index, 'episode_age'] = np.arange(1, length+1)
        inventory.append(dict(episode_id=int(episode_id), start=start, last_true=last_true,
                              first_clear=first_clear, length=length,
                              left_censored=bool(left_censored), right_censored=bool(right_censored),
                              observed_end=observed_end,
                              elapsed_hours=(observed_end-start).total_seconds()/3600,
                              observed_span_hours=(last_true-start).total_seconds()/3600))
    columns = ['episode_id', 'start', 'last_true', 'first_clear', 'length', 'left_censored',
               'right_censored', 'observed_end', 'elapsed_hours', 'observed_span_hours']
    episodes = pd.DataFrame(inventory, columns=columns)
    rows = rows.merge(episodes, on='episode_id', how='left', validate='many_to_one')
    return rows, episodes


def endpoint_location(price, high, low):
    return np.where(np.asarray(price) > np.asarray(high), 'above',
                    np.where(np.asarray(price) < np.asarray(low), 'below', 'inside'))


def path_groups(maximum, minimum, high, low):
    upper, lower = np.asarray(maximum) > np.asarray(high), np.asarray(minimum) < np.asarray(low)
    return np.where(upper, np.where(lower, 'both', 'upper_only'),
                    np.where(lower, 'lower_only', 'contained'))


def endpoint_states(trades, labelled, timestamp, coverage_end=END):
    """Literal asof state, including reflagging as a different episode."""
    columns = ['available_at', 'valid', 'flagged', 'episode_id']
    right = labelled[columns].rename(columns={x: 'asof_'+x for x in columns})
    left = trades[[timestamp, 'episode_id']].copy()
    left['_order'] = np.arange(len(left))
    joined = pd.merge_asof(left.sort_values(timestamp, kind='stable'), right,
                           left_on=timestamp, right_on='asof_available_at', direction='backward',
                           allow_exact_matches=True).sort_values('_order')
    known = (joined.asof_valid.eq(True) & joined[timestamp].lt(coverage_end)
             & joined[timestamp].ge(labelled.available_at.iloc[0]))
    state = np.where(~known, 'unknown',
                     np.where(~joined.asof_flagged.eq(True), 'unflagged',
                              np.where(joined.episode_id.eq(joined.asof_episode_id),
                                       'same_episode', 'later_episode')))
    return pd.DataFrame({'state': state, 'available_at': joined.asof_available_at.to_numpy(),
                         'episode_id': joined.asof_episode_id.to_numpy()}, index=trades.index)


def attribute_trades(trades, labelled, inventory, n, coverage_end=END):
    """All supplied trades are eligible; return those flagged at submission."""
    rows = labelled.copy()
    rows['range_high'] = rows.high.rolling(n, min_periods=n).max()
    rows['range_low'] = rows.low.rolling(n, min_periods=n).min()
    rows['range_start'] = rows.bar_time.shift(n-1)
    columns = ['available_at', 'bar_time', 'valid', 'flagged', 'episode_id', 'episode_age',
               'start', 'last_true', 'first_clear', 'length', 'left_censored', 'right_censored',
               'range_high', 'range_low', 'range_start']
    result = pd.merge_asof(trades.sort_values(['submitted', 'ticket'], kind='stable'), rows[columns],
                           left_on='submitted', right_on='available_at', direction='backward',
                           allow_exact_matches=True)
    result = result.loc[result.flagged.eq(True)].copy().reset_index(drop=True)
    assert result.valid.all() and result.range_high.notna().all()
    assert (result.available_at <= result.submitted).all()
    assert result.submitted.lt(coverage_end).all()
    assert result.episode_id.isin(inventory.episode_id).all()
    q = (result.episode_age-.5)/result.length
    result['retrospective_phase'] = np.where(result.left_censored | result.right_censored, 'censored',
        np.where(result.length.lt(3), 'short_episode',
                 np.where(q.le(1/3), 'early', np.where(q.le(2/3), 'middle', 'late'))))
    result['causal_age_bin'] = np.where(result.episode_age.eq(1), '1',
        np.where(result.episode_age.le(3), '2-3', np.where(result.episode_age.le(8), '4-8', '9+')))
    result['sampled_max_price'] = result.fill_price + result.mfe_money/2
    result['sampled_min_price'] = result.fill_price + result.mae_money/2
    assert (result.sampled_max_price >= result.exit_price).all()
    assert (result.sampled_min_price <= result.exit_price).all()
    assert (result.sampled_max_price >= result.sampled_min_price).all()
    result['path_group'] = path_groups(result.sampled_max_price, result.sampled_min_price,
                                      result.range_high, result.range_low)
    for name, time_column, price_column in [('fill', 'entry_time', 'fill_price'),
                                           ('exit', 'exit_time', 'exit_price')]:
        state = endpoint_states(result, rows, time_column, coverage_end)
        result[name+'_episode_state'] = state.state
        result[name+'_asof_available_at'] = state.available_at
        result[name+'_asof_episode_id'] = state.episode_id
        result[name+'_location'] = endpoint_location(result[price_column], result.range_high, result.range_low)
        # Missing first_clear means censored/unknown, rather than False.
        after = result[time_column].ge(result.first_clear).astype('boolean')
        after.loc[result.first_clear.isna()] = pd.NA
        result[name+'_at_or_after_clear'] = after
    result['submission_delay_minutes'] = (result.entry_time-result.submitted).dt.total_seconds()/60
    assert result.submission_delay_minutes.ge(0).all()
    result['headroom_r'] = (result.range_high-result.requested_price)/(result.requested_price-result.original_sl)
    result['phase_x_path'] = result.retrospective_phase + ' | ' + result.path_group
    return result


def metrics(trades, positive_total=None, loss_total=None):
    positive = float(trades.net_dollars.clip(lower=0).sum())
    loss = float(-trades.net_dollars.clip(upper=0).sum())
    positive_total = positive if positive_total is None else positive_total
    loss_total = loss if loss_total is None else loss_total
    return dict(trades=len(trades), winners=int(trades.net_dollars.gt(0).sum()),
                losers=int(trades.net_dollars.lt(0).sum()), breakeven=int(trades.net_dollars.eq(0).sum()),
                active_episodes=int(trades.episode_id.nunique()), active_sessions=int(trades.session.nunique()),
                active_weeks=int(trades.week_start.nunique()), gross_dollars=float(trades.trade_profit.sum()),
                net_dollars=float(trades.net_dollars.sum()), positive_net_dollars=positive, loss_dollars=loss,
                net_r_total=float(trades.net_r.sum()), net_mean_r=float(trades.net_r.mean()) if len(trades) else np.nan,
                dollar_pf=positive/loss if loss else np.nan,
                winning_dollars_share=positive/positive_total if positive_total else np.nan,
                losing_dollars_share=loss/loss_total if loss_total else np.nan,
                holding_hours=float(trades.holding_minutes.sum()/60),
                mean_holding_minutes=float(trades.holding_minutes.mean()) if len(trades) else np.nan,
                mean_submission_delay_minutes=float(trades.submission_delay_minutes.mean()) if len(trades) else np.nan,
                median_submission_delay_minutes=float(trades.submission_delay_minutes.median()) if len(trades) else np.nan,
                mean_headroom_r=float(trades.headroom_r.mean()) if len(trades) else np.nan)


def summaries_for(trades, flag, timeframe, n):
    rows = []
    for era in ERAS:
        whole = trades.loc[trades.era.eq(era)]
        pos, loss = float(whole.net_dollars.clip(lower=0).sum()), float(-whole.net_dollars.clip(upper=0).sum())
        common = dict(flag=flag, timeframe=timeframe, window=n, era=era)
        rows.append(dict(**common, dimension='all', category='all', **metrics(whole, pos, loss)))
        for dimension in DIMENSIONS:
            groups = []
            for category, part in whole.groupby(dimension, sort=True, dropna=False):
                row = dict(**common, dimension=dimension, category=category, **metrics(part, pos, loss))
                rows.append(row)
                groups.append(row)
            assert sum(x['trades'] for x in groups) == len(whole)
            for field, expected in [('net_dollars', whole.net_dollars.sum()),
                                    ('gross_dollars', whole.trade_profit.sum()),
                                    ('net_r_total', whole.net_r.sum()),
                                    ('positive_net_dollars', pos), ('loss_dollars', loss)]:
                assert np.isclose(sum(x[field] for x in groups), expected, atol=1e-8, rtol=1e-12), (flag, n, era, dimension, field)
    return rows


def episode_pnl(inventory, trades):
    columns = ['episode_id', 'trades', 'winners', 'losers', 'gross_dollars', 'net_dollars',
               'positive_net_dollars', 'loss_dollars', 'net_r_total']
    values = [dict(episode_id=episode_id, **{k: v for k, v in metrics(part).items() if k in columns})
              for episode_id, part in trades.groupby('episode_id', sort=True)]
    pnl = pd.DataFrame(values, columns=columns)
    out = inventory.merge(pnl, on='episode_id', how='left', validate='one_to_one')
    for column in columns[1:]:
        out[column] = out[column].fillna(0)
    for column in ('trades', 'winners', 'losers'):
        out[column] = out[column].astype(int)
    return out


def check_inputs():
    assert digest(PROTOCOL) == PROTOCOL_SHA256
    prior = json.loads((SOURCE/'provenance.json').read_text(encoding='utf-8'))
    paths = [PROTOCOL, SOURCE/'provenance.json', Path(__file__)]
    names = [f'features_{tf}_{n}.csv' for tf in ('d1', 'm30') for n in WINDOWS]
    names += ['trades.csv', 'thresholds.csv', 'summaries.csv', 'named_wick_summary.csv']
    for name in names:
        path = SOURCE/name
        assert digest(path) == prior['outputs_sha256'][name], f'Changed prior output: {path}'
        paths.append(path)
    for name in ('manifest.json', 'runband_tf_20261015_rtl_m30_rr1p0_1.00.csv'):
        path = RAW_DIR/name
        assert digest(path) == prior['inputs_sha256'][str(path)]
        paths.append(path)
    manifest = json.loads((RAW_DIR/'manifest.json').read_text(encoding='utf-8'))
    ea = RAW_DIR/'RTL_timeframe.mq5'
    assert digest(ea) == manifest['prepared_sha256']['RTL_timeframe.mq5']
    paths.append(ea)
    return {str(path): digest(path) for path in paths}


def load_trades():
    dates = ['submitted', 'entry_time', 'exit_time', 'session', 'week_start']
    trades = pd.read_csv(SOURCE/'trades.csv', parse_dates=dates)
    raw = pd.read_csv(RAW_DIR/'runband_tf_20261015_rtl_m30_rr1p0_1.00.csv', sep='\t', encoding='utf-16')
    assert len(trades) == len(raw) == 25833 and raw.ticket.is_unique and trades.ticket.is_unique
    raw['entry_time'] = pd.to_datetime(raw.entry_time, format='%Y.%m.%d %H:%M:%S')
    raw['exit_time'] = pd.to_datetime(raw.exit_time, format='%Y.%m.%d %H:%M:%S')
    joined = trades.merge(raw[['ticket', 'entry_time', 'exit_time', 'trade_profit', 'mae_money', 'mfe_money']],
                           on='ticket', how='left', suffixes=('', '_raw'), validate='one_to_one')
    for field in ('entry_time', 'exit_time', 'trade_profit'):
        assert joined[field].equals(joined[field+'_raw']), field
    joined = joined.drop(columns=[x+'_raw' for x in ('entry_time', 'exit_time', 'trade_profit')])
    assert np.allclose(joined.trade_profit, (joined.exit_price-joined.fill_price)*2, atol=1e-9, rtol=0)
    assert np.allclose(joined.net_dollars, joined.trade_profit-1.05, atol=1e-9, rtol=0)
    assert np.allclose(joined.net_r, joined.net_dollars/joined.initial_risk_dollars, atol=1e-12, rtol=0)
    maximum = joined.fill_price+joined.mfe_money/2
    minimum = joined.fill_price+joined.mae_money/2
    assert maximum.ge(joined.exit_price).all() and minimum.le(joined.exit_price).all()
    assert maximum.ge(minimum).all()
    primary = joined.loc[joined.primary].copy()
    assert primary.groupby('era').size().to_dict() == {'2016-19': 6167, '2020-26': 10501}
    assert primary[['submitted', 'entry_time', 'exit_time']].lt(END).all().all()
    return primary


def main():
    hashes = check_inputs()
    trades = load_trades()
    thresholds = pd.read_csv(SOURCE/'thresholds.csv')
    prior_summaries = pd.concat([pd.read_csv(SOURCE/'summaries.csv'), pd.read_csv(SOURCE/'named_wick_summary.csv')])
    STUDY.mkdir(parents=True, exist_ok=True)
    all_attribution, all_episodes, all_episode_era, all_summaries, reconciliation = [], [], [], [], []
    for n in WINDOWS:
        for timeframe in ('d1', 'm30'):
            features = pd.read_csv(SOURCE/f'features_{timeframe}_{n}.csv',
                                   parse_dates=['bar_time', 'available_at', 'history_start', 'last_bar_time'])
            features = features.loc[features.available_at.lt(END)].reset_index(drop=True)
            cut = thresholds.loc[thresholds.timeframe.eq(timeframe) & thresholds.window.eq(n)].iloc[0]
            # Tolerance is deliberately not used to alter frozen labels: verify exact decisions.
            assert features.low_eff.equals(features.efficiency.le(cut.efficiency_low) & features.valid)
            assert features.high_overlap.equals(features.overlap.ge(cut.overlap_high) & features.valid)
            assert features.high_wick.equals(features.wick.ge(cut.wick_high) & features.valid)
            for flag, (flag_timeframe, prior_group) in FLAGS.items():
                if flag_timeframe != timeframe:
                    continue
                labelled, inventory = build_episodes(features, flag_mask(features, flag))
                attribution = attribute_trades(trades, labelled, inventory, n)
                prefix = f'{timeframe}_{n}_'
                expected = trades[prefix+'valid'] & trades[prefix+'high_overlap']
                if flag != 'm30_broad_wick':
                    expected &= trades[prefix+'low_eff']
                if flag in ('m30_broad_wick', 'm30_triple'):
                    expected &= trades[prefix+'high_wick']
                assert set(attribution.ticket) == set(trades.loc[expected, 'ticket'])
                assert (attribution.available_at == attribution[prefix+'available_at'].astype('datetime64[us]')).all()
                all_summaries.extend(summaries_for(attribution, flag, timeframe, n))
                for era in ERAS:
                    part = attribution.loc[attribution.era.eq(era)]
                    old = prior_summaries.loc[prior_summaries.timeframe.eq(timeframe) & prior_summaries.window.eq(n)
                        & prior_summaries.era.eq(era) & prior_summaries.group.eq(prior_group)].iloc[0]
                    assert len(part) == old.trades
                    assert np.isclose(part.net_dollars.sum(), old.net_dollars, atol=1e-8, rtol=0)
                    assert np.isclose(part.net_r.sum(), old.net_mean_r*old.trades, atol=1e-9, rtol=0)
                    reconciliation.append(dict(flag=flag, timeframe=timeframe, window=n, era=era,
                                               trades=len(part), net_dollars=float(part.net_dollars.sum()),
                                               prior_net_dollars=float(old.net_dollars), passed=True))
                attribution.insert(0, 'window', n)
                attribution.insert(0, 'timeframe', timeframe)
                attribution.insert(0, 'flag', flag)
                all_attribution.append(attribution)
                inv = episode_pnl(inventory, attribution)
                inv.insert(0, 'window', n)
                inv.insert(0, 'timeframe', timeframe)
                inv.insert(0, 'flag', flag)
                all_episodes.append(inv)
                for era, (start, stop) in ERAS.items():
                    relevant = inventory.loc[inventory.start.lt(stop) & inventory.observed_end.gt(start)]
                    inv_era = episode_pnl(relevant, attribution.loc[attribution.era.eq(era)])
                    inv_era.insert(0, 'era', era)
                    inv_era.insert(0, 'window', n)
                    inv_era.insert(0, 'timeframe', timeframe)
                    inv_era.insert(0, 'flag', flag)
                    assert inv_era.trades.sum() == len(attribution.loc[attribution.era.eq(era)])
                    all_episode_era.append(inv_era)
    outputs = {'attribution.csv': pd.concat(all_attribution, ignore_index=True),
               'episodes.csv': pd.concat(all_episodes, ignore_index=True),
               'episode_era.csv': pd.concat(all_episode_era, ignore_index=True),
               'summaries.csv': pd.DataFrame(all_summaries), 'reconciliation.csv': pd.DataFrame(reconciliation)}
    # Exclude redundant original feature-label columns while retaining the raw
    # economic ledger and all new attribution fields.
    redundant = [column for column in outputs['attribution.csv'].columns
                 if column.startswith(('d1_', 'm30_'))]
    outputs['attribution.csv'] = outputs['attribution.csv'].drop(columns=redundant)
    for name, frame in outputs.items():
        frame.to_csv(STUDY/name, index=False, float_format='%.15g')
    assert digest(PROTOCOL) == PROTOCOL_SHA256
    audit = dict(all_passed=True, source_trades=25833, eligible_trades=len(trades),
                 attribution_rows=len(outputs['attribution.csv']), specifications=len(FLAGS)*len(WINDOWS),
                 era_reconciliations=len(reconciliation), exact_existing_submission_flags=True,
                 all_summary_partitions_reconciled=True, raw_extrema_and_exit_gross_reconciled=True,
                 original_source_ea_manifest_hash_verified=True, features_available_strictly_before=str(END),
                 episode_phase='Retrospective only; invalid boundaries censor runs.',
                 range='Last n completed candles, frozen at submission; efficiency uses one extra close.',
                 extrema='Recorded tester POSITION_PROFIT bounds including realized gross exit; no zero clamping.',
                 coverage='Last known label held until study cutoff; invalid row or outside cutoff is unknown.',
                 observed_end='Next observation availability, including invalid break, or study cutoff.',
                 episode_inventory='Full available history; PnL only eligible 2016-September2026 submissions.',
                 selected_count=sum(x['trades'] for x in reconciliation), strategy_changed=False)
    save_json(STUDY/'audit.json', audit)
    save_json(STUDY/'provenance.json', dict(study='RTL flagged-episode profit attribution',
        protocol_sha256=PROTOCOL_SHA256, inputs_sha256=hashes,
        outputs_sha256={name: digest(STUDY/name) for name in [*outputs, 'audit.json']},
        software=dict(numpy=np.__version__, pandas=pd.__version__), primary_eras=ERAS,
        exploratory_only=True, strategy_changed=False, baseline_mutated=False))
    print('All frozen inputs, 16,668 eligible trades, raw gross/extrema, and attribution partitions verified.', flush=True)
    summary = outputs['summaries.csv']
    print(summary.loc[summary.window.eq(20) & summary.dimension.isin(['all', 'path_group', 'fill_episode_state']),
                      ['flag', 'era', 'dimension', 'category', 'trades', 'net_dollars',
                       'positive_net_dollars', 'loss_dollars']].to_string(index=False), flush=True)
    print(f'Wrote {len(outputs)} CSV files, audit and provenance to {STUDY}', flush=True)


if __name__ == '__main__':
    main()
