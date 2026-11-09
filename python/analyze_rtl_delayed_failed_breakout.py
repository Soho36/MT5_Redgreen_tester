"""Reconcile the native delayed-short replays and compare their actual fills."""
from __future__ import annotations

import numpy as np
import pandas as pd

from analyze_rtl_failed_breakout_short import PERIODS, calendar, check_report
from analyze_rtl_short_vwap import bootstrap, metrics
from project_paths import PROJECT_ROOT
from verify_rtl_failed_breakout_short import verify_metrics

RUN = PROJECT_ROOT / 'Reports/rtl_delayed_failed_breakout_20261106'
TAG = 'rtldelay_20261106'
VARIANTS = ('immediate', 'delayed', 'plain')


def read_events(variant):
    return pd.read_csv(RUN / f'failed_breakout_{TAG}_{variant}.csv', sep='\t', encoding='cp1252',
                       parse_dates=['time', 'signal_bar', 'watch_bar'], date_format='%Y.%m.%d %H:%M:%S')


def get_trades(variant):
    trades = check_report(RUN, TAG, variant, offset=0.25)
    events = read_events(variant)
    orders = events.loc[events.event.eq('armed'), ['order', 'time', 'signal_bar', 'watch_bar']]
    trades = trades.merge(orders, left_on='ticket', right_on='order', validate='one_to_one', how='left')
    assert trades.signal_bar.notna().all() and trades.signal_bar.is_unique
    assert trades.submitted.eq(trades.time).all()
    return trades.drop(columns=['order', 'time']).set_index('signal_bar', drop=False)


def attribute(immediate, delayed):
    """Reconcile the old later-fill subset to the deployable rule by signal identity."""
    later = immediate.loc[immediate.entry_time.dt.floor('30min') > immediate.watch_bar]
    union = later.index.union(delayed.index)
    a, b = later.reindex(union), delayed.reindex(union)
    same_path = (a.entry_time.eq(b.entry_time) & a.exit_time.eq(b.exit_time)
                 & a.fill_price.eq(b.fill_price) & a.exit_price.eq(b.exit_price))
    out = pd.DataFrame({'signal_bar': union, 'session': a.session.combine_first(b.session),
                        'old_later_net': a.net_dollars.fillna(0), 'delayed_net': b.net_dollars.fillna(0),
                        'old_later_trade': a.ticket.notna(), 'delayed_trade': b.ticket.notna()})
    out['group'] = np.select([a.ticket.isna(), b.ticket.isna(), same_path],
                             ['new in delayed replay', 'only in old later subset', 'same fill and exit'],
                             default='same signal, changed path')
    assert np.isclose(out.old_later_net.sum(), later.net_dollars.sum())
    assert np.isclose(out.delayed_net.sum(), delayed.net_dollars.sum())
    return out.reset_index(drop=True)


def save_equity(frames, calendar_days):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    days = calendar_days[(calendar_days >= '2016-01-01') & (calendar_days < '2026-10-01')]
    fig, ax = plt.subplots(figsize=(9, 4.6), layout='constrained')
    labels = {'immediate': 'Sell stop on high break', 'delayed': 'Wait for close after high break',
              'plain': 'Wait for close without high-break condition'}
    for variant, trades in frames.items():
        sample = trades.loc[trades.session.ge(days[0]) & trades.session.lt('2026-10-01')]
        daily = sample.groupby(sample.exit_time.dt.normalize()).net_dollars.sum().reindex(days, fill_value=0)
        ax.plot(days, daily.cumsum(), lw=1.3, label=labels[variant])
    ax.axhline(0, color='black', lw=.6)
    ax.set(title='Red-candle shorts on NQ, January 2016 to September 2026',
           ylabel='Cumulative net USD, one MNQ')
    ax.legend(frameon=False)
    ax.grid(alpha=.2)
    fig.savefig(RUN / 'equity.png', dpi=150)
    plt.close(fig)


def main():
    cal = calendar()
    frames = {variant: get_trades(variant) for variant in VARIANTS}
    rows, annual = [], []
    for variant, trades in frames.items():
        for period, (begin, end) in PERIODS.items():
            subset = trades.loc[trades.session.ge(begin) & trades.session.lt(end)]
            days = cal[(cal >= begin) & (cal < end)]
            row = dict(variant=variant, period=period, **metrics(subset, days))
            verify_metrics(subset, pd.Series(row), (variant, period))
            if variant == 'delayed':
                row.update(bootstrap(subset, days, seed=20261106))
            rows.append(row)
        study = trades.loc[trades.session.ge('2016-01-01') & trades.session.lt('2026-10-01')]
        for year, subset in study.groupby(study.session.dt.year):
            row = dict(variant=variant, year=int(year),
                       **metrics(subset, cal[(cal.year == year) & (cal < '2026-10-01')]))
            verify_metrics(subset, pd.Series(row), (variant, int(year)))
            annual.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(RUN / 'summaries.csv', index=False, float_format='%.12g')
    pd.DataFrame(annual).to_csv(RUN / 'annual.csv', index=False, float_format='%.12g')
    signals = attribute(frames['immediate'], frames['delayed'])
    signals.to_csv(RUN / 'signal_comparison.csv', index=False)
    attribution = []
    for period, (begin, end) in PERIODS.items():
        part = signals.loc[signals.session.ge(begin) & signals.session.lt(end)]
        totals = part.groupby('group')[['old_later_trade', 'delayed_trade', 'old_later_net', 'delayed_net']].sum()
        attribution.append(totals.assign(period=period))
    pd.concat(attribution).to_csv(RUN / 'attribution.csv', float_format='%.2f')
    print(summary[['variant', 'period', 'trades', 'net_dollars', 'profit_factor', 'daily_close_dd',
                   'net_mean_r', 'stress1_net_dollars', 'stress2_net_dollars']].to_string(index=False))
    print(attribution[-1].to_string())
    save_equity(frames, cal)


if __name__ == '__main__':
    main()
