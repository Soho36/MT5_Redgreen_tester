"""Figure and tables for the weekly signal gate."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from report_rtl_downtrend_oracle import ERA_TITLES, GRID, INK, MUTED, markdown

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_weekly_gate_20261025'
TRADES = ROOT / 'Reports/rtl_price_structure_20261024/trades.csv'
ERAS = {'2016-19': ('2016-01-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01')}
BASE, GATED, OFF = '#1f1f1e', '#2a78d6', '#ecebe6'


def figure(labels, periods):
    trades = pd.read_csv(TRADES, usecols=['ticket', 'session', 'net_dollars'], parse_dates=['session'])
    data = labels.merge(trades, on='ticket', validate='one_to_one')
    off = periods.loc[periods.series.eq('roll_adjusted') & periods.variant.eq('touch')]
    fig, axes = plt.subplots(2, 1, figsize=(13, 9))
    for ax, (era, (start, stop)) in zip(axes, ERAS.items()):
        part = data.loc[data.era.eq(era)]
        sessions = pd.date_range(start, pd.Timestamp(stop)-pd.Timedelta(days=1), freq='B')
        base = part.groupby('session').net_dollars.sum().reindex(sessions, fill_value=0.).cumsum()
        gated = part.loc[~part['skip|roll_adjusted|touch']].groupby('session').net_dollars.sum().reindex(sessions, fill_value=0.).cumsum()
        for row in off.itertuples():
            left, right = row.off_after_close, row.on_after_close if pd.notna(row.on_after_close) else sessions[-1]
            if right >= pd.Timestamp(start) and left < pd.Timestamp(stop):
                ax.axvspan(max(left, pd.Timestamp(start)), min(right, pd.Timestamp(stop)), color=OFF, zorder=0, lw=0)
        ax.plot(base.index, base, color=BASE, lw=2, label='RTL, every session')
        ax.plot(gated.index, gated, color=GATED, lw=2, label='RTL with weekly gate (touch)')
        for series, color in ((base, BASE), (gated, GATED)):
            ax.annotate(f'${series.iloc[-1]:,.0f}', (series.index[-1], series.iloc[-1]), xytext=(6, 0),
                        textcoords='offset points', va='center', color=INK, fontsize=9)
        ax.set_title(ERA_TITLES[era], color=INK, fontsize=12, loc='left')
        ax.set_ylabel('Cumulative net dollars, one contract', color=MUTED)
        ax.grid(axis='y', color=GRID, lw=.8)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        ax.tick_params(colors=MUTED)
    handles = [plt.Line2D([], [], color=BASE, lw=2, label='RTL, every session'),
               plt.Line2D([], [], color=GATED, lw=2, label='RTL with weekly gate'),
               plt.Rectangle((0, 0), 1, 1, color=OFF, label='weekly gate off')]
    fig.legend(handles=handles, loc='lower center', ncol=3, frameon=False, fontsize=9)
    fig.suptitle('Weekly sell/buy gate: RTL earns more while the weekly chart says sell', x=.06, ha='left',
                 fontsize=14, color=INK)
    fig.text(.06, .935, 'Roll-adjusted M30-based weekly bars; gate switches at the M30 bar where the prior week is broken. '
             'Ledger omission, not an MT5 replay.', fontsize=10, color=MUTED)
    fig.tight_layout(rect=(0, .04, 1, .93))
    fig.savefig(OUT/'gate.png', dpi=150, facecolor='white')
    plt.close(fig)


def tables(rules, periods, decision):
    columns = ['era', 'series', 'variant', 'off_periods', 'median_off_weeks', 'off_bar_share', 'skipped_trades',
               'gain_dollars', 'gain_pct', 'skipped_mean_r', 'retained_mean_r', 'baseline_mean_r', 'losses_avoided',
               'profits_missed', 'retained_daily_dd', 'static_daily_dd', 'static_net_dollars', 'shift_net_p975',
               'share_shifts_net_at_least_rule']
    lines = ['# RTL weekly signal gate: calculated tables', '', rules[columns].round(3).pipe(markdown), '',
             '## Gate-off periods (roll_adjusted, touch)', '',
             periods.loc[periods.series.eq('roll_adjusted') & periods.variant.eq('touch')].pipe(markdown), '',
             '## Protocol decision', '', '```json', json.dumps(decision, indent=2), '```', '']
    (OUT/'report_tables.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    rules = pd.read_csv(OUT/'rules.csv')
    periods = pd.read_csv(OUT/'periods.csv', parse_dates=['off_after_close', 'on_after_close'])
    labels = pd.read_csv(OUT/'trade_labels.csv')
    decision = json.loads((OUT/'decision.json').read_text(encoding='utf-8'))
    figure(labels, periods)
    tables(rules, periods, decision)
    print('Saved gate.png and report_tables.md')


if __name__ == '__main__':
    main()
