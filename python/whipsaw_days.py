"""Whipsaw-session events on M30 bars: sessions, ATR20, zigzag swing counts and event flags.

Only what is known at a session's close lives here: no later session is read.
Frozen with docs/baseline/whipsaw-days/PROTOCOL.md; outcomes and statistics are in
analyze_whipsaw_days.py. Run this file to print the outcome-blind event counts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT

READY_M30 = ROOT / 'Reports/gg_large_candle_20261109/signal_features.csv'
MIN_BARS = 20          # sessions with fewer M30 bars are dropped before anything else
ATR_SESSIONS = 20      # ATR20 = mean true range of this many previous sessions
END = '2026-10-01'     # event sessions before this date
SIZE_GROUPS = 10       # equal-count groups of the day's range / ATR20
# name: (zigzag threshold in ATR20, minimum number of swings)
SWING_EVENTS = {'whipsaw': (0.75, 3), 'looser': (0.50, 4), 'stricter': (1.00, 3)}
OUTSIDE = 'outside_inside'
EVENTS = (*SWING_EVENTS, OUTSIDE)
ERAS = {'2010-15': ('2010-01-01', '2016-01-01'), '2016-19': ('2016-01-01', '2020-01-01'),
        '2020-26': ('2020-01-01', END), '2016-26': ('2016-01-01', END)}
MAIN_ERAS = ('2016-19', '2020-26')
POOLED = '2016-26'
# Counts handed over before the study, 2010-07-06 to 2026-09-30.
EXPECTED_COUNTS = {'sessions': 4180, 'whipsaw': 243, 'looser': 549, 'stricter': 63, OUTSIDE: 233}


def read_m30(path=READY_M30):
    """The saved copy of the checked M30 bars (bar_time, open, high, low, close)."""
    return pd.read_csv(path, usecols=['bar_time', 'open', 'high', 'low', 'close'], parse_dates=['bar_time'])


def bar_path(o, h, l, c):
    """Prices in walking order: open, low, high, close for a bar closing at or above its open,
    otherwise open, high, low, close."""
    o, h, l, c = (np.asarray(v, dtype=float) for v in (o, h, l, c))
    up = c >= o
    path = np.empty((len(o), 4))
    path[:, 0], path[:, 3] = o, c
    path[:, 1] = np.where(up, l, h)
    path[:, 2] = np.where(up, h, l)
    return path.ravel()


def count_swings(path, threshold):
    """Number of confirmed zigzag swings of at least `threshold`.

    The first swing is confirmed once price is `threshold` or more away from the lowest or
    highest price seen so far. Afterwards a swing the other way is confirmed each time price
    reverses by `threshold` or more from the extreme of the current swing.
    """
    if not threshold > 0:
        raise ValueError('threshold must be positive')
    high = low = extreme = float(path[0])
    direction = swings = 0
    for price in path[1:]:
        if direction == 0:
            high, low = max(high, price), min(low, price)
            if price - low >= threshold:
                direction, swings, extreme = 1, 1, price
            elif high - price >= threshold:
                direction, swings, extreme = -1, 1, price
        elif direction == 1:
            if price > extreme:
                extreme = price
            elif extreme - price >= threshold:
                direction, swings, extreme = -1, swings + 1, price
        else:
            if price < extreme:
                extreme = price
            elif price - extreme >= threshold:
                direction, swings, extreme = 1, swings + 1, price
    return swings


def session_table(bars):
    """One row per kept session (calendar date of the bars, at least MIN_BARS bars), in date order."""
    assert bars.bar_time.is_monotonic_increasing and bars.bar_time.is_unique
    assert bars.bar_time.dt.hour.ge(1).all(), 'a session starts at 01:00'
    grouped = bars.groupby(bars.bar_time.dt.normalize().rename('session'), sort=True)
    table = grouped.agg(open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
                        close=('close', 'last'), bars=('open', 'size'))
    return table.loc[table.bars >= MIN_BARS]


def size_groups(values, groups=SIZE_GROUPS):
    """Equal-count groups by rank, ties broken by order of appearance; 0 is the smallest."""
    rank = np.argsort(np.argsort(np.asarray(values), kind='stable'), kind='stable')
    return rank * groups // len(rank)


def event_panel(bars):
    """Kept sessions with a defined ATR20 before END, with everything known at their close."""
    table = session_table(bars)
    prev_close, prev_high, prev_low = table.close.shift(), table.high.shift(), table.low.shift()
    true_range = np.maximum(table.high, prev_close) - np.minimum(table.low, prev_close)  # NaN for the first
    panel = table.assign(atr20=true_range.rolling(ATR_SESSIONS).mean().shift(),
                         prev_high=prev_high, prev_low=prev_low)
    panel['position'] = np.arange(len(table))  # row in session_table, to find later sessions
    panel = panel.loc[panel.atr20.notna() & (panel.index < END)].copy()
    assert panel.atr20.gt(0).all()
    panel['range_ratio'] = (panel.high - panel.low) / panel.atr20
    dates = bars.bar_time.dt.normalize().to_numpy()
    edges = np.flatnonzero(np.r_[True, dates[1:] != dates[:-1], True])
    spans = dict(zip(dates[edges[:-1]], zip(edges[:-1], edges[1:])))
    cols = [bars[k].to_numpy(float) for k in ('open', 'high', 'low', 'close')]
    paths = [bar_path(*(col[slice(*spans[np.datetime64(day)])] for col in cols)) for day in panel.index]
    for name, (multiple, minimum) in SWING_EVENTS.items():
        panel['swings_' + name] = [count_swings(path, multiple * atr) for path, atr in zip(paths, panel.atr20)]
        panel[name] = panel['swings_' + name] >= minimum
    panel[OUTSIDE] = ((panel.high > panel.prev_high) & (panel.low < panel.prev_low)
                      & (panel.close <= panel.prev_high) & (panel.close >= panel.prev_low))
    panel['year'] = panel.index.year
    panel['month'] = panel.index.year * 12 + panel.index.month - 1
    panel['size_group'] = size_groups(panel.range_ratio)
    return panel


def counts(panel):
    return {'sessions': len(panel), **{name: int(panel[name].sum()) for name in EVENTS}}


def in_era(panel, era):
    start, end = ERAS[era]
    return (panel.index >= start) & (panel.index < end)


def main():
    panel = event_panel(read_m30())
    found = counts(panel)
    print(f'{panel.index[0].date()} to {panel.index[-1].date()}: {found}')
    print('by era:', {era: {name: int(panel.loc[in_era(panel, era), name].sum()) for name in EVENTS} for era in ERAS})
    assert found == EXPECTED_COUNTS, (found, EXPECTED_COUNTS)
    print('Handed-over counts reproduced.')


if __name__ == '__main__':
    main()
