"""Render the fixed RTL flagged-episode attribution; no classifier selection."""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_flagged_episodes_20261024'
FLAGS = ['d1_main', 'm30_main', 'm30_broad_wick', 'm30_triple']
NAMES = {'d1_main': 'Daily chop', 'm30_main': 'M30 chop',
         'm30_broad_wick': 'M30 overlap + wick', 'm30_triple': 'M30 chop + wick'}
ERAS = ['2016-19', '2020-26']
PANELS = [
    ('path_group', 'Where the logged trade path went',
     ['contained', 'upper_only', 'lower_only', 'both'],
     ['Stayed inside', 'Above range only', 'Below range only', 'Both boundaries'],
     ['#167d8d', '#c58237', '#8492a0', '#91629e']),
    ('fill_episode_state', 'Flag state when the order filled',
     ['same_episode', 'unflagged', 'later_episode', 'unknown'],
     ['Same episode', 'Unflagged', 'Later episode', 'Unknown'],
     ['#167d8d', '#c58237', '#91629e', '#8492a0']),
    ('retrospective_phase', 'Submission position within the episode',
     ['early', 'middle', 'late', 'short_episode', 'censored'],
     ['Early', 'Middle', 'Late', 'Only 1–2 observations', 'Censored'],
     ['#336b94', '#167d8d', '#c58237', '#8492a0', '#91629e']),
]


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '|' + '|'.join(['---'] * len(headers)) + '|'] +
                     ['| ' + ' | '.join(str(v) for v in row) + ' |' for row in rows])


