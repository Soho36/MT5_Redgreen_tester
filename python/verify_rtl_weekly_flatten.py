"""Independent check of the primary 'W1 flatten' ledger (protocol step 3).

Rebuilds weekly bars (pandas weekly periods), the roll factor (from the rolls file) and
the calendar cutoffs on its own, then steps session by session, finding the first stop or
entry crossing in each live window with numpy. Every trade and daily piece of
Reports/rtl_weekly_flatten_20261027/trades_W1_flatten.csv and pieces_W1_flatten.csv must
match: times to the second, prices, exit reasons and dollars.
"""
import json
import re

import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / 'Reports/rtl_weekly_flatten_20261027'
ROLLS = r'F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_rolls.csv'
LAST_DATE = 20260930
SECONDS = (0, 20, 40, 59)


def ticks(o, h, l, c, previous_move):
    """MT5 1-minute OHLC order; a flat minute follows the last minute that moved (rose: high first)."""
    if c > o or (c == o and previous_move < 0):
        return (o, l, h, c)
    return (o, h, l, c)


def main():
    with np.load(STUDY / 'minutes.npz') as z:
        m = pd.DataFrame({k: z[k] for k in ('date', 'minute', 'o', 'h', 'l', 'c')})
    m = m[m.date <= LAST_DATE].reset_index(drop=True)
    when = pd.to_datetime(m.date.astype(str), format='%Y%m%d')
    # roll factor per session date, from the contract switches
    rolls = pd.read_csv(ROLLS)
    switch = rolls.date[rolls.symbol != rolls.symbol.shift()].iloc[1:].str.replace('-', '').astype(int)
    first = m.groupby('date').head(1)
    last = m.groupby('date').tail(1)
    dates = first.date.to_numpy()
    step = np.ones(len(dates))
    for s in switch[switch <= LAST_DATE]:
        k = int(np.flatnonzero(dates == s)[0])
        step[k - 1] = first.o.iloc[k] / last.c.iloc[k - 1]      # applies to every session before s
    factor_by_date = pd.Series(np.cumprod(step[::-1])[::-1], index=dates)
    f = factor_by_date[m.date].to_numpy()
    o, h, l, c = (m[x].to_numpy() * f for x in 'ohlc')
    previous_move = np.zeros(len(o))     # direction of the last earlier minute whose close differs from its open
    move = 0.0
    for j, (oj, cj) in enumerate(zip(m.o.to_numpy(), m.c.to_numpy())):
        previous_move[j] = move
        if cj != oj:
            move = 1.0 if cj > oj else -1.0
    # weekly bars on the adjusted prices
    week = when.dt.to_period('W-SUN')
    wk = pd.DataFrame({'week': week, 'o': o, 'h': h, 'l': l, 'c': c}).groupby('week').agg(
        o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'))
    week_pos = pd.Series(np.arange(len(wk)), index=wk.index)[week].to_numpy()
    text = (ROOT / 'mt5/experts/early_closes.mqh').read_text()
    ec = dict(zip(*(map(int, re.search(name + r'\[EC_COUNT\] = \{([^}]+)', text).group(1).split(','))
                    for name in ('EC_DATE', 'EC_FLAT_MIN'))))
    starts = first.index.to_numpy()
    ends = np.r_[starts[1:], len(m)]
    minute = m.minute.to_numpy()

    def stamp(j, k):
        return when[j] + pd.Timedelta(seconds=int(minute[j]) * 60 + SECONDS[k])

    trades, pieces = [], []
    trade = pend = leg = None

    def open_piece(j, k, price):
        nonlocal leg
        leg = (stamp(j, k), price)

    def close_piece(j, k, price, why):
        nonlocal leg
        gross = (price - leg[1]) / f[j] * 2.0
        pieces.append({'trade': len(trades), 'entry_time': leg[0], 'entry_price': leg[1],
                       'exit_time': stamp(j, k), 'exit_price': price, 'reason': why, 'gross': gross})
        trade['gross'] += gross
        trade['pieces'] += 1
        leg = None

    def finish(j, k, why):
        nonlocal trade
        trades.append({**trade, 'exit_time': stamp(j, k), 'reason': why})
        trade = None

    def begin(j, k, price):
        nonlocal trade, pend
        trade = {'requested': pend[0], 'sl': pend[1], 'entry_time': stamp(j, k), 'fill': price,
                 'risk_dollars': (price - pend[1]) / f[j] * 2.0, 'gross': 0.0, 'pieces': 0}
        pend = None
        open_piece(j, k, price)

    def first_tick(j, k0, test):
        for k, p in enumerate(ticks(o[j], h[j], l[j], c[j], previous_move[j])):
            if k >= k0 and test(p):
                return k, p
        return None

    for d, (a, e) in enumerate(zip(starts, ends)):
        cutoff = ec.get(int(m.date[a]), 1410)
        live_end = a + int(np.searchsorted(minute[a:e], cutoff))
        new_week = d == 0 or week_pos[a] != week_pos[starts[d - 1]]
        w = week_pos[a]
        p = o[a]
        blocked = False
        if new_week and trade is not None and wk.c.iloc[w - 1] >= trade['fill'] * 2 - trade['sl']:
            finish(a, 0, 'target')
            blocked = True
        if trade is not None:
            if p > trade['sl']:
                open_piece(a, 0, p)
            else:
                finish(a, 0, 'gap_stop')
        elif pend is not None and p >= pend[0]:
            begin(a, 0, p)
        if new_week and w > 0 and not blocked and trade is None:
            prev = wk.iloc[w - 1]
            if prev.c < prev.o:
                pend = (prev.h, prev.l) if prev.h > p and prev.h > prev.l else None
        pos, k0 = a, 1
        while pos < live_end:
            if leg is not None:
                hits = np.flatnonzero(l[pos:live_end] <= trade['sl'])
                if not len(hits):
                    break
                j = pos + int(hits[0])
                hit = first_tick(j, k0 if j == pos else 0, lambda x: x <= trade['sl'])
                if hit is None:
                    pos, k0 = j + 1, 0
                    continue
                close_piece(j, hit[0], hit[1] if hit[0] == 0 else trade['sl'], 'sl')
                finish(j, hit[0], 'sl')
                break
            if pend is not None:
                hits = np.flatnonzero(h[pos:live_end] >= pend[0])
                if not len(hits):
                    break
                j = pos + int(hits[0])
                hit = first_tick(j, k0 if j == pos else 0, lambda x: x >= pend[0])
                if hit is None:
                    pos, k0 = j + 1, 0
                    continue
                begin(j, hit[0], hit[1] if hit[0] == 0 else pend[0])
                pos, k0 = j, hit[0] + 1
                continue
            break
        if leg is not None:
            if live_end < e:
                close_piece(live_end, 0, o[live_end], 'flatten')
            else:
                close_piece(e - 1, 3, c[e - 1], 'session_end')
    if trade is not None:
        finish(len(m) - 1, 3, 'end_of_data')

    mine, mine_p = pd.DataFrame(trades), pd.DataFrame(pieces)
    eng = pd.read_csv(STUDY / 'trades_W1_flatten.csv', parse_dates=['entry_time', 'exit_time'])
    eng_p = pd.read_csv(STUDY / 'pieces_W1_flatten.csv', parse_dates=['entry_time', 'exit_time'])
    assert len(mine) == len(eng), (len(mine), len(eng))
    assert len(mine_p) == len(eng_p), (len(mine_p), len(eng_p))
    for col in ('entry_time', 'exit_time', 'reason', 'pieces'):
        assert (mine[col].to_numpy() == eng[col].to_numpy()).all(), col
    for col in ('requested', 'sl', 'fill', 'risk_dollars', 'gross'):
        assert np.allclose(mine[col], eng[col], rtol=0, atol=1e-6), col
    for col in ('trade', 'entry_time', 'exit_time', 'reason'):
        assert (mine_p[col].to_numpy() == eng_p[col].to_numpy()).all(), col
    for col in ('entry_price', 'exit_price', 'gross'):
        assert np.allclose(mine_p[col], eng_p[col], rtol=0, atol=1e-6), col
    # piece dollars equal raw-price differences
    raw = (mine_p.exit_price - mine_p.entry_price) / f[np.searchsorted(when.to_numpy(), mine_p.exit_time.dt.normalize().to_numpy())] * 2
    assert np.allclose(raw, mine_p.gross)
    result = {'trades': len(mine), 'pieces': len(mine_p), 'match': True,
              'reasons': mine.reason.value_counts().to_dict(), 'piece_reasons': mine_p.reason.value_counts().to_dict()}
    (STUDY / 'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
