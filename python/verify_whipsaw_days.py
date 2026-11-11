"""Independent re-computation of the whipsaw-day study, written from the protocol with separate code.

Nothing is imported from whipsaw_days.py or analyze_whipsaw_days.py. Sessions, ATR20, swing counts,
flags, outcomes, news and ledger columns are rebuilt from the saved M30 bars with plain loops and
compared with the analysis' session table; every row of summary.csv is recomputed the slow way; the
first resampling draws are redone by really repeating whole months.
"""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / 'docs/baseline/whipsaw-days'
RUN = ROOT / 'Reports/whipsaw_days_20261111'
M30 = ROOT / 'Reports/gg_large_candle_20261109/signal_features.csv'
ROLLS = Path(r'F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_rolls.csv')
NEWS = ROOT / 'data/calendars/us_major_news_times_2010_2026.csv'
LEDGERS = {'gg': ROOT / 'Reports/gg_size_cap_20261111/ggcap_20261111_base_control_trades.csv',
           'rtl': ROOT / 'Reports/rtl_gg_exclude16_20261101/ex16_20261101_rtl_base_all_trades.csv'}
END = pd.Timestamp('2026-10-01')
SAMPLES = {'2010-15': ('2010-01-01', '2016-01-01'), '2016-19': ('2016-01-01', '2020-01-01'),
           '2020-26': ('2020-01-01', '2026-10-01'), '2016-26': ('2016-01-01', '2026-10-01')}
SWING_RULES = {'whipsaw': (0.75, 3), 'looser': (0.5, 4), 'stricter': (1.0, 3)}
EVENTS = ['whipsaw', 'looser', 'stricter', 'outside_inside']
MARKET = ['abs_move_1', 'range_1', 'trend_1', 'signed_1', 'abs_move_3', 'range_3', 'trend_3', 'signed_3']
LEDGER = ['gg_net', 'gg_r', 'rtl_net', 'rtl_r']
EXPLICIT_DRAWS = 60


def swings(path, threshold):
    """Zigzag swings by repeated search for the next reversal of at least `threshold`."""
    p = np.asarray(path, float)
    rise = np.flatnonzero(p - np.minimum.accumulate(p) >= threshold)
    fall = np.flatnonzero(np.maximum.accumulate(p) - p >= threshold)
    if not len(rise) and not len(fall):
        return 0
    first_rise = rise[0] if len(rise) else len(p)
    first_fall = fall[0] if len(fall) else len(p)
    at, direction, count = (first_rise, 1, 1) if first_rise < first_fall else (first_fall, -1, 1)
    while True:
        rest = p[at:]
        back = np.maximum.accumulate(rest) - rest if direction == 1 else rest - np.minimum.accumulate(rest)
        hit = np.flatnonzero(back >= threshold)
        if not len(hit):
            return count
        at, direction, count = at + hit[0], -direction, count + 1


