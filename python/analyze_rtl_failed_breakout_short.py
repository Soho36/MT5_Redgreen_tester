"""Reconcile and report the frozen red-candle failed-breakout short experiment.

Native MT5 outcomes only; no retrospective filtering of a baseline ledger.
Run after native OFF reproduction and ON completion.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from analyze_rtl_short_vwap import parse_short_report, economics, metrics, bootstrap
from project_paths import PROJECT_ROOT as ROOT
from run_rtl_vwap_replay import digest, save_json

RUN = ROOT / 'Reports/rtl_failed_breakout_short_20261105'
BASE = ROOT / 'Reports/gg_red_outside_short_20261021'
TAG = 'rtlfailed_20261105'
SYMBOL = 'MNQcontDTBNT20102026_2'
CACHE = ROOT / 'Reports/rtl_weekly_flatten_20261027/minutes.npz'
PERIODS = {'2016-19': ('2016-01-01', '2020-01-01'),
           '2020-26': ('2020-01-01', '2026-10-01'),
           '2016-26': ('2016-01-01', '2026-10-01')}
CURVES = {'off': 'Red short control', 'on': 'Failed-breakout short'}


def calendar():
    with np.load(CACHE) as cache:
        dates = np.unique(cache['day'])
    return pd.DatetimeIndex(dates.astype('datetime64[D]'))


def check_report(run, tag_prefix, variant, offset):
    tag = tag_prefix + '_' + variant
    record = json.loads((run / (tag + '.completed.json')).read_text(encoding='utf-8'))
    assert record['returncode'] == 0
    for name, expected in record['outputs'].items():
        assert digest(run / name) == expected, name
    assert digest(run / (tag + '.htm')) == record['report_sha256']
    frame = economics(parse_short_report(run / (tag + '.htm'), SYMBOL))
    raw = pd.read_csv(run / f'runband_{tag}_1.00.csv', sep='\t', encoding='utf-16')
    stats = pd.read_csv(run / f'runband_{tag}_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
    assert len(frame) == len(raw) == int(stats.trades)
    assert np.array_equal(raw.ticket, frame.ticket)
    assert np.allclose(raw.trade_profit, frame.trade_profit, atol=1e-8, rtol=0)
    risk_dollars = (raw.candle_range + 2 * offset) * 2
    assert np.allclose(risk_dollars, frame.initial_risk_dollars, atol=1e-8, rtol=0)
    assert np.allclose(frame.requested_price, frame.fill_price, atol=1e-8, rtol=0)
    assert np.allclose(frame.trade_profit, (frame.fill_price - frame.exit_price) * 2, atol=1e-8, rtol=0)
    assert np.isclose(frame.trade_profit.sum(), stats.net_profit, atol=1e-6, rtol=0)
    assert frame.entry_time.ge(frame.submitted).all()
    assert frame.exit_time.ge(frame.entry_time).all()
    frame.to_csv(run / f'trades_{variant}.csv', index=False, float_format='%.17g')
    return frame


def plot(frames, cal, run, offset):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cal = cal[(cal >= '2016-01-01') & (cal < '2026-10-01')]
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                             gridspec_kw={'height_ratios': [2, 1]}, layout='constrained')
    for variant, frame in frames.items():
        part = frame.loc[frame.session.ge('2016-01-01') & frame.session.lt('2026-10-01')]
        equity = part.groupby(part.exit_time.dt.normalize()).net_dollars.sum().reindex(cal, fill_value=0.).cumsum()
        peak = equity.cummax().clip(lower=0)
        axes[0].plot(equity.index, equity, label=CURVES[variant], lw=1.5)
        axes[1].plot(equity.index, equity - peak, lw=1.1)
    levels = 'Orders one tick outside the signal candle' if offset else 'Orders at the signal low and high'
    axes[0].set_title(f'NQ red-candle short with and without a high break\n{levels} | One MNQ | $1.05 per trade')
    axes[0].set_ylabel('Cumulative net USD')
    axes[1].set_ylabel('Daily-close drawdown USD')
    axes[0].legend()
    for ax in axes:
        ax.grid(alpha=.2)
        ax.axhline(0, color='gray', lw=.6)
    fig.savefig(run / 'equity.png', dpi=160)
    plt.close(fig)


def main(one_tick=False):
    validation = json.loads((RUN / 'baseline_validation.json').read_text(encoding='utf-8'))
    assert validation['all_passed']
    reference = BASE / 'runband_ggredshort_20261021_control_1.00.csv'
    assert reference.read_bytes() == (RUN / f'runband_{TAG}_off_1.00.csv').read_bytes()
    run, tag, offset = RUN, TAG, 0.0
    if one_tick:
        run = ROOT / 'Reports/rtl_failed_breakout_buffered_20261106'
        tag, offset = 'rtlfailedbuf_20261106', 0.25
    frames = {variant: check_report(run, tag, variant, offset) for variant in CURVES}
    cal = calendar()
    rows, annual = [], []
    for variant, frame in frames.items():
        for period, (start, stop) in PERIODS.items():
            part = frame.loc[frame.session.ge(start) & frame.session.lt(stop)]
            period_cal = cal[(cal >= start) & (cal < stop)]
            row = dict(period=period, variant=variant, curve=CURVES[variant], **metrics(part, period_cal))
            if variant == 'on':
                row.update(bootstrap(part, period_cal, seed=20261105))
            rows.append(row)
        relevant = frame.loc[frame.session.ge('2016-01-01') & frame.session.lt('2026-10-01')]
        for year, part in relevant.groupby(relevant.session.dt.year):
            year_cal = cal[(cal.year == year) & (cal < '2026-10-01')]
            annual.append(dict(year=int(year), variant=variant, curve=CURVES[variant], **metrics(part, year_cal)))
    summaries = pd.DataFrame(rows)
    summaries.to_csv(run / 'summaries.csv', index=False, float_format='%.12g')
    pd.DataFrame(annual).to_csv(run / 'annual.csv', index=False, float_format='%.12g')
    plot(frames, cal, run, offset)
    save_json(run / 'analysis_verification.json', dict(
        all_passed=True, zero_offset_reference_ledger_byte_identical=True, offset_points_per_side=offset,
        native_trades={k: len(v) for k, v in frames.items()},
        report_ledger_and_stats_reconciled=True, dollar_profit_from_native_prices_verified=True,
        cost_per_trade=1.05, point_value=2.0, periods=PERIODS,
        output_hashes={p.name: digest(p) for p in [run / 'summaries.csv', run / 'annual.csv',
            run / 'trades_off.csv', run / 'trades_on.csv', run / 'equity.png']}))
    print(summaries.to_string(index=False), flush=True)
    print(pd.DataFrame(annual)[['year', 'variant', 'trades', 'net_dollars', 'profit_factor']].to_string(index=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--one-tick', action='store_true', help='Analyse the matched one-tick pair')
    main(parser.parse_args().one_tick)