def main():
    frame = pd.read_csv(OUT / 'summaries.csv')
    attribution = pd.read_csv(OUT / 'attribution.csv')
    parts = ['# RTL profit location: calculated attribution tables', '',
             'The range is frozen at order submission. Path bounds come from the saved '
             'trade MFE/MAE, including realized exit. Episode phase uses future episode '
             'length and is descriptive only. Recent period ends September 30, 2026.', '']
    for dimension, title, _, _, _ in PANELS:
        parts += ['## ' + title + ' (20 observations)', '']
        rows = []
        selected = frame.loc[(frame.window == 20) & (frame.dimension == dimension)]
        for r in selected.itertuples():
            rows.append([NAMES[r.flag], r.era, r.category, f'{r.trades:,.0f}', f'{r.active_episodes:,.0f}',
                         f'{r.positive_net_dollars:,.2f}', f'{r.loss_dollars:,.2f}',
                         f'{r.net_dollars:,.2f}', f'{r.net_mean_r:+.4f}', f'{100*r.winning_dollars_share:.1f}%'])
        parts += [table(['Flag', 'Era', 'Category', 'Trades', 'Active episodes', 'Winning $',
                         'Losing $ (absolute)', 'Net $', 'Net R/trade', 'Share of winning $'], rows), '']
    rows = []
    for (flag, n, era), p in frame.groupby(['flag', 'window', 'era'], sort=False):
        whole = p.loc[p.dimension == 'all'].iloc[0]
        inside = p.loc[(p.dimension == 'path_group') & (p.category == 'contained')]
        later = p.loc[(p.dimension == 'fill_episode_state') & p.category.isin(['unflagged', 'later_episode'])]
        contained_net = inside.net_dollars.sum()
        contained_wins = inside.positive_net_dollars.sum()
        rows.append([NAMES[flag], n, era, f'{whole.trades:,.0f}', f'{whole.net_dollars:,.2f}',
                     f'{contained_net:,.2f}', f'{100*contained_wins/whole.positive_net_dollars:.1f}%',
                     f'{later.net_dollars.sum():,.2f}',
                     f'{100*later.positive_net_dollars.sum()/whole.positive_net_dollars:.1f}%'])
    parts += ['## Fixed 10/20/40 sensitivity', '', table(
        ['Flag', 'Window', 'Era', 'Trades', 'All net $', 'Contained net $',
         'Contained winning-$ share', 'Filled after original episode net $', 'After-episode winning-$ share'], rows), '']
    for dimension in ['causal_age_bin', 'exit_episode_state', 'fill_location', 'exit_location', 'phase_x_path']:
        rows = []
        for r in frame.loc[(frame.window == 20) & (frame.dimension == dimension)].itertuples():
            rows.append([NAMES[r.flag], r.era, r.category.replace('|', '/'), f'{r.trades:,.0f}',
                         f'{r.net_dollars:,.2f}', f'{r.net_mean_r:+.4f}',
                         f'{100*r.winning_dollars_share:.1f}%', f'{100*r.losing_dollars_share:.1f}%'])
        parts += ['## ' + dimension.replace('_', ' ') + ' (20 observations)', '', table(
            ['Flag', 'Era', 'Category', 'Trades', 'Net $', 'Net R/trade', 'Winning-$ share', 'Losing-$ share'], rows), '']
    rows = []
    for (flag, era), group in attribution.loc[attribution.window == 20].groupby(['flag', 'era']):
        upper = group.loc[group.path_group == 'upper_only']
        contained = group.loc[group.path_group == 'contained']
        rows.append([NAMES[flag], era, len(group), f'{100*group.headroom_r.lt(1).mean():.1f}%',
                     f'{100*upper.headroom_r.lt(1).mean():.1f}%',
                     f'{100*contained.headroom_r.lt(1).mean():.1f}%',
                     f'{upper.headroom_r.median():.4f}', f'{contained.headroom_r.median():.4f}'])
    parts += ['## Submission headroom to frozen upper boundary (20 observations)', '',
              'Headroom uses requested entry and original planned risk. This is a descriptive '
              'check on the mechanical relationship between the 1R exit objective and a later upper excursion.', '',
              table(['Flag', 'Era', 'Trades', 'All headroom <1R', 'Upper-excursion headroom <1R',
                     'Contained headroom <1R', 'Upper median R', 'Contained median R'], rows), '']
    rows = []
    wick = attribution.loc[(attribution.window == 20) & (attribution.flag == 'm30_broad_wick')]
    for (era, state, path), group in wick.groupby(['era', 'exit_episode_state', 'path_group']):
        rows.append([era, state, path, len(group), f'{group.net_dollars.sum():,.2f}'])
    parts += ['## Broad wick: realized path and exit flag state (20 observations)', '',
              table(['Era', 'Exit state', 'Realized path', 'Trades', 'Net $'], rows), '']
    (OUT / 'report_tables.md').write_text('\n'.join(parts), encoding='utf-8')

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 3, figsize=(17, 8.4))
    for row, era in enumerate(ERAS):
        for col, (dimension, title, categories, labels, colors) in enumerate(PANELS):
            ax = axes[row, col]
            p = frame.loc[(frame.window == 20) & (frame.era == era) & (frame.dimension == dimension)]
            matrix = p.pivot(index='flag', columns='category', values='positive_net_dollars').reindex(
                index=FLAGS, columns=categories).fillna(0)
            denominator = matrix.sum(axis=1).to_numpy()
            assert (denominator > 0).all()
            shares = matrix.to_numpy() / denominator[:, None] * 100
            assert np.allclose(shares.sum(axis=1), 100)
            left = np.zeros(len(FLAGS))
            for i, (category, label, color) in enumerate(zip(categories, labels, colors)):
                width = shares[:, i]
                ax.barh(np.arange(len(FLAGS)), width, left=left, color=color, label=label, height=.60)
                for j, value in enumerate(width):
                    if value >= 12:
                        ax.text(left[j] + value/2, j, f'{value:.0f}%', va='center', ha='center',
                                color='white', fontsize=10, fontweight='bold')
                left += width
            ax.set_yticks(np.arange(len(FLAGS)), [NAMES[x] for x in FLAGS] if col == 0 else [])
            ax.invert_yaxis()
            ax.set_xlim(0, 100)
            ax.set_xticks([0, 25, 50, 75, 100], ['0%', '25%', '50%', '75%', '100%'])
            ax.set_xlabel('Share of winning-trade dollars')
            if row == 0:
                ax.set_title(title, fontsize=12, fontweight='bold', pad=16)
            if col == 0:
                ax.set_ylabel(era, fontsize=12, fontweight='bold')
            if row == 1:
                ax.legend(loc='upper center', bbox_to_anchor=(.5, -.25), ncol=2,
                          fontsize=9, frameon=False)
    fig.suptitle('Where profits occurred inside the existing RTL flags\n'
                 'Fixed 20-observation labels; winning dollars shown separately from losses', fontsize=16)
    fig.text(.5, .02, 'Shares describe profitable trades, not net returns. '
             'Episode phase is retrospective; it cannot be used as a live entry rule.',
             ha='center', fontsize=10)
    fig.tight_layout(rect=[0, .10, 1, .92], h_pad=2.5, w_pad=1.8)
    fig.savefig(OUT / 'profit_location.png', dpi=160)
    plt.close(fig)
    names = ['report_tables.md', 'profit_location.png']
    manifest = {'report_program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'outputs_sha256': {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names}}
    (OUT / 'report_artifacts.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print('Saved episode attribution tables and figure.')


if __name__ == '__main__':
    main()
