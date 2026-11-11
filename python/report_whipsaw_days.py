"""Chart and markdown tables for the whipsaw-day study, from the saved summary files."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from prepare_whipsaw_days import DOC, RUN

# Reference palette of the chart guidelines: one accent hue, the rest in recessive gray.
SURFACE, INK, SECONDARY, MUTED, GRID, AXIS = '#fcfcfb', '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'
ACCENT = '#2a78d6'
MIN_EVENTS = 20      # a whipsaw point is drawn for size groups with at least this many whipsaw days
PRIMARY = 'abs_move_1'
LABELS = {'abs_move_1': "next session's move", 'range_1': "next session's range",
          'trend_1': 'share of trend days, next session', 'signed_1': 'signed move, next session (+ = up)',
          'abs_move_3': 'move over the next three sessions', 'range_3': 'range over the next three sessions',
          'trend_3': 'share of trend spans, next three', 'signed_3': 'signed move, next three (+ = up)',
          'gg_net': 'GG net $, next session', 'gg_r': 'GG net R, next session',
          'rtl_net': 'RTL net $, next session', 'rtl_r': 'RTL net R, next session'}
EVENT_NAMES = {'whipsaw': 'Whipsaw (3+ swings of 0.75 x ATR20)', 'looser': 'Looser (4+ swings of 0.5 x ATR20)',
               'stricter': 'Stricter (3+ swings of 1.0 x ATR20)', 'outside_inside': 'Outside day closing back inside'}


def pick(summary, **conditions):
    mask = np.ones(len(summary), bool)
    for column, value in conditions.items():
        mask &= summary[column].eq(value).to_numpy()
    assert mask.sum() == 1, conditions
    return summary.loc[mask].iloc[0]


def style(ax, title):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc='left', fontsize=10.5, color=INK, fontweight='bold', pad=10)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=8.5, length=0)
    ax.set_axisbelow(True)


def chart(summary, groups, cross):
    plt.rcParams['font.family'] = ['Segoe UI', 'DejaVu Sans']
    fig, (left, right) = plt.subplots(1, 2, figsize=(10.4, 4.1), dpi=150, gridspec_kw=dict(width_ratios=[1, 1.08], wspace=.62))
    fig.patch.set_facecolor(SURFACE)

    style(left, 'After a whipsaw day the next session moves more')
    left.grid(axis='y', color=GRID, linewidth=.8)
    left.plot(groups.other_size, groups.other_mean, color=MUTED, linewidth=2, marker='o', markersize=6.5,
              markeredgecolor=SURFACE, markeredgewidth=1.5, label='other days', solid_capstyle='round', zorder=2)
    shown = groups.loc[groups.events >= MIN_EVENTS]
    left.vlines(shown.event_size, shown.event_mean - 1.96 * shown.event_se, shown.event_mean + 1.96 * shown.event_se,
                color=ACCENT, linewidth=1.2, alpha=.55, zorder=3)
    left.plot(shown.event_size, shown.event_mean, color=ACCENT, linewidth=2, marker='o', markersize=7,
              markeredgecolor=SURFACE, markeredgewidth=1.5, label='whipsaw days', solid_capstyle='round', zorder=4)
    left.set_xlabel('size of the day (its range, in normal-day ranges)', fontsize=9, color=SECONDARY)
    left.set_ylabel("next session's open-to-close move\n(in normal-day ranges)", fontsize=9, color=SECONDARY)
    left.set_xlim(.3, 2.62)
    left.set_ylim(0, 1.35)
    left.legend(loc='upper left', frameon=False, fontsize=8.5, labelcolor=SECONDARY, handlelength=1.6, borderaxespad=.2)
    last = shown.iloc[-1]
    left.annotate('whipsaw days', (last.event_size, last.event_mean), xytext=(-6, 13), textcoords='offset points',
                  ha='right', fontsize=8.5, color=SECONDARY)
    tail = groups.iloc[-1]
    left.annotate('other days', (tail.other_size, tail.other_mean), xytext=(0, -15), textcoords='offset points',
                  ha='center', fontsize=8.5, color=SECONDARY)

    style(right, 'Whipsaw days minus equally large days')
    rows = [('NQ 2016-19', pick(summary, sample='2016-19', variant='all', event='whipsaw', outcome=PRIMARY), 'matched'),
            ('NQ 2020-26', pick(summary, sample='2020-26', variant='all', event='whipsaw', outcome=PRIMARY), 'matched'),
            ('NQ 2016-26', pick(summary, sample='2016-26', variant='all', event='whipsaw', outcome=PRIMARY), 'matched'),
            ('   corrected for exact size', pick(summary, sample='2016-26', variant='all', event='whipsaw', outcome=PRIMARY), 'corrected'),
            ('   without news sessions', pick(summary, sample='2016-26', variant='news_free', event='whipsaw', outcome=PRIMARY), 'matched'),
            None,
            ('looser rule, NQ 2016-26', pick(summary, sample='2016-26', variant='all', event='looser', outcome=PRIMARY), 'matched'),
            ('stricter rule, NQ 2016-26', pick(summary, sample='2016-26', variant='all', event='stricter', outcome=PRIMARY), 'matched')]
    if cross is not None:
        rows.append(None)
        for name, sample in (('ES', '2016-26'), ('YM', '2016-26'), ('RTY', '2018-26')):
            rows.append((f'{name} {sample}', pick(cross, instrument=name, sample=sample, variant='all', event='whipsaw',
                                                 outcome=PRIMARY), 'matched'))
    y, ticks, names = 0.0, [], []
    for row in rows:
        if row is None:
            y -= .55
            continue
        name, values, kind = row
        right.plot([values[kind + '_lo'], values[kind + '_hi']], [y, y], color=ACCENT, linewidth=2, solid_capstyle='round', zorder=3)
        right.plot(values[kind + '_diff'], y, 'o', color=ACCENT, markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=4)
        ticks.append(y)
        names.append(name)
        y -= 1
    right.axvline(0, color=AXIS, linewidth=1.2, zorder=1)
    right.grid(axis='x', color=GRID, linewidth=.8)
    right.set_yticks(ticks, names)
    right.tick_params(axis='y', labelsize=8.5, labelcolor=SECONDARY)
    for label in right.get_yticklabels():
        label.set_horizontalalignment('left')
    right.tick_params(axis='y', pad=118)
    right.set_ylim(y + .4, .7)
    right.set_xlim(-.12, .82)
    right.set_xlabel("difference in the next session's move, with 95% interval\n(in normal-day ranges; right of zero = more after a whipsaw day)",
                     fontsize=9, color=SECONDARY)
    fig.subplots_adjust(left=.075, right=.985, top=.9, bottom=.2)
    (DOC / 'img').mkdir(exist_ok=True)
    fig.savefig(DOC / 'img' / 'whipsaw_days.png', facecolor=SURFACE)
    plt.close(fig)


def number(value, digits=2, sign=False):
    value = round(float(value), digits) + 0.0       # no "-0.00"
    return f'{value:+.{digits}f}' if sign and value else f'{value:.{digits}f}'


def span(row, kind, digits=2):
    return f"{number(row[kind + '_diff'], digits, True)} ({number(row[kind + '_lo'], digits, True)} to {number(row[kind + '_hi'], digits, True)})"


def table(header, lines):
    return '\n'.join(['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)] + ['| ' + ' | '.join(line) + ' |' for line in lines])


def tables(summary, cross, review):
    out = ['### Next session, all sessions (NQ)', '']
    lines = []
    for sample in ('2016-19', '2020-26', '2016-26', '2010-15'):
        r = pick(summary, sample=sample, variant='all', event='whipsaw', outcome=PRIMARY)
        lines.append([sample, str(int(r.events_used)), number(r.event_mean), number(r.control_mean), number(r.other_sessions_mean),
                      span(r, 'matched'), span(r, 'corrected')])
    out += [table(['Period', 'Whipsaw days', 'After whipsaw', 'After equally large days', 'After all other days',
                   'Difference (95% interval)', 'Corrected for exact size'], lines), '']

    out += ['### Without scheduled news (NQ)', '']
    lines = []
    for sample in ('2016-19', '2020-26', '2016-26'):
        r = pick(summary, sample=sample, variant='news_free', event='whipsaw', outcome=PRIMARY)
        lines.append([sample, str(int(r.events_used)), number(r.event_mean), number(r.control_mean), span(r, 'matched'), span(r, 'corrected')])
    out += [table(['Period', 'Whipsaw days', 'After whipsaw', 'After equally large days', 'Difference (95% interval)',
                   'Corrected for exact size'], lines), '']

    out += ['### Other measures, 2016-26 (NQ)', '']
    lines = []
    for outcome in ('range_1', 'trend_1', 'signed_1', 'abs_move_3', 'range_3', 'signed_3'):
        r = pick(summary, sample='2016-26', variant='all', event='whipsaw', outcome=outcome)
        lines.append([LABELS[outcome], number(r.event_mean), number(r.control_mean), span(r, 'matched')])
    out += [table(['Measure', 'After whipsaw', 'After equally large days', 'Difference (95% interval)'], lines), '']

    out += ['### Other definitions, next session move, 2016-26 (NQ)', '']
    lines = []
    for event in ('whipsaw', 'looser', 'stricter', 'outside_inside'):
        r = pick(summary, sample='2016-26', variant='all', event=event, outcome=PRIMARY)
        lines.append([EVENT_NAMES[event], str(int(r.events_used)), number(r.event_mean), number(r.control_mean), span(r, 'matched'),
                      span(r, 'corrected')])
    out += [table(['Definition', 'Days', 'After event', 'After equally large days', 'Difference (95% interval)',
                   'Corrected for exact size'], lines), '']

    out += ['### GG and RTL on the next session, 2016-26', '']
    lines = []
    for outcome in ('gg_net', 'gg_r', 'rtl_net', 'rtl_r'):
        r = pick(summary, sample='2016-26', variant='all', event='whipsaw', outcome=outcome)
        digits = 0 if outcome.endswith('net') else 2
        lines.append([LABELS[outcome], number(r.event_mean, digits), number(r.control_mean, digits), number(r.other_sessions_mean, digits),
                      span(r, 'matched', digits)])
    out += [table(['Per session', 'After whipsaw', 'After equally large days', 'After all other days', 'Difference (95% interval)'], lines), '']

    if cross is not None:
        out += ['### ES, YM and RTY, next session move', '']
        lines = []
        for name, samples in (('ES', ('2016-19', '2020-26', '2016-26')), ('YM', ('2016-19', '2020-26', '2016-26')),
                              ('RTY', ('2018-19', '2020-26', '2018-26'))):
            for sample in samples:
                r = pick(cross, instrument=name, sample=sample, variant='all', event='whipsaw', outcome=PRIMARY)
                lines.append([name, sample, str(int(r.events_used)), number(r.event_mean), number(r.control_mean),
                              span(r, 'matched'), span(r, 'corrected')])
        out += [table(['', 'Period', 'Whipsaw days', 'After whipsaw', 'After equally large days', 'Difference (95% interval)',
                       'Corrected for exact size'], lines), '']

    if review is not None:
        out += ['### By year (NQ, checked after the result)', '']
        years = review.loc[review.check.eq('by year') & review.measure.str.fullmatch(r'\d{4}')]
        counts = review.loc[review.check.eq('whipsaw days by year')].set_index('measure').value
        lines = [[r.measure, str(int(counts[r.measure])), number(r.value, 2, True)] for r in years.itertuples()]
        out += [table(['Year', 'Whipsaw days', 'Difference'], lines), '']
    return '\n'.join(out)


def main():
    summary = pd.read_csv(DOC / 'summary.csv')
    groups = pd.read_csv(DOC / 'size_groups.csv')
    cross = pd.read_csv(DOC / 'cross_summary.csv') if (DOC / 'cross_summary.csv').exists() else None
    review = pd.read_csv(DOC / 'review_checks.csv') if (DOC / 'review_checks.csv').exists() else None
    chart(summary, groups, cross)
    text = tables(summary, cross, review)
    (RUN / 'tables.md').write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
