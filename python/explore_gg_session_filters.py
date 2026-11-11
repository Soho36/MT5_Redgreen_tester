"""First look at "avoid the bad day" filter ideas on the saved normal-GG ledger.

Written on 2026-11-11. A losing GG session (a large green first-cash-bar signal
on a morning with an 08:30 New York release) raised the question whether such
trades or days can be filtered out. These are after-the-fact cuts of trades that
already exist: no new MT5 run, no protocol, nothing adopted. Every cut that was
looked at is in this file, so the number of tries stays visible.

"Skip" figures remove trades from the ledger. That is not a replay: GG holds one
position at a time, so a skipped trade would free later entries that are not
modelled here. Only the stop-for-the-day rules are exact, because they remove
the tail of a session and nothing can replace it.

Reads
  Reports/gg_large_candle_20261109/gglarge_20261109_control_trades.csv  normal GG, native trades
  Reports/gg_large_candle_20261109/signal_features.csv                   every M30 bar and its session ratio
  data/calendars/us_major_news_times_2010_2026.csv                       CPI / payroll / FOMC release times
Writes nothing.

Run:  .\\venv\\Scripts\\python.exe python\\explore_gg_session_filters.py
"""
from __future__ import annotations

import zlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / 'Reports/gg_large_candle_20261109'
TRADES = RUN / 'gglarge_20261109_control_trades.csv'
FEATURES = RUN / 'signal_features.csv'
NEWS_TIMES = ROOT / 'data/calendars/us_major_news_times_2010_2026.csv'

ERAS = ('2016-19', '2020-26')
PUBLISHED = {'2016-19': (6388, 3635.60), '2020-26': (11181, 39315.45)}  # gg-large-candle-stop/RESULTS.md
OPEN_BAR = '16:30'  # research clock (Chicago + 8 h): the 09:30-10:00 New York bar; its order goes in at 17:00
SEED = 20261111
BOOT = 4000   # session-cluster bootstrap draws
DRAWS = 1000  # random skips matched on year and dollar-risk decile

pd.set_option('display.width', 260)
pd.set_option('display.max_columns', 40)
pd.set_option('display.max_rows', 400)
pd.set_option('display.float_format', lambda v: f'{v:,.3f}')


def rng_for(label: str, era: str) -> np.random.Generator:
    """One generator per rule and era, so the printed numbers do not depend on call order."""
    return np.random.default_rng([SEED, zlib.crc32(f'{label}|{era}'.encode())])


def stopped_after(t: pd.DataFrame, k: int, consecutive: bool) -> pd.Series:
    """True for trades that a stop-for-the-day after k (consecutive) losing trades would not take."""
    flag = np.zeros(len(t), bool)
    last, run, total, stopped = None, 0, 0, False
    for i, (session, loss) in enumerate(zip(t.session.to_numpy(), t.loss.to_numpy())):
        if session != last:
            last, run, total, stopped = session, 0, 0, False
        flag[i] = stopped
        if not stopped:
            run = run + 1 if loss else 0
            total += loss
            stopped = (run if consecutive else total) >= k
    return pd.Series(flag, index=t.index)


def load() -> pd.DataFrame:
    t = pd.read_csv(TRADES, parse_dates=['submitted', 'entry_time', 'exit_time', 'signal_bar'])
    t = t[t['sample'] == 'primary'].sort_values(['entry_time', 'ticket']).reset_index(drop=True)
    for era, (n, net) in PUBLISHED.items():
        g = t[t.era == era]
        assert len(g) == n and abs(g.net_dollars.sum() - net) < 0.01, f'{era} does not match the published GG totals'
    assert not (t.exit_time > t.entry_time.shift(-1)).any(), 'overlapping trades'

    t['slot'] = t.signal_bar.dt.strftime('%H:%M')
    t['has_ref'] = t.prior_count >= 5  # the study's rule: at least five earlier bars in the same session
    t['loss'] = (t.net_dollars < 0).astype(int)
    t['prior_losses'] = t.groupby('session').loss.cumsum() - t.loss
    streak, last, run = [], None, 0
    for session, loss in zip(t.session.to_numpy(), t.loss.to_numpy()):
        if session != last:
            last, run = session, 0
        streak.append(run)
        run = run + 1 if loss else 0
    t['loss_streak'] = streak
    t['risk_dec'] = t.groupby('year').initial_risk_dollars.transform(
        lambda x: pd.qcut(x.rank(method='first'), 10, labels=False)) + 1

    # scheduled news: session type and the 08:30 New York release time on CPI / payroll days
    news = pd.read_csv(NEWS_TIMES, usecols=['event', 'research_time'], parse_dates=['research_time'])
    news = news[news.event.isin(['CPI', 'PAYROLLS', 'FOMC'])]
    news['session'] = news.research_time.dt.strftime('%Y-%m-%d')
    t['news'] = t.session.map(news.groupby('session').event.agg(lambda s: '+'.join(sorted(set(s))))).fillna('none')
    early = news[news.event.isin(['CPI', 'PAYROLLS'])].groupby('session').research_time.min()
    t['release'] = pd.to_datetime(t.session.map(early))

    # a red bar of at least 3x its own earlier-session median among the two bars before the signal bar
    f = pd.read_csv(FEATURES, parse_dates=['bar_time']).sort_values('bar_time').reset_index(drop=True)
    big_red = (f.close < f.open) & (f.prior_count >= 5) & (f.ratio >= 3.0)
    f['red_before'] = ((big_red.shift(1, fill_value=False) & (f.session.shift(1) == f.session))
                       | (big_red.shift(2, fill_value=False) & (f.session.shift(2) == f.session)))
    t['red_before'] = t.signal_bar.map(f.set_index('bar_time').red_before).fillna(False).astype(bool)
    return t


