"""Independent verification of the exploratory GG VWAP test (GG_PROTOCOL.md).

Separate code from analyze_gg_vwap.py: the cross test's independent verifier
(HTMLParser report parsing, literal minute-to-M30 features and labels, drawdowns,
contrast) rebuilds every GG label from raw NQ minutes and recomputes the summaries,
contrast, every saved bootstrap and placebo draw, the verdict and the combined account.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import verify_rtl_vwap_cross as ind
from verify_rtl_vwap_cross import ROOT, close, deciles, label, maxdd, sha, weighted_contrast

OUT = ROOT / 'Reports/gg_vwap_20261030'
PROTOCOL = ROOT / 'docs/baseline/rtl-vwap/GG_PROTOCOL.md'
PROTOCOL_SHA = '803d3444f118f88a2e03580e3745be88e28ab408edcb3b156669bd0fdcba779d'
CROSS = ROOT / 'Reports/rtl_vwap_cross_20261027'
STEM = ind.DATA / 'MNQ_16_YEARS/MT5_NQ_continuous_2010-2026'
SAMPLES = (('primary', ind.EARLY), ('secondary', {'2010-15': ('2010-01-01', '2016-01-01')}))
PUBLISHED = {'2016-19': (6388, 3635.60), '2020-26': (11181, 39315.45), '2010-15': (8935, -5108.25)}
DATES = (*ind.DATES, 'exit_time')


def read(path):
    frame = pd.read_csv(path, float_precision='round_trip', low_memory=False)
    for column in DATES:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], format='ISO8601')
    return frame.sort_values(['submitted', 'ticket']).reset_index(drop=True)


def check_labels(saved, features, green):
    f, z, distance, stale = label(saved, features)
    scope = (saved.session < ind.END).to_numpy()
    colour = (f.close > f.open) if green else (f.close < f.open)
    assert (np.isclose(f.high, saved.requested_price, rtol=0, atol=1e-9) & np.isclose(f.low, saved.original_sl, rtol=0, atol=1e-9)
            & colour)[scope].all(), 'signal bar'
    close(z[scope], saved.z.to_numpy(float)[scope], 'z', atol=1e-9)
    far = saved.distance.eq('far_below').to_numpy()
    flip = (far != (distance == 'far_below')) & scope
    assert not flip.any() or np.all(np.abs(z[flip]+1) < 1e-9), 'far-below labels'
    assert np.array_equal(saved.distance.eq('unknown').to_numpy()[scope], (distance == 'unknown')[scope])
    assert np.array_equal(saved.roll_clean.astype(bool).to_numpy()[scope], np.where(stale, False, f.roll_clean)[scope])
    return int(scope.sum()), int(far[scope].sum())


def main():
    assert sha(PROTOCOL) == PROTOCOL_SHA
    report = dict(protocol_sha256=PROTOCOL_SHA)
    calendars = pd.read_csv(CROSS/'calendars.csv', parse_dates=['session'])
    summaries, contrast_table = pd.read_csv(OUT/'summaries.csv'), pd.read_csv(OUT/'contrast.csv')
    placebos, draws = pd.read_csv(OUT/'placebos.csv'), pd.read_csv(OUT/'placebo_draws.csv')
    annual, combined = pd.read_csv(OUT/'annual.csv'), pd.read_csv(OUT/'combined.csv')
    verdict = json.loads((OUT/'verdict.json').read_text(encoding='utf-8'))
    saved = read(OUT/'trades_GG.csv')
    parsed = ind.report_trades(ROOT/'Reports/ym_baselines_20261023/ymbase_20261023_gg_nq.htm', 'MNQcontDTBNT20102026_2', 2.0)
    assert len(parsed) == len(saved)
    for column in ('ticket', 'submitted', 'entry_time', 'exit_time'):
        assert (parsed[column].to_numpy() == saved[column].to_numpy()).all(), column
    for column in ('requested_price', 'original_sl', 'fill_price', 'exit_price', 'trade_profit',
                   'initial_risk_dollars', 'net_dollars', 'net_r'):
        close(parsed[column], saved[column], column, atol=1e-9)
    session = parsed.submitted.dt.normalize()
    for era, (count, net) in PUBLISHED.items():
        s, e = {**ind.EARLY, '2010-15': ('2010-01-01', '2016-01-01')}[era]
        part = parsed.loc[(session >= s) & (session < e)]
        assert len(part) == count and abs(part.net_dollars.sum()-net) < .005, era
    bars, minutes = ind.literal_bars(f'{STEM}_ohlcv-1m.csv')
    features = ind.literal_features(bars, pd.read_csv(f'{STEM}_rolls.csv', parse_dates=['date']))
    observed = pd.DatetimeIndex(bars.index.normalize().unique())
    assert observed.equals(pd.DatetimeIndex(calendars.loc[calendars.instrument.eq('NQ'), 'session']))
    labelled, far_count = check_labels(saved, features, green=True)
    rtl = read(CROSS/'trades_NQ.csv')
    rtl_labelled, rtl_far = check_labels(rtl, features, green=False)
    report.update(report_trades=len(parsed), minutes=minutes, m30_bars=len(bars), labelled=labelled, far_below=far_count,
                  rtl_labelled=rtl_labelled, rtl_far_below=rtl_far)
    masks = np.load(OUT/'placebo_masks_GG.npz')
    boots = np.load(OUT/'bootstrap_GG.npz')
    rows = []
    for sample, eras in SAMPLES:
        frame = saved.loc[saved['sample'].eq(sample)].reset_index(drop=True)
        assert np.array_equal(frame.ticket.to_numpy(), masks[f'{sample}_tickets'])
        far = frame.distance.eq('far_below').to_numpy()
        assert np.array_equal(far, masks[f'{sample}_far'])
        pnl, risk, r = (frame[c].to_numpy(float) for c in ('net_dollars', 'initial_risk_dollars', 'net_r'))
        era_of = frame.era.to_numpy()
        decile, tertile = np.empty(len(frame), int), np.empty(len(frame), int)
        for era in eras:
            inside = era_of == era
            decile[inside] = deciles(frame.loc[inside], 10)
            tertile[inside] = deciles(frame.loc[inside], 3)
        cells = np.array([list(eras).index(e) for e in era_of])*10+decile
        assert np.array_equal(cells, masks[f'{sample}_cells'])
        months = frame.submitted.dt.strftime('%Y-%m').to_numpy()
        month_cells = masks[f'{sample}_month_cells']
        key = pd.Series(months)+'|'+pd.Series(tertile).astype(str)
        assert key.groupby(month_cells).nunique().eq(1).all() and pd.Series(month_cells).groupby(key.to_numpy()).nunique().eq(1).all()
        start, stop = min(s for s, _ in eras.values()), max(e for _, e in eras.values())
        periods = {'pooled': (start, stop)} if len(eras) > 1 else {}
        periods.update(eras)
        sample_period = 'pooled' if len(eras) > 1 else next(iter(eras))
        head = summaries['sample'] == sample
        for p, (s, e) in periods.items():
            cal = observed[(observed >= s) & (observed < e)]
            m = np.ones(len(frame), bool) if p == 'pooled' else (era_of == p)
            day = cal.get_indexer(frame.session)
            assert (day[m] >= 0).all()
            for curve, keep in (('baseline', m), ('retained', m & ~far)):
                row = summaries.loc[head & (summaries.period == p) & (summaries.curve == curve)].iloc[0]
                daily = np.bincount(day[keep], weights=pnl[keep], minlength=len(cal))
                ordered = frame.loc[keep].sort_values(['exit_time', 'entry_time', 'ticket'])
                close([keep.sum(), pnl[keep].sum(), r[keep].mean(), maxdd(daily), maxdd(ordered.net_dollars.to_numpy())],
                      [row.trades, row.net_dollars, row.net_mean_r, row.daily_close_dd, row.closed_trade_dd], f'{sample} {p} {curve}', atol=1e-6)
        crow = contrast_table.loc[contrast_table['sample'] == sample].set_index('period')
        estimates = {}
        for p in periods:
            m = np.ones(len(frame), bool) if p == 'pooled' else (era_of == p)
            estimate, negative, used = weighted_contrast(r[m], far[m], cells[m])
            close([estimate, negative, used], [crow.loc[p, 'estimate'], crow.loc[p, 'negative_cells'], crow.loc[p, 'cells_used']], f'{p} contrast', atol=1e-12)
            estimates[p] = estimate
        weeks = pd.DatetimeIndex(boots[f'{sample}_weeks'].astype('datetime64[D]'))
        s, e = periods[sample_period]
        cal = observed[(observed >= s) & (observed < e)]
        assert weeks[0] == cal[0]-pd.Timedelta(days=cal[0].dayofweek) and weeks[-1] == cal[-1]-pd.Timedelta(days=cal[-1].dayofweek)
        assert len(weeks) == (weeks[-1]-weeks[0]).days//7+1
        wpos = weeks.get_indexer(frame.week_start)
        sums, counts = np.zeros((len(weeks), cells.max()+1, 2)), np.zeros((len(weeks), cells.max()+1, 2))
        for w, c_, fl, x in zip(wpos, cells, far.astype(int), r):
            sums[w, c_, fl] += x
            counts[w, c_, fl] += 1
        starts = boots[f'{sample}_starts'].astype(int)
        values = np.empty(len(starts))
        for d, row in enumerate(starts):
            idx = ((row[:, None]+np.arange(4)) % len(weeks)).ravel()[:len(weeks)]
            mult = np.bincount(idx, minlength=len(weeks)).astype(float)
            s_, c_ = np.tensordot(mult, sums, axes=1), np.tensordot(mult, counts, axes=1)
            ok = (c_[:, 0] > 0) & (c_[:, 1] > 0)
            values[d] = (c_[ok, 1]*(s_[ok, 1]/c_[ok, 1]-s_[ok, 0]/c_[ok, 0])).sum()/c_[ok, 1].sum()
        close(values, boots[f'{sample}_values'], f'{sample} bootstrap draws', atol=1e-10)
        low, high = np.quantile(values, [.025, .975], method='linear')
        close([low, high], [crow.loc[sample_period, 'ci95_low'], crow.loc[sample_period, 'ci95_high']], f'{sample} interval', atol=1e-10)
        unpack = {k: np.unpackbits(masks[f'{sample}_{k}'], axis=1, count=len(frame)).astype(bool) for k in ('B1', 'B2', 'B3')}
        for k, groups in (('B1', cells), ('B3', month_cells)):
            assert not (unpack[k] & far).any(), k
            for g in np.unique(groups):
                inside = groups == g
                assert (unpack[k][:, inside].sum(axis=1) == min(int(far[inside].sum()), int((~far[inside]).sum()))).all(), (sample, k, g)
        offsets = masks[f'{sample}_B2_offsets']
        for j, month in enumerate(pd.unique(months)):
            block = np.flatnonzero(months == month)
            assert np.array_equal(unpack['B2'][:, block], far[block][(np.arange(len(block))[None, :]-offsets[:, j][:, None]) % len(block)])
        b4 = np.zeros(len(frame), bool)
        for era in eras:
            idx = np.flatnonzero(era_of == era)
            ranked = frame.iloc[idx].sort_values(['initial_risk_dollars', 'submitted', 'ticket'], kind='mergesort').index.to_numpy()
            b4[ranked[len(ranked)-int(far[idx].sum()):]] = True
        assert np.array_equal(b4, masks[f'{sample}_B4'])
        prow = placebos.loc[placebos['sample'] == sample]
        for p, (s, e) in periods.items():
            cal = observed[(observed >= s) & (observed < e)]
            m = np.ones(len(frame), bool) if p == 'pooled' else (era_of == p)
            day = cal.get_indexer(frame.session)
            base = np.bincount(day[m], weights=pnl[m], minlength=len(cal))
            rule_dd = maxdd(base-np.bincount(day[m & far], weights=pnl[m & far], minlength=len(cal)))
            for k, mk in (('B1', unpack['B1']), ('B2', unpack['B2']), ('B3', unpack['B3']), ('B4', b4[None, :])):
                stats = np.empty((len(mk), 3))
                for d, mask in enumerate(mk):
                    skip = m & mask
                    stats[d] = (pnl[m].sum()-pnl[skip].sum(), maxdd(base-np.bincount(day[skip], weights=pnl[skip], minlength=len(cal))),
                                1-risk[skip].sum()/risk[m].sum())
                if k != 'B4':
                    saved_draws = draws.loc[(draws['sample'] == sample) & (draws.period == p) & (draws.placebo == k)].sort_values('draw')
                    close(stats, saved_draws[['net_dollars', 'daily_close_dd', 'risk_kept']].to_numpy(), f'{sample} {p} {k} draws', atol=1e-6)
                row = prow.loc[(prow.period == p) & (prow.placebo == k)].iloc[0]
                close([rule_dd, np.median(stats[:, 1]), np.mean(stats[:, 1] > row.rule_dd+1e-6), np.mean(stats[:, 0] < row.rule_net-1e-6)],
                      [row.rule_dd, row.dd_median, row.rule_beats_dd, row.rule_beats_net], f'{sample} {p} {k} summary', atol=1e-6)
        arows = annual.loc[annual['sample'] == sample].set_index('year')
        s, e = periods[sample_period]
        for year in sorted(frame.session.dt.year.unique()):
            cal = observed[(observed >= s) & (observed < e) & (observed.year == year)]
            m = (frame.session.dt.year == year).to_numpy()
            day = cal.get_indexer(frame.session)
            close([pnl[m].sum(), pnl[m & ~far].sum(), maxdd(np.bincount(day[m], weights=pnl[m], minlength=len(cal))),
                   maxdd(np.bincount(day[m & ~far], weights=pnl[m & ~far], minlength=len(cal)))],
                  arows.loc[year, ['baseline_net', 'rule_net', 'baseline_dd', 'rule_dd']].to_numpy(float), f'{year}', atol=1e-6)
        # Combined RTL + GG account from both trade files.
        crows = combined.loc[combined['sample'] == sample].set_index(['period', 'gate'])
        for p, (s, e) in periods.items():
            cal = observed[(observed >= s) & (observed < e)]
            g = frame if p == 'pooled' else frame.loc[frame.era == p]
            t = rtl.loc[(rtl.session >= s) & (rtl.session < e) & (rtl.session < ind.END)]
            for gate, skip_rtl, skip_gg in (('none', False, False), ('rtl_only', True, False), ('both', True, True)):
                parts = [t.loc[~(skip_rtl & t.distance.eq('far_below'))], g.loc[~(skip_gg & g.distance.eq('far_below'))]]
                pnl_all = np.concatenate([x.net_dollars.to_numpy() for x in parts])
                day = cal.get_indexer(pd.concat([x.session for x in parts]))
                assert (day >= 0).all()
                close([len(parts[0]), len(parts[1]), pnl_all.sum(), maxdd(np.bincount(day, weights=pnl_all, minlength=len(cal)))],
                      crows.loc[(p, gate), ['rtl_trades', 'gg_trades', 'net_dollars', 'daily_close_dd']].to_numpy(float), f'{p} {gate} combined', atol=1e-6)
        adequate = all((far & (era_of == era)).sum() >= 200 and frame.loc[far & (era_of == era), 'week_start'].nunique() >= 30 for era in eras)
        pooled = prow.set_index(['period', 'placebo'])
        test1 = bool(estimates[sample_period] < 0 and high < 0)
        test2 = bool(pooled.loc[(sample_period, 'B1'), 'rule_beats_dd'] >= .95 and pooled.loc[(sample_period, 'B2'), 'rule_beats_dd'] >= .95)
        test3 = None if len(eras) == 1 else bool(all(estimates[era] < 0 and pooled.loc[(era, 'B1'), 'rule_dd'] < pooled.loc[(era, 'B1'), 'dd_median']
                                                     and pooled.loc[(era, 'B2'), 'rule_dd'] < pooled.loc[(era, 'B2'), 'dd_median'] for era in eras))
        rows.append(dict(sample=sample, adequate=adequate, test1=test1, test2=test2, test3=test3,
                         confirms=bool(adequate and test1 and test2 and (test3 is None or test3))))
    saved_rows = {row['sample']: row for row in [verdict['primary'], *verdict['secondary']]}
    for row in rows:
        s = saved_rows[row['sample']]
        assert (s['adequate'], s['test1_contrast'], s['test2_placebos'], s['test3_each_era'], s['confirms']) == \
               (row['adequate'], row['test1'], row['test2'], row['test3'], row['confirms']), row
    overall = 'consistent with RTL' if rows[0]['confirms'] else 'not consistent'
    assert overall == verdict['overall']
    report.update(all_passed=True, verdict=overall, rows=rows,
                  outputs_sha256={p.name: sha(p) for p in sorted(OUT.glob('*')) if p.suffix in ('.csv', '.npz', '.json')
                                  and p.name != 'independent_verification.json'})
    (OUT/'independent_verification.json').write_text(json.dumps(report, indent=2, default=str)+'\n', encoding='utf-8')
    print(f'All checks passed. Verdict independently reproduced: {overall}.', flush=True)


if __name__ == '__main__':
    main()
