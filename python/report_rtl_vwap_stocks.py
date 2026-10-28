"""Compact chart of the frozen RTL VWAP stock test (docs/baseline/rtl-vwap/stock_summary.png)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_vwap_stocks_20261028'
CHART = ROOT / 'docs/baseline/rtl-vwap/stock_summary.png'
SURFACE, INK, INK2, MUTED, GRID, BAND = '#fcfcfb', '#0b0b0b', '#52514e', '#8a8984', '#e4e3df', '#f3f2ef'
RISK, MONTH = '#2a78d6', '#eb6834'  # validated categorical slots 1 and 2
PERIODS = (('pooled', 'All stocks, May 2018-Sep 2026'), ('2018-19', '2018-19 (from May)'), ('2020-26', '2020-Sep 2026'))


def percent(v):
    return '100%' if v == 1 else '0%' if v == 0 else f'{v:.1%}'


def main():
    verdict = json.loads((OUT/'verdict.json').read_text(encoding='utf-8'))
    contrast = pd.read_csv(OUT/'contrast.csv').set_index('scope')
    placebos = pd.read_csv(OUT/'placebos.csv').set_index(['period', 'placebo'])
    summaries = pd.read_csv(OUT/'summaries.csv').set_index(['period', 'curve'])
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2,
                         'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK})
    fig, (left, right) = plt.subplots(1, 2, figsize=(13.5, 7.4), gridspec_kw=dict(width_ratios=[1, 1.15], wspace=.42))
    fig.patch.set_facecolor(SURFACE)
    for ax in (left, right):
        ax.set_facecolor(SURFACE)
        ax.grid(axis='x', color=GRID, linewidth=.8)
        ax.set_axisbelow(True)
        for side in ('top', 'right', 'left'):
            ax.spines[side].set_visible(False)
        ax.tick_params(axis='y', length=0)
    # Panel 1: risk-matched contrast, pooled with its interval, eras and each stock as points.
    stocks = verdict['included_stocks']
    rows = [('pooled', 'All stocks'), ('2018-19', '2018-19'), ('2020-26', '2020-Sep 2026')] + [(s, s) for s in stocks]
    ys = [len(rows)+1.2, len(rows)+.2, len(rows)-.8] + list(range(len(stocks)-1, -1, -1))
    left.axhspan(-.6, len(stocks)-.4, color=BAND, zorder=0)
    for y, (scope, label) in zip(ys, rows):
        c = contrast.loc[scope]
        tone = INK if scope in ('pooled', '2018-19', '2020-26') else MUTED
        if scope == 'pooled':
            left.plot([c.ci95_low, c.ci95_high], [y, y], color=INK, linewidth=2, solid_capstyle='round')
        left.plot(c.estimate, y, 'o', color=tone, markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.5)
        anchor = c.ci95_high if scope == 'pooled' else c.estimate
        left.annotate(f'{c.estimate:+.3f}', (anchor, y), xytext=(8, 0), textcoords='offset points', va='center',
                      fontsize=8.5, color=INK2)
    left.axvline(0, color=INK2, linewidth=1)
    left.set_yticks(ys, [label for _, label in rows])
    left.set_xlabel('Far-below minus other trades, mean net R\n(same stock, era and risk decile; line = 95% interval)')
    left.set_title('1 · Do far-below signals earn less?', loc='left', fontsize=11, color=INK, pad=10)
    left.text(left.get_xlim()[0], len(stocks)-.25, 'Each stock (7 of 10 must be below zero)', fontsize=8.5,
              color=INK2, va='bottom')
    # Panel 2: portfolio drawdown versus the two placebos, as a share of the baseline drawdown.
    for y, (period, label) in zip((2, 1, 0), PERIODS):
        base = summaries.loc[(period, 'baseline'), 'daily_close_dd']
        for offset, key, color, marker in ((.16, 'B1', RISK, 's'), (-.16, 'B2', MONTH, '^')):
            p = placebos.loc[(period, key)]
            right.plot([p.dd_q05/base, p.dd_q95/base], [y+offset]*2, color=color, linewidth=2, solid_capstyle='round')
            right.plot(p.dd_median/base, y+offset, marker, color=color, markersize=7, markeredgecolor=SURFACE, markeredgewidth=1)
        rule = placebos.loc[(period, 'B1'), 'rule_dd']/base
        right.plot(rule, y, 'D', color=INK, markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=5)
        right.annotate(f"{percent(placebos.loc[(period, 'B1'), 'rule_beats_dd'])} · {percent(placebos.loc[(period, 'B2'), 'rule_beats_dd'])}",
                       (1.03, y), xycoords=('axes fraction', 'data'), va='center', fontsize=9.5, color=INK2, annotation_clip=False)
    right.annotate('Rule beats\nrisk · months', (1.03, 2.55), xycoords=('axes fraction', 'data'), va='bottom', fontsize=8.5,
                   color=INK2, annotation_clip=False)
    right.axvline(1, color=INK2, linewidth=1)
    right.set_yticks((2, 1, 0), [label for _, label in PERIODS])
    right.set_ylim(-.6, 2.9)
    right.set_xlabel('Portfolio daily-close max drawdown ÷ baseline drawdown\n(bars: middle 90% of 2,000 placebo draws; marker = median)')
    right.set_title('2 · Does skipping them cut drawdown more than placebos?', loc='left', fontsize=11, color=INK, pad=10)
    handles = [plt.Line2D([], [], color=INK, marker='D', linestyle='', markersize=7, label='VWAP rule'),
               plt.Line2D([], [], color=RISK, marker='s', linewidth=2, markersize=6, label='Random skips, same risk decile'),
               plt.Line2D([], [], color=MONTH, marker='^', linewidth=2, markersize=6, label="Rule's skips shifted within month")]
    right.legend(handles=handles, loc='lower center', bbox_to_anchor=(.45, 1.07), ncol=3, frameon=False, fontsize=9,
                 handletextpad=.4, columnspacing=1.2)
    tests = ', '.join(f"test {i} {'passes' if verdict[k] else 'fails'}" for i, k in
                      ((1, 'test1_contrast'), (2, 'test2_placebos'), (3, 'test3')))
    fig.suptitle(f"RTL far-below VWAP rule on ten Nasdaq-100 stocks: {verdict['verdict']} ({tests})", x=.06, ha='left',
                 y=.995, fontsize=13.5, fontweight='bold', color=INK)
    fig.text(.06, .935, 'Unchanged NQ rule; 04:00-15:59 New York session with pre-market, gap-aware fills, \\$10,000 per trade, '
             '\\$2 cost; ledger omission; frozen protocol 2026-10-28.', fontsize=9.5, color=INK2)
    fig.text(.06, .045, 'Supports only if the pooled interval in panel 1 lies below zero, the rule beats at least 95% of both placebos '
             'in panel 2, and the direction holds in each era and in at least 7 of 10 stocks.', fontsize=8.5, color=INK2)
    fig.text(.06, .018, 'Meta from 2022-06-09 only (no FB history available). Volume is Nasdaq-venue only. '
             'Risk: random skips per stock, era and risk decile. Months: the rule\'s skip pattern shifted within each stock-month.',
             fontsize=8.5, color=INK2)
    fig.subplots_adjust(left=.13, right=.86, top=.81, bottom=.19)
    fig.savefig(CHART, dpi=160, facecolor=SURFACE)
    print(f'Saved {CHART}')


if __name__ == '__main__':
    main()
