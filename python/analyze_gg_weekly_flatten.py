"""GG on weekly candles, flattened every session, with the plain-long and random-timing controls (2026-10-27).

GG = RTL with a green signal week. Protocol: docs/baseline/gg-weekly-flatten/PROTOCOL.md.
Uses the RTL weekly studies' minute cache and helpers; outputs in Reports/gg_weekly_flatten_20261027/.
Usage: python analyze_gg_weekly_flatten.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import rtl_weekly_engine as e
from analyze_instrument_baseline import load, max_dd
from analyze_rtl_weekly_control import SPREAD, gain, shifts
from analyze_rtl_weekly_control import STUDY as CONTROL_STUDY
from analyze_rtl_weekly_flatten import COST, ERAS, LAST_DATE, STRESS, VARIANTS, era_slice, extras, metrics, paired, session_long, sha
from analyze_rtl_weekly_flatten import STUDY as FLAT_STUDY

STUDY = e.ROOT / 'Reports/gg_weekly_flatten_20261027'
PROTOCOL = e.ROOT / 'docs/baseline/gg-weekly-flatten/PROTOCOL.md'
GG_M30 = e.ROOT / 'Reports/timeframe_baseline_20261015/runband_tf_20261015_gg_m30_rr1p0_1.00.csv'
W1_LEDGER = STUDY / 'runband_ggwk_20261027_w1_hold_1.00.csv'
SEED = 20261029


def minute_floor(s):
    return pd.to_datetime(s).dt.floor('min')


def validate(bars, cutoffs, factor):
    """GG M30 against its MT5 ledger, GG W1 hold against the fresh MT5 run, RTL unchanged."""
    sim, rejected = e.simulate_m30_ea(bars, cutoffs=cutoffs, signal='green')
    mt = load(GG_M30)
    j = mt.assign(ent=mt.entry.dt.floor('min')).merge(sim.assign(ent=minute_floor(sim.entry_time)), on='ent', how='left',
                                                       suffixes=('_m', '_s'))
    assert j.requested.notna().all(), 'MT5 GG M30 trade missing from the simulation'
    gross = (j.exit_price - j.fill) * e.POINT_VALUE
    extra = sim.loc[~minute_floor(sim.entry_time).isin(mt.entry.dt.floor('min'))]
    m30 = {'mt5_trades': len(mt), 'matched': len(j), 'extra_before_mt5_start': len(extra),
           'extra_after_mt5_start': int((extra.entry_time >= mt.entry.min()).sum()),
           'profit_diff': int((abs(gross - j.trade_profit) > 1e-6).sum()),
           'range_diff': int((abs(j.requested - j.sl - j.candle_range) > 1e-6).sum()),
           'exit_minute_diff': int((minute_floor(j.exit_time_s) != j.exit.dt.floor('min')).sum()),
           'rejected_orders': rejected}
    assert m30['extra_after_mt5_start'] == 0 and m30['profit_diff'] == 0 and m30['range_diff'] == 0
    assert m30['exit_minute_diff'] <= 5
    ones = np.ones(len(bars['o']))
    tr, _, _ = e.simulate_weekly(bars, bars['o'], bars['h'], bars['l'], bars['c'], ones, mode='hold',
                                 fills='mt5', signal='green')
    w1 = load(W1_LEDGER)
    stats = pd.read_csv(STUDY / 'runband_ggwk_20261027_w1_hold_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
    assert len(w1) == int(stats.trades) and abs(w1.trade_profit.sum() - stats.net_profit) < 1e-6
    k = tr.assign(ent=minute_floor(tr.entry_time)).merge(w1.assign(ent=w1.entry.dt.floor('min')), on='ent')
    later = tr[tr.entry_time >= w1.entry.min()]
    assert len(k) == len(w1) == len(later)
    assert (minute_floor(k.exit_time_x) == k.exit.dt.floor('min')).all()
    assert np.allclose(k.gross, k.trade_profit, atol=1e-6) and np.allclose(k.requested - k.sl, k.candle_range)
    w1check = {'mt5_trades': len(w1), 'matched_exact': len(k), 'mt5_first_entry': str(w1.entry.min()),
               'simulated_before_mt5_start': int(len(tr) - len(later)), 'mt5_gross': float(w1.trade_profit.sum())}
    rtl, _, _ = e.simulate_weekly(bars, *(bars[x] * factor for x in 'ohlc'), factor, mode='flat', cutoffs=cutoffs,
                                  last_date=LAST_DATE)
    saved = pd.read_csv(FLAT_STUDY / 'trades_W1_flatten.csv', parse_dates=['entry_time'])
    assert np.allclose(rtl.gross, saved.gross) and (rtl.entry_time == saved.entry_time).all()
    return m30, w1check


def weekly(bars, cutoffs, factor, contracts, mode, basis, fills, control=None):
    f = factor if basis == 'adjusted' else np.ones(len(factor))
    tr, pc, counts = e.simulate_weekly(bars, *(bars[x] * f for x in 'ohlc'), f, mode=mode, fills=fills,
                                       cutoffs=cutoffs, last_date=LAST_DATE, contracts=contracts, signal='green',
                                       control=control, spread=SPREAD if control else 0.0)
    tr['trade'] = np.arange(len(tr))
    tr['turns'] = tr.pieces if mode == 'flat' else 1 + (tr.rolls if basis == 'adjusted' else 0)
    pc['turns'] = 1 if mode == 'flat' else 0
    if mode == 'hold':
        last = pc.groupby('trade').tail(1).index
        pc.loc[last, 'turns'] = tr.turns.to_numpy()[pc.loc[last, 'trade'].to_numpy()]
    return tr, pc, counts, mode


def m30_baseline():
    mt = load(GG_M30)
    tr = pd.DataFrame({'trade': np.arange(len(mt)), 'entry_time': mt.entry, 'exit_time': mt.exit,
                       'gross': mt.trade_profit, 'risk_dollars': mt.candle_range * e.POINT_VALUE, 'turns': 1, 'pieces': 1})
    pc = pd.DataFrame({'trade': tr.trade, 'exit_time': tr.exit_time, 'gross': tr.gross, 'turns': 1})
    return tr, pc, {}, 'm30'


def daily(pc):
    return (pc.gross - COST * pc.turns).groupby(pd.to_datetime(pc.exit_time).dt.normalize()).sum()


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    bars = e.load_minutes(FLAT_STUDY / 'minutes.npz')
    cutoffs = e.load_cutoffs()
    switches = e.roll_switches(LAST_DATE)
    factor = e.roll_factor(bars, switches)
    contracts = e.contract_ids(bars, switches)
    m30check, w1check = validate(bars, cutoffs, factor)
    print('Validation passed:', json.dumps({'m30': m30check, 'w1': w1check}), flush=True)
    runs = {name: weekly(bars, cutoffs, factor, contracts, *spec) for name, spec in VARIANTS.items()}
    runs['M30 baseline'] = m30_baseline()
    plain = weekly(bars, cutoffs, factor, contracts, 'flat', 'adjusted', 'gap', 'plain')
    saved_plain = pd.read_csv(CONTROL_STUDY / 'trades_Plain_long.csv')
    assert np.allclose(plain[0].gross, saved_plain.gross)      # the plain long does not depend on colour
    controls = {'Plain long': plain,
                'Green week, market entry': weekly(bars, cutoffs, factor, contracts, 'flat', 'adjusted', 'gap', 'signal_market')}
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
        for year, g in tr.assign(net=net, r=net / tr.risk_dollars, gr=tr.gross / tr.risk_dollars).groupby(tr.entry_time.dt.year):
            yearly.append({'variant': name, 'year': int(year), 'trades': len(g), 'gross_R': g.gr.mean(), 'net_$': g.net.sum()})
        tag = name.replace(' ', '_').replace('-', '').replace(',', '')
        tr.to_csv(STUDY / f'trades_{tag}.csv', index=False)
        pc.to_csv(STUDY / f'pieces_{tag}.csv', index=False)
    gg = runs['W1 flatten'][0]
    gains = []
    for name, (ctl, *_rest) in controls.items():
        for era, (lo, hi) in ERAS.items():
            a = gg[(gg.entry_time >= lo) & (gg.entry_time < hi)]
            b = ctl[(ctl.entry_time >= lo) & (ctl.entry_time < hi)]
            row = {'control': name, 'era': era, 'gg_trades': len(a), 'control_trades': len(b)}
            for kind, f in (('gross', lambda d: d.gross / d.risk_dollars), ('net', lambda d: (d.gross - COST * d.turns) / d.risk_dollars)):
                g, glo, ghi = gain(f(a).to_numpy(), f(b).to_numpy(), rng)
                row.update({f'{kind}_gain_R': g, f'{kind}_lo': glo, f'{kind}_hi': ghi,
                            f'gg_{kind}_R': f(a).mean(), f'control_{kind}_R': f(b).mean()})
            gains.append(row)
    y = pd.DataFrame(yearly)
    p = y.pivot(index='year', columns='variant', values='gross_R')
    beat = {name: int((p['W1 flatten'] > p[name]).sum()) for name in controls}
    # random timing of GG's own long sessions: from the open (primary), every held session (comparison)
    always = session_long(bars, cutoffs)
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
                'pattern': label, 'era': era, 'in_market': int(mask.sum()), 'shifts': len(ks), 'gg_pattern_$': float(own),
                'shift_p50_$': float(np.median(totals)), 'shift_p95_$': float(np.quantile(totals, .95)),
                'share_shifts_below_gg': float((totals < own).mean()), 'gg_pattern_DD': max_dd(mask * pnl),
                'shift_median_DD': float(np.median(dds)), 'share_shifts_with_higher_DD': float((dds > max_dd(mask * pnl)).mean())}
    # flattening effect, exposure, next to GG M30; then RTL and GG weekly together
    pair = paired(runs['W1 flatten'], runs['W1 hold'])
    pair.to_csv(STUDY / 'paired_flat_hold.csv', index=False)
    sessions = pd.DatetimeIndex(pd.to_datetime(pd.Series(np.unique(bars['date'][bars['date'] <= LAST_DATE])).astype(str)))
    more = extras(runs, pair, sessions, always)
    rtl_pc = pd.read_csv(FLAT_STUDY / 'pieces_W1_flatten.csv', parse_dates=['exit_time'])
    rtl_pc['turns'] = 1
    together = {}
    for era, (lo, hi) in list(ERAS.items())[1:]:
        days = sessions[(sessions >= lo) & (sessions < hi)]
        d = pd.DataFrame({'rtl': daily(rtl_pc), 'gg': daily(pieces), 'plain': daily(plain[1])}).reindex(days).fillna(0.0)
        both = d.rtl + d.gg
        together[era] = {'daily_corr_rtl_gg': float(d.rtl.corr(d.gg)), 'rtl_$': float(d.rtl.sum()), 'gg_$': float(d.gg.sum()),
                         'together_$': float(both.sum()), 'rtl_DD': max_dd(d.rtl.to_numpy()), 'gg_DD': max_dd(d.gg.to_numpy()),
                         'together_DD': max_dd(both.to_numpy()), 'together_worst_day_$': float(both.min()),
                         'sessions_two_contracts': float(((d.rtl != 0) & (d.gg != 0)).mean()),
                         'plain_$': float(d.plain.sum()), 'plain_DD': max_dd(d.plain.to_numpy())}
    summary = pd.DataFrame(rows)
    summary.to_csv(STUDY / 'summary.csv', index=False)
    y.to_csv(STUDY / 'yearly.csv', index=False)
    pd.DataFrame(gains).to_csv(STUDY / 'control_gains.csv', index=False)
    counts = {name: r[2] for name, r in {**runs, **controls}.items() if r[3] != 'm30'}
    out = {'protocol_sha256': sha(PROTOCOL), 'm30_check': m30check, 'w1_check': w1check, 'rtl_unchanged': True,
           'plain_long_equals_rtl_control_study': True, 'counters': counts, 'years_gg_gross_R_higher_of_17': beat,
           'random_timing': timing, 'flatten_effect': more['flatten_effect'], 'exposure': more['exposure'],
           'with_gg_m30': more['with_m30'], 'rtl_and_gg_together': together}
    (STUDY / 'results.json').write_text(json.dumps(out, indent=2, default=float), encoding='utf-8')
    pd.set_option('display.width', 250)
    cols = ['variant', 'era', 'trades', 'pieces_per_trade', 'win%', 'gross_R', 'net_R', 'net_R_lo', 'net_R_hi',
            'net_$', 'PF_net', 'maxDD_$', 'worst_day_$', 'med_risk_$']
    print(summary.loc[summary.stress == 0, cols].to_string(index=False, float_format=lambda x: f'{x:,.3f}'))
    print(pd.DataFrame(gains).to_string(index=False, float_format=lambda x: f'{x:+.3f}'))
    print(json.dumps({k: out[k] for k in ('years_gg_gross_R_higher_of_17', 'random_timing', 'flatten_effect', 'exposure',
                                          'with_gg_m30', 'rtl_and_gg_together', 'counters')}, indent=1, default=float))


if __name__ == '__main__':
    main()
