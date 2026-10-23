"""Execute the frozen RTL trend x volatility diagnostic, with no strategy changes.

All decisions use information preceding actual pending-order submission. The
10,000-draw bootstrap resamples paired calendar-week blocks, preserving trades.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / 'Reports/rtl_market_regimes_20261023'
BASE = ROOT / 'Reports/timeframe_baseline_20261015'
TAG = 'tf_20261015_rtl_m30_rr1p0'
RAW = BASE / f'runband_{TAG}_1.00.csv'
STATS = BASE / f'runband_{TAG}_1.00_stats.csv'
HTML = BASE / f'{TAG}.htm'
INI = BASE / f'{TAG}.ini'
COMPLETION = BASE / f'{TAG}.completed.json'
MANIFEST = BASE / 'manifest.json'
DAILY = ROOT / 'Reports/trend_rr_20261002/daily_reference.csv'
M30 = ROOT / 'Reports/trend_rr_20261002/m30_reference.csv'
MINUTES = Path(r'F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv')
ROLLS = MINUTES.with_name('MT5_NQ_continuous_2010-2026_rolls.csv')
PROTOCOL = ROOT / 'docs/baseline/rtl-market-regimes/PROTOCOL.md'
PROTOCOL_SHA256 = 'c3e8d6035ae712cb0cbf5da666f87d2f4ace29e6722fb314591c7d28464b32fa'
GROUPS = tuple(f'{trend}_{vol}' for trend in ('bull', 'neutral', 'bear')
               for vol in ('normal', 'elevated'))
ERAS = {'2016-19': ('2016-01-01', '2020-01-01'),
        '2020-26': ('2020-01-01', '2026-10-01')}
SENSITIVITIES = {'p70': 'group_p70', 'p80': 'group_p80', 'roll_robust': 'group_roll_robust'}
COST = 1.05
POINT_VALUE = 2.0
DRAWS = 10000
SEED = 20261023


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def source_daily_closes():
    parts = []
    final_timestamp = None
    rows = 0
    for chunk in pd.read_csv(MINUTES, sep='\t', usecols=['<DATE>', '<TIME>', '<CLOSE>'], chunksize=500000):
        rows += len(chunk)
        final_timestamp = str(chunk.iloc[-1]['<DATE>']) + ' ' + str(chunk.iloc[-1]['<TIME>'])
        eligible = chunk.loc[chunk['<TIME>'] >= '01:00:00']
        parts.append(eligible.groupby('<DATE>')['<CLOSE>'].last())
    closes = pd.concat(parts).groupby(level=0).last()
    closes.index = pd.to_datetime(closes.index, format='%Y.%m.%d')
    closes.index.name = 'date'
    return closes, {'minute_rows': rows, 'source_final_timestamp': final_timestamp}


def build_features(closes, switches=()):
    """Compute exact protocol lags; threshold excludes the classified prior SD."""
    close = closes.sort_index().astype(float)
    assert close.index.is_unique and (close > 0).all() and np.isfinite(close).all()
    out = close.to_frame('close')
    out.index.name = 'date'
    out['previous_date'] = out.index.to_series().shift(1)
    out['previous_close'] = close.shift(1)
    out['sma50'] = close.rolling(50, min_periods=50).mean().shift(1)
    out['sma200'] = close.rolling(200, min_periods=200).mean().shift(1)
    out['trend'] = 'neutral'
    out.loc[(out.previous_close > out.sma200) & (out.sma50 > out.sma200), 'trend'] = 'bull'
    out.loc[(out.previous_close < out.sma200) & (out.sma50 < out.sma200), 'trend'] = 'bear'
    out.loc[out.sma200.isna(), 'trend'] = 'warmup'
    returns = np.log(close / close.shift(1))
    out['return_log'] = returns
    out['volatility20'] = returns.rolling(20, min_periods=20).std(ddof=1)
    out['volatility_prior'] = out.volatility20.shift(1)
    switches = pd.DatetimeIndex(pd.to_datetime(list(switches))).normalize()
    out['roll_date'] = out.index.isin(switches)
    robust = returns.mask(out.roll_date)
    # Require twenty-session window history even though fifteen returns suffice.
    robust_vol = robust.rolling(20, min_periods=15).std(ddof=1)
    robust_vol.iloc[:20] = np.nan
    out['volatility_robust20'] = robust_vol
    out['volatility_robust_prior'] = robust_vol.shift(1)
    for percentile in (70, 75, 80):
        threshold = out.volatility20.shift(2).rolling(252, min_periods=252).quantile(percentile / 100, interpolation='linear')
        out[f'volatility_threshold_p{percentile}'] = threshold
        group_column = 'group' if percentile == 75 else f'group_p{percentile}'
        out[group_column] = out.trend + np.where(out.volatility_prior > threshold, '_elevated', '_normal')
        out.loc[threshold.isna() | out.volatility_prior.isna() | (out.trend == 'warmup'), group_column] = 'warmup'
    threshold = robust_vol.shift(2).rolling(252, min_periods=252).quantile(.75, interpolation='linear')
    out['volatility_robust_threshold'] = threshold
    out['group_roll_robust'] = out.trend + np.where(out.volatility_robust_prior > threshold, '_elevated', '_normal')
    out.loc[threshold.isna() | out.volatility_robust_prior.isna() | (out.trend == 'warmup'), 'group_roll_robust'] = 'warmup'
    return out


def parse_report():
    cell_pattern = re.compile(r'<td\b[^>]*>(.*?)</td>', re.I)
    tag_pattern = re.compile(r'<[^>]*>')
    time_pattern = re.compile(r'^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$')
    number = lambda text: float(text.replace(' ', '').replace('\xa0', ''))
    orders, trades, active, section = {}, [], None, None
    with HTML.open(encoding='utf-16') as stream:
        for line in stream:
            if '>Orders<' in line:
                section = 'orders'
            elif '>Deals<' in line:
                section = 'deals'
            if '<tr' not in line or '</tr>' not in line:
                continue
            cells = [html.unescape(tag_pattern.sub('', text)).strip() for text in cell_pattern.findall(line)]
            if not cells or not time_pattern.match(cells[0]):
                continue
            if section == 'orders' and len(cells) == 11 and cells[3] in ('buy stop', 'buy'):
                assert cells[2] == 'MNQcontDTBNT20102026_2' and cells[3] == 'buy stop'
                ticket = int(cells[1])
                assert ticket not in orders
                orders[ticket] = {'submitted': cells[0], 'requested_price': number(cells[5]),
                                  'original_sl': number(cells[6]), 'state': cells[9]}
            elif section == 'deals' and len(cells) == 13 and cells[3] != 'balance':
                assert cells[2] == 'MNQcontDTBNT20102026_2'
                assert number(cells[5]) == 1 and number(cells[8]) == 0 and number(cells[9]) == 0
                if cells[3:5] == ['buy', 'in']:
                    assert active is None
                    ticket = int(cells[7])
                    assert ticket in orders and orders[ticket]['state'] == 'filled'
                    active = dict(orders[ticket], ticket=ticket, entry_time=cells[0],
                                  fill_price=number(cells[6]), entry_profit=number(cells[10]))
                elif cells[3:5] == ['sell', 'out']:
                    assert active is not None
                    trades.append(dict(active, exit_time=cells[0], exit_price=number(cells[6]),
                                       trade_profit=active['entry_profit'] + number(cells[10]),
                                       exit_comment=cells[12]))
                    active = None
                else:
                    raise ValueError(f'Unsupported direction/type: {cells[3:5]}')
    assert active is None and trades
    frame = pd.DataFrame(trades).drop(columns=['state', 'entry_profit'])
    assert frame.ticket.is_unique
    for column in ('submitted', 'entry_time', 'exit_time'):
        frame[column] = pd.to_datetime(frame[column], format='%Y.%m.%d %H:%M:%S')
    return frame


def reconcile_sources(inputs):
    assert inputs[str(PROTOCOL)] == PROTOCOL_SHA256, 'Frozen protocol has changed'
    completion = json.loads(COMPLETION.read_text(encoding='utf-8'))
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert completion['tag'] == TAG
    for path in (RAW, STATS):
        assert completion['outputs'][path.name] == inputs[str(path)]
    assert manifest['prepared_sha256'][INI.name] == inputs[str(INI)]
    assert manifest['max_red_run'] == 0 and manifest['cost_per_trade'] == COST
    jobs = [job for job in manifest['jobs'] if job['tag'] == TAG]
    assert len(jobs) == 1 and jobs[0]['strategy'] == 'RTL' and jobs[0]['rr'] == 1 and jobs[0]['timeframe'] == 'M30'
    ini = INI.read_text(encoding='utf-16')
    for setting in ('MaxRedRun=0', 'MinLocation=0', 'RiskReward=1.0', 'FlattenFallback=true', 'UseEarlyCloseCalendar=true'):
        assert setting in ini, setting
    raw = pd.read_csv(RAW, sep='\t', encoding='utf-16')
    assert raw.ticket.is_unique
    report = parse_report()
    paired = report.set_index('ticket').reindex(raw.ticket)
    assert len(raw) == len(report) and paired.entry_time.notna().all()
    for column in ('entry_time', 'exit_time'):
        assert np.array_equal(pd.to_datetime(raw[column], format='%Y.%m.%d %H:%M:%S').to_numpy(), paired[column].to_numpy())
    for left, right in ((raw.trade_profit, paired.trade_profit),
                        (raw.candle_range, paired.requested_price-paired.original_sl)):
        assert np.allclose(left.to_numpy(), right.to_numpy(), rtol=0, atol=1e-8)
    stats = pd.read_csv(STATS, sep='\t', encoding='utf-16')
    assert len(stats) == 1 and stats.iloc[0].run_tag == TAG and stats.iloc[0].risk_reward == 1
    s = stats.iloc[0]
    totals = {'trades': len(report), 'net_profit': float(report.trade_profit.sum()),
              'gross_profit': float(report.loc[report.trade_profit > 0, 'trade_profit'].sum()),
              'gross_loss': float(report.loc[report.trade_profit < 0, 'trade_profit'].sum())}
    for key, value in totals.items():
        assert np.isclose(value, s[key], rtol=0, atol=1e-7), key
    report = report.merge(raw[['ticket', 'candle_range', 'red_run', 'location']], on='ticket', validate='one_to_one')
    report = report.sort_values(['entry_time', 'ticket'], kind='stable').reset_index(drop=True)
    assert (report.submitted <= report.entry_time).all() and (report.entry_time <= report.exit_time).all()
    assert (report.submitted.dt.normalize() == report.entry_time.dt.normalize()).all()
    assert (report.entry_time.dt.normalize() == report.exit_time.dt.normalize()).all()
    assert (report.submitted.dt.hour >= 1).all()
    assert (report.entry_time.iloc[1:].to_numpy() >= report.exit_time.iloc[:-1].to_numpy()).all()
    assert np.allclose(report.trade_profit, (report.exit_price-report.fill_price)*POINT_VALUE, atol=1e-7, rtol=0)
    return report, {'all_passed': True, 'raw_trades': len(raw), 'html_trades': len(report),
                    'whole_run_totals': totals, 'completion_hashes_match': True, 'ini_manifest_hash_matches': True,
                    'order_risk_matches_ledger': True, 'cross_date_orders': 0, 'cross_date_positions': 0,
                    'overlapping_positions': 0, 'labels_timed_at': 'actual buy-stop submission'}


def add_trade_features(report, features):
    frame = report.copy()
    frame['session'] = frame.submitted.dt.normalize()
    frame['initial_risk_dollars'] = (frame.requested_price-frame.original_sl)*POINT_VALUE
    frame['fill_risk_dollars'] = (frame.fill_price-frame.original_sl)*POINT_VALUE
    frame['fill_minus_request_dollars'] = (frame.fill_price-frame.requested_price)*POINT_VALUE
    assert (frame.initial_risk_dollars > 0).all()
    frame['gross_r'] = frame.trade_profit/frame.initial_risk_dollars
    frame['net_dollars'] = frame.trade_profit-COST
    frame['net_r'] = frame.net_dollars/frame.initial_risk_dollars
    frame['commission_r'] = COST/frame.initial_risk_dollars
    frame['holding_minutes'] = (frame.exit_time-frame.entry_time).dt.total_seconds()/60
    for stress in (1, 2):
        frame[f'stress{stress}_net_dollars'] = frame.net_dollars-stress
        frame[f'stress{stress}_net_r'] = frame[f'stress{stress}_net_dollars']/frame.initial_risk_dollars
    frame['year'] = frame.session.dt.year
    frame['week_start'] = frame.session-pd.to_timedelta(frame.session.dt.dayofweek, unit='D')
    frame['era'] = 'warmup_2010-15'
    for era, (start, stop) in ERAS.items():
        frame.loc[(frame.session >= start) & (frame.session < stop), 'era'] = era
    frame.loc[frame.session >= '2026-10-01', 'era'] = 'partial_endpoint'
    frame['primary'] = frame.era.isin(ERAS)
    frame = frame.merge(features.drop(columns=['close', 'return_log', 'volatility20', 'volatility_robust20']),
                        left_on='session', right_index=True, how='left', validate='many_to_one')
    assert frame.group.notna().all()
    assert frame.loc[frame.primary, ['group', 'group_p70', 'group_p80', 'group_roll_robust']].isin(GROUPS).all().all()
    assert (frame.previous_date.dropna() < frame.loc[frame.previous_date.notna(), 'session']).all()
    return frame


def drawdowns(trades, daily):
    order = trades.sort_values(['exit_time', 'entry_time', 'ticket'], kind='stable')
    equity = np.r_[0.0, order.net_dollars.cumsum().to_numpy()]
    closed_dd = float(np.max(np.maximum.accumulate(equity)-equity))
    peak, balance, duration = 0.0, 0.0, 0
    peak_date = daily.index[0]
    daily_dd = 0.0
    for date, pnl in daily.items():
        balance += float(pnl)
        daily_dd = max(daily_dd, peak-balance)
        if balance >= peak-1e-9:
            peak = max(peak, balance)
            peak_date = date
        else:
            duration = max(duration, (date-peak_date).days)
    return closed_dd, float(daily_dd), int(duration)


def metrics(trades, calendar):
    calendar = pd.DatetimeIndex(calendar)
    assert len(calendar) and calendar.is_unique
    daily = trades.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.0)
    weeks = daily.index-pd.to_timedelta(daily.index.dayofweek, unit='D')
    weekly = daily.groupby(weeks).sum()
    closed_dd, daily_dd, duration = drawdowns(trades, daily)
    losses = float(trades.loc[trades.net_dollars < 0, 'net_dollars'].sum())
    profit = float(trades.loc[trades.net_dollars > 0, 'net_dollars'].sum())
    n = len(trades)
    result = {'trades': n, 'active_sessions': int(trades.session.nunique()),
              'active_weeks': int(trades.week_start.nunique()), 'eligible_sessions': len(calendar),
              'eligible_weeks': len(weekly), 'gross_mean_r': float(trades.gross_r.mean()),
              'net_mean_r': float(trades.net_r.mean()), 'gross_dollars': float(trades.trade_profit.sum()),
              'net_dollars': float(trades.net_dollars.sum()), 'dollar_pf': profit/-losses if losses else np.nan,
              'risk_mean': float(trades.initial_risk_dollars.mean()), 'risk_median': float(trades.initial_risk_dollars.median()),
              'commission_mean_r': float(trades.commission_r.mean()),
              'holding_hours': float(trades.holding_minutes.sum()/60),
              'mean_holding_minutes': float(trades.holding_minutes.mean()),
              'worst_day': float(daily.min()), 'worst_week': float(weekly.min()),
              'worst5pct_session_mean': float(daily.nsmallest(math.ceil(.05*len(daily))).mean()),
              'closed_trade_dd': closed_dd, 'daily_close_dd': daily_dd, 'daily_dd_duration_days': duration}
    for stress in (1, 2):
        result[f'stress{stress}_net_dollars'] = float(trades[f'stress{stress}_net_dollars'].sum())
        result[f'stress{stress}_mean_r'] = float(trades[f'stress{stress}_net_r'].mean())
    return result


def bootstrap_era(trades, calendar, rng):
    """One paired sample of week IDs is shared by every group and complement."""
    first = calendar[0]-pd.Timedelta(days=calendar[0].dayofweek)
    last = calendar[-1]-pd.Timedelta(days=calendar[-1].dayofweek)
    week_index = pd.date_range(first, last, freq='7D')
    n_weeks = len(week_index)
    sums, counts = [], []
    for group in GROUPS:
        part = trades.loc[trades.group == group]
        weekly = part.groupby('week_start').net_r.agg(['sum', 'count']).reindex(week_index, fill_value=0)
        sums.append(weekly['sum'].to_numpy())
        counts.append(weekly['count'].to_numpy())
    sums, counts = np.stack(sums, axis=1), np.stack(counts, axis=1)
    starts = rng.integers(0, n_weeks, size=(DRAWS, math.ceil(n_weeks/4)))
    sampled = ((starts[:, :, None]+np.arange(4)) % n_weeks).reshape(DRAWS, -1)[:, :n_weeks]
    bs_sums, bs_counts = np.zeros((DRAWS, 6)), np.zeros((DRAWS, 6))
    for start in range(0, DRAWS, 250):
        indices = sampled[start:start+250]
        bs_sums[start:start+250] = sums[indices].sum(axis=1)
        bs_counts[start:start+250] = counts[indices].sum(axis=1)
    result = {}
    total_sums, total_counts = bs_sums.sum(axis=1), bs_counts.sum(axis=1)
    metadata = {'draws': DRAWS, 'calendar_weeks': n_weeks, 'block_weeks': 4,
                'blocks_per_draw': math.ceil(n_weeks/4), 'circular': True,
                'trim_sample_to_weeks': n_weeks, 'groups': {}}
    for g, group in enumerate(GROUPS + ('all',)):
        numer = bs_sums[:, g] if group != 'all' else total_sums
        denom = bs_counts[:, g] if group != 'all' else total_counts
        valid_mean = denom > 0
        means = np.full(DRAWS, np.nan)
        means[valid_mean] = numer[valid_mean]/denom[valid_mean]
        valid_difference = valid_mean & ((total_counts-denom) > 0) if group != 'all' else np.zeros(DRAWS, dtype=bool)
        differences = np.full(DRAWS, np.nan)
        differences[valid_difference] = means[valid_difference]-(total_sums[valid_difference]-numer[valid_difference])/(total_counts[valid_difference]-denom[valid_difference])
        values = {}
        for prefix, array in (('mean_net_r', means), ('difference_net_r', differences)):
            finite = array[np.isfinite(array)]
            for suffix, alpha in (('95', .05), ('99_1667', .05/6)):
                low, high = np.quantile(finite, [alpha/2, 1-alpha/2], method='linear') if len(finite) else (np.nan, np.nan)
                values[f'{prefix}_ci{suffix}_low'] = float(low)
                values[f'{prefix}_ci{suffix}_high'] = float(high)
        part = trades.loc[trades.group == group] if group != 'all' else trades
        complement = trades.loc[trades.group != group] if group != 'all' else trades.iloc[:0]
        values['complement_trades'] = len(complement)
        values['complement_net_mean_r'] = float(complement.net_r.mean())
        values['difference_net_r'] = float(part.net_r.mean()-complement.net_r.mean())
        values['bootstrap_valid_mean_draws'] = int(valid_mean.sum())
        values['bootstrap_invalid_mean_draws'] = int((~valid_mean).sum())
        values['bootstrap_valid_difference_draws'] = int(valid_difference.sum())
        values['bootstrap_invalid_difference_draws'] = int((~valid_difference).sum()) if group != 'all' else 0
        result[group] = values
        metadata['groups'][group] = {'invalid_mean_draws': int((~valid_mean).sum()),
                                     'invalid_difference_draws': int((~valid_difference).sum()) if group != 'all' else None,
                                     'mean_distribution_degenerate': bool(np.nanstd(means) == 0),
                                     'difference_distribution_degenerate': bool(np.nanstd(differences) == 0) if group != 'all' else None}
    return result, metadata


def candidate_screen(summaries, yearly, sensitivities):
    primary = summaries.set_index(['group', 'era'])
    sensitivity = sensitivities.set_index(['group', 'era', 'sensitivity'])
    groups = []
    for group in GROUPS:
        eras = primary.loc[group]
        annual = yearly.loc[(yearly.group == group) & (yearly.year <= 2025) & (yearly.trades >= 30)]
        negative_years = int((annual.net_dollars < 0).sum())
        annual_fraction = negative_years/len(annual) if len(annual) else 0.0
        variants = sensitivity.loc[group]
        coverage = bool(((eras.trades >= 200) & (eras.active_weeks >= 30)).all())
        negative = bool(((eras.net_dollars < 0) & (eras.net_mean_r < 0)).all())
        below = bool((eras.difference_net_r < 0).all())
        sensitivity_coverage = bool(((variants.trades >= 200) & (variants.active_weeks >= 30)).all())
        sensitivity_negative = bool(((variants.net_dollars < 0) & (variants.net_mean_r < 0)).all())
        checks = {'coverage': coverage, 'negative_both_eras': negative,
                  'below_complement_both_eras': below,
                  'annual_negative_share': bool(len(annual) >= 5 and annual_fraction >= .6),
                  'sensitivities': sensitivity_coverage and sensitivity_negative}
        groups.append({'group': group, 'checks': checks, 'qualifies': all(checks.values()),
                       'full_year_count': len(annual), 'negative_full_year_count': negative_years,
                       'negative_full_year_fraction': annual_fraction,
                       'sensitivity_coverage': sensitivity_coverage,
                       'sensitivity_negative_dollars_and_r': sensitivity_negative,
                       'sensitivity_result': 'inconclusive_sparse' if not sensitivity_coverage else ('stable_negative' if sensitivity_negative else 'not_stable_negative'),
                       'failed_checks': [key for key, passed in checks.items() if not passed]})
    qualified = [row['group'] for row in groups if row['qualifies']]
    selected = min(qualified, key=lambda group: (primary.loc[(group, '2016-19'), 'net_mean_r'], group)) if qualified else None
    return {'protocol_sha256': PROTOCOL_SHA256, 'exploratory_only': True, 'groups': groups,
            'qualified_groups': qualified, 'selected_candidate': selected,
            'conditional_steps_triggered': bool(qualified),
            'decision': 'freeze_one_candidate_gate_before_simulation' if qualified else 'no_candidate_conditional_steps_6_8_not_triggered'}


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    paths = (PROTOCOL, RAW, STATS, HTML, INI, COMPLETION, MANIFEST, DAILY, M30, MINUTES, ROLLS, Path(__file__))
    inputs = {str(path): digest(path) for path in paths}
    print('Input hashes complete; reconciling original MT5 orders and deals.', flush=True)
    report, audit = reconcile_sources(inputs)
    reference = pd.read_csv(DAILY, parse_dates=['date']).set_index('date')
    m30 = pd.read_csv(M30, parse_dates=['bar_time']).set_index('bar_time')
    closes = m30.loc[m30.index.hour >= 1].groupby(m30.loc[m30.index.hour >= 1].index.normalize()).close.last()
    closes.index.name = 'date'
    pd.testing.assert_index_equal(closes.index, reference.index)
    assert np.array_equal(closes.to_numpy(), reference.close.to_numpy())
    print('Daily and M30 closes agree; checking original minute source.', flush=True)
    source_closes, source_audit = source_daily_closes()
    pd.testing.assert_index_equal(closes.index, source_closes.index)
    assert np.array_equal(closes.to_numpy(), source_closes.to_numpy())
    audit.update(source_audit)
    audit['daily_m30_and_original_minute_closes_match'] = True
    rolls = pd.read_csv(ROLLS, parse_dates=['date'])
    assert rolls.date.is_unique and rolls.date.is_monotonic_increasing
    switches = rolls.loc[rolls.symbol.ne(rolls.symbol.shift()) & rolls.symbol.shift().notna(), 'date']
    assert switches.isin(closes.index).all()
    features = build_features(closes, switches)
    assert np.allclose(features.sma50, reference.sma50, equal_nan=True, atol=1e-8, rtol=1e-10)
    assert np.allclose(features.sma200, reference.sma200, equal_nan=True, atol=1e-8, rtol=1e-10)
    assert np.array_equal(features.trend, reference.regime50)
    audit['trend_reference_matches'] = True
    audit['contract_switch_dates'] = [str(value.date()) for value in switches]
    trades = add_trade_features(report, features)
    final = trades.loc[trades.era == 'partial_endpoint']
    assert len(final) == 1 and final.iloc[0].exit_comment == 'end of test'
    assert final.iloc[0].session == pd.Timestamp('2026-10-01')
    assert pd.Timestamp(source_audit['source_final_timestamp']) == pd.Timestamp('2026-10-01 02:59:00')
    audit['endpoint'] = {'session': '2026-10-01', 'trades': len(final),
                         'gross_dollars': float(final.trade_profit.sum()), 'net_dollars': float(final.net_dollars.sum()),
                         'exit_comment': str(final.iloc[0].exit_comment), 'excluded_primary': True}
    audit['era_reconciliation'] = []
    for era, part in trades.groupby('era', sort=False):
        audit['era_reconciliation'].append({'era': era, 'trades': len(part),
                                            'gross_dollars': float(part.trade_profit.sum()),
                                            'net_dollars': float(part.net_dollars.sum()),
                                            'gross_mean_r': float(part.gross_r.mean()), 'net_mean_r': float(part.net_r.mean())})
    recent_inclusive = trades.loc[trades.session >= '2020-01-01']
    audit['2020_plus_inclusive_reconciliation'] = {'trades': len(recent_inclusive),
                                                  'gross_dollars': float(recent_inclusive.trade_profit.sum()),
                                                  'net_dollars': float(recent_inclusive.net_dollars.sum())}
    features.to_csv(STUDY/'daily_features.csv', float_format='%.15g')
    trades.to_csv(STUDY/'trades.csv', index=False, float_format='%.15g')
    print('Whole-run ledger and causally lagged labels reconciled. Computing primary metrics/bootstrap.', flush=True)
    rng = np.random.default_rng(SEED)
    summary_rows, bootstrap, sensitivity_rows, label_changes, session_rows = [], {}, [], [], []
    for era, (start, stop) in ERAS.items():
        calendar = features.index[(features.index >= start) & (features.index < stop) & (features.group != 'warmup')]
        part = trades.loc[trades.era == era]
        assert part.session.isin(calendar).all()
        estimates, meta = bootstrap_era(part, calendar, rng)
        bootstrap[era] = meta
        for group in GROUPS + ('all',):
            selected = part.loc[part.group == group] if group != 'all' else part
            summary_rows.append(dict(era=era, group=group, **metrics(selected, calendar), **estimates[group]))
            daily = selected.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.0)
            session_rows.extend({'era': era, 'group': group, 'session': str(date.date()), 'net_dollars': float(pnl)} for date, pnl in daily.items())
        for sensitivity, column in SENSITIVITIES.items():
            for group in GROUPS + ('all',):
                selected = part.loc[part[column] == group] if group != 'all' else part
                sensitivity_rows.append(dict(sensitivity=sensitivity, era=era, group=group, **metrics(selected, calendar)))
            f = features.loc[calendar]
            label_changes.append({'era': era, 'sensitivity': sensitivity, 'eligible_sessions': len(calendar),
                                   'changed_sessions': int((f[column] != f.group).sum()), 'trades': len(part),
                                   'changed_trade_labels': int((part[column] != part.group).sum())})
    summaries = pd.DataFrame(summary_rows)
    sensitivities = pd.DataFrame(sensitivity_rows)
    yearly_rows = []
    for year in range(2016, 2027):
        stop = min(pd.Timestamp(year+1, 1, 1), pd.Timestamp('2026-10-01'))
        calendar = features.index[(features.index >= pd.Timestamp(year, 1, 1)) & (features.index < stop) & (features.group != 'warmup')]
        part = trades.loc[trades.primary & (trades.year == year)]
        for group in GROUPS + ('all',):
            selected = part.loc[part.group == group] if group != 'all' else part
            yearly_rows.append(dict(year=year, partial=(year == 2026), group=group, **metrics(selected, calendar)))
    yearly = pd.DataFrame(yearly_rows)
    for era in ERAS:
        subset = summaries.loc[(summaries.era == era) & (summaries.group != 'all')]
        whole = summaries.loc[(summaries.era == era) & (summaries.group == 'all')].iloc[0]
        assert subset.trades.sum() == whole.trades
        assert np.isclose(subset.net_dollars.sum(), whole.net_dollars, atol=1e-8)
    summaries.to_csv(STUDY/'summaries.csv', index=False, float_format='%.15g')
    yearly.to_csv(STUDY/'yearly.csv', index=False, float_format='%.15g')
    sensitivities.to_csv(STUDY/'sensitivities.csv', index=False, float_format='%.15g')
    pd.DataFrame(label_changes).to_csv(STUDY/'sensitivity_label_changes.csv', index=False)
    pd.DataFrame(session_rows).to_csv(STUDY/'session_pnl.csv', index=False, float_format='%.15g')
    gates = candidate_screen(summaries, yearly, sensitivities)
    save_json(STUDY/'candidate_gates.json', gates)
    audit['exact_six_group_partition'] = True
    audit['bootstrap'] = {'seed': SEED, 'eras': bootstrap,
                           'rng': 'numpy.default_rng PCG64, era order 2016-19 then 2020-26',
                           'quantiles': {'95': [.025, .975], '99.1666667': [.05/12, 1-.05/12]}}
    audit['metric_definitions'] = {'week': 'Monday-start calendar week, no omitted calendar weeks in bootstrap',
                                  'worst5pct': 'ceil(0.05 * eligible sessions), including zero group PnL sessions',
                                  'closed_trade_order': 'exit_time, entry_time, ticket ascending stable',
                                  'daily_dd_duration': 'calendar days from last daily-close high; initial zero anchored first eligible session; ties reset; unrecovered periods included',
                                  'daily_pnl': 'realized completed-trade net dollars; no cross-date positions; no intratrade MTM',
                                  'commission': '1.05 USD per completed trade', 'planned_risk': '(requested price - original stop) * 2 USD',
                                  'cost_stress': 'additional 1 and 2 USD per trade, not measured slippage'}
    save_json(STUDY/'audit.json', audit)
    generated_names = ('daily_features.csv', 'trades.csv', 'summaries.csv', 'yearly.csv', 'sensitivities.csv',
                       'sensitivity_label_changes.csv', 'session_pnl.csv', 'candidate_gates.json', 'audit.json')
    outputs = {name: digest(STUDY/name) for name in generated_names}
    provenance = {'study': 'RTL daily trend x volatility frozen first-stage diagnostic',
                  'protocol_sha256': PROTOCOL_SHA256, 'inputs_sha256': inputs, 'outputs_sha256': outputs,
                  'primary_eras': ERAS, 'software': {'numpy': np.__version__, 'pandas': pd.__version__},
                  'baseline_mutated': False, 'strategy_changed': False,
                  'limitations': ['One-minute OHLC tester data; no measured slippage.',
                                  'Historical research repeatedly examined; no untouched validation.',
                                  'Closed-trade and daily-close drawdown exclude intratrade MTM.',
                                  'Inference uses only complete sessions; final end-of-test trade separately reconciled.']}
    save_json(STUDY/'provenance.json', provenance)
    print(summaries[['era', 'group', 'trades', 'net_dollars', 'net_mean_r', 'risk_mean']].to_string(index=False), flush=True)
    print(json.dumps({'qualified_groups': gates['qualified_groups'], 'selected_candidate': gates['selected_candidate']}), flush=True)
    print('Wrote study outputs, audit, and SHA256 provenance.', flush=True)


if __name__ == '__main__':
    main()

