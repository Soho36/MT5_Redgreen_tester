"""Frozen cross-instrument test of the RTL far-below VWAP rule (ledger omission).

Protocol: docs/baseline/rtl-vwap/CROSS_PROTOCOL.md (ES, YM, RTY; NQ reference).
`prepare` parses, reconciles and labels trades and computes no outcome;
`analyze` reads outcomes only after every source check in `prepare` passed.
"""
from __future__ import annotations

import html
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_rtl_market_regimes as regimes
import analyze_rtl_vwap as av
import build_rtl_vwap_features as vw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_vwap_cross_20261027'
PROTOCOL = ROOT / 'docs/baseline/rtl-vwap/CROSS_PROTOCOL.md'
PROTOCOL_SHA256 = '39a0884b7d746de14902e8a87833c4903da0965e331b47e7ead3b277cf912886'
NQ_STUDY = ROOT / 'Reports/rtl_vwap_20261025'
YM_RUNS, RTY_RUNS = ROOT / 'Reports/ym_baselines_20261023', ROOT / 'Reports/rty_baselines_20261023'
DATA = Path(r'F:\DATABENTO')
COST, END = 1.05, pd.Timestamp('2026-10-01')
BOOT_DRAWS, PLACEBO_DRAWS = 5000, 2000
TIE = 1e-6  # dollars: PnL moves in whole ticks, so equal totals differ only by float error; ties count against the rule
VARIANT = 'full_hlc3'
SETTINGS = ('MaxRedRun=0', 'MinLocation=0', 'RiskReward=1.0', 'FlattenFallback=true',
            'UseEarlyCloseCalendar=true', 'Period=M30', 'Model=1')
EARLY = {'2016-19': ('2016-01-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01')}
OLD = {'2010-15': ('2010-01-01', '2016-01-01')}
INSTRUMENTS = {
    'NQ': dict(k=0, role='reference', runs=YM_RUNS, tag='ymbase_20261023_rtl_nq',
               symbol='MNQcontDTBNT20102026_2', point_value=2.0, primary=EARLY, secondary=OLD,
               minutes=DATA/'MNQ_16_YEARS/MT5_NQ_continuous_2010-2026_ohlcv-1m.csv'),
    'ES': dict(k=1, role='primary', runs=YM_RUNS, tag='ymbase_20261023_rtl_es',
               symbol='MEScontDTBNT20102026_2', point_value=5.0, primary=EARLY, secondary=OLD,
               minutes=DATA/'ES_16_YEARS/MT5_ES_continuous_2010-2026_ohlcv-1m.csv'),
    'YM': dict(k=2, role='primary', runs=YM_RUNS, tag='ymbase_20261023_rtl_ym',
               symbol='MYMcontDTBNT20102026', point_value=0.5, primary=EARLY, secondary=OLD,
               minutes=DATA/'YM_16_YEARS/MT5_YM_continuous_2010-2026_ohlcv-1m.csv'),
    'RTY': dict(k=3, role='primary', runs=RTY_RUNS, tag='rtybase_20261023_rtl',
                symbol='M2KcontDTBNT20172026', point_value=5.0,
                primary={'2018-19': ('2018-01-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01')},
                secondary={'2017H2': ('2017-07-01', '2018-01-01')},
                minutes=DATA/'RTY_16_YEARS/MT5_RTY_continuous_2017-2026_ohlcv-1m.csv'),
}
# Hashes copied from the frozen protocol's input table.
FROZEN = {
    DATA/'ES_16_YEARS/MT5_ES_continuous_2010-2026_ohlcv-1m.csv': '433cd1ee3f0f3c8b9d644849b75290927a80e8e5d5ff869e6781a53c5ee966a5',
    DATA/'ES_16_YEARS/MT5_ES_continuous_2010-2026_rolls.csv': '7fdadb910fc8797bcb3a8d591ecd5e264df783bac78e50552bfff10e72432b56',
    DATA/'YM_16_YEARS/MT5_YM_continuous_2010-2026_ohlcv-1m.csv': 'bc9f4ceb85c32ad856faeb5f1bda31d02006c98d9bbb5c941d1969388fb5cea5',
    DATA/'YM_16_YEARS/MT5_YM_continuous_2010-2026_rolls.csv': 'a43f1072b26a45f6d835e3f0d10833875ca6515ed318d12db4cdec60831c34db',
    DATA/'RTY_16_YEARS/MT5_RTY_continuous_2017-2026_ohlcv-1m.csv': '0d039c8cda8311ee4e26937a2d5512652654466853c56fe91781a59ac39d349c',
    DATA/'RTY_16_YEARS/MT5_RTY_continuous_2017-2026_rolls.csv': '6bbf3e99ac7389417eef24a332660c66f2bb15a999a8d0ab3609d5f919597943',
    DATA/'MNQ_16_YEARS/MT5_NQ_continuous_2010-2026_ohlcv-1m.csv': 'df3390928189f0d12c2140c3994671998151d8cb7289189b6f8a8ad83ff74e6a',
    DATA/'MNQ_16_YEARS/MT5_NQ_continuous_2010-2026_rolls.csv': '7421df167e9bcdcdd21a310395f388e041d50de4ed42d987095c5596109be49d',
    YM_RUNS/'ymbase_20261023_rtl_es.htm': '1e30301889f3bc164f186d8149672cb945e57a7d2a72afdb8b737e88d6174e81',
    YM_RUNS/'runband_ymbase_20261023_rtl_es_1.00.csv': '78df4a367427fa81a6831ce6cb3d12c453cfb8dacc573f9e46c9d006ef96c0b3',
    YM_RUNS/'runband_ymbase_20261023_rtl_es_1.00_stats.csv': '4470e5846fc9fdabe61697bc59907d71b30d009ce1899d8ede71568176728393',
    YM_RUNS/'ymbase_20261023_rtl_ym.htm': '741c3ec4810088c4f6f491d77cb34e950c7bf5d721f7a0b80558d429823578f0',
    YM_RUNS/'runband_ymbase_20261023_rtl_ym_1.00.csv': '012e8c1213ce1fa09a77ccdca30910df5398b6cbfa8b82889736b74b59a88416',
    YM_RUNS/'runband_ymbase_20261023_rtl_ym_1.00_stats.csv': 'b5c132502832f422c7d79cf7e444167936a381919a88b8eed653c7d2d4445148',
    RTY_RUNS/'rtybase_20261023_rtl.htm': '3da4d2f36bde2c21f19a087a0686d4d999a2730be7f45ef2d38820c27286c580',
    RTY_RUNS/'runband_rtybase_20261023_rtl_1.00.csv': 'fe0aeee980857bb96613dac6a29f5726ef68c4ba108f98909b4632a9497d9479',
    RTY_RUNS/'runband_rtybase_20261023_rtl_1.00_stats.csv': '13e1df0e1b4ad1e84a63b2028646a8294635fd5905c250b8065f0d5eae1201d1',
    YM_RUNS/'ymbase_20261023_rtl_nq.htm': '6b724f98866f81d8493f4a317bd841d6fe16633761ca0004e1c31f8ff8cd48c2',
    YM_RUNS/'runband_ymbase_20261023_rtl_nq_1.00.csv': '88c0d6144b1ce8ecc937a8f5333188240bc41b6cf241cef2e3778dde7bd752e5',
    YM_RUNS/'runband_ymbase_20261023_rtl_nq_1.00_stats.csv': 'a9be3898eb2d75fee95df2a94452682ee8941e1fce5964d6d76f6ff713723ee2',
    NQ_STUDY/'trades.csv': '1a3fbb6b4303ec6c72d2b2c85c9d9db1303ec66fd398a9ff5ea1c2af8ea91365',
    ROOT/'python/build_rtl_vwap_features.py': '1dd7adc771100f80570b8ce608f3a11d3fc0a81c4c103536c6de119bbbfc51e4',
}
PUBLISHED = {('ES', '2016-19'): (6286, -4652.80), ('ES', '2020-26'): (10803, -9085.65),
             ('YM', '2016-19'): (6209, 690.55), ('YM', '2020-26'): (10889, -2466.95),
             ('RTY', '2018-19'): (3207, -2179.35), ('RTY', '2020-26'): (10778, -3486.40)}
