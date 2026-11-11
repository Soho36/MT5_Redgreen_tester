"""Review checks for the RTL news-day study: what carries the 2020-26 result?

Written on 2026-11-10, after the study's results were known. These are
after-the-fact diagnostics that describe the committed result; they are not a
new test. Nothing here changes the study's own files or its evidence.

Reads
  Reports/rtl_news_days_20261110/          control trades, session envelopes, summary, comparisons
  Reports/rtl_gg_exclude16_20261101/       trade ledgers of the filtered RTL variants
  Reports/buy_hold_20261108/session_flat/  one long per session, flat at the close
  Reports/rtl_vwap_cross_20261027/calendars.csv     NQ session calendar used by the study
  data/calendars/us_major_news_2010_2026.csv        release dates (the study's calendar)
  data/calendars/us_major_news_times_2010_2026.csv  release times (from the 30-minute follow-up)
Writes
  docs/baseline/rtl-news-days/review_checks.csv     every number printed, in long format

Run:  .\\venv\\Scripts\\python.exe python\\review_rtl_news_days.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / 'Reports/rtl_news_days_20261110'
VARIANTS = ROOT / 'Reports/rtl_gg_exclude16_20261101'
HOLD = ROOT / 'Reports/buy_hold_20261108/session_flat/verified_trades.csv'
SESSIONS = ROOT / 'Reports/rtl_vwap_cross_20261027/calendars.csv'
NEWS_DATES = ROOT / 'data/calendars/us_major_news_2010_2026.csv'
NEWS_TIMES = ROOT / 'data/calendars/us_major_news_times_2010_2026.csv'
DOC = ROOT / 'docs/baseline/rtl-news-days'

END = '2026-10-01'  # the study publishes results up to 30 September 2026
ERAS = {'2016-19': ('2016-01-01', '2020-01-01'), '2020-26': ('2020-01-01', END)}
EARLY = {'2010-15': ('2010-01-01', '2016-01-01')}  # the study's secondary, loss-making period
SEED = 20261110  # the study's seed, so its random-day ranks reproduce exactly
DRAWS = 10_000
LEAVE_OUT = (1, 2, 3, 5, 10)
VARIANT_LABELS = {
    'rtl_base_all': 'Original RTL',
    'rtl_base_skip': 'RTL + exclude16-17',
    'rtl_vwap_all': 'RTL + VWAP',
    'rtl_vwap_skip': 'RTL + VWAP + exclude16-17',
}

ROWS: list[dict] = []


def record(check, period, row, measure, value):
    ROWS.append(dict(check=check, period=period, row=str(row), measure=measure, value=float(value)))


def require(condition, message):
    """Stop with a clear message. Unlike assert, this still runs under python -O."""
    if not condition:
        raise SystemExit('Review check failed: ' + message)


def show(title, frame, decimals=0):
    print('\n' + title)
    print(frame.round(decimals).to_string())


def plain(value):
    """Whole numbers without a trailing .0, everything else to one decimal."""
    return f'{value:,.0f}' if float(value).is_integer() else f'{value:,.1f}'


def in_era(values, era, eras=None):
    start, end = (eras or ERAS)[era]
    return (values >= start) & (values < end)


def load():
    sessions = pd.read_csv(SESSIONS, parse_dates=['session'])
    sessions = pd.DatetimeIndex(sessions.loc[sessions.instrument.eq('NQ'), 'session']).sort_values()
    sessions = sessions[sessions < END]
    news = pd.DatetimeIndex(pd.read_csv(NEWS_DATES, parse_dates=['date']).date.unique())
    trades = pd.read_csv(RUN / 'news_20261110_control_trades.csv',
                         parse_dates=['entry_time', 'exit_time', 'session'], low_memory=False)
    trades = trades.loc[trades.session < END].copy()
    trades['news'] = trades.session.isin(news)
    envelopes = pd.read_csv(RUN / 'baseline_session_envelopes.csv', parse_dates=['session']).set_index('session')
    envelopes = envelopes.reindex(sessions, fill_value=0.0)
    return sessions, news, trades, envelopes


def max_drawdown(env, keep):
    """Largest peak-to-trough fall in equity when only the kept sessions are traded.

    Each session is stored as its net result, the lowest and highest point it
    reached, and the deepest fall inside it. That is enough to rebuild the exact
    intraday drawdown of any selection of sessions. `keep` holds one row of
    True/False per scenario; one drawdown is returned per row.
    """
    keep = np.atleast_2d(keep)
    net = keep * env.net.to_numpy()
    start = np.cumsum(net, axis=1) - net  # equity when each session opens
    high = start + keep * env.high.to_numpy()
    low = start + keep * env.low.to_numpy()
    peak_before = np.maximum.accumulate(np.c_[np.zeros(len(keep)), high], axis=1)[:, :-1]
    return np.maximum(peak_before - low, keep * env.dd.to_numpy()).max(axis=1)


def daily_close_drawdown(daily_net):
    equity = np.r_[0.0, np.cumsum(daily_net)]
    return float((np.maximum.accumulate(equity) - equity).max())


def reconcile_with_study(env, news):
    """My own drawdown code must give the study's published net and equity DD."""
    summary = pd.read_csv(RUN / 'summary.csv').set_index(['policy', 'period'])
    for era in ERAS:
        e = env.loc[in_era(env.index, era)]
        is_news = e.index.isin(news)
        for policy, keep in (('control', np.ones(len(e), bool)), ('skip_all', ~is_news)):
            net, dd = e.net[keep].sum(), max_drawdown(e, keep)[0]
            want = summary.loc[(policy, era)]
            require(abs(net - want.net_dollars) < 0.01 and abs(dd - want.equity_dd) < 0.01,
                    f'{policy} {era}: {net:.2f}/{dd:.2f} differs from summary.csv')
    print('Reconciled: net and equity DD match the study for control and skip-all in both eras.')


