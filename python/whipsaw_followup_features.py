"""Causal features for the exploratory whipsaw follow-up; original rule unchanged."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_whipsaw_days as original
import whipsaw_days as wd
from prepare_whipsaw_days import FREEZE, ROOT, digest, frozen_texts
from verify_rtl_failed_breakout_short import CACHE

DOC = ROOT / 'docs/baseline/whipsaw-followup'
RUN = ROOT / 'Reports/whipsaw_followup_20261112'
SHAPE_TOLERANCE = .10
BREAK_BUFFER = .05
RETURN_BARS = 4


def verify_original():
    """Check every frozen input, not only the old event counts."""
    record = json.loads(FREEZE.read_text(encoding='utf-8-sig'))
    for key, value in frozen_texts().items():
        if record[key] != value:
            raise ValueError(f'Original frozen text changed: {key}')
    for name, expected in record['inputs_sha256'].items():
        path = Path(name)
        if not path.is_absolute():
            path = ROOT / path
        if digest(path) != expected:
            raise ValueError(f'Original input changed: {name}')
    return record


def swing_trace(path, threshold):
    """Return confirmed swing indices and observed endpoints, each (index, price, high/low).

    Endpoints include the final, not-yet-reversed extreme. A confirmation's
    information time is its own index, never the earlier extreme's index.
    """
    p = np.asarray(path, float)
    if not len(p) or not np.isfinite(p).all() or not threshold > 0:
        raise ValueError('finite nonempty path and positive threshold required')
    high = low = extreme = p[0]
    high_at = low_at = extreme_at = 0
    direction = 0
    points, confirmations = [], []
    for at, price in enumerate(p[1:], 1):
        if direction == 0:
            if price > high:
                high, high_at = price, at
            if price < low:
                low, low_at = price, at
            if price - low >= threshold:
                direction = 1
                points.append((low_at, low, 'low'))
            elif high - price >= threshold:
                direction = -1
                points.append((high_at, high, 'high'))
            else:
                continue
            extreme, extreme_at = price, at
            confirmations.append(at)
        elif direction * (price - extreme) > 0:
            extreme, extreme_at = price, at
        elif direction * (extreme - price) >= threshold:
            points.append((extreme_at, extreme, 'high' if direction == 1 else 'low'))
            direction *= -1
            extreme, extreme_at = price, at
            confirmations.append(at)
    if direction:
        points.append((extreme_at, extreme, 'high' if direction == 1 else 'low'))
    return points, confirmations


def geometry(points, atr):
    """Initial three-leg geometry; the fourth endpoint may be terminal at close."""
    if len(points) < 4:
        return 'not_whipsaw'
    highs = [price for _, price, kind in points[:4] if kind == 'high']
    lows = [price for _, price, kind in points[:4] if kind == 'low']
    if len(highs) != 2 or len(lows) != 2:
        raise ValueError('endpoints must alternate')
    dh, dl = highs[1] - highs[0], lows[1] - lows[0]
    tolerance = SHAPE_TOLERANCE * atr
    if abs(dh) <= tolerance and abs(dl) <= tolerance:
        return 'bounded'
    if dh > tolerance and dl < -tolerance:
        return 'expanding'
    return 'other'


def failed_boundary(high, low, close, level, atr, side):
    """First buffered breach only; return the confirmation bar or None."""
    if side not in ('high', 'low'):
        raise ValueError('side must be high or low')
    breached = np.asarray(high) >= level + BREAK_BUFFER * atr if side == 'high' else (
        np.asarray(low) <= level - BREAK_BUFFER * atr)
    hits = np.flatnonzero(breached)
    if not len(hits):
        return None
    first = int(hits[0])
    ends = np.asarray(close)[first:first + RETURN_BARS]
    inside = ends <= level if side == 'high' else ends >= level
    returned = np.flatnonzero(inside)
    return first + int(returned[0]) if len(returned) else None


def minute_measures(minutes):
    """Daily price-change volatility from M1 and five-minute bucket closes."""
    day = minutes['day']
    epoch = day * 1440 + minutes['minute']
    if not np.all(np.diff(epoch) > 0):
        raise ValueError('minute timestamps must be strictly increasing')
    edges = np.flatnonzero(np.r_[True, day[1:] != day[:-1], True])
    rows = []
    for start, end in zip(edges[:-1], edges[1:]):
        close = minutes['c'][start:end]
        opening = minutes['o'][start]
        buckets = minutes['minute'][start:end] // 5
        last = np.flatnonzero(np.r_[buckets[1:] != buckets[:-1], True])
        d1 = np.diff(np.r_[opening, close])
        d5 = np.diff(np.r_[opening, close[last]])
        rows.append((pd.Timestamp(int(day[start]), unit='D'),
                     np.sqrt(d1 @ d1), np.sqrt(d5 @ d5), end - start))
    return pd.DataFrame(rows, columns=['session', 'rv1_points', 'rv5m_points', 'minutes']).set_index('session')


def add_volatility(panel, table, daily):
    """Lag after selecting kept sessions, with the current day's ATR denominator."""
    out = panel.copy()
    kept = daily.reindex(table.index)
    if kept[['rv1_points', 'rv5m_points']].isna().any().any():
        raise ValueError('missing minute session')
    for name in ('rv1', 'rv5m'):
        points = kept[name + '_points']
        out[name] = points.reindex(out.index) / out.atr20
        for lag in (5, 20):
            out[f'{name}_prior{lag}'] = points.shift().rolling(lag).mean().reindex(out.index) / out.atr20
    previous = table.close.shift()
    tr = np.maximum(table.high, previous) - np.minimum(table.low, previous)
    out['recent5'] = tr.shift().rolling(5).mean().reindex(out.index) / out.atr20
    out['signed_body'] = (out.close - out.open) / out.atr20
    return out