NQ_OMISSION = {'2016-19': (3938.65, 931.95), '2020-26': (43435.25, 3084.05)}
DERIVED = ('gross_r', 'net_dollars', 'net_r', 'commission_r', 'holding_minutes', 'stress1_net_dollars',
           'stress1_net_r', 'stress2_net_dollars', 'stress2_net_r')
DATE_COLUMNS = ('submitted', 'entry_time', 'exit_time', 'session', 'week_start', 'bar_time',
                'available_at', 'feature_session', 'first_minute', 'last_minute')
CELL = re.compile(r'<td\b[^>]*>(.*?)</td>', re.I)
TAG = re.compile(r'<[^>]*>')
STAMP = re.compile(r'^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$')


def number(text):
    return float(text.replace(' ', '').replace('\xa0', ''))


def rolls_path(spec):
    return spec['minutes'].with_name(spec['minutes'].name.replace('_ohlcv-1m.csv', '_rolls.csv'))


def run_paths(spec):
    folder, tag = spec['runs'], spec['tag']
    return dict(report=folder/f'{tag}.htm', ledger=folder/f'runband_{tag}_1.00.csv',
                stats=folder/f'runband_{tag}_1.00_stats.csv', ini=folder/f'{tag}.ini',
                completed=folder/f'{tag}.completed.json')


# ---------------------------------------------------------------- prepare (no outcomes)

def parse_report(path, symbol):
    """Buy-stop orders and buy-in/sell-out deal pairs from an MT5 tester report."""
    orders, trades, active, section = {}, [], None, None
    with Path(path).open(encoding='utf-16') as stream:
        for line in stream:
            if '>Orders<' in line:
                section = 'orders'
            elif '>Deals<' in line:
                section = 'deals'
            if '<tr' not in line or '</tr>' not in line:
                continue
            cells = [html.unescape(TAG.sub('', text)).strip() for text in CELL.findall(line)]
            if not cells or not STAMP.match(cells[0]):
                continue
            if section == 'orders' and len(cells) == 11 and cells[3] in ('buy stop', 'buy'):
                assert cells[2] == symbol and cells[3] == 'buy stop', cells
                ticket = int(cells[1])
                assert ticket not in orders
                orders[ticket] = {'submitted': cells[0], 'requested_price': number(cells[5]),
                                  'original_sl': number(cells[6]), 'state': cells[9]}
            elif section == 'deals' and len(cells) == 13 and cells[3] != 'balance':
                assert cells[2] == symbol, cells
                assert number(cells[5]) == 1 and number(cells[8]) == 0 and number(cells[9]) == 0, cells
                if cells[3:5] == ['buy', 'in']:
                    assert active is None
                    ticket = int(cells[7])
                    assert ticket in orders and orders[ticket]['state'] == 'filled'
                    active = dict(orders[ticket], ticket=ticket, entry_time=cells[0],
                                  fill_price=number(cells[6]), entry_profit=number(cells[10]))
                elif cells[3:5] == ['sell', 'out']:
                    assert active is not None
                    trades.append(dict(active, exit_time=cells[0], exit_price=number(cells[6]),
                                       trade_profit=active['entry_profit']+number(cells[10]),
                                       exit_comment=cells[12]))
                    active = None
                else:
                    raise ValueError(f'Unsupported deal {cells[3:5]}')
    assert active is None and trades
    frame = pd.DataFrame(trades).drop(columns=['state', 'entry_profit'])
    assert frame.ticket.is_unique
    for column in ('submitted', 'entry_time', 'exit_time'):
        frame[column] = pd.to_datetime(frame[column], format='%Y.%m.%d %H:%M:%S')
    return frame


