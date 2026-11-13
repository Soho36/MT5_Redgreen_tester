"""Review of the native whipsaw overlays (docs/baseline/whipsaw-native/RESULTS.md).

Written 2026-11-12 at the user's request. Descriptive, on the same reused history; nothing here is
a new rule. Every check was fixed in this docstring before its result was looked at.

A. Reproduce the published figures with separate code
   1. Trades and net dollars of the eight native runs: parsed reports against the EA's own ledgers.
   2. The 174 next sessions and the 403 sessions of days 1-3, rebuilt from the frozen event study;
      the selected arms equal the control's trades on those sessions.
   3. Equity drawdown of the controls and of every overlay, rebuilt sample by sample from the raw
      native equity files (full paths, no session envelopes).
   4. The month-resampling intervals of the extra dollars per calendar session.

B. What the figures mean
   1. Per trade: planned risk, gross R, commission in R and net R on next sessions and elsewhere.
   2. Trades of equal planned risk in the same year (tenths of risk within each year): is a
      next-session trade better, in gross R and in net R? Month resampling, 5,000 draws.
   3. Concentration: the extra profit by year and without its five best sessions; how many of the
      control's ten best and ten worst sessions are next sessions.
   4. The extra contract against three alternatives that need no whipsaw rule:
      a) the normal strategy scaled up evenly to the same profit;
      b) an extra contract on as many randomly chosen other sessions of the same years;
      c) an extra contract on the sessions after equally large days: for every whipsaw day one
         non-whipsaw day of the same year and size group (the frozen study's controls).
      b and c: 5,000 draws each; the whipsaw overlay's extra profit, drawdown and profit per
      dollar of drawdown are ranked among the draws.
   5. The per-trade comparison (B1, B2) on the saved native RTL and GG runs of ES, YM and RTY,
      with each instrument's own whipsaw days.
   6. 2R against 1R on every session with the minute simulator: is the next session special?
      The simulated next-session 2R trades must equal the native 2R arm in net dollars.

Added after the first run of A and B1-B6, each again written down before its result was seen
(except the two market figures of B7, noticed while reading the follow-up's prediction file):

   3+. Are the control's worst session, worst drawdown inside a session and largest single-trade
       risk on next sessions? How much does one session's result vary there and elsewhere?
   4d. Label shuffle: the whipsaw label is shuffled among all days of the same year and size group
       (whipsaw days included), so the few extreme sessions can land in any draw. The share of
       draws that earn less is a fair test; b and c leave the whipsaw sessions out of the draws.
   4e. Dollar split of the next-session profit: what the same trades would have earned at the net R
       of other trades of equal risk in the same year, and the rest ("better trades").
   7.  The flag against a volatility forecast: in each year take as many days as there were
       whipsaw days, those with the highest volatility-only forecast of the follow-up study
       (fitted on earlier years). Next move, and what RTL and GG earned on the sessions after.
   8.  Shorts: the saved native RTL-short and GG-short runs on next sessions and elsewhere.

Pooled = 2016 to September 2026 unless said otherwise. One MNQ, $1.05 per round trip.
"""
import json

import numpy as np
import pandas as pd

import analyze_rtl_vwap_cross as cx
import analyze_whipsaw_days as study
import rtl_weekly_engine as engine
import whipsaw_days as wd
from project_paths import PROJECT_ROOT as ROOT
from verify_rtl_failed_breakout_short import CACHE

NATIVE = ROOT / 'Reports/whipsaw_native_20261112'
DAYS = ROOT / 'Reports/whipsaw_days_20261111'
DOC = ROOT / 'docs/baseline/whipsaw-native'
COST = 1.05
SEED, DRAWS = 20261112, 5000
ERAS = {'2016-19': ('2016-01-01', '2020-01-01'), '2020-26': ('2020-01-01', '2026-10-01'),
        '2016-26': ('2016-01-01', '2026-10-01')}
POLICIES = {'control': 1, 'day1': 1, 'days123': 1, 'day1_rr2': 2}
EQUITY = np.dtype([('time', '<i8'), ('balance', '<f8'), ('equity', '<f8'), ('closed', '<i8')])
OTHER = {'ES': ('ym_baselines_20261023', 'ymbase_20261023_{}_es', ('2016-01-01', '2026-10-01')),
         'YM': ('ym_baselines_20261023', 'ymbase_20261023_{}_ym', ('2016-01-01', '2026-10-01')),
         'RTY': ('rty_baselines_20261023', 'rtybase_20261023_{}', ('2018-01-01', '2026-10-01'))}
