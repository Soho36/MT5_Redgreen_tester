"""Verify native whole-session replays and reconstruct baseline-plus-overlay equity."""
import json
import numpy as np
import pandas as pd
import analyze_rtl_vwap_cross as cx
import analyze_whipsaw_days as study
import whipsaw_days as wd
from prepare_whipsaw_days import LEDGERS, digest
from prepare_whipsaw_native import RUN, DOC, ROOT
from analyze_rtl_news_days import session_envelopes, envelope_dd

PERIODS = {'2016-19': ('2016-01-01', '2020-01-01'),
           '2020-26': ('2020-01-01', '2026-10-01'), '2016-26': ('2016-01-01', '2026-10-01')}


def metrics(t, e):
    n = t.net_dollars
    losses = -n[n < 0].sum()
    risk = t.groupby(['submitted', 'entry_time']).initial_risk_dollars.sum()
    return dict(contract_round_trips=len(t), net=float(n.sum()), mean_net_r=float(t.net_r.mean()),
                pf=float(n[n > 0].sum() / losses) if losses else np.nan,
                equity_dd=float(envelope_dd(e)[0]), worst_session=float(e.net.min()),
                worst_session_dd=float(e.dd.max()), max_position_risk=float(risk.max()),
                stress_extra2_net=float(n.sum() - 2 * len(t)),
                net_without_top5_sessions=float(n.sum() - e.net.nlargest(5).sum()))


def interval(values, dates):
    months, ids = np.unique(pd.DatetimeIndex(dates).to_period('M').astype(str), return_inverse=True)
    totals, counts = np.bincount(ids, weights=values), np.bincount(ids)
    w = np.random.default_rng(20261112).multinomial(len(months), np.ones(len(months)) / len(months), size=5000)
    return np.percentile((w @ totals) / (w @ counts), [2.5, 97.5]).tolist()


def combine_envelopes(base, selected, active, replace=False):
    out = base.copy()
    active = out.index.intersection(pd.DatetimeIndex(active))
    if replace:
        out.loc[active] = selected.loc[active]
    else:
        # Selected paths must equal base paths. Scaling their envelopes is then exact.
        np.testing.assert_allclose(base.loc[active], selected.loc[active], rtol=0, atol=2e-6)
        out.loc[active] *= 2
    return out