def concentration(env, news):
    """How much of the result sits in the few worst news sessions?"""
    for era in ERAS:
        e = env.loc[in_era(env.index, era)]
        is_news = e.index.isin(news)
        news_net = e.net[is_news].sort_values()  # worst first
        other_net = e.net[~is_news]
        facts = {'news sessions': len(news_net), 'news total': news_net.sum(),
                 'news median': news_net.median(), 'other median': other_net.median(),
                 'news sessions up': (news_net > 0).sum(), 'news sessions down': (news_net < 0).sum()}
        for measure, value in facts.items():
            record('concentration', era, 'news sessions', measure, value)
        print(f'\n{era}: ' + ', '.join(f'{k} {plain(v)}' for k, v in facts.items()))

        scenarios = {'Original RTL': np.ones(len(e), bool), 'Skip every news day': ~is_news}
        for k in LEAVE_OUT:
            worst = e.index.isin(news_net.index[:k])
            those = 'the worst news day' if k == 1 else f'the {k} worst news days'
            scenarios[f'Skip only {those}'] = ~worst
            scenarios[f'Skip every news day except {those}'] = ~(is_news & ~worst)
        table = pd.DataFrame.from_dict({name: dict(net=e.net[keep].sum(), equity_dd=max_drawdown(e, keep)[0])
                                        for name, keep in scenarios.items()}, orient='index')
        table['net_over_dd'] = table.net / table.equity_dd
        for name, row in table.iterrows():
            for measure, value in row.items():
                record('concentration', era, name, measure, value)
        show(f'{era}: leaving the worst news days in or out', table, 2)
        for date, value in news_net.head(5).items():
            record('worst news sessions', era, date.date(), 'rtl_net', value)
        print('  five worst news sessions: ' + ', '.join(f'{d.date()} {v:,.0f}' for d, v in news_net.head(5).items())
              + f' = {news_net.head(5).sum():,.0f}; all the others {news_net.iloc[5:].sum():,.0f}')


