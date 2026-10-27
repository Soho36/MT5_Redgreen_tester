"""Render audited RTL VWAP replay curves and risk comparisons as a static figure.

Usage: python report_rtl_vwap_replay.py [--planned-risk]
Requires completed analyzer outputs; this script never launches a backtest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / 'Reports/rtl_vwap_replay_20261026'
OUTPUT = ROOT / 'docs/baseline/rtl-vwap/replay_summary.png'
ERAS = [('2016-19', '2016–2019'), ('2020-26', '2020–September 2026')]
STYLE = {
    'baseline': dict(color='#374151', label='Baseline · 1 contract', linestyle='-', linewidth=1.6),
    'gated': dict(color='#007F79', label='VWAP gate · 1 contract', linestyle='-', linewidth=1.8),
    'static_holding': dict(color='#BE7B18', label='Baseline sized to same total holding time',
                           linestyle=(0, (5, 2.5)), linewidth=1.5),
    'static_planned_risk': dict(color='#8854A0', label='Baseline sized to same total planned risk',
                                linestyle=(0, (2, 2)), linewidth=1.4),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_audited_outputs():
    audit = json.loads((RUN / 'analysis_audit.json').read_text(encoding='utf-8'))
    baseline = json.loads((RUN / 'baseline_validation.json').read_text(encoding='utf-8'))
    if audit.get('all_passed') is not True or baseline.get('all_passed') is not True:
        raise RuntimeError('Figure requires successful analysis and baseline validation')
    names = ['summaries.csv', 'daily_curves.csv', 'open_equity.csv']
    for name in names:
        if digest(RUN / name) != audit['outputs_sha256'][name]:
            raise RuntimeError('Audited result changed: ' + name)
    summaries = pd.read_csv(RUN / names[0])
    daily = pd.read_csv(RUN / names[1], parse_dates=['session'])
    equity = pd.read_csv(RUN / names[2])
    if summaries.duplicated(['era', 'curve']).any() or daily.duplicated(['era', 'curve', 'session']).any():
        raise RuntimeError('Duplicate era/curve rows')
    return summaries.set_index(['era', 'curve']), daily, equity


def dollars(value):
    return f'${value:,.0f}' if value >= 0 else f'−${abs(value):,.0f}'


def axis_dollars(value, _):
    return f'−${abs(value):,.0f}' if value < 0 else f'${value:,.0f}'


def render(include_planned_risk=False):
    summaries, daily, equity = read_audited_outputs()
    curves = ['baseline', 'gated', 'static_holding']
    if include_planned_risk:
        curves.append('static_planned_risk')
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 10,
        'axes.titlesize': 13, 'axes.labelsize': 10,
        'axes.edgecolor': '#CCD2D7', 'axes.labelcolor': '#374151',
        'xtick.color': '#59636E', 'ytick.color': '#59636E',
        'text.color': '#17212D', 'figure.facecolor': 'white',
        'axes.spines.top': False, 'axes.spines.right': False,
        'savefig.facecolor': 'white',
    })
    fig = plt.figure(figsize=(15, 10.4))
    grid = fig.add_gridspec(2, 2, left=.085, right=.975, top=.79, bottom=.32,
                           hspace=.10, wspace=.22, height_ratios=[1.65, 1])
    fig.text(.055, .963, 'RTL long strategy · full VWAP order replay',
             fontsize=21, weight='bold', va='top')
    fig.text(.055, .922,
             'NQ price/volume · MNQ $2/point valuation · M30 signals · 1-minute OHLC · $1.05/trade',
             fontsize=11, color='#4B5563', va='top', parse_math=False)
    fig.text(.055, .895,
             'Gate: skip a new buy-stop replacement when the completed close is below session VWAP − A20.',
             fontsize=10.5, color='#4B5563', va='top')
    handles = [Line2D([0], [0], **STYLE[curve]) for curve in curves]
    fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(.049, .863),
               frameon=False, ncol=2 if include_planned_risk else 3,
               handlelength=3.1, columnspacing=2.0, fontsize=10)

    for column, (era, label) in enumerate(ERAS):
        pnl_ax = fig.add_subplot(grid[0, column])
        dd_ax = fig.add_subplot(grid[1, column], sharex=pnl_ax)
        pnl_ax.set_title(label, loc='left', weight='bold', pad=14)
        calendars = []
        for curve in curves:
            values = daily.loc[daily.era.eq(era) & daily.curve.eq(curve)].sort_values('session')
            if values.empty or not np.isfinite(values.net_dollars).all():
                raise RuntimeError('Missing/nonfinite curve: ' + era + '/' + curve)
            dates = pd.DatetimeIndex(values.session)
            calendars.append(dates)
            cumulative = np.r_[0., values.net_dollars.cumsum().to_numpy()]
            drawdown = cumulative - np.maximum.accumulate(cumulative)
            expected = summaries.loc[(era, curve)]
            np.testing.assert_allclose(cumulative[-1], expected.net_dollars, rtol=0, atol=1e-6)
            np.testing.assert_allclose(-drawdown.min(), expected.daily_close_dd, rtol=0, atol=1e-6)
            dates = dates.insert(0, dates[0] - pd.Timedelta(days=1))
            pnl_ax.plot(dates, cumulative, **STYLE[curve])
            dd_ax.plot(dates, drawdown, **STYLE[curve])
        if any(not calendars[0].equals(calendar) for calendar in calendars[1:]):
            raise RuntimeError('Curves use different eligible sessions')
        for axis in (pnl_ax, dd_ax):
            axis.axhline(0, color='#9CA3AF', linewidth=.7, zorder=0)
            axis.grid(axis='y', color='#E7EAED', linewidth=.7)
            axis.set_axisbelow(True)
            axis.yaxis.set_major_formatter(FuncFormatter(axis_dollars))
            axis.yaxis.set_major_locator(MaxNLocator(nbins=5))
            axis.tick_params(axis='both', labelsize=9, length=3)
            axis.margins(x=.015)
        pnl_ax.tick_params(axis='x', labelbottom=False)
        dd_ax.xaxis.set_major_locator(mdates.YearLocator())
        dd_ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        pnl_ax.set_ylabel('Cumulative net profit')
        dd_ax.set_ylabel('Daily-close drawdown')
        dd_ax.set_ylim(top=max(1., abs(dd_ax.get_ylim()[0]) * .05))

        # Summarize full-era open-equity risk separately: the plotted lines are
        # daily realized P&L, whereas this statistic includes open positions.
        current = equity.loc[equity.era.eq(era) & np.isclose(equity.cost_per_trade, 1.05)]
        if 'year' in current:
            current = current.loc[current.year.isna()]
        if set(current.variant) != {'off', 'on'} or len(current) != 2:
            raise RuntimeError('Expected one full-era base-cost open-equity row per arm')
        open_dd = current.set_index('variant').sampled_open_equity_dd
        holding = summaries.loc[(era, 'gated'), 'retained_holding_fraction']
        table_curves = ['baseline', 'gated', 'static_holding']
        rows = [
            ['Net profit'] + [dollars(summaries.loc[(era, c), 'net_dollars']) for c in table_curves],
            ['Max daily-close DD'] + [dollars(summaries.loc[(era, c), 'daily_close_dd']) for c in table_curves],
            ['Max sampled open-equity DD', dollars(open_dd['off']), dollars(open_dd['on']), '—'],
            ['Trades'] + [f'{int(summaries.loc[(era, c), "trades"]):,}' for c in table_curves],
        ]
        left = .055 if column == 0 else .55
        table_ax = fig.add_axes([left, .116, .425, .145])
        table_ax.axis('off')
        table = table_ax.table(cellText=rows,
            colLabels=['', 'Baseline', 'VWAP gate', f'Baseline × {holding:.1%}'],
            colWidths=[.43, .18, .18, .21], loc='center', cellLoc='right')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.4)
        for (row, col), cell in table.get_celld().items():
            cell.set_edgecolor('white')
            cell.set_linewidth(0)
            cell.set_facecolor('#F0F3F5' if row == 0 else ('#F8F9FA' if row % 2 else 'white'))
            if row == 0:
                cell.set_text_props(weight='bold')
            if col == 0:
                cell.set_text_props(ha='left', color='#4B5563')
        fig.text(left, .274, label + ' · full-era results', fontsize=10.5, weight='bold')

    fig.text(.055, .077,
             'Each era starts at $0; vertical scales differ. October 2026 partial endpoint excluded. '
             'Daily curves include realized trade P&L only.', fontsize=9, color='#59636E')
    fig.text(.055, .055,
             'Scaled baselines are analytical fractional-contract comparisons, sized separately within each era; '
             'they are not additional replay runs.', fontsize=9, color='#59636E')
    fig.text(.055, .033,
             'Source: exact-baseline-validated MT5 replay and audited analysis outputs. '
             'A20 is the mean true range of 20 completed M30 bars.', fontsize=9, color='#59636E')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=200, metadata={'Title': 'RTL VWAP full replay comparison',
                                        'Description': 'Audited historical simulation; no live-trading recommendation.'})
    plt.close(fig)
    print(str(OUTPUT), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--planned-risk', action='store_true',
                        help='Also plot the baseline scaled to matching total planned risk')
    render(parser.parse_args().planned_risk)