ROWS = []


def record(check, item, measure, value, low=np.nan, high=np.nan):
    ROWS.append(dict(check=check, item=item, measure=measure, value=value, low=low, high=high))


def inside(dates, era):
    start, end = ERAS[era] if isinstance(era, str) else era
    return (dates >= start) & (dates < end)


def native_trades(strategy, policy):
    path = NATIVE / f'whipnative_20261112_{strategy}_{policy}_trades.csv'
    return pd.read_csv(path, parse_dates=['submitted', 'entry_time', 'exit_time', 'session'])


# ---------------------------------------------------------------- A: reproduction

def sessions_after_whipsaw():
    """Next sessions (day 1) and the union of days 1-3, from the frozen study's own session table."""
    panel = pd.read_csv(DAYS / 'sessions.csv', index_col=0, parse_dates=[0, 'next_session'])
    table = wd.session_table(wd.read_m30())
    events = panel.loc[panel.whipsaw & inside(panel.index, '2016-26')]
    day1 = pd.DatetimeIndex(events.next_session.dropna())
    later = set()
    for position in events.position:
        for step in (1, 2, 3):
            if position + step < len(table) and table.index[position + step] < pd.Timestamp(wd.END):
                later.add(table.index[position + step])
    return panel, table, day1, pd.DatetimeIndex(sorted(later))


def check_ledgers(trades):
    published = pd.read_csv(DOC / 'native_summary.csv').set_index(['strategy', 'policy', 'era'])
    for (strategy, policy), frame in trades.items():
        rr = POLICIES[policy]
        own = pd.read_csv(NATIVE / f'rtlvwap_whipnative_20261112_{strategy}_{policy}_{rr:.2f}.csv', sep='\t', encoding='utf-16')
        assert len(own) == len(frame) and np.isclose(own.trade_profit.sum(), frame.trade_profit.sum(), atol=1e-6)
        assert np.array_equal(np.sort(own.ticket.to_numpy()), np.sort(frame.ticket.to_numpy()))
        for era in ERAS:
            part = frame.loc[inside(frame.session, era)]
            net = float((part.trade_profit - COST).sum())
            row = published.loc[(strategy, policy, era)]
            assert len(part) == row.contract_round_trips and abs(net - row.net) < .005, (strategy, policy, era)
            record('A1 ledgers', f'{strategy} {policy} {era}', 'trades', len(part))
            record('A1 ledgers', f'{strategy} {policy} {era}', 'net dollars', net)


def check_subsets(trades, day1, days123):
    for strategy in ('rtl', 'gg'):
        control = trades[(strategy, 'control')]
        for policy, dates in (('day1', day1), ('days123', days123)):
            arm = trades[(strategy, policy)]
            arm = arm.loc[inside(arm.session, '2016-26')]
            subset = control.loc[control.session.isin(dates) & inside(control.session, '2016-26')]
            assert len(arm) == len(subset) and set(arm.session) <= set(dates)
            assert np.isclose(arm.net_dollars.sum(), subset.net_dollars.sum(), atol=1e-6)
            assert np.array_equal(arm.entry_time.to_numpy(), subset.entry_time.to_numpy())
            record('A2 sessions', f'{strategy} {policy}', 'sessions allowed', len(dates))
            record('A2 sessions', f'{strategy} {policy}', 'trades equal to the control subset', len(arm))


def session_paths(strategy, policy, trades):
    """Per session: the cost-adjusted equity path relative to the session's start, from raw samples."""
    data = np.fromfile(NATIVE / f'window_equity_whipnative_20261112_{strategy}_{policy}.bin', dtype=EQUITY)
    times, equity = data['time'], data['equity']
    exits = np.sort(trades.exit_time.to_numpy().astype('datetime64[s]').astype(np.int64))
    missing = exits[~np.isin(exits, times)]         # a zero-profit close leaves no equity sample
    if len(missing):
        before = np.searchsorted(times, missing, side='right') - 1
        times, equity = np.r_[times, missing], np.r_[equity, equity[before]]
        order = np.argsort(times, kind='stable')
        times, equity = times[order], equity[order]
    net = equity - COST * np.searchsorted(exits, times, side='right')
    day = times // 86400
    edges = np.r_[0, np.flatnonzero(np.diff(day)) + 1, len(day)]
    paths, level = {}, 500000.0
    for a, b in zip(edges[:-1], edges[1:]):
        paths[pd.Timestamp(int(day[a]), unit='D')] = net[a:b] - level
        level = net[b - 1]
    return paths