def reconcile(spec):
    """MT5 report against its runband ledger, stats file, INI and completion record."""
    paths = run_paths(spec)
    completion = json.loads(paths['completed'].read_text(encoding='utf-8'))
    assert completion['tag'] == spec['tag']
    for key in ('ledger', 'stats'):
        assert completion['outputs'][paths[key].name] == av.digest(paths[key]), key
    ini = paths['ini'].read_text(encoding='utf-16')
    for setting in (*SETTINGS, f"Symbol={spec['symbol']}"):
        assert setting in ini, setting
    raw = pd.read_csv(paths['ledger'], sep='\t', encoding='utf-16')
    assert raw.ticket.is_unique
    report = parse_report(paths['report'], spec['symbol'])
    paired = report.set_index('ticket').reindex(raw.ticket)
    assert len(raw) == len(report) and paired.entry_time.notna().all()
    for column in ('entry_time', 'exit_time'):
        assert np.array_equal(pd.to_datetime(raw[column], format='%Y.%m.%d %H:%M:%S').to_numpy(), paired[column].to_numpy())
    assert np.allclose(raw.trade_profit, paired.trade_profit, rtol=0, atol=1e-8)
    assert np.allclose(raw.candle_range, paired.requested_price-paired.original_sl, rtol=0, atol=1e-8)
    stats = pd.read_csv(paths['stats'], sep='\t', encoding='utf-16')
    assert len(stats) == 1 and stats.iloc[0].run_tag == spec['tag'] and stats.iloc[0].risk_reward == 1
    totals = {'trades': len(report), 'net_profit': float(report.trade_profit.sum()),
              'gross_profit': float(report.loc[report.trade_profit > 0, 'trade_profit'].sum()),
              'gross_loss': float(report.loc[report.trade_profit < 0, 'trade_profit'].sum())}
    for key, value in totals.items():
        assert np.isclose(value, stats.iloc[0][key], rtol=0, atol=1e-7), key
    report = report.merge(raw[['ticket', 'candle_range', 'red_run', 'location']], on='ticket', validate='one_to_one')
    report = report.sort_values(['entry_time', 'ticket'], kind='stable').reset_index(drop=True)
    assert (report.submitted <= report.entry_time).all() and (report.entry_time <= report.exit_time).all()
    # Cross-date orders/positions are allowed only where session data ends early (checked later).
    cross_orders = int((report.submitted.dt.normalize() != report.entry_time.dt.normalize()).sum())
    cross_positions = int((report.entry_time.dt.normalize() != report.exit_time.dt.normalize()).sum())
    assert (report.submitted.dt.hour >= 1).all()
    assert (report.entry_time.iloc[1:].to_numpy() >= report.exit_time.iloc[:-1].to_numpy()).all()
    pv = spec['point_value']
    assert np.allclose(report.trade_profit, (report.exit_price-report.fill_price)*pv, atol=1e-7, rtol=0)
    return report, dict(report_trades=len(report), ledger_trades=len(raw), whole_run_totals=totals,
                        ini_settings=[*SETTINGS, f"Symbol={spec['symbol']}"], completion_hashes_match=True,
                        cross_date_orders=cross_orders, cross_date_positions=cross_positions, overlapping_positions=0)


def explain_cross_date(report, bars):
    """A date-crossing order or position must come from a session whose data ends before
    the 23:30 flatten, and resolve in the first minute of the next session's data."""
    day = bars.bar_time.dt.normalize()
    last, first = bars.groupby(day).last_minute.max(), bars.groupby(day).first_minute.min()
    rows = []
    for row in report.itertuples():
        for start, event, kind in ((row.submitted, row.entry_time, 'order'), (row.entry_time, row.exit_time, 'position')):
            if start.normalize() == event.normalize():
                continue
            session = start.normalize()
            following = first.loc[first.index > session].iloc[0]
            ended = last.loc[session]
            explained = bool(ended.hour*60+ended.minute < 23*60+29 and event.floor('min') == following)
            rows.append(dict(kind=kind, ticket=int(row.ticket), session=str(session.date()),
                             session_last_minute=str(ended), resolved_at=str(event), next_first_minute=str(following),
                             explained=explained))
    assert all(row['explained'] for row in rows), rows
    return rows