def rebuild_sessions():
    by_day = defaultdict(list)
    with M30.open(newline='') as stream:
        for row in csv.DictReader(stream):
            by_day[row['bar_time'][:10]].append(tuple(float(row[k]) for k in ('open', 'high', 'low', 'close')))
    days = [day for day in sorted(by_day) if len(by_day[day]) >= 20]
    daily = [(by_day[d][0][0], max(b[1] for b in by_day[d]), min(b[2] for b in by_day[d]), by_day[d][-1][3]) for d in days]
    true_range = [None] + [max(daily[i][1], daily[i - 1][3]) - min(daily[i][2], daily[i - 1][3]) for i in range(1, len(days))]
    with ROLLS.open(newline='') as stream:
        rolls = list(csv.DictReader(stream))
    roll_days = {b['date'] for a, b in zip(rolls, rolls[1:]) if a['symbol'] != b['symbol']}
    news = pd.read_csv(NEWS, usecols=['event', 'research_time'])
    news_days = set(news.loc[news.event.isin(['CPI', 'PAYROLLS', 'FOMC']), 'research_time'].str[:10])
    ledgers = {}
    for name, path in LEDGERS.items():
        trades = pd.read_csv(path, usecols=['session', 'net_dollars', 'net_r', 'sample'])
        trades = trades.loc[trades['sample'] == 'primary']
        ledgers[name] = (trades.groupby('session').net_dollars.sum().to_dict(), trades.groupby('session').net_r.sum().to_dict())

    def inside(i):
        return i < len(days) and pd.Timestamp(days[i]) < END

    rows = []
    for i in range(21, len(days)):
        if pd.Timestamp(days[i]) >= END:
            continue
        o, h, l, c = daily[i]
        atr = sum(true_range[i - 20:i]) / 20
        path = []
        for bo, bh, bl, bc in by_day[days[i]]:
            path += [bo, bl, bh, bc] if bc >= bo else [bo, bh, bl, bc]
        row = dict(session=days[i], atr20=atr, range_ratio=(h - l) / atr, year=int(days[i][:4]))
        for name, (multiple, minimum) in SWING_RULES.items():
            row[name] = swings(path, multiple * atr) >= minimum
        ph, pl = daily[i - 1][1], daily[i - 1][2]
        row['outside_inside'] = h > ph and l < pl and pl <= c <= ph
        if inside(i + 1):
            o1, h1, l1, c1 = daily[i + 1]
            row.update(abs_move_1=abs(c1 - o1) / atr, range_1=(h1 - l1) / atr, signed_1=(c1 - o1) / atr,
                       trend_1=float(abs(c1 - o1) >= 0.6 * (h1 - l1) and h1 > l1), next_session=days[i + 1])
        if inside(i + 3):
            shift, highs, lows = 0.0, [], []
            for j in (i + 1, i + 2, i + 3):
                if j > i + 1 and days[j] in roll_days:
                    shift += daily[j][0] - daily[j - 1][3]      # old contract's close to new contract's open
                highs.append(daily[j][1] - shift)
                lows.append(daily[j][2] - shift)
            move, span = daily[i + 3][3] - shift - daily[i + 1][0], max(highs) - min(lows)
            row.update(abs_move_3=abs(move) / atr, range_3=span / atr, signed_3=move / atr,
                       trend_3=float(abs(move) >= 0.6 * span and span > 0))
        following = row.get('next_session')
        row['news'] = days[i] in news_days
        row['next_news'] = following in news_days
        row['news_free'] = not (row['news'] or row['next_news'])
        if following and days[i] >= '2016-01-01':
            for name, (net, r) in ledgers.items():
                row[name + '_net'], row[name + '_r'] = net.get(following, 0.0), r.get(following, 0.0)
        rows.append(row)
    frame = pd.DataFrame(rows)
    order = sorted(range(len(frame)), key=lambda k: (frame.range_ratio[k], k))
    group = [0] * len(frame)
    for rank, k in enumerate(order):
        group[k] = rank * 10 // len(frame)
    frame['size_group'] = group
    frame['month'] = frame.session.str[:7]
    return frame, len(roll_days)


def matched(frame, event, outcome):
    total = weight = 0.0
    for _, cell in frame.dropna(subset=[outcome]).groupby(['year', 'size_group']):
        events, controls = cell.loc[cell[event], outcome], cell.loc[~cell[event], outcome]
        if len(events) and len(controls):
            total += len(events) * (events.mean() - controls.mean())
            weight += len(events)
    return total / weight if weight else float('nan')


def corrected(frame, event, outcome):
    data = frame.dropna(subset=[outcome])
    cells = pd.factorize(data.year.astype(str) + '/' + data.size_group.astype(str))[0]
    design = np.column_stack([data[event].to_numpy(float), data.range_ratio.to_numpy(float), np.eye(cells.max() + 1)[cells]])
    return float(np.linalg.lstsq(design, data[outcome].to_numpy(float), rcond=None)[0][0])


def sample_of(frame, name, variant):
    start, end = SAMPLES[name]
    part = frame.loc[(frame.session >= start) & (frame.session < end)]
    return part if variant == 'all' else part.loc[part.news_free]


