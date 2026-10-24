"""Figure and calculated tables for the downtrend crystal-ball study."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_downtrend_oracle_20261024'
SIZES = (.02, .03, .05, .10)
DELAYS = (0, 1, 2, 3, 5, 10, 20)
# Ordered blue ramp (steps 250/400/550/700): a bigger drop is a darker line.
COLORS = {.02: '#86b6ef', .03: '#3987e5', .05: '#1c5cab', .10: '#0d366b'}
ERA_TITLES = {'2016-19': '2016-19', '2020-26': '2020 - Sep 2026'}
INK, MUTED, GRID = '#1f1f1e', '#6b6a64', '#e4e3de'


def figure(rules):
    primary = rules.loc[rules.series.eq('roll_adjusted')]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), sharey=True)
    positions = list(range(len(DELAYS)))
    live_x = len(DELAYS)+.6
    for ax, era in zip(axes, ERA_TITLES):
        part = primary.loc[primary.era.eq(era)]
        ax.axvspan(3-.4, len(DELAYS)-.6, color='#f3f2ee', zorder=0)
        ax.text(3-.3, 205, 'protocol test: 3+ sessions late', color=MUTED, fontsize=9, va='top')
        ax.axhline(0, color=MUTED, lw=1.2, zorder=1)
        ax.axvline(len(DELAYS)-.2, color=GRID, lw=1, zorder=1)
        for rank, x in enumerate(SIZES):
            rows = part.loc[part['size'].eq(x)].set_index('rule')
            values = [rows.loc[f'oracle_d{d}', 'gain_pct'] for d in DELAYS]
            beats = [bool(rows.loc[f'oracle_d{d}', 'beats_shift_p975']) for d in DELAYS]
            color = COLORS[x]
            ax.plot(positions, values, color=color, lw=2, zorder=3, label=f'{x:.0%} drop')
            for position, value, beat in zip(positions, values, beats):
                ax.plot(position, value, 'o', ms=8, mew=2, zorder=4,
                        mfc=color if beat else 'white', mec='white' if beat else color)
            live = rows.loc['live_zigzag']
            ax.plot(live_x+(rank-1.5)*.22, live.gain_pct, 'D', ms=8, color=color, mec='white', mew=2, zorder=4)
            ax.annotate(f'{x:.0%}', (0, values[0]), xytext=(-10, 0), textcoords='offset points',
                        ha='right', va='center', color=INK, fontsize=9)
        ax.set_xticks(positions+[live_x], [str(d) for d in DELAYS]+['live\nzigzag'])
        ax.set_xlim(-.9, live_x+.6)
        ax.set_ylim(-100, 215)
        ax.set_title(ERA_TITLES[era], color=INK, fontsize=12, loc='left')
        ax.set_xlabel('Crystal-ball delay (sessions late)', color=MUTED)
        ax.grid(axis='y', color=GRID, lw=.8)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        ax.tick_params(colors=MUTED)
    axes[0].set_ylabel('Change in net profit vs trading every session (%)', color=MUTED)
    handles = [plt.Line2D([], [], color=COLORS[x], lw=2, marker='o', ms=7, mec='white', label=f'{x:.0%} drop') for x in SIZES]
    handles += [plt.Line2D([], [], ls='', marker='o', ms=7, mfc=MUTED, mec='white', label='beats 97.5% of shifted skips'),
                plt.Line2D([], [], ls='', marker='o', ms=7, mfc='white', mec=MUTED, label='does not'),
                plt.Line2D([], [], ls='', marker='D', ms=7, color=MUTED, mec='white', label='live zigzag (no hindsight)')]
    fig.legend(handles=handles, loc='lower center', ncol=7, frameon=False, fontsize=9)
    fig.suptitle('Skipping RTL in daily downtrends: a crystal ball helps only when it is on time',
                 x=.06, ha='left', fontsize=14, color=INK)
    fig.text(.06, .905, 'Roll-adjusted daily closes; one MNQ contract, $1.05 per trade; ledger omission, not an MT5 replay.',
             fontsize=10, color=MUTED)
    fig.tight_layout(rect=(0, .07, 1, .9))
    fig.savefig(OUT/'decay.png', dpi=150, facecolor='white')
    plt.close(fig)


def markdown(frame):
    """Plain pipe table; flattens any index into leading columns."""
    flat = frame.reset_index() if not isinstance(frame.index, pd.RangeIndex) else frame
    headers = [' '.join(str(p) for p in c if p != '') if isinstance(c, tuple) else str(c) for c in flat.columns]
    cell = lambda v: f'{v:.3f}' if isinstance(v, float) else str(v)
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '|' + '|'.join(['---']*len(headers)) + '|'] +
                     ['| ' + ' | '.join(cell(v) for v in row) + ' |' for row in flat.itertuples(index=False)])


def tables(rules, lags, yearly, decision):
    lines = ['# RTL downtrend crystal ball: calculated tables', '']
    for series in ('roll_adjusted', 'raw'):
        part = rules.loc[rules.series.eq(series)]
        for metric, label in (('gain_pct', 'Change in net profit, %'), ('skipped_mean_r', 'Skipped trades, mean net R'),
                              ('retained_daily_dd', 'Retained daily-close drawdown, $')):
            lines += [f'## {series}: {label}', '']
            view = part.pivot_table(index=['era', 'size'], columns='rule', values=metric)
            view = view[[f'oracle_d{d}' for d in DELAYS]+['live_zigzag']]
            lines += [view.round(3).pipe(markdown), '']
    lines += ['## Controls and skipped share (roll_adjusted)', '']
    columns = ['era', 'size', 'rule', 'skipped_session_share', 'skipped_trades', 'gain_dollars', 'static_net_dollars',
               'static_daily_dd', 'shift_net_p975', 'share_shifts_net_at_least_rule']
    lines += [rules.loc[rules.series.eq('roll_adjusted'), columns].round(3).pipe(markdown), '']
    lines += ['## Live zigzag lags (sessions after the true peak / trough)', '', lags.round(2).pipe(markdown), '']
    lines += ['## Downtrends per year (roll_adjusted)', '']
    view = yearly.loc[yearly.series.eq('roll_adjusted')].pivot_table(index='year', columns='size',
                                                                    values=['downtrends_starting', 'share_sessions_in_downtrend'])
    lines += [view.round(3).pipe(markdown), '']
    lines += ['## Protocol decision', '', pd.DataFrame(decision['rows']).round(3).pipe(markdown), '',
              '```json', json.dumps(decision['summary'], indent=2), '```', '']
    (OUT/'report_tables.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    rules = pd.read_csv(OUT/'rules.csv')
    lags = pd.read_csv(OUT/'lags.csv')
    yearly = pd.read_csv(OUT/'yearly.csv')
    decision = json.loads((OUT/'decision.json').read_text(encoding='utf-8'))
    figure(rules)
    tables(rules, lags, yearly, decision)
    print('Saved decay.png and report_tables.md')


if __name__ == '__main__':
    main()