def economics(report, spec):
    frame = report.copy()
    pv = spec['point_value']
    frame['session'] = frame.submitted.dt.normalize()
    frame['initial_risk_dollars'] = (frame.requested_price-frame.original_sl)*pv
    frame['fill_risk_dollars'] = (frame.fill_price-frame.original_sl)*pv
    frame['fill_minus_request_dollars'] = (frame.fill_price-frame.requested_price)*pv
    assert (frame.initial_risk_dollars > 0).all()
    frame['gross_r'] = frame.trade_profit/frame.initial_risk_dollars
    frame['net_dollars'] = frame.trade_profit-COST
    frame['net_r'] = frame.net_dollars/frame.initial_risk_dollars
    frame['commission_r'] = COST/frame.initial_risk_dollars
    frame['holding_minutes'] = (frame.exit_time-frame.entry_time).dt.total_seconds()/60
    for stress in (1, 2):
        frame[f'stress{stress}_net_dollars'] = frame.net_dollars-stress
        frame[f'stress{stress}_net_r'] = frame[f'stress{stress}_net_dollars']/frame.initial_risk_dollars
    frame['year'] = frame.session.dt.year
    frame['week_start'] = frame.session-pd.to_timedelta(frame.session.dt.dayofweek, unit='D')
    frame['era'] = 'outside'
    frame['sample'] = 'excluded'
    for sample in ('secondary', 'primary'):
        for era, (start, stop) in spec[sample].items():
            inside = (frame.session >= start) & (frame.session < stop)
            frame.loc[inside, 'era'] = era
            frame.loc[inside, 'sample'] = sample
    frame.loc[frame.session >= END, ['era', 'sample']] = ['endpoint', 'excluded']
    assert not frame.era.eq('outside').any()
    return frame


def minute_bars(path):
    chunks, last, rows = [], None, 0
    for raw in pd.read_csv(path, sep='\t', chunksize=400000):
        bars, first, final = vw.aggregate_chunk(raw)
        assert last is None or first > last
        last = final
        rows += len(raw)
        chunks.append(bars)
    return vw.combine_bars(pd.concat(chunks, ignore_index=True)), rows


def switch_flags(bars, path):
    """First observed M30 bar on each date that trades a new contract."""
    rolls = pd.read_csv(path, parse_dates=['date'])
    assert rolls.date.is_unique and rolls.date.is_monotonic_increasing
    dates = pd.DatetimeIndex(rolls.loc[rolls.symbol.ne(rolls.symbol.shift()) & rolls.symbol.shift().notna(), 'date'])
    first = bars.groupby(bars.bar_time.dt.normalize()).bar_time.first()
    assert dates.isin(first.index).all()
    return bars.bar_time.isin(first.loc[dates]).to_numpy(), len(dates)


def signal_bar_check(labelled):
    """Labelled bar must be the red signal bar: high = buy stop, low = stop."""
    scope = labelled.loc[labelled.session < END]
    match = (np.isclose(scope.requested_price, scope.high, rtol=0, atol=1e-9)
             & np.isclose(scope.original_sl, scope.low, rtol=0, atol=1e-9) & scope.close.lt(scope.open))
    bad = scope.loc[~match, ['ticket', 'submitted', 'requested_price', 'high', 'original_sl', 'low', 'open', 'close']]
    share = float(len(bad)/len(scope))
    assert share <= .001, f'Signal-bar mismatches {len(bad)} of {len(scope)}'
    return dict(checked=len(scope), mismatches=len(bad), share=share,
                examples=bad.head(20).astype(str).to_dict('records'))


def same(actual, expected):
    a, b = pd.Series(actual).reset_index(drop=True), pd.Series(expected).reset_index(drop=True)
    if pd.api.types.is_datetime64_any_dtype(a) or pd.api.types.is_datetime64_any_dtype(b):
        return bool(pd.to_datetime(a).equals(pd.to_datetime(b)))
    if pd.api.types.is_bool_dtype(a) or pd.api.types.is_bool_dtype(b):
        return bool(np.array_equal(a.astype(bool), b.astype(bool)))
    if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
        return bool(np.array_equal(a.to_numpy(float), b.to_numpy(float), equal_nan=True))
    return bool(np.array_equal(a.fillna('').astype(str).to_numpy(), b.fillna('').astype(str).to_numpy()))


def nq_reference(features, labelled, calendar_all):
    """New code on the NQ run must reproduce the VWAP study's features, panel and omission."""
    expected = av.dates(pd.read_csv(NQ_STUDY/f'features_{VARIANT}.csv', float_precision='round_trip'),
                        ['bar_time', 'available_at', 'feature_session', 'first_minute', 'last_minute'])
    assert list(expected.columns) == list(features.columns)
    differing = [c for c in features.columns if not same(features[c], expected[c])]
    assert not differing, f'NQ features differ: {differing}'
    panel = av.dates(pd.read_csv(NQ_STUDY/'trades.csv', float_precision='round_trip'), DATE_COLUMNS)
    panel = panel.loc[panel.variant.eq(VARIANT)].sort_values(['submitted', 'ticket'], kind='stable').reset_index(drop=True)
    mine = labelled.loc[labelled['sample'].eq('primary')].sort_values(['submitted', 'ticket'], kind='stable').reset_index(drop=True)
    assert len(mine) == len(panel) == 16668
    assert same(mine.submitted, panel.submitted) and same(mine.entry_time, panel.entry_time)
    compared = [c for c in panel.columns if c in mine.columns]
    differing = [c for c in compared if c not in DERIVED and not same(mine[c], panel[c])]
    assert not differing, f'NQ panel differs: {differing}'
    # The reference stores derived economics at 15 significant digits (market-regimes CSV).
    rounding = {c: float(np.max(np.abs(mine[c].to_numpy(float)-panel[c].to_numpy(float)))) for c in DERIVED}
    assert max(rounding.values()) <= 1e-9, rounding
    omission = {}
    for era, (net, dd) in NQ_OMISSION.items():
        start, stop = EARLY[era]
        calendar = calendar_all[(calendar_all >= start) & (calendar_all < stop)]
        rows, _ = av.policy_comparison(mine.loc[mine.era.eq(era)], calendar, 'skip_far_below', with_sessions=False)
        retained = next(row for row in rows if row['curve'] == 'retained')
        assert np.isclose(retained['net_dollars'], net, rtol=0, atol=1e-6), era
        assert np.isclose(retained['daily_close_dd'], dd, rtol=0, atol=1e-6), era
        omission[era] = dict(net_dollars=retained['net_dollars'], daily_close_dd=retained['daily_close_dd'])
    return dict(features_identical=True, feature_rows=len(features), panel_trades=len(mine),
                panel_columns_identical=[c for c in compared if c not in DERIVED],
                derived_max_abs_difference=rounding, omission=omission)


