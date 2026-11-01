"""Descriptive GG open-versus-close cutoff study; see GG_OPEN_PROTOCOL.md."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_gg_vwap as gg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Reports/gg_vwap_open_20261101'
DOC = ROOT / 'docs/baseline/rtl-vwap'
PERIODS = {'2016-19': ('2016-01-01', '2020-01-01'),
           '2020-26': ('2020-01-01', '2026-10-01'),
           '2016-26': ('2016-01-01', '2026-10-01'),
           '2010-15': ('2010-01-01', '2016-01-01')}


def sha(p):
    with open(p, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def dd(values):
    equity = np.r_[0., np.cumsum(values)]
    return float((np.maximum.accumulate(equity) - equity).max())


def metrics(frame, calendar, scale=1.):
    pnl = frame.net_dollars * scale
    daily = pnl.groupby(frame.session).sum().reindex(calendar, fill_value=0.)
    net, drawdown = float(pnl.sum()), dd(daily)
    loss = -float(pnl[pnl < 0].sum())
    return dict(trades=len(frame), net_dollars=net, net_mean_r=float(frame.net_r.mean()),
                win_rate=float((pnl > 0).mean()), profit_factor=float(pnl[pnl > 0].sum()) / loss if loss else np.nan,
                daily_close_dd=drawdown, net_over_dd=net / drawdown if drawdown else np.nan,
                planned_risk=float(frame.initial_risk_dollars.sum()) * scale, scale=scale)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = gg.OUT / 'trades_GG.csv'
    audit = json.loads((gg.OUT / 'source_audit.json').read_text())
    independent = json.loads((gg.OUT / 'independent_verification.json').read_text())
    assert audit['all_passed'] and independent['all_passed']
    assert sha(source) == audit['outputs_sha256'][source.name]
    for path, digest in gg.FROZEN.items():
        assert sha(path) == digest, path
    inputs = [source, gg.OUT / 'source_audit.json', gg.OUT / 'independent_verification.json',
              gg.OUT / 'summaries.csv', DOC / 'GG_OPEN_PROTOCOL.md', *gg.FROZEN]
    save('input_manifest.json', {str(p.relative_to(ROOT)): sha(p) for p in inputs})
    t = pd.read_csv(source, float_precision='round_trip', low_memory=False)
    for c in ('submitted', 'session', 'bar_time', 'available_at', 'feature_session'):
        t[c] = pd.to_datetime(t[c])
    t = t.loc[t.session < '2026-10-01'].copy()
    assert t.ticket.is_unique and (t.close > t.open).all()
    assert (t.available_at <= t.submitted).all()
    assert np.allclose(t.high, t.requested_price, rtol=0, atol=1e-9)
    assert np.allclose(t.low, t.original_sl, rtol=0, atol=1e-9)
    known = t.vwap_available & t.a20.gt(0) & t.vwap.notna() & t.feature_session.eq(t.session)
    assert np.array_equal(known, t.distance.ne('unknown'))
    t['cutoff'] = t.vwap - t.a20
    t['skip_close'] = known & (t.close < t.cutoff)
    t['skip_open'] = known & (t.open < t.cutoff)
    assert np.array_equal(t.skip_close, t.distance.eq('far_below'))
    assert not (t.skip_close & ~t.skip_open).any()
    t['group'] = np.select([~known, t.skip_close, t.skip_open],
                           ['unknown_kept', 'both_skip', 'open_only_skip'], default='both_keep')
    t.to_csv(OUT / 'trades.csv', index=False, float_format='%.17g')
    cal = gg.nq_calendar()
    old = pd.read_csv(gg.OUT / 'summaries.csv')
    summaries, groups, annual, daily_out = [], [], [], []
    scopes = [(name, start, end, False) for name, (start, end) in PERIODS.items()]
    scopes += [(str(y), f'{y}-01-01', f'{y+1}-01-01' if y < 2026 else '2026-10-01', True)
               for y in range(2010, 2027)]
    for name, start, end, yearly in scopes:
        part = t.loc[t.session.ge(start) & t.session.lt(end)]
        calendar = cal[(cal >= start) & (cal < end)]
        assert part.session.isin(calendar).all()
        rows = []
        for policy, mask in [('baseline', np.ones(len(part), bool)),
                             ('close', ~part.skip_close), ('open', ~part.skip_open)]:
            kept = part.loc[mask]
            row = dict(period=name, policy=policy, **metrics(kept, calendar))
            row['risk_fraction'] = kept.initial_risk_dollars.sum() / part.initial_risk_dollars.sum()
            rows.append(row)
            if not yearly:
                d = kept.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.)
                daily_out.append(pd.DataFrame(dict(period=name, policy=policy, session=calendar, net_dollars=d.values)))
                if policy != 'open':
                    ref = old.loc[old.period.eq('pooled' if name == '2016-26' else name)
                                  & old.curve.eq('retained' if policy == 'close' else 'baseline')].iloc[0]
                    assert row['trades'] == ref.trades
                    for c in ('net_dollars', 'net_mean_r', 'daily_close_dd'):
                        assert np.isclose(row[c], ref[c], rtol=0, atol=1e-6), (name, policy, c)
        for policy in ('close', 'open'):
            fraction = next(r['risk_fraction'] for r in rows if r['policy'] == policy)
            rows.append(dict(period=name, policy=f'{policy}_risk_scaled_baseline',
                             **metrics(part, calendar, fraction), risk_fraction=fraction))
        (annual if yearly else summaries).extend(rows)
        for group in ('both_skip', 'open_only_skip', 'both_keep', 'unknown_kept'):
            groups.append(dict(period=name, annual=yearly, group=group,
                               **metrics(part.loc[part.group.eq(group)], calendar)))
        extra = part.loc[part.group.eq('open_only_skip'), 'net_dollars'].sum()
        assert np.isclose(rows[1]['net_dollars'] - rows[2]['net_dollars'], extra, rtol=0, atol=1e-7)
    for name, data in [('summaries', summaries), ('groups', groups), ('annual', annual)]:
        pd.DataFrame(data).to_csv(OUT / f'{name}.csv', index=False, float_format='%.17g')
    pd.concat(daily_out).to_csv(OUT / 'daily.csv', index=False, float_format='%.17g')
    save('source_checks.json', dict(all_passed=True, trades=len(t),
         green_signal_bars=True, close_labels_reproduced=True, close_summaries_reproduced=True,
         close_skip_subset_of_open_skip=True, incremental_profit_decomposition=True))
    save('output_hashes.json', {p.name: sha(p) for p in OUT.glob('*.csv')})
    print(pd.DataFrame(summaries).to_string(index=False))
    print('\nAdditional open-only skipped group:')
    print(pd.DataFrame(groups).query("annual == False and group == 'open_only_skip'").to_string(index=False))


if __name__ == '__main__':
    main()
