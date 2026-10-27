"""Independent verification of the cross-instrument RTL VWAP test.

Separate code from analyze_rtl_vwap_cross.py: HTMLParser report parsing, literal
minute-to-M30 features and labels, economics, drawdowns, contrast, every saved
bootstrap and placebo draw, invariants and the verdict.
"""
from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_vwap_cross_20261027'
PROTOCOL = ROOT / 'docs/baseline/rtl-vwap/CROSS_PROTOCOL.md'
PROTOCOL_SHA = '39a0884b7d746de14902e8a87833c4903da0965e331b47e7ead3b277cf912886'
NQ_PANEL = ROOT / 'Reports/rtl_vwap_20261025/trades.csv'
DATA = Path(r'F:\DATABENTO')
END = pd.Timestamp('2026-10-01')
COST = 1.05
EARLY = {'2016-19': ('2016-01-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01')}
SPEC = {
    'NQ': ('ym_baselines_20261023/ymbase_20261023_rtl_nq.htm', 'MNQcontDTBNT20102026_2', 2.0,
           'MNQ_16_YEARS/MT5_NQ_continuous_2010-2026', 'reference', EARLY, {'2010-15': ('2010-01-01', '2016-01-01')}),
    'ES': ('ym_baselines_20261023/ymbase_20261023_rtl_es.htm', 'MEScontDTBNT20102026_2', 5.0,
           'ES_16_YEARS/MT5_ES_continuous_2010-2026', 'primary', EARLY, {'2010-15': ('2010-01-01', '2016-01-01')}),
    'YM': ('ym_baselines_20261023/ymbase_20261023_rtl_ym.htm', 'MYMcontDTBNT20102026', 0.5,
           'YM_16_YEARS/MT5_YM_continuous_2010-2026', 'primary', EARLY, {'2010-15': ('2010-01-01', '2016-01-01')}),
    'RTY': ('rty_baselines_20261023/rtybase_20261023_rtl.htm', 'M2KcontDTBNT20172026', 5.0,
            'RTY_16_YEARS/MT5_RTY_continuous_2017-2026', 'primary',
            {'2018-19': ('2018-01-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01')},
            {'2017H2': ('2017-07-01', '2018-01-01')}),
}
PUBLISHED = {('ES', '2016-19'): (6286, -4652.80), ('ES', '2020-26'): (10803, -9085.65),
             ('YM', '2016-19'): (6209, 690.55), ('YM', '2020-26'): (10889, -2466.95),
             ('RTY', '2018-19'): (3207, -2179.35), ('RTY', '2020-26'): (10778, -3486.40)}
DATES = ('submitted', 'entry_time', 'exit_time', 'session', 'week_start', 'bar_time', 'available_at', 'feature_session')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()


def close(actual, expected, label, atol=1e-8):
    a, b = np.asarray(actual, float), np.asarray(expected, float)
    assert a.shape == b.shape, label
    assert np.array_equal(np.isnan(a), np.isnan(b)), label+' NaN pattern'
    finite = ~np.isnan(a)
    assert np.allclose(a[finite], b[finite], rtol=0, atol=atol), f'{label}: max {np.max(np.abs(a[finite]-b[finite]))}'