def prepare():
    assert av.digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol changed'
    for path, value in FROZEN.items():
        assert av.digest(path) == value, f'Frozen input changed: {path}'
    OUT.mkdir(parents=True, exist_ok=True)
    audit, calendars = dict(protocol_sha256=PROTOCOL_SHA256, inputs_verified=len(FROZEN), instruments={}), []
    for name, spec in INSTRUMENTS.items():
        report, source = reconcile(spec)
        trades = economics(report, spec)
        published = {}
        for (instrument, era), (count, net) in PUBLISHED.items():
            if instrument == name:
                part = trades.loc[trades.era.eq(era)]
                assert len(part) == count and np.isclose(part.net_dollars.sum(), net, rtol=0, atol=.005), (name, era)
                published[era] = dict(trades=len(part), net_dollars=round(float(part.net_dollars.sum()), 2))
        bars, rows = minute_bars(spec['minutes'])
        source['cross_date'] = explain_cross_date(report, bars)
        bars['switch_bar'], roll_dates = switch_flags(bars, rolls_path(spec))
        features = vw.build_features(bars, VARIANT).loc[lambda x: x.available_at < END].reset_index(drop=True)
        labelled = vw.label_trades(trades, features)
        assert len(labelled) == len(trades) and labelled.ticket.is_unique
        calendar_all = pd.DatetimeIndex(features.bar_time.dt.normalize().unique()).sort_values()
        in_sample = labelled.loc[labelled['sample'].ne('excluded')]
        assert in_sample.session.isin(calendar_all).all()
        entry = dict(source=source, published=published, minute_rows=rows, m30_bars=len(bars),
                     feature_rows=len(features), roll_dates=roll_dates, switch_bars=int(bars.switch_bar.sum()),
                     signal_bar=signal_bar_check(labelled),
                     sample_trades=in_sample.groupby(['sample', 'era']).size().rename('n').reset_index().to_dict('records'),
                     labels=in_sample.groupby(['era', 'distance']).size().rename('n').reset_index().to_dict('records'),
                     unknown_reasons=in_sample.unknown_reason.fillna('').value_counts().to_dict())
        if name == 'NQ':
            entry['reference'] = nq_reference(features, labelled, calendar_all)
        features.to_csv(OUT/f'features_{name}.csv', index=False, float_format='%.17g')
        labelled.to_csv(OUT/f'trades_{name}.csv', index=False, float_format='%.17g')
        calendars.append(pd.DataFrame(dict(instrument=name, session=calendar_all)))
        audit['instruments'][name] = entry
        print(f"{name}: {len(trades):,} trades reconciled, {rows:,} minutes, {len(bars):,} M30 bars, "
              f"signal-bar mismatches {entry['signal_bar']['mismatches']}", flush=True)
    pd.concat(calendars, ignore_index=True).to_csv(OUT/'calendars.csv', index=False)
    audit['outputs_sha256'] = {p.name: av.digest(p) for p in sorted(OUT.glob('*.csv'))}
    audit['all_passed'] = True
    av.save_json(OUT/'source_audit.json', audit)
    print('All source checks passed; no outcome computed.', flush=True)


# ---------------------------------------------------------------- analyze (outcomes)

def rank_groups(frame, k):
    """Equal-count groups by planned risk, ties by submission time (sizes differ by <= 1)."""
    order = np.lexsort((frame.ticket.to_numpy(), frame.submitted.to_numpy(), frame.initial_risk_dollars.to_numpy()))
    groups = np.empty(len(frame), int)
    groups[order] = np.arange(len(frame))*k//len(frame)
    return groups


def contrast(r, far, cells, members=None):
    """Far-below minus other mean net R per cell, weighted by far-below counts."""
    keep = np.ones(len(r), bool) if members is None else members
    rows = []
    for cell in np.unique(cells[keep]):
        inside = keep & (cells == cell)
        f, o = inside & far, inside & ~far
        used = bool(f.any() and o.any())
        rows.append(dict(cell=int(cell), far_trades=int(f.sum()), other_trades=int(o.sum()),
                         far_mean_r=float(r[f].mean()) if f.any() else np.nan,
                         other_mean_r=float(r[o].mean()) if o.any() else np.nan,
                         difference=float(r[f].mean()-r[o].mean()) if used else np.nan, used=used))
    frame = pd.DataFrame(rows)
    used = frame.loc[frame.used]
    estimate = float((used.far_trades*used.difference).sum()/used.far_trades.sum()) if len(used) else np.nan
    return estimate, frame


