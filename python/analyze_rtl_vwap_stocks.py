"""Frozen test of the RTL far-below VWAP rule on ten Nasdaq-100 stocks (ledger omission).

Protocol: docs/baseline/rtl-vwap/STOCK_PROTOCOL.md. `prepare` checks the sources, simulates
RTL and labels trades without computing outcomes; `analyze` computes outcomes only after every
source check passed.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import databento as db
import numpy as np
import pandas as pd

import analyze_rtl_vwap as av
import analyze_rtl_vwap_cross as cx
import build_rtl_vwap_features as vw
import rtl_stock_engine as engine

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_vwap_stocks_20261028'
PROTOCOL = ROOT / 'docs/baseline/rtl-vwap/STOCK_PROTOCOL.md'
PROTOCOL_SHA256 = 'a12a4172b7d326e4e86d2537ddd0101c93849ccbe22daee11120211c5bfb4e38'
DATA = Path(r'F:\DATABENTO\STOCKS')
FROZEN = {DATA/'NVDA-XNAS-20261028-NHDY74EDDE.zip': '07188fceb083489dd18389b42b330b8e8f4d726dcda452d9f802befdb88a1062',
          ROOT/'python/build_rtl_vwap_features.py': '1dd7adc771100f80570b8ce608f3a11d3fc0a81c4c103536c6de119bbbfc51e4'}
NVDA_DBN_SHA256 = 'd2486d79131a6e2a06771f7fc98174cad3b8740db3d1386ea9e367c49e40c781'
NQ_FEATURES = ROOT / 'Reports/rtl_vwap_cross_20261027/features_NQ.csv'
NQ_MT5 = ROOT / 'Reports/rtl_vwap_replay_20261026/trades_off.csv'
STOCKS = ('AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'AVGO', 'TSLA', 'COST', 'NFLX')
META_FROM = pd.Timestamp('2022-06-09')    # FB before, META from; earlier META bars are another security
START, END = pd.Timestamp('2018-05-01'), pd.Timestamp('2026-10-01')
ERAS = {'2018-19': ('2018-05-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01')}
SESSION_START, SESSION_END, EARLY_END, RTH_START = 4*60, 16*60, 13*60, 9*60+30
CUTOFF, EARLY_CUTOFF = 15*60+30, 12*60+30
NOTIONAL, COST = 10_000.0, 2.0
BOOT_SEED, PLACEBO_SEED = 2026102801, 2026102802
# Announced splits (first split-adjusted session, ratio n:1); each is confirmed in the data.
SPLITS = {('AAPL', '2020-08-31'): 4, ('TSLA', '2020-08-31'): 5, ('NVDA', '2021-07-20'): 4,
          ('AMZN', '2022-06-06'): 20, ('GOOGL', '2022-07-18'): 20, ('TSLA', '2022-08-25'): 3,
          ('NVDA', '2024-06-10'): 10, ('AVGO', '2024-07-15'): 10, ('NFLX', '2025-11-17'): 10}
# Other overnight moves beyond 30%, investigated: real price moves, not data errors.
GENUINE_MOVES = {('NFLX', '2022-04-20'): 'earnings reaction (Q1 2022 subscriber loss)'}
# Nasdaq 13:00 closes in the data range: detected from volume and present in the EA's calendar.
EARLY_CLOSES = ('2018-07-03', '2018-11-23', '2018-12-24', '2019-07-03', '2019-11-29', '2019-12-24',
                '2020-11-27', '2020-12-24', '2021-11-26', '2022-11-25', '2023-07-03', '2023-11-24',
                '2024-07-03', '2024-11-29', '2024-12-24', '2025-07-03', '2025-11-28', '2025-12-24')
DATE_COLUMNS = ('submitted', 'entry_time', 'exit_time', 'session', 'week_start', 'bar_time',
                'available_at', 'feature_session', 'first_minute', 'last_minute')


def sha(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- prepare (no outcomes)

def read_sources():
    """Every zip in the folder: metadata checks, hashes, minutes in New York time."""
    for path, value in FROZEN.items():
        assert av.digest(path) == value, f'Frozen input changed: {path}'
    frames, files = [], []
    for path in sorted(DATA.glob('*.zip')):
        z = zipfile.ZipFile(path)
        query = json.loads(z.read('metadata.json'))['query']
        assert query['dataset'] == 'XNAS.ITCH' and query['schema'] == 'ohlcv-1m' and query['stype_in'] == 'raw_symbol', path
        member = [n for n in z.namelist() if n.endswith('.dbn')]
        assert len(member) == 1
        raw = z.read(member[0])
        if path.name.startswith('NVDA-'):
            assert sha(raw) == NVDA_DBN_SHA256
        df = db.DBNStore.from_bytes(io.BytesIO(raw)).to_df(pretty_ts=True, price_type='float')
        frames.append(pd.DataFrame(dict(symbol=df.symbol.to_numpy(), t=df.index.tz_convert('America/New_York').tz_localize(None),
                                        open=df.open.to_numpy(float), high=df.high.to_numpy(float), low=df.low.to_numpy(float),
                                        close=df.close.to_numpy(float), volume=df.volume.to_numpy(float))))
        files.append(dict(file=path.name, sha256=av.digest(path), dbn=member[0], dbn_sha256=sha(raw), symbols=query['symbols'],
                          start=str(pd.Timestamp(query['start'], unit='ns').date()), end=str(pd.Timestamp(query['end'], unit='ns').date())))
    minutes = pd.concat(frames, ignore_index=True)
    requested = [s for f in files for s in f['symbols']]
    missing = sorted(set(STOCKS) - set(requested))
    assert not missing, f'Missing raw symbols {missing}: download them before any label (protocol source check)'
    assert len(requested) == len(set(requested)), 'A raw symbol was downloaded twice'
    # Deviation decided before any outcome: Databento offers no FB history to the user, so Meta
    # enters from 2022-06-09 (its first META session); earlier META bars belong to an ETF.
    for f in files:
        assert f['start'] <= '2018-05-01' and f['end'] >= ('2022-06-09' if f['symbols'] == ['FB'] else '2026-10-27'), f
    fb, meta = minutes.symbol.eq('FB'), minutes.symbol.eq('META')
    dropped_meta = int((meta & (minutes.t < META_FROM)).sum())
    minutes = minutes.loc[~(meta & (minutes.t < META_FROM)) & ~(fb & (minutes.t >= META_FROM))].copy()
    minutes.loc[minutes.symbol.eq('FB'), 'symbol'] = 'META'
    assert set(minutes.symbol) == set(STOCKS)
    # A few bars carry volume but no price (Databento undefined price). They cannot enter VWAP or
    # fills, so they are dropped and counted; decided before any outcome.
    undefined = ~np.isfinite(minutes[['open', 'high', 'low', 'close']].to_numpy()).all(axis=1)
    clock = minutes.t.dt.hour*60 + minutes.t.dt.minute
    priceless = minutes.loc[undefined].assign(in_session=(clock[undefined] >= SESSION_START) & (clock[undefined] < SESSION_END))
    priceless = priceless.astype({'t': str})[['symbol', 't', 'volume', 'in_session']].to_dict('records')
    minutes = minutes.loc[~undefined]
    return minutes.sort_values(['symbol', 't'], kind='stable').reset_index(drop=True), files, dropped_meta, priceless


def early_close_check(minutes):
    """Days whose 14:00-15:59 share of regular-hours volume collapses (median over stocks)."""
    m = minutes.t.dt.hour*60 + minutes.t.dt.minute
    r = minutes.loc[(m >= RTH_START) & (m < SESSION_END)].assign(date=lambda x: x.t.dt.normalize(),
                                                                  late=lambda x: x.t.dt.hour >= 14)
    share = (r.loc[r.late].groupby(['date', 'symbol']).volume.sum() / r.groupby(['date', 'symbol']).volume.sum()).fillna(0)
    share = share.groupby('date').median()
    detected = sorted(f'{d:%Y-%m-%d}' for d in share.index[share < .08])
    assert detected == sorted(EARLY_CLOSES), detected
    return dict(early_closes=detected, lowest_share_other_days=float(share[share >= .08].min()),
                normal_median_share=float(share.median()))


def session_minutes(minutes, start_minute):
    m = minutes.t.dt.hour*60 + minutes.t.dt.minute
    end = np.where(minutes.t.dt.normalize().isin(pd.to_datetime(EARLY_CLOSES)), EARLY_END, SESSION_END)
    keep = (m >= start_minute) & (m < end) & (minutes.t >= START)
    return minutes.loc[keep].reset_index(drop=True)


def split_check(stock, g):
    """Overnight moves beyond 30% must be announced splits or investigated real moves."""
    days = g.groupby(g.t.dt.normalize()).agg(first=('open', 'first'), last=('close', 'last'))
    ratio = days['first'] / days['last'].shift()
    flagged = {f'{d:%Y-%m-%d}': float(r) for d, r in ratio[(ratio < 1/1.3) | (ratio > 1.3)].items()}
    rows = []
    for day, r in flagged.items():
        if (stock, day) in SPLITS:
            n = SPLITS[(stock, day)]
            assert abs(r*n - 1) < .15, (stock, day, r)
            rows.append(dict(stock=stock, date=day, ratio=r, split=n, deviation=r*n-1, within_5pct=bool(abs(r*n-1) <= .05)))
        else:
            assert (stock, day) in GENUINE_MOVES, f'Unexplained overnight move {stock} {day} {r:.4f}'
            rows.append(dict(stock=stock, date=day, ratio=r, split=None, deviation=None, within_5pct=None,
                             note=GENUINE_MOVES[(stock, day)]))
    for (s, day), n in SPLITS.items():
        if s == stock:
            assert day in flagged, f'Announced split not visible: {s} {day}'
    return rows


def adjust_splits(stock, g):
    factor = np.ones(len(g))
    for (s, day), n in SPLITS.items():
        if s == stock:
            factor[(g.t < pd.Timestamp(day)).to_numpy()] *= n
    g = g.copy()
    for column in ('open', 'high', 'low', 'close'):
        g[column] = g[column].to_numpy() / factor
    g['volume'] = g.volume.to_numpy() * factor
    return g


def validate_minutes(g):
    assert g.t.is_monotonic_increasing and g.t.is_unique
    assert (g.volume > 0).all() and np.isfinite(g[['open', 'high', 'low', 'close', 'volume']].to_numpy()).all()
    assert (g.high >= g[['open', 'close', 'low']].max(axis=1)).all() and (g.low <= g[['open', 'close', 'high']].min(axis=1)).all()


def cutoffs():
    return {int(d.replace('-', '')): EARLY_CUTOFF for d in EARLY_CLOSES}


def economics(sim, stock):
    t = sim.rename(columns={'requested': 'requested_price', 'sl': 'original_sl', 'fill': 'fill_price', 'reason': 'exit_comment'})
    for column in ('submitted', 'entry_time', 'exit_time'):
        t[column] = pd.to_datetime(t[column])
    shares = NOTIONAL / t.requested_price
    t['symbol'], t['ticket'], t['shares'] = stock, np.arange(len(t)), shares
    t['trade_profit'] = shares*(t.exit_price-t.fill_price)
    t['initial_risk_dollars'] = shares*(t.requested_price-t.original_sl)
    t['fill_risk_dollars'] = shares*(t.fill_price-t.original_sl)
    assert (t.initial_risk_dollars > 0).all()
    t['gross_r'] = t.trade_profit/t.initial_risk_dollars
    t['net_dollars'] = t.trade_profit-COST
    t['net_r'] = t.net_dollars/t.initial_risk_dollars
    t['commission_r'] = COST/t.initial_risk_dollars
    t['holding_minutes'] = (t.exit_time-t.entry_time).dt.total_seconds()/60
    for stress, extra in ((1, 2.0), (2, 4.0)):
        t[f'stress{stress}_net_dollars'] = t.net_dollars-extra
        t[f'stress{stress}_net_r'] = t[f'stress{stress}_net_dollars']/t.initial_risk_dollars
    t['session'] = t.submitted.dt.normalize()
    t['year'] = t.session.dt.year
    t['week_start'] = t.session-pd.to_timedelta(t.session.dt.dayofweek, unit='D')
    t['era'], t['sample'] = 'outside', 'excluded'
    for era, (start, stop) in ERAS.items():
        inside = (t.session >= start) & (t.session < stop)
        t.loc[inside, ['era', 'sample']] = [era, 'primary']
    return t


def features_for(g):
    raw = pd.DataFrame({'<DATE>': g.t.dt.strftime('%Y.%m.%d'), '<TIME>': g.t.dt.strftime('%H:%M:%S'),
                        '<OPEN>': g.open, '<HIGH>': g.high, '<LOW>': g.low, '<CLOSE>': g.close,
                        '<TICKVOL>': g.volume, '<VOL>': g.volume})
    bars, _, _ = vw.aggregate_chunk(raw)
    bars = vw.combine_bars(bars)
    bars['switch_bar'] = False
    return bars, vw.build_features(bars, cx.VARIANT).loc[lambda x: x.available_at < END].reset_index(drop=True)


def label(trades, features):
    """NQ's labelling, with trade times in the features' datetime resolution."""
    trades = trades.copy()
    for column in ('submitted', 'entry_time', 'exit_time', 'session', 'week_start'):
        trades[column] = trades[column].astype(features.available_at.dtype)
    return vw.label_trades(trades, features)


def cross_session_check(trades, bars, day_cutoffs):
    """Orders and positions stay in their session unless its data ends before the cutoff."""
    day = bars.bar_time.dt.normalize()
    last, first = bars.groupby(day).last_minute.max(), bars.groupby(day).first_minute.min()
    rows = []
    for row in trades.itertuples():
        for begin, event, kind in ((row.submitted, row.entry_time, 'order'), (row.entry_time, row.exit_time, 'position')):
            if begin.normalize() == event.normalize():
                continue
            session = begin.normalize()
            cut = day_cutoffs.get(int(f'{session:%Y%m%d}'), CUTOFF)
            ended = last.loc[session]
            following = first.loc[first.index > session]
            explained = bool(ended.hour*60+ended.minute < cut and len(following) and event.floor('min') == following.iloc[0])
            rows.append(dict(kind=kind, ticket=int(row.ticket), session=str(session.date()), last_minute=str(ended),
                             resolved_at=str(event), explained=explained))
    assert all(r['explained'] for r in rows), rows
    return rows


def nq_engine_check():
    """With NQ's session, cutoffs and MT5 fills the engine reproduces every MT5 NQ trade."""
    sim, rejected = engine.simulate(engine.nq_minutes(), engine.nq_cutoffs(), engine.NQ_CUTOFF, fills='mt5', first_order_minute=60)
    mt = pd.read_csv(NQ_MT5, usecols=['submitted', 'requested_price', 'original_sl', 'entry_time', 'exit_time', 'fill_price',
                                      'exit_price', 'trade_profit'], parse_dates=['submitted', 'entry_time', 'exit_time'])
    minute = lambda s: pd.to_datetime(s).dt.floor('min')
    sim['ent'], mt['ent'] = minute(sim.entry_time), minute(mt.entry_time)
    j = mt.merge(sim, on='ent', how='left', suffixes=('_m', '_s'), validate='one_to_one')
    extra = sim.loc[~sim.ent.isin(mt.ent)]
    result = dict(mt5_trades=len(mt), matched=int(j.requested.notna().sum()),
                  extra_before_mt5_start=int((extra.ent < mt.ent.min()).sum()), extra_after=int((extra.ent >= mt.ent.min()).sum()),
                  submit_minute_diff=int((minute(j.submitted_s) != minute(j.submitted_m)).sum()),
                  level_diff=int(((j.requested != j.requested_price) | (j.sl != j.original_sl) | (j.fill != j.fill_price)).sum()),
                  exit_price_diff=int((j.exit_price_s != j.exit_price_m).sum()),
                  exit_minute_diff=int((minute(j.exit_time_s) != minute(j.exit_time_m)).sum()),
                  profit_diff=int((np.abs((j.exit_price_s-j.fill)*2.0-j.trade_profit) > 1e-6).sum()))
    assert result['matched'] == result['mt5_trades'] == 25833 and result['extra_after'] == 0
    assert all(result[k] == 0 for k in ('submit_minute_diff', 'level_diff', 'exit_price_diff', 'exit_minute_diff', 'profit_diff'))
    return result