def build_features():
    bars = wd.read_m30()
    table = wd.session_table(bars)
    panel = wd.event_panel(bars)
    if wd.counts(panel) != wd.EXPECTED_COUNTS:
        raise ValueError('original event counts changed')
    with np.load(CACHE) as saved:
        minutes = {key: saved[key] for key in ('day', 'minute', 'o', 'h', 'l', 'c')}
    panel = add_volatility(panel, table, minute_measures(minutes))
    rolls = original.roll_dates()
    panel['roll_day'] = panel.index.isin(rolls)
    following = panel.position.to_numpy() + 1
    panel['next_session'] = [table.index[i] if i < len(table) and table.index[i] < pd.Timestamp(wd.END) else pd.NaT
                             for i in following]
    panel = original.add_news(panel, original.news_dates())
    rows = []
    for day, b in bars.groupby(bars.bar_time.dt.normalize(), sort=True):
        if day not in panel.index:
            continue
        row = panel.loc[day]
        path = wd.bar_path(*(b[k].to_numpy() for k in ('open', 'high', 'low', 'close')))
        points, confirmations = swing_trace(path, .75 * row.atr20)
        if len(confirmations) != row.swings_whipsaw:
            raise ValueError(f'trace does not match original count: {day}')
        shape = geometry(points, row.atr20)
        detected_bar = confirmations[2] // 4 if len(confirmations) >= 3 else None
        detected_at = b.bar_time.iloc[detected_bar] + pd.Timedelta(minutes=30) if detected_bar is not None else pd.NaT
        comparable = not row.roll_day
        hi = failed_boundary(b.high, b.low, b.close, row.prev_high, row.atr20, 'high') if comparable else None
        lo = failed_boundary(b.high, b.low, b.close, row.prev_low, row.atr20, 'low') if comparable else None
        both = hi is not None and lo is not None
        both_at = b.bar_time.iloc[max(hi, lo)] + pd.Timedelta(minutes=30) if both else pd.NaT
        rows.append(dict(session=day, geometry=shape, detected_bar=detected_bar,
                         detected_at=detected_at, bars_after_detection=(len(b) - detected_bar - 1)
                         if detected_bar is not None else np.nan,
                         prior_levels_available=comparable, failed_high=hi is not None,
                         failed_low=lo is not None, failed_both=both, failed_both_at=both_at))
    panel = panel.join(pd.DataFrame(rows).set_index('session'))
    for name in ('bounded', 'expanding'):
        panel['whipsaw_' + name] = panel.whipsaw & panel.geometry.eq(name)
    panel['whipsaw_failed_both'] = panel.whipsaw & panel.failed_both
    # M1 reconstruction is a fixed robustness diagnostic, not a replacement event.
    edges = np.flatnonzero(np.r_[True, np.diff(minutes['day']) != 0, True])
    flags = {}
    for start, end in zip(edges[:-1], edges[1:]):
        day = pd.Timestamp(int(minutes['day'][start]), unit='D')
        if day in panel.index:
            path = wd.bar_path(*(minutes[k][start:end] for k in 'ohlc'))
            flags[day] = wd.count_swings(path, .75 * panel.at[day, 'atr20']) >= 3
    panel['m1_whipsaw'] = pd.Series(flags)
    required = ['rv1', 'rv1_prior5', 'rv1_prior20', 'rv5m', 'rv5m_prior5', 'rv5m_prior20', 'recent5']
    if panel[required].isna().any().any():
        raise ValueError('incomplete volatility history')
    return panel, bars


def add_remaining_outcomes(panel, bars):
    """Start strictly after the recognition bar, at the next observed M30 open."""
    result = panel.copy()
    result['remaining_abs_move'] = np.nan
    result['remaining_range'] = np.nan
    for day, b in bars.groupby(bars.bar_time.dt.normalize()):
        if day not in result.index or pd.isna(result.at[day, 'detected_bar']):
            continue
        later = b.iloc[int(result.at[day, 'detected_bar']) + 1:]
        if len(later):
            atr = result.at[day, 'atr20']
            result.at[day, 'remaining_abs_move'] = abs(later.close.iloc[-1] - later.open.iloc[0]) / atr
            result.at[day, 'remaining_range'] = (later.high.max() - later.low.min()) / atr
    return result

