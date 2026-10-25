"""Frozen RTL MA agreement features and event attribution, without outcome selection."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'Reports/rtl_price_structure_20261024'
OUT = ROOT / 'Reports/rtl_ma_agreement_20261024'
PROTOCOL = ROOT / 'docs/baseline/rtl-ma-agreement/PROTOCOL.md'
PROTOCOL_SHA256 = '5241d5d396f03887c2139af0322a9a891980ef74b30b4b5d890947c5dd6e36ab'
END = pd.Timestamp('2026-10-01')
CALIBRATION_END = pd.Timestamp('2016-01-01')
PRIMARY = (5, 10, 20, 40, 80, 160, 200)
DENSE = tuple(range(5, 201, 5))
VARIANTS = {'primary': (PRIMARY, 5, False), 'loose': (PRIMARY, 4, False),
            'strict': (PRIMARY, 6, False), 'zero_band': (PRIMARY, 5, True),
            'dense': (DENSE, 29, False)}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def age_bins(age):
    age = np.asarray(age)
    return np.where(age <= 0, 'unknown', np.where(age == 1, '1',
                    np.where(age <= 3, '2-3', np.where(age <= 8, '4-8', '9+'))))


def compute_features(bars):
    """Observed-bar features; return common-valid slopes and pre-2016 cutoffs."""
    columns = ['bar_time', 'available_at', 'open', 'high', 'low', 'close', 'switch_bar']
    f = bars[columns].sort_values('available_at', kind='stable').reset_index(drop=True).copy()
    assert f.available_at.is_unique
    assert (f.available_at == f.bar_time + pd.Timedelta(minutes=30)).all()
    f['row_index'] = np.arange(len(f))
    prev = f.close.shift()
    f['TR'] = pd.concat([f.high-f.low, (f.high-prev).abs(), (f.low-prev).abs()], axis=1).max(axis=1)
    # No first-bar true range: its previous close does not exist.
    f.loc[prev.isna(), 'TR'] = np.nan
    f.loc[~np.isfinite(f[['high', 'low', 'close']]).all(axis=1), 'TR'] = np.nan
    f['a20'] = f.TR.rolling(20, min_periods=20).mean()
    f['history_start'] = f.bar_time.shift(200)
    complete = np.isfinite(f.close).astype(int).rolling(201, min_periods=201).sum().eq(201)
    f['valid'] = complete & np.isfinite(f.a20) & f.a20.gt(0)
    f['roll_clean'] = f.valid & f.switch_bar.astype(int).rolling(201, min_periods=201).sum().eq(0)
    for length in DENSE:
        f[f'z_{length}'] = ((f.close-f.close.shift(length))/length/f.a20).where(f.valid)
    calibration = f.valid & f.available_at.lt(CALIBRATION_END)
    if not calibration.any():
        raise ValueError('No common-valid pre-2016 calibration rows.')
    cutoffs = pd.DataFrame([{'L': length,
                            'cutoff': f.loc[calibration, f'z_{length}'].abs().quantile(.2, interpolation='linear'),
                            'calibration_observations': int(calibration.sum())}
                           for length in DENSE])
    return f, cutoffs


def votes(values, cutoffs):
    """Strict boundaries, exact equality flat; input rows are already valid."""
    return np.where(values > cutoffs, 1, np.where(values < -cutoffs, -1, 0))


def band_direction(vote_array):
    return np.where((vote_array == 1).sum(axis=1) >= 2, 'up',
                    np.where((vote_array == -1).sum(axis=1) >= 2, 'down', 'mixed'))


def classify(features, cutoffs, variant):
    lengths, requirement, zero = VARIANTS[variant]
    f = features
    cut = cutoffs.set_index('L').cutoff
    values = f[[f'z_{length}' for length in lengths]].to_numpy()
    limits = np.zeros(len(lengths)) if zero else cut.loc[list(lengths)].to_numpy()
    v = votes(values, limits)
    valid = f.valid.to_numpy(dtype=bool)
    v[~valid] = 0
    result = f[['row_index', 'bar_time', 'available_at', 'close', 'a20',
                'valid', 'history_start', 'roll_clean']].copy()
    result.insert(0, 'variant', variant)
    result['up_votes'] = (v == 1).sum(axis=1)
    result['down_votes'] = (v == -1).sum(axis=1)
    result['flat_votes'] = np.where(valid, (v == 0).sum(axis=1), 0)
    result['breadth'] = np.where(valid, (result.up_votes-result.down_votes)/len(lengths), np.nan)
    result['state'] = np.where(~valid, 'unknown', np.where(result.up_votes >= requirement, 'up',
                                  np.where(result.down_votes >= requirement, 'down', 'mixed')))
    # All variants retain this same PRIMARY-band context, not variant-specific votes.
    pv = votes(f[[f'z_{length}' for length in PRIMARY]].to_numpy(), cut.loc[list(PRIMARY)].to_numpy())
    result['short_direction'] = np.where(valid, band_direction(pv[:, :3]), 'unknown')
    result['long_direction'] = np.where(valid, band_direction(pv[:, -3:]), 'unknown')
    result['context'] = np.where(valid, 'short_' + result.short_direction + '_long_' + result.long_direction, 'unknown')
    return result


def build_state_episodes(states, coverage_end=END):
    """Maximal valid same-state runs, with causal observed-row ages."""
    rows = states.reset_index(drop=True).copy()
    valid = rows.valid.to_numpy(dtype=bool)
    state = rows.state.to_numpy()
    start = valid & (~np.r_[False, valid[:-1]] | (state != np.concatenate([['unknown'], state[:-1]])))
    episode_id = np.where(valid, np.cumsum(start), 0)
    rows['episode_id'] = episode_id
    indexes = np.arange(len(rows))
    start_index = np.maximum.accumulate(np.where(start, indexes, -1))
    age = np.where(valid, indexes-start_index+1, 0)
    rows['state_age'] = age
    rows['age_bin'] = age_bins(age)
    starts = np.flatnonzero(start)
    inventory = []
    valid_ends = valid & (~np.r_[valid[1:], False] | (state != np.concatenate([state[1:], ['unknown']])))
    ends = np.flatnonzero(valid_ends)
    for first, last in zip(starts, ends):
        left = first == 0 or not valid[first-1]
        right = last+1 == len(rows) or not valid[last+1]
        inventory.append(dict(variant=rows.variant.iloc[first], episode_id=int(episode_id[first]),
            state=str(state[first]), start_row=int(first), last_row=int(last),
            episode_start=rows.available_at.iloc[first], last_observation=rows.available_at.iloc[last],
            observations=int(last-first+1), prior_state='unknown' if left else str(state[first-1]),
            next_state='unknown' if right else str(state[last+1]),
            next_observation=pd.NaT if right else rows.available_at.iloc[last+1],
            observed_end=rows.available_at.iloc[last+1] if last+1 < len(rows) else coverage_end,
            left_censored=bool(left), right_censored=bool(right)))
    columns = ['variant', 'episode_id', 'state', 'start_row', 'last_row', 'episode_start',
               'last_observation', 'observations', 'prior_state', 'next_state', 'next_observation',
               'observed_end', 'left_censored', 'right_censored']
    episodes = pd.DataFrame(inventory, columns=columns)
    look = episodes.set_index('episode_id')
    for column in ['episode_start', 'prior_state', 'left_censored']:
        rows[column] = rows.episode_id.map(look[column])
    rows['prior_state'] = rows.prior_state.fillna('unknown')
    rows['left_censored'] = rows.left_censored.astype('boolean')
    rows['up_reentry_age'] = np.where(rows.state.eq('up') & rows.prior_state.isin(['down', 'mixed']), rows.age_bin, 'unknown')
    return rows, episodes


def add_nonup_spells(primary, coverage_end=END):
    """Historical non-up endpoints never cross an invalid boundary."""
    rows = primary.reset_index(drop=True).copy()
    valid = rows.valid.to_numpy(dtype=bool)
    state = rows.state.to_numpy()
    nonup = valid & (state != 'up')
    start = nonup & ~np.r_[False, nonup[:-1]]
    end = nonup & ~np.r_[nonup[1:], False]
    ids = np.where(nonup, np.cumsum(start), 0)
    rows['nonup_id'] = ids
    rows['first_up'] = valid & (state == 'up') & np.r_[False, nonup[:-1]]
    inventory = []
    for first, last in zip(np.flatnonzero(start), np.flatnonzero(end)):
        left = first == 0 or not valid[first-1]
        right = last+1 == len(rows) or not valid[last+1]
        inventory.append(dict(nonup_id=int(ids[first]), start_row=int(first), last_row=int(last),
            spell_start=rows.available_at.iloc[first], last_observation=rows.available_at.iloc[last],
            observations=int(last-first+1), start_state=str(state[first]), end_state=str(state[last]),
            left_censored=bool(left), right_censored=bool(right),
            first_up=pd.NaT if right else rows.available_at.iloc[last+1],
            first_up_row=np.nan if right else int(last+1),
            first_up_close=np.nan if right else float(rows.close.iloc[last+1]),
            observed_end=rows.available_at.iloc[last+1] if last+1 < len(rows) else coverage_end))
    columns = ['nonup_id', 'start_row', 'last_row', 'spell_start', 'last_observation', 'observations',
               'start_state', 'end_state', 'left_censored', 'right_censored', 'first_up',
               'first_up_row', 'first_up_close', 'observed_end']
    spells = pd.DataFrame(inventory, columns=columns)
    lookup = spells.set_index('nonup_id')
    mapping = {'first_up': 'next_up_at', 'first_up_row': 'next_up_row', 'first_up_close': 'next_up_close',
               'left_censored': 'nonup_left_censored', 'right_censored': 'nonup_right_censored'}
    for source, dest in mapping.items():
        rows[dest] = rows.nonup_id.map(lookup[source])
    rows['next_up_at'] = pd.to_datetime(rows.next_up_at)
    for column in ['next_up_row', 'next_up_close']:
        rows[column] = pd.to_numeric(rows[column])
    rows['next_up_delay_bars'] = rows.next_up_row-rows.row_index
    rows['next_up_delay_minutes'] = (rows.next_up_at-rows.available_at).dt.total_seconds()/60
    rows['next_up_move_atr'] = (rows.next_up_close-rows.close)/rows.a20
    return rows, spells


def endpoint_state(trades, primary, timestamp, coverage_end=END):
    right = primary[['available_at', 'valid', 'state', 'episode_id', 'state_age']].rename(
        columns={c: 'event_'+c for c in ['available_at', 'valid', 'state', 'episode_id', 'state_age']})
    left = trades[[timestamp]].copy()
    left['_order'] = np.arange(len(left))
    joined = pd.merge_asof(left.sort_values(timestamp, kind='stable'), right,
        left_on=timestamp, right_on='event_available_at', direction='backward', allow_exact_matches=True).sort_values('_order')
    known = joined.event_valid.eq(True) & joined[timestamp].lt(coverage_end)
    joined['event_state'] = joined.event_state.where(known, 'unknown')
    return joined.reset_index(drop=True)


def join_trades(base, states, primary):
    """Latest completed labels at submission and independent primary event lookups."""
    result = pd.merge_asof(base.sort_values(['submitted', 'ticket'], kind='stable'), states,
        left_on='submitted', right_on='available_at', direction='backward', allow_exact_matches=True)
    assert result.valid.eq(True).all(), 'Some eligible trades lack common-valid MA history.'
    assert result.available_at.le(result.submitted).all()
    if states.variant.iloc[0] == 'primary':
        for label, timestamp in [('fill', 'entry_time'), ('exit', 'exit_time')]:
            event = endpoint_state(result, primary, timestamp)
            for field in ['state', 'available_at', 'episode_id', 'state_age']:
                result[f'{label}_{field}'] = event[f'event_{field}'].to_numpy()
        result['firstup_timing'] = np.where(result.state.eq('up'), 'already_up',
            np.where(result.next_up_at.isna(), 'no_observed_up',
            np.where(result.next_up_at.le(result.entry_time), 'up_by_fill',
            np.where(result.next_up_at.le(result.exit_time), 'up_during_trade', 'up_after_exit'))))
        # Bars count from the completed submission observation; elapsed time starts at the actual order.
        result['next_up_delay_from_feature_minutes'] = result.next_up_delay_minutes
        result['next_up_delay_minutes'] = (result.next_up_at-result.submitted).dt.total_seconds()/60
    return result


def main():
    assert digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen MA protocol changed.'
    prior = json.loads((SOURCE/'provenance.json').read_text(encoding='utf-8'))
    verified = json.loads((SOURCE/'independent_verification.json').read_text(encoding='utf-8'))
    assert verified['status'] == 'PASS'
    for name in ['features_m30_20.csv', 'trades.csv']:
        actual = digest(SOURCE/name)
        assert actual == prior['outputs_sha256'][name] == verified['artifact_sha256'][name]
    source = pd.read_csv(SOURCE/'features_m30_20.csv', parse_dates=['bar_time', 'available_at'])
    source = source.loc[source.available_at.lt(END)].reset_index(drop=True)
    source_trades = pd.read_csv(SOURCE/'trades.csv')
    assert len(source_trades) == 25833
    base = source_trades.loc[source_trades.primary].drop(
        columns=[c for c in source_trades if c.startswith(('d1_', 'm30_'))]).copy()
    for column in ['submitted', 'entry_time', 'exit_time', 'session', 'week_start']:
        base[column] = pd.to_datetime(base[column])
    base = base.sort_values(['submitted', 'ticket'], kind='stable').reset_index(drop=True)
    assert len(base) == 16668 and base.ticket.is_unique
    assert base.submitted.lt(END).all() and base.exit_time.lt(END).all()
    economics = {}
    for era, count, total in [('2016-19', 6167, 4416.65), ('2020-26', 10501, 38399.95)]:
        group = base.loc[base.era.eq(era)]
        assert len(group) == count
        assert abs(group.net_dollars.sum()-total) < 1e-7
        economics[era] = dict(trades=count, gross_dollars=float(group.trade_profit.sum()),
            net_dollars=float(group.net_dollars.sum()), net_r=float(group.net_r.sum()))
    print('Verified source hashes and preserved eligible trade economics.', flush=True)
    features, cutoffs = compute_features(source)
    all_states, all_episodes, all_trades = [], [], []
    primary = None
    for variant in VARIANTS:
        states, episodes = build_state_episodes(classify(features, cutoffs, variant))
        if variant == 'primary':
            states, spells = add_nonup_spells(states)
            primary = states
        labelled = join_trades(base, states, primary)
        assert len(labelled) == len(base)
        for field in base.columns:
            pd.testing.assert_series_equal(labelled[field].reset_index(drop=True), base[field].reset_index(drop=True), check_names=False)
        all_states.append(states)
        all_episodes.append(episodes)
        all_trades.append(labelled)
        print(f'{variant}: {len(states):,} observed bars, {len(episodes):,} episodes, {len(labelled):,} valid trades.', flush=True)
    states = pd.concat(all_states, ignore_index=True)
    episodes = pd.concat(all_episodes, ignore_index=True)
    trades = pd.concat(all_trades, ignore_index=True)
    # Keep zero-trade episodes and spells explicitly in the inventories.
    counts = trades.groupby(['variant', 'episode_id']).size().rename('eligible_trades')
    episodes = episodes.join(counts, on=['variant', 'episode_id'])
    episodes['eligible_trades'] = episodes.eligible_trades.fillna(0).astype(int)
    primary_trades = trades.loc[trades.variant.eq('primary')]
    counts = primary_trades.loc[primary_trades.nonup_id.gt(0)].groupby('nonup_id').size()
    spells['eligible_trades'] = spells.nonup_id.map(counts).fillna(0).astype(int)
    assert episodes.eligible_trades.sum() == len(trades)
    assert spells.eligible_trades.sum() == primary_trades.state.ne('up').sum()
    OUT.mkdir(parents=True, exist_ok=True)
    frames = {'features.csv': features, 'cutoffs.csv': cutoffs, 'states.csv': states,
              'episodes.csv': episodes, 'nonup_spells.csv': spells, 'trades.csv': trades}
    for name, frame in frames.items():
        frame.to_csv(OUT/name, index=False, float_format='%.17g')
    audit = dict(all_passed=True, protocol_sha256=PROTOCOL_SHA256,
        source_hashes_checked=True, source_trade_count=len(source_trades),
        eligible_trades_per_variant=len(base), labelled_trade_rows=len(trades),
        observed_m30_bars=len(features), valid_bars=int(features.valid.sum()),
        calibration_observations=int(cutoffs.calibration_observations.iloc[0]),
        common_validity_observations=201, roll_clean_observations=201,
        eras=economics, episodes=len(episodes), nonup_spells=len(spells),
        zero_trade_episodes=int(episodes.eligible_trades.eq(0).sum()),
        zero_trade_nonup_spells=int(spells.eligible_trades.eq(0).sum()),
        exact_economics_preserved=True, all_submission_asof_valid=True,
        future_conditioned_columns=['next_up_at', 'next_up_row', 'next_up_close',
            'next_up_delay_bars', 'next_up_delay_minutes', 'next_up_move_atr', 'firstup_timing'],
        no_outcome_selection=True)
    save_json(OUT/'feature_audit.json', audit)
    inputs = [PROTOCOL, SOURCE/'features_m30_20.csv', SOURCE/'trades.csv', SOURCE/'provenance.json',
              SOURCE/'independent_verification.json', SOURCE/'audit.json']
    provenance = dict(study='RTL MA agreement features and event labels',
        protocol_sha256=PROTOCOL_SHA256, inputs_sha256={str(p): digest(p) for p in inputs},
        program_sha256={str(Path(__file__)): digest(Path(__file__))},
        outputs_sha256={name: digest(OUT/name) for name in list(frames)+['feature_audit.json']},
        prior_source_provenance=prior,
        software={'numpy': np.__version__, 'pandas': pd.__version__},
        exploratory_only=True, strategy_changed=False)
    assert digest(PROTOCOL) == PROTOCOL_SHA256
    save_json(OUT/'feature_provenance.json', provenance)
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == '__main__':
    main()