def drawdown_episodes(env, news, count=4):
    """Which news sessions sit inside the deepest drawdowns of the original RTL, 2020-26?

    A drawdown runs from the session that set an equity high down to the lowest
    point reached before a higher high. Falls are measured to each session's
    low, as in max_drawdown.
    """
    e = env.loc[in_era(env.index, '2020-26')]
    is_news = e.index.isin(news)
    everything = np.ones(len(e), bool)
    start = (e.net.cumsum() - e.net).to_numpy()
    high, low = start + e.high.to_numpy(), start + e.low.to_numpy()
    peak_before = np.maximum.accumulate(np.r_[0.0, high])[:-1]
    sets_high = high > peak_before
    last_high = np.maximum.accumulate(np.where(sets_high, np.arange(len(e)), -1))
    measured_from = np.r_[-1, last_high[:-1]]  # the session whose high each fall is measured from
    fall = pd.Series(peak_before - low)
    troughs = fall.groupby(measured_from).idxmax()  # the lowest session under each high
    deepest = fall[troughs].sort_values(ascending=False).head(count)
    require(abs(deepest.iloc[0] - max_drawdown(e, everything)[0]) < 0.01,
            'the deepest episode is not the published equity DD')

    inside_any = np.zeros(len(e), bool)
    for trough, depth in deepest.items():
        peak = max(measured_from[trough], 0)
        window = (np.arange(len(e)) > peak) & (np.arange(len(e)) <= trough)
        on_news = e.net[window & is_news].sort_values()
        inside_any |= window & is_news
        label = f'{e.index[peak].date()} to {e.index[trough].date()}'
        facts = {'depth': depth, 'sessions': window.sum(), 'news sessions': len(on_news), 'news net': on_news.sum()}
        for measure, value in facts.items():
            record('drawdown episodes', '2020-26', label, measure, value)
        for date, value in on_news.head(3).items():
            record('drawdown episodes', '2020-26', f'{label}: {date.date()}', 'rtl_net', value)
        print(f'  {label}: depth {depth:,.0f}, {window.sum()} sessions, {len(on_news)} news sessions with net '
              f'{on_news.sum():,.0f} (' + ', '.join(f'{d.date()} {v:,.0f}' for d, v in on_news.head(3).items()) + ')')

    scenarios = {f'Skip only the {inside_any.sum()} news days inside these drawdowns': ~inside_any,
                 f'Skip only the other {(is_news & ~inside_any).sum()} news days': ~(is_news & ~inside_any)}
    for name, keep in scenarios.items():
        net, dd = e.net[keep].sum(), max_drawdown(e, keep)[0]
        record('drawdown episodes', '2020-26', name, 'net', net)
        record('drawdown episodes', '2020-26', name, 'equity_dd', dd)
        print(f'  {name}: net {net:,.0f}, equity DD {dd:,.0f}')


def mean_r_gap_interval(part):
    """95% range for (mean net R on news days - mean net R on other days), resampling whole weeks."""
    weekly = (part.assign(week=part.session.dt.to_period('W-SUN'), count=1.0)
              .groupby(['week', 'news'])[['net_r', 'count']].sum().unstack('news').fillna(0.0))
    r_news, r_other = weekly[('net_r', True)].to_numpy(), weekly[('net_r', False)].to_numpy()
    n_news, n_other = weekly[('count', True)].to_numpy(), weekly[('count', False)].to_numpy()
    pick = np.random.default_rng(SEED).integers(len(weekly), size=(DRAWS, len(weekly)))
    gap = r_news[pick].sum(axis=1) / n_news[pick].sum(axis=1) - r_other[pick].sum(axis=1) / n_other[pick].sum(axis=1)
    return np.quantile(gap, [0.025, 0.975])


def per_unit_of_risk(trades):
    """Were news-day trades worse per unit of risk, or only in dollars?"""
    rows = {}
    for era in {**EARLY, **ERAS}:
        part = trades.loc[in_era(trades.session, era, {**EARLY, **ERAS})]
        for flag, label in ((True, 'news days'), (False, 'other days')):
            g = part.loc[part.news.eq(flag)]
            rows[(era, label)] = dict(trades=len(g), net=g.net_dollars.sum(), avg_net=g.net_dollars.mean(),
                                      mean_net_r=g.net_r.mean(), mean_risk=g.initial_risk_dollars.mean())
        low, high = mean_r_gap_interval(part)
        gap = rows[(era, 'news days')]['mean_net_r'] - rows[(era, 'other days')]['mean_net_r']
        for measure, value in (('mean_net_r_gap', gap), ('gap_95_low', low), ('gap_95_high', high)):
            record('per unit of risk', era, 'news minus other', measure, value)
        print(f'  {era}: mean net R, news minus other days {gap:+.4f} (95% range {low:+.4f} to {high:+.4f})')
    table = pd.DataFrame.from_dict(rows, orient='index')
    for (era, label), row in table.iterrows():
        for measure, value in row.items():
            record('per unit of risk', era, label, measure, value)
    show('News-day trades against the rest', table, 4)

    part = trades.loc[in_era(trades.session, '2020-26')]
    cutoff = part.initial_risk_dollars.quantile(0.99)
    big = part.loc[part.initial_risk_dollars > cutoff]
    for flag, label in ((True, 'news days'), (False, 'other days')):
        g = big.loc[big.news.eq(flag)]
        for measure, value in (('trades', len(g)), ('net', g.net_dollars.sum()), ('mean_net_r', g.net_r.mean())):
            record('largest 1% by risk', '2020-26', label, measure, value)
        print(f'  2020-26, largest 1% of trades by dollar risk (above ${cutoff:,.2f}), {label}: '
              f'{len(g)} trades, net {g.net_dollars.sum():,.0f}, mean net R {g.net_r.mean():+.3f}')


