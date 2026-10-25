"""Render the frozen MA study; no setting selection or new trading rules."""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'Reports/rtl_ma_agreement_20261024'
STATES = ['up', 'down', 'mixed']
ERAS = ['2016-19', '2020-26']
POLICIES = ['skip_mixed', 'skip_down', 'only_up']
LABELS = {'skip_mixed': 'Skip mixed', 'skip_down': 'Skip down', 'only_up': 'Only up'}


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '|'+ '|'.join(['---']*len(headers))+'|']+
        ['| '+' | '.join(str(x).replace('|', ' / ') for x in row)+' |' for row in rows])


def main():
    summaries = pd.read_csv(OUT/'summaries.csv')
    policies = pd.read_csv(OUT/'policies.csv')
    uncertainty = pd.read_csv(OUT/'uncertainty.csv')
    placement = pd.read_csv(OUT/'placement_summary.csv')
    rolls = pd.read_csv(OUT/'roll_summary.csv')
    yearly = pd.read_csv(OUT/'yearly.csv')
    trades = pd.read_csv(OUT/'trades.csv')
    parts = ['# RTL MA agreement: calculated tables', '',
        'Primary: M30 SMA 5/10/20/40/80/160/200, five votes; per-length flat bands '
        'calibrated on pre-2016 prices. Recent period ends September 30, 2026. '
        'One MNQ-valued contract, $1.05 costs. This is ledger omission, not a full gated-strategy replay.', '']
    rows = []
    for r in summaries.loc[summaries.dimension.eq('state')].itertuples():
        rows.append([r.variant, r.era, r.category, f'{r.trades:,}', f'{r.active_weeks:,}',
                     f'{r.net_dollars:,.2f}', f'{r.net_mean_r:+.4f}', f'{r.dollar_pf:.3f}',
                     f'{r.daily_close_dd:,.2f}', f'{r.risk_mean:.2f}'])
    parts += ['## States and all frozen variants', '', table(
        ['Variant', 'Era', 'State', 'Trades', 'Active weeks', 'Net $', 'Mean net R', 'PF', 'Daily-close DD $', 'Mean risk $'], rows), '']
    rows = []
    for year, group in yearly.loc[yearly.variant.eq('primary')].groupby('year', sort=True):
        group = group.set_index('state')
        rows.append([str(year)+(' (Jan-Sep)' if year == 2026 else ''),
                     *[f'{group.loc[state, "net_dollars"]:,.2f}' for state in ['all', *STATES]],
                     *[f'{group.loc[state, "net_mean_r"]:+.4f}' for state in STATES]])
    parts += ['## Primary annual outcomes', '', table(
        ['Year', 'All net $', 'Up net $', 'Down net $', 'Mixed net $', 'Up mean R', 'Down mean R', 'Mixed mean R'], rows), '']
    rows = []
    for r in policies.loc[policies.variant.eq('primary')].itertuples():
        rows.append([r.era, LABELS[r.policy], r.curve, f'{r.trades:,}', f'{r.net_dollars:,.2f}',
            f'{r.net_mean_r:+.4f}', f'{r.daily_close_dd:,.2f}', f'{r.closed_trade_dd:,.2f}',
            f'{r.losses_avoided:,.2f}', f'{r.profits_missed:,.2f}', f'{100*r.retained_holding_fraction:.1f}%'])
    parts += ['## Primary policies and same-holding exposure controls', '',
        'Avoided losses and missed profits describe each policy, repeated across its comparator rows. '
        'Fractional sizing is a diagnostic, not an executable one-contract rule. '
        'Scaled holding time denotes equivalent contract exposure, not shorter physical trade durations.', '', table(
        ['Era', 'Policy', 'Curve', 'Trades', 'Net $', 'Mean net R', 'Daily DD $', 'Closed DD $',
         'Losses avoided $', 'Profits missed $', 'Retained holding'], rows), '']
    rows = []
    for r in policies.loc[policies.curve.eq('retained')].itertuples():
        rows.append([r.variant, r.era, LABELS[r.policy], r.trades, f'{r.net_dollars:,.2f}',
                     f'{r.net_mean_r:+.4f}', f'{r.daily_close_dd:,.2f}', f'{r.skipped_net_dollars:,.2f}'])
    parts += ['## Policy sensitivity (all frozen variants)', '', table(
        ['Variant', 'Era', 'Policy', 'Retained trades', 'Retained net $', 'Retained mean R', 'Daily DD $', 'Skipped net $'], rows), '']
    for dimension in ['context', 'context_state', 'state_age', 'fill_state', 'exit_state',
                      'firstup_timing_state', 'up_reentry_age']:
        rows = []
        for r in summaries.loc[summaries.dimension.eq(dimension)].itertuples():
            rows.append([r.era, r.category, r.trades, r.active_episodes, r.active_weeks,
                         f'{r.positive_net_dollars:,.2f}', f'{r.loss_dollars:,.2f}',
                         f'{r.net_dollars:,.2f}', f'{r.net_mean_r:+.4f}'])
        parts += ['## '+dimension.replace('_', ' '), '', table(
            ['Era', 'Category', 'Trades', 'Episodes', 'Weeks', 'Winning $', 'Losses $', 'Net $', 'Mean net R'], rows), '']
    rows = []
    primary = trades.loc[trades.variant.eq('primary')]
    for era in ERAS:
        nonup = primary.loc[primary.era.eq(era) & primary.state.ne('up')]
        winning = nonup.net_dollars.clip(lower=0).sum()
        losing = -nonup.net_dollars.clip(upper=0).sum()
        for category, g in nonup.groupby('firstup_timing'):
            pos, neg = g.net_dollars.clip(lower=0).sum(), -g.net_dollars.clip(upper=0).sum()
            rows.append([era, category, len(g), f'{g.net_dollars.sum():,.2f}', f'{pos:,.2f}', f'{neg:,.2f}',
                         f'{100*pos/winning:.1f}%', f'{100*neg/losing:.1f}%',
                         f'{g.next_up_delay_bars.median():.1f}', f'{g.next_up_move_atr.median():+.3f}'])
    parts += ['## Trades omitted by only-up: when consensus returned', '',
        'First-up timing and the following move are retrospective. These are full trade outcomes; '
        'they do not estimate PnL achievable by entering at confirmation. No-observed-up is censored.', '', table(
        ['Era', 'Timing', 'Trades', 'Net $', 'Winning $', 'Losses $', 'Share missed winning $',
         'Share avoided losing $', 'Median bars to up', 'Median move to up / initial A20'], rows), '']
    rows = []
    for r in uncertainty.itertuples():
        rows.append([r.era, r.group, f'{r.net_mean_r:+.4f}',
                     f'[{r.mean_net_r_ci95_low:+.4f}, {r.mean_net_r_ci95_high:+.4f}]',
                     f'[{r.mean_net_r_ci98_33_low:+.4f}, {r.mean_net_r_ci98_33_high:+.4f}]',
                     f'{r.difference_net_r:+.4f}',
                     f'[{r.difference_net_r_ci98_33_low:+.4f}, {r.difference_net_r_ci98_33_high:+.4f}]'])
    parts += ['## Paired four-week block uncertainty (primary)', '',
        '10,000 draws per era. The 98.33% intervals adjust only the three primary state comparisons '
        'within that era, not all previously inspected research.', '', table(
        ['Era', 'State', 'Mean R', 'Mean 95% CI', 'Mean 98.33% CI', 'State minus complement R', 'Difference 98.33% CI'], rows), '']
    rows = []
    for r in placement.itertuples():
        rows.append([r.era, LABELS[r.policy], f'{100*r.fraction_shifts_beaten_net:.1f}%',
            f'{100*r.fraction_shifts_beaten_dd:.1f}%', f'{100*r.fraction_scaled_shifts_beaten_net:.1f}%',
            f'{100*r.fraction_scaled_shifts_beaten_dd:.1f}%'])
    parts += ['## Circular-placement controls', '',
        'Percent of 2,000 shifted masks beaten by the actual policy, separately by dollars and drawdown. '
        'Not a combined significance test; shifts preserve trade-order runs, not calendar duration or volatility.', '', table(
        ['Era', 'Policy', 'Raw net', 'Raw DD', 'Same-holding net', 'Same-holding DD'], rows), '']
    rows = []
    for r in rolls.itertuples():
        rows.append([r.variant, r.era, r.state, r.trades, f'{r.net_dollars:,.2f}', f'{r.net_mean_r:+.4f}'])
    parts += ['## Common 201-observation roll-clean sensitivity', '', table(
        ['Variant', 'Era', 'State', 'Trades', 'Net $', 'Mean net R'], rows), '']
    (OUT/'report_tables.md').write_text('\n'.join(parts), encoding='utf-8')

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 3, figsize=(17, 9))
    colors = ['#247d85', '#bc624e', '#8c8c9b']
    policy_colors = ['#76629f', '#c08636', '#287fba']
    for row, era in enumerate(ERAS):
        part = summaries.loc[summaries.variant.eq('primary') & summaries.era.eq(era)
                             & summaries.dimension.eq('state')].set_index('category').loc[STATES]
        ax = axes[row, 0]
        ax.bar(STATES, part.net_dollars/1000, color=colors)
        ax.axhline(0, color='#777777', linewidth=.8)
        for j, value in enumerate(part.net_dollars/1000):
            ax.annotate(f'{value:+.1f}', (j, value), xytext=(0, 5 if value >= 0 else -5),
                        textcoords='offset points', ha='center', va='bottom' if value >= 0 else 'top')
        ax.margins(y=.25)
        ax.set_ylabel(f'{era}\nNet dollars, thousands')
        if row == 0:
            ax.set_title('Profit by submission state', fontweight='bold')
        ax = axes[row, 1]
        interval = uncertainty.loc[uncertainty.era.eq(era)].set_index('group').loc[STATES]
        center = interval.net_mean_r.to_numpy()
        bounds = np.vstack([center-interval.mean_net_r_ci95_low, interval.mean_net_r_ci95_high-center])
        ax.errorbar(np.arange(3), center, yerr=bounds, fmt='o', color='#283c4d', capsize=6)
        ax.set_xticks(np.arange(3), STATES)
        ax.axhline(0, color='#777777', linewidth=.8)
        ax.set_ylabel('Mean net R per trade')
        if row == 0:
            ax.set_title('Mean R with nominal 95% intervals', fontweight='bold')
        ax = axes[row, 2]
        p = policies.loc[policies.variant.eq('primary') & policies.era.eq(era)]
        baseline = p.loc[p.curve.eq('baseline')].iloc[0]
        ax.scatter(baseline.daily_close_dd/1000, baseline.net_dollars/1000, c='#263a46', marker='*', s=150, label='Baseline', zorder=5)
        for policy, color in zip(POLICIES, policy_colors):
            selected = p.loc[p.policy.eq(policy)].set_index('curve')
            retained, scaled = selected.loc['retained'], selected.loc['static_holding_scaled']
            ax.plot([scaled.daily_close_dd/1000, retained.daily_close_dd/1000],
                    [scaled.net_dollars/1000, retained.net_dollars/1000], color=color, alpha=.45, linewidth=1.2)
            ax.scatter(scaled.daily_close_dd/1000, scaled.net_dollars/1000, facecolors='none', edgecolors=color, marker='s', s=45)
            ax.scatter(retained.daily_close_dd/1000, retained.net_dollars/1000, c=color, s=55, label=LABELS[policy])
        ax.set_xlabel('Daily-close drawdown, $ thousands')
        ax.set_ylabel('Net profit, $ thousands')
        ax.margins(.15)
        if row == 0:
            ax.set_title('Profit and drawdown after omission', fontweight='bold')
        if row == 1:
            ax.legend(frameon=False, ncol=2, loc='upper center', bbox_to_anchor=(.5, -.23), fontsize=9)
    fig.suptitle('RTL: does agreement among moving-average slopes identify trades to avoid?\n'
        'M30; fixed seven-length primary definition; one contract after $1.05 costs', fontsize=16)
    fig.text(.5, .025, 'Right: filled dots are retained ledgers after omission; hollow squares are baseline scaled to the same holding exposure.\n'
        'Historical diagnostics, not a full strategy replay. Recent data ends September 30, 2026.', ha='center', fontsize=10)
    fig.tight_layout(rect=[0, .10, 1, .92], h_pad=3, w_pad=2.5)
    fig.savefig(OUT/'ma_agreement.png', dpi=160)
    plt.close(fig)
    names = ['report_tables.md', 'ma_agreement.png']
    manifest = dict(report_program_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        outputs_sha256={name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names})
    (OUT/'report_artifacts.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print('Saved MA tables and figure.')


if __name__ == '__main__':
    main()
