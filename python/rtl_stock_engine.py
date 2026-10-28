"""RTL M30 order logic on minute bars: stocks, and the check against MT5 on NQ.

The order logic is the MT5 EA emulation of rtl_weekly_engine.simulate_m30_ea: red-bar signal,
pending buy-stop maintenance, RR bar-close exit, cutoff flatten and next-session fallback.
Protocol: docs/baseline/rtl-vwap/STOCK_PROTOCOL.md. Two fill models:
'mt5' fills stops at their level, as MT5's 1-minute OHLC tester does (reproduces NQ exactly);
'gap' fills at a minute's open when that open is already beyond the level (stocks).
Within a minute, ticks follow MT5's order: open, low/high, close at :00/:20/:40/:59.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
NQ_MINUTES = Path(r'F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv')
NQ_CALENDAR = ROOT / 'mt5/experts/early_closes.mqh'
NQ_CUTOFF = 23 * 60 + 30
TICK_SECONDS = (0, 20, 40, 59)


def nq_minutes():
    """NQ minute arrays in the EA's source clock."""
    d = pd.read_csv(NQ_MINUTES, sep='\t', usecols=[0, 1, 2, 3, 4, 5], header=0,
                    names=['date', 'time', 'o', 'h', 'l', 'c'], dtype={'date': str, 'time': str})
    t = pd.to_datetime(d.date+' '+d.time, format='%Y.%m.%d %H:%M:%S')
    return minute_arrays(t, d.o, d.h, d.l, d.c)


def nq_cutoffs():
    """Flatten minute per session date from the EA's early-close calendar."""
    text = NQ_CALENDAR.read_text(encoding='utf-8')
    dates = [int(x) for x in re.search(r'EC_DATE\[EC_COUNT\] = \{([^}]+)', text).group(1).split(',')]
    times = [int(x) for x in re.search(r'EC_FLAT_MIN\[EC_COUNT\] = \{([^}]+)', text).group(1).split(',')]
    return dict(zip(dates, times))


def minute_arrays(times, o, h, l, c):
    """Arrays date (yyyymmdd), day (days since 1970), minute (of day), o/h/l/c."""
    times = pd.DatetimeIndex(times)
    day = times.normalize().to_numpy().astype('datetime64[D]').astype(np.int64)
    bars = {'date': (times.year*10000+times.month*100+times.day).to_numpy(np.int64), 'day': day,
            'minute': (times.hour*60+times.minute).to_numpy(np.int64),
            **{k: np.asarray(v, np.float64) for k, v in zip('ohlc', (o, h, l, c))}}
    assert (np.diff(day*1440+bars['minute']) > 0).all(), 'minutes must be strictly increasing'
    return bars


def low_first(o, c):
    """Per minute: True when MT5 goes open, low, high, close (a flat minute repeats the last move)."""
    move = np.sign(c - o)
    last = pd.Series(np.where(move != 0, move, np.nan)).ffill().shift(1).fillna(0).to_numpy()
    return (move > 0) | ((move == 0) & (last < 0))


def stamp(day, minute, k):
    return np.datetime64(int(day), 'D') + np.timedelta64(int(minute) * 60 + TICK_SECONDS[k], 's')


def simulate(bars, cutoffs=None, default_cutoff=NQ_CUTOFF, fills='mt5', rr=1.0, first_order_minute=60):
    """RTL on M30 bars built from the minutes; one position at a time."""
    assert fills in ('mt5', 'gap')
    cutoffs = cutoffs or {}
    gap = fills == 'gap'
    date, day, minute = bars['date'], bars['day'], bars['minute']
    o, h, l, c = bars['o'], bars['h'], bars['l'], bars['c']
    n = len(o)
    slot = day * 48 + minute // 30
    lf = low_first(o, c)
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
        if not new and (pend is None or h[i] < pend['requested']):
            if pos is None or l[i] > pos['sl']:
                continue
        ticks = (o[i], l[i], h[i], c[i]) if lf[i] else (o[i], h[i], l[i], c[i])
        for k, p in enumerate(ticks):
            if pos is not None and p <= pos['sl']:
                close(i, k, p if gap and k == 0 else pos['sl'], 'sl')
            if pend is not None and p >= pend['requested']:
                fill = p if gap and k == 0 else pend['requested']
                pos = {**pend, 'entry_time': stamp(day[i], minute[i], k), 'fill': fill}
                pend = None
            if k or not new:
                continue
            # ---- first tick of a new M30 bar
            bar_date, bar_min = date[i], (minute[i] // 30) * 30
            if prev_date and bar_date != prev_date and last_flat != prev_date:
                last_flat = prev_date
                if pos is not None:
                    close(i, k, p, 'fallback')
                pend = None
            prev_date = bar_date
            if bar_min >= cutoffs.get(bar_date, default_cutoff):
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
            if bar_min < first_order_minute:
                pend = None
                continue
            if bar1 is not None and bar1[3] < bar1[0]:
                pend = None
                if bar1[1] - bar1[2] <= 0:
                    continue
                if bar1[1] <= p:
                    rejected += 1
                    continue
                pend = {'submitted': stamp(day[i], minute[i], 0), 'requested': bar1[1], 'sl': bar1[2]}
    if pos is not None:
        close(n - 1, 3, c[n - 1], 'end_of_data')
    return pd.DataFrame(trades), rejected
