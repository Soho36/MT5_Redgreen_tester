"""Independently reconstruct eligible watches, skips, submissions and native fills."""
from __future__ import annotations

from collections import Counter
from itertools import groupby

import numpy as np
import pandas as pd

from analyze_rtl_delayed_failed_breakout import RUN, TAG, read_events
from analyze_rtl_short_vwap import parse_short_report
from rtl_weekly_engine import CUTOFF, load_cutoffs
from run_rtl_vwap_replay import save_json
from verify_rtl_failed_breakout_short import SYMBOL, epoch, load_quote_index, native_orders


def reconcile(variant, quotes):
    report = RUN / f'{TAG}_{variant}.htm'
    orders = native_orders(report).set_index('order')
    trades = parse_short_report(report, SYMBOL)
    fills = trades.set_index('ticket')
    assert set(fills.index) == set(orders.loc[orders.state.eq('filled')].index)
    entries = trades.entry_time.to_numpy(dtype='datetime64[s]').astype('int64')
    exits = trades.exit_time.to_numpy(dtype='datetime64[s]').astype('int64')
    broker_exit = trades.exit_comment.fillna('').str.startswith('sl ').to_numpy()
    assert np.all(entries[1:] >= exits[:-1])

    events = read_events(variant)
    for col in ('time', 'signal_bar', 'watch_bar'):
        events[col] = events[col].to_numpy(dtype='datetime64[s]').astype('int64')
    assert events.time.is_monotonic_increasing
    starts = quotes.starts
    slot_times = quotes.slots * 1800
    dates = quotes.b['date'][starts]
    minute_of_day = quotes.slots % 48 * 30
    cutoffs = load_cutoffs()
    entry_open = (minute_of_day >= 60) & (minute_of_day < [cutoffs.get(d, CUTOFF) for d in dates])
    bar_first = np.array([next(quotes.quotes(i, i + 1))[0] for i in starts])
    # SL fills are processed by the broker before the EA sees the new bar.
    # Manually closing an existing position in the EA consumes that bar.
    last_trade = np.searchsorted(entries, bar_first, side='right') - 1
    occupied = (last_trade >= 0) & ((bar_first < exits[last_trade])
                                   | ((bar_first == exits[last_trade]) & ~broker_exit[last_trade]))
    red = quotes.ohlc[:, 3] < quotes.ohlc[:, 0]
    expected = set(slot_times[(dates >= 20160101) & entry_open & ~occupied & np.r_[False, red[:-1]]])
    watch_events = events.loc[events.event.eq('watch')]
    actual = set(watch_events.watch_bar)
    assert len(watch_events) == len(actual)
    assert actual == expected, ('missing or unexpected watch', variant, sorted(expected-actual)[:8],
                                sorted(actual-expected)[:8])

    accepted = {}
    counts = Counter()
    for bar, group in groupby(events.itertuples(index=False), key=lambda r: r.watch_bar):
        records = iter(group)
        row = next(records)
        j = quotes.lookup[bar]
        high, low = quotes.ohlc[j - 1, 1:3]
        entry, protective = low - .25, high + .25
        signal = slot_times[j - 1]

        def check(event, obs, when, bid):
            assert (obs.event, obs.time, obs.bid, obs.signal_bar, obs.watch_bar,
                    obs.signal_high, obs.signal_low) == (event, when, bid, signal, bar, high, low), (variant, obs, event, when, bid)
            if event in ('armed', 'rejected'):
                assert (event == 'armed') == (obs.retcode in (10008, 10009))
            else:
                assert obs.order == 0 and obs.retcode == 0
            counts[event] += 1

        check('watch', row, bar_first[j], quotes.ohlc[j, 0])
        path = quotes.quotes(starts[j], quotes.ends[j])
        before_next = None
        qualified = variant == 'plain'
        if not qualified:
            cross = next(((t, p) for t, p in path if p > high), None)
            if cross is not None:
                qualified = True
                check('break', next(records), *cross)
        if qualified:
            before_next = next(((t, p) for t, p in path if p <= entry), None)
        if before_next is not None:
            check('touched', next(records), *before_next)
        elif j + 1 < len(starts):
            k = j + 1
            now, bid = bar_first[k], quotes.ohlc[k, 0]
            if not qualified:
                why = 'expired'
            elif dates[j] != dates[k] or slot_times[k] != bar + 1800 or not entry_open[k]:
                why = 'session'
            elif occupied[k]:
                why = 'occupied'
            elif red[j]:
                why = 'replaced'
            elif bid <= entry:
                why = 'gap'
            else:
                why = 'armed'
            obs = next(records)
            check(why, obs, now, bid)
            if why == 'armed':
                assert obs.order > 0 and obs.order not in accepted
                accepted[obs.order] = (now, entry, protective)
        assert next(records, None) is None, ('unexpected extra event', variant, bar)
    assert set(accepted) == set(orders.index)
    for order in orders.itertuples():
        submitted, entry, stop = accepted[order.Index]
        assert (epoch(order.submitted), order.low, order.high) == (submitted, entry, stop)
        hit = quotes.first_below_after(submitted, epoch(order.finished), entry)
        if order.state == 'filled':
            fill = fills.loc[order.Index]
            assert hit is not None and hit[0] == epoch(order.finished)
            assert fill.entry_time == order.finished and fill.fill_price == entry and fill.original_sl == stop
        else:
            assert order.state == 'canceled' and hit is None
    return dict(events=dict(counts), candidate_coverage_exact=True, accepted_orders=len(accepted),
                fills_checked=len(fills), unfilled_orders_checked=len(accepted)-len(fills))


def main():
    quotes = load_quote_index()
    evidence = {variant: reconcile(variant, quotes) for variant in ('delayed', 'plain')}
    save_json(RUN / 'independent_chronology.json', dict(all_passed=True, **evidence))
    print(evidence)


if __name__ == '__main__':
    main()
