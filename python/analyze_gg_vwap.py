"""Exploratory test of the far-below VWAP rule on GG, NQ (ledger omission).

Protocol: docs/baseline/rtl-vwap/GG_PROTOCOL.md. Uses the cross test's code
(analyze_rtl_vwap_cross.py) and its frozen NQ features unchanged.
`prepare` reconciles and labels trades and computes no outcome;
`analyze` reads outcomes only after every source check in `prepare` passed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_rtl_vwap as av
import analyze_rtl_vwap_cross as cx
import build_rtl_vwap_features as vw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/gg_vwap_20261030'
PROTOCOL = ROOT / 'docs/baseline/rtl-vwap/GG_PROTOCOL.md'
PROTOCOL_SHA256 = '803d3444f118f88a2e03580e3745be88e28ab408edcb3b156669bd0fdcba779d'
CROSS = ROOT / 'Reports/rtl_vwap_cross_20261027'
NAME = 'GG'
SPEC = dict(role='primary', runs=cx.YM_RUNS, tag='ymbase_20261023_gg_nq', symbol='MNQcontDTBNT20102026_2',
            point_value=2.0, primary=cx.EARLY, secondary=cx.OLD)
SETTINGS = ('MinGreenRun=1', 'MaxGreenRun=0', 'MinLocation=0', 'RiskReward=1.0', 'FlattenFallback=true',
            'UseEarlyCloseCalendar=true', 'Period=M30', 'Model=1')
BOOT_SEED, PLACEBO_SEED = 202610300, 202610310
# Hashes copied from the frozen protocol's input table.
FROZEN = {
    cx.YM_RUNS/'ymbase_20261023_gg_nq.htm': '031d4f2cff7cdfe07b8704ffd3277517684756c64f1ce3bb536442611da9600d',
    cx.YM_RUNS/'runband_ymbase_20261023_gg_nq_1.00.csv': '091a3eeb2dae54698df78fb6860939593564c123681646efe822fd0e9333b459',
    cx.YM_RUNS/'runband_ymbase_20261023_gg_nq_1.00_stats.csv': '6dea87bb5cdf704ad529af25e1e6eef0f4f6a91e98332ae5dbf60a3344d9be4c',
    CROSS/'features_NQ.csv': 'd88bbd10f82df2b6bb428b418b5cbbdb3c13f8baea3fa2d6ae491656d3bc92d6',
    CROSS/'trades_NQ.csv': '1c8537e0eca9de7a0470e9e6a9668687d3a09c0387c664b182c6d0f6f7ddaf3e',
    CROSS/'calendars.csv': '64be3ff61751cc8237c82f5c4adad9e70e73f698d59715195c5e8586b0866141',
}
PUBLISHED = {'2016-19': (6388, 3635.60), '2020-26': (11181, 39315.45), '2010-15': (8935, -5108.25)}
FEATURE_DATES = ('bar_time', 'available_at', 'feature_session', 'first_minute', 'last_minute')
LABEL_COLUMNS = ('z', 'distance', 'unknown_reason', 'vwap', 'a20', 'roll_clean')


def reconcile():
    """The cross test's reconciliation with the GG run's settings in place of RTL's."""
    rtl_settings, cx.SETTINGS = cx.SETTINGS, SETTINGS
    try:
        return cx.reconcile(SPEC)
    finally:
        cx.SETTINGS = rtl_settings


def load_features():
    return av.dates(pd.read_csv(CROSS/'features_NQ.csv', float_precision='round_trip'), FEATURE_DATES)


def nq_calendar():
    calendars = pd.read_csv(CROSS/'calendars.csv', parse_dates=['session'])
    return pd.DatetimeIndex(calendars.loc[calendars.instrument.eq('NQ'), 'session']).sort_values()


def load_rtl():
    return av.dates(pd.read_csv(CROSS/'trades_NQ.csv', float_precision='round_trip', low_memory=False), cx.DATE_COLUMNS)