def release_split(trades):
    """Was the money lost before the number came out, or after?"""
    times = pd.read_csv(NEWS_TIMES, parse_dates=['date', 'research_time'])
    first_release = times.groupby('date').research_time.min()
    on_news = trades.loc[trades.news].copy()
    on_news['release'] = on_news.session.map(first_release)
    require(on_news.release.notna().all(), 'a news session has no release time')
    on_news['phase'] = np.select(
        [on_news.exit_time <= on_news.release, on_news.entry_time >= on_news.release],
        ['closed before the release', 'entered after the release'], 'open across the release')
    for era in ERAS:
        part = on_news.loc[in_era(on_news.session, era)]
        table = part.groupby('phase').agg(trades=('net_r', 'size'), net=('net_dollars', 'sum'),
                                          mean_net_r=('net_r', 'mean'), mean_risk=('initial_risk_dollars', 'mean'))
        for phase, row in table.iterrows():
            for measure, value in row.items():
                record('release split', era, phase, measure, value)
        show(f'{era}: news-day trades by when they ran', table, 3)


def market_control(env, news, sessions):
    """What did a plain long do on the same sessions?"""
    hold = pd.read_csv(HOLD)
    hold['session'] = pd.to_datetime(hold.session, format='%Y.%m.%d')
    hold = hold.set_index('session').net.reindex(sessions, fill_value=0.0)
    rtl = env.net
    is_news = sessions.isin(news)
    years = {}
    for year in range(2016, 2027):
        mask = (sessions.year == year) & is_news
        years[year] = dict(news_sessions=mask.sum(), rtl_on_news_days=rtl[mask].sum(), plain_long_on_news_days=hold[mask].sum())
    table = pd.DataFrame.from_dict(years, orient='index')
    for year, row in table.iterrows():
        for measure, value in row.items():
            record('market control', str(year), 'news days', measure, value)
    show('News-day totals by year: RTL against one plain long per session', table)
    for era in ERAS:
        mask = in_era(sessions, era)
        facts = {'rtl_news': rtl[mask & is_news].mean(), 'plain_long_news': hold[mask & is_news].mean(),
                 'rtl_other': rtl[mask & ~is_news].mean(), 'plain_long_other': hold[mask & ~is_news].mean()}
        for measure, value in facts.items():
            record('market control', era, 'mean per session', measure, value)
        print(f'  {era} mean per session: ' + ', '.join(f'{k} {v:,.1f}' for k, v in facts.items()))
    recent = in_era(sessions, '2020-26') & is_news
    for date in rtl[recent].sort_values().index[:5]:
        record('worst news sessions', '2020-26', date.date(), 'plain_long_net', hold[date])
        print(f'  {date.date()}: RTL {rtl[date]:,.0f}, plain long {hold[date]:,.0f}')


def filtered_variants(news, sessions):
    """Does skipping news days still help once the other filters are on?

    Whole sessions are subtracted from each saved ledger. The study proved this
    exact for the original RTL only, so the filtered rows are an estimate, and
    drawdown here is at daily closes, not intraday.
    """
    rows = {}
    for era in ERAS:
        days = sessions[in_era(sessions, era)]
        is_news = days.isin(news)
        for key, label in VARIANT_LABELS.items():
            ledger = pd.read_csv(VARIANTS / f'ex16_20261101_{key}_trades.csv', parse_dates=['session'], low_memory=False)
            daily = ledger.groupby('session').net_dollars.sum().reindex(days, fill_value=0.0).to_numpy()
            rows[(era, label)] = dict(
                news_days_net=daily[is_news].sum(), net=daily.sum(), net_if_skipped=daily[~is_news].sum(),
                close_dd=daily_close_drawdown(daily), close_dd_if_skipped=daily_close_drawdown(np.where(is_news, 0.0, daily)))
    table = pd.DataFrame.from_dict(rows, orient='index')
    for (era, label), row in table.iterrows():
        for measure, value in row.items():
            record('filtered variants', era, label, measure, value)
    show('Skipping news days on each RTL variant (ledger subtraction, daily-close DD)', table)


