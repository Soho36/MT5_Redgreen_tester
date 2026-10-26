"""Minute-bar RTL simulator: MT5 M30 EA emulation, and RTL on weekly bars, held or session-flattened.

Ticks follow MT5's 1-minute OHLC model: open, then low and high (bullish minute) or
high and low (otherwise), then close, at :00/:20/:40/:59. With 'gap' fills an order fills
at its level, or at a minute's open when that open is already beyond it.
Prices o/h/l/c are in the level basis (raw or roll-adjusted). `fac` = basis / raw for
each minute, constant within a session, so raw points = basis difference / fac.
Protocol: docs/baseline/rtl-weekly-flatten/PROTOCOL.md.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT

MINUTES = Path(r'F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv')
ROLLS = MINUTES.with_name('MT5_NQ_continuous_2010-2026_rolls.csv')
CALENDAR = ROOT / 'mt5/experts/early_closes.mqh'
POINT_VALUE = 2.0
CUTOFF = 23 * 60 + 30
TICK_SECONDS = (0, 20, 40, 59)


def load_minutes(cache=None):
    """Arrays date (yyyymmdd), day (days since 1970), minute (of day), o/h/l/c (raw)."""
    if cache is not None and Path(cache).exists():
        with np.load(cache) as z:
            return {k: z[k] for k in z.files}
    d = pd.read_csv(MINUTES, sep='\t', usecols=[0, 1, 2, 3, 4, 5], header=0,
                    names=['date', 'time', 'o', 'h', 'l', 'c'], dtype={'date': str, 'time': str})
    keys = pd.Series(pd.unique(d.date))
    days = pd.to_datetime(keys, format='%Y.%m.%d').to_numpy().astype('datetime64[D]').astype(np.int64)
    day = pd.Series(days, index=keys)[d.date].to_numpy()
    bars = {'date': d.date.str.replace('.', '', regex=False).astype(np.int64).to_numpy(), 'day': day,
            'minute': (d.time.str[:2].astype(int) * 60 + d.time.str[3:5].astype(int)).to_numpy(),
            **{k: d[k].to_numpy(np.float64) for k in 'ohlc'}}
    t = bars['day'] * 1440 + bars['minute']
    assert (np.diff(t) > 0).all(), 'minutes must be strictly increasing'
    if cache is not None:
        np.savez(cache, **bars)
    return bars


def load_cutoffs():
    """Flatten minute per session date from the EA's early-close calendar (23:30 otherwise)."""
    text = CALENDAR.read_text(encoding='utf-8')
    dates = [int(x) for x in re.search(r'EC_DATE\[EC_COUNT\] = \{([^}]+)', text).group(1).split(',')]
    times = [int(x) for x in re.search(r'EC_FLAT_MIN\[EC_COUNT\] = \{([^}]+)', text).group(1).split(',')]
    return dict(zip(dates, times))


def roll_switches(last_date):
    """Session dates (yyyymmdd) on which the traded contract changes."""
    rolls = pd.read_csv(ROLLS)
    change = rolls.symbol.ne(rolls.symbol.shift()) & rolls.symbol.shift().notna()
    dates = rolls.loc[change, 'date'].str.replace('-', '').astype(int)
    return [d for d in dates if d <= last_date]


def roll_factor(bars, switches):
    """Ratio back-adjustment: the last close before a switch to its first open becomes a zero move."""
    date, o, c = bars['date'], bars['o'], bars['c']
    factor = np.ones(len(o))
    for switch in switches:
        first = int(np.searchsorted(date, switch))
        assert date[first] == switch and first > 0
        factor[:first] *= o[first] / c[first - 1]
    return factor


def contract_ids(bars, switches):
    return np.searchsorted(np.asarray(switches), bars['date'], side='right')


def week_keys(day):
    """Monday of each date's week (days since 1970; 1970-01-01 was a Thursday)."""
    return day - (day + 3) % 7


def path(o, h, l, c):
    return (o, l, h, c) if c > o else (o, h, l, c)