def prepare():
    assert av.digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol changed'
    OUT.mkdir(parents=True, exist_ok=True)
    audit = dict(protocol_sha256=PROTOCOL_SHA256, nq_engine=nq_engine_check())
    print('Engine reproduces all 25,833 MT5 NQ trades.', flush=True)
    minutes, files, dropped, priceless = read_sources()
    meta_from = minutes.loc[minutes.symbol.eq('META'), 't'].min()
    audit.update(files=files, meta_rows_dropped_before_2022_06_09=dropped, priceless_bars_dropped=priceless,
                 early_close=early_close_check(minutes),
                 meta_history=('FB then META' if any(f['symbols'] == ['FB'] for f in files) else
                               f'META only, from {meta_from:%Y-%m-%d}: FB not offered by Databento (user), '
                               'deviation decided before any outcome'))
    stocks, splits, calendars = {}, [], []
    for stock in STOCKS:
        raw = minutes.loc[minutes.symbol.eq(stock)]
        primary = session_minutes(raw, SESSION_START)
        splits += split_check(stock, primary)
        entry = dict(raw_minutes=len(raw))
        for name, start in (('primary', SESSION_START), ('rth', RTH_START)):
            g = adjust_splits(stock, session_minutes(raw, start))
            validate_minutes(g)
            bars_m1 = engine.minute_arrays(g.t, g.open, g.high, g.low, g.close)
            sim, rejected = engine.simulate(bars_m1, cutoffs(), CUTOFF, fills='gap', first_order_minute=0)
            trades = economics(sim, stock)
            bars, features = features_for(g)
            labelled = label(trades, features)
            assert len(labelled) == len(trades)
            in_sample = labelled.loc[labelled['sample'].eq('primary')]
            calendar = pd.DatetimeIndex(features.bar_time.dt.normalize().unique())
            calendar = calendar[(calendar >= START) & (calendar < END)]
            assert in_sample.session.isin(calendar).all()
            entry[name] = dict(session_minutes=len(g), m30_bars=len(bars), feature_rows=len(features), trades=len(trades),
                               rejected=rejected, sample_trades=len(in_sample), signal_bar=cx.signal_bar_check(labelled),
                               cross_session=cross_session_check(trades, bars, cutoffs()),
                               exits=labelled.exit_comment.value_counts().to_dict(),
                               labels=in_sample.distance.value_counts().to_dict())
            suffix = '' if name == 'primary' else '_rth'
            labelled.to_csv(OUT/f'trades{suffix}_{stock}.csv', index=False, float_format='%.17g')
            if name == 'primary':
                features.to_csv(OUT/f'features_{stock}.csv', index=False, float_format='%.17g')
                calendars.append(pd.DataFrame(dict(stock=stock, session=calendar)))
        stocks[stock] = entry
        print(f"{stock}: {entry['primary']['sample_trades']:,} trades in sample, signal-bar mismatches "
              f"{entry['primary']['signal_bar']['mismatches']}", flush=True)
    pd.concat(calendars, ignore_index=True).to_csv(OUT/'calendars.csv', index=False)
    audit.update(splits=splits, stocks=stocks)
    audit['outputs_sha256'] = {p.name: av.digest(p) for p in sorted(OUT.glob('*.csv'))}
    audit['all_passed'] = True
    av.save_json(OUT/'source_audit.json', cx.plain(audit))
    print('All source checks passed; no outcome computed.', flush=True)