def analyze():
    manifest = json.loads((RUN / 'manifest.json').read_text())
    for name, h in manifest['prepared_sha256'].items():
        assert digest(RUN / name) == h, name
    assert digest(DOC / 'PROTOCOL.md') == manifest['protocol_sha256']
    bars = wd.read_m30()
    table = wd.session_table(bars)
    calendar = pd.DatetimeIndex(bars.bar_time.dt.normalize().unique())
    pairs = pd.read_csv(RUN / 'event_sessions.csv', parse_dates=['event', 'session'])
    trades, envelopes, rows, checks = {}, {}, [], []
    for j in manifest['jobs']:
        done = json.loads((RUN / (j['tag'] + '.completed.json')).read_text())
        for n, h in done['outputs'].items():
            assert digest(RUN / n) == h
        t = cx.economics(cx.parse_report(RUN / (j['tag'] + '.htm'), cx.INSTRUMENTS['NQ']['symbol']), cx.INSTRUMENTS['NQ'])
        assert (t.submitted.dt.normalize() == t.entry_time.dt.normalize()).all(), 'cross-date order'
        assert (t.entry_time.dt.normalize() == t.exit_time.dt.normalize()).all(), 'cross-date position'
        key = (j['strategy'], j['policy'])
        trades[key] = t
        envelopes[key] = session_envelopes(RUN / f"window_equity_{j['tag']}.bin", t, calendar)
        t.to_csv(RUN / (j['tag'] + '_trades.csv'), index=False)
        if j['policy'] == 'control':
            old = pd.read_csv(LEDGERS[j['strategy']], parse_dates=['submitted', 'entry_time', 'exit_time', 'session'])
            a, b = t.loc[t['sample'].eq('primary')], old.loc[old['sample'].eq('primary')]
        else:
            horizons = [1] if j['policy'].startswith('day1') else [1, 2, 3]
            dates = pairs.loc[pairs.horizon.isin(horizons), 'session'].unique()
            assert t.session.isin(dates).all(), 'entry on disabled session'
            a = t.loc[t['sample'].eq('primary')]
            control = trades[(j['strategy'], 'control')]
            b = control.loc[control['sample'].eq('primary') & control.session.isin(dates)]
        if j['rr'] == 1:
            assert len(a) == len(b), (key, len(a), len(b))
            for c in ('submitted', 'entry_time', 'exit_time'):
                assert np.array_equal(a[c].to_numpy(), b[c].to_numpy()), (key, c)
            for c in ('requested_price', 'original_sl', 'fill_price', 'exit_price', 'net_dollars', 'net_r'):
                np.testing.assert_allclose(a[c], b[c], atol=1e-8, rtol=0)
        checks.append(dict(strategy=j['strategy'], policy=j['policy'], primary_trades=len(a),
                           control_or_subset_match=j['rr'] == 1, all_orders_in_allowed_sessions=True))
        for era, (start, end) in PERIODS.items():
            part = t.loc[t.session.ge(start) & t.session.lt(end)]
            e = envelopes[key].loc[start:pd.Timestamp(end) - pd.Timedelta(days=1)]
            rows.append(dict(strategy=j['strategy'], policy=j['policy'], era=era, **metrics(part, e)))
        print('Verified', key, len(a), flush=True)
    overlays, horizon = [], []
    panel = wd.event_panel(bars)
    main_day1 = pd.DatetimeIndex(pairs.loc[pairs.horizon.eq(1), 'session'].unique())
    for strategy in ('rtl', 'gg'):
        base, be = trades[(strategy, 'control')], envelopes[(strategy, 'control')]
        for policy in ('day1', 'days123', 'day1_rr2'):
            selected, se = trades[(strategy, policy)], envelopes[(strategy, policy)]
            active = pairs.loc[pairs.horizon.isin([1] if policy.startswith('day1') else [1, 2, 3]), 'session'].unique()
            replace = policy == 'day1_rr2'
            oe = combine_envelopes(be, se, active, replace)
            ot = pd.concat([base.loc[~base.session.isin(active)] if replace else base, selected]).sort_values('exit_time')
            br = base.groupby('session').net_r.sum().reindex(be.index, fill_value=0)
            rr = ot.groupby('session').net_r.sum().reindex(be.index, fill_value=0)
            for era, (start, end) in PERIODS.items():
                e = oe.loc[start:pd.Timestamp(end) - pd.Timedelta(days=1)]
                old = be.reindex(e.index)
                delta = e.net - old.net
                dr = (rr - br).reindex(e.index)
                t = ot.loc[ot.session.ge(start) & ot.session.lt(end)]
                lo, hi = interval(delta, e.index)
                rlo, rhi = interval(dr, e.index)
                overlays.append(dict(strategy=strategy, policy=policy, era=era, **metrics(t, e),
                    enabled_sessions=int(e.index.isin(active).sum()), extra_net=float(delta.sum()),
                    extra_mean_per_session=float(delta.mean()), extra_mean_ci_low=lo, extra_mean_ci_high=hi,
                    extra_r_per_session=float(dr.mean()), extra_r_ci_low=rlo, extra_r_ci_high=rhi))
            oe.to_csv(RUN / f'{strategy}_{policy}_overlay_envelopes.csv')
        for h in (1, 2, 3):
            ep = pairs.loc[pairs.horizon.eq(h) & pairs.event.ge('2016-01-01') & pairs.event.lt('2026-10-01')]
            assert ep.session.is_unique
            dates = pd.DatetimeIndex(ep.session)
            for cohort, keep in [('all', np.ones(len(ep), bool)),
                                 ('not_a_new_day1', ~dates.isin(main_day1) if h > 1 else np.ones(len(ep), bool))]:
                if h == 1 and cohort != 'all':
                    continue
                ds = dates[keep]
                if not len(ds):
                    continue
                net = be.net.reindex(ds)
                r = base.groupby('session').net_r.sum().reindex(ds, fill_value=0)
                atr = panel.atr20.reindex(ep.loc[keep, 'event']).to_numpy()
                market = (table.close - table.open).reindex(ds).to_numpy() / atr
                span = (table.high - table.low).reindex(ds).to_numpy() / atr
                lo, hi = interval(net, ds)
                horizon.append(dict(strategy=strategy, horizon=h, cohort=cohort, events=len(ds),
                    also_new_day1=int(ds.isin(main_day1).sum()) if h > 1 else 0,
                    net=float(net.sum()), mean_net=float(net.mean()), mean_net_r=float(r.mean()),
                    net_ci_low=lo, net_ci_high=hi, mean_abs_market_move=float(np.mean(np.abs(market))),
                    trend_share=float(np.mean(np.abs(market) >= .6 * span))))
    for name, data in [('native_summary', rows), ('overlays', overlays), ('horizons', horizon)]:
        pd.DataFrame(data).to_csv(DOC / (name + '.csv'), index=False)
    (DOC / 'verification.json').write_text(json.dumps(dict(checks=checks, all_passed=True,
        flat_boundaries_verified=True, full_native_equity_dd_reconciled=True), indent=2))
    print(pd.DataFrame(overlays).to_string(index=False))
    print(pd.DataFrame(horizon).to_string(index=False))


if __name__ == '__main__':
    analyze()
