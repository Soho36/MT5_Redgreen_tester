"""Independent feature lookup and arithmetic checks for SLOPE_PROTOCOL.md.

Does not import the slope analyzer. Reuses the frozen, previously independently
verified M30 panel; checks both adjacent VWAP subtraction and its volume-update
identity, then reconstructs every policy, group and plotted daily series.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Reports/rtl_vwap_slope_20261101'
SOURCE = ROOT / 'Reports/rtl_vwap_cross_20261027'
PERIODS = ('2016-19', '2020-26', '2016-26', '2010-15')
POLICIES = ('baseline', 'orange', 'rising', 'orange_rising', 'known_baseline',
            'known_orange', 'rising_risk_scaled_baseline', 'combined_risk_scaled_orange')
METRICS = ('trades', 'net_dollars', 'gross_mean_r', 'net_mean_r', 'win_rate',
           'profit_factor', 'daily_close_dd', 'net_over_dd', 'planned_risk', 'scale')


def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bounds(period):
    period = str(period)
    if len(period) == 4:
        start, end = f'{period}-01-01', f'{int(period)+1}-01-01'
    else:
        start, end = f'{period[:4]}-01-01', f'{2001+int(period[-2:])}-01-01'
    return start, min(end, '2026-10-01')


def reconstructed_metrics(trades, selected, calendar, scale):
    p = trades.loc[selected, 'net_dollars'].to_numpy(float) * scale
    index = calendar.get_indexer(pd.to_datetime(trades.loc[selected, 'session']))
    assert (index >= 0).all()
    daily = np.bincount(index, weights=p, minlength=len(calendar))
    equity = peak = drawdown = 0.
    for value in daily:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    losses = -float(p[p < 0].sum())
    expected = [int(selected.sum()), float(p.sum()), trades.loc[selected, 'gross_r'].mean(),
                trades.loc[selected, 'net_r'].mean(), float((p > 0).mean()) if len(p) else np.nan,
                float(p[p > 0].sum()) / losses if losses else np.nan, drawdown,
                float(p.sum()) / drawdown if drawdown else np.nan,
                float(trades.loc[selected, 'initial_risk_dollars'].sum()) * scale, scale]
    return expected, daily


def main():
    for name, expected in json.loads((OUT / 'input_manifest.json').read_text()).items():
        assert digest(ROOT / name) == expected, f'Input changed: {name}'
    hashes = json.loads((OUT / 'output_hashes.json').read_text())
    for name, expected in hashes.items():
        assert digest(OUT / name) == expected, f'Output changed: {name}'
    original_check = json.loads((SOURCE / 'independent_verification.json').read_text())
    assert original_check['all_passed']

    original = pd.read_csv(SOURCE / 'trades_NQ.csv', float_precision='round_trip', low_memory=False)
    original = original.loc[pd.to_datetime(original.session) < pd.Timestamp('2026-10-01')]
    saved = pd.read_csv(OUT / 'trades.csv', float_precision='round_trip', low_memory=False)
    assert original.ticket.is_unique and saved.ticket.is_unique
    assert set(original.ticket) == set(saved.ticket)
    t = original.set_index('ticket').loc[saved.ticket].reset_index()
    assert len(t) == 25832
    for column in ('submitted', 'bar_time', 'entry_time', 'exit_time', 'session'):
        assert np.array_equal(pd.to_datetime(t[column]), pd.to_datetime(saved[column])), column
    for column in ('requested_price', 'original_sl', 'open', 'close', 'high', 'low',
                   'trade_profit', 'net_dollars', 'gross_r', 'net_r', 'initial_risk_dollars'):
        np.testing.assert_allclose(saved[column], t[column], atol=1e-9, rtol=0, err_msg=column)

    features = pd.read_csv(SOURCE / 'features_NQ.csv', float_precision='round_trip')
    features = features.sort_values('available_at').reset_index(drop=True)
    submitted = pd.to_datetime(t.submitted)
    session = pd.to_datetime(t.session)
    available = pd.to_datetime(features.available_at).to_numpy()
    pos = np.searchsorted(available, submitted.to_numpy(), side='right') - 1
    assert (pos >= 0).all()
    current = features.iloc[pos].reset_index(drop=True)
    previous = features.iloc[np.maximum(pos - 1, 0)].reset_index(drop=True)
    assert (pd.to_datetime(current.available_at).to_numpy() <= submitted.to_numpy()).all()
    assert np.array_equal(pd.to_datetime(current.bar_time), pd.to_datetime(t.bar_time))
    for column in ('open', 'close', 'high', 'low'):
        np.testing.assert_allclose(current[column], t[column], rtol=0, atol=1e-9)
    assert (current.close < current.open).all()
    np.testing.assert_allclose(current.high, t.requested_price, rtol=0, atol=1e-9)
    np.testing.assert_allclose(current.low, t.original_sl, rtol=0, atol=1e-9)

    stale = pd.to_datetime(current.feature_session).ne(submitted.dt.normalize())
    same_session = current.feature_session.eq(previous.feature_session)
    adjacent = (pd.to_datetime(current.bar_time) - pd.to_datetime(previous.bar_time)).eq(pd.Timedelta(minutes=30))
    vwap_valid = current.vwap_available & previous.vwap_available & np.isfinite(current.vwap) & np.isfinite(previous.vwap)
    added_volume = current.cum_volume - previous.cum_volume
    volume_valid = np.isfinite(added_volume) & added_volume.gt(0) & previous.cum_volume.gt(0)
    known = (pos > 0) & same_session & adjacent & vwap_valid & volume_valid & ~stale
    delta = current.vwap - previous.vwap
    state = np.where(~known, 'unknown', np.where(delta.gt(0), 'up', np.where(delta.lt(0), 'down', 'flat')))
    assert np.array_equal(saved.slope_state, state), 'Slope states'
    np.testing.assert_allclose(saved.slope_delta, delta.where(known), atol=1e-10, rtol=0, equal_nan=True)
    normalized = (delta / current.a20).where(known & current.a20.gt(0))
    np.testing.assert_allclose(saved.slope_per_a20, normalized, atol=1e-10, rtol=0, equal_nan=True)

    # Independent cumulative update: v/(Vprev+v) * (bar VW price - VWAPprev).
    np.testing.assert_allclose(added_volume[known], current.volume[known], rtol=0, atol=1e-6)
    identity = (current.volume / current.cum_volume) * (current.pv_hlc3 / current.volume - previous.vwap)
    residual = np.abs(identity[known] - delta[known])
    np.testing.assert_allclose(identity[known], delta[known], rtol=0, atol=1e-8)
    sign_disagree = known & np.sign(identity).ne(np.sign(delta))
    assert (np.abs(delta[sign_disagree]) <= 1e-8).all(), 'Non-roundoff slope identity sign mismatch'

    orange_known = ~stale & current.vwap_available & np.isfinite(current.vwap) & current.a20.gt(0)
    orange = ~(orange_known & current.close.lt(current.vwap - current.a20))
    assert np.array_equal(orange, t.distance.ne('far_below'))
    assert np.array_equal(orange, saved.orange_keep)
    rising = pd.Series(state == 'up')
    slope_known = pd.Series(state != 'unknown')
    reasons = saved.slope_reason.fillna('')
    expected_reason = np.where((pos == 0) | ~same_session, 'session_start',
                      np.where(~adjacent, 'time_gap', np.where(~vwap_valid, 'unavailable_vwap',
                      np.where(~volume_valid, 'no_added_volume', ''))))
    expected_reason = np.where(stale, 'submission_session_reset', expected_reason)
    assert np.array_equal(reasons, expected_reason), 'Slope unknown reasons'

    cal = pd.read_csv(SOURCE / 'calendars.csv', parse_dates=['session'])
    observed = pd.DatetimeIndex(cal.loc[cal.instrument.eq('NQ'), 'session']).sort_values()
    daily_saved = pd.read_csv(OUT / 'daily.csv', parse_dates=['session'])
    counts = dict(metric_rows=0, daily_series=0)
    for filename in ('summaries.csv', 'annual.csv', 'groups.csv', 'unknown_reasons.csv'):
        rows = pd.read_csv(OUT / filename)
        if filename == 'summaries.csv':
            assert set(zip(rows.period.astype(str), rows.policy)) == {(p, q) for p in PERIODS for q in POLICIES}
            assert len(rows) == len(PERIODS) * len(POLICIES)
        if filename == 'annual.csv':
            assert set(zip(rows.period.astype(str), rows.policy)) == {(str(y), q) for y in range(2010, 2027) for q in POLICIES}
            assert len(rows) == 17 * len(POLICIES)
        if filename == 'groups.csv':
            expected_groups = {(p, scope, state) for p in PERIODS
                               for scope in ('all', 'orange_kept', 'orange_skipped')
                               for state in ('up', 'down', 'flat', 'unknown')}
            assert set(zip(rows.period.astype(str), rows.scope, rows.state)) == expected_groups
            assert len(rows) == len(expected_groups)
        if filename == 'unknown_reasons.csv':
            expected_reasons = set()
            for period in PERIODS:
                start, end = bounds(period)
                inside = session.ge(start) & session.lt(end) & ~slope_known
                expected_reasons.update((period, str(reason)) for reason in reasons[inside].unique())
            assert set(zip(rows.period.astype(str), rows.reason)) == expected_reasons
            assert len(rows) == len(expected_reasons)
        for _, row in rows.iterrows():
            start, end = bounds(row.period)
            scope = session.ge(start) & session.lt(end)
            calendar = observed[(observed >= start) & (observed < end)]
            scale = 1.
            if filename == 'groups.csv':
                keep = scope & (state == row.state)
                if row.scope == 'orange_kept':
                    keep &= orange
                elif row.scope == 'orange_skipped':
                    keep &= ~orange
                else:
                    assert row.scope == 'all'
            elif filename == 'unknown_reasons.csv':
                keep = scope & ~slope_known & reasons.eq(row.reason)
            else:
                masks = dict(baseline=scope, orange=scope & orange, rising=scope & rising,
                             orange_rising=scope & orange & rising, known_baseline=scope & slope_known,
                             known_orange=scope & orange & slope_known,
                             rising_risk_scaled_baseline=scope,
                             combined_risk_scaled_orange=scope & orange)
                keep = masks[row.policy]
                if row.policy == 'rising_risk_scaled_baseline':
                    scale = t.loc[scope & rising, 'initial_risk_dollars'].sum() / t.loc[scope, 'initial_risk_dollars'].sum()
                elif row.policy == 'combined_risk_scaled_orange':
                    scale = t.loc[scope & orange & rising, 'initial_risk_dollars'].sum() / t.loc[scope & orange, 'initial_risk_dollars'].sum()
                fraction = t.loc[keep, 'initial_risk_dollars'].sum() * scale / t.loc[scope, 'initial_risk_dollars'].sum()
                np.testing.assert_allclose(row.risk_fraction, fraction, rtol=0, atol=1e-12)
            expected, daily = reconstructed_metrics(t, keep, calendar, scale)
            np.testing.assert_allclose(row[list(METRICS)].to_numpy(float), expected,
                                       rtol=0, atol=1e-7, equal_nan=True,
                                       err_msg=f'{filename} {row.to_dict()}')
            counts['metric_rows'] += 1
            if filename == 'summaries.csv' and row.policy in ('baseline', 'orange', 'rising', 'orange_rising'):
                chart = daily_saved.loc[daily_saved.period.eq(str(row.period)) & daily_saved.policy.eq(row.policy)]
                assert np.array_equal(chart.session.to_numpy(), calendar.to_numpy())
                np.testing.assert_allclose(chart.net_dollars, daily, atol=1e-7, rtol=0)
                counts['daily_series'] += 1
    distributions = pd.read_csv(OUT / 'slope_distribution.csv')
    assert set(zip(distributions.period, distributions.measure)) == {
        (p, m) for p in PERIODS for m in ('slope_delta', 'slope_per_a20')}
    assert len(distributions) == 8
    for _, row in distributions.iterrows():
        start, end = bounds(row.period)
        inside = session.ge(start) & session.lt(end)
        values = (delta.where(known) if row.measure == 'slope_delta' else normalized).loc[inside].dropna()
        expected = [len(values), values.min(), values.median(), values.max(),
                    int((values.abs().le(1e-9) & values.ne(0)).sum())]
        actual = row[['count', 'minimum', 'median', 'maximum', 'near_zero_nonflat']].to_numpy(float)
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-10)
    result = dict(all_passed=True, independently_joined_trades=len(t), **counts,
                  distribution_rows_checked=len(distributions),
                  slope_states=pd.Series(state).value_counts().to_dict(),
                  max_vwap_update_identity_residual=float(residual.max()),
                  identity_sign_disagreements_within_roundoff=int(sign_disagree.sum()),
                  known_delta_within_1e_minus_9=int((known & delta.abs().le(1e-9)).sum()),
                  input_and_output_hashes_checked=True)
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
