"""RTL mirrored: sell limit at the red M30 candle's high (user experiment, 2026-11-16).

Protocol: docs/baseline/rtl-sell-limit-fade/PROTOCOL.md.

Usage: rtl_sell_limit_fade.py prepare | analyze
  prepare  writes the EA, its INIs and a manifest to the run folder; then run
           python/run_mt5_job.py <run folder> RTL_red_high_sell_limit
  analyze  reads the native reports, rebuilds every trade from the raw minutes with
           simulate_fade() and writes the tables and chart.

simulate_fade() mirrors rtl_weekly_engine.simulate_m30_ea. MT5 tester conventions for the
short side on MNQcontDTBNT20102026_2 (measured on the saved red-short control, 18,040 trades):
a stop fills at its level on the first quote that reaches it, and a market buy fills one
tick (0.25) above the quote.
"""
from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import rtl_weekly_engine as e
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / 'Reports/rtl_sell_limit_fade_20261116'
DOC = ROOT / 'docs/baseline/rtl-sell-limit-fade'
SOURCE = ROOT / 'mt5/experts/shorts/RTL_red_high_sell_limit.cs'
CACHE = ROOT / 'Reports/rtl_weekly_flatten_20261027/minutes.npz'
EXPERT = 'RTL_red_high_sell_limit'
SYMBOL = 'MNQcontDTBNT20102026_2'
# arm -> (ExitMode, AllowOrderAtMarket). The first two follow the protocol; the '_atmarket' arms let MT5
# fill a sell limit that is already at or below the market (it never rejects one, unlike a buy stop).
ARMS = {'close': (0, False), 'tp': (1, False), 'close_atmarket': (0, True), 'tp_atmarket': (1, True)}
PRIMARY = ('close', 'tp')
LABELS = {'close': 'Sell limit, bar-close exit', 'tp': 'Sell limit, take profit at the low',
          'close_atmarket': 'Bar-close exit, orders at the market allowed',
          'tp_atmarket': 'Take profit, orders at the market allowed', 'rtl': 'RTL long (baseline)',
          'close_through': 'Bar-close exit, filled only one tick through the price',
          'tp_through': 'Take profit, filled only one tick through the price'}
FIRST_BUILD = {'close_atmarket': 'close', 'tp_atmarket': 'tp'}   # same behaviour as the first EA build's runs
TICK = 0.25
POINT_VALUE = 2.0
COST = 1.05
END = '2026-10-01'
PERIODS = {'2010-15': ('2010-01-01', '2016-01-01'), '2016-19': ('2016-01-01', '2020-01-01'),
           '2020-26': ('2020-01-01', END), '2016-26': ('2016-01-01', END)}
WINDOWS = ['W0000W0100', 'W0100W0130', 'W0130W0200'] + [f'W{h:02d}00W{h + 1:02d}00' for h in range(2, 23)] + [
    'W2300W2330', 'W2330W0000']


def tag(arm):
    return 'selllimit_20261116_' + arm


# ---------------------------------------------------------------- simulator