def rules(t: pd.DataFrame) -> dict[str, pd.Series]:
    """Each rule marks the trades it would not take."""
    big = lambda x: t.has_ref & (t.ratio >= x)
    open_bar = t.slot == OPEN_BAR
    out = {
        'signal >= 2.5x session median': big(2.5),
        'signal >= 3x session median': big(3.0),
        'signal >= 3.5x session median': big(3.5),
        'signal >= 5x session median': big(5.0),
        'first cash bar as signal (16:30)': open_bar,
        'first cash bar and >= 3x': open_bar & big(3.0),
        'first cash bar on CPI/payroll day': open_bar & t.release.notna(),
        'signal bar at/after 08:30 release': t.release.notna() & (t.signal_bar >= t.release),
        'any signal after a >= 3x red bar': t.red_before,
        '>= 3x signal after a >= 3x red bar': big(3.0) & t.red_before,
        'whole CPI/payroll/FOMC sessions': t.news != 'none',
        'CPI sessions': t.news.str.contains('CPI'),
        'payroll sessions': t.news.str.contains('PAYROLLS'),
        'FOMC sessions': t.news.str.contains('FOMC'),
        'top risk decile of its year (hindsight)': t.risk_dec == 10,
    }
    for k in (2, 3, 4, 5, 6):
        out[f'stop for the day after {k} losses (exact)'] = stopped_after(t, k, consecutive=False)
    for k in (2, 3, 4, 5):
        out[f'stop after {k} losses in a row (exact)'] = stopped_after(t, k, consecutive=True)
    return out


def daily_dd(g: pd.DataFrame) -> float:
    eq = g.groupby('session').net_dollars.sum().sort_index().cumsum().to_numpy()
    return float((np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:] - eq).max()) if len(eq) else 0.0


def contrast(g: pd.DataFrame, f: np.ndarray, rng: np.random.Generator, col: str = 'gross_r'):
    """mean(col | skipped) - mean(col | kept) with a 95% interval, resampling whole sessions."""
    v = g[col].to_numpy()
    a = pd.DataFrame({'s': g.session.to_numpy(), 'vf': np.where(f, v, 0.0), 'nf': f.astype(float),
                      'vr': np.where(~f, v, 0.0), 'nr': (~f).astype(float)}).groupby('s').sum().to_numpy()
    tot = a.sum(axis=0)
    b = rng.multinomial(len(a), np.full(len(a), 1.0 / len(a)), size=BOOT) @ a
    with np.errstate(divide='ignore', invalid='ignore'):
        d = b[:, 0] / b[:, 1] - b[:, 2] / b[:, 3]
    lo, hi = np.nanpercentile(d, [2.5, 97.5])
    return tot[0] / tot[1], tot[2] / tot[3], lo, hi


def placebo(g: pd.DataFrame, f: np.ndarray, rng: np.random.Generator):
    """Share of random skips (same count per year and risk decile) that the rule beats on daily DD and net/DD."""
    strata = (g.year.astype(str) + '_' + g.risk_dec.astype(str)).to_numpy()
    net = g.net_dollars.to_numpy()
    codes, _ = pd.factorize(g.session)

    def stats(keep):
        eq = np.bincount(codes[keep], weights=net[keep], minlength=codes.max() + 1).cumsum()
        return net[keep].sum(), (np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:] - eq).max()

    members: dict[str, list[int]] = {}
    for i, s in enumerate(strata):
        members.setdefault(s, []).append(i)
    need = pd.Series(strata[f]).value_counts().to_dict()
    rule_net, rule_dd = stats(~f)
    nets, dds = np.empty(DRAWS), np.empty(DRAWS)
    for j in range(DRAWS):
        skip = np.zeros(len(g), bool)
        for s, k in need.items():
            skip[rng.choice(members[s], size=k, replace=False)] = True
        nets[j], dds[j] = stats(~skip)
    return 100 * (dds > rule_dd).mean(), 100 * (nets / dds < rule_net / rule_dd).mean()