def path_drawdown(pieces):
    """Largest fall from an earlier peak along consecutive session paths, starting flat at zero."""
    level, peak, worst = 0.0, 0.0, 0.0
    for piece in pieces:
        values = level + piece
        running = np.maximum.accumulate(np.r_[peak, values])
        worst = max(worst, float((running[1:] - values).max()))
        peak, level = float(running[-1]), float(values[-1])
    return worst


def envelopes(paths, calendar):
    """Net, lowest, highest and internal drawdown of each session path, zero on idle sessions."""
    rows = {}
    for date in calendar:
        p = np.r_[0.0, paths.get(date, np.zeros(1))]
        rows[date] = (p[-1], p.min(), p.max(), float((np.maximum.accumulate(p) - p).max()))
    return pd.DataFrame.from_dict(rows, orient='index', columns=['net', 'low', 'high', 'dd'])


def scaled_drawdown(env, multiple):
    """Equity drawdown when each session's path is multiplied (rows of `multiple` = scenarios)."""
    multiple = np.atleast_2d(multiple).astype(float)
    net = multiple * env.net.to_numpy()
    before = np.cumsum(net, axis=1) - net
    high, low = before + multiple * env.high.to_numpy(), before + multiple * env.low.to_numpy()
    peak = np.maximum.accumulate(np.c_[np.zeros(len(multiple)), high], axis=1)[:, :-1]
    return np.maximum(peak - low, multiple * env.dd.to_numpy()).max(axis=1)


def month_interval(values, dates):
    months, index = np.unique(dates.year * 12 + dates.month, return_inverse=True)
    totals, counts = np.bincount(index, weights=values), np.bincount(index)
    weights = np.random.default_rng(SEED).multinomial(len(months), np.full(len(months), 1 / len(months)), size=DRAWS)
    return np.percentile((weights @ totals) / (weights @ counts), [2.5, 97.5])


def check_overlays(trades, paths, calendar, day1, days123):
    published = pd.read_csv(DOC / 'overlays.csv').set_index(['strategy', 'policy', 'era'])
    summary = pd.read_csv(DOC / 'native_summary.csv').set_index(['strategy', 'policy', 'era'])
    out = {}
    for strategy in ('rtl', 'gg'):
        base = paths[(strategy, 'control')]
        for era in ERAS:
            dates = calendar[inside(calendar, era)]
            flat = np.zeros(1)
            control_dd = path_drawdown(base.get(d, flat) for d in dates)
            assert abs(control_dd - summary.loc[(strategy, 'control', era), 'equity_dd']) < .01, (strategy, era, control_dd)
            record('A3 drawdown', f'{strategy} control {era}', 'equity drawdown', control_dd)
            for policy, active in (('day1', day1), ('days123', days123), ('day1_rr2', day1)):
                on = set(active)
                other = paths[(strategy, policy)]
                if policy == 'day1_rr2':
                    pieces = [(other.get(d, flat) if d in on else base.get(d, flat)) for d in dates]
                else:
                    pieces = [base.get(d, flat) * (2 if d in on else 1) for d in dates]
                    for d in dates:     # the selected arm's own path must be the control's path on that session
                        if d in on and d in base:
                            mine, theirs = base[d], other[d]
                            same = mine.shape == theirs.shape and np.allclose(mine, theirs, atol=2e-6)
                            assert same or np.allclose([mine[-1], mine.min(), mine.max()],
                                                       [theirs[-1], theirs.min(), theirs.max()], atol=2e-6), (strategy, policy, d)
                dd, net = path_drawdown(pieces), float(sum(p[-1] for p in pieces))
                row = published.loc[(strategy, policy, era)]
                assert abs(dd - row.equity_dd) < .01 and abs(net - row.net) < .01, (strategy, policy, era, dd, net)
                base_net = np.array([base.get(d, flat)[-1] for d in dates])
                delta = np.array([p[-1] for p in pieces]) - base_net
                low, high = month_interval(delta, dates)
                assert abs(low - row.extra_mean_ci_low) < 1e-6 and abs(high - row.extra_mean_ci_high) < 1e-6, (strategy, policy, era)
                record('A3 drawdown', f'{strategy} {policy} {era}', 'equity drawdown', dd)
                record('A3 drawdown', f'{strategy} {policy} {era}', 'net dollars', net)
                record('A4 intervals', f'{strategy} {policy} {era}', 'extra dollars per calendar session', delta.mean(), low, high)
                out[(strategy, policy, era)] = dict(net=net, dd=dd, extra=float(delta.sum()))
            out[(strategy, 'control', era)] = dict(net=float(sum(base.get(d, flat)[-1] for d in dates)), dd=control_dd, extra=0.0)
    return out


