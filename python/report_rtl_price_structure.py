"""Readable tables and static figures for the frozen RTL structure diagnostic."""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_price_structure_20261024'
GROUPS = ['low_eff_high_overlap', 'low_eff_other_overlap',
          'other_eff_high_overlap', 'other_eff_other_overlap']
LABELS = ['Low efficiency / high overlap', 'Low efficiency / other overlap',
          'Other efficiency / high overlap', 'Other efficiency / other overlap']
ERAS = ['2016-19', '2020-26']
COLORS = ['#b4652d', '#147d83']


def read(name):
    frame = pd.read_csv(OUT / name)
    if 'timeframe' in frame:
        frame['timeframe'] = frame.timeframe.str.upper()
    return frame


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '|' + '|'.join(['---'] * len(headers)) + '|'] +
                     ['| ' + ' | '.join(str(x) for x in row) + ' |' for row in rows])


def money(value):
    return f'{value:,.2f}'


def frame_table(frame, columns=None):
    if columns is not None:
        frame = frame.loc[:, columns]
    def fmt(value):
        if pd.isna(value):
            return '—'
        if isinstance(value, (float, np.floating)):
            return f'{value:,.4f}'
        return str(value)
    return table(list(frame.columns), [[fmt(v) for v in row] for row in frame.itertuples(index=False, name=None)])