def contrast_bootstrap(r, far, cells, week_pos, nweeks, rng):
    """Circular 4-week blocks over calendar weeks; each draw recomputes cells and weights."""
    ncell = int(cells.max())+1
    sums, counts = np.zeros((nweeks, ncell, 2)), np.zeros((nweeks, ncell, 2))
    flag = far.astype(int)
    np.add.at(sums, (week_pos, cells, flag), r)
    np.add.at(counts, (week_pos, cells, flag), 1)
    starts = rng.integers(0, nweeks, size=(BOOT_DRAWS, math.ceil(nweeks/4)))
    indices = ((starts[:, :, None]+np.arange(4)) % nweeks).reshape(BOOT_DRAWS, -1)[:, :nweeks]
    present = np.zeros(ncell, bool)
    present[np.unique(cells)] = True
    values, left_out = np.empty(BOOT_DRAWS), np.empty(BOOT_DRAWS, int)
    for offset in range(0, BOOT_DRAWS, 100):
        s, c = sums[indices[offset:offset+100]].sum(axis=1), counts[indices[offset:offset+100]].sum(axis=1)
        valid = (c[:, :, 0] > 0) & (c[:, :, 1] > 0)
        means = np.divide(s, c, out=np.zeros_like(s), where=c > 0)
        weights = np.where(valid, c[:, :, 1], 0.)
        total = weights.sum(axis=1)
        values[offset:offset+100] = np.divide((weights*(means[:, :, 1]-means[:, :, 0])).sum(axis=1), total,
                                              out=np.full(len(total), np.nan), where=total > 0)
        left_out[offset:offset+100] = (present[None, :] & ~valid).sum(axis=1)
    return values, left_out, starts.astype(np.int32)


def cell_placebo(far, cells, rng):
    """Per cell, skip as many non-far-below trades as far-below ones (all if too few)."""
    plan, shortfall = [], 0
    for cell in np.unique(cells):
        idx = np.flatnonzero(cells == cell)
        need, pool = int(far[idx].sum()), idx[~far[idx]]
        if need > len(pool):
            shortfall += need-len(pool)
            need = len(pool)
        if need:
            plan.append((pool, need))
    masks = np.zeros((PLACEBO_DRAWS, len(far)), bool)
    for draw in range(PLACEBO_DRAWS):
        for pool, need in plan:
            masks[draw, rng.choice(pool, need, replace=False)] = True
    return masks, shortfall


def rolled_placebo(far, months, rng):
    """Roll the actual skip pattern circularly within each month (submission order)."""
    blocks = [np.flatnonzero(months == month) for month in pd.unique(months)]
    sizes = np.array([len(block) for block in blocks])
    offsets = rng.integers(0, sizes, size=(PLACEBO_DRAWS, len(blocks)))
    masks = np.zeros((PLACEBO_DRAWS, len(far)), bool)
    for j, block in enumerate(blocks):
        positions = (np.arange(len(block))[None, :]-offsets[:, j][:, None]) % len(block)
        masks[:, block] = far[block][positions]
    return masks, offsets.astype(np.int32)


def largest_risk(frame, far):
    mask = np.zeros(len(frame), bool)
    for era in pd.unique(frame.era):
        idx = np.flatnonzero(frame.era.eq(era).to_numpy())
        order = idx[np.lexsort((frame.ticket.to_numpy()[idx], frame.submitted.to_numpy()[idx],
                                frame.initial_risk_dollars.to_numpy()[idx]))]
        count = int(far[idx].sum())
        mask[order[len(order)-count:]] = True
    return mask


def period_stats(masks, pnl, risk, members, day, ncal):
    """Net, daily-close DD and planned risk kept for each skip mask, within one period."""
    idx = np.flatnonzero(members)
    total_risk = risk[idx].sum()
    out = np.empty((len(masks), 3))
    for draw, mask in enumerate(masks):
        keep = idx[~mask[idx]]
        daily = np.bincount(day[keep], weights=pnl[keep], minlength=ncal)
        out[draw] = (pnl[keep].sum(), av.max_dd(daily), risk[keep].sum()/total_risk)
    return out


def comovement_labels(trades, nq):
    joined = pd.merge_asof(trades[['submitted', 'ticket']].sort_values(['submitted', 'ticket']), nq,
                           left_on='submitted', right_on='available_at', direction='backward', allow_exact_matches=True)
    joined = joined.set_index('ticket').reindex(trades.ticket)
    known = joined.feature_session.eq(trades.submitted.dt.normalize().to_numpy()).to_numpy() & joined.z.notna().to_numpy()
    return np.where(known, joined.distance.to_numpy(), 'unknown')


def load_trades(name):
    return av.dates(pd.read_csv(OUT/f'trades_{name}.csv', float_precision='round_trip', low_memory=False), DATE_COLUMNS)