# ---------------------------------------------------------------- analyze (outcomes)

def load(stock, suffix=''):
    frame = pd.read_csv(OUT/f'trades{suffix}_{stock}.csv', float_precision='round_trip', low_memory=False)
    frame = av.dates(frame, DATE_COLUMNS)
    return frame.loc[frame['sample'].eq('primary')].sort_values(['submitted', 'ticket'], kind='stable').reset_index(drop=True)


def maxdd_rows(daily):
    """Daily-close max drawdown of each row, starting from zero."""
    equity = np.concatenate([np.zeros((len(daily), 1)), np.cumsum(daily, axis=1)], axis=1)
    return np.max(np.maximum.accumulate(equity, axis=1)-equity, axis=1)


def label_cells(frame, stocks):
    """Stock x era x risk decile cells, and stock x month x risk tertile cells."""
    s = frame.symbol.map({k: i for i, k in enumerate(stocks)}).to_numpy()
    e = frame.era.map({k: i for i, k in enumerate(ERAS)}).to_numpy()
    decile, tertile = np.empty(len(frame), int), np.empty(len(frame), int)
    for (si, ei), idx in pd.Series(range(len(frame))).groupby([s, e]).groups.items():
        idx = np.asarray(idx)
        decile[idx] = cx.rank_groups(frame.iloc[idx], 10)
        tertile[idx] = cx.rank_groups(frame.iloc[idx], 3)
    month = frame.submitted.dt.strftime('%Y-%m').to_numpy()
    month_cells = pd.factorize(pd.Series(frame.symbol.to_numpy())+'|'+month+'|'+tertile.astype(str))[0]
    return s, e, s*20+e*10+decile, month_cells, month, tertile