def main():
    summary = read('summaries.csv')
    uncertainty = read('uncertainty.csv')
    omission = read('omission.csv')
    named = read('named_wick_summary.csv').query('window == 20')
    wick = read('wick_summary.csv')
    thresholds = read('thresholds.csv')
    sessions = read('session_pnl.csv')
    sessions['session'] = pd.to_datetime(sessions.session)
    primary = summary.loc[summary.window == 20]
    parts = ['# RTL price structure: calculated tables', '',
             'Frozen definitions: docs/baseline/rtl-price-structure/PROTOCOL.md. '
             '2020-26 ends September 30; all figures are exploratory.', '']
    for tf in ['D1', 'M30']:
        for era in ERAS:
            p = primary.loc[(primary.timeframe == tf) & (primary.era == era)].set_index('group')
            rows = []
            for g in GROUPS + ['all']:
                r = p.loc[g]
                rows.append([g, f'{r.trades:,.0f}', f'{r.active_weeks:.0f}', money(r.net_dollars),
                             f'{r.dollar_pf:.3f}', f'{r.gross_mean_r:+.4f}', f'{r.net_mean_r:+.4f}',
                             money(r.closed_trade_dd), money(r.daily_close_dd)])
            parts += [f'## {tf}, 20 bars, {era}', '', table(
                ['Group', 'Trades', 'Active weeks', 'Net $', 'PF', 'Gross R/trade', 'Net R/trade',
                 'Closed DD $', 'Daily DD $'], rows), '']
    parts += ['## Calibration thresholds', '', frame_table(thresholds), '']
    rows = []
    for r in summary.loc[summary.group == GROUPS[0]].itertuples():
        rows.append([r.timeframe, r.window, r.era, f'{r.trades:,.0f}', money(r.net_dollars),
                     f'{r.net_mean_r:+.4f}', f'{r.dollar_pf:.3f}'])
    parts += ['## Fixed 10/20/40-window sensitivity: main candidate', '', table(
        ['Timeframe', 'Window', 'Era', 'Trades', 'Net $', 'Net R/trade', 'PF'], rows), '']
    rows = []
    for r in wick.itertuples():
        rows.append([r.timeframe, r.era, r.group, r.wick_state, f'{r.trades:,.0f}',
                     money(r.net_dollars), f'{r.net_mean_r:+.4f}', f'{r.mean_wick:.3f}'])
    parts += ['## Wick diagnostic: all eight cells', '', table(
        ['Timeframe', 'Era', 'Group', 'Wick state', 'Trades', 'Net $', 'Net R/trade', 'Mean wick'], rows), '']
    parts += ['## Named M30 wick subsets', '', frame_table(named, [
                  'timeframe', 'era', 'group', 'trades', 'active_weeks', 'net_dollars',
                  'net_mean_r', 'risk_mean', 'commission_mean_r']), '',
              '## Omission and static exposure controls', '', frame_table(omission, [
                  'timeframe', 'era', 'subset', 'curve', 'trades', 'net_dollars',
                  'closed_trade_dd', 'daily_close_dd', 'holding_hours']), '',
              '## Paired four-week bootstrap uncertainty', '', frame_table(uncertainty, [
                  'timeframe', 'era', 'group', 'mean_net_r_ci95_low', 'mean_net_r_ci95_high',
                  'difference_net_r', 'difference_net_r_ci95_low', 'difference_net_r_ci95_high']), '',
              '## Roll-excluded main candidate', '',
              frame_table(read('roll_sensitivity.csv').query('group == "low_eff_high_overlap"'), [
                  'timeframe', 'window', 'era', 'trades', 'active_weeks', 'net_dollars', 'net_mean_r']), '',
              '## Circular-placement controls (matched holding exposure)', '',
              frame_table(read('placement_summary.csv'), [
                  'timeframe', 'era', 'subset', 'actual_net_dollars', 'actual_daily_close_dd',
                  'exposure_scaled_net_dollars_p50', 'exposure_scaled_daily_close_dd_p50',
                  'matched_fraction_net_at_least_actual', 'matched_fraction_dd_at_most_actual']), '',
              'Ledger omission is a diagnostic, not a complete executable strategy replay. '
              'Drawdowns exclude intratrade equity. Circular shifts are dependent placement controls, '
              'not a randomized significance test.', '']
    (OUT / 'report_tables.md').write_text('\n'.join(parts), encoding='utf-8')

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.titleweight': 'bold'})
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), layout='constrained',
                             gridspec_kw={'height_ratios': [1, 1.15]})
    for col, tf in enumerate(['D1', 'M30']):
        ax = axes[0, col]
        for k, era in enumerate(ERAS):
            p = primary.loc[(primary.timeframe == tf) & (primary.era == era)].set_index('group').loc[GROUPS]
            u = uncertainty.loc[(uncertainty.timeframe == tf) & (uncertainty.era == era)].set_index('group').loc[GROUPS]
            y = np.arange(4) + (k - .5) * .22
            ax.hlines(y, u.mean_net_r_ci95_low, u.mean_net_r_ci95_high, color=COLORS[k], alpha=.65, lw=2)
            ax.scatter(p.net_mean_r, y, color=COLORS[k], s=36, label=era, zorder=3)
        ax.axvline(0, color='#59636e', lw=1)
        ax.set_yticks(np.arange(4), [x.replace(' / ', '\n') for x in LABELS])
        ax.set_ylim(3.5, -.65)
        ax.grid(axis='x', alpha=.16)
        ax.set_title(f'{tf}: net R per trade by structure')
        ax.set_xlabel('Planned-risk R per trade; 95% block-bootstrap intervals')
        ax.legend(loc='upper right', frameon=False, ncol=2)
        ax = axes[1, col]
        p = sessions.loc[(sessions.timeframe == tf) & (sessions.era == ERAS[1]) &
                         (sessions.subset == GROUPS[0])]
        for curve, label, color, style in [
                ('baseline', 'All RTL', '#344256', '-'),
                ('omitted', 'Omit low efficiency + high overlap', '#147d83', '-'),
                ('static_holding_scaled', 'Static, same retained holding exposure', '#b4652d', '--')]:
            q = p.loc[p.curve == curve].sort_values('session')
            assert len(q) > 0, (tf, curve)
            assert q.session.is_unique, (tf, curve)
            dates = [q.session.iloc[0] - pd.Timedelta(days=1), *q.session]
            ax.plot(dates, np.r_[0., q.net_dollars.cumsum()], label=label, color=color, ls=style, lw=1.6)
        ax.set_title(f'{tf}: recent-period omission diagnostic')
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'${x / 1000:,.0f}k'))
        ax.set_ylabel('Cumulative realized net dollars')
        ax.grid(alpha=.16)
        ax.legend(loc='upper left', fontsize=8, frameon=False)
    fig.suptitle('RTL price structure | fixed 20-bar definitions\n'
                 'Pre-2016 price calibration; current uncapped M30 strategy', fontsize=17)
    fig.supxlabel('2020–26 ends September 30. Net of $1.05/trade. Historical diagnosis; '
                  'omission curves are not full strategy replays.', fontsize=10)
    fig.savefig(OUT / 'structure_diagnosis.png', dpi=160)
    plt.close(fig)
    artifacts = ['report_tables.md', 'structure_diagnosis.png']
    manifest = {'report_program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'outputs_sha256': {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
                                   for name in artifacts}}
    (OUT / 'report_artifacts.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('Saved structure tables and diagnostic figure.')


if __name__ == '__main__':
    main()
