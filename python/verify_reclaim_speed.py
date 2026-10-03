"""Independent checks of saved Q9 timing, pairs, response partitions and inputs."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_reclaim_speed import STUDY, UPSTREAM, load_minutes
from analyze_price_levels import sha256


def main():
    f = pd.read_csv(STUDY / 'speed_features.csv', parse_dates=['signal_time', 'submission_time'])
    r = pd.read_csv(STUDY / 'responses.csv')
    p = pd.read_csv(STUDY / 'pairs.csv')
    old = pd.read_csv(UPSTREAM / 'attempt_features.csv', parse_dates=['signal_time', 'submission_time'])
    pd.testing.assert_frame_equal(f[old.columns], old)
    old_r = pd.read_csv(UPSTREAM / 'forward_responses.csv')
    pd.testing.assert_frame_equal(r[old_r.columns], old_r)
    assert not r.duplicated(['event_id', 'horizon']).any()
    for scale in ('r', 'a'):
        known = r[f'{scale}_return'].notna()
        v = r.loc[known, f'{scale}_return']
        assert (r.loc[known, f'{scale}_up'] == (v >= .5)).all()
        assert (r.loc[known, f'{scale}_down'] == (v <= -.5)).all()
        assert np.allclose(r.loc[known, f'{scale}_balance'],
                           r.loc[known, f'{scale}_up'] - r.loc[known, f'{scale}_down'])
        path = r.dropna(subset=[f'{scale}_hit_both'])
        assert np.allclose(path[[f'{scale}_hit_{x}' for x in ('both', 'up_only', 'down_only', 'neither')]].sum(axis=1), 1)
        assert np.allclose(path[[f'{scale}_first_{x}' for x in ('up', 'down', 'ambiguous', 'neither')]].sum(axis=1), 1)
        assert np.allclose(path[f'{scale}_hit_up'] + path[f'{scale}_hit_down'] - path[f'{scale}_hit_both'], 1 - path[f'{scale}_hit_neither'])
        assert (path[f'{scale}_first_ambiguous'] <= path[f'{scale}_hit_both']).all()
    assert r.loc[r.path_status != 'complete', 'r_hit_both'].isna().all()

    # Rebuild pair restrictions from the physical quantities, not matcher helpers.
    indexed = f.set_index(['source', 'event_id'])
    for (source, period, contrast, cutoff), pairs in p.groupby(['source', 'period', 'contrast', 'cutoff']):
        assert pairs.a_event.is_unique and pairs.b_event.is_unique
        a = indexed.loc[[(source, e) for e in pairs.a_event]].reset_index()
        b = indexed.loc[[(source, e) for e in pairs.b_event]].reset_index()
        assert (a.period == period).all() and (b.period == period).all()
        assert (a.year == b.year).all()
        assert (a.signal_path_status == 'complete').all() and (b.signal_path_status == 'complete').all()
        for column in ('depth_a', 'atr_lag', 'range_a'):
            ratio = a[column] / b[column]
            assert ratio.between(.5 - 1e-12, 2 + 1e-12).all()
        assert ((a.breach_minute - b.breach_minute).abs() <= 5).all()
        assert ((a.clock_minutes - b.clock_minutes).abs() <= 120).all()
        assert (a.group == 'breach_reclaim').all()
        if contrast == 'speed':
            assert (b.group == 'breach_reclaim').all()
            assert (a.recovery_delay <= cutoff).all() and (b.recovery_delay >= 6).all()
        else:
            assert (b.group == 'breach_unrecovered').all()

    # Stratified minute checks include slow, transient, missing and boundary cases.
    samples = []
    fresh = f[f.group.isin(['breach_reclaim', 'breach_unrecovered', 'breach_exact_close'])]
    for _, g in fresh.groupby(['source', 'period', 'group', 'speed_group']):
        samples.append(g.sample(n=min(15, len(g)), random_state=20261003))
    sample = pd.concat(samples).drop_duplicates(['event_id', 'source'])
    minutes = load_minutes()
    for row in sample.itertuples():
        path = minutes.loc[row.signal_time:row.signal_time + pd.Timedelta(minutes=29)]
        expected = pd.date_range(row.signal_time, periods=30, freq='min')
        complete = path.index.equals(expected)
        assert complete == (row.signal_path_status == 'complete')
        if not complete:
            assert np.isnan(row.recovery_delay)
            continue
        first = path.index[path.low < row.low][0]
        later = path.loc[first:]
        recovery = later.index[later.close > row.low]
        assert row.breach_minute == (first - row.signal_time).total_seconds() / 60
        if len(recovery):
            delay = (recovery[0] + pd.Timedelta(minutes=1) - first).total_seconds() / 60
            assert delay == row.recovery_delay
        else:
            assert np.isnan(row.recovery_delay)
        assert row.below_closes == (later.close < row.low).sum()

    # Independent path first-touch audit using timestamp sets.
    event = f.drop_duplicates('event_id').set_index('event_id')
    paths = r[r.path_status == 'complete'].sample(n=300, random_state=20261003)
    for row in paths.itertuples():
        e = event.loc[row.event_id]
        start = e.signal_time + pd.Timedelta(minutes=30)
        path = minutes.loc[start:start + pd.Timedelta(minutes=row.horizon*30-1)]
        for scale, size in [('r', e.candle_range), ('a', e.atr_lag)]:
            if not np.isfinite(size):
                continue
            upper, lower = e.signal_close + .5 * size, e.signal_close - .5 * size
            up, down = path.index[path.high >= upper], path.index[path.low <= lower]
            first = 'neither'
            if len(up) and (not len(down) or up[0] < down[0]):
                first = 'up'
            elif len(down) and (not len(up) or down[0] < up[0]):
                first = 'down'
            elif len(up) and len(down):
                opening = path.loc[up[0], 'open']
                first = 'up' if opening >= upper else 'down' if opening <= lower else 'ambiguous'
            assert getattr(row, f'{scale}_first_{first}') == 1
            assert getattr(row, f'{scale}_hit_both') == bool(len(up) and len(down))

    provenance = json.loads((STUDY / 'provenance.json').read_text())
    for entry in provenance['files']:
        assert sha256(entry['path']) == entry['sha256'], entry['path']
    output = dict(upstream_feature_rows_unchanged=len(f), upstream_response_rows_unchanged=len(r),
                  matching_pairs_checked=len(p), independent_signal_paths=len(sample),
                  independent_forward_paths=len(paths), provenance_hashes_checked=len(provenance['files']),
                  verifier_sha256=sha256(Path(__file__)), status='passed')
    (STUDY / 'verification.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
