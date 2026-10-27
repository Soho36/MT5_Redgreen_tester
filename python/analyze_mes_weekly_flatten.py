"""RTL on weekly MES candles, flattened every session, with the plain-long and random-timing controls (2026-10-27).

Protocol: docs/baseline/mes-weekly-flatten/PROTOCOL.md. Same simulator and helpers as the NQ weekly
studies, on the ES 1-minute source at $5 per point. Outputs in Reports/mes_weekly_flatten_20261027/.
Usage: python analyze_mes_weekly_flatten.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import rtl_weekly_engine as e
from analyze_instrument_baseline import load, max_dd
from analyze_rtl_weekly_control import SPREAD, gain, shifts
from analyze_rtl_weekly_control import STUDY as NQ_CONTROL
from analyze_rtl_weekly_flatten import COST, ERAS, LAST_DATE, STRESS, VARIANTS, era_slice, extras, metrics, paired, session_long, sha
from analyze_rtl_weekly_flatten import STUDY as NQ_FLAT

STUDY = e.ROOT / 'Reports/mes_weekly_flatten_20261027'
PROTOCOL = e.ROOT / 'docs/baseline/mes-weekly-flatten/PROTOCOL.md'
ES_M30 = e.ROOT / 'Reports/ym_baselines_20261023/runband_ymbase_20261023_rtl_es_1.00.csv'
NQ_M30 = e.ROOT / 'Reports/rtl_market_regimes_20261023/trades.csv'
W1_LEDGER = STUDY / 'runband_meswk_20261027_w1_hold_1.00.csv'
PV = 5.0
TICK = 0.25
DATA_HOLES = (20200228, 20200630)
SEED = 20261030


def minute_floor(s):
    return pd.to_datetime(s).dt.floor('min')


def validate(bars, cutoffs):
    """ES M30 against its MT5 ledger, MES W1 hold against the fresh MT5 run, NQ weekly unchanged."""
    sim, rejected = e.simulate_m30_ea(bars, cutoffs=cutoffs)
    mt = load(ES_M30)
    j = mt.assign(ent=mt.entry.dt.floor('min')).merge(sim.assign(ent=minute_floor(sim.entry_time)), on='ent',
                                                       how='left', suffixes=('_m', '_s'))
    assert j.requested.notna().all(), 'MT5 ES M30 trade missing from the simulation'
    gross = (j.exit_price - j.fill) * PV
    extra = sim.loc[~minute_floor(sim.entry_time).isin(mt.entry.dt.floor('min'))]
    m30 = {'mt5_trades': len(mt), 'matched': len(j), 'extra_before_mt5_start': int((extra.entry_time < mt.entry.min()).sum()),
           'extra_after_mt5_start': int((extra.entry_time >= mt.entry.min()).sum()),
           'profit_diff': int((abs(gross - j.trade_profit) > 1e-6).sum()),
           'range_diff': int((abs(j.requested - j.sl - j.candle_range) > 1e-6).sum()),
           'exit_minute_diff': int((minute_floor(j.exit_time_s) != j.exit.dt.floor('min')).sum()),
           'rejected_orders': rejected}
    assert m30['extra_after_mt5_start'] == 0 and m30['profit_diff'] == 0 and m30['range_diff'] == 0
    assert m30['exit_minute_diff'] == 0
    ones = np.ones(len(bars['o']))
    tr, _, _ = e.simulate_weekly(bars, bars['o'], bars['h'], bars['l'], bars['c'], ones, mode='hold', fills='mt5',
                                 point_value=PV)
    w1 = load(W1_LEDGER)
    stats = pd.read_csv(STUDY / 'runband_meswk_20261027_w1_hold_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
    assert len(w1) == int(stats.trades) and abs(w1.trade_profit.sum() - stats.net_profit) < 1e-6
    k = tr.assign(ent=minute_floor(tr.entry_time)).merge(w1.assign(ent=w1.entry.dt.floor('min')), on='ent')
    later = tr[tr.entry_time >= w1.entry.min()]
    assert len(k) == len(w1) == len(later)
    assert (minute_floor(k.exit_time_x) == k.exit.dt.floor('min')).all()
    assert np.allclose(k.gross, k.trade_profit, atol=1e-6) and np.allclose(k.requested - k.sl, k.candle_range)
    w1check = {'mt5_trades': len(w1), 'matched_exact': len(k), 'mt5_first_entry': str(w1.entry.min()),
               'simulated_before_mt5_start': int(len(tr) - len(later)), 'mt5_gross': float(w1.trade_profit.sum())}
    nq = e.load_minutes(NQ_FLAT / 'minutes.npz')
    f = e.roll_factor(nq, e.roll_switches(LAST_DATE))
    rtl, _, _ = e.simulate_weekly(nq, *(nq[x] * f for x in 'ohlc'), f, mode='flat', cutoffs=cutoffs, last_date=LAST_DATE)
    saved = pd.read_csv(NQ_FLAT / 'trades_W1_flatten.csv', parse_dates=['entry_time'])
    assert np.allclose(rtl.gross, saved.gross) and (rtl.entry_time == saved.entry_time).all()
    return m30, w1check


def weekly(bars, cutoffs, factor, contracts, mode, basis, fills, control=None):
    f = factor if basis == 'adjusted' else np.ones(len(factor))
    tr, pc, counts = e.simulate_weekly(bars, *(bars[x] * f for x in 'ohlc'), f, mode=mode, fills=fills,
                                       cutoffs=cutoffs, last_date=LAST_DATE, contracts=contracts, control=control,
                                       spread=SPREAD if control else 0.0, point_value=PV)
    tr['trade'] = np.arange(len(tr))
    tr['turns'] = tr.pieces if mode == 'flat' else 1 + (tr.rolls if basis == 'adjusted' else 0)
    pc['turns'] = 1 if mode == 'flat' else 0
    if mode == 'hold':
        last = pc.groupby('trade').tail(1).index
        pc.loc[last, 'turns'] = tr.turns.to_numpy()[pc.loc[last, 'trade'].to_numpy()]
    return tr, pc, counts, mode


def m30_baseline():
    mt = load(ES_M30)
    tr = pd.DataFrame({'trade': np.arange(len(mt)), 'entry_time': mt.entry, 'exit_time': mt.exit,
                       'gross': mt.trade_profit, 'risk_dollars': mt.candle_range * PV, 'turns': 1, 'pieces': 1})
    pc = pd.DataFrame({'trade': tr.trade, 'exit_time': tr.exit_time, 'gross': tr.gross, 'turns': 1})
    return tr, pc, {}, 'm30'


def resolution(runs):
    """Median signal range in ticks, ES and NQ, M30 and W1 (first-fill risk / point value / tick)."""
    nq_m30 = pd.read_csv(NQ_M30, parse_dates=['entry_time'])
    nq_w1 = pd.read_csv(NQ_FLAT / 'trades_W1_flatten.csv', parse_dates=['entry_time'])
    es_m30, es_w1 = runs['M30 baseline'][0], runs['W1 flatten'][0]
    out = {}
    for era, (lo, hi) in list(ERAS.items())[1:]:
        sel = lambda d: d[(d.entry_time >= lo) & (d.entry_time < hi)]
        out[era] = {'ES M30': float((sel(es_m30).risk_dollars / PV / TICK).median()),
                    'NQ M30': float((sel(nq_m30).candle_range / TICK).median()),
                    'ES W1': float((sel(es_w1).risk_dollars / PV / TICK).median()),
                    'NQ W1': float((sel(nq_w1).risk_dollars / e.POINT_VALUE / TICK).median())}
    return out


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    bars = e.load_minutes(STUDY / 'minutes_es.npz', source=e.ES_MINUTES)
    cutoffs = e.load_cutoffs()
    switches = e.roll_switches(LAST_DATE, e.ES_ROLLS)
    factor = e.roll_factor(bars, switches)
    contracts = e.contract_ids(bars, switches)
    m30check, w1check = validate(bars, cutoffs)
    print('Validation passed:', json.dumps({'m30': m30check, 'w1': w1check}), flush=True)
    runs = {name: weekly(bars, cutoffs, factor, contracts, *spec) for name, spec in VARIANTS.items()}
    runs['M30 baseline'] = m30_baseline()
    controls = {'Plain long': weekly(bars, cutoffs, factor, contracts, 'flat', 'adjusted', 'gap', 'plain'),
                'Red week, market entry': weekly(bars, cutoffs, factor, contracts, 'flat', 'adjusted', 'gap', 'signal_market')}
    rng = np.random.default_rng(SEED)
    rows, yearly = [], []
    for name, (tr, pc, counts, mode) in {**runs, **controls}.items():
        for era, (lo, hi) in ERAS.items():
            t, p = era_slice(tr, pc, pd.Timestamp(lo), pd.Timestamp(hi))
            for extra in STRESS:
                rows.append({'variant': name, 'era': era, 'stress': extra, **metrics(t, p, extra, rng)})
            if 'reason' in t:
                rows[-3].update({f'exit_{k}': v for k, v in t.reason.value_counts().items()})
        net = tr.gross - COST * tr.turns
        for year, g in tr.assign(net=net, gr=tr.gross / tr.risk_dollars).groupby(tr.entry_time.dt.year):
            yearly.append({'variant': name, 'year': int(year), 'trades': len(g), 'gross_R': g.gr.mean(), 'net_$': g.net.sum()})
        tag = name.replace(' ', '_').replace('-', '').replace(',', '')
        tr.to_csv(STUDY / f'trades_{tag}.csv', index=False)
        pc.to_csv(STUDY / f'pieces_{tag}.csv', index=False)
    rtl = runs['W1 flatten'][0]
    gains = []
    for name, (ctl, *_rest) in controls.items():
        for era, (lo, hi) in ERAS.items():
            a = rtl[(rtl.entry_time >= lo) & (rtl.entry_time < hi)]
            b = ctl[(ctl.entry_time >= lo) & (ctl.entry_time < hi)]
            row = {'control': name, 'era': era, 'rtl_trades': len(a), 'control_trades': len(b)}
            for kind, f in (('gross', lambda d: d.gross / d.risk_dollars), ('net', lambda d: (d.gross - COST * d.turns) / d.risk_dollars)):
                g, glo, ghi = gain(f(a).to_numpy(), f(b).to_numpy(), rng)
                row.update({f'{kind}_gain_R': g, f'{kind}_lo': glo, f'{kind}_hi': ghi,
                            f'rtl_{kind}_R': f(a).mean(), f'control_{kind}_R': f(b).mean()})
            gains.append(row)
    y = pd.DataFrame(yearly)
    p = y.pivot(index='year', columns='variant', values='gross_R')
    beat = {name: int((p['W1 flatten'] > p[name]).sum()) for name in controls}
    always = session_long(bars, cutoffs, PV)
    pieces = runs['W1 flatten'][1]
    is_first = np.r_[True, bars['date'][1:] != bars['date'][:-1]]
    opens = pd.Series(e.stamp_array(bars['day'][is_first], bars['minute'][is_first]),
                      index=pd.to_datetime(pd.Series(bars['date'][is_first]).astype(str)).to_numpy())
    from_open = pieces.entry_time.to_numpy() == opens.reindex(pieces.entry_time.dt.normalize()).to_numpy()
    patterns = {'from the open': pieces.entry_time[from_open].dt.normalize().unique(),
                'every held session': pieces.exit_time.dt.normalize().unique()}
    timing = {}
    for label, held in patterns.items():
        for era, (lo, hi) in list(ERAS.items())[1:]:
            s = always[(always.index >= lo) & (always.index < hi)]
            mask, pnl = s.index.isin(held).astype(float), s.to_numpy()
            ks, totals, dds = shifts(mask, pnl)
            fft = np.real(np.fft.ifft(np.conj(np.fft.fft(mask)) * np.fft.fft(pnl)))
            own = (mask * pnl).sum()
            assert np.allclose(fft[ks], totals) and np.isclose(fft[0], own)
            timing[f'{label} {era}'] = {
                'pattern': label, 'era': era, 'in_market': int(mask.sum()), 'shifts': len(ks), 'rtl_pattern_$': float(own),
                'shift_p50_$': float(np.median(totals)), 'shift_p95_$': float(np.quantile(totals, .95)),
                'share_shifts_below_rtl': float((totals < own).mean()), 'rtl_pattern_DD': max_dd(mask * pnl),
                'shift_median_DD': float(np.median(dds)), 'share_shifts_with_higher_DD': float((dds > max_dd(mask * pnl)).mean()),
                'always_long_$': float(pnl.sum()), 'always_long_DD': max_dd(pnl)}
    pair = paired(runs['W1 flatten'], runs['W1 hold'])
    pair.to_csv(STUDY / 'paired_flat_hold.csv', index=False)
    sessions = pd.DatetimeIndex(pd.to_datetime(pd.Series(np.unique(bars['date'][bars['date'] <= LAST_DATE])).astype(str)))
    more = extras(runs, pair, sessions, always)
    holes = {name: int(pc[pd.to_datetime(pc.exit_time).dt.strftime('%Y%m%d').astype(int).isin(DATA_HOLES)].shape[0])
             for name, (tr, pc, counts, mode) in runs.items() if mode == 'flat'}
    nq_gain = pd.read_csv(NQ_CONTROL / 'control_gains.csv')
    summary = pd.DataFrame(rows)
    summary.to_csv(STUDY / 'summary.csv', index=False)
    y.to_csv(STUDY / 'yearly.csv', index=False)
    pd.DataFrame(gains).to_csv(STUDY / 'control_gains.csv', index=False)
    counts = {name: r[2] for name, r in {**runs, **controls}.items() if r[3] != 'm30'}
    out = {'protocol_sha256': sha(PROTOCOL), 'point_value': PV, 'roll_switches': len(switches), 'm30_check': m30check,
           'w1_check': w1check, 'nq_weekly_unchanged': True, 'counters': counts, 'pieces_on_data_hole_days': holes,
           'years_rtl_gross_R_higher_of_17': beat, 'random_timing': timing, 'flatten_effect': more['flatten_effect'],
           'exposure': more['exposure'], 'with_es_m30': more['with_m30'], 'always_long': more['always_long'],
           'signal_range_ticks_median': resolution(runs),
           'nq_weekly_gain_over_plain_long': nq_gain.loc[nq_gain.control == 'Plain long', ['era', 'gross_gain_R', 'gross_lo', 'gross_hi']].to_dict('records')}
    (STUDY / 'results.json').write_text(json.dumps(out, indent=2, default=float), encoding='utf-8')
    pd.set_option('display.width', 250)
    cols = ['variant', 'era', 'trades', 'pieces_per_trade', 'win%', 'gross_R', 'net_R', 'net_R_lo', 'net_R_hi',
            'net_$', 'PF_net', 'maxDD_$', 'worst_day_$', 'med_risk_$']
    print(summary.loc[summary.stress == 0, cols].to_string(index=False, float_format=lambda x: f'{x:,.3f}'))
    print(pd.DataFrame(gains).to_string(index=False, float_format=lambda x: f'{x:+.3f}'))
    print(json.dumps({k: out[k] for k in ('years_rtl_gross_R_higher_of_17', 'random_timing', 'flatten_effect', 'exposure',
                                          'with_es_m30', 'always_long', 'signal_range_ticks_median', 'pieces_on_data_hole_days',
                                          'counters')}, indent=1, default=float))


if __name__ == '__main__':
    main()