# ---------------------------------------------------------------- B: meaning

def per_trade(frame, flag, label, check='B1 per trade'):
    for group, part in (('next sessions', frame.loc[flag]), ('other sessions', frame.loc[~flag])):
        for measure, value in (('trades', len(part)), ('mean planned risk $', part.initial_risk_dollars.mean()),
                               ('gross R', part.gross_r.mean()), ('commission R', part.commission_r.mean()),
                               ('net R', part.net_r.mean()), ('win %', 100 * part.net_dollars.gt(0).mean()),
                               ('net $ per trade', part.net_dollars.mean())):
            record(check, f'{label} {group}', measure, value)


def risk_matched(frame, flag, label, check='B2 equal risk'):
    """Next-session trades minus other trades of the same year and the same tenth of planned risk."""
    data = frame.assign(next_session_trade=np.asarray(flag)).sort_values(['submitted', 'ticket'], kind='stable').reset_index(drop=True)
    flag = data.next_session_trade.to_numpy()
    year = data.session.dt.year.to_numpy()
    tenth = np.empty(len(data), int)
    for value in np.unique(year):
        rows = np.flatnonzero(year == value)
        tenth[rows] = wd.size_groups(data.initial_risk_dollars.to_numpy()[rows])
    panel = pd.DataFrame(dict(year=year, size_group=tenth, event=flag, range_ratio=np.log(data.initial_risk_dollars.to_numpy()),
                              gross_r=data.gross_r.to_numpy(), net_r=data.net_r.to_numpy()))
    months, month = np.unique(data.session.dt.year.to_numpy() * 12 + data.session.dt.month.to_numpy(), return_inverse=True)
    weights = study.month_weights(len(months), DRAWS, SEED)
    for outcome in ('gross_r', 'net_r'):
        row, _ = study.compare(panel, 'event', outcome, month, weights)
        record(check, label, f'{outcome}: next minus equal-risk trades', row['matched_diff'], row['matched_lo'], row['matched_hi'])
        record(check, label, f'{outcome}: same, corrected for exact risk', row['corrected_diff'], row['corrected_lo'], row['corrected_hi'])
    record(check, label, 'next-session trades used', int(row['events_used']))


def dollar_split(frame, flag, label):
    """Next-session net dollars = the same risk at the net R of equal-risk other trades + the rest."""
    data = frame.assign(next_session_trade=np.asarray(flag)).sort_values(['submitted', 'ticket'], kind='stable').reset_index(drop=True)
    on = data.next_session_trade.to_numpy()
    year = data.session.dt.year.to_numpy()
    tenth = np.empty(len(data), int)
    for value in np.unique(year):
        rows = np.flatnonzero(year == value)
        tenth[rows] = wd.size_groups(data.initial_risk_dollars.to_numpy()[rows])
    cells, cell = np.unique(year * 10 + tenth, return_inverse=True)
    months, month = np.unique(year * 12 + data.session.dt.month.to_numpy(), return_inverse=True)
    flat = month * len(cells) + cell

    def total(values, keep):
        return np.bincount(flat[keep], weights=values[keep], minlength=len(months) * len(cells)).reshape(len(months), len(cells))

    risk, net, r = (data[c].to_numpy(float) for c in ('initial_risk_dollars', 'net_dollars', 'net_r'))
    sums = [total(r, ~on), total(np.ones(len(data)), ~on), total(risk, on), total(net, on)]

    def split(weights):
        other_r, others, next_risk, next_net = (weights @ s for s in sums)
        usable = (others > 0) & (next_risk > 0)
        expected = np.where(usable, next_risk * np.divide(other_r, others, out=np.zeros_like(other_r), where=others > 0), 0.0)
        return expected.sum(-1), np.where(usable, next_net, 0.0).sum(-1) - expected.sum(-1)

    expected, better = split(np.ones(len(months)))
    draws_expected, draws_better = split(study.month_weights(len(months), DRAWS, SEED).astype(float))
    record('B4e dollar split', label, 'next-session net dollars', float(net[on].sum()))
    record('B4e dollar split', label, 'expected at the net R of equal-risk other trades', float(expected), *np.percentile(draws_expected, [2.5, 97.5]))
    record('B4e dollar split', label, 'rest: better trades', float(better), *np.percentile(draws_better, [2.5, 97.5]))


