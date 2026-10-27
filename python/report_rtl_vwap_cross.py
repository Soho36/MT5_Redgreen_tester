"""Compact chart of the frozen cross-instrument VWAP test (docs/baseline/rtl-vwap/cross_summary.png)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_vwap_cross_20261027'
CHART = ROOT / 'docs/baseline/rtl-vwap/cross_summary.png'
SURFACE, INK, INK2, MUTED, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#8a8984', '#e4e3df'
RISK, MONTH = '#2a78d6', '#eb6834'  # validated categorical slots 1 and 2
ROWS = [('NQ', 'primary', 'pooled', 'NQ 2016–26 · reference'), ('ES', 'primary', 'pooled', 'ES 2016–26'),
        ('YM', 'primary', 'pooled', 'YM 2016–26'), ('RTY', 'primary', 'pooled', 'RTY 2018–26'),
        ('NQ', 'secondary', '2010-15', 'NQ 2010–15'), ('ES', 'secondary', '2010-15', 'ES 2010–15'),
        ('YM', 'secondary', '2010-15', 'YM 2010–15')]


def main():
    contrast = pd.read_csv(OUT/'contrast.csv').set_index(['instrument', 'sample', 'period'])
    placebos = pd.read_csv(OUT/'placebos.csv').set_index(['instrument', 'sample', 'period', 'placebo'])
    summaries = pd.read_csv(OUT/'summaries.csv').set_index(['instrument', 'sample', 'period', 'curve'])
    verdict = json.loads((OUT/'verdict.json').read_text(encoding='utf-8'))
    confirms = {(r['instrument'], r['sample']): r['confirms'] for r in verdict['primary']+verdict['reference_and_secondary']}
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2,
                         'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK})
    fig, (left, right) = plt.subplots(1, 2, figsize=(13.5, 7.4), sharey=True, gridspec_kw=dict(width_ratios=[1, 1.2], wspace=.08))
    fig.patch.set_facecolor(SURFACE)
    positions = [6.6, 5.6, 4.6, 3.6, 2, 1, 0]
    for ax in (left, right):
        ax.set_facecolor(SURFACE)
        ax.grid(axis='x', color=GRID, linewidth=.8)
        ax.set_axisbelow(True)
        for side in ('top', 'right', 'left'):
            ax.spines[side].set_visible(False)
        ax.tick_params(axis='y', length=0)
        ax.axhspan(-.6, 2.6, color='#f3f2ef', zorder=0)
    for y, (name, sample, period, label) in zip(positions, ROWS):
        c = contrast.loc[(name, sample, period)]
        tone = INK if sample == 'primary' else MUTED
        left.plot([c.ci95_low, c.ci95_high], [y, y], color=tone, linewidth=2, solid_capstyle='round')
        left.plot(c.estimate, y, 'o', color=tone, markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.5)
        left.annotate(f'{c.estimate:+.3f}', (c.ci95_high, y), xytext=(6, 0), textcoords='offset points',
                      va='center', fontsize=9, color=INK2)
        base = summaries.loc[(name, sample, period, 'baseline'), 'daily_close_dd']
        for offset, key, color, marker in ((.16, 'B1', RISK, 's'), (-.16, 'B2', MONTH, '^')):
            p = placebos.loc[(name, sample, period, key)]
            right.plot([p.dd_q05/base, p.dd_q95/base], [y+offset]*2, color=color, linewidth=2, solid_capstyle='round')
            right.plot(p.dd_median/base, y+offset, marker, color=color, markersize=7, markeredgecolor=SURFACE, markeredgewidth=1)
        rule = placebos.loc[(name, sample, period, 'B1')]
        right.plot(rule.rule_dd/base, y, 'D', color=INK, markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=5)
        share = lambda key: placebos.loc[(name, sample, period, key), 'rule_beats_dd']
        percent = lambda v: '100%' if v == 1 else '0%' if v == 0 else f'{v:.1%}'
        beats = f"{percent(share('B1'))} · {percent(share('B2'))}"
        status = 'confirms' if confirms[(name, sample)] else 'fails'
        right.annotate(beats, (1.04, y), xycoords=('axes fraction', 'data'), va='center', fontsize=9.5, color=INK2,
                       annotation_clip=False)
        right.annotate(status, (1.29, y), xycoords=('axes fraction', 'data'), va='center', fontsize=9.5,
                       color=INK if status == 'confirms' else INK2, fontweight='bold' if status == 'confirms' else 'normal',
                       annotation_clip=False)
    for x, text in ((1.04, 'Rule beats\nrisk · months'), (1.29, 'Verdict')):
        right.annotate(text, (x, 7.05), xycoords=('axes fraction', 'data'), va='bottom', fontsize=8.5, color=INK2,
                       annotation_clip=False)
    left.axvline(0, color=INK2, linewidth=1)
    left.set_xlim(-.16, .135)
    left.set_yticks(positions, [label for *_, label in ROWS])
    left.set_xlabel('Far-below minus other trades, mean net R\n(within the same risk decile; line = 95% interval)')
    left.set_title('1 · Do far-below signals earn less?', loc='left', fontsize=11, color=INK, pad=10)
    left.text(-.155, 2.35, 'Earlier years · descriptive, not in the verdict', fontsize=8.5, color=INK2)
    right.axvline(1, color=INK2, linewidth=1)
    right.text(1.01, 7.1, 'baseline', fontsize=8.5, color=INK2)
    right.set_xlabel('Daily-close max drawdown ÷ baseline drawdown\n(bars: middle 90% of 2,000 placebo draws; marker = median)')
    right.set_title('2 · Does skipping them cut drawdown more than placebos?', loc='left', fontsize=11, color=INK, pad=10)
    handles = [plt.Line2D([], [], color=INK, marker='D', linestyle='', markersize=7, label='VWAP rule'),
               plt.Line2D([], [], color=RISK, marker='s', linewidth=2, markersize=6, label='Random skips, same risk decile'),
               plt.Line2D([], [], color=MONTH, marker='^', linewidth=2, markersize=6, label="Rule's skips shifted within month")]
    right.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, 1.07), ncol=3, frameon=False, fontsize=9,
                 handletextpad=.4, columnspacing=1.2)
    right.set_ylim(-.6, 7.4)
    fig.suptitle('RTL far-below VWAP rule on ES, YM and RTY: does not transfer (0 of 3 confirm)',
                 x=.06, ha='left', y=.995, fontsize=14, fontweight='bold', color=INK)
    fig.text(.06, .935, 'Unchanged NQ rule: skip a new RTL buy stop when the signal close is below full-session VWAP − A20. '
             'Ledger omission; frozen protocol 2026-10-27.', fontsize=9.5, color=INK2)
    fig.text(.06, .045, 'Confirms only if the interval in panel 1 lies below zero and the rule beats at least 95% of draws of both '
             'placebos in panel 2, with the same direction in each era.', fontsize=8.5, color=INK2)
    fig.text(.06, .018, 'Ledger omission, not a replay. Risk: random skips of as many trades per risk decile. Months: the '
             "rule's own skip pattern shifted within each month. RTY 2017 H2 left out: too few far-below weeks.",
             fontsize=8.5, color=INK2)
    fig.subplots_adjust(left=.15, right=.77, top=.81, bottom=.19)
    fig.savefig(CHART, dpi=160, facecolor=SURFACE)
    print(f'Saved {CHART}')


if __name__ == '__main__':
    main()
