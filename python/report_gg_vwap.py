"""Compact chart of the exploratory GG VWAP test (docs/baseline/rtl-vwap/gg_summary.png)."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/gg_vwap_20261030'
CROSS = ROOT / 'Reports/rtl_vwap_cross_20261027'
CHART = ROOT / 'docs/baseline/rtl-vwap/gg_summary.png'
SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
BASE, RULE = '#2a78d6', '#eb6834'  # validated categorical slots 1 and 2


def curves(trades, calendar):
    out = {}
    for name, keep in (('All GG trades', trades), ('Far-below skipped', trades.loc[~trades.distance.eq('far_below')])):
        equity = keep.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.).cumsum()
        out[name] = (equity, equity.cummax()-equity)
    return out


def main():
    trades = pd.read_csv(OUT/'trades_GG.csv', parse_dates=['session'], low_memory=False)
    trades = trades.loc[trades['sample'].eq('primary')]
    calendars = pd.read_csv(CROSS/'calendars.csv', parse_dates=['session'])
    calendar = pd.DatetimeIndex(calendars.loc[calendars.instrument.eq('NQ'), 'session'])
    calendar = calendar[(calendar >= '2016-01-01') & (calendar < '2026-10-01')]
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2,
                         'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK})
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw=dict(height_ratios=[1.6, 1], hspace=.08))
    fig.patch.set_facecolor(SURFACE)
    for (name, (equity, drawdown)), colour in zip(curves(trades, calendar).items(), (BASE, RULE)):
        top.plot(equity.index, equity, color=colour, linewidth=1.6, label=f'{name}: ${equity.iloc[-1]:,.0f}')
        bottom.plot(drawdown.index, -drawdown, color=colour, linewidth=1.2, label=f'{name}: max ${drawdown.max():,.0f}')
    for ax, corner in ((top, 'upper left'), (bottom, 'lower left')):
        ax.set_facecolor(SURFACE)
        ax.grid(color=GRID, linewidth=.8)
        ax.set_axisbelow(True)
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
        ax.legend(frameon=False, loc=corner)
        ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter('${x:,.0f}'))
    top.set_ylabel('Cumulative net')
    bottom.set_ylabel('Daily-close drawdown')
    top.set_title('GG on NQ, 2016 to September 2026: skipping far-below signals (exploratory, ledger omission)',
                  loc='left', fontsize=12, color=INK)
    fig.savefig(CHART, dpi=110, bbox_inches='tight', facecolor=SURFACE)
    print(f'Wrote {CHART}')


if __name__ == '__main__':
    main()
