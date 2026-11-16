"""Independent minute replay and native audit of RTL's buy-stop midpoint experiment."""
from __future__ import annotations
import json
import sys
import numpy as np
import pandas as pd
import rtl_weekly_engine as e
import analyze_rtl_vwap_cross as cx
from prepare_rtl_midpoint import ROOT, RUN, DOC, BASE, tag, sha
from rtl_sell_limit_fade import economics, metrics, weekly_interval, compare, label_native, PERIODS, CACHE


def midpoint(high, low, tick=.25):
    return float(np.ceil((high + low) / (2 * tick) - 1e-9) * tick)


def simulate(bars, cutoffs=None, spread=.25):
    """Buy stops only, rounded midpoint > ask, original low stop and 1R close exit.

    MT5's saved MNQ OHLC model executes resting stops at their level, and checks
    stops/entries before the EA receives the first quote of each new bar.
    No order/position uses information from a signal before it has closed.
    """
    cutoffs = cutoffs or {}
    date, day, minute = (bars[k] for k in ('date', 'day', 'minute'))
    o, h, l, c = (bars[k] for k in 'ohlc')
    slot = day * 48 + minute // 30
    lowfirst = e.low_first(o, c)
    pending = position = previous = current = None
    current_slot = -1
    previous_date = last_flat = rejected = 0
    trades = []

    def close(i, k, price, reason):
        nonlocal position
        trades.append({**position, 'exit_time': e.stamp(day[i], minute[i], k),
                       'exit_price': price, 'reason': reason})
        position = None

    for i in range(len(o)):
        newbar = slot[i] != current_slot
        if newbar:
            previous, current = current, [o[i], h[i], l[i], c[i]]
            current_slot = slot[i]
        else:
            current[1] = max(current[1], h[i])
            current[2] = min(current[2], l[i])
            current[3] = c[i]
        if not newbar and (pending is None or h[i] < pending['requested']):
            if position is None or l[i] > position['sl']:
                continue
        for k, price in enumerate(e.path(o[i], h[i], l[i], c[i], lowfirst[i])):
            if position is not None and price <= position['sl']:
                close(i, k, position['sl'], 'sl')
            if pending is not None and price >= pending['requested']:
                position = {**pending, 'entry_time': e.stamp(day[i], minute[i], k), 'fill': pending['requested']}
                pending = None
            if k != 0 or not newbar:
                continue
            bar_minute = minute[i] // 30 * 30
            if previous_date and date[i] != previous_date and last_flat != previous_date:
                last_flat = previous_date
                if position is not None:
                    close(i, k, price, 'fallback')
                pending = None
            previous_date = date[i]
            if bar_minute >= cutoffs.get(date[i], e.CUTOFF):
                if last_flat != date[i]:
                    last_flat = date[i]
                    if position is not None:
                        close(i, k, price, 'flatten')
                    pending = None
                continue
            if position is not None:
                target = 2 * position['fill'] - position['sl']
                if previous[3] >= target:
                    close(i, k, price, 'target')
                continue
            if bar_minute < 60:
                pending = None
                continue
            if previous is not None and previous[3] < previous[0]:
                pending = None
                entry = midpoint(previous[1], previous[2])
                if entry <= previous[2] or entry <= price + spread:
                    rejected += 1
                    continue
                pending = dict(submitted=e.stamp(day[i], minute[i], 0), requested=entry, sl=previous[2])
    if position is not None:
        close(len(o) - 1, 3, c[-1], 'end_of_data')
    return pd.DataFrame(trades), rejected


