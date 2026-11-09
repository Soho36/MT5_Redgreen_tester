"""Short one MNQ in the final half-hour of weak NQ sessions, with a matched control.

Run with the project venv. See docs/baseline/mnq-weak-close/PROTOCOL.md.
"""
from datetime import date, timedelta
import json

from dateutil.easter import easter
import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT
from rtl_weekly_engine import MINUTES, ROLLS
from verify_rtl_failed_breakout_short import CACHE, digest, load_quote_index

RUN = ROOT / 'Reports/mnq_weak_close_20261106'
PROTOCOL = ROOT / 'docs/baseline/mnq-weak-close/PROTOCOL.md'
PROTOCOL_SHA = 'c8255dcbb5d92929f2fb57acb24ae97a28905f541c2254049ce50c9e396cd365'
START, END = date(2016, 1, 1), date(2026, 9, 30)
PERIODS = {'2016-19': ('2016-01-01', '2019-12-31'),
           '2020-26': ('2020-01-01', '2026-09-30'),
           '2016-26': ('2016-01-01', '2026-09-30'),
           'post-paper': ('2020-05-04', '2026-09-30')}
FILLS = {'next_quote': 'entry_quote', 'minute_open': 'entry_1531'}
ONE_DAY = timedelta(days=1)
FEE, POINT_VALUE = 1.05, 2.


def weekday_in_month(year, month, weekday, n):
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + (n - 1) * 7)


def observed(d):
    return d - ONE_DAY if d.weekday() == 5 else d + ONE_DAY if d.weekday() == 6 else d


def cash_schedule():
    """US stock exchange sessions, 2015–2026, sufficient to form the first prior close."""
    schedule = {}
    for year in range(2015, END.year + 1):
        new_year = date(year, 1, 1)
        thanks = weekday_in_month(year, 11, 3, 4)
        may_end = date(year, 5, 31)
        holidays = {new_year + ONE_DAY if new_year.weekday() == 6 else new_year,
                    weekday_in_month(year, 1, 0, 3), weekday_in_month(year, 2, 0, 3),
                    easter(year) - 2 * ONE_DAY, may_end - timedelta(days=may_end.weekday()),
                    observed(date(year, 7, 4)), weekday_in_month(year, 9, 0, 1), thanks,
                    observed(date(year, 12, 25)), date(2018, 12, 5), date(2025, 1, 9)}
        if year >= 2022:
            holidays.add(observed(date(year, 6, 19)))
        half_days = {date(year, 7, 3), date(year, 12, 24), thanks + ONE_DAY}
        d = new_year
        while d.year == year and d <= END:
            if d.weekday() < 5 and d not in holidays:
                schedule[d] = 13 if d in half_days else 16
            d += ONE_DAY
    return schedule


def build_sessions(quotes, rolls):
    schedule = cash_schedule()
    roll_dates = rolls.date.to_numpy(dtype='datetime64[D]')
    contract_ids = rolls.instrument_id.to_numpy()
    clock = quotes.minute_epoch
    def contract(d):
        pos = np.searchsorted(roll_dates, np.datetime64(d), side='right') - 1
        if pos < 0:
            raise ValueError(f'Missing roll record for {d}')
        return int(contract_ids[pos])

    def locate(d, minute_et):
        # The source strips Chicago tz/DST and adds 8h. US Eastern is Chicago+1h.
        epoch = (d - date(1970, 1, 1)).days * 86400 + (minute_et + 7 * 60) * 60
        i = int(np.searchsorted(clock, epoch))
        return i if i < len(clock) and clock[i] == epoch else None

    rows = []
    dates = list(schedule)
    for prev, d in zip(dates, dates[1:]):
        if d < START:
            continue
        prior_hour = schedule[prev]
        prior_id, current_id = contract(prev), contract(d)
        row = dict(date=d.isoformat(), prior_date=prev.isoformat(),
                   prior_close_time_et=f'{prior_hour-1:02d}:59', close_hour_et=schedule[d],
                   contract_id=current_id, prior_contract_id=prior_id)
        rows.append(row)
        if schedule[d] != 16:
            row['reason'] = 'early_close'
            continue
        if prior_id != current_id:
            row['reason'] = 'contract_change'
            continue
        points = dict(prior_close=locate(prev, prior_hour * 60 - 1),
                      signal=locate(d, 15 * 60 + 30), entry_1531=locate(d, 15 * 60 + 31),
                      exit=locate(d, 16 * 60))
        missing = [name for name, i in points.items() if i is None]
        if missing:
            row['reason'] = 'missing_' + '_'.join(missing)
            continue
        i = points['signal']
        sequence = iter(quotes.quotes(i, points['entry_1531'] + 1))
        decision_time, signal = next(sequence)
        entry_time, fill = next(sequence)
        assert decision_time < entry_time and signal == quotes.b['o'][i]
        prior = float(quotes.b['c'][points['prior_close']])
        row.update(reason='eligible', prior_close=prior, signal_price=signal,
                   decision_second=decision_time - int(clock[i]), weak=signal < prior,
                   entry_quote=fill, entry_quote_second=entry_time - int(clock[i]),
                   entry_1531=float(quotes.b['o'][points['entry_1531']]),
                   exit_price=float(quotes.b['o'][points['exit']]))
        for fill_name, price in FILLS.items():
            row[fill_name + '_net_dollars'] = (row[price] - row['exit_price']) * POINT_VALUE - FEE
    return pd.DataFrame(rows)


