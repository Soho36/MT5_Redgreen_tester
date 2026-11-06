"""Verify the one-tick red short and its matched immediate-entry control."""
import json

from project_paths import PROJECT_ROOT as ROOT
from verify_rtl_failed_breakout_short import (
    CACHE, SYMBOL, digest, epoch, load_quote_index, native_orders,
    parse_short_report, verify_economics, verify_events,
)


RUN = ROOT / 'Reports/rtl_failed_breakout_buffered_20261106'
TAG = 'rtlfailedbuf_20261106'
TICK = 0.25


def verify_control(quotes):
    """Reconstruct every immediately submitted control order from raw M30 bars."""
    report = RUN / (TAG + '_off.htm')
    orders = native_orders(report)
    filled = orders.loc[orders.state.eq('filled')].set_index('order')
    trades = parse_short_report(report, SYMBOL).set_index('ticket')
    assert set(filled.index) == set(trades.index)
    for order in orders.itertuples(index=False):
        # The maker of an OFF order is the last completed candle at submission.
        j = quotes.lookup[epoch(order.submitted.floor('30min'))]
        assert j > 0
        o, h, l, c = quotes.ohlc[j - 1]
        assert c < o and (order.low, order.high) == (l - TICK, h + TICK), order
        first, _ = next(quotes.quotes(quotes.starts[j], quotes.starts[j] + 1))
        assert epoch(order.submitted) == first, order
        crossing = quotes.first_below_after(first, epoch(order.finished), order.low)
        if order.state == 'filled':
            assert crossing is not None and crossing[0] == epoch(order.finished), (order, crossing)
            trade = trades.loc[order.order]
            assert trade.fill_price == order.low and trade.original_sl == order.high, order
            assert trade.submitted == order.submitted and trade.entry_time == order.finished, order
        else:
            assert order.state == 'canceled' and crossing is None, (order, crossing)
    return dict(orders=len(orders), filled=len(trades), canceled=len(orders) - len(trades),
                levels_match_prior_red_candle_plus_one_tick=True,
                all_orders_submitted_at_first_quote=True, all_fills_at_first_subsequent_crossing=True)


def main():
    quotes = load_quote_index()
    on = verify_events(RUN, tag_prefix=TAG, entry_buffer=TICK, stop_buffer=TICK, quotes=quotes)
    control = verify_control(quotes)
    economics = verify_economics(RUN, tag_prefix=TAG, total_buffer=2 * TICK, check_baseline=False)
    evidence = dict(all_passed=True, point_buffer_each_side=TICK, failed_breakout=on,
                    matched_control=control, economics=economics, input_cache_sha256=digest(CACHE))
    (RUN / 'independent_verification.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