def worst_sessions(env, news):
    """Are news days over-represented among the worst sessions?"""
    for era in ERAS:
        e = env.loc[in_era(env.index, era)]
        share = e.index.isin(news).mean()
        ranked = e.net.sort_values()
        for count in (10, 50):
            facts = {'news among worst': ranked.index[:count].isin(news).sum(),
                     'news among best': ranked.index[-count:].isin(news).sum(), 'expected by chance': count * share}
            for measure, value in facts.items():
                record('worst sessions', era, f'{count} sessions', measure, value)
            print(f'  {era}, {count} sessions: ' + ', '.join(f'{k} {plain(v)}' for k, v in facts.items()))


def random_days(env, trades, news):
    """Rank the news days against random days, as the study did and also matched on day size."""
    comparisons = pd.read_csv(RUN / 'comparisons.csv').set_index(['period', 'policy'])
    session_risk = trades.groupby('session').initial_risk_dollars.sum().reindex(env.index, fill_value=0.0)
    for era in ERAS:
        e = env.loc[in_era(env.index, era)]
        removed = e.index.isin(news)
        net_seen = e.net[~removed].sum()
        dd_seen = max_drawdown(e, ~removed)[0]
        risk = session_risk.reindex(e.index)
        size_third = risk.groupby(risk.index.year).transform(
            lambda s: pd.qcut(s.rank(method='first'), 3, labels=False)).to_numpy()
        year_weekday = e.index.year * 10 + e.index.dayofweek
        designs = {'same year and weekday (the study)': np.asarray(year_weekday),
                   'same year, weekday and day size': np.asarray(year_weekday) * 10 + size_third}
        for name, labels in designs.items():
            rng = np.random.default_rng(SEED)
            groups = [(np.flatnonzero(labels == k), int(removed[labels == k].sum())) for k in np.unique(labels)]
            nets, dds = [], []
            for start in range(0, DRAWS, 250):
                n = min(250, DRAWS - start)
                keep = np.ones((n, len(e)), bool)
                for members, count in groups:
                    if count:
                        chosen = np.argsort(rng.random((n, len(members))), axis=1)[:, :count]
                        keep[np.arange(n)[:, None], members[chosen]] = False
                nets.append((keep * e.net.to_numpy()).sum(axis=1))
                dds.append(max_drawdown(e, keep))
            nets, dds = np.concatenate(nets), np.concatenate(dds)
            facts = {'net beats %': (nets <= net_seen).mean() * 100, 'dd no worse than %': (dds >= dd_seen).mean() * 100,
                     'net/dd beats %': (nets / dds <= net_seen / dd_seen).mean() * 100,
                     'random median net': np.median(nets), 'random median dd': np.median(dds)}
            for measure, value in facts.items():
                record('random days', era, name, measure, value)
            print(f'  {era}, {name}: ' + ', '.join(f'{k} {v:,.2f}' for k, v in facts.items()))
            if name.endswith('(the study)'):
                want = comparisons.loc[(era, 'skip_all')]
                require(abs(facts['net beats %'] - want.net_percentile) < 1e-6
                        and abs(facts['dd no worse than %'] - want.dd_better_percent) < 1e-6
                        and abs(facts['net/dd beats %'] - want.net_dd_percentile) < 1e-6,
                        f'{era}: random-day ranks differ from comparisons.csv')


def main():
    sessions, news, trades, env = load()
    reconcile_with_study(env, news)
    print('\n1. Concentration')
    concentration(env, news)
    print('\n2. Drawdown episodes of the original RTL')
    drawdown_episodes(env, news)
    print('\n3. Per unit of risk')
    per_unit_of_risk(trades)
    print('\n4. Before or after the release')
    release_split(trades)
    print('\n5. The market on the same days')
    market_control(env, news, sessions)
    print('\n6. Filtered variants')
    filtered_variants(news, sessions)
    print('\n7. Worst sessions')
    worst_sessions(env, news)
    print('\n8. Random days (10,000 draws each; the study\'s design must reproduce its published ranks)')
    random_days(env, trades, news)
    pd.DataFrame(ROWS).to_csv(DOC / 'review_checks.csv', index=False, float_format='%.4f')
    print(f'\nSaved {len(ROWS)} numbers to {DOC / "review_checks.csv"}')


if __name__ == '__main__':
    main()