def analyze():
    assert av.digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol changed'
    audit = json.loads((OUT/'source_audit.json').read_text(encoding='utf-8'))
    assert audit['all_passed']
    for file, value in audit['outputs_sha256'].items():
        assert av.digest(OUT/file) == value, f'Prepared output changed: {file}'
    frames = {stock: load(stock) for stock in STOCKS}
    adequacy = {stock: dict(far=int(f.distance.eq('far_below').sum()),
                            far_weeks=int(f.loc[f.distance.eq('far_below'), 'week_start'].nunique())) for stock, f in frames.items()}
    included = [s for s in STOCKS if adequacy[s]['far'] >= 200 and adequacy[s]['far_weeks'] >= 30]
    frame = pd.concat([frames[s] for s in included], ignore_index=True)
    calendars = pd.read_csv(OUT/'calendars.csv', parse_dates=['session'])
    cal = pd.DatetimeIndex(calendars.session.unique()).sort_values()
    periods = {'pooled': (str(START.date()), str(END.date())), **ERAS}
    bounds = {p: (int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b)))) for p, (a, b) in periods.items()}
    far = frame.distance.eq('far_below').to_numpy()
    pnl, risk, r = (frame[c].to_numpy(float) for c in ('net_dollars', 'initial_risk_dollars', 'net_r'))
    day = cal.get_indexer(frame.session)
    assert (day >= 0).all()
    s_idx, e_idx, cells, month_cells, months, tertile = label_cells(frame, included)
    tables = {k: [] for k in ('summaries', 'contrast', 'stocks', 'placebos', 'annual', 'descriptive', 'comovement')}
    # Portfolio baseline, rule and same-holding scaling per period (the NQ study's comparison).
    for p, (a, b) in periods.items():
        members = ((frame.session >= a) & (frame.session < b)).to_numpy()
        rows, _ = av.policy_comparison(frame.loc[members], cal[bounds[p][0]:bounds[p][1]], 'skip_far_below', with_sessions=False)
        tables['summaries'].extend(dict(period=p, **row) for row in rows)
    # A. Risk-matched contrast: pooled with bootstrap (same weeks for every stock), eras, stocks.
    boot_rng, placebo_rng = np.random.default_rng(BOOT_SEED), np.random.default_rng(PLACEBO_SEED)
    weeks = pd.date_range(cal[0]-pd.Timedelta(days=cal[0].dayofweek), cal[-1]-pd.Timedelta(days=cal[-1].dayofweek), freq='7D')
    week_pos = weeks.get_indexer(frame.week_start)
    assert (week_pos >= 0).all()
    values, left_out, starts = cx.contrast_bootstrap(r, far, cells, week_pos, len(weeks), boot_rng)
    finite = values[np.isfinite(values)]
    low, high = np.quantile(finite, [.025, .975], method='linear')
    np.savez_compressed(OUT/'bootstrap.npz', values=values, left_out=left_out, starts=starts,
                        weeks=weeks.to_numpy().astype('datetime64[D]').astype(np.int64), cells=cells)
    contrasts = {}
    for name, members in (('pooled', np.ones(len(frame), bool)), *((era, e_idx == i) for i, era in enumerate(ERAS)),
                          *((stock, s_idx == i) for i, stock in enumerate(included))):
        estimate, cell_frame = cx.contrast(r, far, cells, members)
        contrasts[name] = estimate
        row = dict(scope=name, estimate=estimate, cells_used=int(cell_frame.used.sum()),
                   negative_cells=int((cell_frame.difference < 0).sum()), far_trades=int(far[members].sum()))
        if name == 'pooled':
            row.update(ci95_low=float(low), ci95_high=float(high), boot_draws=len(values), boot_valid=len(finite),
                       boot_mean_left_out=float(left_out.mean()))
        tables['contrast'].append(row)
    # B. Placebos within each stock; statistics on the portfolio.
    ndays, keys = len(cal), ('B1', 'B2', 'B3')
    daily = {k: np.zeros((cx.PLACEBO_DRAWS, ndays)) for k in keys}
    kept = {k: np.zeros((cx.PLACEBO_DRAWS, len(ERAS))) for k in keys}
    stock_dd = {k: np.zeros((cx.PLACEBO_DRAWS, len(included))) for k in keys}
    base_daily, rule_daily, b4_daily = np.zeros(ndays), np.zeros(ndays), np.zeros(ndays)
    shortfalls = {k: 0 for k in keys}
    for i, stock in enumerate(included):
        idx = np.flatnonzero(s_idx == i)
        f_far, f_day, f_pnl, f_risk, f_era = far[idx], day[idx], pnl[idx], risk[idx], e_idx[idx]
        b1, short1 = cx.cell_placebo(f_far, cells[idx], placebo_rng)
        b2, offsets = cx.rolled_placebo(f_far, months[idx], placebo_rng)
        b3, short3 = cx.cell_placebo(f_far, month_cells[idx], placebo_rng)
        b4 = cx.largest_risk(frame.iloc[idx], f_far)
        shortfalls['B1'] += short1; shortfalls['B3'] += short3
        np.savez_compressed(OUT/f'placebo_masks_{stock}.npz', rows=idx, B1=np.packbits(b1, axis=1), B2=np.packbits(b2, axis=1),
                            B3=np.packbits(b3, axis=1), B2_offsets=offsets, B4=b4)
        base_daily += np.bincount(f_day, weights=f_pnl, minlength=ndays)
        rule_daily += np.bincount(f_day[~f_far], weights=f_pnl[~f_far], minlength=ndays)
        b4_daily += np.bincount(f_day[~b4], weights=f_pnl[~b4], minlength=ndays)
        for key, masks in (('B1', b1), ('B2', b2), ('B3', b3)):
            for d, mask in enumerate(masks):
                keep = ~mask
                one = np.bincount(f_day[keep], weights=f_pnl[keep], minlength=ndays)
                daily[key][d] += one
                stock_dd[key][d, i] = maxdd_rows(one[None, :])[0]
                for e in range(len(ERAS)):
                    kept[key][d, e] += f_risk[keep & (f_era == e)].sum()
        stock_rule = maxdd_rows(np.bincount(f_day[~f_far], weights=f_pnl[~f_far], minlength=ndays)[None, :])[0]
        stock_base = maxdd_rows(np.bincount(f_day, weights=f_pnl, minlength=ndays)[None, :])[0]
        tables['stocks'].append(dict(stock=stock, trades=len(idx), far_trades=int(f_far.sum()), far_share=float(f_far.mean()),
                                     contrast=contrasts[stock], baseline_net=float(f_pnl.sum()), rule_net=float(f_pnl[~f_far].sum()),
                                     baseline_dd=float(stock_base), rule_dd=float(stock_rule),
                                     rule_beats_B1_dd=float(np.mean(stock_dd['B1'][:, i] > stock_rule+cx.TIE)),
                                     rule_beats_B2_dd=float(np.mean(stock_dd['B2'][:, i] > stock_rule+cx.TIE))))
        print(f'{stock}: placebos drawn.', flush=True)
    era_risk = np.array([risk[e_idx == e].sum() for e in range(len(ERAS))])
    draws_out = []
    for p, (i0, i1) in bounds.items():
        cols = slice(i0, i1)
        era_cols = list(range(len(ERAS))) if p == 'pooled' else [list(ERAS).index(p)]
        rule_dd = float(maxdd_rows(rule_daily[None, cols])[0])
        rule_net = float(rule_daily[cols].sum())
        rule_kept = float(risk[~far & np.isin(e_idx, era_cols)].sum()/era_risk[era_cols].sum())
        for key in (*keys, 'B4'):
            if key == 'B4':
                dd = maxdd_rows(b4_daily[None, cols]); net = np.array([b4_daily[cols].sum()]); kept_share = np.array([np.nan])
            else:
                dd, net = maxdd_rows(daily[key][:, cols]), daily[key][:, cols].sum(axis=1)
                kept_share = kept[key][:, era_cols].sum(axis=1)/era_risk[era_cols].sum()
                draws_out.append(pd.DataFrame(dict(period=p, placebo=key, draw=np.arange(len(dd)), net_dollars=net,
                                                   daily_close_dd=dd, risk_kept=kept_share)))
            tables['placebos'].append(dict(period=p, placebo=key, draws=len(dd), shortfall=shortfalls.get(key, 0),
                                           rule_net=rule_net, rule_dd=rule_dd, rule_risk_kept=rule_kept,
                                           net_median=float(np.median(net)), dd_q05=float(np.quantile(dd, .05)),
                                           dd_median=float(np.median(dd)), dd_q95=float(np.quantile(dd, .95)),
                                           risk_kept_median=float(np.nanmedian(kept_share)) if key != 'B4' else np.nan,
                                           rule_beats_dd=float(np.mean(dd > rule_dd+cx.TIE)),
                                           ties_dd=float(np.mean(np.abs(dd-rule_dd) <= cx.TIE)),
                                           rule_beats_net=float(np.mean(net < rule_net-cx.TIE))))
    pd.concat(draws_out, ignore_index=True).to_csv(OUT/'placebo_draws.csv', index=False, float_format='%.15g')
    descriptive(frame, far, cells, tertile, cal, tables)
    write(tables, adequacy, included, contrasts)


