"""Figure and tables for the pullback/bounce warning statistics."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from report_rtl_downtrend_oracle import COLORS, ERA_TITLES, GRID, INK, MUTED, markdown

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_pullback_stats_20261025'
SIZES = (.02, .03, .05)
PREDICTORS = ('rise_5', 'rise_10', 'rise_20', 'zscore_5', 'zscore_10', 'zscore_20')
LABELS = ('rise\n5', 'rise\n10', 'rise\n20', 'vol-scaled\n5', 'vol-scaled\n10', 'vol-scaled\n20')
AGE_BINS = ('[1, 2]', '[3, 5]', '[6, 10]', '[11, 20]', '[21, 1000000]')
AGE_LABELS = ('1-2', '3-5', '6-10', '11-20', '21+')


def style(ax):
    ax.grid(axis='y', color=GRID, lw=.8)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    ax.tick_params(colors=MUTED)


def figure(stats, hazard):
    primary = stats.loc[stats.series.eq('roll_adjusted') & stats.level.eq('primary') & stats.k.eq(2)]
    fig, axes = plt.subplots(3, 2, figsize=(13, 12), sharey='row')
    titles = {'stop': 'Pullback warning ("up a lot"): peak within 2 sessions',
              'resume': 'Bounce warning ("down a lot"): low within 2 sessions'}
    for row, direction in enumerate(('stop', 'resume')):
        for column, era in enumerate(ERA_TITLES):
            ax = axes[row, column]
            part = primary.loc[primary.direction.eq(direction) & primary.era.eq(era)]
            ax.axhline(1, color=MUTED, lw=1.2)
            ax.axhline(1.25, color=MUTED, lw=.8, ls=':')
            for rank, x in enumerate(SIZES):
                rows = part.loc[part['size'].eq(x)].set_index('predictor').loc[list(PREDICTORS)]
                positions = [p+(rank-1)*.2 for p in range(len(PREDICTORS))]
                for position, r in zip(positions, rows.itertuples()):
                    passed = r.hit_rate > r.shift_p975
                    ax.plot(position, r.lift_vol_matched, 'o', ms=8, mew=2, zorder=3,
                            mfc=COLORS[x] if passed else 'white', mec='white' if passed else COLORS[x])
            ax.set_xticks(range(len(PREDICTORS)), LABELS, fontsize=9)
            ax.set_title(f'{ERA_TITLES[era]}: {titles[direction]}', color=INK, fontsize=10.5, loc='left')
            style(ax)
        axes[row, 0].set_ylabel('Hit rate / volatility-matched base rate', color=MUTED)
    for column, era in enumerate(ERA_TITLES):
        ax = axes[2, column]
        part = hazard.loc[hazard.series.eq('roll_adjusted') & hazard.era.eq(era) & hazard.leg.eq('rising')]
        for x in SIZES:
            rows = part.loc[part['size'].eq(x)].set_index('age_bin').reindex(list(AGE_BINS))
            ax.plot(range(len(AGE_BINS)), rows.turn_within_2*100, color=COLORS[x], lw=2, marker='o', ms=7, mec='white')
            last = rows.turn_within_2.dropna()
            ax.annotate(f'{x:.0%}', (len(AGE_BINS)-1, last.iloc[-1]*100), xytext=(8, 0), textcoords='offset points',
                        va='center', color=INK, fontsize=9)
        ax.set_xticks(range(len(AGE_BINS)), AGE_LABELS)
        ax.set_xlabel('Rally age: sessions since the low (hindsight)', color=MUTED)
        ax.set_title(f'{ERA_TITLES[era]}: do rallies get tired? Chance the peak is within 2 sessions',
                     color=INK, fontsize=10.5, loc='left')
        style(ax)
    axes[2, 0].set_ylabel('Share of rally sessions (%)', color=MUTED)
    handles = [plt.Line2D([], [], ls='', marker='o', ms=8, mfc=COLORS[x], mec='white', label=f'{x:.0%} drop') for x in SIZES]
    handles += [plt.Line2D([], [], ls='', marker='o', ms=8, mfc='white', mec=MUTED, label='not above 97.5% of shifted signals'),
                plt.Line2D([], [], color=MUTED, lw=.8, ls=':', label='1.25x: required lift')]
    fig.legend(handles=handles, loc='lower center', ncol=5, frameon=False, fontsize=9)
    fig.suptitle('Warning signals: "down a lot" finds lows; "up a lot" barely finds peaks', x=.06, ha='left',
                 fontsize=14, color=INK)
    fig.text(.06, .945, 'Roll-adjusted daily closes, 2016-19 and 2020 - Sep 2026; signals = top/bottom 10% of pre-2016 moves.',
             fontsize=10, color=MUTED)
    fig.tight_layout(rect=(0, .03, 1, .94))
    fig.savefig(OUT/'warnings.png', dpi=150, facecolor='white')
    plt.close(fig)


def tables(stats, hazard, durations, decision):
    lines = ['# Pullback and bounce warning statistics: calculated tables', '']
    for series in ('roll_adjusted', 'raw'):
        for level in ('primary', 'sensitivity'):
            part = stats.loc[stats.series.eq(series) & stats.level.eq(level) & stats.k.eq(2)]
            columns = ['size', 'direction', 'predictor', 'era', 'signals', 'hit_rate', 'base_rate', 'vol_matched_base',
                       'lift_base', 'lift_vol_matched', 'shift_p975', 'share_shifts_at_least', 'timing_hit',
                       'timing_early', 'timing_late', 'timing_false_alarm']
            lines += [f'## {series}, {level} cutoffs, k = 2', '', part[columns].round(3).pipe(markdown), '']
    for k in (1, 3):
        part = stats.loc[stats.series.eq('roll_adjusted') & stats.level.eq('primary') & stats.k.eq(k)]
        lines += [f'## roll_adjusted, primary, k = {k}', '',
                  part[['size', 'direction', 'predictor', 'era', 'hit_rate', 'lift_vol_matched', 'shift_p975']].round(3).pipe(markdown), '']
    lines += ['## Hindsight hazard: turn within 2 sessions by leg age', '', hazard.round(3).pipe(markdown), '']
    lines += ['## Leg durations (sessions)', '', durations.round(2).pipe(markdown), '']
    lines += ['## Protocol decision', '', '```json', json.dumps(decision, indent=2), '```', '']
    (OUT/'report_tables.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    stats = pd.read_csv(OUT/'stats.csv')
    hazard = pd.read_csv(OUT/'hazard.csv')
    durations = pd.read_csv(OUT/'durations.csv')
    decision = json.loads((OUT/'decision.json').read_text(encoding='utf-8'))
    figure(stats, hazard)
    tables(stats, hazard, durations, decision)
    print('Saved warnings.png and report_tables.md')


if __name__ == '__main__':
    main()
