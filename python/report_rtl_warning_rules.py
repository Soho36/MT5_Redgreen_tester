"""Figure and tables for the warning-based skip rules."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from report_rtl_downtrend_oracle import COLORS, ERA_TITLES, GRID, INK, MUTED, markdown

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_warning_rules_20261025'
GROUPS = (('Rule A\npullback stop', 'A|', 'A|rise_5|M20', None, '#4a4a46'),
          ('Rule B, 2%\nzigzag stop', 'B|0.02|', 'B|0.02|rise_5', 'zigzag|0.02', COLORS[.02]),
          ('Rule B, 3%\nzigzag stop', 'B|0.03|', 'B|0.03|rise_5', 'zigzag|0.03', COLORS[.03]),
          ('Rule B, 5%\nzigzag stop', 'B|0.05|', 'B|0.05|rise_5', 'zigzag|0.05', COLORS[.05]))


def figure(rules):
    primary = rules.loc[rules.series.eq('roll_adjusted')]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.8), sharey=True)
    for ax, era in zip(axes, ERA_TITLES):
        part = primary.loc[primary.era.eq(era)].set_index('rule')
        ax.axhline(0, color=MUTED, lw=1.2)
        for position, (_, prefix, main, plain, color) in enumerate(GROUPS):
            variants = part.loc[part.index.str.startswith(prefix) & (part.index != main), 'gain_pct']
            ax.plot([position-.12]*len(variants), variants, 'o', ms=5, color='#b9b8b1', zorder=2)
            ax.plot(position, part.loc[main, 'gain_pct'], 'o', ms=11, color=color, mec='white', mew=2, zorder=4)
            ax.annotate(f"{part.loc[main, 'gain_pct']:+.0f}%", (position, part.loc[main, 'gain_pct']), xytext=(10, 0),
                        textcoords='offset points', va='center', color=INK, fontsize=9)
            if plain:
                ax.plot(position+.18, part.loc[plain, 'gain_pct'], 'D', ms=8, mfc='white', mec=color, mew=2, zorder=3)
        ax.set_xticks(range(len(GROUPS)), [g[0] for g in GROUPS])
        ax.set_xlim(-.6, len(GROUPS)-.4)
        ax.set_title(ERA_TITLES[era], color=INK, fontsize=12, loc='left')
        ax.grid(axis='y', color=GRID, lw=.8)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        ax.tick_params(colors=MUTED)
    axes[0].set_ylabel('Change in net profit vs trading every session (%)', color=MUTED)
    handles = [plt.Line2D([], [], ls='', marker='o', ms=10, color=MUTED, mec='white', label='primary rule'),
               plt.Line2D([], [], ls='', marker='o', ms=5, color='#b9b8b1', label='other bounce signals / timeouts'),
               plt.Line2D([], [], ls='', marker='D', ms=8, mfc='white', mec=MUTED, mew=2, label='plain live zigzag')]
    fig.legend(handles=handles, loc='lower center', ncol=3, frameon=False, fontsize=9)
    fig.suptitle('Warning-based skip rules: the bounce warning repairs the zigzag, but nothing beats trading every session',
                 x=.06, ha='left', fontsize=13, color=INK)
    fig.text(.06, .905, 'Roll-adjusted daily closes; one MNQ contract, $1.05 per trade; ledger omission, not an MT5 replay.',
             fontsize=10, color=MUTED)
    fig.tight_layout(rect=(0, .06, 1, .9))
    fig.savefig(OUT/'rules.png', dpi=150, facecolor='white')
    plt.close(fig)


def tables(rules, decision):
    lines = ['# RTL warning-based skip rules: calculated tables', '']
    columns = ['era', 'rule', 'stops', 'median_stop_sessions', 'share_resumed_by_bounce', 'share_zero_length',
               'skipped_session_share', 'skipped_trades', 'gain_dollars', 'gain_pct', 'skipped_mean_r', 'retained_mean_r',
               'baseline_mean_r', 'retained_daily_dd', 'static_daily_dd', 'static_net_dollars', 'shift_net_p975',
               'share_shifts_net_at_least_rule']
    for series in ('roll_adjusted', 'raw'):
        lines += [f'## {series}', '', rules.loc[rules.series.eq(series), columns].round(3).pipe(markdown), '']
    lines += ['## Protocol decision', '', '```json', json.dumps(decision, indent=2), '```', '']
    (OUT/'report_tables.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    rules = pd.read_csv(OUT/'rules.csv')
    decision = json.loads((OUT/'decision.json').read_text(encoding='utf-8'))
    figure(rules)
    tables(rules, decision)
    print('Saved rules.png and report_tables.md')


if __name__ == '__main__':
    main()