def extremes(strategy, control, day1, env):
    """Where the control's worst moments are, and how much one session varies."""
    on = env.index.isin(day1)
    record('B3+ extremes', f'{strategy} control', 'worst session is a next session (low = its result)', int(env.net.idxmin() in day1), env.net.min())
    record('B3+ extremes', f'{strategy} control', 'worst drawdown inside a session is on a next session (high = its size)',
           int(env.dd.idxmax() in day1), high=env.dd.max())
    scope = control.loc[inside(control.session, '2016-26')]
    largest = scope.loc[scope.initial_risk_dollars.idxmax()]
    record('B3+ extremes', f'{strategy} control', 'largest single-trade risk is on a next session (high = its size)',
           int(largest.session in day1), high=largest.initial_risk_dollars)
    for group, keep in (('next sessions', on), ('other sessions', ~on)):
        record('B3+ extremes', f'{strategy} {group}', 'session result: mean $', env.net[keep].mean())
        record('B3+ extremes', f'{strategy} {group}', 'session result: standard deviation $', env.net[keep].std())
        record('B3+ extremes', f'{strategy} {group}', 'session result: median $', env.net[keep].median())
        record('B3+ extremes', f'{strategy} {group}', 'session result: the worst 5% of sessions lose more than $', -env.net[keep].quantile(.05))
        record('B3+ extremes', f'{strategy} {group}', 'drawdown inside a session: mean $', env.dd[keep].mean())


def concentration(strategy, control, day1):
    part = control.loc[control.session.isin(day1) & inside(control.session, '2016-26')]
    by_year = part.groupby(part.session.dt.year).net_dollars.sum()
    for year, value in by_year.items():
        record('B3 concentration', f'{strategy} next sessions', f'net dollars {year}', value)
    record('B3 concentration', f'{strategy} next sessions', 'years above zero', int((by_year > 0).sum()), high=len(by_year))
    by_session = part.groupby('session').net_dollars.sum().reindex(day1, fill_value=0.0)
    record('B3 concentration', f'{strategy} next sessions', 'net dollars', by_session.sum())
    record('B3 concentration', f'{strategy} next sessions', 'net without the five best sessions', by_session.sum() - by_session.nlargest(5).sum())
    record('B3 concentration', f'{strategy} next sessions', 'sessions above zero %', 100 * (by_session > 0).mean())
    everything = control.loc[inside(control.session, '2016-26')].groupby('session').net_dollars.sum()
    record('B3 concentration', f'{strategy} control', 'next sessions among its ten best sessions', int(everything.nlargest(10).index.isin(day1).sum()))
    record('B3 concentration', f'{strategy} control', 'next sessions among its ten worst sessions', int(everything.nsmallest(10).index.isin(day1).sum()))
    record('B3 concentration', f'{strategy} control', 'sessions above zero %', 100 * (everything > 0).mean())