class Rows(HTMLParser):
    """Collect table rows as lists of cell texts."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(''.join(self.cell).strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def report_trades(path, symbol, point_value):
    parser = Rows()
    parser.feed(Path(path).read_text(encoding='utf-16'))
    value = lambda text: float(text.replace('\xa0', '').replace(' ', ''))
    section, orders, deals = None, {}, []
    for row in parser.rows:
        if row and row[0] in ('Orders', 'Deals'):
            section = row[0]
            continue
        if not row or len(row[0]) != 19 or row[0][4] != '.':
            continue
        if section == 'Orders' and len(row) == 11 and row[3] == 'buy stop':
            assert row[2] == symbol
            orders[int(row[1])] = (row[0], value(row[5]), value(row[6]), row[9])
        elif section == 'Deals' and len(row) == 13 and row[3] in ('buy', 'sell'):
            deals.append(row)
    records, opened = [], None
    for row in deals:
        assert row[2] == symbol and value(row[5]) == 1
        if row[4] == 'in':
            assert opened is None and row[3] == 'buy'
            opened = row
        else:
            assert opened is not None and row[3:5] == ['sell', 'out']
            submitted, requested, stop, state = orders[int(opened[7])]
            assert state == 'filled'
            records.append(dict(ticket=int(opened[7]), submitted=submitted, requested_price=requested, original_sl=stop,
                                entry_time=opened[0], fill_price=value(opened[6]), exit_time=row[0],
                                exit_price=value(row[6]), trade_profit=value(opened[10])+value(row[10])))
            opened = None
    frame = pd.DataFrame(records)
    for column in ('submitted', 'entry_time', 'exit_time'):
        frame[column] = pd.to_datetime(frame[column], format='%Y.%m.%d %H:%M:%S')
    frame['initial_risk_dollars'] = (frame.requested_price-frame.original_sl)*point_value
    frame['net_dollars'] = frame.trade_profit-COST
    frame['net_r'] = frame.net_dollars/frame.initial_risk_dollars
    return frame.sort_values(['submitted', 'ticket']).reset_index(drop=True)


def literal_bars(path):
    pieces, minutes, last = [], 0, None
    cols = ['<DATE>', '<TIME>', '<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>', '<VOL>', '<TICKVOL>']
    for raw in pd.read_csv(path, sep='\t', usecols=cols, chunksize=500000):
        t = pd.to_datetime(raw['<DATE>']+' '+raw['<TIME>'], format='%Y.%m.%d %H:%M:%S')
        assert t.is_monotonic_increasing and t.is_unique and (last is None or t.iloc[0] > last)
        last = t.iloc[-1]
        assert (t.dt.hour >= 1).all()
        o, h, l, c = (raw[k].to_numpy(float) for k in cols[2:6])
        v = raw['<VOL>'].to_numpy(float)
        assert (v > 0).all() and np.array_equal(v, raw['<TICKVOL>'].to_numpy(float))
        assert np.all(h >= np.maximum.reduce([o, l, c])) and np.all(l <= np.minimum.reduce([o, h, c]))
        part = pd.DataFrame(dict(bar_time=t.dt.floor('30min'), open=o, high=h, low=l, close=c, volume=v, pv=((h+l+c)/3)*v))
        pieces.append(part.groupby('bar_time').agg(open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
                                                    close=('close', 'last'), volume=('volume', 'sum'), pv=('pv', 'sum')))
        minutes += len(raw)
    bars = pd.concat(pieces).groupby(level=0).agg(open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
                                                  close=('close', 'last'), volume=('volume', 'sum'), pv=('pv', 'sum'))
    return bars.loc[bars.index+pd.Timedelta(minutes=30) < END], minutes


def literal_features(bars, rolls):
    n = len(bars)
    h, l, c = (bars[k].to_numpy() for k in ('high', 'low', 'close'))
    prev = np.r_[np.nan, c[:-1]]
    tr = np.maximum.reduce([h-l, np.abs(h-prev), np.abs(l-prev)])
    a20 = np.full(n, np.nan)
    a20[19:] = np.lib.stride_tricks.sliding_window_view(tr, 20).mean(axis=1)
    day = bars.index.normalize()
    switch_days = set(rolls.date.loc[rolls.symbol.ne(rolls.symbol.shift()) & rolls.symbol.shift().notna()])
    switch = (~pd.Series(day).duplicated()).to_numpy() & np.isin(day, list(switch_days))
    clean = np.zeros(n, bool)
    clean[20:] = ~np.lib.stride_tricks.sliding_window_view(switch, 21).any(axis=1)
    clean &= np.isfinite(a20) & (a20 > 0)
    vwap = np.empty(n)
    starts = np.r_[0, np.flatnonzero(day[1:] != day[:-1])+1]
    for start, stop in zip(starts, np.r_[starts[1:], n]):
        vwap[start:stop] = np.cumsum(bars.pv.to_numpy()[start:stop])/np.cumsum(bars.volume.to_numpy()[start:stop])
    z = np.where(np.isfinite(a20) & (a20 > 0), (c-vwap)/np.where(a20 > 0, a20, 1), np.nan)
    return pd.DataFrame(dict(bar_time=bars.index, available_at=bars.index+pd.Timedelta(minutes=30), high=h, low=l,
                             close=c, open=bars.open.to_numpy(), a20=a20, vwap=vwap, z=z, roll_clean=clean))


def label(trades, features):
    i = np.searchsorted(features.available_at.to_numpy(), trades.submitted.to_numpy(), side='right')-1
    assert (i >= 0).all()
    f = features.iloc[i].reset_index(drop=True)
    stale = f.bar_time.dt.normalize().to_numpy() != trades.submitted.dt.normalize().to_numpy()
    z = np.where(stale, np.nan, f.z.to_numpy())
    distance = np.where(np.isnan(z), 'unknown', np.where(z < -1, 'far_below', 'other'))
    return f, z, distance, stale


def maxdd(daily):
    equity = np.r_[0., np.cumsum(daily)]
    return float(np.max(np.maximum.accumulate(equity)-equity))


def deciles(frame, k):
    ordered = frame.sort_values(['initial_risk_dollars', 'submitted', 'ticket'], kind='mergesort')
    groups = pd.Series(np.arange(len(frame))*k//len(frame), index=ordered.index)
    return groups.reindex(frame.index).to_numpy()


def weighted_contrast(r, far, cells):
    total, weight, negative, used = 0., 0, 0, 0
    for cell in np.unique(cells):
        f, o = (cells == cell) & far, (cells == cell) & ~far
        if f.any() and o.any():
            d = r[f].mean()-r[o].mean()
            total, weight, negative, used = total+f.sum()*d, weight+f.sum(), negative+(d < 0), used+1
    return total/weight, int(negative), used


def main():
    assert sha(PROTOCOL) == PROTOCOL_SHA
    report = dict(protocol_sha256=PROTOCOL_SHA, instruments={})
    calendars = pd.read_csv(OUT/'calendars.csv', parse_dates=['session'])
    summaries, contrast_table = pd.read_csv(OUT/'summaries.csv'), pd.read_csv(OUT/'contrast.csv')
    placebos, draws = pd.read_csv(OUT/'placebos.csv'), pd.read_csv(OUT/'placebo_draws.csv')
    annual, comove = pd.read_csv(OUT/'annual.csv'), pd.read_csv(OUT/'comovement.csv')
    verdict = json.loads((OUT/'verdict.json').read_text(encoding='utf-8'))
    nq_features = None
    recomputed_verdict = []
    for name, (html_path, symbol, pv, stem, role, primary, secondary) in SPEC.items():
        checks = {}
        saved = pd.read_csv(OUT/f'trades_{name}.csv', float_precision='round_trip', low_memory=False)
        for column in DATES:
            saved[column] = pd.to_datetime(saved[column], format='ISO8601')
        saved = saved.sort_values(['submitted', 'ticket']).reset_index(drop=True)
        parsed = report_trades(ROOT/'Reports'/html_path, symbol, pv)
        assert len(parsed) == len(saved)
        for column in ('ticket', 'submitted', 'entry_time', 'exit_time'):
            assert (parsed[column].to_numpy() == saved[column].to_numpy()).all(), column
        for column in ('requested_price', 'original_sl', 'fill_price', 'exit_price', 'trade_profit',
                       'initial_risk_dollars', 'net_dollars', 'net_r'):
            close(parsed[column], saved[column], f'{name} {column}', atol=1e-9)
        checks['report_trades'] = len(parsed)
        session = parsed.submitted.dt.normalize()
        for (instrument, era), (count, net) in PUBLISHED.items():
            if instrument == name:
                s, e = primary[era]
                part = parsed.loc[(session >= s) & (session < e)]
                assert len(part) == count and abs(part.net_dollars.sum()-net) < .005, (name, era)
        bars, minutes = literal_bars(DATA/f'{stem}_ohlcv-1m.csv')
        features = literal_features(bars, pd.read_csv(DATA/f'{stem}_rolls.csv', parse_dates=['date']))
        if name == 'NQ':
            nq_features = features
        observed = pd.DatetimeIndex(bars.index.normalize().unique())
        assert observed.equals(pd.DatetimeIndex(calendars.loc[calendars.instrument.eq(name), 'session']))
        f, z, distance, stale = label(saved, features)
        scope = (saved.session < END).to_numpy()
        assert (np.isclose(f.high, saved.requested_price, rtol=0, atol=1e-9) & np.isclose(f.low, saved.original_sl, rtol=0, atol=1e-9)
                & (f.close < f.open))[scope].all(), 'signal bar'
        close(z[scope], saved.z.to_numpy(float)[scope], f'{name} z', atol=1e-9)
        far = saved.distance.eq('far_below').to_numpy()
        flip = (far != (distance == 'far_below')) & scope
        assert not flip.any() or np.all(np.abs(z[flip]+1) < 1e-9), f'{name} far-below labels'
        assert np.array_equal(saved.distance.eq('unknown').to_numpy()[scope], (distance == 'unknown')[scope])
        assert np.array_equal(saved.roll_clean.astype(bool).to_numpy()[scope], np.where(stale, False, f.roll_clean)[scope])
        checks.update(minutes=minutes, m30_bars=len(bars), labelled=int(scope.sum()), far_below=int(far[scope].sum()))
        if name == 'NQ':
            panel = pd.read_csv(NQ_PANEL, float_precision='round_trip')
            panel = panel.loc[panel.variant.eq('full_hlc3')]
            panel['submitted'] = pd.to_datetime(panel.submitted, format='ISO8601')
            mine = pd.DataFrame(dict(submitted=saved.submitted, ticket=saved.ticket, z=z))
            joined = panel.merge(mine, on=['submitted', 'ticket'], suffixes=('', '_mine'), validate='one_to_one')
            assert len(joined) == 16668
            close(joined.z_mine, joined.z, 'NQ panel z', atol=1e-9)
            checks['nq_panel_z'] = len(joined)
        masks = np.load(OUT/f'placebo_masks_{name}.npz')
        boots = np.load(OUT/f'bootstrap_{name}.npz')
        for sample, eras in (('primary', primary), ('secondary', secondary)):
            frame = saved.loc[saved['sample'].eq(sample)].sort_values(['submitted', 'ticket']).reset_index(drop=True)
            assert np.array_equal(frame.ticket.to_numpy(), masks[f'{sample}_tickets'])
            far = frame.distance.eq('far_below').to_numpy()
            assert np.array_equal(far, masks[f'{sample}_far'])
            pnl, risk, r = (frame[c].to_numpy(float) for c in ('net_dollars', 'initial_risk_dollars', 'net_r'))
            era_of = frame.era.to_numpy()
            decile, tertile = np.empty(len(frame), int), np.empty(len(frame), int)
            for i, era in enumerate(eras):
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
            head = (summaries.instrument == name) & (summaries['sample'] == sample)
            # Summaries: baseline, rule, same-holding scaling.
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
                          [row.trades, row.net_dollars, row.net_mean_r, row.daily_close_dd, row.closed_trade_dd], f'{name} {sample} {p} {curve}', atol=1e-6)
                holding = frame.holding_minutes.to_numpy()
                fraction = holding[m & ~far].sum()/holding[m].sum()
                retained = summaries.loc[head & (summaries.period == p) & (summaries.curve == 'retained')].iloc[0]
                close([fraction, risk[m & ~far].sum()/risk[m].sum()], [retained.retained_holding_fraction, retained.retained_planned_risk_fraction], f'{name} {p} kept', atol=1e-12)
                scaled = summaries.loc[head & (summaries.period == p) & (summaries.curve == 'static_holding_scaled')].iloc[0]
                base_daily = np.bincount(day[m], weights=pnl[m], minlength=len(cal))
                close([pnl[m].sum()*fraction, maxdd(base_daily)*fraction], [scaled.net_dollars, scaled.daily_close_dd], f'{name} {p} scaled', atol=1e-6)
            # Contrast A point estimates and every saved bootstrap draw.
            crow = contrast_table.loc[(contrast_table.instrument == name) & (contrast_table['sample'] == sample)].set_index('period')
            estimates = {}
            for p in periods:
                m = np.ones(len(frame), bool) if p == 'pooled' else (era_of == p)
                estimate, negative, used = weighted_contrast(r[m], far[m], cells[m])
                close([estimate, negative, used], [crow.loc[p, 'estimate'], crow.loc[p, 'negative_cells'], crow.loc[p, 'cells_used']], f'{name} {p} contrast', atol=1e-12)
                estimates[p] = estimate
            weeks = pd.DatetimeIndex(boots[f'{sample}_weeks'].astype('datetime64[D]'))
            s, e = periods[sample_period]
            cal = observed[(observed >= s) & (observed < e)]
            assert weeks[0] == cal[0]-pd.Timedelta(days=cal[0].dayofweek) and weeks[-1] == cal[-1]-pd.Timedelta(days=cal[-1].dayofweek)
            assert len(weeks) == (weeks[-1]-weeks[0]).days//7+1
            wpos = weeks.get_indexer(frame.week_start)
            ncell = cells.max()+1
            sums = np.zeros((len(weeks), ncell, 2))
            counts = np.zeros((len(weeks), ncell, 2))
            for w, c_, fl, x in zip(wpos, cells, far.astype(int), r):
                sums[w, c_, fl] += x
                counts[w, c_, fl] += 1
            starts = boots[f'{sample}_starts'].astype(int)
            nweeks = len(weeks)
            values = np.empty(len(starts))
            for d, row in enumerate(starts):
                idx = ((row[:, None]+np.arange(4)) % nweeks).ravel()[:nweeks]
                mult = np.bincount(idx, minlength=nweeks).astype(float)
                s_, c_ = np.tensordot(mult, sums, axes=1), np.tensordot(mult, counts, axes=1)
                ok = (c_[:, 0] > 0) & (c_[:, 1] > 0)
                diff = s_[ok, 1]/c_[ok, 1]-s_[ok, 0]/c_[ok, 0]
                values[d] = (c_[ok, 1]*diff).sum()/c_[ok, 1].sum()
            close(values, boots[f'{sample}_values'], f'{name} {sample} bootstrap draws', atol=1e-10)
            low, high = np.quantile(values, [.025, .975], method='linear')
            close([low, high], [crow.loc[sample_period, 'ci95_low'], crow.loc[sample_period, 'ci95_high']], f'{name} {sample} interval', atol=1e-10)
            # Placebo invariants and every draw's statistics.
            unpack = {k: np.unpackbits(masks[f'{sample}_{k}'], axis=1, count=len(frame)).astype(bool) for k in ('B1', 'B2', 'B3')}
            for key, groups in (('B1', cells), ('B3', month_cells)):
                assert not (unpack[key] & far).any(), key
                for g in np.unique(groups):
                    inside = groups == g
                    expected = min(int(far[inside].sum()), int((~far[inside]).sum()))
                    assert (unpack[key][:, inside].sum(axis=1) == expected).all(), (name, sample, key, g)
            offsets = masks[f'{sample}_B2_offsets']
            for j, month in enumerate(pd.unique(months)):
                block = np.flatnonzero(months == month)
                rolled = far[block][(np.arange(len(block))[None, :]-offsets[:, j][:, None]) % len(block)]
                assert np.array_equal(unpack['B2'][:, block], rolled), (name, sample, month)
            b4 = np.zeros(len(frame), bool)
            for era in eras:
                idx = np.flatnonzero(era_of == era)
                ranked = frame.iloc[idx].sort_values(['initial_risk_dollars', 'submitted', 'ticket'], kind='mergesort').index.to_numpy()
                b4[ranked[len(ranked)-int(far[idx].sum()):]] = True
            assert np.array_equal(b4, masks[f'{sample}_B4'])
            prow = placebos.loc[(placebos.instrument == name) & (placebos['sample'] == sample)]
            for p, (s, e) in periods.items():
                cal = observed[(observed >= s) & (observed < e)]
                m = np.ones(len(frame), bool) if p == 'pooled' else (era_of == p)
                day = cal.get_indexer(frame.session)
                base = np.bincount(day[m], weights=pnl[m], minlength=len(cal))
                rule_dd = maxdd(base-np.bincount(day[m & far], weights=pnl[m & far], minlength=len(cal)))
                for key, mk in (('B1', unpack['B1']), ('B2', unpack['B2']), ('B3', unpack['B3']), ('B4', b4[None, :])):
                    stats = np.empty((len(mk), 3))
                    for d, mask in enumerate(mk):
                        skip = m & mask
                        stats[d] = (pnl[m].sum()-pnl[skip].sum(),
                                    maxdd(base-np.bincount(day[skip], weights=pnl[skip], minlength=len(cal))),
                                    1-risk[skip].sum()/risk[m].sum())
                    if key != 'B4':
                        saved_draws = draws.loc[(draws.instrument == name) & (draws['sample'] == sample) & (draws.period == p) & (draws.placebo == key)].sort_values('draw')
                        close(stats, saved_draws[['net_dollars', 'daily_close_dd', 'risk_kept']].to_numpy(), f'{name} {sample} {p} {key} draws', atol=1e-6)
                    row = prow.loc[(prow.period == p) & (prow.placebo == key)].iloc[0]
                    close([rule_dd, np.median(stats[:, 1]), np.mean(stats[:, 1] > row.rule_dd+1e-6), np.mean(stats[:, 0] < row.rule_net-1e-6)],
                          [row.rule_dd, row.dd_median, row.rule_beats_dd, row.rule_beats_net], f'{name} {sample} {p} {key} summary', atol=1e-6)
            # Annual rows.
            arows = annual.loc[(annual.instrument == name) & (annual['sample'] == sample)].set_index('year')
            s, e = periods[sample_period]
            for year in sorted(frame.session.dt.year.unique()):
                cal = observed[(observed >= s) & (observed < e) & (observed.year == year)]
                m = (frame.session.dt.year == year).to_numpy()
                day = cal.get_indexer(frame.session)
                close([pnl[m].sum(), pnl[m & ~far].sum(), maxdd(np.bincount(day[m], weights=pnl[m], minlength=len(cal))),
                       maxdd(np.bincount(day[m & ~far], weights=pnl[m & ~far], minlength=len(cal)))],
                      arows.loc[year, ['baseline_net', 'rule_net', 'baseline_dd', 'rule_dd']].to_numpy(float), f'{name} {year}', atol=1e-6)
            # Co-movement with NQ (independent NQ features).
            if name != 'NQ':
                f_nq, z_nq, _, _ = label(frame, nq_features)
                nq_far = z_nq < -1
                for p in periods:
                    m = np.ones(len(frame), bool) if p == 'pooled' else (era_of == p)
                    row = comove.loc[(comove.instrument == name) & (comove['sample'] == sample) & (comove.period == p)].iloc[0]
                    estimate, negative, _ = weighted_contrast(r[m & ~nq_far], far[m & ~nq_far], cells[m & ~nq_far])
                    close([(m & far & nq_far).sum(), (m & nq_far).sum(), estimate, negative],
                          [row.far_with_nq_far, row.all_with_nq_far, row.contrast_without_nq_far, row.negative_cells_without_nq_far],
                          f'{name} {p} comovement', atol=1e-12)
            # Verdict from verified numbers.
            adequate = all((far & (era_of == era)).sum() >= 200 and frame.loc[far & (era_of == era), 'week_start'].nunique() >= 30 for era in eras)
            pooled = prow.set_index(['period', 'placebo'])
            test1 = bool(estimates[sample_period] < 0 and high < 0)
            test2 = bool(pooled.loc[(sample_period, 'B1'), 'rule_beats_dd'] >= .95 and pooled.loc[(sample_period, 'B2'), 'rule_beats_dd'] >= .95)
            test3 = None if len(eras) == 1 else bool(all(estimates[era] < 0 and pooled.loc[(era, 'B1'), 'rule_dd'] < pooled.loc[(era, 'B1'), 'dd_median']
                                                         and pooled.loc[(era, 'B2'), 'rule_dd'] < pooled.loc[(era, 'B2'), 'dd_median'] for era in eras))
            confirms = bool(adequate and test1 and test2 and (test3 is None or test3))
            recomputed_verdict.append(dict(instrument=name, sample=sample, counts=(role == 'primary' and sample == 'primary'),
                                           adequate=adequate, test1=test1, test2=test2, test3=test3, confirms=confirms))
        report['instruments'][name] = checks
        print(f'{name}: independently verified.', flush=True)
    saved_rows = {(row['instrument'], row['sample']): row for row in verdict['primary']+verdict['reference_and_secondary']}
    for row in recomputed_verdict:
        s = saved_rows[(row['instrument'], row['sample'])]
        assert (s['adequate'], s['test1_contrast'], s['test2_placebos'], s['test3_each_era'], s['confirms']) == \
               (row['adequate'], row['test1'], row['test2'], row['test3'], row['confirms']), row
    confirmed = sum(row['confirms'] for row in recomputed_verdict if row['counts'])
    overall = 'transfers' if confirmed >= 2 else 'partial' if confirmed == 1 else 'does not transfer'
    assert overall == verdict['overall']
    report.update(all_passed=True, verdict=overall, confirming=confirmed, rows=recomputed_verdict,
                  outputs_sha256={p.name: sha(p) for p in sorted(OUT.glob('*')) if p.suffix in ('.csv', '.npz', '.json')
                                  and p.name != 'independent_verification.json'})
    (OUT/'independent_verification.json').write_text(json.dumps(report, indent=2, default=str)+'\n', encoding='utf-8')
    print(f'All checks passed. Verdict independently reproduced: {overall}.', flush=True)


if __name__ == '__main__':
    main()
