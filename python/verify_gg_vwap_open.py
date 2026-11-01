"""Separate feature lookup and arithmetic verification of GG_OPEN_PROTOCOL results."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Reports/gg_vwap_open_20261101'


def digest(p):
    with open(p, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    for name, expected in json.loads((OUT / 'input_manifest.json').read_text()).items():
        assert digest(ROOT / name) == expected, name
    for name, expected in json.loads((OUT / 'output_hashes.json').read_text()).items():
        assert digest(OUT / name) == expected, name
    t = pd.read_csv(ROOT / 'Reports/gg_vwap_20261030/trades_GG.csv', float_precision='round_trip')
    t = t.loc[pd.to_datetime(t.session) < pd.Timestamp('2026-10-01')].reset_index(drop=True)
    f = pd.read_csv(ROOT / 'Reports/rtl_vwap_cross_20261027/features_NQ.csv', float_precision='round_trip')
    f = f.sort_values('available_at').reset_index(drop=True)
    submitted = pd.to_datetime(t.submitted)
    pos = np.searchsorted(pd.to_datetime(f.available_at).to_numpy(), submitted.to_numpy(), side='right') - 1
    assert (pos >= 0).all()
    selected = f.iloc[pos].reset_index(drop=True)
    for c in ('open', 'close', 'high', 'low'):
        np.testing.assert_allclose(selected[c], t[c], rtol=0, atol=1e-9)
    assert (selected.close > selected.open).all()
    assert (pd.to_datetime(selected.available_at).to_numpy() <= submitted.to_numpy()).all()
    known = (pd.to_datetime(selected.feature_session).eq(submitted.dt.normalize())
             & selected.vwap_available & selected.a20.gt(0) & selected.vwap.notna())
    boundary = selected.vwap - selected.a20
    close_skip = known & selected.close.lt(boundary)
    open_skip = known & selected.open.lt(boundary)
    assert not (close_skip & ~open_skip).any()
    saved = pd.read_csv(OUT / 'trades.csv', float_precision='round_trip')
    assert saved.ticket.equals(t.ticket)
    assert np.array_equal(saved.skip_close, close_skip) and np.array_equal(saved.skip_open, open_skip)
    category = np.where(~known, 'unknown_kept', np.where(close_skip, 'both_skip',
                        np.where(open_skip, 'open_only_skip', 'both_keep')))
    assert np.array_equal(saved.group, category)
    cal = pd.read_csv(ROOT / 'Reports/rtl_vwap_cross_20261027/calendars.csv')
    calendar = pd.DatetimeIndex(pd.to_datetime(cal.loc[cal.instrument.eq('NQ'), 'session'])).sort_values()
    session = pd.to_datetime(t.session)
    saved_daily = pd.read_csv(OUT / 'daily.csv', parse_dates=['session'])
    checked = 0
    for file in ('summaries.csv', 'annual.csv', 'groups.csv'):
        table = pd.read_csv(OUT / file)
        for _, row in table.iterrows():
            label = str(row.period)
            if len(label) == 4:
                start, end = f'{label}-01-01', f'{int(label)+1}-01-01'
            else:
                start, end = f'{label[:4]}-01-01', f'{2001+int(label[-2:])}-01-01'
            end = min(end, '2026-10-01')
            scope = session.ge(start) & session.lt(end)
            days = calendar[(calendar >= start) & (calendar < end)]
            scale = 1.
            if file == 'groups.csv':
                keep = scope & (category == row.group)
            elif row.policy == 'baseline':
                keep = scope
            else:
                skip = open_skip if row.policy.startswith('open') else close_skip
                filtered = scope & ~skip
                frac = t.loc[filtered, 'initial_risk_dollars'].sum() / t.loc[scope, 'initial_risk_dollars'].sum()
                np.testing.assert_allclose(frac, row.risk_fraction, rtol=0, atol=1e-12)
                keep = scope if 'scaled' in row.policy else filtered
                if 'scaled' in row.policy:
                    scale = frac
            pnl = t.loc[keep, 'net_dollars'].to_numpy() * scale
            ids = days.get_indexer(session[keep])
            assert (ids >= 0).all()
            daily = np.bincount(ids, weights=pnl, minlength=len(days))
            if file == 'summaries.csv' and row.policy in ('baseline', 'close', 'open'):
                plotted = saved_daily.loc[saved_daily.period.eq(label) & saved_daily.policy.eq(row.policy)]
                assert np.array_equal(plotted.session.to_numpy(), days.to_numpy())
                np.testing.assert_allclose(plotted.net_dollars, daily, rtol=0, atol=1e-7)
            peak = equity = max_dd = 0.
            for x in daily:
                equity += x
                peak = max(peak, equity)
                max_dd = max(max_dd, peak - equity)
            loss = -pnl[pnl < 0].sum()
            expected = [keep.sum(), pnl.sum(), t.loc[keep, 'net_r'].mean(), (pnl > 0).mean(),
                        pnl[pnl > 0].sum() / loss if loss else np.nan, max_dd,
                        pnl.sum() / max_dd if max_dd else np.nan,
                        t.loc[keep, 'initial_risk_dollars'].sum() * scale, scale]
            actual = row[['trades', 'net_dollars', 'net_mean_r', 'win_rate', 'profit_factor',
                          'daily_close_dd', 'net_over_dd', 'planned_risk', 'scale']].to_numpy(float)
            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-7, equal_nan=True)
            checked += 1
    result = dict(all_passed=True, independently_joined_trades=len(t), metric_rows_checked=checked,
                  labels_from_frozen_features=True, input_and_output_hashes_checked=True)
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