def descriptive(frame, far, cells, tertile, cal, tables):
    """Unadjusted and time x risk contrasts, annual, costs, regular hours, co-movement with NQ."""
    r = frame.net_r.to_numpy(float)
    regular = (frame.submitted.dt.hour*60+frame.submitted.dt.minute >= RTH_START).to_numpy()
    for p, (a, b) in {'pooled': (START, END), **{k: (pd.Timestamp(x), pd.Timestamp(y)) for k, (x, y) in ERAS.items()}}.items():
        m = ((frame.session >= a) & (frame.session < b)).to_numpy()
        tables['descriptive'].append(dict(measure='unadjusted far-below minus others, mean net R', period=p,
                                          value=float(r[m & far].mean()-r[m & ~far].mean())))
        total, weight = 0., 0
        for block in (False, True):
            for t in range(3):
                c = m & (regular == block) & (tertile == t)
                if (c & far).any() and (c & ~far).any():
                    total += (c & far).sum()*(r[c & far].mean()-r[c & ~far].mean()); weight += (c & far).sum()
        tables['descriptive'].append(dict(measure='pre-market/regular x risk-group adjusted difference, mean net R', period=p,
                                          value=float(total/weight)))
        for extra, column in ((2, 'stress1_net_dollars'), (4, 'stress2_net_dollars')):
            tables['descriptive'].append(dict(measure=f'net at +${extra} cost: baseline / rule', period=p,
                                              value=float(frame.loc[m, column].sum()), value2=float(frame.loc[m & ~far, column].sum())))
    pnl = frame.net_dollars.to_numpy(float)
    for year in sorted(frame.year.unique()):
        ycal = cal[cal.year == year]
        m = frame.year.eq(year).to_numpy()
        ids = ycal.get_indexer(frame.session[m])
        tables['annual'].append(dict(year=int(year), trades=int(m.sum()), far_trades=int((m & far).sum()),
                                     baseline_net=float(pnl[m].sum()), rule_net=float(pnl[m & ~far].sum()),
                                     baseline_dd=float(maxdd_rows(np.bincount(ids, weights=pnl[m], minlength=len(ycal))[None, :])[0]),
                                     rule_dd=float(maxdd_rows(np.bincount(ids[~far[m]], weights=pnl[m][~far[m]], minlength=len(ycal))[None, :])[0])))
    # Regular-hours version (session and VWAP from 09:30): point estimates only.
    rth = pd.concat([load(s, '_rth') for s in frame.symbol.unique()], ignore_index=True)
    rfar = rth.distance.eq('far_below').to_numpy()
    _, _, rcells, _, _, _ = label_cells(rth, list(frame.symbol.unique()))
    estimate, _ = cx.contrast(rth.net_r.to_numpy(float), rfar, rcells)
    rday = cal.get_indexer(rth.session)
    ok = rday >= 0
    rp = rth.net_dollars.to_numpy(float)
    tables['descriptive'].append(dict(measure='regular hours: risk-matched contrast, mean net R', period='pooled', value=float(estimate)))
    tables['descriptive'].append(dict(measure='regular hours: net baseline / rule', period='pooled', value=float(rp.sum()),
                                      value2=float(rp[~rfar].sum())))
    tables['descriptive'].append(dict(measure='regular hours: daily-close DD baseline / rule', period='pooled',
        value=float(maxdd_rows(np.bincount(rday[ok], weights=rp[ok], minlength=len(cal))[None, :])[0]),
        value2=float(maxdd_rows(np.bincount(rday[ok & ~rfar], weights=rp[ok & ~rfar], minlength=len(cal))[None, :])[0])))
    # Co-movement with NQ: NQ's label at the same moment (NQ clock = New York + 7 hours).
    nq = av.dates(pd.read_csv(NQ_FEATURES, usecols=['available_at', 'feature_session', 'z', 'distance'],
                              float_precision='round_trip'), ['available_at', 'feature_session']).sort_values('available_at')
    shifted = frame[['submitted', 'ticket']].assign(submitted=frame.submitted+pd.Timedelta(hours=7))
    shifted['ticket'] = np.arange(len(frame))
    nq_label = cx.comovement_labels(shifted, nq)
    estimate, cell_frame = cx.contrast(r, far, cells, nq_label != 'far_below')
    tables['comovement'].append(dict(far_trades=int(far.sum()), far_with_nq_far=int((far & (nq_label == 'far_below')).sum()),
                                     far_with_nq_unknown=int((far & (nq_label == 'unknown')).sum()),
                                     contrast_without_nq_far=float(estimate),
                                     negative_cells_without_nq_far=int((cell_frame.difference < 0).sum())))