def rule_table(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, flag in rules(t).items():
        for era in ERAS:
            g = t[t.era == era]
            f = flag[g.index].to_numpy()
            cut, kept = g[f], g[~f]
            mean_cut, mean_kept, lo, hi = contrast(g, f, rng_for(label, era))
            # no random comparison for the session-tail rules, nor for the risk decile itself:
            # skips matched on risk decile would pick exactly the same trades
            plain = '(exact)' not in label and '(hindsight)' not in label
            dd_pct, ratio_pct = placebo(g, f, rng_for(label + '|placebo', era)) if plain else (np.nan, np.nan)
            rows.append({
                'rule (trades not taken)': label, 'era': era, 'n': int(f.sum()),
                'their net $': cut.net_dollars.sum(), 'their gross R': mean_cut, 'other gross R': mean_kept,
                'diff lo': lo, 'diff hi': hi,
                'net $ before': g.net_dollars.sum(), 'net $ after': kept.net_dollars.sum(),
                'daily DD before': daily_dd(g), 'daily DD after': daily_dd(kept),
                'net/DD before': g.net_dollars.sum() / daily_dd(g), 'net/DD after': kept.net_dollars.sum() / daily_dd(kept),
                'DD beats % random': dd_pct, 'net/DD beats % random': ratio_pct,
            })
    return pd.DataFrame(rows)


def summ(g: pd.DataFrame) -> pd.Series:
    risk = g.initial_risk_dollars
    return pd.Series({
        'n': len(g), 'net$': g.net_dollars.sum(), 'net_R': g.net_r.mean(), 'gross_R': g.gross_r.mean(),
        'win%': 100 * (g.net_dollars > 0).mean(), 'med_risk$': risk.median(), 'sum_risk$': risk.sum(),
        'net/risk$': g.net_dollars.sum() / risk.sum() if risk.sum() else np.nan, 'worst$': g.net_dollars.min(),
    })


def table(t: pd.DataFrame, key, title: str) -> None:
    print(f'\n=== {title}')
    for era in ERAS:
        g = t[t.era == era]
        out = g.groupby(key, observed=True).apply(summ, include_groups=False)
        out['share_n%'] = 100 * out.n / out.n.sum()
        out['share_net%'] = 100 * out['net$'] / g.net_dollars.sum()
        print(f'--- {era}  (n={len(g)}, net=${g.net_dollars.sum():,.2f})')
        print(out)


def main() -> None:
    t = load()
    big3 = t.has_ref & (t.ratio >= 3.0)
    open_bar = t.slot == OPEN_BAR
    print(t.groupby('era').agg(trades=('net_dollars', 'size'), net=('net_dollars', 'sum'), sessions=('session', 'nunique')))

    print('\n=== skip rules: what the skipped trades earned, and the ledger without them')
    r = rule_table(t)
    print(r.to_string(index=False, float_format=lambda v: f'{v:,.3f}' if abs(v) < 20 else f'{v:,.0f}'))

    t['ratio_class'] = pd.cut(np.where(t.has_ref, t.ratio, -1.0), [-2, -0.5, 1, 2, 2.5, 3, 3.5, 5, 1e9], right=False,
                              labels=['no ref (<5 bars)', '<1', '1-2', '2-2.5', '2.5-3', '3-3.5', '3.5-5', '>=5'])
    table(t, 'ratio_class', 'signal range / median range of earlier same-session M30 bars')
    table(t, 'slot', 'signal-bar slot (bar open, research clock; the order goes in 30 minutes later)')
    minutes = t.signal_bar.dt.hour * 60 + t.signal_bar.dt.minute
    t['block'] = pd.cut(minutes, [0, 930, 990, 1020, 1110, 1380, 1440], right=False,
                        labels=['01:00-15:00 overnight', '15:30-16:00 pre-open', '16:30 first cash bar',
                                '17:00-18:00 next 3 bars', '18:30-22:30 rest of cash', '23:00+'])
    table(t, 'block', 'session blocks by signal bar')
    t['block_big'] = t.block.astype(str) + np.where(big3, ' | >=3x', ' | <3x')
    table(t, 'block_big', 'session block x signal >= 3x')
    ob = t[open_bar].assign(band=pd.cut(np.where(t.has_ref, t.ratio, -1.0)[open_bar], [-2, 3, 5, 8, 1e9], right=False,
                                        labels=['<3 / no ref', '3-5', '5-8', '>=8']))
    table(ob, 'band', 'first cash bar signals by ratio band')
    table(t, 'risk_dec', 'dollar-risk decile within year (10 = largest)')
    t['losses_so_far'] = t.prior_losses.clip(upper=6)
    table(t, 'losses_so_far', 'losing trades already taken in the same session (6 = six or more)')
    t['streak'] = t.loss_streak.clip(upper=5)
    table(t, 'streak', 'losses in a row immediately before, same session (5 = five or more)')
    table(t, 'news', 'session news type (CPI / payrolls / scheduled FOMC)')
    m = t[t.release.notna()].copy()
    m['timing'] = np.select([m.exit_time <= m.release, m.entry_time < m.release, m.signal_bar < m.release],
                            ['closed before release', 'open across release', 'signal bar before, filled after'],
                            'signal bar at/after release')
    table(m, 'timing', 'CPI/payroll days: trade timing relative to the 08:30 New York release')
    after = m[(m.timing == 'signal bar at/after release') & m.slot.isin(['15:30', '16:00', '16:30', '17:00', '17:30', '18:00'])]
    table(after, 'slot', 'CPI/payroll days: signal bars 15:30-18:00 (release at 15:30 research time)')

    print('\n=== how trades end by signal size, 2020-26 (% of class; mean gross R; median minutes held)')
    x = t[t.era == '2020-26'].copy()
    x['end'] = np.select([x.exit_comment.fillna('').str.startswith('sl'), x.gross_r >= 1.0], ['stopped', 'closed at +1R or more'],
                         'closed below +1R (mostly session end)')
    x['cls'] = np.where(x.has_ref & (x.ratio >= 5), '>=5x', np.where(x.has_ref & (x.ratio >= 3), '3-5x', '<3x / no ref'))
    e = x.groupby(['cls', 'end']).agg(n=('gross_r', 'size'), gross_R=('gross_r', 'mean'), net=('net_dollars', 'sum'),
                                      minutes=('holding_minutes', 'median'))
    e['% of class'] = 100 * e.n / e.groupby(level=0).n.transform('sum')
    print(e)

    print('\n=== sessions by year: how often a day loses or gains this much (one MNQ, net)')
    d = t.groupby(['year', 'session']).net_dollars.sum().reset_index()
    print(d.groupby('year').net_dollars.agg(
        sessions='size', losing_pct=lambda s: 100 * (s < 0).mean(), p05=lambda s: s.quantile(.05), worst='min',
        le_minus500=lambda s: int((s <= -500).sum()), le_minus700=lambda s: int((s <= -700).sum()),
        ge_plus500=lambda s: int((s >= 500).sum()), ge_plus700=lambda s: int((s >= 700).sum()), best='max'))
    for era in ERAS:
        g = t[t.era == era]
        s = g.groupby('session').net_dollars.sum()
        k = max(1, len(s) // 20)
        worst, best = s.nsmallest(k).index, s.nlargest(k).index
        gb3 = big3[g.index]
        print(f'{era}: worst 5% of sessions {s.nsmallest(k).sum():,.0f} (>=3x signals {g[g.session.isin(worst) & gb3].net_dollars.sum():,.0f}), '
              f'best 5% {s.nlargest(k).sum():,.0f} (>=3x signals {g[g.session.isin(best) & gb3].net_dollars.sum():,.0f}), all {s.sum():,.0f}')

    print('\n=== trade risk by year, and the largest-risk trades')
    print(t.groupby('year').initial_risk_dollars.agg(median='median', p90=lambda s: s.quantile(.9), p99=lambda s: s.quantile(.99), max='max'))
    for floor in (300, 500):
        b = t[t.initial_risk_dollars >= floor]
        print(f'risk >= ${floor}: n={len(b)}, net ${b.net_dollars.sum():,.2f}, gross R {b.gross_r.mean():+.3f}')
        print(b.groupby('year').agg(n=('net_dollars', 'size'), net=('net_dollars', 'sum'), wins=('net_dollars', lambda s: int((s > 0).sum())),
                                    stops=('gross_r', lambda s: int((s <= -0.999).sum())), worst=('net_dollars', 'min'), best=('net_dollars', 'max')))

    print('\n=== by year: net $ of the trades each idea would skip')
    print(t.groupby('year').apply(lambda g: pd.Series({
        'all': g.net_dollars.sum(),
        '>=3x n': int(big3[g.index].sum()), '>=3x net': g[big3[g.index]].net_dollars.sum(),
        '>=5x n': int((g.has_ref & (g.ratio >= 5)).sum()), '>=5x net': g[g.has_ref & (g.ratio >= 5)].net_dollars.sum(),
        'first cash bar n': int((g.slot == OPEN_BAR).sum()), 'first cash bar net': g[g.slot == OPEN_BAR].net_dollars.sum(),
        'news sessions net': g[g.news != 'none'].net_dollars.sum(),
        'after 4 losses net': g[g.prior_losses >= 4].net_dollars.sum(),
    }), include_groups=False))


if __name__ == '__main__':
    main()