def native(arm):
    t = cx.parse_report(RUN / (tag(arm) + '.htm'), 'MNQcontDTBNT20102026_2')
    t = t.rename(columns={'requested_price': 'requested', 'fill_price': 'fill', 'original_sl': 'sl'})
    t['reason'] = np.select([t.exit_comment.str.startswith('sl'), t.exit_comment.str.startswith('end of test')],
                            ['sl', 'end_of_data'], 'market')
    t = label_native(t, e.load_cutoffs())
    stats = pd.read_csv(RUN / f'runband_{tag(arm)}_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
    ledger = pd.read_csv(RUN / f'runband_{tag(arm)}_1.00.csv', sep='\t', encoding='utf-16')
    assert len(t) == stats.trades == len(ledger), (len(t), stats.trades, len(ledger))
    assert np.array_equal(t.ticket, ledger.ticket)
    assert np.allclose(t.trade_profit, (t.exit_price - t.fill) * 2, rtol=0, atol=1e-8)
    assert np.allclose(t.trade_profit, ledger.trade_profit, rtol=0, atol=1e-8)
    assert np.isclose(t.trade_profit.sum(), stats.net_profit, rtol=0, atol=1e-6)
    assert t.fill.eq(t.requested).all()
    done = json.loads((RUN / (tag(arm) + '.completed.json')).read_text())
    assert all(sha(RUN / f) == digest for f, digest in done['outputs'].items())
    return t


def analyze():
    bars, cutoffs = e.load_minutes(CACHE), e.load_cutoffs()
    calendar = pd.DatetimeIndex(np.unique(bars['day']).astype('datetime64[D]'))
    manifest = json.loads((RUN / 'manifest.json').read_text())
    for path, digest in manifest['input_hashes'].items():
        assert sha(__import__('pathlib').Path(path)) == digest, path
    audit = {'protocol_after_clarification_sha256': sha(DOC / 'PROTOCOL.md'),
             'minute_cache_sha256': sha(CACHE), 'script_sha256': sha(ROOT / 'python/rtl_midpoint.py')}
    curves, rows, annual = {}, [], []
    for arm in ('baseline', 'stop_only'):
        print('Checking', arm, flush=True)
        t = native(arm)
        replay, rejected = (e.simulate_m30_ea(bars, cutoffs=cutoffs) if arm == 'baseline' else simulate(bars, cutoffs))
        check = compare(t, replay)
        audit[arm] = dict(replay=check, replay_rejections=rejected, report_ledger_totals_match=True)
        (DOC / 'verification.json').write_text(json.dumps(audit, indent=2) + '\n')
        print(json.dumps(check, indent=2), flush=True)
        assert check.get('all_trades_identical'), check
        if arm == 'baseline':
            reference = BASE / 'runband_tf_20261015_rtl_m30_rr1p0_1.00.csv'
            audit['baseline_ledger_byte_identical'] = reference.read_bytes() == (RUN / f'runband_{tag(arm)}_1.00.csv').read_bytes()
            assert audit['baseline_ledger_byte_identical']
        curves[arm] = economics(t, short=False)
        curves[arm].to_csv(RUN / f'trades_{arm}.csv', index=False)
        for period, (start, stop) in PERIODS.items():
            part = curves[arm].loc[lambda f: f.session.ge(start) & f.session.lt(stop)]
            low, high = weekly_interval(part)
            rows.append(dict(arm=arm, period=period, **metrics(part, calendar[(calendar >= start) & (calendar < stop)]),
                             net_mean_r_low=low, net_mean_r_high=high))
        inside = curves[arm].loc[lambda f: f.session.lt('2026-10-01')]
        for year, part in inside.groupby(inside.session.dt.year):
            annual.append(dict(arm=arm, year=int(year), **metrics(part, calendar[calendar.year == year])))
    summary = pd.DataFrame(rows)
    summary.to_csv(DOC / 'summary.csv', index=False, float_format='%.8g')
    pd.DataFrame(annual).to_csv(DOC / 'annual.csv', index=False, float_format='%.8g')
    (DOC / 'verification.json').write_text(json.dumps(audit, indent=2) + '\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 5), layout='constrained')
    for arm, frame in curves.items():
        t = frame.loc[lambda f: f.session.ge('2016-01-01') & f.session.lt('2026-10-01')]
        net = t.groupby(t.exit_time.dt.normalize()).net.sum().reindex(calendar[(calendar >= '2016-01-01') & (calendar < '2026-10-01')], fill_value=0)
        ax.plot(net.index, net.cumsum(), label={'baseline': 'Original RTL', 'stop_only': 'Midpoint buy stop'}[arm])
    ax.axhline(0, color='gray', lw=.7)
    ax.grid(alpha=.2)
    ax.legend()
    ax.set_ylabel('Cumulative net USD')
    ax.set_title('RTL: high entry vs midpoint buy stop\nOne MNQ, $1.05 per trade, MT5 1-minute OHLC')
    (DOC / 'img').mkdir(exist_ok=True)
    fig.savefig(DOC / 'img/equity.png', dpi=150)
    plt.close(fig)
    print(summary.to_string(index=False), flush=True)

if __name__ == '__main__':
    analyze()
