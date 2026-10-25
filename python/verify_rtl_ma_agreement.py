"""Independent reconstruction of the frozen RTL MA agreement experiment.

This verifier imports neither analyzer. It binds the independently verified
baseline, reconstructs the causal features and all historical attribution, then
checks every economic partition, control draw and reported uncertainty interval.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'Reports/rtl_price_structure_20261024'
OUT = ROOT / 'Reports/rtl_ma_agreement_20261024'
PROTOCOL = ROOT / 'docs/baseline/rtl-ma-agreement/PROTOCOL.md'
PROTOCOL_SHA = '5241d5d396f03887c2139af0322a9a891980ef74b30b4b5d890947c5dd6e36ab'
END = pd.Timestamp('2026-10-01')
START = pd.Timestamp('2016-01-01')
ERAS = {'2016-19': ('2016-01-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01')}
LENGTHS = tuple(range(5, 201, 5))
GRID = (5, 10, 20, 40, 80, 160, 200)
VARIANTS = {'primary': (GRID, 5, True), 'loose': (GRID, 4, True),
            'strict': (GRID, 6, True), 'zero_band': (GRID, 5, False),
            'dense': (LENGTHS, 29, True)}
STATES = ('up', 'down', 'mixed')


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def numeric(actual, expected, label, atol=1e-8):
    np.testing.assert_allclose(np.asarray(actual, float), np.asarray(expected, float),
                               rtol=1e-10, atol=atol, equal_nan=True, err_msg=label)


def same(actual, expected, label):
    a = pd.Series(actual).reset_index(drop=True).astype(object).fillna('<NA>').astype(str)
    e = pd.Series(expected).reset_index(drop=True).astype(object).fillna('<NA>').astype(str)
    assert a.equals(e), f'{label}: {pd.DataFrame({"actual": a, "expected": e}).loc[a != e].head()}'


def dates(actual, expected, label):
    a = pd.Series(pd.to_datetime(actual, format='ISO8601')).reset_index(drop=True)
    e = pd.Series(pd.to_datetime(expected, format='ISO8601')).reset_index(drop=True)
    assert ((a == e) | (a.isna() & e.isna())).all(), label


def read_csv(name):
    return pd.read_csv(OUT / name, float_precision='round_trip', low_memory=False)


def source_checks():
    assert digest(PROTOCOL) == PROTOCOL_SHA, 'Frozen MA protocol changed'
    provenance = json.loads((SOURCE / 'provenance.json').read_text())
    verified = json.loads((SOURCE / 'independent_verification.json').read_text())
    assert verified['status'] == 'PASS'
    hashes = {str(PROTOCOL): PROTOCOL_SHA}
    for name in ('features_m30_20.csv', 'trades.csv'):
        value = digest(SOURCE / name)
        assert value == provenance['outputs_sha256'][name] == verified['artifact_sha256'][name], name
        hashes[str(SOURCE / name)] = value
    return hashes


def reconstruct_features():
    source = pd.read_csv(SOURCE / 'features_m30_20.csv', float_precision='round_trip')
    for col in ('bar_time', 'available_at'):
        source[col] = pd.to_datetime(source[col])
    dates(source.available_at, source.bar_time + pd.Timedelta(minutes=30), 'source availability')
    source = source.loc[source.available_at < END].reset_index(drop=True)
    assert source.available_at.is_unique and source.available_at.is_monotonic_increasing
    close = source.close.to_numpy(float)
    previous = np.r_[np.nan, close[:-1]]
    tr = np.maximum.reduce([source.high.to_numpy() - source.low.to_numpy(),
                            np.abs(source.high.to_numpy() - previous),
                            np.abs(source.low.to_numpy() - previous)])
    # Explicit summation is independent of pandas rolling and exactly preserves
    # quarter-point OHLC arithmetic before the final division.
    a20 = np.full(len(source), np.nan)
    a20[19:] = np.lib.stride_tricks.sliding_window_view(tr, 20).sum(axis=1)/20
    common = np.zeros(len(source), bool)
    common[200:] = np.lib.stride_tricks.sliding_window_view(np.isfinite(close), 201).all(axis=1)
    common &= np.isfinite(a20) & (a20 > 0)
    clean = np.zeros(len(source), bool)
    clean[200:] = ~np.lib.stride_tricks.sliding_window_view(source.switch_bar.to_numpy(bool), 201).any(axis=1)
    clean &= common
    result = source[['bar_time', 'available_at', 'open', 'high', 'low', 'close', 'switch_bar']].copy()
    result['row_index'] = np.arange(len(source))
    result['tr'] = tr
    result['a20'] = a20
    result['valid'] = common
    result['roll_clean'] = clean
    result['history_start'] = source.bar_time.shift(200)
    calibration = common & (source.available_at < START).to_numpy()
    cutoffs = {}
    max_error = 0.
    for length in LENGTHS:
        slope = np.full(len(source), np.nan)
        slope[length:] = (close[length:] - close[:-length]) / length
        explicit = pd.Series(close).rolling(length, min_periods=length).mean().diff().to_numpy()
        valid = np.isfinite(slope)
        max_error = max(max_error, float(np.abs(explicit[valid] - slope[valid]).max()))
        numeric(explicit, slope, f'literal rolling SMA slope/{length}', atol=1e-10)
        z = np.divide(slope, a20, out=np.full(len(source), np.nan), where=(a20 > 0))
        result[f'd_{length}'] = slope
        result[f'z_{length}'] = np.where(common, z, np.nan)
        cutoffs[length] = float(np.quantile(np.abs(z[calibration]), .2, method='linear'))
    return result, cutoffs, dict(feature_rows=len(result), calibration_rows=int(calibration.sum()),
                                literal_sma_max_abs_error=max_error)


def votes_and_states(features, cuts, variant):
    grid, needed, band = VARIANTS[variant]
    z = features[[f'z_{n}' for n in grid]].to_numpy()
    bounds = np.array([cuts[n] if band else 0. for n in grid])
    votes = np.where(z > bounds, 1, np.where(z < -bounds, -1, 0))
    valid = features.valid.to_numpy(bool)
    votes[~valid] = 0
    up = (votes == 1).sum(axis=1)
    down = (votes == -1).sum(axis=1)
    state = np.where(up >= needed, 'up', np.where(down >= needed, 'down', 'mixed')).astype(object)
    state[~valid] = 'unknown'
    result = features[['row_index', 'bar_time', 'available_at', 'close', 'a20', 'history_start', 'valid', 'roll_clean']].copy()
    result['variant'] = variant
    result['state'] = state
    result['up_votes'], result['down_votes'] = up, down
    result['flat_votes'] = np.where(valid, len(grid) - up - down, 0)
    result['breadth'] = np.where(valid, (up - down) / len(grid), np.nan)
    primary_z = features[[f'z_{n}' for n in GRID]].to_numpy()
    primary_bounds = np.array([cuts[n] for n in GRID])
    primary_votes = np.where(primary_z > primary_bounds, 1, np.where(primary_z < -primary_bounds, -1, 0))
    for name, indexes in (('short_direction', [0, 1, 2]), ('long_direction', [4, 5, 6])):
        subset = primary_votes[:, indexes]
        direction = np.where((subset == 1).sum(axis=1) >= 2, 'up',
                             np.where((subset == -1).sum(axis=1) >= 2, 'down', 'mixed')).astype(object)
        direction[~valid] = 'unknown'
        result[name] = direction
    result['context'] = np.where(valid, 'short_'+result.short_direction+'_long_'+result.long_direction, 'unknown')
    return result


def literal_episodes(frame):
    """Independent literal observation walk; gaps and era edges do not reset."""
    valid = frame.valid.to_numpy(bool)
    state = frame.state.to_numpy()
    ids, ages = np.zeros(len(frame), int), np.zeros(len(frame), int)
    prior = np.full(len(frame), 'unknown', object)
    inventory = []
    row = 0
    while row < len(frame):
        if not valid[row]:
            row += 1
            continue
        begin = row
        while row + 1 < len(frame) and valid[row + 1] and state[row + 1] == state[begin]:
            row += 1
        end = row
        number = len(inventory) + 1
        left = begin == 0 or not valid[begin - 1]
        right = end == len(frame) - 1 or not valid[end + 1]
        previous = 'unknown' if left else state[begin - 1]
        inventory.append(dict(episode_id=number, state=state[begin], start_index=begin,
                              end_index=end, length=end-begin+1, start=frame.available_at.iloc[begin],
                              last=frame.available_at.iloc[end], left_censored=left,
                              right_censored=right, prior_state=previous,
                              first_next=pd.NaT if right else frame.available_at.iloc[end+1]))
        ids[begin:end+1] = number
        ages[begin:end+1] = np.arange(1, end-begin+2)
        prior[begin:end+1] = previous
        row += 1
    frame = frame.copy()
    frame['episode_id'], frame['state_age'], frame['prior_state'] = ids, ages, prior
    return frame, pd.DataFrame(inventory)


def literal_spells(frame):
    valid = frame.valid.to_numpy(bool)
    state = frame.state.to_numpy()
    ids = np.zeros(len(frame), int)
    next_up = np.full(len(frame), -1, int)
    inventory = []
    row = 0
    while row < len(frame):
        if not valid[row] or state[row] == 'up':
            row += 1
            continue
        start = row
        while row + 1 < len(frame) and valid[row + 1] and state[row + 1] != 'up':
            row += 1
        end = row
        left = start == 0 or not valid[start - 1]
        right = end == len(frame) - 1 or not valid[end + 1]
        number = len(inventory) + 1
        first_up = -1 if right else end + 1
        inventory.append(dict(spell_id=number, start_index=start, end_index=end,
                              start=frame.available_at.iloc[start], last=frame.available_at.iloc[end],
                              length=end-start+1, left_censored=left, right_censored=right,
                              first_up_index=first_up,
                              first_up=pd.NaT if right else frame.available_at.iloc[first_up]))
        ids[start:end+1] = number
        next_up[start:end+1] = first_up
        row += 1
    return ids, next_up, pd.DataFrame(inventory)


def source_trades():
    ledger = pd.read_csv(SOURCE / 'trades.csv', float_precision='round_trip')
    assert len(ledger) == 25833 and ledger.ticket.is_unique
    for col in ('submitted', 'entry_time', 'exit_time', 'session', 'week_start'):
        ledger[col] = pd.to_datetime(ledger[col])
    trades = ledger.loc[ledger.primary].copy().reset_index(drop=True)
    assert len(trades) == 16668
    dates(trades.session, trades.submitted.dt.normalize(), 'submission session')
    dates(trades.week_start, trades.session-pd.to_timedelta(trades.session.dt.weekday, unit='D'), 'trade weeks')
    numeric(trades.initial_risk_dollars, 2*(trades.requested_price-trades.original_sl), 'planned risk')
    numeric(trades.trade_profit, 2*(trades.exit_price-trades.fill_price), 'original gross PnL')
    numeric(trades.net_dollars, trades.trade_profit-1.05, 'costs')
    numeric(trades.gross_r, trades.trade_profit/trades.initial_risk_dollars, 'gross R')
    numeric(trades.net_r, trades.net_dollars/trades.initial_risk_dollars, 'net R')
    numeric(trades.commission_r, 1.05/trades.initial_risk_dollars, 'commission R')
    numeric(trades.holding_minutes, (trades.exit_time-trades.entry_time).dt.total_seconds()/60, 'holding')
    for stress in (1, 2):
        numeric(trades[f'stress{stress}_net_dollars'], trades.net_dollars-stress, 'stress dollars')
        numeric(trades[f'stress{stress}_net_r'], (trades.net_dollars-stress)/trades.initial_risk_dollars, 'stress R')
    for era, count, dollars in (('2016-19', 6167, 4416.65), ('2020-26', 10501, 38399.95)):
        part = trades.loc[trades.era == era]
        assert len(part) == count
        numeric([part.net_dollars.sum()], [dollars], 'baseline ' + era)
    return trades


def asof_index(availability, timestamps):
    return pd.DatetimeIndex(availability).searchsorted(pd.DatetimeIndex(timestamps), side='right')-1


def daily_drawdown(values, dates_index):
    equity = np.r_[0., np.cumsum(values)]
    dd = float((np.maximum.accumulate(equity)-equity).max())
    peak, balance, duration, peak_date = 0., 0., 0, dates_index[0]
    for date, pnl in zip(dates_index, values):
        balance += float(pnl)
        if balance >= peak-1e-9:
            peak = max(peak, balance)
            peak_date = date
        else:
            duration = max(duration, (date-peak_date).days)
    return dd, duration


def metrics(trades, calendar):
    count = len(trades)
    daily = trades.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.)
    weekly = daily.groupby(daily.index-pd.to_timedelta(daily.index.weekday, unit='D')).sum()
    ordered = trades.sort_values(['exit_time', 'entry_time', 'ticket'])
    equity = np.r_[0., ordered.net_dollars.cumsum().to_numpy()]
    daily_dd, duration = daily_drawdown(daily.to_numpy(), daily.index)
    positive = float(trades.loc[trades.net_dollars > 0, 'net_dollars'].sum())
    negative = float(-trades.loc[trades.net_dollars < 0, 'net_dollars'].sum())
    result = dict(trades=count, active_sessions=trades.session.nunique(), active_weeks=trades.week_start.nunique(),
                  eligible_sessions=len(calendar), eligible_weeks=len(weekly), gross_mean_r=trades.gross_r.mean(),
                  net_mean_r=trades.net_r.mean(), gross_dollars=trades.trade_profit.sum(),
                  net_dollars=trades.net_dollars.sum(), dollar_pf=positive/negative if negative else np.nan,
                  risk_mean=trades.initial_risk_dollars.mean(), risk_median=trades.initial_risk_dollars.median(),
                  commission_mean_r=trades.commission_r.mean(), holding_hours=trades.holding_minutes.sum()/60,
                  mean_holding_minutes=trades.holding_minutes.mean(), worst_day=daily.min(), worst_week=weekly.min(),
                  worst5pct_session_mean=np.sort(daily.to_numpy())[:math.ceil(.05*len(daily))].mean(),
                  closed_trade_dd=float((np.maximum.accumulate(equity)-equity).max()), daily_close_dd=daily_dd,
                  daily_dd_duration_days=duration, winners=int((trades.net_dollars > 0).sum()),
                  losers=int((trades.net_dollars < 0).sum()), positive_net_dollars=positive, loss_dollars=negative,
                  net_r_total=trades.net_r.sum(), active_episodes=trades.episode_id.nunique(),
                  adequate_coverage=count >= 200 and trades.week_start.nunique() >= 30,
                  planned_risk_total=trades.initial_risk_dollars.sum())
    for stress in (1, 2):
        result[f'stress{stress}_net_dollars'] = trades[f'stress{stress}_net_dollars'].sum()
        result[f'stress{stress}_mean_r'] = trades[f'stress{stress}_net_r'].mean()
    return result


def verify_metric_row(row, expected, label):
    for column, value in expected.items():
        assert column in row.index, f'{label}: missing {column}'
        numeric([row[column]], [value], label+'/'+column)


DATE_COLUMNS = {'bar_time', 'available_at', 'history_start', 'episode_start', 'last_observation',
                'next_observation', 'observed_end', 'spell_start', 'first_up', 'next_up_at',
                'submitted', 'entry_time', 'exit_time', 'session', 'week_start',
                'fill_available_at', 'exit_available_at'}


def compare_frame(actual, expected, label):
    assert len(actual) == len(expected), f'{label}: row count {len(actual)} != {len(expected)}'
    for column in expected:
        assert column in actual, f'{label}: missing {column}'
        a, e = actual[column], expected[column]
        if column in DATE_COLUMNS and not pd.api.types.is_bool_dtype(e.dtype):
            dates(a, e, label+'/'+column)
        elif pd.api.types.is_numeric_dtype(e.dtype) and not pd.api.types.is_bool_dtype(e.dtype):
            numeric(a, e, label+'/'+column)
        else:
            same(a, e, label+'/'+column)


def expected_state_panel(features, cutoffs, variant):
    frame, inventory = literal_episodes(votes_and_states(features, cutoffs, variant))
    inventory = inventory.rename(columns={'start_index': 'start_row', 'end_index': 'last_row',
        'length': 'observations', 'start': 'episode_start', 'last': 'last_observation', 'first_next': 'next_observation'})
    inventory['variant'] = variant
    following = inventory.last_row.to_numpy()+1
    inventory['next_state'] = [frame.state.iloc[p] if p < len(frame) and frame.valid.iloc[p] else 'unknown' for p in following]
    inventory['observed_end'] = [frame.available_at.iloc[p] if p < len(frame) else END for p in following]
    mapping = inventory.set_index('episode_id')
    frame['episode_start'] = frame.episode_id.map(mapping.episode_start)
    frame['left_censored'] = frame.episode_id.map(mapping.left_censored).astype('boolean')
    frame['age_bin'] = ['unknown' if a == 0 else '1' if a == 1 else '2-3' if a <= 3 else '4-8' if a <= 8 else '9+' for a in frame.state_age]
    frame['up_reentry_age'] = np.where(frame.state.eq('up') & frame.prior_state.isin(['down', 'mixed']), frame.age_bin, 'unknown')
    return frame, inventory


def add_expected_spells(frame):
    ids, future, spells = literal_spells(frame)
    spells = spells.rename(columns={'spell_id': 'nonup_id', 'start_index': 'start_row', 'end_index': 'last_row',
        'start': 'spell_start', 'last': 'last_observation', 'length': 'observations', 'first_up_index': 'first_up_row'})
    spells['start_state'] = frame.state.to_numpy()[spells.start_row.to_numpy()]
    spells['end_state'] = frame.state.to_numpy()[spells.last_row.to_numpy()]
    spells['first_up_close'] = [frame.close.iloc[p] if p >= 0 else np.nan for p in spells.first_up_row]
    spells['observed_end'] = [frame.available_at.iloc[p+1] if p+1 < len(frame) else END for p in spells.last_row]
    spells['first_up_row'] = spells.first_up_row.where(spells.first_up_row >= 0, np.nan)
    frame = frame.copy()
    frame['nonup_id'] = ids
    frame['first_up'] = frame.valid & frame.state.eq('up') & np.r_[False, ids[:-1] > 0]
    lookup = spells.set_index('nonup_id')
    for source, target in [('first_up', 'next_up_at'), ('first_up_row', 'next_up_row'),
        ('first_up_close', 'next_up_close'), ('left_censored', 'nonup_left_censored'), ('right_censored', 'nonup_right_censored')]:
        frame[target] = frame.nonup_id.map(lookup[source])
    frame['next_up_delay_bars'] = np.where(future >= 0, future-frame.row_index, np.nan)
    frame['next_up_delay_minutes'] = (frame.next_up_at-frame.available_at).dt.total_seconds()/60
    frame['next_up_move_atr'] = (frame.next_up_close-frame.close)/frame.a20
    return frame, spells


def expected_trades(base, frame, primary):
    base = base.drop(columns=[c for c in base if c.startswith(('d1_', 'm30_'))]).sort_values(['submitted', 'ticket']).reset_index(drop=True)
    positions = asof_index(frame.available_at, base.submitted)
    assert (positions >= 0).all() and frame.valid.iloc[positions].all()
    result = pd.concat([base, frame.iloc[positions].reset_index(drop=True)], axis=1)
    assert result.columns.is_unique
    if frame.variant.iloc[0] == 'primary':
        for label, event in [('fill', 'entry_time'), ('exit', 'exit_time')]:
            idx = asof_index(primary.available_at, base[event])
            assert (idx >= 0).all()
            event_rows = primary.iloc[idx]
            result[label+'_available_at'] = event_rows.available_at.to_numpy()
            result[label+'_episode_id'] = event_rows.episode_id.to_numpy()
            result[label+'_state_age'] = event_rows.state_age.to_numpy()
            result[label+'_state'] = np.where(event_rows.valid.to_numpy() & (base[event] < END).to_numpy(), event_rows.state, 'unknown')
        result['firstup_timing'] = ['already_up' if r.state == 'up' else 'no_observed_up' if pd.isna(r.next_up_at)
            else 'up_by_fill' if r.next_up_at <= r.entry_time else 'up_during_trade' if r.next_up_at <= r.exit_time
            else 'up_after_exit' for r in result.itertuples()]
        result['next_up_delay_from_feature_minutes'] = result.next_up_delay_minutes
        result['next_up_delay_minutes'] = (result.next_up_at-result.submitted).dt.total_seconds()/60
    return result


def verify_features_and_trades():
    expected, cuts, audit = reconstruct_features()
    actual = read_csv('features.csv')
    for column in expected:
        if column.startswith('d_'):
            continue  # Explicit SMA is checked above; production stores normalized slopes.
        target = 'TR' if column == 'tr' else column
        compare_frame(actual[[target]], expected[[column]].rename(columns={column: target}), 'features')
    cutoff_frame = read_csv('cutoffs.csv').set_index('L')
    assert set(cutoff_frame.index) == set(LENGTHS)
    for length in LENGTHS:
        numeric([cutoff_frame.loc[length, 'cutoff']], [cuts[length]], 'cutoff '+str(length), atol=1e-15)
        assert cutoff_frame.loc[length, 'calibration_observations'] == audit['calibration_rows']
    actual_states = read_csv('states.csv')
    actual_episodes, actual_spells, actual_trades = read_csv('episodes.csv'), read_csv('nonup_spells.csv'), read_csv('trades.csv')
    base = source_trades()
    frames, primary = [], None
    count_episodes = 0
    for variant in VARIANTS:
        states, episodes = expected_state_panel(expected, cuts, variant)
        if variant == 'primary':
            states, spells = add_expected_spells(states)
            primary = states
        subset = actual_states.loc[actual_states.variant == variant].sort_values('row_index')
        compare_frame(subset, states, variant+'/states')
        labelled = expected_trades(base, states, primary)
        counts = labelled.groupby('episode_id').size()
        episodes['eligible_trades'] = episodes.episode_id.map(counts).fillna(0).astype(int)
        compare_frame(actual_episodes.loc[actual_episodes.variant == variant].sort_values('episode_id'), episodes, variant+'/episodes')
        compare_frame(actual_trades.loc[actual_trades.variant == variant].sort_values(['submitted', 'ticket']), labelled, variant+'/trades')
        if variant == 'primary':
            counts = labelled.loc[labelled.nonup_id > 0].groupby('nonup_id').size()
            spells['eligible_trades'] = spells.nonup_id.map(counts).fillna(0).astype(int)
            compare_frame(actual_spells.sort_values('nonup_id'), spells, 'nonup spells')
            audit['nonup_spells'] = len(spells)
            audit['zero_trade_nonup_spells'] = int(spells.eligible_trades.eq(0).sum())
        frames.append(labelled)
        count_episodes += len(episodes)
        print(f'Independently verified {variant}: votes, states, episodes and all 16,668 event joins.', flush=True)
    audit.update(episodes=count_episodes, labelled_trades=sum(map(len, frames)), source_trades=25833, eligible_trades=16668)
    return pd.concat(frames, ignore_index=True), expected, audit


def skip_for(trades, policy):
    return (trades.state == 'mixed').to_numpy() if policy == 'skip_mixed' else (
        (trades.state == 'down').to_numpy() if policy == 'skip_down' else (trades.state != 'up').to_numpy())


def verify_economic_tables(trades, features):
    summaries, yearly, rolls = read_csv('summaries.csv'), read_csv('yearly.csv'), read_csv('roll_summary.csv')
    policies, sessions = read_csv('policies.csv'), read_csv('policy_sessions.csv')
    calendars = pd.DatetimeIndex(features.bar_time.dt.normalize().unique()).sort_values()
    summary_keys, yearly_keys, roll_keys, policy_keys, curve_keys = set(), set(), set(), set(), set()
    for era, (start, stop) in ERAS.items():
        calendar = calendars[(calendars >= start) & (calendars < stop)]
        for variant in VARIANTS:
            frame = trades.loc[(trades.era == era) & (trades.variant == variant)].copy()
            pieces = [('state', state, frame if state == 'all' else frame.loc[frame.state == state]) for state in ('all', *STATES)]
            if variant == 'primary':
                mapping = {'context': frame.context, 'context_state': frame.context+'|'+frame.state,
                    'state_age': frame.state+'|'+frame.age_bin, 'fill_state': frame.fill_state, 'exit_state': frame.exit_state,
                    'firstup_timing_state': frame.firstup_timing+'|'+frame.state,
                    'up_reentry_age': pd.Series(np.where(frame.state == 'up', frame.prior_state+'|'+frame.up_reentry_age, 'not_up'), index=frame.index)}
                for dimension, category_series in mapping.items():
                    for category in sorted(category_series.unique()):
                        pieces.append((dimension, category, frame.loc[category_series == category]))
            for dimension, category, selected in pieces:
                key = (variant, era, dimension, category)
                summary_keys.add(key)
                row = summaries.loc[(summaries.variant == variant) & (summaries.era == era)
                    & (summaries.dimension == dimension) & (summaries.category == category)]
                assert len(row) == 1, key
                verify_metric_row(row.iloc[0], metrics(selected, calendar), '/'.join(key))
                if dimension != 'state':
                    continue
                key3 = (variant, era, category)
                roll_keys.add(key3)
                row = rolls.loc[(rolls.variant == variant) & (rolls.era == era) & (rolls.state == category)]
                assert len(row) == 1, key3
                verify_metric_row(row.iloc[0], metrics(selected.loc[selected.roll_clean], calendar), 'roll/'+str(key3))
                for year in sorted(frame.year.unique()):
                    key4 = (variant, era, year, category)
                    yearly_keys.add(key4)
                    row = yearly.loc[(yearly.variant == variant) & (yearly.era == era) & (yearly.year == year) & (yearly.state == category)]
                    assert len(row) == 1, key4
                    assert row.partial.iloc[0] == (year == 2026)
                    verify_metric_row(row.iloc[0], metrics(selected.loc[selected.year == year], calendar[calendar.year == year]), 'year/'+str(key4))
            for policy in ('skip_mixed', 'skip_down', 'only_up'):
                skip = skip_for(frame, policy)
                retained, omitted = frame.loc[~skip], frame.loc[skip]
                holding_fraction = retained.holding_minutes.sum()/frame.holding_minutes.sum()
                extra = dict(skipped_trades=len(omitted), skipped_active_weeks=omitted.week_start.nunique(),
                    skipped_net_dollars=omitted.net_dollars.sum(), skipped_net_mean_r=omitted.net_r.mean(),
                    losses_avoided=-omitted.loc[omitted.net_dollars < 0, 'net_dollars'].sum(),
                    profits_missed=omitted.loc[omitted.net_dollars > 0, 'net_dollars'].sum(),
                    retained_trade_fraction=len(retained)/len(frame), retained_holding_fraction=holding_fraction,
                    retained_planned_risk_fraction=retained.initial_risk_dollars.sum()/frame.initial_risk_dollars.sum())
                scaled = frame.copy()
                for column in ('net_dollars', 'trade_profit', 'initial_risk_dollars', 'fill_risk_dollars',
                    'stress1_net_dollars', 'stress2_net_dollars', 'holding_minutes'):
                    scaled[column] = frame[column]*holding_fraction
                for curve, selected in [('baseline', frame), ('retained', retained), ('static_holding_scaled', scaled)]:
                    key = (variant, era, policy, curve)
                    policy_keys.add(key)
                    selector = (policies.variant == variant) & (policies.era == era) & (policies.policy == policy) & (policies.curve == curve)
                    row = policies.loc[selector]
                    assert len(row) == 1, key
                    expected = metrics(selected, calendar)
                    expected.update(extra, pnl_scale=holding_fraction if curve == 'static_holding_scaled' else 1.)
                    verify_metric_row(row.iloc[0], expected, 'policy/'+str(key))
                    actual_daily = sessions.loc[(sessions.variant == variant) & (sessions.era == era)
                        & (sessions.policy == policy) & (sessions.curve == curve)].sort_values('session')
                    daily = selected.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.)
                    dates(actual_daily.session, daily.index, 'policy calendar/'+str(key))
                    numeric(actual_daily.net_dollars, daily.values, 'policy daily PnL/'+str(key))
                    curve_keys.update((*key, date.strftime('%Y-%m-%d')) for date in calendar)
        print(f'Independently verified {era}: all partitions, annual/roll tables, policies and daily curves.', flush=True)
    for frame, columns, expected in [(summaries, ['variant', 'era', 'dimension', 'category'], summary_keys),
        (yearly, ['variant', 'era', 'year', 'state'], yearly_keys), (rolls, ['variant', 'era', 'state'], roll_keys),
        (policies, ['variant', 'era', 'policy', 'curve'], policy_keys)]:
        assert not frame.duplicated(columns).any(), columns
        assert set(frame[columns].itertuples(index=False, name=None)) == expected, columns
    session_key = sessions[['variant', 'era', 'policy', 'curve', 'session']].copy()
    session_key.session = pd.to_datetime(session_key.session).dt.strftime('%Y-%m-%d')
    assert not session_key.duplicated().any()
    assert set(session_key.itertuples(index=False, name=None)) == curve_keys
    return calendars, dict(summary_rows=len(summaries), yearly_rows=len(yearly), roll_rows=len(rolls),
                           policy_rows=len(policies), daily_curve_rows=len(sessions))


def verify_bootstrap(trades, calendars):
    actual_draws, uncertainty = read_csv('bootstrap_draws.csv'), read_csv('uncertainty.csv')
    assert len(actual_draws) == 60000 and len(uncertainty) == 6
    rng = np.random.default_rng(20261024)
    for era, (start, stop) in ERAS.items():
        calendar = calendars[(calendars >= start) & (calendars < stop)]
        first = calendar[0]-pd.Timedelta(days=calendar[0].weekday())
        last = calendar[-1]-pd.Timedelta(days=calendar[-1].weekday())
        weeks = pd.date_range(first, last, freq='7D')
        frame = trades.loc[(trades.variant == 'primary') & (trades.era == era)]
        starts = rng.integers(0, len(weeks), size=(10000, math.ceil(len(weeks)/4)))
        sample = ((starts[:, :, None]+np.arange(4)) % len(weeks)).reshape(10000, -1)[:, :len(weeks)]
        # Count how often every calendar week was selected, then use weighted
        # totals; this differs from the analyzer's advanced-indexed weekly sum.
        multiplicity = np.zeros((10000, len(weeks)), dtype=np.int64)
        np.add.at(multiplicity, (np.arange(10000)[:, None], sample), 1)
        assert (multiplicity.sum(axis=1) == len(weeks)).all()
        for state in STATES:
            chosen, other = frame.loc[frame.state == state], frame.loc[frame.state != state]
            weekly = chosen.groupby('week_start').net_r.agg(['sum', 'count']).reindex(weeks, fill_value=0.)
            complement = other.groupby('week_start').net_r.agg(['sum', 'count']).reindex(weeks, fill_value=0.)
            values, remaining = multiplicity @ weekly.to_numpy(), multiplicity @ complement.to_numpy()
            mean = values[:, 0]/values[:, 1]
            difference = mean-remaining[:, 0]/remaining[:, 1]
            expected = pd.DataFrame(dict(draw=np.arange(10000), selected_net_r=values[:, 0], selected_trades=values[:, 1],
                complement_net_r=remaining[:, 0], complement_trades=remaining[:, 1], mean_net_r=mean, difference_net_r=difference))
            actual = actual_draws.loc[(actual_draws.era == era) & (actual_draws.group == state)].sort_values('draw')
            compare_frame(actual, expected, f'bootstrap draws/{era}/{state}')
            assert not actual.draw.duplicated().any()
            row = uncertainty.loc[(uncertainty.era == era) & (uncertainty.group == state)]
            assert len(row) == 1
            metrics_row = dict(trades=len(chosen), active_weeks=chosen.week_start.nunique(), net_mean_r=chosen.net_r.mean(),
                complement_trades=len(other), complement_net_mean_r=other.net_r.mean(),
                difference_net_r=chosen.net_r.mean()-other.net_r.mean(),
                valid_mean_draws=int(np.isfinite(mean).sum()), valid_difference_draws=int(np.isfinite(difference).sum()))
            for name, vector in [('mean_net_r', mean), ('difference_net_r', difference)]:
                for suffix, alpha in [('95', .05), ('98_33', .05/3)]:
                    low, high = np.quantile(vector[np.isfinite(vector)], [alpha/2, 1-alpha/2], method='linear')
                    metrics_row[f'{name}_ci{suffix}_low'], metrics_row[f'{name}_ci{suffix}_high'] = low, high
            verify_metric_row(row.iloc[0], metrics_row, f'bootstrap intervals/{era}/{state}')
        print(f'Independently reconstructed all 10,000 paired block draws and intervals for {era}.', flush=True)


def verify_placements_and_screen(trades, calendars):
    actual_draws, summaries, screen = read_csv('placement_draws.csv'), read_csv('placement_summary.csv'), read_csv('screen.csv')
    assert len(actual_draws) == 12000 and len(summaries) == 6 and len(screen) == 3
    rng = np.random.default_rng(20261025)
    qualifies = {policy: {} for policy in ('skip_mixed', 'skip_down', 'only_up')}
    for era, (start, stop) in ERAS.items():
        calendar = calendars[(calendars >= start) & (calendars < stop)]
        frame = trades.loc[(trades.variant == 'primary') & (trades.era == era)].sort_values(['entry_time', 'ticket'])
        offsets = rng.integers(0, len(frame), size=2000)
        base_daily = frame.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.)
        base_dd = daily_drawdown(base_daily.to_numpy(), calendar)[0]
        dates_index = calendar.get_indexer(frame.session)
        pnl, hours = frame.net_dollars.to_numpy(), frame.holding_minutes.to_numpy()/60
        for policy in qualifies:
            skipped = skip_for(frame, policy)
            retained, omitted = frame.loc[~skipped], frame.loc[skipped]
            retained_daily = retained.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.)
            actual_net, actual_hours = retained.net_dollars.sum(), retained.holding_minutes.sum()/60
            actual_dd = daily_drawdown(retained_daily.to_numpy(), calendar)[0]
            qualifies[policy][era] = (omitted.net_dollars.sum() < 0 and omitted.net_r.mean() < 0 and len(omitted) >= 200
                and omitted.week_start.nunique() >= 30 and actual_dd < base_dd)
            rows = []
            for draw, shift in enumerate(offsets):
                # Explicit modular lookup rather than np.roll.
                selected = ~skipped[(np.arange(len(frame))-shift) % len(frame)]
                dollars, holding = pnl[selected].sum(), hours[selected].sum()
                daily = np.zeros(len(calendar))
                np.add.at(daily, dates_index[selected], pnl[selected])
                equity = np.r_[0., np.cumsum(daily)]
                dd = (np.maximum.accumulate(equity)-equity).max()
                scale = actual_hours/holding
                rows.append(dict(draw=draw, offset=int(shift), retained_trades=int(selected.sum()), net_dollars=dollars,
                    daily_close_dd=dd, holding_hours=holding, exposure_scale=scale,
                    exposure_scaled_net_dollars=dollars*scale, exposure_scaled_daily_close_dd=dd*scale))
            expected = pd.DataFrame(rows)
            actual = actual_draws.loc[(actual_draws.era == era) & (actual_draws.policy == policy)].sort_values('draw')
            compare_frame(actual, expected, f'placement/{era}/{policy}')
            assert not actual.draw.duplicated().any()
            result = dict(draws=2000, actual_retained_net_dollars=actual_net, actual_daily_close_dd=actual_dd,
                actual_holding_hours=actual_hours,
                fraction_shifts_beaten_net=(expected.net_dollars < actual_net).mean(),
                fraction_shifts_beaten_dd=(expected.daily_close_dd > actual_dd).mean(),
                fraction_scaled_shifts_beaten_net=(expected.exposure_scaled_net_dollars < actual_net).mean(),
                fraction_scaled_shifts_beaten_dd=(expected.exposure_scaled_daily_close_dd > actual_dd).mean())
            for col in ('net_dollars', 'daily_close_dd', 'exposure_scaled_net_dollars', 'exposure_scaled_daily_close_dd'):
                for q in (.025, .5, .975):
                    result[f'{col}_q{int(q*1000)}'] = np.quantile(expected[col], q, method='linear')
            row = summaries.loc[(summaries.era == era) & (summaries.policy == policy)]
            assert len(row) == 1
            verify_metric_row(row.iloc[0], result, f'placement summary/{era}/{policy}')
        print(f'Independently reconstructed all 6,000 circular placement controls for {era}.', flush=True)
    for policy, passed in qualifies.items():
        row = screen.loc[screen.policy == policy]
        assert len(row) == 1
        for era, value in passed.items():
            assert bool(row[f'{era}_passes'].iloc[0]) == bool(value)
        assert bool(row.warrants_followup_replay.iloc[0]) == all(passed.values())


def main():
    inputs = source_checks()
    features_provenance = json.loads((OUT/'feature_provenance.json').read_text())
    provenance = json.loads((OUT/'provenance.json').read_text())
    for manifest in (features_provenance, provenance):
        assert manifest['protocol_sha256'] == PROTOCOL_SHA
        for name, expected in manifest['outputs_sha256'].items():
            assert digest(OUT/name) == expected, 'artifact hash/'+name
    for path, value in features_provenance['inputs_sha256'].items():
        assert digest(path) == value, 'feature input hash/'+path
    for path, value in features_provenance['program_sha256'].items():
        assert digest(path) == value, 'feature program hash/'+path
    for name, value in provenance['inputs_sha256'].items():
        assert digest(OUT/name) == value, 'economics input hash/'+name
    assert digest(ROOT/'python/analyze_rtl_ma_agreement.py') == provenance['program_sha256']
    assert digest(ROOT/'python/analyze_rtl_market_regimes.py') == provenance['prior_metrics_program_sha256']
    trades, features, audit = verify_features_and_trades()
    calendars, table_audit = verify_economic_tables(trades, features)
    verify_bootstrap(trades, calendars)
    verify_placements_and_screen(trades, calendars)
    artifacts = {**features_provenance['outputs_sha256'], **provenance['outputs_sha256']}
    result = dict(status='PASS', protocol_sha256=PROTOCOL_SHA, inputs_sha256=inputs,
        artifact_sha256={name: digest(OUT/name) for name in artifacts},
        program_sha256={str(Path(__file__)): digest(Path(__file__)),
                        str(ROOT/'python/test_rtl_ma_agreement.py'): digest(ROOT/'python/test_rtl_ma_agreement.py')},
        **audit, **table_audit, bootstrap_draws_verified=60000, placement_draws_verified=12000,
        literal_sma_verified=True, complete_tr_true_range_verified=True, cutoffs_votes_and_states_exact=True,
        asof_joins_and_future_timing_verified=True, inventories_include_zero_trade_episodes=True,
        economics_partitions_policies_drawdowns_verified=True, all_output_and_program_hashes_match=True,
        no_analyzer_functions_imported=True)
    (OUT/'independent_verification.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()

