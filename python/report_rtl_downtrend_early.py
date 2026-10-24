"""Figure and tables for the early-signal crystal-ball addendum."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from report_rtl_downtrend_oracle import COLORS, ERA_TITLES, GRID, INK, MUTED, SIZES, markdown

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_downtrend_early_20261025'
FIRST = ROOT / 'Reports/rtl_downtrend_oracle_20261024'
TIMING = (-5, -3, -2, -1, 0, 1, 2, 3, 5, 10, 20)
EARLY_STOP = (0, 1, 2, 3, 5)


def combined():
    early = pd.read_csv(OUT/'rules.csv')
    late = pd.read_csv(FIRST/'rules.csv')
    late = late.loc[late.rule.str.startswith('oracle_d') & ~late.rule.eq('oracle_d0')].copy()
    late['timing'] = late.rule.str.removeprefix('oracle_d').astype(int)
    symmetric = early.loc[~early.rule.str.startswith('early_stop')].copy()
    symmetric['timing'] = -symmetric.sessions_early
    stop = early.loc[early.rule.str.startswith('early_stop') | early.rule.eq('oracle_d0')].copy()
    stop['timing'] = stop.sessions_early
    return pd.concat([symmetric, late], ignore_index=True), stop


def panel(ax, part, axis_values, title):
    positions = range(len(axis_values))
    for x in SIZES:
        rows = part.loc[part['size'].eq(x)].set_index('timing').loc[list(axis_values)]
        color = COLORS[x]
        ax.plot(positions, rows.gain_pct, color=color, lw=2, zorder=3)
        for position, (value, beat) in enumerate(zip(rows.gain_pct, rows.beats_shift_p975)):
            ax.plot(position, value, 'o', ms=7, mew=2, zorder=4, mfc=color if beat else 'white', mec='white' if beat else color)
    ax.axhline(0, color=MUTED, lw=1.2, zorder=1)
    ax.set_xticks(list(positions), [str(v) for v in axis_values])
    ax.set_title(title, color=INK, fontsize=11, loc='left')
    ax.grid(axis='y', color=GRID, lw=.8)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    ax.tick_params(colors=MUTED)


def figure(symmetric, stop):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharey='row', gridspec_kw=dict(width_ratios=(1, 1)))
    for column, era in enumerate(ERA_TITLES):
        primary = symmetric.loc[symmetric.series.eq('roll_adjusted') & symmetric.era.eq(era)]
        ax = axes[0, column]
        ax.axvspan(-.4, 3.4, color='#f3f2ee', zorder=0)
        ax.axvline(4, color=MUTED, lw=.8, ls=':', zorder=1)
        panel(ax, primary, TIMING, f'{ERA_TITLES[era]}: stop and resume both shifted')
        ax.set_xlabel('Sessions early (negative) or late (positive)', color=MUTED)
        ax.text(1.5, ax.get_ylim()[1]*.97 if column else 205, 'early', color=MUTED, fontsize=9, ha='center', va='top')
        primary = stop.loc[stop.series.eq('roll_adjusted') & stop.era.eq(era)]
        ax = axes[1, column]
        panel(ax, primary, EARLY_STOP, f'{ERA_TITLES[era]}: stop early, resume exactly at the low')
        ax.set_xlabel('Sessions early on the stop only', color=MUTED)
    for ax in axes[:, 0]:
        ax.set_ylabel('Change in net profit vs trading every session (%)', color=MUTED)
    axes[0, 0].set_ylim(-100, 215)
    axes[1, 0].set_ylim(-10, 215)
    handles = [plt.Line2D([], [], color=COLORS[x], lw=2, marker='o', ms=7, mec='white', label=f'{x:.0%} drop') for x in SIZES]
    handles += [plt.Line2D([], [], ls='', marker='o', ms=7, mfc=MUTED, mec='white', label='beats 97.5% of shifted skips'),
                plt.Line2D([], [], ls='', marker='o', ms=7, mfc='white', mec=MUTED, label='does not')]
    fig.legend(handles=handles, loc='lower center', ncol=6, frameon=False, fontsize=9)
    fig.suptitle('Crystal ball timing: being early costs far less than being late', x=.06, ha='left', fontsize=14, color=INK)
    fig.text(.06, .935, 'Roll-adjusted daily closes; shaded = early. One MNQ contract, $1.05 per trade; ledger omission, not an MT5 replay.',
             fontsize=10, color=MUTED)
    fig.tight_layout(rect=(0, .04, 1, .93))
    fig.savefig(OUT/'timing.png', dpi=150, facecolor='white')
    plt.close(fig)


def tables(symmetric, stop, decision):
    lines = ['# RTL downtrend crystal ball, early signals: calculated tables', '']
    for series in ('roll_adjusted', 'raw'):
        for frame, axis_values, label in ((symmetric, TIMING, 'stop and resume shifted (negative = early)'),
                                          (stop, EARLY_STOP, 'stop early, resume on time')):
            for metric in ('gain_pct', 'retained_mean_r', 'share_shifts_net_at_least_rule'):
                part = frame.loc[frame.series.eq(series)]
                view = part.pivot_table(index=['era', 'size'], columns='timing', values=metric)[list(axis_values)]
                lines += [f'## {series}: {label}: {metric}', '', view.round(3).pipe(markdown), '']
    lines += ['## Addendum decision', '', '```json', json.dumps(decision, indent=2), '```', '']
    (OUT/'report_tables.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    symmetric, stop = combined()
    decision = json.loads((OUT/'decision.json').read_text(encoding='utf-8'))
    figure(symmetric, stop)
    tables(symmetric, stop, decision)
    print('Saved timing.png and report_tables.md')


if __name__ == '__main__':
    main()