def alternatives(strategy, env, day1, panel, actual, base):
    """The extra contract on next sessions against even scaling and against placebo sessions."""
    dates = env.index
    record('B4 alternatives', f'{strategy} even scaling', 'drawdown at the overlay\'s profit', base['dd'] * actual['net'] / base['net'])
    record('B4 alternatives', f'{strategy} even scaling', 'profit at the overlay\'s drawdown', base['net'] * actual['dd'] / base['dd'])
    record('B4 alternatives', f'{strategy} whipsaw overlay', 'profit', actual['net'])
    record('B4 alternatives', f'{strategy} whipsaw overlay', 'drawdown', actual['dd'])
    rng = np.random.default_rng(SEED)
    is_day1 = dates.isin(day1)
    year = dates.year.to_numpy()
    per_year = {y: int(is_day1[year == y].sum()) for y in np.unique(year)}
    pools = {y: np.flatnonzero((year == y) & ~is_day1) for y in per_year}
    events = panel.loc[panel.whipsaw & inside(panel.index, '2016-26') & panel.next_session.notna()]
    controls = panel.loc[~panel.whipsaw & inside(panel.index, '2016-26') & panel.next_session.notna()]
    position = pd.Series(np.arange(len(dates)), index=dates)
    cells, shuffled = [], []
    for key, part in events.groupby(['year', 'size_group']):
        pool = controls.loc[(controls.year == key[0]) & (controls.size_group == key[1]), 'next_session']
        pool = position.reindex(pd.DatetimeIndex(pool)).dropna().to_numpy(int)
        own = position.reindex(pd.DatetimeIndex(part.next_session)).to_numpy(int)
        cells.append((pool, len(part)))
        shuffled.append((np.r_[pool, own], len(part)))
    record('B4 alternatives', f'{strategy} after equally large days', 'sessions per draw', sum(min(k, len(p)) for p, k in cells))

    def draws(kind):
        multiple = np.ones((DRAWS, len(dates)))
        for i in range(DRAWS):
            if kind == 'random':
                chosen = np.concatenate([rng.choice(pools[y], per_year[y], replace=False) for y in per_year if per_year[y]])
            else:
                source = cells if kind == 'matched' else shuffled
                chosen = np.concatenate([rng.choice(pool, min(k, len(pool)), replace=False) for pool, k in source])
            multiple[i, chosen] = 2
        extra = (multiple - 1) @ env.net.to_numpy()
        dd = np.concatenate([scaled_drawdown(env, multiple[a:a + 250]) for a in range(0, DRAWS, 250)])
        return extra, dd

    for kind, label in (('random', 'random other sessions, same years'), ('matched', 'after equally large days'),
                        ('shuffled', 'label shuffled within year and size group')):
        extra, dd = draws(kind)
        ratio = (base['net'] + extra) / dd
        item = f'{strategy} {label}'
        record('B4 alternatives', item, 'extra profit: median of draws', np.median(extra), *np.percentile(extra, [2.5, 97.5]))
        record('B4 alternatives', item, 'drawdown: median of draws', np.median(dd), *np.percentile(dd, [2.5, 97.5]))
        record('B4 alternatives', item, 'profit per drawdown dollar: median of draws', np.median(ratio), *np.percentile(ratio, [2.5, 97.5]))
        record('B4 alternatives', item, 'whipsaw overlay earns more than % of draws', 100 * np.mean(actual['extra'] > extra))
        record('B4 alternatives', item, 'whipsaw overlay has a smaller drawdown than % of draws', 100 * np.mean(actual['dd'] < dd))
        record('B4 alternatives', item, 'whipsaw overlay has more profit per drawdown dollar than % of draws',
               100 * np.mean(actual['net'] / actual['dd'] > ratio))


def other_instruments():
    for name, (folder, pattern, era) in OTHER.items():
        spec = cx.INSTRUMENTS[name]
        sessions = pd.read_csv(DAYS / f'sessions_{name}.csv', index_col=0, parse_dates=[0, 'next_session'])
        day1 = pd.DatetimeIndex(sessions.loc[sessions.whipsaw & inside(sessions.index, era), 'next_session'].dropna())
        for strategy in ('rtl', 'gg'):
            report = ROOT / 'Reports' / folder / (pattern.format(strategy) + '.htm')
            trades = cx.economics(cx.parse_report(report, spec['symbol']), spec)
            trades = trades.loc[inside(trades.session, era)].reset_index(drop=True)
            flag = trades.session.isin(day1).to_numpy()
            label = f'{name} {strategy}'
            record('B5 other instruments', label, 'next sessions', len(day1))
            per_trade(trades, flag, label, 'B5 other instruments')
            risk_matched(trades, flag, label, 'B5 other instruments')
            print('other instrument', label, len(trades), int(flag.sum()), flush=True)


