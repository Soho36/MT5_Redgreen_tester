"""Mirrored RTL sell limit, only after signals that closed below session VWAP - A20 (2026-11-16).

User follow-up, exploratory. Minute replay only (simulate_fade reproduces the ungated MT5 runs
trade for trade). Labels: the frozen RTL VWAP feature file; a signal is taken only when its
VWAP is known for the current session and close < vwap - a20, the short-VWAP study's rule.
The complement (every other red signal) is replayed as the comparison.
"""
import numpy as np
import pandas as pd

import rtl_weekly_engine as e
import rtl_sell_limit_fade as f

FEATURES = f.ROOT / 'Reports/rtl_gg_exclude16_20261101/rtl_vwap_replay_20261026_features.csv'
FIRST_DAY = pd.Timestamp('2010-06-10')


def slots():
    d = pd.read_csv(FEATURES, sep='\t', float_precision='round_trip')
    slot = d.bar_epoch // 1800
    same = d.session_epoch // 86400 == d.bar_epoch // 86400
    known = d.known.eq(1) & same
    below = known & d.close.lt(d.vwap - d.a20)
    return set(slot[below]), set(slot[~below]), dict(labels=len(d), known=int(known.sum()), far_below=int(below.sum()))


def main():
    bars = e.load_minutes(f.CACHE)
    cutoffs = e.load_cutoffs()
    calendar = pd.DatetimeIndex(np.unique(bars['day']).astype('datetime64[D]'))
    below, rest, counts = slots()
    print(counts)
    rows, annual = [], []
    for exit_name, tp in (('close', False), ('tp', True)):
        for gate, allowed in (('far below VWAP only', below), ('all other signals', rest), ('no gate', None)):
            trades, _ = f.simulate_fade(bars, cutoffs, resting_tp=tp, allowed=allowed)
            t = f.economics(trades.loc[trades.submitted.ge(FIRST_DAY)])
            t.to_csv(f.RUN / f'vwap_{exit_name}_{gate.split()[0]}.csv', index=False, float_format='%.10g')
            for period, (start, stop) in f.PERIODS.items():
                part = t.loc[t.session.ge(start) & t.session.lt(stop)]
                low, high = f.weekly_interval(part)
                rows.append(dict(exit=exit_name, gate=gate, period=period,
                                 **f.metrics(part, calendar[(calendar >= start) & (calendar < stop)]),
                                 net_mean_r_low=low, net_mean_r_high=high))
            inside = t.loc[t.session.lt(f.END)]
            for year, part in inside.groupby(inside.session.dt.year):
                annual.append(dict(exit=exit_name, gate=gate, year=int(year), trades=len(part), net=float(part.net.sum()),
                                   gross_mean_r=float(part.gross_r.mean())))
    summary, annual = pd.DataFrame(rows), pd.DataFrame(annual)
    summary.to_csv(f.DOC / 'vwap_summary.csv', index=False, float_format='%.6g')
    annual.to_csv(f.DOC / 'vwap_annual.csv', index=False, float_format='%.6g')
    pd.set_option('display.width', 250)
    cols = ['exit', 'gate', 'period', 'trades', 'net', 'win_pct', 'profit_factor', 'gross_mean_r', 'net_mean_r',
            'daily_dd', 'net_plus_1_dollar', 'net_mean_r_low', 'net_mean_r_high']
    print(summary[cols].round(3).to_string(index=False))
    g = annual[annual.gate.eq('far below VWAP only')].pivot(index='year', columns='exit', values='net').round(0)
    g['trades_close'] = annual[annual.gate.eq('far below VWAP only') & annual.exit.eq('close')].set_index('year').trades
    print(g.to_string())
    print('positive years:', (g[['close', 'tp']] > 0).sum().to_dict())


if __name__ == '__main__':
    main()
