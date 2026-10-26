"""Weekly RTL controls (2026-10-27): plain long, red week with a market entry, random timing.

Protocol: docs/baseline/rtl-weekly-flatten/CONTROL_PROTOCOL.md. Uses the weekly-flatten study's
minute cache and RTL ledger; outputs in Reports/rtl_weekly_control_20261027/.
Usage: python analyze_rtl_weekly_control.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import rtl_weekly_engine as e
from analyze_instrument_baseline import load, max_dd
from analyze_rtl_weekly_flatten import COST, ERAS, LAST_DATE, era_slice, metrics, session_long, sha
from analyze_rtl_weekly_flatten import STUDY as FLAT_STUDY

STUDY = e.ROOT / 'Reports/rtl_weekly_control_20261027'
PROTOCOL = e.ROOT / 'docs/baseline/rtl-weekly-flatten/CONTROL_PROTOCOL.md'
LEDGER = STUDY / 'runband_wkctrl_20261027_w1_plain_hold_1.00.csv'
SPREAD = 0.25       # MT5 fills a market buy one tick above the open on this symbol
MIN_SHIFT = 60
SEED = 20261028
DRAWS = 10000
CONTROLS = {'Plain long': 'plain', 'Red week, market entry': 'signal_market'}


def minute_floor(s):
    return pd.to_datetime(s).dt.floor('min')


def validate(bars):
    """The plain-long code path against the MT5 W1 run of SignalMode 3 (held, raw, MT5 fills)."""
    ones = np.ones(len(bars['o']))
    tr, _, _ = e.simulate_weekly(bars, bars['o'], bars['h'], bars['l'], bars['c'], ones, mode='hold',
                                 fills='mt5', control='plain', spread=SPREAD)
    mt = load(LEDGER)
    stats = pd.read_csv(STUDY / 'runband_wkctrl_20261027_w1_plain_hold_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
    assert len(mt) == int(stats.trades) and abs(mt.trade_profit.sum() - stats.net_profit) < 1e-6
    start = mt.entry.min()
    # MT5's first trade opens on its tester start tick (mid-week); the simulator, which starts in 2010,
    # opened the same trade at that week's first open and has it running.
    twin = tr[(tr.entry_time < start) & (tr.exit_time > start)]
    assert len(twin) == 1 and abs(twin.gross.iloc[0] - mt.trade_profit.iloc[0]) < 1e-6
    later = tr[tr.entry_time > start]
    k = later.assign(ent=minute_floor(later.entry_time)).merge(mt.iloc[1:].assign(ent=mt.entry.iloc[1:].dt.floor('min')), on='ent')
    assert len(k) == len(later) == len(mt) - 1
    assert (minute_floor(k.exit_time_x) == k.exit.dt.floor('min')).all()
    assert np.allclose(k.gross, k.trade_profit, atol=1e-6)
    assert np.allclose(k.fill - k.sl, k.candle_range)
    return {'mt5_trades': len(mt), 'matched_exact': len(k), 'first_trade': 'tester start tick; twin opened one session earlier, same profit',
            'mt5_first_entry': str(start), 'mt5_net': float(stats.net_profit)}


def run(bars, cutoffs, factor, control):
    o, h, l, c = (bars[x] * factor for x in 'ohlc')
    tr, pc, counts = e.simulate_weekly(bars, o, h, l, c, factor, mode='flat', fills='gap', cutoffs=cutoffs,
                                       last_date=LAST_DATE, control=control, spread=SPREAD if control else 0.0)
    tr['trade'] = np.arange(len(tr))
    tr['turns'] = tr.pieces
    pc['turns'] = 1
    return tr, pc, counts


def gain(a, b, rng):
    """Mean of a minus mean of b, with independent trade bootstraps."""
    da = a[rng.integers(len(a), size=(DRAWS, len(a)))].mean(axis=1)
    db = b[rng.integers(len(b), size=(DRAWS, len(b)))].mean(axis=1)
    lo, hi = np.quantile(da - db, [.025, .975])
    return a.mean() - b.mean(), lo, hi


def shifts(mask, pnl):
    """P&L and max DD of the mask circularly shifted by every k with MIN_SHIFT <= k <= n - MIN_SHIFT."""
    n = len(mask)
    ks = np.arange(MIN_SHIFT, n - MIN_SHIFT + 1)
    totals, dds = np.empty(len(ks)), np.empty(len(ks))
    for j, k in enumerate(ks):
        x = np.roll(mask, k) * pnl
        totals[j], dds[j] = x.sum(), max_dd(x)
    return ks, totals, dds


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    bars = e.load_minutes(FLAT_STUDY / 'minutes.npz')
    cutoffs = e.load_cutoffs()
    check = validate(bars)
    print('Validation passed:', json.dumps(check), flush=True)
    switches = e.roll_switches(LAST_DATE)
    factor = e.roll_factor(bars, switches)
    runs = {'RTL (buy stop)': run(bars, cutoffs, factor, None)}
    saved = pd.read_csv(FLAT_STUDY / 'trades_W1_flatten.csv', parse_dates=['entry_time', 'exit_time'])
    assert np.allclose(runs['RTL (buy stop)'][0].gross, saved.gross) and (runs['RTL (buy stop)'][0].entry_time == saved.entry_time).all()
    for name, control in CONTROLS.items():
        runs[name] = run(bars, cutoffs, factor, control)
    rng = np.random.default_rng(SEED)
    rows, gains, yearly = [], [], []
    for name, (tr, pc, counts) in runs.items():
        for era, (lo, hi) in ERAS.items():
            t, p = era_slice(tr, pc, pd.Timestamp(lo), pd.Timestamp(hi))
            rows.append({'variant': name, 'era': era, **metrics(t, p, 0.0, rng),
                         **{f'exit_{k}': v for k, v in t.reason.value_counts().items()}})
        net = tr.gross - COST * tr.turns
        for year, g in tr.assign(gross_r=tr.gross / tr.risk_dollars, net=net).groupby(tr.entry_time.dt.year):
            yearly.append({'variant': name, 'year': int(year), 'trades': len(g), 'gross_R': g.gross_r.mean(), 'net_$': g.net.sum()})
        tr.to_csv(STUDY / f"trades_{name.split(' (')[0].replace(' ', '_').replace(',', '')}.csv", index=False)
        pc.to_csv(STUDY / f"pieces_{name.split(' (')[0].replace(' ', '_').replace(',', '')}.csv", index=False)
    rtl = runs['RTL (buy stop)'][0]
    for name in CONTROLS:
        ctl = runs[name][0]
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
    beat = {}
    for name in CONTROLS:
        p = y[y.year.between(2010, 2026)].pivot(index='year', columns='variant', values='gross_R')
        beat[name] = {'years_rtl_higher': int((p['RTL (buy stop)'] > p[name]).sum()), 'years': int(p[name].notna().sum())}
    # random timing of RTL's own in-market sessions. 'as fixed': every session with a piece (protocol).
    # 'from the open' (post-hoc correction): only sessions RTL was long from the first bar. A fill day
    # is in the pattern because price broke out during it, so scoring it from the open looks ahead.
    always = session_long(bars, cutoffs)
    pieces = runs['RTL (buy stop)'][1]
    day = pieces.entry_time.dt.normalize()
    is_first = np.r_[True, bars['date'][1:] != bars['date'][:-1]]
    opens = pd.Series(e.stamp_array(bars['day'][is_first], bars['minute'][is_first]),
                      index=pd.to_datetime(pd.Series(bars['date'][is_first]).astype(str)).to_numpy())
    from_open = pieces.entry_time.to_numpy() == opens.reindex(day).to_numpy()
    patterns = {'as fixed': pieces.exit_time.dt.normalize().unique(),
                'from the open': pieces.entry_time[from_open].dt.normalize().unique()}
    timing = {}
    for label, held in patterns.items():
        for era, (lo, hi) in list(ERAS.items())[1:]:
            s = always[(always.index >= lo) & (always.index < hi)]
            mask = s.index.isin(held).astype(float)
            pnl = s.to_numpy()
            ks, totals, dds = shifts(mask, pnl)
            # independent checks of every shift total: FFT circular correlation and direct indexing
            fft = np.real(np.fft.ifft(np.conj(np.fft.fft(mask)) * np.fft.fft(pnl)))
            own = (mask * pnl).sum()
            idx = (np.arange(len(pnl))[None, :] - ks[:, None]) % len(pnl)
            assert np.allclose(totals, (mask[idx] * pnl[None, :]).sum(axis=1))
            assert np.allclose(fft[ks], totals) and np.isclose(fft[0], own)
            actual = pieces[(pieces.exit_time >= lo) & (pieces.exit_time < hi)]
            fill_days = s.index.isin(pieces.entry_time[~from_open].dt.normalize().unique())
            timing[f'{label} {era}'] = {
                'pattern': label, 'era': era, 'sessions': len(s), 'in_market': int(mask.sum()), 'shifts': len(ks),
                'rtl_pattern_$': float(own), 'rtl_pattern_DD': max_dd(mask * pnl),
                'shift_mean_$': float(totals.mean()), 'shift_p05_$': float(np.quantile(totals, .05)),
                'shift_p50_$': float(np.median(totals)), 'shift_p95_$': float(np.quantile(totals, .95)),
                'share_shifts_below_rtl': float((totals < own).mean()),
                'shift_median_DD': float(np.median(dds)), 'share_shifts_with_lower_DD': float((dds < max_dd(mask * pnl)).mean()),
                'fill_days': int(fill_days.sum()), 'fill_days_full_session_$': float(pnl[fill_days].sum()),
                'rtl_actual_$': float((actual.gross - COST).sum()), 'always_long_$': float(pnl.sum()),
                'always_long_DD': max_dd(pnl)}
    summary = pd.DataFrame(rows)
    summary.to_csv(STUDY / 'control_summary.csv', index=False)
    pd.DataFrame(gains).to_csv(STUDY / 'control_gains.csv', index=False)
    y.to_csv(STUDY / 'control_yearly.csv', index=False)
    counts = {name: run_[2] for name, run_ in runs.items()}
    out = {'protocol_sha256': sha(PROTOCOL), 'spread': SPREAD, 'min_shift': MIN_SHIFT, 'mt5_check': check,
           'rtl_reproduces_flatten_ledger': True, 'counters': counts, 'years_rtl_gross_R_higher': beat,
           'random_timing': timing}
    (STUDY / 'control_results.json').write_text(json.dumps(out, indent=2, default=float), encoding='utf-8')
    pd.set_option('display.width', 250)
    cols = ['variant', 'era', 'trades', 'pieces_per_trade', 'win%', 'gross_R', 'net_R', 'net_R_lo', 'net_R_hi',
            'net_$', 'PF_net', 'maxDD_$', 'worst_day_$', 'med_risk_$']
    print(summary[cols].to_string(index=False, float_format=lambda x: f'{x:,.3f}'))
    print(pd.DataFrame(gains).to_string(index=False, float_format=lambda x: f'{x:+.3f}'))
    print(json.dumps({'beat': beat, 'timing': timing, 'counts': counts}, indent=1, default=float))


if __name__ == '__main__':
    main()