def analyze():
    assert av.digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol changed'
    audit = json.loads((OUT/'source_audit.json').read_text(encoding='utf-8'))
    assert audit['all_passed']
    for file, value in audit['outputs_sha256'].items():
        assert av.digest(OUT/file) == value, f'Prepared output changed: {file}'
    calendars = pd.read_csv(OUT/'calendars.csv', parse_dates=['session'])
    nq = av.dates(pd.read_csv(OUT/'features_NQ.csv', usecols=['available_at', 'feature_session', 'z', 'distance'],
                              float_precision='round_trip'), ['available_at', 'feature_session']).sort_values('available_at')
    tables = {key: [] for key in ('summaries', 'contrast', 'contrast_cells', 'unadjusted', 'confounds', 'placebos',
                                  'placebo_draws', 'annual', 'roll_clean', 'comovement', 'verdict')}
    for name, spec in INSTRUMENTS.items():
        trades = load_trades(name)
        observed = pd.DatetimeIndex(calendars.loc[calendars.instrument.eq(name), 'session']).sort_values()
        boot_rng = np.random.default_rng(202610270+spec['k'])
        placebo_rng = np.random.default_rng(202610280+spec['k'])
        masks_out, boot_out = {}, {}
        for sample in ('primary', 'secondary'):
            eras = spec[sample]
            role = spec['role'] if sample == 'primary' else 'secondary'
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
                deciles[inside] = rank_groups(frame.loc[inside], 10)
                tertiles[inside] = rank_groups(frame.loc[inside], 3)
            cells = era_index*10+deciles
            months = frame.submitted.dt.to_period('M').astype(str).to_numpy()
            month_cells = pd.factorize(pd.Series(months)+'_'+pd.Series(tertiles).astype(str))[0]
            members = {p: (np.ones(len(frame), bool) if p == 'pooled' else frame.era.eq(p).to_numpy()) for p in periods}
            days = {p: cal.get_indexer(frame.session) for p, cal in periods.items()}
            for p in periods:
                assert (days[p][members[p]] >= 0).all(), (name, sample, p)
            head = dict(instrument=name, role=role, sample=sample)
            # Baseline, rule and same-holding scaling (NQ study's comparison).
            for p, cal in periods.items():
                rows, _ = av.policy_comparison(frame.loc[members[p]], cal, 'skip_far_below', with_sessions=False)
                tables['summaries'].extend(dict(head, period=p, **row) for row in rows)
            # A. Risk-matched contrast; bootstrap on the sample (pooled when two eras).
            sample_period = 'pooled' if 'pooled' in periods else next(iter(periods))
            weeks = pd.date_range(periods[sample_period][0]-pd.Timedelta(days=periods[sample_period][0].dayofweek),
                                  periods[sample_period][-1]-pd.Timedelta(days=periods[sample_period][-1].dayofweek), freq='7D')
            week_pos = weeks.get_indexer(frame.week_start)
            assert (week_pos >= 0).all()
            values, left_out, starts = contrast_bootstrap(r, far, cells, week_pos, len(weeks), boot_rng)
            boot_out.update({f'{sample}_values': values, f'{sample}_left_out': left_out, f'{sample}_starts': starts,
                             f'{sample}_weeks': weeks.to_numpy().astype('datetime64[D]').astype(np.int64)})
            finite = values[np.isfinite(values)]
            low, high = np.quantile(finite, [.025, .975], method='linear')
            for p in periods:
                estimate, cell_frame = contrast(r, far, cells, members[p])
                tables['contrast_cells'].extend(dict(head, period=p, **row) for row in cell_frame.to_dict('records'))
                row = dict(head, period=p, estimate=estimate, cells=len(cell_frame), cells_used=int(cell_frame.used.sum()),
                           negative_cells=int((cell_frame.difference < 0).sum()),
                           far_trades=int(far[members[p]].sum()), far_active_weeks=int(frame.loc[members[p] & far, 'week_start'].nunique()))
                if p == sample_period:
                    row.update(ci95_low=float(low), ci95_high=float(high), boot_draws=len(values), boot_valid=len(finite),
                               boot_mean_left_out=float(left_out.mean()), boot_max_left_out=int(left_out.max()))
                tables['contrast'].append(row)
            # C. NQ study's unadjusted contrast (its bootstrap) and time x risk adjustment, per era.
            for era in eras:
                era_frame = frame.loc[frame.era.eq(era)]
                rows, _, _ = av.bootstrap(era_frame, periods[era], boot_rng)
                tables['unadjusted'].extend(dict(head, period=era, **row) for row in rows if row['policy'] == 'skip_far_below')
                _, summary = av.confounds(era_frame, 'skip_far_below')
                tables['confounds'].append(dict(head, period=era, **summary))
            # B. Placebos without VWAP (pooled draws; eras restrict the same draws).
            b1, short1 = cell_placebo(far, cells, placebo_rng)
            b2, offsets = rolled_placebo(far, months, placebo_rng)
            b3, short3 = cell_placebo(far, month_cells, placebo_rng)
            b4 = largest_risk(frame, far)[None, :]
            masks_out.update({f'{sample}_tickets': frame.ticket.to_numpy(), f'{sample}_far': far,
                              f'{sample}_cells': cells, f'{sample}_month_cells': month_cells,
                              f'{sample}_B2_offsets': offsets, f'{sample}_B4': b4[0]})
            for key, masks in (('B1', b1), ('B2', b2), ('B3', b3)):
                masks_out[f'{sample}_{key}'] = np.packbits(masks, axis=1)
            for p, cal in periods.items():
                rule = period_stats(far[None, :], pnl, risk, members[p], days[p], len(cal))[0]
                retained = next(row for row in tables['summaries'] if row['instrument'] == name and row['sample'] == sample
                                and row['period'] == p and row['curve'] == 'retained')
                assert np.isclose(rule[0], retained['net_dollars'], rtol=0, atol=1e-6)
                assert np.isclose(rule[1], retained['daily_close_dd'], rtol=0, atol=1e-6)
                for key, masks, shortfall in (('B1', b1, short1), ('B2', b2, 0), ('B3', b3, short3), ('B4', b4, 0)):
                    stats = period_stats(masks, pnl, risk, members[p], days[p], len(cal))
                    if key != 'B4':
                        tables['placebo_draws'].append(pd.DataFrame(dict(instrument=name, sample=sample, period=p, placebo=key,
                            draw=np.arange(len(stats)), net_dollars=stats[:, 0], daily_close_dd=stats[:, 1], risk_kept=stats[:, 2])))
                    q = np.quantile(stats, [.05, .5, .95], axis=0)
                    tables['placebos'].append(dict(head, period=p, placebo=key, draws=len(stats),
                        shortfall=shortfall if p == 'pooled' or len(periods) == 1 else np.nan,
                        rule_net=rule[0], rule_dd=rule[1], rule_risk_kept=rule[2],
                        net_q05=q[0, 0], net_median=q[1, 0], net_q95=q[2, 0], dd_q05=q[0, 1], dd_median=q[1, 1],
                        dd_q95=q[2, 1], risk_kept_median=q[1, 2],
                        rule_beats_dd=float(np.mean(stats[:, 1] > rule[1]+TIE)),
                        ties_dd=float(np.mean(np.abs(stats[:, 1]-rule[1]) <= TIE)),
                        rule_beats_net=float(np.mean(stats[:, 0] < rule[0]-TIE)),
                        ties_net=float(np.mean(np.abs(stats[:, 0]-rule[0]) <= TIE))))
            # C. Annual, roll-clean and co-movement with NQ.
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
                estimate, cell_frame = contrast(r, far, cells, members[p] & clean)
                for row in rows:
                    tables['roll_clean'].append(dict(head, period=p, contrast_estimate=estimate,
                                                     contrast_negative_cells=int((cell_frame.difference < 0).sum()), **row))
            if name != 'NQ':
                nq_label = comovement_labels(frame, nq)
                for p in periods:
                    m = members[p]
                    estimate, cell_frame = contrast(r, far, cells, m & (nq_label != 'far_below'))
                    tables['comovement'].append(dict(head, period=p, trades=int(m.sum()), far_trades=int((m & far).sum()),
                        far_with_nq_far=int((m & far & (nq_label == 'far_below')).sum()),
                        far_with_nq_known_not_far=int((m & far & (nq_label != 'far_below') & (nq_label != 'unknown')).sum()),
                        far_with_nq_unknown=int((m & far & (nq_label == 'unknown')).sum()),
                        all_with_nq_far=int((m & (nq_label == 'far_below')).sum()),
                        contrast_without_nq_far=estimate, negative_cells_without_nq_far=int((cell_frame.difference < 0).sum()),
                        far_trades_without_nq_far=int(cell_frame.far_trades.sum())))
            tables['verdict'].append(verdict_row(head, eras, sample_period, tables))
        np.savez_compressed(OUT/f'placebo_masks_{name}.npz', **masks_out)
        np.savez_compressed(OUT/f'bootstrap_{name}.npz', **boot_out)
        print(f'{name}: outcomes computed.', flush=True)
    write_outputs(tables)