def two_r(trades, panel, day1, calendar):
    """2R minus 1R on every session; next sessions against all others and against equally large days."""
    minutes = engine.load_minutes(cache=CACHE)
    cutoffs = engine.load_cutoffs()
    for strategy, signal in (('rtl', 'red'), ('gg', 'green')):
        sim, _ = engine.simulate_m30_ea(minutes, rr=2.0, signal=signal, cutoffs=cutoffs)
        sim['session'] = pd.to_datetime(sim.submitted).dt.normalize()
        sim['net'] = (sim.exit_price - sim.fill) * engine.POINT_VALUE - COST
        sim = sim.loc[inside(sim.session, '2016-26')]
        two = sim.groupby('session').net.sum()
        control = trades[(strategy, 'control')]
        one = control.loc[inside(control.session, '2016-26')].groupby('session').net_dollars.sum()
        dates = calendar[inside(calendar, '2016-26')]
        delta = two.reindex(dates, fill_value=0.0) - one.reindex(dates, fill_value=0.0)
        native = trades[(strategy, 'day1_rr2')]
        native = native.loc[inside(native.session, '2016-26')]
        assert abs(two.reindex(day1, fill_value=0.0).sum() - native.net_dollars.sum()) < .01, strategy
        on = dates.isin(day1)
        record('B6 2R', f'{strategy} next sessions', '2R minus 1R, dollars', delta[on].sum())
        record('B6 2R', f'{strategy} next sessions', '2R minus 1R per session', delta[on].mean(), *month_interval(delta[on].to_numpy(), dates[on]))
        record('B6 2R', f'{strategy} all other sessions', '2R minus 1R, dollars', delta[~on].sum())
        record('B6 2R', f'{strategy} all other sessions', '2R minus 1R per session', delta[~on].mean(), *month_interval(delta[~on].to_numpy(), dates[~on]))
        frame = panel.loc[inside(panel.index, '2016-26')].copy()
        frame['delta'] = frame.next_session.map(delta)
        months, month = np.unique(frame.month.to_numpy(), return_inverse=True)
        row, _ = study.compare(frame, 'whipsaw', 'delta', month, study.month_weights(len(months), DRAWS, SEED))
        record('B6 2R', f'{strategy}', '2R minus 1R after equally large days, per session', row['control_mean'])
        record('B6 2R', f'{strategy}', '2R gain: next sessions minus sessions after equally large days', row['matched_diff'], row['matched_lo'], row['matched_hi'])
        print('2R simulated', strategy, len(sim), flush=True)


def forecast_days(trades, panel):
    """As many days per year as whipsaw days, chosen by the follow-up's volatility-only forecast."""
    predicted = pd.read_csv(ROOT / 'Reports/whipsaw_followup_20261112/predictions.csv', index_col=0, parse_dates=[0, 'next_session'])
    predicted = predicted.loc[inside(predicted.index, '2016-26') & predicted.next_session.notna()]
    chosen = []
    for year, part in predicted.groupby(predicted.index.year):
        chosen.extend(part.pred_baseline.nlargest(int(part.whipsaw.sum())).index)
    top = predicted.loc[sorted(chosen)]
    flagged = predicted.loc[predicted.whipsaw]
    assert len(top) == len(flagged) == 174
    for label, part in (('whipsaw days', flagged), ('highest volatility forecast', top)):
        record('B7 forecast', label, 'days', len(part))
        record('B7 forecast', label, 'next move, normal-day ranges', part.abs_move_1.mean())
        record('B7 forecast', label, 'next move at least one normal range %', 100 * part.abs_move_1.ge(1).mean())
        record('B7 forecast', label, 'of them whipsaw days %', 100 * part.whipsaw.mean())
        for strategy in ('rtl', 'gg'):
            control = trades[(strategy, 'control')]
            session = control.loc[inside(control.session, '2016-26')].groupby('session').net_dollars.sum()
            net = session.reindex(pd.DatetimeIndex(part.next_session), fill_value=0.0)
            record('B7 forecast', label, f'{strategy} net dollars on the sessions after', net.sum())
            record('B7 forecast', label, f'{strategy} net dollars per session after', net.mean(), *month_interval(net.to_numpy(), net.index))
    both = top.index.intersection(flagged.index)
    record('B7 forecast', 'overlap', 'days in both lists', len(both))


