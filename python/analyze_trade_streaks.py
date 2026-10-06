"""Q24 saved-ledger streak study; definitions in TRADE_STREAKS_PROTOCOL.md."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_price_levels import PERIODS, sha256
from project_paths import PROJECT_ROOT as ROOT
from verify_location_validation import read_rows

BASE = ROOT / 'Reports/trend_rr_20261002'
TAG = 'trendrr_20261002_f50_baseline'
STUDY = ROOT / 'Reports/trade_streaks_20261007'
PROTOCOL = ROOT / 'docs/TRADE_STREAKS_PROTOCOL.md'
N = 2000
SEED = 20261007


def metrics(net, r):
    net, r = np.asarray(net), np.asarray(r)
    equity = np.r_[0., net.cumsum()]
    dd = float((np.maximum.accumulate(equity) - equity).max())
    losses = -net[net < 0].sum()
    return dict(n=len(net), net=float(net.sum()), sum_r=float(r.sum()),
                mean_r=float(r.mean()) if len(r) else None,
                mean_dollars=float(net.mean()) if len(net) else None,
                win_rate=float((net > 0).mean()) if len(net) else None,
                pf=float(net[net > 0].sum() / losses) if losses else None,
                dd=dd, net_dd=float(net.sum() / dd) if dd else None)


def states(net, sessions, daily=True):
    """Signed preceding CLOSED streak. Caller audits exit <= submission."""
    sign = np.sign(net).astype(int)
    sessions = np.asarray(sessions)
    if not len(sign):
        return np.array([], dtype=int), np.array([], dtype=int)
    boundary = np.r_[True, sign[1:] != sign[:-1]] | (sign == 0)
    if daily:
        boundary |= np.r_[True, sessions[1:] != sessions[:-1]]
    length = np.arange(len(sign)) - np.maximum.accumulate(np.where(boundary, np.arange(len(sign)), 0)) + 1
    after = length * sign
    before = np.r_[0, after[:-1]]
    if daily:
        before[np.r_[True, sessions[1:] != sessions[:-1]]] = 0
    return before, after


def run_summary(net, sessions, daily):
    _, after = states(net, sessions, daily)
    end = np.r_[np.sign(after[1:]) != np.sign(after[:-1]), True]
    if daily:
        end |= np.r_[np.asarray(sessions)[1:] != np.asarray(sessions)[:-1], True]
    terminal = after[end & (after != 0)]
    return dict(runs=len(terminal), longest_win=int(max(0, after.max(initial=0))),
                longest_loss=int(-min(0, after.min(initial=0))),
                win_runs_ge5=int((terminal >= 5).sum()), loss_runs_ge3=int((terminal <= -3).sum()))


def holm(values):
    """Adjusted p-values; missing tests stay missing."""
    out = np.full(len(values), np.nan)
    valid = np.flatnonzero(np.isfinite(values))
    order = valid[np.argsort(np.asarray(values)[valid])]
    if len(order):
        out[order] = np.minimum(1, np.maximum.accumulate(np.asarray(values)[order] * np.arange(len(order), 0, -1)))
    return out


def wilson(wins, total):
    if not total:
        return None, None
    z = 1.959963984540054
    p = wins / total
    center = (p + z*z/(2*total)) / (1 + z*z/total)
    width = z*np.sqrt(p*(1-p)/total + z*z/(4*total*total)) / (1 + z*z/total)
    return float(center-width), float(center+width)


def labels(before):
    result = [('none', before == 0)]
    for sign, name in ((1, 'win'), (-1, 'loss')):
        for k in range(1, 8):
            result.append((f'{name}_exact_{k if k < 7 else "7plus"}',
                           before == sign*k if k < 7 else before*sign >= 7))
        for k in range(2, 7):
            result.append((f'{name}_ge_{k}', before*sign >= k))
    return result


def boot_contrasts(f, masks, rng):
    week = f.submission_time.dt.normalize() - pd.to_timedelta(f.submission_time.dt.dayofweek, unit='D')
    start, end = PERIODS[f.period.iloc[0]]
    first = pd.Timestamp(start) - pd.Timedelta(days=pd.Timestamp(start).dayofweek)
    last = pd.Timestamp(end) - pd.Timedelta(days=1)
    weeks = pd.date_range(first, last, freq='7D')
    code = weeks.get_indexer(week)
    assert (code >= 0).all()
    counts = rng.multinomial(len(weeks), np.full(len(weeks), 1/len(weeks)), size=N)
    values = np.array([np.ones(len(f)), (f.net > 0).astype(float), f.net_r]).T
    total = np.stack([np.bincount(code, weights=v, minlength=len(weeks)) for v in values.T], axis=1)
    totals = counts @ total
    results = []
    for mask in masks:
        group = np.stack([np.bincount(code, weights=v*mask, minlength=len(weeks)) for v in values.T], axis=1)
        a = counts @ group
        b = totals - a
        good = (a[:, 0] > 0) & (b[:, 0] > 0)
        with np.errstate(divide='ignore', invalid='ignore'):
            delta = a[good, 1:] / a[good, :1] - b[good, 1:] / b[good, :1]
        interval = np.quantile(delta, [.025, .975], axis=0) if len(delta) else np.full((2, 2), np.nan)
        results.append(dict(win_diff_lo=interval[0, 0], win_diff_hi=interval[1, 0],
                            r_diff_lo=interval[0, 1], r_diff_hi=interval[1, 1], valid_boot=int(good.sum())))
    return results


def exact_differences(net, r, session, daily):
    before, _ = states(net, session, daily)
    code = np.where(before > 0, np.minimum(before, 7), np.where(before < 0, 7 + np.minimum(-before, 7), 0))
    count = np.bincount(code, minlength=15)[1:]
    win = np.bincount(code, weights=(net > 0), minlength=15)[1:]
    sums = np.bincount(code, weights=r, minlength=15)[1:]
    with np.errstate(divide='ignore', invalid='ignore'):
        wd = win / count - ((net > 0).sum() - win) / (len(net) - count)
        rd = sums / count - (r.sum() - sums) / (len(net) - count)
    return np.stack([wd, rd], axis=1)


def permutations(f, period):
    net, r, session = f.net.to_numpy(), f.net_r.to_numpy(), f.session.to_numpy()
    observed = np.concatenate([exact_differences(net, r, session, daily) for daily in (True, False)])
    rows, runs = [], []
    for mode, keys in [('month', f.submission_time.dt.to_period('M')), ('session', f.session)]:
        rng = np.random.default_rng(SEED + (1 if mode == 'session' else 0))
        groups = list(pd.Series(np.arange(len(f))).groupby(np.asarray(keys)).apply(np.asarray))
        null = np.full((N, 28, 2), np.nan)
        run_null = {scope: [] for scope in ('session', 'global')}
        for j in range(N):
            idx = np.arange(len(f))
            for group in groups:
                idx[group] = rng.permutation(group)
            for k, daily in enumerate((True, False)):
                null[j, k*14:(k+1)*14] = exact_differences(net[idx], r[idx], session, daily)
                run_null['session' if daily else 'global'].append(run_summary(net[idx], session, daily))
        center = np.nanmean(null, axis=0)
        p = np.full((28, 2), np.nan)
        valid = np.isfinite(null).sum(axis=0)
        for i in range(28):
            for m in range(2):
                if np.isfinite(observed[i, m]) and valid[i, m]:
                    vals = null[:, i, m][np.isfinite(null[:, i, m])]
                    p[i, m] = (1 + (np.abs(vals-center[i, m]) >= abs(observed[i, m]-center[i, m])).sum()) / (1+len(vals))
        adjusted = np.stack([holm(p[:, m]) for m in range(2)], axis=1)
        for i in range(28):
            for m, metric in enumerate(('win_rate', 'mean_r')):
                vals = null[:, i, m][np.isfinite(null[:, i, m])]
                lo, hi = np.quantile(vals, [.025, .975]) if len(vals) else (np.nan, np.nan)
                rows.append(dict(period=period, shuffle=mode, scope='session' if i < 14 else 'global',
                                 sign='win' if i % 14 < 7 else 'loss', length=(i % 7)+1,
                                 metric=metric, observed_difference=observed[i, m], null_center=center[i, m],
                                 null_lo=lo, null_hi=hi, p=p[i, m], p_holm=adjusted[i, m], valid=int(valid[i, m])))
        for scope, values in run_null.items():
            actual = run_summary(net, session, scope == 'session')
            for key, value in actual.items():
                vals = np.array([v[key] for v in values])
                lo, hi = np.quantile(vals, [.025, .975])
                runs.append(dict(period=period, shuffle=mode, scope=scope, metric=key,
                                 observed=value, null_mean=vals.mean(), null_lo=lo, null_hi=hi,
                                 p_upper=(1+int((vals >= value).sum()))/(N+1)))
        print(f'{period}: {mode} shuffles complete', flush=True)
    return rows, runs


def stop_mask(net, sessions, sign, threshold):
    """Keep the trigger, skip its whole session remainder, reset next session."""
    sessions = np.asarray(sessions)
    _, after = states(net, sessions, daily=True)
    take = np.ones(len(net), dtype=bool)
    triggers = []
    for session in pd.unique(sessions):
        positions = np.flatnonzero(sessions == session)
        hits = positions[after[positions]*sign >= threshold]
        if len(hits):
            first = int(hits[0])
            take[positions[positions > first]] = False
            triggers.append(first)
    return take, triggers


def load():
    ledger = BASE / f'runband_{TAG}_1.00.csv'
    signals = BASE / f'{TAG}_signals.csv'
    stats_path = BASE / f'runband_{TAG}_1.00_stats.csv'
    ini_path = BASE / f'{TAG}.ini'
    q10_path = ROOT / 'Reports/levels/support_interaction_20261003/trades.csv'
    paths = [ledger, signals, stats_path, ini_path, q10_path, PROTOCOL, Path(__file__)]
    ini = ini_path.read_text(encoding='utf-16').splitlines()
    for needle in ('Model=1', 'Symbol=MNQcontDTBNT20102026_2', 'MaxRedRun=3', 'MinLocation=0',
                   'BullRR=1.0', 'BearRR=1.0', 'AverageNearStopR=0', 'FlattenFallback=true', 'UseEarlyCloseCalendar=true'):
        assert needle in ini, needle
    f = pd.DataFrame(read_rows(ledger))
    stats = read_rows(stats_path)[0]
    f.trade_profit = pd.to_numeric(f.trade_profit)
    assert len(f) == int(stats['trades'])
    assert abs(f.trade_profit.sum() - float(stats['net_profit'])) < 1e-6
    for col in ('signal_time', 'entry_time', 'exit_time'):
        f[col] = pd.to_datetime(f[col], format='%Y.%m.%d %H:%M:%S')
    for col in ('candle_range', 'assigned_rr', 'initial_risk_money', 'base_volume', 'add_volume'):
        f[col] = pd.to_numeric(f[col])
    assert (f.assigned_rr == 1).all() and (f.base_volume == 1).all() and (f.add_volume == 0).all()
    assert np.allclose(f.initial_risk_money, f.candle_range*2)
    s = pd.DataFrame(read_rows(signals))[['signal_time', 'submission_time']]
    for col in s:
        s[col] = pd.to_datetime(s[col], format='%Y.%m.%d %H:%M:%S')
    assert s.signal_time.is_unique and f.signal_time.is_unique
    f = f.merge(s, on='signal_time', validate='one_to_one').sort_values('entry_time').reset_index(drop=True)
    assert len(f) == int(stats['trades']), 'Ledger trade missing from signal log'
    assert (f.signal_time + pd.Timedelta(minutes=30) <= f.submission_time).all()
    assert (f.submission_time <= f.entry_time).all() and (f.entry_time <= f.exit_time).all()
    assert (f.exit_time.shift() <= f.submission_time).iloc[1:].all(), 'Previous result unavailable at submission'
    assert (f.entry_time.dt.normalize() == f.exit_time.dt.normalize()).all()
    assert (f.submission_time.dt.normalize() == f.entry_time.dt.normalize()).all()
    assert (f.initial_risk_money > 0).all()
    f['net'] = f.trade_profit - 1.05
    f['net_r'] = f.net / f.initial_risk_money
    f['session'] = f.submission_time.dt.normalize()
    f['year'] = f.submission_time.dt.year
    f['period'] = None
    for period, (start, end) in PERIODS.items():
        f.loc[f.submission_time.between(start, end, inclusive='left'), 'period'] = period
    f = f[f.period.notna()].copy().reset_index(drop=True)
    q = pd.read_csv(q10_path, parse_dates=['signal_time']).drop_duplicates('signal_time')
    audit = f.merge(q[['signal_time', 'net', 'net_r']], on='signal_time', suffixes=('', '_q10'), validate='one_to_one')
    assert len(audit) == len(f) == len(q) == 14968
    assert np.allclose(audit.net, audit.net_q10) and np.allclose(audit.net_r, audit.net_r_q10)
    assert np.isfinite(f[['net', 'net_r']]).all().all()
    return f, paths, dict(full_ledger_trades=int(stats['trades']), selected_trades=len(f), q10_identical=True,
                         previous_exit_known_at_submission=True, no_overlap=True, no_cross_session=True)


def main():
    f, paths, audit = load()
    print('PASS: MT5 stats, Q10 equality, costs, risks and information timing', flush=True)
    STUDY.mkdir(parents=True, exist_ok=True)
    conditional, yearly, stops, tails, stop_yearly, permutation, runs = [], [], [], [], [], [], []
    for period in PERIODS:
        x = f[f.period == period].reset_index(drop=True).copy()
        net, r, session = x.net.to_numpy(), x.net_r.to_numpy(), x.session.to_numpy()
        base = metrics(net, r)
        for scope in ('session', 'global'):
            before, after = states(net, session, scope == 'session')
            x[f'{scope}_before'] = before
            x[f'{scope}_after'] = after
            named = labels(before)
            intervals = boot_contrasts(x, [mask for _, mask in named], np.random.default_rng(SEED))
            for (name, mask), interval in zip(named, intervals):
                a, b = metrics(net[mask], r[mask]), metrics(net[~mask], r[~mask])
                lo, hi = wilson(int((net[mask] > 0).sum()), int(mask.sum()))
                conditional.append(dict(period=period, scope=scope, state=name, **a,
                                        complement_n=b['n'], complement_mean_r=b['mean_r'], complement_win_rate=b['win_rate'],
                                        r_difference=a['mean_r']-b['mean_r'] if a['n'] and b['n'] else None,
                                        win_difference=a['win_rate']-b['win_rate'] if a['n'] and b['n'] else None,
                                        win_wilson_lo=lo, win_wilson_hi=hi, **interval))
                for year in sorted(x.year.unique()):
                    ym = x.year.to_numpy() == year
                    ay, by = metrics(net[mask & ym], r[mask & ym]), metrics(net[~mask & ym], r[~mask & ym])
                    yearly.append(dict(period=period, scope=scope, state=name, year=int(year), **ay,
                                       complement_mean_r=by['mean_r'], r_difference=ay['mean_r']-by['mean_r'] if ay['n'] and by['n'] else None))
        f.loc[f.period == period, ['session_before', 'session_after', 'global_before', 'global_after']] = x[
            ['session_before', 'session_after', 'global_before', 'global_after']].to_numpy()
        stops.append(dict(period=period, rule='baseline', **base, removed=0, affected_sessions=0))
        for sign, name in ((1, 'win'), (-1, 'loss')):
            for threshold in range(2, 7):
                take, triggers = stop_mask(net, session, sign, threshold)
                rule = f'stop_{name}_{threshold}'
                m = metrics(net[take], r[take])
                tail = metrics(net[~take], r[~take])
                stops.append(dict(period=period, rule=rule, **m, removed=int((~take).sum()),
                                  affected_sessions=len(triggers), net_change=m['net']-base['net'],
                                  net_retained=m['net']/base['net'], dd_ratio=m['dd']/base['dd'],
                                  net_dd_ratio=m['net_dd']/base['net_dd'] if m['net_dd'] is not None else None,
                                  removed_net=tail['net'], removed_mean_r=tail['mean_r']))
                for trigger in triggers:
                    day = np.flatnonzero(session == session[trigger])
                    remainder = day[day > trigger]
                    cumulative = net[day[day <= trigger]].sum()
                    rest = net[remainder].sum()
                    tails.append(dict(period=period, rule=rule, session=str(session[trigger]), trigger_index=trigger,
                                      trigger_exit=str(x.exit_time.iloc[trigger]), session_profit_at_trigger=float(cumulative),
                                      subsequent_trades=len(remainder), remainder_net=float(rest),
                                      remainder_r=float(r[remainder].sum()), loses_remainder=bool(rest < 0),
                                      positive_at_trigger=bool(cumulative > 0),
                                      gives_back_half=bool(cumulative > 0 and rest < -cumulative/2)))
                for year in sorted(x.year.unique()):
                    ym = x.year.to_numpy() == year
                    a, b = metrics(net[take & ym], r[take & ym]), metrics(net[ym], r[ym])
                    stop_yearly.append(dict(period=period, rule=rule, year=int(year), **a,
                                            baseline_net=b['net'], net_change=a['net']-b['net']))
        pp, rr = permutations(x, period)
        permutation.extend(pp)
        runs.extend(rr)
    f.to_csv(STUDY / 'trades.csv', index=False)
    for name, values in dict(conditional=conditional, yearly=yearly, stops=stops, session_tails=tails,
                             stop_yearly=stop_yearly, permutation=permutation, runs=runs).items():
        pd.DataFrame(values).to_csv(STUDY / f'{name}.csv', index=False)
    (STUDY / 'audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    outputs = [dict(path=str(p), sha256=sha256(p)) for p in sorted(STUDY.iterdir()) if p.name != 'provenance.json']
    (STUDY / 'provenance.json').write_text(json.dumps(dict(seed=SEED, resamples=N,
        files=[dict(path=str(p), sha256=sha256(p)) for p in paths], outputs=outputs), indent=2), encoding='utf-8')
    print(pd.DataFrame(stops)[['period', 'rule', 'n', 'net', 'pf', 'dd', 'net_change', 'net_dd_ratio']].to_string(index=False))
    print('Saved', STUDY, flush=True)


if __name__ == '__main__':
    main()
