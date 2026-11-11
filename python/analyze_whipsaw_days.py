"""Whipsaw-day event study: what follows a whipsaw session, against equally large sessions.

Protocol: docs/baseline/whipsaw-days/PROTOCOL.md, frozen in freeze.json before this file
existed. main() stops if the protocol or the event code (whipsaw_days.py) has changed.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import rtl_weekly_engine as engine
import whipsaw_days as wd
from prepare_whipsaw_days import DOC, FREEZE, LEDGERS, NEWS, RUN, digest, frozen_texts

DRAWS = 5000
SEED = 20261111
TREND = 0.6                       # trend day: |open-to-close| at least this share of the range
NEWS_EVENTS = ('CPI', 'PAYROLLS', 'FOMC')
MARKET = [f'{name}_{horizon}' for horizon in (1, 3) for name in ('abs_move', 'range', 'trend', 'signed')]
LEDGER = ['gg_net', 'gg_r', 'rtl_net', 'rtl_r']
PRIMARY = 'abs_move_1'
LEDGER_START = '2016-01-01'       # the ledgers' primary rows cover the main eras only
VARIANTS = ('all', 'news_free')
# Published trades and net dollars of the saved ledgers, by era (source check).
PUBLISHED = {'gg': {'2016-19': (6388, 3635.60), '2020-26': (11181, 39315.45)},
             'rtl': {'2016-19': (6167, 4416.65), '2020-26': (10501, 38399.95)}}


# ---------------------------------------------------------------- data

def checked_m30():
    """M30 bars rebuilt from the minute cache, which is checked against the raw minute file."""
    from verify_rtl_failed_breakout_short import load_quote_index
    quotes = load_quote_index()
    bars = pd.DataFrame(dict(bar_time=pd.to_datetime(quotes.slots * 1800, unit='s'), open=quotes.ohlc[:, 0],
                             high=quotes.ohlc[:, 1], low=quotes.ohlc[:, 2], close=quotes.ohlc[:, 3]))
    saved = wd.read_m30()
    assert len(bars) == len(saved)
    assert np.array_equal(bars.bar_time.to_numpy('datetime64[s]'), saved.bar_time.to_numpy('datetime64[s]'))
    for column in ('open', 'high', 'low', 'close'):
        assert np.array_equal(bars[column], saved[column]), column
    return bars, len(quotes.b['o'])


def roll_dates(last='2026-10-01'):
    switches = engine.roll_switches(int(last.replace('-', '')))
    return pd.to_datetime([str(day) for day in switches], format='%Y%m%d')


def news_dates(path=NEWS):
    news = pd.read_csv(path, usecols=['event', 'research_time'], parse_dates=['research_time'])
    return pd.DatetimeIndex(news.loc[news.event.isin(NEWS_EVENTS), 'research_time'].dt.normalize().unique())


def add_outcomes(panel, table, rolls=()):
    """Next kept session, and the next three together, in units of the event session's ATR20.

    Reads only sessions after the event session. A contract roll inside the three sessions
    counts as no move from the old contract's last close to the new contract's first open.
    """
    o, h, l, c = (table[k].to_numpy(float) for k in ('open', 'high', 'low', 'close'))
    dates = table.index
    inside = np.asarray(dates < wd.END)
    gap = np.where(dates.isin(pd.DatetimeIndex(rolls)), o - np.r_[np.nan, c[:-1]], 0.0)
    out = panel.copy()
    position, atr = out.position.to_numpy(), out.atr20.to_numpy(float)

    def later(values, steps):
        index = position + steps
        found = np.full(len(position), np.nan)
        ok = index < len(table)
        ok[ok] = inside[index[ok]]
        found[ok] = values[index[ok]]
        return found

    def measures(move, span, suffix):
        out['abs_move_' + suffix] = np.abs(move) / atr
        out['range_' + suffix] = span / atr
        trend = ((np.abs(move) >= TREND * span) & (span > 0)).astype(float)
        out['trend_' + suffix] = np.where(np.isnan(move), np.nan, trend)
        out['signed_' + suffix] = move / atr

    measures(later(c, 1) - later(o, 1), later(h, 1) - later(l, 1), '1')
    shift2 = later(gap, 2)
    shift3 = shift2 + later(gap, 3)
    top = np.maximum.reduce([later(h, 1), later(h, 2) - shift2, later(h, 3) - shift3])
    bottom = np.minimum.reduce([later(l, 1), later(l, 2) - shift2, later(l, 3) - shift3])
    measures(later(c, 3) - shift3 - later(o, 1), top - bottom, '3')
    following = position + 1
    ok = following < len(table)
    ok[ok] = inside[following[ok]]
    next_session = np.full(len(position), np.datetime64('NaT', 'ns'), dtype='datetime64[ns]')
    next_session[ok] = dates[following[ok]].to_numpy('datetime64[ns]')
    out['next_session'] = next_session
    return out


def add_news(panel, dates):
    """News-free: neither the session nor the next one is a CPI, payroll or FOMC session."""
    out = panel.copy()
    out['news'] = out.index.isin(dates)
    out['next_news'] = out.next_session.isin(dates).to_numpy()
    out['news_free'] = ~(out.news | out.next_news)
    return out


def session_ledger(path):
    """Net dollars, net R and trade count per session from a saved native ledger (primary rows)."""
    trades = pd.read_csv(path, usecols=['session', 'net_dollars', 'net_r', 'era', 'sample'], parse_dates=['session'])
    trades = trades.loc[trades['sample'].eq('primary')]
    by_session = trades.groupby('session').agg(net=('net_dollars', 'sum'), r=('net_r', 'sum'), trades=('net_r', 'size'))
    by_era = trades.groupby('era').net_dollars.agg(['size', 'sum'])
    return by_session, by_era


def add_ledgers(panel, ledgers=LEDGERS, published=PUBLISHED):
    """Next-session strategy results, zero when the strategy did not trade; main eras only."""
    out = panel.copy()
    covered = out.next_session.notna().to_numpy() & (out.index >= LEDGER_START)
    for name, path in ledgers.items():
        by_session, by_era = session_ledger(path)
        for era, (trades, net) in (published or {}).get(name, {}).items():
            assert by_era.loc[era, 'size'] == trades and abs(by_era.loc[era, 'sum'] - net) < .005, (name, era)
        for column in ('net', 'r'):
            values = out.next_session.map(by_session[column]).fillna(0.0)
            out[f'{name}_{column}'] = np.where(covered, values, np.nan)
    return out


# ---------------------------------------------------------------- comparisons

def cell_ids(frame):
    """Year-and-size-group of each session: the groups inside which sessions are compared."""
    return frame.year.to_numpy() * wd.SIZE_GROUPS + frame.size_group.to_numpy()


def month_cell_sums(y, event, size, cell, month, months):
    """Per (month, cell) sums of everything both comparisons need; sessions without an outcome are left out."""
    keep = ~np.isnan(y)
    y, f, x = y[keep], event[keep].astype(float), size[keep].astype(float)
    cells, c = np.unique(cell[keep], return_inverse=True)
    flat = month[keep] * len(cells) + c

    def total(values):
        return np.bincount(flat, weights=values, minlength=months * len(cells)).reshape(months, len(cells))

    return dict(n=total(np.ones(len(y))), f=total(f), x=total(x), y=total(y),
                xx=total(x * x), fx=total(f * x), fy=total(f * y), xy=total(x * y))


def estimates(s):
    """Both comparisons from cell sums (cells on the last axis).

    matched: over event sessions, outcome minus the mean of the non-event sessions in the same cell.
    corrected: coefficient of the event flag in outcome ~ flag + size + one level per cell.
    """
    n, f, y, fy = s['n'], s['f'], s['y'], s['fy']
    controls = n - f
    usable = (f > 0) & (controls > 0)
    with np.errstate(divide='ignore', invalid='ignore'):
        used = np.where(usable, f, 0.0)
        events = used.sum(-1)
        event_mean = np.where(usable, fy, 0.0).sum(-1) / events
        control_mean = np.where(usable, f * (y - fy) / controls, 0.0).sum(-1) / events
        event_size = np.where(usable, s['fx'], 0.0).sum(-1) / events
        control_size = np.where(usable, f * (s['x'] - s['fx']) / controls, 0.0).sum(-1) / events
        inverse = np.where(n > 0, 1 / n, 0.0)
        sff = (f - f * f * inverse).sum(-1)
        sfx = (s['fx'] - f * s['x'] * inverse).sum(-1)
        sxx = (s['xx'] - s['x'] ** 2 * inverse).sum(-1)
        sfy = (fy - f * y * inverse).sum(-1)
        sxy = (s['xy'] - s['x'] * y * inverse).sum(-1)
        determinant = sff * sxx - sfx ** 2
        determinant = np.where(determinant > 1e-12 * np.maximum(sff * sxx, 1e-300), determinant, np.nan)
        corrected = (sfy * sxx - sfx * sxy) / determinant
        slope = (sff * sxy - sfx * sfy) / determinant
    return dict(matched=event_mean - control_mean, corrected=corrected, slope=slope, events_used=events,
                controls_used=np.where(usable, controls, 0.0).sum(-1), event_mean=event_mean,
                control_mean=control_mean, event_size=event_size, control_size=control_size)


def month_weights(months, draws=DRAWS, seed=SEED):
    """How often each calendar month is drawn in each resample: whole months, with replacement."""
    return np.random.default_rng(seed).multinomial(months, np.full(months, 1 / months), size=draws)


def interval(values):
    """2.5th to 97.5th percentile of the draws that could be computed."""
    values = values[~np.isnan(values)]
    return tuple(np.percentile(values, [2.5, 97.5])) if len(values) else (np.nan, np.nan)


def compare(frame, event, outcome, month, weights):
    """Point estimates and month-resampling intervals for one event definition and one outcome."""
    y = frame[outcome].to_numpy(float)
    flag = frame[event].to_numpy(bool)
    sums = month_cell_sums(y, flag, frame.range_ratio.to_numpy(float), cell_ids(frame), month, weights.shape[1])
    point = estimates({k: v.sum(0) for k, v in sums.items()})
    resampled = estimates({k: weights @ v for k, v in sums.items()})
    have = ~np.isnan(y)
    row = dict(sessions=int(have.sum()), events=int((flag & have).sum()),
               events_used=int(point['events_used']), controls_used=int(point['controls_used']),
               all_events_mean=float(y[flag & have].mean()) if (flag & have).any() else np.nan,
               other_sessions_mean=float(y[~flag & have].mean()),
               event_mean=float(point['event_mean']), control_mean=float(point['control_mean']),
               event_size=float(point['event_size']), control_size=float(point['control_size']))
    for name in ('matched', 'corrected'):
        low, high = interval(resampled[name])
        row.update({name + '_diff': float(point[name]), name + '_lo': float(low), name + '_hi': float(high),
                    name + '_draws_failed': int(np.isnan(resampled[name]).sum())})
    row['size_slope'] = float(point['slope'])
    return row, resampled


def matched_plain(frame, event, outcome):
    """The matched difference written the slow, obvious way (independent check)."""
    data = frame[[event, outcome, 'year', 'size_group']].dropna(subset=[outcome])
    total = weight = 0.0
    for _, cell in data.groupby(['year', 'size_group']):
        events, controls = cell.loc[cell[event], outcome], cell.loc[~cell[event], outcome]
        if len(events) and len(controls):
            total += len(events) * (events.mean() - controls.mean())
            weight += len(events)
    return total / weight


def corrected_plain(frame, event, outcome):
    """The size-corrected difference by least squares with explicit cell dummies (independent check)."""
    data = frame[[event, outcome, 'range_ratio', 'year', 'size_group']].dropna(subset=[outcome])
    cells = pd.factorize(cell_ids(data))[0]
    design = np.column_stack([data[event].to_numpy(float), data.range_ratio.to_numpy(float),
                              np.eye(cells.max() + 1)[cells]])
    return float(np.linalg.lstsq(design, data[outcome].to_numpy(float), rcond=None)[0][0])


def in_sample(panel, sample, eras=None):
    start, end = (eras or wd.ERAS)[sample]
    return (panel.index >= start) & (panel.index < end)


def summarise(panel, outcomes_by_sample, draws=DRAWS, seed=SEED, keep_draws=(), eras=None):
    """Every sample x session variant x event definition x outcome."""
    rows, kept = [], {}
    for sample, outcomes in outcomes_by_sample.items():
        base = panel.loc[in_sample(panel, sample, eras)]
        month_values, month_index = np.unique(base.month.to_numpy(), return_inverse=True)
        weights = month_weights(len(month_values), draws, seed)
        for variant in VARIANTS:
            keep = np.ones(len(base), bool) if variant == 'all' else base.news_free.to_numpy()
            frame, month = base.loc[keep], month_index[keep]
            for event in wd.EVENTS:
                for outcome in outcomes:
                    row, resampled = compare(frame, event, outcome, month, weights)
                    rows.append(dict(sample=sample, variant=variant, event=event, outcome=outcome,
                                     months=len(month_values), **row))
                    if (sample, variant, event, outcome) in keep_draws:
                        kept[(sample, variant, event, outcome)] = resampled
    return pd.DataFrame(rows), kept


def reading(summary, main_eras=wd.MAIN_ERAS, pooled_era=wd.POOLED, neighbours=True):
    """The four conditions fixed in the protocol, on all sessions and the next-session move.

    Other instruments are judged by points 1 to 3 only (neighbours=False).
    """
    def pick(sample, event='whipsaw', variant='all'):
        match = summary.loc[summary['sample'].eq(sample) & summary.variant.eq(variant)
                            & summary.event.eq(event) & summary.outcome.eq(PRIMARY)]
        assert len(match) == 1
        return match.iloc[0]

    pooled = pick(pooled_era)
    conditions = {
        '1_matched_above_zero_in_both_eras': bool(all(pick(era).matched_diff > 0 for era in main_eras)),
        '2_pooled_matched_interval_above_zero': bool(pooled.matched_lo > 0),
        '3_pooled_size_corrected_interval_above_zero': bool(pooled.corrected_lo > 0)}
    if neighbours:
        conditions['4_both_neighbours_above_zero_pooled'] = bool(all(
            pick(pooled_era, name).matched_diff > 0 for name in ('looser', 'stricter')))
    supported = all(conditions.values())
    news_free = pick(pooled_era, variant='news_free')
    return dict(supported=supported, conditions=conditions,
                news_free_pooled_matched_above_zero=bool(news_free.matched_diff > 0),
                verdict=('supported' if supported and news_free.matched_diff > 0 else
                         'supported, but an effect of scheduled news' if supported else 'not supported'))


def size_group_table(panel, sample=wd.POOLED, event='whipsaw', outcome=PRIMARY):
    """For the chart: the outcome by size group, event sessions against the others."""
    frame = panel.loc[wd.in_era(panel, sample)].dropna(subset=[outcome])
    rows = []
    for group, cell in frame.groupby('size_group'):
        events, others = cell.loc[cell[event]], cell.loc[~cell[event]]
        rows.append(dict(size_group=int(group) + 1, size_low=cell.range_ratio.min(), size_high=cell.range_ratio.max(),
                         events=len(events), others=len(others),
                         event_size=events.range_ratio.mean() if len(events) else np.nan,
                         other_size=others.range_ratio.mean(),
                         event_mean=events[outcome].mean() if len(events) else np.nan,
                         other_mean=others[outcome].mean(),
                         event_se=events[outcome].sem() if len(events) > 1 else np.nan,
                         other_se=others[outcome].sem()))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- run

def main():
    freeze = json.loads(FREEZE.read_text(encoding='utf-8'))
    for key, value in frozen_texts().items():
        assert freeze[key] == value, f'{key} changed after the freeze: no outcome computed'
    bars, raw_minutes = checked_m30()
    table = wd.session_table(bars)
    panel = wd.event_panel(bars)
    assert wd.counts(panel) == freeze['counts'] == wd.EXPECTED_COUNTS
    print(f'Frozen protocol and event code verified; {raw_minutes:,} raw minutes and {len(bars):,} M30 bars checked; '
          f'event counts reproduced: {wd.counts(panel)}', flush=True)

    rolls = roll_dates()
    panel = add_ledgers(add_news(add_outcomes(panel, table, rolls), news_dates()))
    outcomes = {era: MARKET + LEDGER for era in (*wd.MAIN_ERAS, wd.POOLED)}
    outcomes['2010-15'] = MARKET
    headline = [(sample, 'all', event, PRIMARY) for sample in outcomes for event in wd.EVENTS]
    summary, draws = summarise(panel, outcomes, keep_draws=headline)

    # Independent check of every next-session-move row against the slow, obvious versions.
    checked = 0
    for row in summary.loc[summary.outcome.eq(PRIMARY)].itertuples():
        frame = panel.loc[wd.in_era(panel, row.sample)]
        frame = frame if row.variant == 'all' else frame.loc[frame.news_free]
        assert np.isclose(row.matched_diff, matched_plain(frame, row.event, PRIMARY), rtol=0, atol=1e-10)
        assert np.isclose(row.corrected_diff, corrected_plain(frame, row.event, PRIMARY), rtol=0, atol=1e-8)
        checked += 1
    result = reading(summary)

    RUN.mkdir(parents=True, exist_ok=True)
    panel.to_csv(RUN / 'sessions.csv')
    pd.DataFrame({'|'.join(key): value['matched'] for key, value in draws.items()}).to_csv(
        RUN / 'bootstrap_matched_draws.csv', index=False)
    pd.DataFrame({'|'.join(key): value['corrected'] for key, value in draws.items()}).to_csv(
        RUN / 'bootstrap_corrected_draws.csv', index=False)
    summary.to_csv(DOC / 'summary.csv', index=False)
    size_group_table(panel).to_csv(DOC / 'size_groups.csv', index=False)
    result.update(protocol_sha256=freeze['protocol_sha256'], event_code_sha256=freeze['event_code_sha256'],
                  frozen_at_utc=freeze['frozen_at_utc'], analysis_code_sha256=digest(__file__),
                  raw_minutes_checked=raw_minutes, m30_bars=len(bars), sessions=len(panel),
                  roll_dates=len(rolls), independent_rows_checked=checked, draws=DRAWS, seed=SEED,
                  news_sessions=int(panel.news.sum()), news_free_sessions=int(panel.news_free.sum()))
    (DOC / 'verdict.json').write_text(json.dumps(result, indent=2), encoding='utf-8')

    show = summary.loc[summary.outcome.eq(PRIMARY) & summary.variant.eq('all'),
                       ['sample', 'event', 'events_used', 'event_mean', 'control_mean', 'matched_diff', 'matched_lo',
                        'matched_hi', 'corrected_diff', 'corrected_lo', 'corrected_hi']]
    print(show.to_string(index=False, float_format=lambda v: f'{v:.3f}'))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
