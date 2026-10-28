"""Independent verification of the RTL VWAP stock test.

Separate code from analyze_rtl_vwap_stocks.py and rtl_stock_engine.py: raw DBN re-reading, session
filter and split adjustment, a separately written RTL state machine (first checked against MT5's
25,833 NQ trades), literal VWAP/A20/z labels, economics, contrasts, every bootstrap and placebo
draw, placebo invariants and the verdict.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

import databento as db
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_vwap_stocks_20261028'
PROTOCOL = ROOT / 'docs/baseline/rtl-vwap/STOCK_PROTOCOL.md'
PROTOCOL_SHA = 'a12a4172b7d326e4e86d2537ddd0101c93849ccbe22daee11120211c5bfb4e38'
DATA = Path(r'F:\DATABENTO\STOCKS')
NQ_CSV = Path(r'F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv')
NQ_CALENDAR = ROOT / 'mt5/experts/early_closes.mqh'
NQ_MT5 = ROOT / 'Reports/rtl_vwap_replay_20261026/trades_off.csv'
STOCKS = ('AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'AVGO', 'TSLA', 'COST', 'NFLX')
SPLITS = {('AAPL', '2020-08-31'): 4, ('TSLA', '2020-08-31'): 5, ('NVDA', '2021-07-20'): 4,
          ('AMZN', '2022-06-06'): 20, ('GOOGL', '2022-07-18'): 20, ('TSLA', '2022-08-25'): 3,
          ('NVDA', '2024-06-10'): 10, ('AVGO', '2024-07-15'): 10, ('NFLX', '2025-11-17'): 10}
EARLY_DAYS = pd.to_datetime(['2018-07-03', '2018-11-23', '2018-12-24', '2019-07-03', '2019-11-29', '2019-12-24',
                             '2020-11-27', '2020-12-24', '2021-11-26', '2022-11-25', '2023-07-03', '2023-11-24',
                             '2024-07-03', '2024-11-29', '2024-12-24', '2025-07-03', '2025-11-28', '2025-12-24'])
START, END = pd.Timestamp('2018-05-01'), pd.Timestamp('2026-10-01')
ERAS = {'2018-19': ('2018-05-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01')}
NOTIONAL, COST, TIE = 10_000.0, 2.0, 1e-6
SECONDS = (0, 20, 40, 59)


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()


def close(actual, expected, label, atol=1e-8):
    a, b = np.asarray(actual, float), np.asarray(expected, float)
    assert a.shape == b.shape, label
    assert np.array_equal(np.isnan(a), np.isnan(b)), label+' NaN pattern'
    ok = ~np.isnan(a)
    assert np.allclose(a[ok], b[ok], rtol=0, atol=atol), f'{label}: max {np.max(np.abs(a[ok]-b[ok]))}'


def maxdd(x):
    equity = np.r_[0., np.cumsum(x)]
    return float(np.max(np.maximum.accumulate(equity)-equity))


# ---------------------------------------------------------------- RTL state machine

def order_flags(o, c):
    """True where MT5 visits the low before the high: rising minutes, and flat minutes after a fall."""
    n = len(o)
    move = np.sign(c-o)
    where = np.where(move != 0, np.arange(n), -1)
    before = np.r_[-1, np.maximum.accumulate(where)[:-1]]
    previous = np.where(before >= 0, move[np.maximum(before, 0)], 0)
    return (move > 0) | ((move == 0) & (previous < 0))


def replay(t, o, h, l, c, cutoff_of, gap, first_order_minute=0, rr=1.0):
    t = pd.DatetimeIndex(t)
    secs = t.values.astype('datetime64[s]').astype(np.int64)
    mod = (t.hour*60+t.minute).to_numpy()
    key = (t.year*10000+t.month*100+t.day).to_numpy()
    bucket = secs // 1800
    lows = order_flags(o, c)
    stamp = lambda i, k: np.datetime64(int(secs[i]+SECONDS[k]), 's')
    out, pending, position, done = [], None, None, set()
    previous = current = None
    bucket_now, day_before = None, None

    def finish(i, k, price, why):
        out.append(dict(submitted=position['submitted'], requested=position['level'], sl=position['stop'],
                        entry_time=position['entry'], fill=position['fill'], exit_time=stamp(i, k), exit_price=price, reason=why))

    for i in range(len(o)):
        fresh = bucket[i] != bucket_now
        if fresh:
            previous, current, bucket_now = current, [o[i], h[i], l[i], c[i]], bucket[i]
        else:
            current = [current[0], max(current[1], h[i]), min(current[2], l[i]), c[i]]
            if not ((pending is not None and h[i] >= pending['level']) or (position is not None and l[i] <= position['stop'])):
                continue
        path = (o[i], l[i], h[i], c[i]) if lows[i] else (o[i], h[i], l[i], c[i])
        for k, price in enumerate(path):
            if position is not None and price <= position['stop']:
                finish(i, k, price if gap and k == 0 else position['stop'], 'sl')
                position = None
            if pending is not None and price >= pending['level']:
                position = dict(pending, entry=stamp(i, k), fill=price if gap and k == 0 else pending['level'])
                pending = None
            if k or not fresh:
                continue
            day, slot_minute = key[i], (mod[i]//30)*30
            if day_before is not None and day != day_before and day_before not in done:
                done.add(day_before)
                if position is not None:
                    finish(i, k, price, 'fallback'); position = None
                pending = None
            day_before = day
            if slot_minute >= cutoff_of(day):
                if day not in done:
                    done.add(day)
                    if position is not None:
                        finish(i, k, price, 'flatten'); position = None
                    pending = None
                continue
            if position is not None:
                if previous[3] >= position['fill']+rr*(position['fill']-position['stop']):
                    finish(i, k, price, 'target'); position = None
                continue
            if slot_minute < first_order_minute:
                pending = None
                continue
            if previous is not None and previous[3] < previous[0]:
                pending = None
                if previous[1] > previous[2] and previous[1] > price:
                    pending = dict(level=previous[1], stop=previous[2], submitted=stamp(i, 0))
    if position is not None:
        n = len(o)-1
        finish(n, 3, c[n], 'end_of_data')
    return pd.DataFrame(out)


def check_on_nq():
    d = pd.read_csv(NQ_CSV, sep='\t', usecols=[0, 1, 2, 3, 4, 5], header=0, names=['d', 'tm', 'o', 'h', 'l', 'c'], dtype=str)
    t = pd.to_datetime(d.d+' '+d.tm, format='%Y.%m.%d %H:%M:%S')
    text = NQ_CALENDAR.read_text(encoding='utf-8')
    days = [int(x) for x in re.search(r'EC_DATE\[EC_COUNT\] = \{([^}]+)', text).group(1).split(',')]
    flat = [int(x) for x in re.search(r'EC_FLAT_MIN\[EC_COUNT\] = \{([^}]+)', text).group(1).split(',')]
    table = dict(zip(days, flat))
    sim = replay(t, *(d[k].astype(float).to_numpy() for k in 'ohlc'), lambda day: table.get(day, 1410), gap=False, first_order_minute=60)
    mt = pd.read_csv(NQ_MT5, usecols=['submitted', 'requested_price', 'original_sl', 'entry_time', 'exit_time', 'fill_price',
                                      'exit_price', 'trade_profit'], parse_dates=['submitted', 'entry_time', 'exit_time'])
    sim['minute'] = pd.to_datetime(sim.entry_time).dt.floor('min')
    mt['minute'] = mt.entry_time.dt.floor('min')
    j = mt.merge(sim, on='minute', how='inner', validate='one_to_one')
    assert len(j) == len(mt) == 25833
    assert (sim.minute[~sim.minute.isin(mt.minute)] < mt.minute.min()).all()
    assert (pd.to_datetime(j.submitted_y).dt.floor('min') == j.submitted_x.dt.floor('min')).all()
    assert (pd.to_datetime(j.exit_time_y).dt.floor('min') == j.exit_time_x.dt.floor('min')).all()
    for a, b in (('requested', 'requested_price'), ('sl', 'original_sl'), ('fill', 'fill_price'), ('exit_price_y', 'exit_price_x')):
        assert (j[a] == j[b]).all(), a
    close((j.exit_price_y-j.fill)*2.0, j.trade_profit, 'NQ profit', atol=1e-6)
    return dict(mt5_trades=len(mt), matched=len(j), extra_before_mt5=int((~sim.minute.isin(mt.minute)).sum()))


# ---------------------------------------------------------------- stock data

def stock_minutes():
    parts = {}
    for path in sorted(DATA.glob('*.zip')):
        z = zipfile.ZipFile(path)
        name = [x for x in z.namelist() if x.endswith('.dbn')][0]
        df = db.DBNStore.from_bytes(io.BytesIO(z.read(name))).to_df(pretty_ts=True, price_type='float')
        local = df.index.tz_convert('America/New_York').tz_localize(None)
        symbols = df.symbol.to_numpy()
        for s in np.unique(symbols):
            m = symbols == s
            parts.setdefault('META' if s == 'FB' else s, []).append(pd.DataFrame(dict(
                t=local[m], o=df.open.to_numpy(float)[m], h=df.high.to_numpy(float)[m], l=df.low.to_numpy(float)[m],
                c=df.close.to_numpy(float)[m], v=df.volume.to_numpy(float)[m], raw=s)))
    result = {}
    for s, frames in parts.items():
        f = pd.concat(frames).sort_values('t', kind='stable')
        f = f[np.isfinite(f[['o', 'h', 'l', 'c']].to_numpy()).all(axis=1)]   # bars without a price
        if s == 'META':
            f = f[((f.raw == 'META') & (f.t >= '2022-06-09')) | ((f.raw == 'FB') & (f.t < '2022-06-09'))]
        result[s] = f.reset_index(drop=True)
    return result


def in_session(f, first):
    clock = (f.t.dt.hour*60+f.t.dt.minute).to_numpy()
    last = np.where(f.t.dt.normalize().isin(EARLY_DAYS), 780, 960)
    return f[(clock >= first) & (clock < last) & (f.t >= START).to_numpy()].reset_index(drop=True)


def unsplit(stock, f):
    mult = np.ones(len(f))
    for (s, d), n in SPLITS.items():
        if s == stock:
            mult *= np.where(f.t < pd.Timestamp(d), n, 1)
    f = f.copy()
    for k in 'ohlc':
        f[k] = f[k].to_numpy()/mult
    f['v'] = f.v.to_numpy()*mult
    return f


def literal_labels(f, trades):
    """M30 bars, cumulative session VWAP, A20 and z; the latest completed bar at submission."""
    g = f.assign(bar=f.t.dt.floor('30min'), pv=(f.h+f.l+f.c)/3*f.v)
    bars = g.groupby('bar').agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), v=('v', 'sum'), pv=('pv', 'sum'))
    bars = bars.loc[bars.index+pd.Timedelta(minutes=30) < END]
    hh, ll, cc = bars.h.to_numpy(), bars.l.to_numpy(), bars.c.to_numpy()
    prev = np.r_[np.nan, cc[:-1]]
    tr = np.maximum.reduce([hh-ll, np.abs(hh-prev), np.abs(ll-prev)])
    a20 = np.full(len(bars), np.nan)
    a20[19:] = np.lib.stride_tricks.sliding_window_view(tr, 20).mean(axis=1)
    day = bars.index.normalize()
    vwap = (bars.pv.groupby(day).cumsum()/bars.v.groupby(day).cumsum()).to_numpy()
    z = np.where(a20 > 0, (cc-vwap)/np.where(a20 > 0, a20, 1), np.nan)
    avail = (bars.index+pd.Timedelta(minutes=30)).to_numpy()
    i = np.searchsorted(avail, pd.to_datetime(trades.submitted).to_numpy().astype(avail.dtype), side='right')-1
    assert (i >= 0).all()
    stale = day.to_numpy()[i] != pd.to_datetime(trades.submitted).dt.normalize().to_numpy().astype(day.to_numpy().dtype)
    zz = np.where(stale, np.nan, z[i])
    signal_ok = (hh[i] == trades.requested_price.to_numpy()) & (ll[i] == trades.original_sl.to_numpy()) & (cc[i] < bars.o.to_numpy()[i])
    return zz, signal_ok


def rank_in(frame, k):
    order = frame.sort_values(['initial_risk_dollars', 'submitted', 'ticket'], kind='mergesort').index
    return pd.Series(np.arange(len(frame))*k//len(frame), index=order).reindex(frame.index).to_numpy()


def weighted(r, far, cells):
    total, weight, negative = 0., 0, 0
    for cell in np.unique(cells):
        f, o = (cells == cell) & far, (cells == cell) & ~far
        if f.any() and o.any():
            d = r[f].mean()-r[o].mean()
            total, weight, negative = total+f.sum()*d, weight+f.sum(), negative+(d < 0)
    return total/weight, int(negative)


def main():
    assert sha_file(PROTOCOL) == PROTOCOL_SHA
    report = dict(nq=check_on_nq(), stocks={})
    print('Independent state machine matches all MT5 NQ trades.', flush=True)
    raw = stock_minutes()
    cut = lambda day: 750 if day in {int(f'{d:%Y%m%d}') for d in EARLY_DAYS} else 930
    early_keys = {int(f'{d:%Y%m%d}') for d in EARLY_DAYS}
    cut = lambda day: 750 if day in early_keys else 930
    saved = {}
    for stock in STOCKS:
        entry = {}
        for suffix, first in (('', 240), ('_rth', 570)):
            f = unsplit(stock, in_session(raw[stock], first))
            sim = replay(f.t, f.o.to_numpy(), f.h.to_numpy(), f.l.to_numpy(), f.c.to_numpy(), cut, gap=True)
            mine = pd.read_csv(OUT/f'trades{suffix}_{stock}.csv', float_precision='round_trip', low_memory=False)
            for column in ('submitted', 'entry_time', 'exit_time', 'session', 'week_start'):
                mine[column] = pd.to_datetime(mine[column], format='ISO8601')
            assert len(sim) == len(mine), (stock, suffix, len(sim), len(mine))
            for a, b in (('submitted', 'submitted'), ('entry_time', 'entry_time'), ('exit_time', 'exit_time')):
                assert (pd.to_datetime(sim[a]).to_numpy() == mine[b].to_numpy().astype('datetime64[s]')).all(), (stock, a)
            for a, b in (('requested', 'requested_price'), ('sl', 'original_sl'), ('fill', 'fill_price'), ('exit_price', 'exit_price')):
                assert (sim[a].to_numpy() == mine[b].to_numpy()).all(), (stock, a)
            assert (sim.reason.to_numpy() == mine.exit_comment.to_numpy()).all()
            shares = NOTIONAL/sim.requested
            profit = shares*(sim.exit_price-sim.fill)
            risk = shares*(sim.requested-sim.sl)
            close(profit, mine.trade_profit, f'{stock}{suffix} profit', 1e-9)
            close(risk, mine.initial_risk_dollars, f'{stock}{suffix} risk', 1e-9)
            close((profit-COST)/risk, mine.net_r, f'{stock}{suffix} net R', 1e-12)
            scope = (mine.session < END).to_numpy()
            z, signal_ok = literal_labels(f, mine.loc[scope])
            assert signal_ok.all(), (stock, suffix, 'signal bar')
            close(z, mine.z.to_numpy(float)[scope], f'{stock}{suffix} z', 1e-9)
            far = mine.distance.eq('far_below').to_numpy()[scope]
            flip = far != (z < -1)
            assert not flip.any() or np.all(np.abs(z[flip]+1) < 1e-9), (stock, 'far labels')
            entry[suffix or 'primary'] = dict(trades=len(sim), labelled=int(scope.sum()))
            if not suffix:
                saved[stock] = mine.loc[mine['sample'].eq('primary')].sort_values(['submitted', 'ticket'], kind='stable').reset_index(drop=True)
        report['stocks'][stock] = entry
        print(f'{stock}: trades, economics and labels independently reproduced.', flush=True)
    verify_analysis(saved, report)


def verify_analysis(saved, report):
    verdict = json.loads((OUT/'verdict.json').read_text(encoding='utf-8'))
    included = verdict['included_stocks']
    for s in STOCKS:
        far = saved[s].distance.eq('far_below')
        adequate = far.sum() >= 200 and saved[s].loc[far, 'week_start'].nunique() >= 30
        assert adequate == (s in included), s
    frame = pd.concat([saved[s] for s in included], ignore_index=True)
    cal = pd.DatetimeIndex(pd.read_csv(OUT/'calendars.csv', parse_dates=['session']).session.unique()).sort_values()
    far = frame.distance.eq('far_below').to_numpy()
    pnl, risk, r = (frame[c].to_numpy(float) for c in ('net_dollars', 'initial_risk_dollars', 'net_r'))
    s_idx = frame.symbol.map({k: i for i, k in enumerate(included)}).to_numpy()
    e_idx = frame.era.map({k: i for i, k in enumerate(ERAS)}).to_numpy()
    decile, tertile = np.empty(len(frame), int), np.empty(len(frame), int)
    for (si, ei), g in frame.groupby([s_idx, e_idx]):
        decile[g.index] = rank_in(g, 10)
        tertile[g.index] = rank_in(g, 3)
    cells = s_idx*20+e_idx*10+decile
    boots = np.load(OUT/'bootstrap.npz')
    assert np.array_equal(cells, boots['cells'])
    contrast = pd.read_csv(OUT/'contrast.csv').set_index('scope')
    scopes = {'pooled': np.ones(len(frame), bool), **{era: e_idx == i for i, era in enumerate(ERAS)},
              **{s: s_idx == i for i, s in enumerate(included)}}
    estimates = {}
    for name, m in scopes.items():
        estimates[name], negative = weighted(r[m], far[m], cells[m])
        close([estimates[name], negative], [contrast.loc[name, 'estimate'], contrast.loc[name, 'negative_cells']], f'contrast {name}', 1e-12)
    weeks = pd.DatetimeIndex(boots['weeks'].astype('datetime64[D]'))
    assert weeks[0] == cal[0]-pd.Timedelta(days=cal[0].dayofweek) and len(weeks) == (weeks[-1]-weeks[0]).days//7+1
    wpos = weeks.get_indexer(frame.week_start)
    sums, counts = np.zeros((len(weeks), cells.max()+1, 2)), np.zeros((len(weeks), cells.max()+1, 2))
    np.add.at(sums, (wpos, cells, far.astype(int)), r)
    np.add.at(counts, (wpos, cells, far.astype(int)), 1)
    values = []
    for row in boots['starts'].astype(int):
        mult = np.bincount(((row[:, None]+np.arange(4)) % len(weeks)).ravel()[:len(weeks)], minlength=len(weeks)).astype(float)
        s_, c_ = np.tensordot(mult, sums, axes=1), np.tensordot(mult, counts, axes=1)
        ok = (c_[:, 0] > 0) & (c_[:, 1] > 0)
        values.append((c_[ok, 1]*(s_[ok, 1]/c_[ok, 1]-s_[ok, 0]/c_[ok, 0])).sum()/c_[ok, 1].sum())
    close(values, boots['values'], 'bootstrap draws', 1e-10)
    low, high = np.quantile(values, [.025, .975], method='linear')
    close([low, high], [contrast.loc['pooled', 'ci95_low'], contrast.loc['pooled', 'ci95_high']], 'interval', 1e-10)
    # Placebo invariants and portfolio draw statistics.
    day = cal.get_indexer(frame.session)
    months = frame.submitted.dt.strftime('%Y-%m').to_numpy()
    nd = len(cal)
    port = {k: np.zeros((2000, nd)) for k in ('B1', 'B2', 'B3')}
    kept = {k: np.zeros((2000, 2)) for k in port}
    b4_daily = np.zeros(nd)
    for i, stock in enumerate(included):
        z = np.load(OUT/f'placebo_masks_{stock}.npz')
        idx = np.flatnonzero(s_idx == i)
        assert np.array_equal(idx, z['rows'])
        f_far = far[idx]
        masks = {k: np.unpackbits(z[k], axis=1, count=len(idx)).astype(bool) for k in ('B1', 'B2', 'B3')}
        mcell = pd.factorize(pd.Series(months[idx])+'|'+pd.Series(tertile[idx]).astype(str))[0]
        for key, groups in (('B1', cells[idx]), ('B3', mcell)):
            assert not (masks[key] & f_far).any()
            for g in np.unique(groups):
                m = groups == g
                assert (masks[key][:, m].sum(axis=1) == min(int(f_far[m].sum()), int((~f_far[m]).sum()))).all(), (stock, key)
        for j, month in enumerate(pd.unique(months[idx])):
            block = np.flatnonzero(months[idx] == month)
            rolled = f_far[block][(np.arange(len(block))[None, :]-z['B2_offsets'][:, j][:, None]) % len(block)]
            assert np.array_equal(masks['B2'][:, block], rolled), (stock, month)
        b4 = np.zeros(len(idx), bool)
        sub = frame.iloc[idx].reset_index(drop=True)
        for e in range(2):
            members = np.flatnonzero(e_idx[idx] == e)
            ranked = sub.iloc[members].sort_values(['initial_risk_dollars', 'submitted', 'ticket'], kind='mergesort').index.to_numpy()
            b4[ranked[len(ranked)-int(f_far[members].sum()):]] = True
        assert np.array_equal(b4, z['B4'])
        b4_daily += np.bincount(day[idx][~b4], weights=pnl[idx][~b4], minlength=nd)
        for key in port:
            for d in range(2000):
                keep = idx[~masks[key][d]]
                port[key][d] += np.bincount(day[keep], weights=pnl[keep], minlength=nd)
                for e in range(2):
                    kept[key][d, e] += risk[keep][e_idx[keep] == e].sum()
    draws = pd.read_csv(OUT/'placebo_draws.csv')
    placebos = pd.read_csv(OUT/'placebos.csv').set_index(['period', 'placebo'])
    summaries = pd.read_csv(OUT/'summaries.csv').set_index(['period', 'curve'])
    era_risk = np.array([risk[e_idx == e].sum() for e in range(2)])
    rule_daily = np.bincount(day[~far], weights=pnl[~far], minlength=nd)
    base_daily = np.bincount(day, weights=pnl, minlength=nd)
    for p, (a, b) in {'pooled': ('2018-05-01', '2026-10-01'), **ERAS}.items():
        cols = slice(cal.searchsorted(pd.Timestamp(a)), cal.searchsorted(pd.Timestamp(b)))
        eras = [0, 1] if p == 'pooled' else [list(ERAS).index(p)]
        rule_dd = maxdd(rule_daily[cols])
        close([base_daily[cols].sum(), maxdd(base_daily[cols]), rule_daily[cols].sum(), rule_dd],
              [summaries.loc[(p, 'baseline'), 'net_dollars'], summaries.loc[(p, 'baseline'), 'daily_close_dd'],
               summaries.loc[(p, 'retained'), 'net_dollars'], summaries.loc[(p, 'retained'), 'daily_close_dd']], f'summary {p}', 1e-6)
        for key in port:
            dd = np.array([maxdd(x) for x in port[key][:, cols]])
            net = port[key][:, cols].sum(axis=1)
            share = kept[key][:, eras].sum(axis=1)/era_risk[eras].sum()
            x = draws.loc[(draws.period == p) & (draws.placebo == key)].sort_values('draw')
            close(np.c_[net, dd, share], x[['net_dollars', 'daily_close_dd', 'risk_kept']].to_numpy(), f'{p} {key} draws', 1e-6)
            row = placebos.loc[(p, key)]
            close([np.median(dd), np.mean(dd > rule_dd+TIE), np.mean(net < row.rule_net-TIE)],
                  [row.dd_median, row.rule_beats_dd, row.rule_beats_net], f'{p} {key} summary', 1e-6)
        close([maxdd(b4_daily[cols])], [placebos.loc[(p, 'B4'), 'dd_median']], f'{p} B4', 1e-6)
    # Verdict from verified numbers.
    test1 = bool(estimates['pooled'] < 0 and high < 0)
    test2 = bool(placebos.loc[('pooled', 'B1'), 'rule_beats_dd'] >= .95 and placebos.loc[('pooled', 'B2'), 'rule_beats_dd'] >= .95)
    eras_ok = all(estimates[e] < 0 and placebos.loc[(e, 'B1'), 'rule_dd'] < placebos.loc[(e, 'B1'), 'dd_median']
                  and placebos.loc[(e, 'B2'), 'rule_dd'] < placebos.loc[(e, 'B2'), 'dd_median'] for e in ERAS)
    test3 = bool(eras_ok and sum(estimates[s] < 0 for s in included) >= 7)
    result = 'inconclusive' if len(included) < 8 else 'supports' if (test1 and test2 and test3) else 'does not support'
    assert result == verdict['verdict'] and (test1, test2, test3) == (verdict['test1_contrast'], verdict['test2_placebos'], verdict['test3'])
    report.update(all_passed=True, verdict=result, tests=dict(test1=test1, test2=test2, test3=test3),
                  outputs_sha256={p.name: sha_file(p) for p in sorted(OUT.glob('*')) if p.suffix in ('.csv', '.npz', '.json')
                                  and p.name != 'independent_verification.json'})
    (OUT/'independent_verification.json').write_text(json.dumps(report, indent=2, default=str)+'\n', encoding='utf-8')
    print(f'All checks passed. Verdict independently reproduced: {result}.', flush=True)


if __name__ == '__main__':
    main()
