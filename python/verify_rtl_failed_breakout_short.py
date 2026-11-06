"""Independent raw-minute chronology and economics audit for failed-breakout shorts.

The quote path is the project's MT5 one-minute OHLC convention. This is an
order/activation verifier, not another strategy engine or a real-tick claim.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

import rtl_weekly_engine as engine
from analyze_rtl_vwap_cross import CELL, TAG as HTML_TAG, STAMP, number
from analyze_rtl_short_vwap import parse_short_report
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / 'Reports/rtl_failed_breakout_short_20261105'
CACHE = ROOT / 'Reports/rtl_weekly_flatten_20261027/minutes.npz'
TAG = 'rtlfailed_20261105'
SYMBOL = 'MNQcontDTBNT20102026_2'
PERIODS = {'2016-19': ('2016-01-01', '2020-01-01'),
           '2020-26': ('2020-01-01', '2026-10-01'),
           '2016-26': ('2016-01-01', '2026-10-01')}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class QuoteIndex:
    """Raw chronological M1 quotes plus independently aggregated M30 candles."""
    def __init__(self, bars):
        self.b = bars
        self.volume = bars.get('tick_volume', np.full(len(bars['day']), 4, dtype=np.int8))
        self.minute_epoch = bars['day'] * 86400 + bars['minute'] * 60
        self.lowfirst = engine.low_first(bars['o'], bars['c'])
        slots = bars['day'] * 48 + bars['minute'] // 30
        self.starts = np.flatnonzero(np.r_[True, slots[1:] != slots[:-1]])
        self.ends = np.r_[self.starts[1:], len(slots)]
        self.slots = slots[self.starts]
        self.lookup = {int(slot * 1800): j for j, slot in enumerate(self.slots)}
        self.ohlc = np.c_[bars['o'][self.starts],
                          np.maximum.reduceat(bars['h'], self.starts),
                          np.minimum.reduceat(bars['l'], self.starts),
                          bars['c'][self.ends - 1]]

    def quotes(self, begin, end):
        for i in range(begin, end):
            prices = engine.path(*(self.b[k][i] for k in 'ohlc'), self.lowfirst[i])
            o, h, l, c = (self.b[k][i] for k in 'ohlc')
            volume = self.volume[i]
            if h == l:
                # The only distinct price arrives at :30 for volume one,
                # otherwise at :01 on this native MT5 custom symbol.
                points = [(30 if volume == 1 else 1, c)]
                # A pending order may be placed exactly at this first bid.
                # MT5 can execute it at the repeated price on the next quote
                # (buffered control order 4884, flat M1 with six source ticks).
                if volume >= 4:
                    points.extend((second, c) for second in engine.TICK_SECONDS[1:])
            elif volume < 4:
                # For a sparse minute the body endpoints cover the full
                # range unless there is a distinct intermediate shadow.
                # Preserve the native first arrival of each OHLC price.
                shadows = [p for p in prices[1:3] if p not in (o, c)]
                if len(shadows) == 2:
                    points = zip(engine.TICK_SECONDS, prices)
                elif shadows:
                    points = [(0, o), (30, shadows[0]), (59, c)]
                else:
                    points = [(0, o), (30 if volume == 2 else 59, c)]
            else:
                points = zip(engine.TICK_SECONDS, prices)
            for second, price in points:
                yield int(self.minute_epoch[i] + second), float(price)

    def first_above(self, bar_epoch, high):
        j = self.lookup[int(bar_epoch)]
        return next(((t, p) for t, p in self.quotes(self.starts[j], self.ends[j]) if p > high), None)

    def first_below_after(self, after_epoch, stop_epoch, low, inclusive_end=True):
        """First eligible quote after activation, never an earlier low touch."""
        begin = int(np.searchsorted(self.minute_epoch, after_epoch // 60 * 60))
        end = int(np.searchsorted(self.minute_epoch, stop_epoch // 60 * 60, side='right'))
        for t, p in self.quotes(begin, end):
            if t <= after_epoch:
                continue
            if t > stop_epoch or (t == stop_epoch and not inclusive_end):
                break
            if p <= low:
                return t, p
        return None


def epoch(value):
    return int(pd.Timestamp(value).value // 10**9)


def load_quote_index():
    """Join the missing tick volumes by checked minute, not by assumed row order."""
    with np.load(CACHE) as cache:
        bars = {key: cache[key] for key in cache.files}
    bars['tick_volume'] = np.empty(len(bars['day']), dtype=np.int64)
    start = 0
    for chunk in pd.read_csv(engine.MINUTES, sep='\t', chunksize=250_000,
                             usecols=['<DATE>', '<TIME>', '<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>', '<TICKVOL>']):
        end = start + len(chunk)
        dates = chunk['<DATE>'].map({d: int(d.replace('.', '')) for d in chunk['<DATE>'].unique()})
        times = chunk['<TIME>'].map({t: 60 * int(t[:2]) + int(t[3:5]) for t in chunk['<TIME>'].unique()})
        assert np.array_equal(dates, bars['date'][start:end])
        assert np.array_equal(times, bars['minute'][start:end])
        for field, key in zip(('<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>'), 'ohlc'):
            assert np.array_equal(chunk[field], bars[key][start:end])
        bars['tick_volume'][start:end] = chunk['<TICKVOL>']
        start = end
    assert start == len(bars['day'])
    return QuoteIndex(bars)


def native_orders(path):
    """Read all original orders, including canceled ones, independently of trades."""
    rows = []
    section = None
    for line in Path(path).read_text(encoding='utf-16').splitlines():
        if '>Orders<' in line:
            section = 'orders'
        elif '>Deals<' in line:
            section = 'deals'
        if section != 'orders' or '<tr' not in line or '</tr>' not in line:
            continue
        cells = [html.unescape(HTML_TAG.sub('', c)).strip() for c in CELL.findall(line)]
        if len(cells) != 11 or not STAMP.match(cells[0]):
            continue
        if cells[3] in ('buy stop', 'sell stop', 'buy limit', 'sell limit'):
            assert cells[3] == 'sell stop' and cells[2] == SYMBOL, cells
            rows.append(dict(order=int(cells[1]), submitted=pd.Timestamp(cells[0]),
                             low=number(cells[5]), high=number(cells[6]),
                             finished=pd.Timestamp(cells[8]), state=cells[9]))
    frame = pd.DataFrame(rows)
    assert len(frame) and frame.order.is_unique
    return frame


def max_dd(values):
    equity = peak = drawdown = 0.0
    for value in values:
        equity += float(value)
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def metric_values(trades):
    net = trades.trade_profit - 1.05
    risk = (trades.original_sl - trades.requested_price) * 2
    loss = -net[net < 0].sum()
    return dict(trades=len(trades), net_dollars=float(net.sum()),
                gross_mean_r=float((trades.trade_profit / risk).mean()),
                net_mean_r=float((net / risk).mean()),
                profit_factor=float(net[net > 0].sum() / loss) if loss else np.nan,
                daily_close_dd=max_dd(net.groupby(trades.exit_time.dt.normalize()).sum().sort_index()),
                closed_trade_dd=max_dd(trades.assign(net=net).sort_values(['exit_time', 'entry_time', 'ticket']).net),
                win_pct=float(100 * net.gt(0).mean()),
                stress1_net_dollars=float(net.sum() - len(trades)),
                stress2_net_dollars=float(net.sum() - 2 * len(trades)))


def verify_metrics(frame, expected_row, label):
    expected = metric_values(frame)
    for key, value in expected.items():
        assert key in expected_row.index, (label, 'missing metric', key)
        assert np.isclose(value, expected_row[key], atol=1e-5, rtol=1e-8, equal_nan=True), (
            label, key, value, expected_row[key])
    return len(expected)


def verify_economics(run=RUN, tag_prefix=TAG, total_buffer=0., check_baseline=True):
    if check_baseline:
        baseline = json.loads((run / 'baseline_validation.json').read_text())
        assert baseline['all_passed'] and baseline['native_ledger_byte_identical']
    summaries = pd.read_csv(run / 'summaries.csv')
    annual = pd.read_csv(run / 'annual.csv')
    audits = []
    for variant in ('off', 'on'):
        tag = tag_prefix + '_' + variant
        done = json.loads((run / (tag + '.completed.json')).read_text())
        assert done['returncode'] == 0 and done['dedicated_tester_only_binary']
        for name, wanted in done['outputs'].items():
            assert digest(run / name) == wanted, name
        assert digest(run / (tag + '.htm')) == done['report_sha256']
        trades = parse_short_report(run / (tag + '.htm'), SYMBOL)
        raw = pd.read_csv(run / f'runband_{tag}_1.00.csv', sep='\t', encoding='utf-16')
        stats = pd.read_csv(run / f'runband_{tag}_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
        assert len(trades) == len(raw) == int(stats.trades)
        assert np.array_equal(trades.ticket, raw.ticket)
        assert np.allclose(trades.trade_profit, raw.trade_profit, atol=1e-8, rtol=0)
        assert np.allclose(trades.trade_profit, (trades.fill_price - trades.exit_price) * 2, atol=1e-8, rtol=0)
        assert np.allclose(trades.original_sl - trades.requested_price, raw.candle_range + total_buffer, atol=1e-8, rtol=0)
        assert np.isclose(trades.trade_profit.sum(), stats.net_profit, atol=1e-5, rtol=0)
        exported = pd.read_csv(run / f'trades_{variant}.csv', parse_dates=['submitted', 'entry_time', 'exit_time'])
        for col in ('ticket', 'submitted', 'entry_time', 'exit_time', 'requested_price',
                    'original_sl', 'fill_price', 'exit_price', 'trade_profit'):
            assert np.array_equal(trades[col], exported[col]), (variant, col)
        for _, row in summaries.loc[summaries.variant.eq(variant)].iterrows():
            start, stop = PERIODS[row.period]
            part = trades.loc[trades.submitted.ge(start) & trades.submitted.lt(stop)]
            checked = verify_metrics(part, row, (variant, row.period))
            audits.append(dict(variant=variant, period=row.period, trades=len(part), metrics=checked))
        for _, row in annual.loc[annual.variant.eq(variant)].iterrows():
            part = trades.loc[trades.submitted.dt.year.eq(row.year) & trades.submitted.lt('2026-10-01')]
            verify_metrics(part, row, (variant, int(row.year)))
    return dict(summary_checks=audits, annual_rows_checked=len(annual), native_hashes_verified=True)


def main():
    # The event audit is below; economics must also succeed before declaring completion.
    result = dict(all_passed=True, **verify_events(), **verify_economics())
    result['input_cache_sha256'] = digest(CACHE)
    (RUN / 'independent_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


def audit_event_rows(events, quotes, orders, entry_buffer=0., stop_buffer=0.):
    """Validate every lifecycle record against raw prices, then every broker order."""
    allowed = {'watch', 'armed', 'rejected', 'expired'}
    assert set(events.event).issubset(allowed)
    assert events.time.is_monotonic_increasing
    active = None
    armed = {}
    watched = set()
    counts = {event: 0 for event in allowed}
    no_retro_fill = 0
    for row in events.itertuples(index=False):
        counts[row.event] += 1
        signal, watch, now = epoch(row.signal_bar), epoch(row.watch_bar), epoch(row.time)
        assert watch in quotes.lookup, ('missing watch candle', row)
        j = quotes.lookup[watch]
        assert j > 0 and signal == int(quotes.slots[j - 1] * 1800), ('non-adjacent signal', row)
        o, h, l, c = quotes.ohlc[j - 1]
        assert c < o, ('signal is not red', row)
        assert h == row.signal_high and l == row.signal_low, ('signal levels', row)
        if row.event == 'watch':
            assert active is None, ('watch replaced without terminal event', active, row)
            assert watch not in watched, ('duplicate watch', row)
            watched.add(watch)
            assert now == next(quotes.quotes(quotes.starts[j], quotes.starts[j] + 1))[0], ('late watch', row)
            assert row.bid == quotes.b['o'][quotes.starts[j]], ('watch bid', row)
            assert row.order == 0 and row.retcode == 0
            active = row
            continue
        assert active is not None, ('orphan terminal event', row)
        assert (row.signal_bar, row.watch_bar, h, l) == (
            active.signal_bar, active.watch_bar, active.signal_high, active.signal_low)
        first = quotes.first_above(watch, h)
        if row.event == 'expired':
            assert first is None, ('missed qualifying high break', row, first)
            assert j + 1 < len(quotes.starts), ('expiry without later candle', row)
            assert now == next(quotes.quotes(quotes.starts[j + 1], quotes.starts[j + 1] + 1))[0], ('wrong expiry boundary', row)
            assert row.order == 0 and row.retcode == 0
        else:
            assert first is not None and (now, row.bid) == first, ('not first strict break', row, first)
            assert row.bid > h
            if row.event == 'armed':
                assert row.retcode in (10008, 10009) and row.order > 0, ('unsuccessful arm', row)
                assert row.order not in armed, ('duplicate order', row)
                armed[int(row.order)] = row
            else:
                assert row.retcode not in (10008, 10009), ('successful order logged rejected', row)
            if quotes.first_below_after(epoch(active.time) - 1, now, l - entry_buffer) is not None:
                no_retro_fill += 1
        active = None
    if active is not None:
        # The data can end halfway through the last watched M30 candle.
        assert quotes.lookup[epoch(active.watch_bar)] == len(quotes.starts) - 1
        assert quotes.first_above(epoch(active.watch_bar), active.signal_high) is None
    assert set(orders.order) == set(armed), ('actual orders differ from arms',
                                          len(orders), len(armed))
    fills = delayed_fills = 0
    for order in orders.itertuples(index=False):
        arm = armed[order.order]
        assert order.submitted == arm.time
        assert (order.low, order.high) == (arm.signal_low - entry_buffer, arm.signal_high + stop_buffer)
        assert order.finished >= order.submitted
        crossing = quotes.first_below_after(epoch(order.submitted), epoch(order.finished), order.low)
        if order.state == 'filled':
            fills += 1
            assert crossing is not None and crossing[0] == epoch(order.finished), (
                'fill must be first low touch after arming', order, crossing)
            assert order.finished > order.submitted
            delayed_fills += int(order.finished.floor('30min') > arm.watch_bar)
        else:
            assert order.state == 'canceled', ('unknown pending state', order)
            assert crossing is None, ('missed fill before cancellation', order, crossing)
    return dict(event_counts=counts, original_orders=len(orders), filled_orders=fills,
                filled_after_activation_candle=delayed_fills,
                low_before_high_watches=no_retro_fill,
                all_first_strict_high_breaks_causal=True,
                all_fills_after_activation_at_first_low_touch=True,
                all_order_levels_use_original_red_signal=True,
                terminal_unexpired_watch=int(active is not None))


def verify_events(run=RUN, tag_prefix=TAG, entry_buffer=0., stop_buffer=0., quotes=None):
    events = pd.read_csv(run / f'failed_breakout_{tag_prefix}_on.csv', sep='\t', encoding='cp1252')
    for col in ('time', 'signal_bar', 'watch_bar'):
        events[col] = pd.to_datetime(events[col], format='%Y.%m.%d %H:%M:%S')
    if quotes is None:
        quotes = load_quote_index()
    orders = native_orders(run / f'{tag_prefix}_on.htm')
    result = audit_event_rows(events, quotes, orders, entry_buffer, stop_buffer)
    trades = parse_short_report(run / f'{tag_prefix}_on.htm', SYMBOL)
    filled = orders.loc[orders.state.eq('filled')].set_index('order')
    assert set(trades.ticket) == set(filled.index)
    for row in trades.itertuples(index=False):
        order = filled.loc[row.ticket]
        assert row.entry_time == order.finished and row.submitted == order.submitted
        assert row.requested_price == order.low and row.original_sl == order.high
        assert row.fill_price == order.low
    return result


if __name__ == '__main__':
    main()