def write(tables, adequacy, included, contrasts):
    frames = {k: pd.DataFrame(v) for k, v in tables.items()}
    for key, f in frames.items():
        f.to_csv(OUT/f'{key}.csv', index=False, float_format='%.15g')
    placebo = frames['placebos'].set_index(['period', 'placebo'])
    pooled = frames['contrast'].set_index('scope').loc['pooled']
    enough = len(included) >= 8
    test1 = bool(pooled.estimate < 0 and pooled.ci95_high < 0)
    test2 = bool(placebo.loc[('pooled', 'B1'), 'rule_beats_dd'] >= .95 and placebo.loc[('pooled', 'B2'), 'rule_beats_dd'] >= .95)
    eras_ok = all(contrasts[era] < 0 and placebo.loc[(era, 'B1'), 'rule_dd'] < placebo.loc[(era, 'B1'), 'dd_median']
                  and placebo.loc[(era, 'B2'), 'rule_dd'] < placebo.loc[(era, 'B2'), 'dd_median'] for era in ERAS)
    negative_stocks = int(sum(contrasts[s] < 0 for s in included))
    test3 = bool(eras_ok and negative_stocks >= 7)
    verdict = 'inconclusive' if not enough else 'supports' if (test1 and test2 and test3) else 'does not support'
    result = dict(verdict=verdict, included_stocks=included, adequacy=adequacy, test1_contrast=test1, test2_placebos=test2,
                  test3_eras=eras_ok, negative_stocks=negative_stocks, test3=test3,
                  pooled_contrast=dict(estimate=pooled.estimate, ci95_low=pooled.ci95_low, ci95_high=pooled.ci95_high),
                  beats=dict(B1=placebo.loc[('pooled', 'B1'), 'rule_beats_dd'], B2=placebo.loc[('pooled', 'B2'), 'rule_beats_dd']))
    av.save_json(OUT/'verdict.json', cx.plain(result))
    av.save_json(OUT/'provenance.json', cx.plain(dict(
        protocol_sha256=PROTOCOL_SHA256, seeds=dict(bootstrap=BOOT_SEED, placebos=PLACEBO_SEED),
        draws=dict(bootstrap=cx.BOOT_DRAWS, placebos=cx.PLACEBO_DRAWS),
        programs_sha256={p.name: av.digest(p) for p in (Path(__file__), Path(engine.__file__), Path(cx.__file__), Path(vw.__file__), Path(av.__file__))},
        outputs_sha256={p.name: av.digest(p) for p in sorted(OUT.glob('*')) if p.suffix in ('.csv', '.npz', '.json')
                        and p.name not in ('provenance.json', 'independent_verification.json')},
        software=dict(numpy=np.__version__, pandas=pd.__version__, databento=db.__version__))))
    print(frames['contrast'].to_string(index=False))
    print(frames['placebos'].loc[frames['placebos'].placebo.isin(['B1', 'B2'])].to_string(index=False))
    print(json.dumps(cx.plain(result), indent=1))


if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    assert stage in ('prepare', 'analyze', 'all')
    if stage in ('prepare', 'all'):
        prepare()
    if stage in ('analyze', 'all'):
        analyze()