def shorts(day1):
    """Saved native short runs (2026-10-23, same settings mirrored): next sessions against the rest."""
    for strategy in ('rtl', 'gg'):
        ledger = pd.read_csv(ROOT / f'Reports/ym_baselines_20261023/runband_ymbase_20261023_{strategy}_short_nq_1.00.csv',
                             sep='\t', encoding='utf-16')
        frame = pd.DataFrame(dict(
            ticket=ledger.ticket, submitted=pd.to_datetime(ledger.entry_time, format='%Y.%m.%d %H:%M:%S'),
            initial_risk_dollars=ledger.candle_range * engine.POINT_VALUE, trade_profit=ledger.trade_profit))
        frame['session'] = frame.submitted.dt.normalize()
        frame = frame.loc[inside(frame.session, '2016-26') & frame.initial_risk_dollars.gt(0)].reset_index(drop=True)
        frame['net_dollars'] = frame.trade_profit - COST
        frame['gross_r'] = frame.trade_profit / frame.initial_risk_dollars
        frame['net_r'] = frame.net_dollars / frame.initial_risk_dollars
        frame['commission_r'] = COST / frame.initial_risk_dollars
        flag = frame.session.isin(day1).to_numpy()
        label = f'{strategy} short'
        record('B8 shorts', f'{label} next sessions', 'net dollars', frame.net_dollars[flag].sum())
        record('B8 shorts', f'{label} other sessions', 'net dollars', frame.net_dollars[~flag].sum())
        per_trade(frame, flag, label, 'B8 shorts')
        risk_matched(frame, flag, label, 'B8 shorts')


def main():
    panel, table, day1, days123 = sessions_after_whipsaw()
    assert len(day1) == 174 and len(days123) == 403
    calendar = pd.DatetimeIndex(wd.read_m30().bar_time.dt.normalize().unique())
    trades = {(s, p): native_trades(s, p) for s in ('rtl', 'gg') for p in POLICIES}
    check_ledgers(trades)
    check_subsets(trades, day1, days123)
    print('A1, A2 reproduced', flush=True)
    paths = {key: session_paths(*key, frame) for key, frame in trades.items()}
    overlay = check_overlays(trades, paths, calendar, day1, days123)
    print('A3, A4 reproduced', flush=True)

    for strategy in ('rtl', 'gg'):
        control = trades[(strategy, 'control')]
        for era in ERAS:
            part = control.loc[inside(control.session, era)].reset_index(drop=True)
            flag = part.session.isin(day1).to_numpy()
            per_trade(part, flag, f'{strategy} {era}')
            risk_matched(part, flag, f'{strategy} {era}')
            dollar_split(part, flag, f'{strategy} {era}')
        concentration(strategy, control, day1)
        dates = calendar[inside(calendar, '2016-26')]
        env = envelopes(paths[(strategy, 'control')], dates)
        extremes(strategy, control, day1, env)
        assert abs(scaled_drawdown(env, np.ones(len(env)))[0] - overlay[(strategy, 'control', '2016-26')]['dd']) < .01
        assert abs(scaled_drawdown(env, 1 + dates.isin(day1))[0] - overlay[(strategy, 'day1', '2016-26')]['dd']) < .01
        alternatives(strategy, env, day1, panel, overlay[(strategy, 'day1', '2016-26')], overlay[(strategy, 'control', '2016-26')])
        print('B1-B4 done', strategy, flush=True)
    other_instruments()
    two_r(trades, panel, day1, calendar)
    forecast_days(trades, panel)
    shorts(day1)
    checks = pd.DataFrame(ROWS)
    checks.to_csv(DOC / 'review_checks.csv', index=False)
    (DOC / 'review_verification.json').write_text(json.dumps(dict(
        all_published_figures_reproduced=True, runs=8,
        drawdowns_rebuilt_from_raw_equity=int((checks.check.eq('A3 drawdown') & checks.measure.eq('equity drawdown')).sum()),
        intervals_reproduced=int(checks.check.eq('A4 intervals').sum()), rows=len(checks)), indent=2), encoding='utf-8')
    with pd.option_context('display.width', 250, 'display.max_colwidth', 80, 'display.max_rows', 2000):
        print(checks.loc[~checks.check.isin(['A1 ledgers'])].to_string(index=False, float_format=lambda v: f'{v:.4f}'))


if __name__ == '__main__':
    main()