def simulate_fade(bars, cutoffs=None, last_date=None, rr=1.0, resting_tp=False, tp_spread=0.0, at_market=False,
                  through=0.0):
    """The EA on M30 from 1-minute bars: sell limit at the last red candle's high while flat,
    stop one candle range above, RTL's order lifetime, windows and flatten.
    resting_tp False: buy back at the next bar's first quote after a bar closes at or below
    entry - rr x (stop - entry). True: a take profit rests at high - rr x range instead and
    fills at its level once quote + tp_spread reaches it.
    at_market False: no order when the new bar opens at or above the high (RTL's buy stop is
    rejected there). True: MT5's own handling, an immediate fill at that opening quote.
    through: the resting order fills (still at its price) only once a quote is this far above
    it. 0 is MT5's rule, a touch fills; one tick is the cautious case for a real limit order.
    Returns (trades, orders not placed)."""
    cutoffs = cutoffs or {}
    date, day, minute = bars['date'], bars['day'], bars['minute']
    o, h, l, c = bars['o'], bars['h'], bars['l'], bars['c']
    n = len(o) if last_date is None else int(np.searchsorted(date, last_date, side='right'))
    slot = day * 48 + minute // 30
    lf = e.low_first(o, c)
    trades, rejected = [], 0
    pend = pos = None
    last_flat = prev_date = 0
    bar1 = cur = None
    cur_slot = -1

    def close(i, k, price, why):
        nonlocal pos
        trades.append({**pos, 'exit_time': e.stamp(day[i], minute[i], k), 'exit_price': price, 'reason': why})
        pos = None

    for i in range(n):
        new = slot[i] != cur_slot
        if new:
            bar1 = cur
            cur = [o[i], h[i], l[i], c[i]]
            cur_slot = slot[i]
        else:
            cur[1] = max(cur[1], h[i]); cur[2] = min(cur[2], l[i]); cur[3] = c[i]
        if not new and (pend is None or h[i] < pend['requested'] + through):
            if pos is None:
                continue
            if h[i] < pos['sl'] and (pos['tp'] is None or l[i] + tp_spread > pos['tp']):
                continue
        for k, p in enumerate(e.path(o[i], h[i], l[i], c[i], lf[i])):
            # Attached exits are checked before a pending entry; a fresh fill's exits
            # become executable on the next quote.
            if pos is not None and p >= pos['sl']:
                close(i, k, pos['sl'], 'sl')
            if pos is not None and pos['tp'] is not None and p + tp_spread <= pos['tp']:
                close(i, k, pos['tp'], 'tp')
            if pend is not None and p >= pend['requested'] + through:
                pos = {**pend, 'entry_time': e.stamp(day[i], minute[i], k), 'fill': pend['requested']}
                pend = None
            if k or not new:
                continue
            # ---- OnTick at the first tick of a new M30 bar
            bar_date, bar_min = date[i], (minute[i] // 30) * 30
            if prev_date and bar_date != prev_date and last_flat != prev_date:
                last_flat = prev_date
                if pos is not None:
                    close(i, k, p + TICK, 'fallback')
                pend = None
            prev_date = bar_date
            if bar_min >= cutoffs.get(bar_date, e.CUTOFF):
                if last_flat != bar_date:
                    last_flat = bar_date
                    if pos is not None:
                        close(i, k, p + TICK, 'flatten')
                    pend = None
                continue
            if pos is not None:
                if pos['tp'] is None and bar1[3] <= pos['fill'] - rr * (pos['sl'] - pos['fill']):
                    close(i, k, p + TICK, 'target')
                continue
            if bar_min < 60:
                pend = None
                continue
            if bar1 is not None and bar1[3] < bar1[0]:
                pend = None
                rng = bar1[1] - bar1[2]
                if rng <= 0:
                    continue
                order = {'submitted': e.stamp(day[i], minute[i], 0), 'requested': bar1[1], 'sl': bar1[1] + rng,
                         'tp': bar1[1] - rr * rng if resting_tp else None}
                if bar1[1] > p:
                    pend = order
                elif at_market:
                    pos = {**order, 'entry_time': order['submitted'], 'fill': p}
                else:
                    rejected += 1
    if pos is not None:
        close(n - 1, 3, c[n - 1] + TICK, 'end_of_data')
    return pd.DataFrame(trades), rejected


# ---------------------------------------------------------------- native run files

def prepare():
    if (RUN / 'manifest.json').exists():
        raise RuntimeError('Preserve prepared study')
    assert (DOC / 'PROTOCOL.md').exists(), 'Write the protocol before preparing outcomes'
    RUN.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, RUN / (EXPERT + '.mq5'))
    shutil.copyfile(ROOT / 'mt5/experts/early_closes.mqh', RUN / 'early_closes.mqh')
    jobs = []
    for arm, (mode, at_market) in ARMS.items():
        inputs = dict(Lots='1.0', RiskReward='1.0', Slippage='5', EntryOffsetTicks='0',
                      AllowOrderAtMarket=str(at_market).lower(), ExitMode=str(mode), UseFlattenEnd='true', FlattenHourEnd='23', FlattenMinuteEnd='30', FlattenFallback='true',
                      UseEarlyCloseCalendar='true', ServerClock='0', UseTradeWindow='true', RunTag=tag(arm))
        inputs.update({w: 'false' if w in ('W0000W0100', 'W2330W0000') else 'true' for w in WINDOWS})
        declared = [line.split('=')[0].split()[-1] for line in SOURCE.read_text(encoding='utf-8').splitlines()
                    if line.startswith('input ')]
        assert sorted(declared) == sorted(inputs), set(declared) ^ set(inputs)   # the tester remembers omitted inputs
        tester = dict(Expert=f'CodexResearch\\{EXPERT}.ex5', Symbol=SYMBOL, Period='M30', Optimization=0, Model=1,
                      FromDate='2010.06.07', ToDate='2026.10.15', ForwardMode=0, Deposit=500000, Currency='USD',
                      ProfitInPips=0, Leverage=100, ExecutionMode=0, OptimizationCriterion=0, Visual=0, UseLocal=1,
                      UseRemote=0, UseCloud=0, ShutdownTerminal=1, Report=tag(arm) + '.htm', ReplaceReport=1)
        lines = (['[Tester]'] + [f'{k}={v}' for k, v in tester.items()] + ['[TesterInputs]']
                 + [f'{k}={v}' for k, v in inputs.items()]
                 + ['[Experts]', 'Enabled=0', 'AllowLiveTrading=0', 'AllowDllImport=0'])
        (RUN / (tag(arm) + '.ini')).write_text('\n'.join(lines) + '\n', encoding='utf-16')
        jobs.append(dict(tag=tag(arm), arm=arm, exit_mode=mode, allow_order_at_market=at_market,
                         outputs=[f'sell_limit_{tag(arm)}_1.00.csv', f'sell_limit_{tag(arm)}_1.00_stats.csv']))
    (RUN / 'manifest.json').write_text(json.dumps(dict(expert=EXPERT, symbol=SYMBOL, jobs=jobs), indent=2),
                                       encoding='utf-8')
    print('Prepared', RUN)