def relabel_check(features, trade_columns):
    """The loaded features must give the cross test's RTL labels back exactly."""
    saved = load_rtl().sort_values(['submitted', 'ticket'], kind='stable').reset_index(drop=True)
    again = vw.label_trades(saved[list(trade_columns)], features).reset_index(drop=True)
    assert np.array_equal(again.ticket.to_numpy(), saved.ticket.to_numpy())
    differing = [c for c in LABEL_COLUMNS if not cx.same(again[c], saved[c])]
    assert not differing, f'RTL labels differ: {differing}'
    return dict(rtl_trades=len(saved), columns_identical=list(LABEL_COLUMNS))


def signal_bar_check(labelled):
    """Labelled bar must be the green signal bar: high = buy stop, low = stop."""
    scope = labelled.loc[labelled.session < cx.END]
    match = (np.isclose(scope.requested_price, scope.high, rtol=0, atol=1e-9)
             & np.isclose(scope.original_sl, scope.low, rtol=0, atol=1e-9) & scope.close.gt(scope.open))
    bad = scope.loc[~match, ['ticket', 'submitted', 'requested_price', 'high', 'original_sl', 'low', 'open', 'close']]
    share = float(len(bad)/len(scope))
    assert share <= .001, f'Signal-bar mismatches {len(bad)} of {len(scope)}'
    return dict(checked=len(scope), mismatches=len(bad), share=share, examples=bad.head(20).astype(str).to_dict('records'))


def prepare():
    assert av.digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol changed'
    for path, value in {**FROZEN, **{p: v for p, v in cx.FROZEN.items() if 'MNQ_16_YEARS' in str(p)}}.items():
        assert av.digest(path) == value, f'Frozen input changed: {path}'
    OUT.mkdir(parents=True, exist_ok=True)
    report, source = reconcile()
    trades = cx.economics(report, SPEC)
    published = {}
    for era, (count, net) in PUBLISHED.items():
        part = trades.loc[trades.era.eq(era)]
        assert len(part) == count and np.isclose(part.net_dollars.sum(), net, rtol=0, atol=.005), era
        published[era] = dict(trades=len(part), net_dollars=round(float(part.net_dollars.sum()), 2))
    features = load_features()
    source['cross_date'] = cx.explain_cross_date(report.loc[report.submitted < cx.END], features)
    reference = relabel_check(features, trades.columns)
    labelled = vw.label_trades(trades, features)
    assert len(labelled) == len(trades) and labelled.ticket.is_unique
    calendar = nq_calendar()
    in_sample = labelled.loc[labelled['sample'].ne('excluded')]
    assert in_sample.session.isin(calendar).all()
    audit = dict(protocol_sha256=PROTOCOL_SHA256, inputs_verified=len(FROZEN)+2, source=source, published=published,
                 rtl_relabel=reference, signal_bar=signal_bar_check(labelled),
                 sample_trades=in_sample.groupby(['sample', 'era']).size().rename('n').reset_index().to_dict('records'),
                 labels=in_sample.groupby(['era', 'distance']).size().rename('n').reset_index().to_dict('records'),
                 unknown_reasons=in_sample.unknown_reason.fillna('').value_counts().to_dict())
    labelled.to_csv(OUT/'trades_GG.csv', index=False, float_format='%.17g')
    audit['outputs_sha256'] = {'trades_GG.csv': av.digest(OUT/'trades_GG.csv')}
    audit['all_passed'] = True
    av.save_json(OUT/'source_audit.json', cx.plain(audit))
    print(f"GG: {len(trades):,} trades reconciled, signal-bar mismatches {audit['signal_bar']['mismatches']}, "
          f"RTL relabel identical ({reference['rtl_trades']:,} trades)", flush=True)
    print('All source checks passed; no outcome computed.', flush=True)