def main():
    frame, roll_days = rebuild_sessions()
    saved = pd.read_csv(RUN / 'sessions.csv', dtype={'session': str})
    assert len(frame) == len(saved) == 4180 and (frame.session == saved.session).all()
    assert {name: int(frame[name].sum()) for name in EVENTS} == dict(whipsaw=243, looser=549, stricter=63, outside_inside=233)
    for column in EVENTS + ['news', 'next_news', 'news_free', 'size_group', 'year']:
        assert (frame[column].to_numpy() == saved[column].to_numpy()).all(), column
    for column in ['atr20', 'range_ratio'] + MARKET + LEDGER:
        np.testing.assert_allclose(frame[column].to_numpy(float), saved[column].to_numpy(float), rtol=0, atol=1e-9,
                                   equal_nan=True, err_msg=column)
    assert (frame.next_session.fillna('') == saved.next_session.fillna('')).all()
    print(f'{len(frame):,} sessions rebuilt: flags, sizes, outcomes, news and ledger columns all equal', flush=True)

    summary = pd.read_csv(DOC / 'summary.csv')
    for row in summary.itertuples():
        part = sample_of(frame, row.sample, row.variant)
        assert np.isclose(matched(part, row.event, row.outcome), row.matched_diff, rtol=0, atol=1e-9), row
        assert np.isclose(corrected(part, row.event, row.outcome), row.corrected_diff, rtol=0, atol=1e-7), row
        have = part.dropna(subset=[row.outcome])
        assert (len(have), int(have[row.event].sum())) == (row.sessions, row.events), row
        np.testing.assert_allclose([have.loc[have[row.event], row.outcome].mean(), have.loc[~have[row.event], row.outcome].mean()],
                                   [row.all_events_mean, row.other_sessions_mean], rtol=0, atol=1e-9)
    print(f'{len(summary)} summary rows recomputed: both differences and the plain means all equal', flush=True)

    # Resampling: the same month counts, but applied by really repeating each month's sessions.
    draws = {kind: pd.read_csv(RUN / f'bootstrap_{kind}_draws.csv') for kind in ('matched', 'corrected')}
    redone = 0
    for name in SAMPLES:
        part = sample_of(frame, name, 'all')
        months = sorted(part.month.unique())
        by_month = [part.loc[part.month == m] for m in months]
        counts = np.random.default_rng(20261111).multinomial(len(months), np.full(len(months), 1 / len(months)), size=5000)
        for event in EVENTS:
            key = f'{name}|all|{event}|abs_move_1'
            for draw in range(EXPLICIT_DRAWS):
                again = pd.concat([m for m, k in zip(by_month, counts[draw]) for _ in range(k)], ignore_index=True)
                assert np.isclose(matched(again, event, 'abs_move_1'), draws['matched'][key][draw], rtol=0, atol=1e-9, equal_nan=True)
                assert np.isclose(corrected(again, event, 'abs_move_1'), draws['corrected'][key][draw], rtol=0, atol=1e-6, equal_nan=True)
                redone += 2
            row = summary.loc[(summary['sample'] == name) & (summary.variant == 'all') & (summary.event == event)
                              & (summary.outcome == 'abs_move_1')].iloc[0]
            for kind in ('matched', 'corrected'):
                values = draws[kind][key].dropna()
                np.testing.assert_allclose(np.percentile(values, [2.5, 97.5]), [row[kind + '_lo'], row[kind + '_hi']], rtol=0, atol=1e-12)
    print(f'{redone} resampling draws redone by repeating whole months; all 32 headline intervals equal', flush=True)

    result = dict(all_passed=True, sessions=len(frame), roll_dates=roll_days, summary_rows=len(summary),
                  explicit_resampling_draws=redone, headline_intervals=32,
                  summary_sha256=hashlib.sha256((DOC / 'summary.csv').read_bytes()).hexdigest(),
                  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (DOC / 'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