def parse_report(path):
    """Sell-limit orders and sell-in / buy-out deal pairs from an MT5 tester report."""
    from analyze_rtl_vwap_cross import CELL, TAG, STAMP, number
    orders, trades, active, section = {}, [], None, None
    with Path(path).open(encoding='utf-16') as stream:
        for line in stream:
            if '>Orders<' in line:
                section = 'orders'
            elif '>Deals<' in line:
                section = 'deals'
            if '<tr' not in line or '</tr>' not in line:
                continue
            cells = [html.unescape(TAG.sub('', text)).strip() for text in CELL.findall(line)]
            if not cells or not STAMP.match(cells[0]):
                continue
            if section == 'orders' and len(cells) == 11 and cells[3] == 'sell limit':
                assert cells[2] == SYMBOL, cells
                orders[int(cells[1])] = dict(submitted=cells[0], requested=number(cells[5]), sl=number(cells[6]),
                                             tp=number(cells[7]) if cells[7] else np.nan, state=cells[9])
            elif section == 'deals' and len(cells) == 13 and cells[3] != 'balance':
                assert cells[2] == SYMBOL and number(cells[5]) == 1, cells
                assert number(cells[8]) == 0 and number(cells[9]) == 0, cells      # no commission or swap in the tester
                if cells[3:5] == ['sell', 'in']:
                    assert active is None, cells
                    ticket = int(cells[7])
                    assert orders[ticket]['state'] == 'filled', cells
                    active = dict(orders[ticket], ticket=ticket, entry_time=cells[0], fill=number(cells[6]))
                elif cells[3:5] == ['buy', 'out']:
                    assert active is not None, cells
                    trades.append(dict(active, exit_time=cells[0], exit_price=number(cells[6]),
                                       trade_profit=number(cells[10]), comment=cells[12]))
                    active = None
                else:
                    raise ValueError(f'Unsupported deal {cells[3:5]}')
    assert active is None and trades
    frame = pd.DataFrame(trades).drop(columns='state')
    for column in ('submitted', 'entry_time', 'exit_time'):
        frame[column] = pd.to_datetime(frame[column], format='%Y.%m.%d %H:%M:%S')
    frame['reason'] = np.select([frame.comment.str.startswith('sl'), frame.comment.str.startswith('tp'),
                                 frame.comment.str.startswith('end of test')], ['sl', 'tp', 'end_of_data'], 'market')
    counts = pd.Series([o['state'] for o in orders.values()]).value_counts().to_dict()
    return frame, counts


# ---------------------------------------------------------------- economics