def combined(frame, rtl, periods, eras):
    """RTL + GG daily account: no gate, gate on RTL only, gate on both (descriptive)."""
    rows = []
    for p, cal in periods.items():
        g = frame if p == 'pooled' else frame.loc[frame.era.eq(p)]
        r = rtl.loc[rtl.era.isin(eras)] if p == 'pooled' else rtl.loc[rtl.era.eq(p)]
        g_far, r_far = g.distance.eq('far_below'), r.distance.eq('far_below')
        for gate, parts in (('none', (r, g)), ('rtl_only', (r.loc[~r_far], g)), ('both', (r.loc[~r_far], g.loc[~g_far]))):
            both = pd.concat([part[['session', 'net_dollars']] for part in parts])
            daily = both.groupby('session').net_dollars.sum().reindex(cal, fill_value=0.)
            assert daily.index.equals(cal) and both.session.isin(cal).all()
            rows.append(dict(period=p, gate=gate, rtl_trades=len(parts[0]), gg_trades=len(parts[1]),
                             net_dollars=float(both.net_dollars.sum()), daily_close_dd=av.max_dd(daily.to_numpy())))
    return rows


def analyze():
    assert av.digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol changed'
    audit = json.loads((OUT/'source_audit.json').read_text(encoding='utf-8'))
    assert audit['all_passed']
    for file, value in audit['outputs_sha256'].items():
        assert av.digest(OUT/file) == value, f'Prepared output changed: {file}'
    trades = av.dates(pd.read_csv(OUT/'trades_GG.csv', float_precision='round_trip', low_memory=False), cx.DATE_COLUMNS)
    rtl = load_rtl()
    observed = nq_calendar()
    boot_rng, placebo_rng = np.random.default_rng(BOOT_SEED), np.random.default_rng(PLACEBO_SEED)
    tables = {key: [] for key in ('summaries', 'contrast', 'contrast_cells', 'placebos', 'placebo_draws', 'annual',
                                  'roll_clean', 'combined', 'verdict')}
    masks_out, boot_out = {}, {}
    for sample in ('primary', 'secondary'):
        eras = SPEC[sample]
        role = SPEC['role'] if sample == 'primary' else 'secondary'
        frame = trades.loc[trades['sample'].eq(sample)].sort_values(['submitted', 'ticket'], kind='stable').reset_index(drop=True)
        start, stop = min(s for s, _ in eras.values()), max(e for _, e in eras.values())
        periods = {'pooled': observed[(observed >= start) & (observed < stop)]} if len(eras) > 1 else {}
        periods.update({era: observed[(observed >= s) & (observed < e)] for era, (s, e) in eras.items()})
        far = frame.distance.eq('far_below').to_numpy()
        pnl, risk, r = (frame[c].to_numpy(float) for c in ('net_dollars', 'initial_risk_dollars', 'net_r'))
        era_index = frame.era.map({era: i for i, era in enumerate(eras)}).to_numpy()
        deciles, tertiles = np.empty(len(frame), int), np.empty(len(frame), int)
        for i, era in enumerate(eras):
            inside = era_index == i
            deciles[inside] = cx.rank_groups(frame.loc[inside], 10)
            tertiles[inside] = cx.rank_groups(frame.loc[inside], 3)
        cells = era_index*10+deciles
        months = frame.submitted.dt.to_period('M').astype(str).to_numpy()
        month_cells = pd.factorize(pd.Series(months)+'_'+pd.Series(tertiles).astype(str))[0]
        members = {p: (np.ones(len(frame), bool) if p == 'pooled' else frame.era.eq(p).to_numpy()) for p in periods}
        days = {p: cal.get_indexer(frame.session) for p, cal in periods.items()}
        for p in periods:
            assert (days[p][members[p]] >= 0).all(), (sample, p)
        head = dict(instrument=NAME, role=role, sample=sample)
        for p, cal in periods.items():
            rows, _ = av.policy_comparison(frame.loc[members[p]], cal, 'skip_far_below', with_sessions=False)
            tables['summaries'].extend(dict(head, period=p, **row) for row in rows)
        # A. Risk-matched contrast; bootstrap on the sample (pooled when two eras).
        sample_period = 'pooled' if 'pooled' in periods else next(iter(periods))
        first, last = periods[sample_period][0], periods[sample_period][-1]
        weeks = pd.date_range(first-pd.Timedelta(days=first.dayofweek), last-pd.Timedelta(days=last.dayofweek), freq='7D')
        week_pos = weeks.get_indexer(frame.week_start)
        assert (week_pos >= 0).all()
        values, left_out, starts = cx.contrast_bootstrap(r, far, cells, week_pos, len(weeks), boot_rng)
        boot_out.update({f'{sample}_values': values, f'{sample}_left_out': left_out, f'{sample}_starts': starts,
                         f'{sample}_weeks': weeks.to_numpy().astype('datetime64[D]').astype(np.int64)})
        finite = values[np.isfinite(values)]
        low, high = np.quantile(finite, [.025, .975], method='linear')
        for p in periods:
            estimate, cell_frame = cx.contrast(r, far, cells, members[p])
            tables['contrast_cells'].extend(dict(head, period=p, **row) for row in cell_frame.to_dict('records'))
            row = dict(head, period=p, estimate=estimate, cells=len(cell_frame), cells_used=int(cell_frame.used.sum()),
                       negative_cells=int((cell_frame.difference < 0).sum()),
                       far_trades=int(far[members[p]].sum()), far_active_weeks=int(frame.loc[members[p] & far, 'week_start'].nunique()))
            if p == sample_period:
                row.update(ci95_low=float(low), ci95_high=float(high), boot_draws=len(values), boot_valid=len(finite),
                           boot_mean_left_out=float(left_out.mean()), boot_max_left_out=int(left_out.max()))
            tables['contrast'].append(row)
        # B. Placebos without VWAP (pooled draws; eras restrict the same draws).
        b1, short1 = cx.cell_placebo(far, cells, placebo_rng)
        b2, offsets = cx.rolled_placebo(far, months, placebo_rng)
        b3, short3 = cx.cell_placebo(far, month_cells, placebo_rng)
        b4 = cx.largest_risk(frame, far)[None, :]
        masks_out.update({f'{sample}_tickets': frame.ticket.to_numpy(), f'{sample}_far': far, f'{sample}_cells': cells,
                          f'{sample}_month_cells': month_cells, f'{sample}_B2_offsets': offsets, f'{sample}_B4': b4[0]})
        for key, masks in (('B1', b1), ('B2', b2), ('B3', b3)):
            masks_out[f'{sample}_{key}'] = np.packbits(masks, axis=1)
        for p, cal in periods.items():
            rule = cx.period_stats(far[None, :], pnl, risk, members[p], days[p], len(cal))[0]
            retained = next(row for row in tables['summaries'] if row['sample'] == sample and row['period'] == p
                            and row['curve'] == 'retained')
            assert np.isclose(rule[0], retained['net_dollars'], rtol=0, atol=1e-6)
            assert np.isclose(rule[1], retained['daily_close_dd'], rtol=0, atol=1e-6)
            for key, masks, shortfall in (('B1', b1, short1), ('B2', b2, 0), ('B3', b3, short3), ('B4', b4, 0)):
                stats = cx.period_stats(masks, pnl, risk, members[p], days[p], len(cal))
                if key != 'B4':
                    tables['placebo_draws'].append(pd.DataFrame(dict(instrument=NAME, sample=sample, period=p, placebo=key,
                        draw=np.arange(len(stats)), net_dollars=stats[:, 0], daily_close_dd=stats[:, 1], risk_kept=stats[:, 2])))
                q = np.quantile(stats, [.05, .5, .95], axis=0)
                tables['placebos'].append(dict(head, period=p, placebo=key, draws=len(stats),
                    shortfall=shortfall if p == 'pooled' or len(periods) == 1 else np.nan,
                    rule_net=rule[0], rule_dd=rule[1], rule_risk_kept=rule[2],
                    net_q05=q[0, 0], net_median=q[1, 0], net_q95=q[2, 0], dd_q05=q[0, 1], dd_median=q[1, 1],
                    dd_q95=q[2, 1], risk_kept_median=q[1, 2],
                    rule_beats_dd=float(np.mean(stats[:, 1] > rule[1]+cx.TIE)),
                    ties_dd=float(np.mean(np.abs(stats[:, 1]-rule[1]) <= cx.TIE)),
                    rule_beats_net=float(np.mean(stats[:, 0] < rule[0]-cx.TIE)),
                    ties_net=float(np.mean(np.abs(stats[:, 0]-rule[0]) <= cx.TIE))))
        # C. Annual, roll-clean and the combined RTL + GG account (descriptive).
        for year in sorted(frame.year.unique()):
            cal = periods[sample_period]
            cal = cal[cal.year == year]
            part = frame.year.eq(year).to_numpy()
            ids = cal.get_indexer(frame.session[part])
            p_pnl, p_far = pnl[part], far[part]
            tables['annual'].append(dict(head, year=int(year), trades=int(part.sum()), far_trades=int(p_far.sum()),
                baseline_net=float(p_pnl.sum()), rule_net=float(p_pnl[~p_far].sum()),
                baseline_dd=av.max_dd(np.bincount(ids, weights=p_pnl, minlength=len(cal))),
                rule_dd=av.max_dd(np.bincount(ids[~p_far], weights=p_pnl[~p_far], minlength=len(cal)))))
        clean = frame.roll_clean.to_numpy(bool)
        for p, cal in periods.items():
            rows, _ = av.policy_comparison(frame.loc[members[p] & clean], cal, 'skip_far_below', with_sessions=False)
            estimate, cell_frame = cx.contrast(r, far, cells, members[p] & clean)
            for row in rows:
                tables['roll_clean'].append(dict(head, period=p, contrast_estimate=estimate,
                                                 contrast_negative_cells=int((cell_frame.difference < 0).sum()), **row))
        tables['combined'].extend(dict(head, **row) for row in combined(frame, rtl, periods, list(eras)))
        tables['verdict'].append(cx.verdict_row(head, eras, sample_period, tables))
    np.savez_compressed(OUT/'placebo_masks_GG.npz', **masks_out)
    np.savez_compressed(OUT/'bootstrap_GG.npz', **boot_out)
    write_outputs(tables)