def measure(net):
    values = net.to_numpy()
    equity = np.r_[0., values.cumsum()]
    loss = -values[values < 0].sum()
    pnl = values.sum()
    return dict(trades=len(values), gross_dollars=pnl + FEE * len(values), net_dollars=pnl,
                avg_net_dollars=pnl / len(values) if len(values) else np.nan,
                profit_factor=values[values > 0].sum() / loss if loss else np.nan,
                win_pct=100 * (values > 0).mean() if len(values) else np.nan,
                daily_close_dd=(np.maximum.accumulate(equity) - equity).max(),
                stress1_net_dollars=pnl - len(values), stress2_net_dollars=pnl - 2 * len(values))


def summarize(part):
    for fill in FILLS:
        for variant, trades in [('weak', part[part.weak]), ('all', part), ('nonweak', part[~part.weak])]:
            yield dict(fill=fill, variant=variant, **measure(trades[fill + '_net_dollars']))


def bootstrap(part, fill):
    pnl = part[fill + '_net_dollars']
    weeks = pd.to_datetime(part.date).dt.to_period('W-SUN')
    weekly = pd.DataFrame(dict(all_net=pnl, n=1, weak_net=pnl.where(part.weak, 0.),
                               nw=part.weak.astype(int))).groupby(weeks).sum()
    weekly = weekly.reindex(pd.period_range(weeks.min(), weeks.max(), freq='W-SUN'), fill_value=0)
    rng = np.random.default_rng(20261106)
    starts = rng.integers(0, len(weekly), size=(5000, (len(weekly) + 3) // 4))
    idx = ((starts[:, :, None] + np.arange(4)) % len(weekly)).reshape(5000, -1)[:, :len(weekly)]
    weak_mean, difference = [], []
    for batch in np.array_split(idx, 20):
        total, n, weak, nw = weekly.to_numpy()[batch].sum(axis=1).T
        weak_mean.extend(weak / nw)
        difference.extend(weak / nw - total / n)
    return dict(weak_mean_lo=np.quantile(weak_mean, .025), weak_mean_hi=np.quantile(weak_mean, .975),
                weak_minus_all_mean_lo=np.quantile(difference, .025), weak_minus_all_mean_hi=np.quantile(difference, .975))


def main():
    assert digest(PROTOCOL).lower() == PROTOCOL_SHA
    q = load_quote_index()
    sessions = build_sessions(q, pd.read_csv(ROLLS))
    eligible = sessions.loc[sessions.reason.eq('eligible')].copy()
    eligible['weak'] = eligible.weak.astype(bool)
    summary, annual, intervals = [], [], []
    for period, (lo, hi) in PERIODS.items():
        part = eligible.loc[eligible.date.between(lo, hi)]
        summary.extend(dict(period=period, **s) for s in summarize(part))
        intervals.extend(dict(period=period, fill=fill, **bootstrap(part, fill)) for fill in FILLS)
    for year, part in eligible.groupby(eligible.date.str[:4]):
        annual.extend(dict(year=year, **s) for s in summarize(part))

    RUN.mkdir(exist_ok=True, parents=True)
    dfs = {'sessions.csv': sessions, 'summaries.csv': pd.DataFrame(summary),
           'annual.csv': pd.DataFrame(annual), 'intervals.csv': pd.DataFrame(intervals)}
    for name, frame in dfs.items():
        frame.to_csv(RUN / name, index=False, float_format='%.12g')
    provenance = dict(inputs={str(p): digest(p) for p in [PROTOCOL, MINUTES, ROLLS, CACHE,
                      ROOT / 'python/verify_rtl_failed_breakout_short.py', ROOT / 'python/rtl_weekly_engine.py',
                      ROOT / 'python/analyze_mnq_weak_close.py']},
                      cost=FEE, point_value=POINT_VALUE, bootstrap_draws=5000, block_weeks=4,
                      exclusions=sessions.reason.value_counts().to_dict(),
                      hashes={name: digest(RUN / name) for name in dfs})
    (RUN / 'manifest.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(sessions.reason.value_counts().to_string())
    print(dfs['summaries.csv'].round(3).to_string(index=False))
    print(dfs['intervals.csv'].round(3).to_string(index=False))


if __name__ == '__main__':
    main()