def economics(frame, short=True):
    """One MNQ: gross dollars from the fills, R on the order's planned stop distance (the
    candle's range; an order filled at the market can sit closer to its stop), $1.05 per trade."""
    frame = frame.copy()
    for column in ('submitted', 'entry_time', 'exit_time'):
        frame[column] = pd.to_datetime(frame[column])
    side = -1.0 if short else 1.0
    frame['gross'] = side * (frame.exit_price - frame.fill) * POINT_VALUE
    frame['risk'] = side * (frame.requested - frame.sl) * POINT_VALUE
    assert frame.risk.gt(0).all()
    frame['net'] = frame.gross - COST
    frame['gross_r'] = frame.gross / frame.risk
    frame['net_r'] = frame.net / frame.risk
    frame['session'] = frame.submitted.dt.normalize()
    return frame


def max_dd(pnl):
    equity = np.r_[0., np.asarray(pnl, float).cumsum()]
    return float((np.maximum.accumulate(equity) - equity).max())


def metrics(part, calendar):
    """Period metrics; drawdown on daily closed profit over every session of the period."""
    if not len(part):
        return dict(trades=0)
    net = part.net
    losses = -net[net < 0].sum()
    daily = part.groupby(part.exit_time.dt.normalize()).net.sum().reindex(calendar, fill_value=0.)
    reasons = part.reason.replace({'fallback': 'flatten', 'market_flat': 'flatten'}).value_counts(normalize=True)
    return dict(trades=len(part), net=float(net.sum()), gross=float(part.gross.sum()),
                win_pct=float(100 * net.gt(0).mean()), profit_factor=float(net[net > 0].sum() / losses),
                gross_mean_r=float(part.gross_r.mean()), net_mean_r=float(part.net_r.mean()),
                cost_r=float((COST / part.risk).mean()), daily_dd=max_dd(daily),
                net_plus_1_dollar=float(net.sum() - len(part)),
                stop_pct=float(100 * reasons.get('sl', 0.)),
                target_pct=float(100 * (reasons.get('target', 0.) + reasons.get('tp', 0.))),
                flatten_pct=float(100 * reasons.get('flatten', 0.)))


def weekly_interval(part, draws=2000, seed=20261116):
    """95% interval of the mean net R, resampling whole weeks."""
    week = part.session - pd.to_timedelta(part.session.dt.dayofweek, unit='D')
    g = part.groupby(week).net_r.agg(['sum', 'count']).to_numpy()
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(g), size=(draws, len(g)))
    means = g[pick, 0].sum(axis=1) / g[pick, 1].sum(axis=1)
    return float(np.quantile(means, .025)), float(np.quantile(means, .975))


# ---------------------------------------------------------------- analysis

def label_native(frame, cutoffs):
    """Split MT5's market buy-backs into the bar-close target and the session flatten."""
    frame = frame.copy()
    minute = frame.exit_time.dt.hour * 60 + frame.exit_time.dt.minute
    date = (frame.exit_time.dt.year * 10000 + frame.exit_time.dt.month * 100 + frame.exit_time.dt.day).astype(int)
    cut = date.map(lambda d: cutoffs.get(d, e.CUTOFF))
    late = (minute >= cut) | (frame.exit_time.dt.normalize() > frame.entry_time.dt.normalize())
    market = frame.reason.eq('market')
    frame.loc[market & late, 'reason'] = 'flatten'
    frame.loc[market & ~late, 'reason'] = 'target'
    return frame


