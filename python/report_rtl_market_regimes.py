"""Render the frozen RTL regime screen; calculations live in the analyzer.

Usage: python python/report_rtl_market_regimes.py
Produces report_tables.md and a static diagnostic figure beside the study outputs.
"""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from project_paths import PROJECT_ROOT

STUDY = PROJECT_ROOT / 'Reports/rtl_market_regimes_20261023'
GROUPS = ['bull_normal', 'bull_elevated', 'neutral_normal', 'neutral_elevated',
          'bear_normal', 'bear_elevated']
LABELS = ['Bull / normal', 'Bull / elevated', 'Neutral / normal',
          'Neutral / elevated', 'Bear / normal', 'Bear / elevated']
ERAS = ['2016-19', '2020-26']


def money(value):
    return f'{value:,.0f}'


def markdown_table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '|' + '|'.join(['---'] * len(headers)) + '|'] +
                     ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])


def main():
    frame = pd.read_csv(STUDY / 'summaries.csv')
    assert set(frame.group) == set(GROUPS + ['all'])
    assert len(frame) == 14
    tables = []
    for era in ERAS:
        part = frame[frame.era == era].set_index('group').reindex(GROUPS + ['all'])
        assert part.trades.iloc[:-1].sum() == part.loc['all', 'trades']
        assert np.isclose(part.net_dollars.iloc[:-1].sum(), part.loc['all', 'net_dollars'])
        rows = []
        for group, row in part.iterrows():
            label = 'All RTL' if group == 'all' else LABELS[GROUPS.index(group)]
            rows.append([label, f'{row.trades:,.0f}', money(row.net_dollars),
                         f'{row.dollar_pf:.3f}', f'{row.gross_mean_r:+.3f}',
                         f'{row.net_mean_r:+.3f}', money(row.risk_mean)])
        tables += [f'## {era} primary groups', '', markdown_table(
            ['Group', 'Trades', 'Net $', 'PF', 'Gross R/trade', 'Net R/trade', 'Mean initial risk $'], rows), '']
    tables += ['## Uncertainty (four-week moving blocks)', '',
               'Intervals below are exploratory, two-sided and in R/trade. The 99.1667% interval accounts for the six groups within each era.', '']
    rows = []
    for row in frame[frame.group != 'all'].itertuples():
        rows.append([row.era, row.group.replace('_', ' / '),
                     f'[{row.mean_net_r_ci95_low:+.3f}, {row.mean_net_r_ci95_high:+.3f}]',
                     f'[{row.mean_net_r_ci99_1667_low:+.3f}, {row.mean_net_r_ci99_1667_high:+.3f}]',
                     f'{row.difference_net_r:+.3f}',
                     f'[{row.difference_net_r_ci95_low:+.3f}, {row.difference_net_r_ci95_high:+.3f}]'])
    tables += [markdown_table(['Era', 'Group', 'Mean net R: 95%', 'Mean net R: 99.1667%',
                               'R vs others', 'Difference: 95%'], rows), '']
    rows = []
    for row in frame.itertuples():
        rows.append([row.era, row.group.replace('_', ' / '), money(row.risk_mean),
                     money(row.risk_median), f'{row.commission_mean_r:.3f}',
                     money(row.worst_day), money(row.worst_week),
                     money(row.daily_close_dd), f'{row.daily_dd_duration_days:.0f}'])
    tables += ['## Dollar risk and daily-close outcomes', '', markdown_table(
        ['Era', 'Group', 'Mean risk $', 'Median risk $', 'Mean commission R', 'Worst day $',
         'Worst week $', 'Daily-close DD $', 'Max DD duration days'], rows), '',
         'Subset drawdowns do not add to portfolio drawdown; daily-close figures exclude intratrade equity excursions.', '']
    rows = [[row.era, row.group.replace('_', ' / '), money(row.net_dollars),
             money(row.stress1_net_dollars), money(row.stress2_net_dollars)] for row in frame.itertuples()]
    tables += ['## Fixed cost allowances', '', markdown_table(
        ['Era', 'Group', 'Net at $1.05', 'Net at $2.05', 'Net at $3.05'], rows), '',
        'Extra allowances are sensitivity assumptions, not observed execution costs.', '']
    (STUDY / 'report_tables.md').write_text('\n'.join(tables), encoding='utf-8')

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.1), gridspec_kw={'height_ratios': [1.15, 1]},
                             layout='constrained')
    y = np.arange(6)
    lo = min(-0.05, frame.mean_net_r_ci95_low.min() - 0.015)
    hi = max(0.1, frame.mean_net_r_ci95_high.max() + 0.015)
    maxrisk = frame[frame.group != 'all'].risk_mean.max() * 1.24
    for col, era in enumerate(ERAS):
        p = frame[frame.era == era].set_index('group').reindex(GROUPS)
        ax = axes[0, col]
        colors = ['#137b80' if x >= 0 else '#c16437' for x in p.net_mean_r]
        ax.barh(y, p.net_mean_r, color=colors, height=.56, alpha=.85)
        for pos, row in enumerate(p.itertuples()):
            ax.plot([row.mean_net_r_ci95_low, row.mean_net_r_ci95_high], [pos, pos],
                    color='#293947', linewidth=1.6)
            ax.plot(row.net_mean_r, pos, 'o', color='#293947', markersize=4)
        ax.axvline(0, color='#293947', linewidth=.8)
        ax.set_yticks(y, LABELS)
        ax.invert_yaxis()
        ax.set_xlim(lo, hi)
        ax.set_xlabel('Average net R per trade (bars); 95% interval (lines)')
        ax.set_title('2016-2019' if era == '2016-19' else '2020-September 2026',
                     fontweight='bold', fontsize=13, pad=12)
        ax.grid(axis='x', alpha=.15)
        ax.set_axisbelow(True)
        ax = axes[1, col]
        ax.barh(y, p.risk_mean, color='#647c91', height=.56)
        for pos, val in enumerate(p.risk_mean):
            ax.text(val + maxrisk * .015, pos, f'${val:.0f}', va='center', fontsize=10)
        ax.set_yticks(y, LABELS)
        ax.invert_yaxis()
        ax.set_xlim(0, maxrisk)
        ax.set_xlabel('Mean planned initial risk per one-contract trade ($)')
        ax.grid(axis='x', alpha=.15)
        ax.set_axisbelow(True)
    fig.suptitle('RTL: six market conditions\n'
                 'Uncapped M30 / RR 1 / one MNQ-valued contract / $1.05 per trade',
                 fontsize=16, fontweight='bold')
    fig.savefig(STUDY / 'regime_diagnosis.png', dpi=180, facecolor='white')
    plt.close(fig)
    artifacts = ['summaries.csv', 'report_tables.md', 'regime_diagnosis.png']
    provenance = {name: hashlib.sha256((STUDY / name).read_bytes()).hexdigest()
                  for name in artifacts}
    provenance['renderer_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (STUDY / 'report_artifacts.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print('Wrote report_tables.md and regime_diagnosis.png')


if __name__ == '__main__':
    main()