def write_outputs(tables):
    frames = {}
    for key, rows in tables.items():
        frames[key] = pd.concat(rows, ignore_index=True) if key == 'placebo_draws' else pd.DataFrame(rows)
        frames[key].to_csv(OUT/f'{key}.csv', index=False, float_format='%.15g')
    verdict = frames['verdict']
    primary = verdict.loc[verdict['sample'].eq('primary')].iloc[0]
    overall = 'consistent with RTL' if primary.confirms else 'not consistent'
    av.save_json(OUT/'verdict.json', cx.plain(dict(overall=overall, exploratory=True, primary=primary.to_dict(),
                                                   secondary=verdict.loc[verdict['sample'].eq('secondary')].to_dict('records'))))
    provenance = dict(protocol_sha256=PROTOCOL_SHA256, inputs_sha256={str(k): v for k, v in FROZEN.items()},
                      programs_sha256={p.name: av.digest(p) for p in (Path(__file__), Path(cx.__file__), Path(vw.__file__),
                                                                       Path(av.__file__))},
                      outputs_sha256={p.name: av.digest(p) for p in sorted(OUT.glob('*')) if p.suffix in ('.csv', '.npz', '.json')
                                      and p.name not in ('provenance.json', 'independent_verification.json')},
                      seeds=dict(bootstrap=BOOT_SEED, placebos=PLACEBO_SEED),
                      draws=dict(bootstrap=cx.BOOT_DRAWS, placebos=cx.PLACEBO_DRAWS),
                      software=dict(numpy=np.__version__, pandas=pd.__version__), exploratory=True, replay=False)
    av.save_json(OUT/'provenance.json', provenance)
    print(verdict.to_string(index=False))
    print(f'Verdict (exploratory): {overall}.', flush=True)


if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    assert stage in ('prepare', 'analyze', 'all')
    if stage in ('prepare', 'all'):
        prepare()
    if stage in ('analyze', 'all'):
        analyze()