def compare(native, sim):
    """Trade-by-trade agreement of the native run and the minute replay, from the first
    session after the tester's own start-up (it trades only after ~100 chart bars)."""
    start = native.submitted.min().normalize() + pd.Timedelta(days=1)
    a = native.loc[native.submitted.ge(start) & native.submitted.lt(END)].reset_index(drop=True)
    b = sim.loc[sim.submitted.ge(start) & sim.submitted.lt(END)].reset_index(drop=True)
    b = b.assign(reason=b.reason.replace('fallback', 'flatten'))
    result = dict(compared_from=str(start.date()), native_trades=len(a), replay_trades=len(b))
    if len(a) != len(b):
        merged = a.merge(b, on='submitted', how='outer', indicator=True)
        result.update(same_count=False, only_native=int(merged._merge.eq('left_only').sum()),
                      only_replay=int(merged._merge.eq('right_only').sum()),
                      first_difference=str(merged.loc[merged._merge.ne('both'), 'submitted'].min()))
        return result
    # Times to the minute: in a minute with fewer than four ticks MT5 stamps its quotes at :01 or :30.
    checks = dict(submitted_minute=a.submitted.dt.floor('min').eq(b.submitted.dt.floor('min')),
                  entry_price=a.requested.eq(b.requested) & a.fill.eq(b.fill),
                  stop=a.sl.eq(b.sl), entry_minute=a.entry_time.dt.floor('min').eq(b.entry_time.dt.floor('min')),
                  exit_minute=a.exit_time.dt.floor('min').eq(b.exit_time.dt.floor('min')),
                  exit_price=a.exit_price.eq(b.exit_price), reason=a.reason.eq(b.reason))
    result.update(same_count=True, mismatches={k: int((~v).sum()) for k, v in checks.items()})
    bad = ~np.logical_and.reduce(list(checks.values()))
    result['all_trades_identical'] = not bad.any()
    if bad.any():
        result['mismatching_trades'] = [
            dict(submitted=str(x.submitted), native_exit=str(x.exit_time), replay_exit=str(y.exit_time),
                 native_exit_price=x.exit_price, replay_exit_price=y.exit_price)
            for x, y in zip(a[bad].head(5).itertuples(), b[bad].head(5).itertuples())]
    return result


def plot(curves, calendar):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cal = calendar[(calendar >= '2016-01-01') & (calendar < END)]
    fig, ax = plt.subplots(figsize=(11, 5.5), layout='constrained')
    for name, frame in curves.items():
        part = frame.loc[frame.session.ge('2016-01-01') & frame.session.lt(END)]
        equity = part.groupby(part.exit_time.dt.normalize()).net.sum().reindex(cal, fill_value=0.).cumsum()
        ax.plot(equity.index, equity, label=LABELS[name], lw=1.4)
    ax.axhline(0, color='gray', lw=.6)
    ax.grid(alpha=.2)
    ax.legend()
    ax.set_ylabel('Cumulative net USD')
    ax.set_title('NQ: sell limit at the red M30 high (RTL mirrored) against RTL\n'
                 'One MNQ, $1.05 per trade, 2016 - September 2026, MT5 1-minute OHLC')
    (DOC / 'img').mkdir(parents=True, exist_ok=True)
    fig.savefig(DOC / 'img/equity.png', dpi=150)
    plt.close(fig)


