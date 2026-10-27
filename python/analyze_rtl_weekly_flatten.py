"""RTL on weekly candles with a session flatten (2026-10-27): validate the simulator, run the variants.

Protocol: docs/baseline/rtl-weekly-flatten/PROTOCOL.md. Outputs in Reports/rtl_weekly_flatten_20261027/.
Usage: python analyze_rtl_weekly_flatten.py
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

import rtl_weekly_engine as e
from analyze_instrument_baseline import load, max_dd

STUDY = e.ROOT / 'Reports/rtl_weekly_flatten_20261027'
PROTOCOL = e.ROOT / 'docs/baseline/rtl-weekly-flatten/PROTOCOL.md'
M30_TRADES = e.ROOT / 'Reports/rtl_market_regimes_20261023/trades.csv'
W1_LEDGER = STUDY / 'runband_wkflat_20261027_w1_hold_1.00.csv'
LAST_DATE = 20260930
COST = 1.05
STRESS = (0.0, 1.0, 2.0)
ERAS = {'2010-15 reference': ('2010-01-01', '2016-01-01'), '2016-19': ('2016-01-01', '2020-01-01'),
        '2020-26': ('2020-01-01', '2026-10-01')}
VARIANTS = {'W1 flatten': ('flat', 'adjusted', 'gap'), 'W1 flatten raw': ('flat', 'raw', 'gap'),
            'W1 hold': ('hold', 'adjusted', 'gap'), 'W1 hold MT5-style': ('hold', 'raw', 'mt5')}
SEED = 20261027
DRAWS = 10000


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def minute_floor(s):
    return pd.to_datetime(s).dt.floor('min')


def validate(bars, cutoffs):
    """Protocol step 1 (M30 EA vs the MT5 ledger) and step 2 (W1 hold vs the MT5 W1 run)."""
    sim, rejected = e.simulate_m30_ea(bars, cutoffs=cutoffs)
    mt = pd.read_csv(M30_TRADES, parse_dates=['submitted', 'entry_time', 'exit_time'])
    j = mt.assign(ent=minute_floor(mt.entry_time)).merge(sim.assign(ent=minute_floor(sim.entry_time)),
                                                         on='ent', how='left', suffixes=('_m', '_s'))
    assert j.requested.notna().all(), 'MT5 M30 trade missing from the simulation'
    extra = sim.loc[~minute_floor(sim.entry_time).isin(minute_floor(mt.entry_time))]
    assert (extra.entry_time < mt.entry_time.min()).all(), 'unmatched simulated M30 trades after MT5 start'
    m30 = {'mt5_trades': len(mt), 'matched': int(len(j)), 'extra_before_mt5_start': len(extra),
           'requested_diff': int((j.requested_price != j.requested).sum()),
           'sl_diff': int((j.original_sl != j.sl).sum()), 'fill_diff': int((j.fill_price != j.fill).sum()),
           'exit_price_diff': int((j.exit_price_m != j.exit_price_s).sum()),
           'exit_minute_diff': int((minute_floor(j.exit_time_m) != minute_floor(j.exit_time_s)).sum()),
           'rejected_orders': rejected}
    assert m30['requested_diff'] == m30['sl_diff'] == m30['fill_diff'] == m30['exit_price_diff'] == 0
    assert m30['exit_minute_diff'] == 0
    ones = np.ones(len(bars['o']))
    tr, _, _ = e.simulate_weekly(bars, bars['o'], bars['h'], bars['l'], bars['c'], ones, mode='hold', fills='mt5')
    w1 = load(W1_LEDGER)
    stats = pd.read_csv(STUDY / 'runband_wkflat_20261027_w1_hold_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
    assert len(w1) == int(stats.trades) and abs(w1.trade_profit.sum() - stats.net_profit) < 1e-6
    k = tr.assign(ent=minute_floor(tr.entry_time)).merge(w1.assign(ent=w1.entry.dt.floor('min')), on='ent')
    later = tr[tr.entry_time >= w1.entry.min()]
    assert len(k) == len(w1) == len(later)
    assert (minute_floor(k.exit_time_x) == k.exit.dt.floor('min')).all()
    assert np.allclose(k.gross, k.trade_profit, atol=1e-6)
    assert np.allclose(k.requested - k.sl, k.candle_range)
    w1check = {'mt5_trades': len(w1), 'matched_exact': len(k), 'mt5_first_entry': str(w1.entry.min()),
               'simulated_before_mt5_start': int(len(tr) - len(later)), 'mt5_gross': float(w1.trade_profit.sum())}
    return m30, w1check


def run_variants(bars, cutoffs, factor, contracts):
    out = {}
    for name, (mode, basis, fills) in VARIANTS.items():
        f = factor if basis == 'adjusted' else np.ones(len(factor))
        tr, pc, counts = e.simulate_weekly(bars, bars['o'] * f, bars['h'] * f, bars['l'] * f, bars['c'] * f, f,
                                           mode=mode, fills=fills, cutoffs=cutoffs, last_date=LAST_DATE,
                                           contracts=contracts)
        tr['trade'] = np.arange(len(tr))
        # Round turns: every flat piece; held: one per trade, plus one per roll on adjusted prices.
        tr['turns'] = tr.pieces if mode == 'flat' else 1 + (tr.rolls if basis == 'adjusted' else 0)
        pc['turns'] = 1 if mode == 'flat' else 0
        if mode == 'hold':
            last = pc.groupby('trade').tail(1).index
            pc.loc[last, 'turns'] = tr.turns.to_numpy()[pc.loc[last, 'trade'].to_numpy()]
        out[name] = (tr, pc, counts, mode)
    return out


def m30_baseline():
    mt = pd.read_csv(M30_TRADES, parse_dates=['submitted', 'entry_time', 'exit_time'])
    tr = pd.DataFrame({'trade': np.arange(len(mt)), 'entry_time': mt.entry_time, 'exit_time': mt.exit_time,
                       'gross': mt.trade_profit, 'risk_dollars': mt.fill_risk_dollars, 'turns': 1, 'pieces': 1})
    pc = pd.DataFrame({'trade': tr.trade, 'exit_time': tr.exit_time, 'gross': tr.gross, 'turns': 1})
    return tr, pc


def metrics(tr, pc, extra, rng):
    """Per-trade and daily-equity figures at one contract; extra = added cost per round turn."""
    net = tr.gross - (COST + extra) * tr.turns
    risk = tr.risk_dollars
    r = net / risk
    piece_net = pc.gross - (COST + extra) * pc.turns
    piece_r = piece_net / risk.to_numpy()[pc.trade.to_numpy()]
    day = pc.exit_time.dt.normalize()
    daily, daily_r = piece_net.groupby(day).sum(), piece_r.groupby(day).sum()
    win, loss = net[net > 0].sum(), -net[net < 0].sum()
    boot = r.to_numpy()[rng.integers(len(r), size=(DRAWS, len(r)))].mean(axis=1) if len(r) else np.array([np.nan])
    return {'trades': len(tr), 'pieces': int(tr.pieces.sum()), 'pieces_per_trade': tr.pieces.mean(),
            'win%': 100 * (net > 0).mean(), 'gross_R': (tr.gross / risk).mean(), 'net_R': r.mean(),
            'net_R_lo': np.quantile(boot, .025), 'net_R_hi': np.quantile(boot, .975), 'net_R_sum': r.sum(),
            'net_$': net.sum(), 'PF_net': win / loss if loss else np.inf, 'maxDD_$': max_dd(daily.to_numpy()),
            'maxDD_R': max_dd(daily_r.to_numpy()), 'worst_day_$': daily.min(), 'med_risk_$': risk.median(),
            'days_with_pnl': len(daily)}


def era_slice(tr, pc, lo, hi):
    keep = tr.trade[(tr.entry_time >= lo) & (tr.entry_time < hi)]
    t = tr[tr.trade.isin(keep)].copy()
    p = pc[pc.trade.isin(keep)].copy()
    # positional risk lookup inside metrics()
    remap = pd.Series(np.arange(len(t)), index=t.trade.to_numpy())
    t['trade'] = np.arange(len(t))
    p['trade'] = remap[p.trade].to_numpy()
    return t.reset_index(drop=True), p.reset_index(drop=True)


def paired(flat, hold):
    """Same signal week and level: how flattening changes each trade (R at the hold trade's risk)."""
    f, h = flat[0], hold[0]
    fnet = f.gross - COST * f.turns
    hnet = h.gross - COST * h.turns
    a = f.assign(net=fnet)[['signal_week', 'requested', 'entry_time', 'reason', 'net', 'risk_dollars', 'pieces', 'flat_fill']]
    b = h.assign(net=hnet)[['signal_week', 'requested', 'entry_time', 'reason', 'net', 'risk_dollars', 'pieces']]
    j = a.merge(b, on=['signal_week', 'requested'], how='outer', suffixes=('_flat', '_hold'), indicator=True)
    return j


def era_of(times):
    return pd.Series(np.select([times >= pd.Timestamp(lo) for _, (lo, _) in reversed(list(ERAS.items()))],
                               list(reversed(list(ERAS))), 'none'), index=times.index)


def session_long(bars, cutoffs, point_value=e.POINT_VALUE):
    """Benchmark: one contract long from every session's first bar to its flatten, net of $1.05."""
    date, minute, o, c = bars['date'], bars['minute'], bars['o'], bars['c']
    keep = date <= LAST_DATE
    d = pd.DataFrame({'date': date[keep], 'minute': minute[keep], 'o': o[keep], 'c': c[keep]})
    d['cut'] = d.minute >= d.date.map(lambda x: cutoffs.get(x, e.CUTOFF))
    first = d.groupby('date').o.first()
    flat = d[d.cut].groupby('date').o.first().reindex(first.index)
    exit_ = flat.fillna(d.groupby('date').c.last())
    pnl = (exit_ - first) * point_value - COST
    pnl.index = pd.to_datetime(pnl.index.astype(str))
    return pnl


def extras(runs, pair, sessions, always_long):
    """Flatten effect split into commission and price, market exposure, and W1 flatten next to M30."""
    flat, hold = runs['W1 flatten'][0], runs['W1 hold'][0]
    b = pair[pair._merge == 'both'].merge(flat[['signal_week', 'requested', 'gross', 'turns']], on=['signal_week', 'requested'])
    b = b.merge(hold[['signal_week', 'requested', 'gross', 'turns']], on=['signal_week', 'requested'], suffixes=('_f', '_h'))
    risk = b.risk_dollars_hold
    b['price_R'] = (b.gross_f - b.gross_h) / risk
    b['commission_R'] = -COST * (b.turns_f - b.turns_h) / risk
    b['era'] = era_of(b.entry_time_hold)
    out = {'flatten_effect': {}, 'exposure': {}, 'with_m30': {}}
    for era, g in b.groupby('era'):
        same = g[g.reason_flat == g.reason_hold]
        out['flatten_effect'][era] = {
            'matched': len(g), 'different_exit': int((g.reason_flat != g.reason_hold).sum()),
            'total_R': float((g.price_R + g.commission_R).mean()), 'price_R': float(g.price_R.mean()),
            'commission_R': float(g.commission_R.mean()),
            'same_exit_total_R': float((same.price_R + same.commission_R).mean()),
            'median_abs_R': float((g.price_R + g.commission_R).abs().median())}
    out['flatten_effect']['unmatched'] = pair.loc[pair._merge != 'both', ['signal_week', '_merge']].astype(str).to_dict('records')
    out['always_long'] = {}
    for era, (lo, hi) in list(ERAS.items())[1:]:
        g = always_long[(always_long.index >= lo) & (always_long.index < hi)]
        out['always_long'][era] = {'sessions': len(g), 'net_$': float(g.sum()), 'maxDD_$': max_dd(g.to_numpy()),
                                   'worst_day_$': float(g.min())}
    m30 = runs['M30 baseline']
    wpc = runs['W1 flatten'][1]
    daily = lambda pc: (pc.gross - COST * pc.turns).groupby(pc.exit_time.dt.normalize()).sum()
    w, m = daily(wpc), daily(m30[1])
    for era, (lo, hi) in list(ERAS.items())[1:]:
        days = sessions[(sessions >= lo) & (sessions < hi)]
        both = pd.DataFrame({'w1': w, 'm30': m}).reindex(days).fillna(0.0)
        out['exposure'][era] = float(both.w1.ne(0).mean())
        out['with_m30'][era] = {'daily_corr': float(both.w1.corr(both.m30)), 'w1_$': float(both.w1.sum()),
                                'm30_$': float(both.m30.sum()), 'together_$': float(both.sum(axis=1).sum()),
                                'w1_DD': max_dd(both.w1.to_numpy()), 'm30_DD': max_dd(both.m30.to_numpy()),
                                'together_DD': max_dd(both.sum(axis=1).to_numpy())}
    return out


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    bars = e.load_minutes(STUDY / 'minutes.npz')
    cutoffs = e.load_cutoffs()
    m30check, w1check = validate(bars, cutoffs)
    print('Validation passed:', json.dumps({'m30': m30check, 'w1': w1check}), flush=True)
    switches = e.roll_switches(LAST_DATE)
    factor = e.roll_factor(bars, switches)
    contracts = e.contract_ids(bars, switches)
    runs = run_variants(bars, cutoffs, factor, contracts)
    runs['M30 baseline'] = (*m30_baseline(), {}, 'm30')
    rng = np.random.default_rng(SEED)
    rows, yearly = [], []
    for name, (tr, pc, counts, mode) in runs.items():
        for era, (lo, hi) in ERAS.items():
            t, p = era_slice(tr, pc, pd.Timestamp(lo), pd.Timestamp(hi))
            for extra in STRESS:
                rows.append({'variant': name, 'era': era, 'stress': extra, **metrics(t, p, extra, rng)})
            reasons = t.reason.value_counts().to_dict() if 'reason' in t else {}
            rows[-3].update({f'exit_{k}': v for k, v in reasons.items()})
            if 'flat_fill' in t:
                rows[-3]['flat_fills'] = int(t.flat_fill.sum())
        net = tr.gross - COST * tr.turns
        for year, g in tr.assign(net=net, r=net / tr.risk_dollars).groupby(tr.entry_time.dt.year):
            yearly.append({'variant': name, 'year': int(year), 'trades': len(g), 'net_$': g.net.sum(), 'net_R_sum': g.r.sum()})
        tr.to_csv(STUDY / f"trades_{name.replace(' ', '_').replace('-', '')}.csv", index=False)
        pc.to_csv(STUDY / f"pieces_{name.replace(' ', '_').replace('-', '')}.csv", index=False)
    summary = pd.DataFrame(rows)
    summary.to_csv(STUDY / 'summary.csv', index=False)
    pd.DataFrame(yearly).to_csv(STUDY / 'yearly.csv', index=False)
    pair = paired(runs['W1 flatten'], runs['W1 hold'])
    pair.to_csv(STUDY / 'paired_flat_hold.csv', index=False)
    counts = {name: {k: v for k, v in run[2].items()} for name, run in runs.items() if run[3] != 'm30'}
    sessions = pd.to_datetime(pd.Series(np.unique(bars['date'][bars['date'] <= LAST_DATE])).astype(str))
    more = extras(runs, pair, pd.DatetimeIndex(sessions), session_long(bars, cutoffs))
    (STUDY / 'extras.json').write_text(json.dumps(more, indent=2), encoding='utf-8')
    audit = {'protocol_sha256': sha(PROTOCOL), 'minutes_csv': str(e.MINUTES), 'roll_switches': len(switches),
             'last_date': LAST_DATE, 'm30_check': m30check, 'w1_check': w1check, 'counters': counts}
    (STUDY / 'audit.json').write_text(json.dumps(audit, indent=2, default=str), encoding='utf-8')
    pd.set_option('display.width', 250)
    cols = ['variant', 'era', 'trades', 'pieces_per_trade', 'win%', 'gross_R', 'net_R', 'net_R_lo', 'net_R_hi',
            'net_R_sum', 'net_$', 'PF_net', 'maxDD_$', 'maxDD_R', 'worst_day_$', 'med_risk_$']
    print(summary.loc[summary.stress == 0, cols].to_string(index=False, float_format=lambda x: f'{x:,.3f}'))
    print(json.dumps(counts, indent=1))


if __name__ == '__main__':
    main()