def is_signal(o, c, signal):
    """RTL arms on a red bar, GG (signal 'green') on a green bar."""
    return c > o if signal == 'green' else c < o


def stamp(day, minute, k):
    return np.datetime64(int(day), 'D') + np.timedelta64(int(minute) * 60 + TICK_SECONDS[k], 's')


def stamp_array(day, minute, k=0):
    return (np.asarray(day).astype('datetime64[D]') + (np.asarray(minute) * 60 + TICK_SECONDS[k]).astype('timedelta64[s]'))


# ---------------------------------------------------------------- M30 EA emulation

def simulate_m30_ea(bars, rr=1.0, cutoffs=None, last_date=None, signal='red'):
    """RR_r_MFE_buy-stop-entry_runband on M30, uncapped, all 01:00-23:30 windows, flatten fallback
    and early-close calendar, MT5 tester fills (pending and stop orders fill at their level)."""
    cutoffs = cutoffs or {}
    date, day, minute = bars['date'], bars['day'], bars['minute']
    o, h, l, c = bars['o'], bars['h'], bars['l'], bars['c']
    n = len(o) if last_date is None else int(np.searchsorted(date, last_date, side='right'))
    slot = day * 48 + minute // 30
    trades, rejected = [], 0
    pend = pos = None
    last_flat = prev_date = 0
    bar1 = cur = None
    cur_slot = -1

    def close(i, k, price, why):
        nonlocal pos
        trades.append({**pos, 'exit_time': stamp(day[i], minute[i], k), 'exit_price': price, 'reason': why})
        pos = None

    for i in range(n):
        new = slot[i] != cur_slot
        if new:
            bar1 = cur
            cur = [o[i], h[i], l[i], c[i]]
            cur_slot = slot[i]
        else:
            cur[1] = max(cur[1], h[i]); cur[2] = min(cur[2], l[i]); cur[3] = c[i]
        if not new and (pend is None or h[i] < pend['requested']) and (pos is None or l[i] > pos['sl']):
            continue
        for k, p in enumerate(path(o[i], h[i], l[i], c[i])):
            if pos is not None and p <= pos['sl']:
                close(i, k, pos['sl'], 'sl')
            if pend is not None and p >= pend['requested']:
                pos = {**pend, 'entry_time': stamp(day[i], minute[i], k), 'fill': pend['requested']}
                pend = None
            if k or not new:
                continue
            # ---- OnTick at the first tick of a new M30 bar
            bar_date, bar_min = date[i], (minute[i] // 30) * 30
            if prev_date and bar_date != prev_date and last_flat != prev_date:
                last_flat = prev_date
                if pos is not None:
                    close(i, k, p, 'fallback')
                pend = None
            prev_date = bar_date
            if bar_min >= cutoffs.get(bar_date, CUTOFF):
                if last_flat != bar_date:
                    last_flat = bar_date
                    if pos is not None:
                        close(i, k, p, 'flatten')
                    pend = None
                continue
            if pos is not None:
                if bar1[3] >= pos['fill'] + rr * (pos['fill'] - pos['sl']):
                    close(i, k, p, 'target')
                continue
            if bar_min < 60:
                pend = None
                continue
            if bar1 is not None and is_signal(bar1[0], bar1[3], signal):
                pend = None
                if bar1[1] - bar1[2] <= 0:
                    continue
                if bar1[1] <= p:
                    rejected += 1
                    continue
                pend = {'submitted': stamp(day[i], bar_min, 0), 'requested': bar1[1], 'sl': bar1[2]}
    if pos is not None:
        close(n - 1, 3, c[n - 1], 'end_of_data')
    return pd.DataFrame(trades), rejected


# ---------------------------------------------------------------- weekly RTL

def weekly_bars(bars, o, h, l, c):
    """Index of the first minute of each week and that week's OHLC in the level basis."""
    wk = week_keys(bars['day'])
    starts = np.flatnonzero(np.r_[True, wk[1:] != wk[:-1]])
    ends = np.r_[starts[1:], len(o)]
    return starts, np.c_[o[starts], np.maximum.reduceat(h, starts), np.minimum.reduceat(l, starts), c[ends - 1]]


def simulate_weekly(bars, o, h, l, c, fac, mode='flat', fills='gap', rr=1.0, cutoffs=None,
                    last_date=None, contracts=None, control=None, spread=0.0, signal='red'):
    """RTL on weekly bars. mode 'flat': live only 01:00-cutoff, reopen at each session open.
    mode 'hold': the EA on W1 with flattening and windows off. fills 'gap': at the level or a
    worse open; 'mt5': always at the level (MT5 tester). Returns (trades, pieces, counters).
    Pieces are round turns in flat mode; in hold mode, a held trade's P&L per session ('mark').
    control 'plain': market buy at every week's first open while flat, stop one previous-week
    range below (the EA's SignalMode 3); 'signal_market': market buy after a signal week, stop at
    its low. signal 'red' = RTL, 'green' = GG. Market buys pay `spread` (MT5: ask = bid + 0.01)."""
    cutoffs = cutoffs or {}
    date, day, minute = bars['date'], bars['day'], bars['minute']
    n = len(o) if last_date is None else int(np.searchsorted(date, last_date, side='right'))
    starts, weeks = weekly_bars(bars, o, h, l, c)
    week_of = np.searchsorted(starts, np.arange(n), side='right') - 1
    contracts = np.zeros(len(o), int) if contracts is None else contracts
    trades, pieces = [], []
    counts = dict(rejected=0, flat_fills=0, gap_stops=0, target_weeks_red=0, no_cutoff_bar=0)
    pend = trade = None
    leg = None          # open piece: (start time, start price); hold mode: one per session held
    live = False

    def start_trade(i, k, price, flat_fill=False):
        nonlocal trade, pend, leg
        trade = {'signal_week': pend['week'], 'submitted': pend['submitted'], 'requested': pend['requested'],
                 'sl': pend['sl'], 'entry_time': stamp(day[i], minute[i], k), 'fill': price,
                 'risk_dollars': (price - pend['sl']) / fac[i] * POINT_VALUE, 'flat_fill': flat_fill,
                 'gross': 0.0, 'pieces': 0, 'rolls': 0}
        pend = None
        leg = (trade['entry_time'], price)

    def close_piece(i, k, price, why):
        nonlocal leg
        gross = (price - leg[1]) / fac[i] * POINT_VALUE
        trade['gross'] += gross
        trade['pieces'] += 1
        pieces.append({'trade': len(trades), 'entry_time': leg[0], 'entry_price': leg[1],
                       'exit_time': stamp(day[i], minute[i], k), 'exit_price': price, 'reason': why,
                       'gross': gross})
        leg = None

    def end_trade(i, k, why):
        nonlocal trade
        trades.append({**trade, 'exit_time': stamp(day[i], minute[i], k), 'reason': why})
        trade = None

    def weekly_order(i, p):
        """EA placement at a new week with no position: a red week replaces the pending order."""
        nonlocal pend
        w = week_of[i]
        if w == 0:
            return
        wo, wh, wl, wc = weeks[w - 1]
        week = stamp(day[starts[w - 1]], 0, 0)
        if control == 'plain':
            if wh - wl > 0:
                pend = {'week': week, 'submitted': stamp(day[i], minute[i], 0),
                        'requested': p + spread, 'sl': p + spread - (wh - wl)}
                start_trade(i, 0, p + spread)
            return
        if is_signal(wo, wc, signal):
            pend = None
            if control == 'signal_market':
                if p + spread <= wl:
                    counts['rejected'] += 1
                    return
                pend = {'week': week, 'submitted': stamp(day[i], minute[i], 0), 'requested': p + spread, 'sl': wl}
                start_trade(i, 0, p + spread)
                return
            if wh - wl <= 0:
                return
            if wh <= p:
                counts['rejected'] += 1
                return
            pend = {'week': week, 'submitted': stamp(day[i], minute[i], 0), 'requested': wh, 'sl': wl}

    def target_hit(i):
        w = week_of[i]
        return weeks[w - 1][3] >= trade['fill'] + rr * (trade['fill'] - trade['sl'])

    for i in range(n):
        first_day = i == 0 or date[i] != date[i - 1]
        first_week = i == 0 or week_of[i] != week_of[i - 1]
        k0 = 0
        if mode == 'hold':
            if trade is not None and first_day and i:      # mark the held position at each session close
                close_piece(i - 1, 3, c[i - 1], 'mark')
                leg = (stamp(day[i - 1], minute[i - 1], 3), c[i - 1])
                trade['rolls'] += int(contracts[i] != contracts[i - 1])
            if first_week:
                k0 = 1
                p = o[i]
                if trade is not None and p <= trade['sl']:          # tester triggers come before OnTick
                    close_piece(i, 0, trade['sl'] if fills == 'mt5' else p, 'sl')
                    end_trade(i, 0, 'sl')
                if trade is None and pend is not None and p >= pend['requested']:
                    start_trade(i, 0, pend['requested'] if fills == 'mt5' else p)
                if trade is not None:
                    if week_of[i] and target_hit(i):
                        counts['target_weeks_red'] += int(weeks[week_of[i] - 1][3] < weeks[week_of[i] - 1][0])
                        close_piece(i, 0, p, 'target')
                        end_trade(i, 0, 'target')
                else:
                    weekly_order(i, p)
        else:
            if first_day:
                live = True
                cut = cutoffs.get(date[i], CUTOFF)
                p = o[i]
                k0 = 1
                blocked = False
                if trade is not None and first_week and target_hit(i):
                    counts['target_weeks_red'] += int(weeks[week_of[i] - 1][3] < weeks[week_of[i] - 1][0])
                    end_trade(i, 0, 'target')
                    blocked = True
                if minute[i] >= cut:
                    live = False
                elif trade is not None:
                    if p > trade['sl']:
                        leg = (stamp(day[i], minute[i], 0), p)
                    else:
                        counts['gap_stops'] += 1
                        end_trade(i, 0, 'gap_stop')
                elif pend is not None and p >= pend['requested']:
                    counts['flat_fills'] += 1
                    start_trade(i, 0, p, flat_fill=True)
                if first_week and not blocked and trade is None:
                    weekly_order(i, p)
            if live and minute[i] >= cut:
                if leg is not None:
                    close_piece(i, 0, o[i], 'flatten')
                live = False
            if not live:
                continue
        if (pend is None or h[i] < pend['requested']) and (leg is None or l[i] > trade['sl']):
            if mode == 'flat' and leg is not None and (i + 1 == n or date[i + 1] != date[i]):
                counts['no_cutoff_bar'] += 1
                close_piece(i, 3, c[i], 'session_end')
                live = False
            continue
        ticks = path(o[i], h[i], l[i], c[i])
        for k in range(k0, 4):
            p = ticks[k]
            gap = fills == 'gap' and k == 0      # only a bar's open can jump past a level
            if leg is not None and p <= trade['sl']:
                close_piece(i, k, p if gap else trade['sl'], 'sl')
                end_trade(i, k, 'sl')
            if pend is not None and trade is None and p >= pend['requested']:
                start_trade(i, k, p if gap else pend['requested'])
        if mode == 'flat' and leg is not None and (i + 1 == n or date[i + 1] != date[i]):
            counts['no_cutoff_bar'] += 1
            close_piece(i, 3, c[i], 'session_end')
            live = False
    if trade is not None:
        if leg is not None:
            close_piece(n - 1, 3, c[n - 1], 'end_of_data')
        end_trade(n - 1, 3, 'end_of_data')
    return pd.DataFrame(trades), pd.DataFrame(pieces), counts
