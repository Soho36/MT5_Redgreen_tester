"""Render fixed VWAP study comparisons from saved economics."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_vwap_20261025'
DOC = ROOT / 'docs/baseline/rtl-vwap'
ERAS = ('2016-19', '2020-26')
COLORS = ('#2378a0', '#d77b2b')
LABELS = {'skip_below':'Skip below', 'skip_far_below':'Skip far below',
          'skip_far_above':'Skip far above', 'skip_churn':'Skip crossings'}


def main():
    sums = pd.read_csv(OUT/'summaries.csv').query("variant == 'full_hlc3'")
    policies = pd.read_csv(OUT/'policies.csv').query("variant == 'full_hlc3'")
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    for ax, dimension, categories, title in (
        (axes[0,0], 'distance', ['far_below','below','above','far_above'], 'Distance from session VWAP'),
        (axes[0,1], 'churn', ['churn','orderly'], 'Repeated VWAP crossings (descriptive)')):
        xs = np.arange(len(categories))
        for k, era in enumerate(ERAS):
            part = sums.loc[sums.era.eq(era)&sums.dimension.eq(dimension)].set_index('category').loc[categories]
            ax.bar(xs+(k-.5)*.36, part.net_mean_r, .36, color=COLORS[k], label=era)
        ax.axhline(0, color='#555555', lw=.8)
        ax.set_xticks(xs, [c.replace('_',' ').title() for c in categories])
        ax.set_ylabel('Mean net R per trade')
        ax.set_title(title, loc='left', fontsize=12, fontweight='bold')
        ax.grid(axis='y', alpha=.18)
        ax.legend(frameon=False)
    for ax, era, color in zip(axes[1], ERAS, COLORS):
        part = policies.loc[policies.era.eq(era)]
        baseline = part.loc[part.curve.eq('baseline')].iloc[0]
        ax.scatter([baseline.daily_close_dd/1000], [baseline.net_dollars/1000],
                   marker='*', s=180, color='#202020', label='Baseline', zorder=4)
        ax.annotate('Baseline', (baseline.daily_close_dd/1000, baseline.net_dollars/1000),
                    xytext=(7,5), textcoords='offset points', fontsize=9)
        # The line shows uniform fractional scaling, a diagnostic comparator.
        ax.plot([0, baseline.daily_close_dd/1000], [0,baseline.net_dollars/1000],
                color='#777777', ls='--', alpha=.6)
        for policy, label in LABELS.items():
            row = part.loc[part.policy.eq(policy)&part.curve.eq('retained')].iloc[0]
            x, y = row.daily_close_dd/1000, row.net_dollars/1000
            ax.scatter([x], [y], color=color, s=45)
            offsets = {'skip_below':(-5,14),'skip_far_above':(7,-22),
                       'skip_far_below':(10,8),'skip_churn':(-90,20)}
            ax.annotate(label, (x,y), xytext=offsets[policy], textcoords='offset points', fontsize=9,
                        arrowprops=dict(arrowstyle='-', color='#777777', lw=.7))
        ax.set_title(f'{era}: profit and drawdown tradeoff', loc='left', fontsize=12, fontweight='bold')
        ax.set_xlabel('Daily-close maximum drawdown ($ thousands)')
        ax.set_ylabel('Net profit ($ thousands)')
        ax.margins(.25)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.grid(alpha=.18)
    fig.suptitle('RTL and session VWAP: exploratory ledger study', fontsize=17, fontweight='bold')
    fig.supxlabel('One MNQ-valued contract; $1.05 cost. Far = more than one A20 from VWAP.\n'
                  'Dashed line: uniformly reduced baseline. Submission labels; unknowns retained.\n'
                  'Historical associations; omission is not a full strategy replay.', fontsize=10)
    fig.savefig(DOC/'vwap_summary.png', dpi=160, facecolor='white')
    plt.close(fig)
    print(DOC/'vwap_summary.png')


if __name__ == '__main__':
    main()