def analyze():
    bars = e.load_minutes(CACHE)
    cutoffs = e.load_cutoffs()
    calendar = pd.DatetimeIndex(np.unique(bars['day']).astype('datetime64[D]'))
    curves, verification, rows, annual = {}, {}, [], []
    for arm, (mode, at_market) in ARMS.items():
        done = json.loads((RUN / (tag(arm) + '.completed.json')).read_text(encoding='utf-8'))
        native, order_states = parse_report(RUN / (tag(arm) + '.htm'))
        ledger_file = RUN / f'sell_limit_{tag(arm)}_1.00.csv'
        ledger = pd.read_csv(ledger_file, sep='\t', encoding='utf-16')
        stats = pd.read_csv(RUN / f'sell_limit_{tag(arm)}_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
        native = label_native(native, cutoffs)
        # the report, the EA's own ledger and MT5's totals must tell the same story
        assert len(native) == int(stats.trades)
        assert np.allclose(native.trade_profit, (native.fill - native.exit_price) * POINT_VALUE, atol=1e-8, rtol=0)
        assert np.isclose(native.trade_profit.sum(), stats.net_profit, atol=1e-6, rtol=0)
        # a resting sell limit fills exactly at its price; only an order sent at the market fills better
        immediate = native.entry_time.eq(native.submitted)
        assert native.fill[~immediate].eq(native.requested[~immediate]).all() and native.fill.ge(native.requested).all()
        assert at_market or not immediate.any()
        assert (int(stats.exit_mode), bool(stats.allow_order_at_market)) == (mode, at_market)
        # The EA's ledger misses a trade that opens and closes between two of its ticks: an order
        # sent at the market and stopped on the very next quote. Only the '_atmarket' arms have any.
        logged = native.ticket.isin(ledger.ticket)
        unlogged = native.loc[~logged]
        assert at_market or not len(unlogged)
        assert unlogged.entry_time.eq(unlogged.submitted).all() and unlogged.reason.eq('sl').all()
        assert np.array_equal(native.ticket[logged], ledger.ticket)
        assert np.allclose(native.trade_profit[logged], ledger.trade_profit, atol=1e-8, rtol=0)
        assert np.allclose((native.sl - native.requested)[logged], ledger.candle_range, atol=1e-8, rtol=0)
        sim, not_placed = simulate_fade(bars, cutoffs, resting_tp=bool(mode), at_market=at_market)
        record = dict(seconds=done['seconds'], native_trades=len(native), native_order_states=order_states,
                      native_orders_placed=int(stats.orders_placed), native_orders_rejected=int(stats.orders_rejected),
                      native_orders_skipped_at_market=int(stats.orders_skipped_at_market),
                      replay_orders_not_placed=not_placed, trades_missing_from_ea_ledger=len(unlogged),
                      report_ledger_and_totals_reconciled=True, replay=compare(native, sim))
        if at_market:
            # MT5 fills a stop at its level even when the market is already beyond it. A sell limit
            # sent above its own stop is "stopped" at once BELOW its fill: a profit no market pays.
            beyond = immediate & native.fill.ge(native.sl)
            inside = immediate & native.fill.lt(native.sl)
            record['filled_at_submission'] = dict(
                trades=int(immediate.sum()), gross_dollars=float(native.trade_profit[immediate].sum()),
                at_the_session_open=int((immediate & native.submitted.dt.strftime('%H:%M').eq('01:00')).sum()),
                filled_at_or_above_own_stop=int(beyond.sum()),
                their_gross_dollars=float(native.trade_profit[beyond].sum()),
                filled_below_own_stop=int(inside.sum()), their_gross_dollars_below_stop=float(native.trade_profit[inside].sum()))
            old = RUN / 'first_build' / f'sell_limit_{tag(FIRST_BUILD[arm])}_1.00.csv'
            record['ledger_identical_to_first_build'] = old.read_bytes() == ledger_file.read_bytes()
        verification[arm] = record
        native = economics(native)
        native.to_csv(RUN / f'trades_{arm}.csv', index=False, float_format='%.10g')
        curves[arm] = native
    # Replay-only curves start on the tester's first trading day (it waits for ~100 chart bars).
    first_day = min(curves[arm].submitted.min() for arm in PRIMARY).normalize()
    rtl, rtl_rejected = e.simulate_m30_ea(bars, cutoffs=cutoffs)
    rtl = rtl.loc[rtl.submitted.ge(first_day)]
    verification['rtl_baseline_replay'] = dict(first_day=str(first_day.date()), trades=len(rtl),
                                               buy_stops_rejected_at_market=rtl_rejected)
    curves['rtl'] = economics(rtl, short=False)
    # MT5 fills a limit on a touch. A real one may need price to trade through it: replay with one tick.
    for arm in PRIMARY:
        strict, _ = simulate_fade(bars, cutoffs, resting_tp=bool(ARMS[arm][0]), through=TICK)
        curves[arm + '_through'] = economics(strict.loc[strict.submitted.ge(first_day)])
    for name, frame in curves.items():
        for period, (start, stop) in PERIODS.items():
            part = frame.loc[frame.session.ge(start) & frame.session.lt(stop)]
            low, high = weekly_interval(part)
            rows.append(dict(curve=name, label=LABELS[name], source='MT5' if name in ARMS else 'minute replay',
                             period=period, **metrics(part, calendar[(calendar >= start) & (calendar < stop)]),
                             net_mean_r_low=low, net_mean_r_high=high))
        inside = frame.loc[frame.session.lt(END)]
        for year, part in inside.groupby(inside.session.dt.year):
            annual.append(dict(curve=name, year=int(year), **metrics(part, calendar[calendar.year == year])))
    summary, annual = pd.DataFrame(rows), pd.DataFrame(annual)
    DOC.mkdir(parents=True, exist_ok=True)
    summary.to_csv(DOC / 'summary.csv', index=False, float_format='%.6g')
    annual.to_csv(DOC / 'annual.csv', index=False, float_format='%.6g')
    (DOC / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n', encoding='utf-8')
    plot({name: curves[name] for name in (*PRIMARY, 'rtl')}, calendar)
    pd.set_option('display.width', 250)
    print(summary.drop(columns='label').to_string(index=False))
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'analyze': analyze}[sys.argv[1]]()