def verdict_row(head, eras, sample_period, tables):
    def pick(table, **keys):
        rows = [row for row in tables[table] if all(row.get(k) == v for k, v in {**head, **keys}.items())]
        return rows
    contrast_rows = {row['period']: row for row in pick('contrast')}
    placebo = {(row['period'], row['placebo']): row for row in pick('placebos')}
    adequate = all(contrast_rows[era]['far_trades'] >= 200 and contrast_rows[era]['far_active_weeks'] >= 30 for era in eras)
    main = contrast_rows[sample_period]
    test1 = bool(main['estimate'] < 0 and main['ci95_high'] < 0)
    test2 = bool(placebo[(sample_period, 'B1')]['rule_beats_dd'] >= .95 and placebo[(sample_period, 'B2')]['rule_beats_dd'] >= .95)
    if len(eras) > 1:
        test3 = all(contrast_rows[era]['estimate'] < 0
                    and placebo[(era, 'B1')]['rule_dd'] < placebo[(era, 'B1')]['dd_median']
                    and placebo[(era, 'B2')]['rule_dd'] < placebo[(era, 'B2')]['dd_median'] for era in eras)
    else:
        test3 = None
    confirms = bool(adequate and test1 and test2 and (test3 is None or test3))
    return dict(head, period=sample_period, adequate=adequate, test1_contrast=test1, test2_placebos=test2,
                test3_each_era=test3, confirms=confirms, counts_for_verdict=head['role'] == 'primary')


def plain(value):
    """JSON-safe copy: numpy scalars to Python, non-finite floats to None."""
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def write_outputs(tables):
    frames = {}
    for key, rows in tables.items():
        frames[key] = pd.concat(rows, ignore_index=True) if key == 'placebo_draws' else pd.DataFrame(rows)
        frames[key].to_csv(OUT/f'{key}.csv', index=False, float_format='%.15g')
    verdict = frames['verdict']
    primary = verdict.loc[verdict.counts_for_verdict]
    confirmed = int(primary.confirms.sum())
    overall = 'transfers' if confirmed >= 2 else 'partial' if confirmed == 1 else 'does not transfer'
    result = dict(overall=overall, confirming_instruments=primary.loc[primary.confirms, 'instrument'].tolist(),
                  primary=primary.to_dict('records'),
                  reference_and_secondary=verdict.loc[~verdict.counts_for_verdict].to_dict('records'))
    av.save_json(OUT/'verdict.json', plain(result))
    provenance = dict(protocol_sha256=PROTOCOL_SHA256, inputs_sha256={str(k): v for k, v in FROZEN.items()},
                      programs_sha256={p.name: av.digest(p) for p in (Path(__file__), Path(vw.__file__), Path(av.__file__),
                                                                       Path(regimes.__file__))},
                      outputs_sha256={p.name: av.digest(p) for p in sorted(OUT.glob('*')) if p.suffix in ('.csv', '.npz', '.json')
                                      and p.name not in ('provenance.json', 'independent_verification.json')},
                      seeds=dict(bootstrap='202610270 + k', placebos='202610280 + k', k={n: s['k'] for n, s in INSTRUMENTS.items()}),
                      draws=dict(bootstrap=BOOT_DRAWS, placebos=PLACEBO_DRAWS),
                      software=dict(numpy=np.__version__, pandas=pd.__version__), exploratory=False, replay=False)
    av.save_json(OUT/'provenance.json', provenance)
    print(verdict.to_string(index=False))
    print(f'Overall: {overall} ({confirmed} of 3 primary instruments confirm).', flush=True)


if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    assert stage in ('prepare', 'analyze', 'all')
    if stage in ('prepare', 'all'):
        prepare()
    if stage in ('analyze', 'all'):
        analyze()
