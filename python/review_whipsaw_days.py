"""Checks made AFTER the frozen whipsaw-day reading came out as supported.

Not part of the protocol. They cannot change its verdict; they show how far it can be trusted and
what it means. Each check was written down here before its result was looked at:

1. Concentration. The matched difference year by year, with each year left out in turn, and without
   the five whipsaw sessions that were followed by the largest moves.
2. Plain counts. How often the next session moved more than a full normal range, how often a
   whipsaw day was followed by a larger move than the typical one of its own controls, and how
   often the next session closed above its open.
3. Is it the back-and-forth shape, or was the day simply more volatile than its range shows? The
   frozen size-corrected regression again, adding (a) how much price moved inside the session
   (root of the summed squared M30 changes, in ATR20 units), (b) whether the 20-session yardstick was
   already stale (mean true range of the 5 previous sessions / ATR20), (c) both.

All on NQ, primary event, next-session open-to-close move, all sessions, 2016 to September 2026.
"""
import numpy as np
import pandas as pd

import analyze_whipsaw_days as study
import whipsaw_days as wd
from prepare_whipsaw_days import DOC, RUN

EVENT, OUTCOME, SAMPLE = 'whipsaw', study.PRIMARY, wd.POOLED
BIG_MOVE = 1.0      # "a big day": open-to-close move of at least one normal day's range


def movement_inside(bars):
    """Root of the summed squared M30 changes of each session, the first one from the session's open."""
    day = bars.bar_time.dt.normalize()
    change = bars.close - bars.close.groupby(day).shift().fillna(bars.open)
    return np.sqrt((change ** 2).groupby(day).sum())


def with_extra_measures(panel, bars):
    table = wd.session_table(bars)
    prev_close = table.close.shift()
    true_range = np.maximum(table.high, prev_close) - np.minimum(table.low, prev_close)
    recent = true_range.rolling(5).mean().shift()
    out = panel.copy()
    out['inside_move'] = movement_inside(bars).reindex(out.index).to_numpy() / out.atr20
    out['recent5'] = recent.reindex(out.index).to_numpy() / out.atr20
    return out


def flag_coefficient(y, columns, cell, weight):
    """Coefficient of the first column in y ~ columns + one level per cell, with session weights."""
    total = np.bincount(cell, weights=weight)
    scale = np.divide(1.0, total, out=np.zeros_like(total), where=total > 0)

    def centred(values):
        return values - (np.bincount(cell, weights=weight * values) * scale)[cell]

    x = np.column_stack([centred(c) for c in columns])
    xw = x * weight[:, None]
    return np.linalg.solve(xw.T @ x, xw.T @ centred(y))[0]


def regression(frame, covariates, cell_by='size_group'):
    """Flag coefficient and month-resampling interval for the flag plus the named covariates."""
    data = frame.dropna(subset=[OUTCOME, *covariates])
    y = data[OUTCOME].to_numpy(float)
    columns = [data[EVENT].to_numpy(float)] + [data[c].to_numpy(float) for c in covariates]
    cell = pd.factorize(data.year.to_numpy() * 100 + data[cell_by].to_numpy())[0]
    months, month = np.unique(data.month.to_numpy(), return_inverse=True)
    weights = study.month_weights(len(months))
    point = flag_coefficient(y, columns, cell, np.ones(len(y)))
    draws = np.array([flag_coefficient(y, columns, cell, w[month].astype(float)) for w in weights])
    return point, *study.interval(draws)


def main():
    panel = pd.read_csv(RUN / 'sessions.csv', index_col=0, parse_dates=[0])
    panel = with_extra_measures(panel, wd.read_m30())
    frame = panel.loc[wd.in_era(panel, SAMPLE)].copy()
    rows = []

    def record(check, measure, value, low=np.nan, high=np.nan):
        rows.append(dict(check=check, measure=measure, value=value, low=low, high=high))

    # the frozen figures this review starts from
    pooled = study.matched_plain(frame, EVENT, OUTCOME)
    record('frozen', 'matched difference, 2016-26', pooled)

    # 1. concentration
    yearly = {int(year): study.matched_plain(part, EVENT, OUTCOME) for year, part in panel.groupby('year')
              if part[EVENT].sum()}
    for year, value in yearly.items():
        record('by year', str(year), value)
        record('whipsaw days by year', str(year), int(panel.loc[panel.year.eq(year), EVENT].sum()))
    main_years = [value for year, value in yearly.items() if year >= 2016]
    record('by year', 'years above zero, 2016-26', sum(v > 0 for v in main_years), high=len(main_years))
    record('by year', 'years above zero, 2010-26', sum(v > 0 for v in yearly.values()), high=len(yearly))
    left_out = {year: study.matched_plain(frame.loc[frame.year != year], EVENT, OUTCOME) for year in sorted(frame.year.unique())}
    record('leave one year out', 'smallest pooled difference', min(left_out.values()))
    record('leave one year out', 'largest pooled difference', max(left_out.values()))
    record('leave one year out', 'year whose removal lowers it most', min(left_out, key=left_out.get))
    largest = frame.loc[frame[EVENT], OUTCOME].nlargest(5)
    trimmed = frame.copy()
    trimmed.loc[largest.index, OUTCOME] = np.nan
    record('without the 5 largest', 'matched difference', study.matched_plain(trimmed, EVENT, OUTCOME))
    record('without the 5 largest', 'smallest of the five outcomes removed', largest.min())

    # 2. plain counts
    frame['big'] = np.where(frame[OUTCOME].notna(), (frame[OUTCOME] >= BIG_MOVE).astype(float), np.nan)
    events, others = frame.loc[frame[EVENT]], frame.loc[~frame[EVENT]]
    record('big next session', 'share after whipsaw days', events.big.mean())
    record('big next session', 'share after their matched controls', events.big.mean() - study.matched_plain(frame, EVENT, 'big'))
    record('big next session', 'share after all other days', others.big.mean())
    above = total = 0
    for _, cell in frame.dropna(subset=[OUTCOME]).groupby(['year', 'size_group']):
        own, controls = cell.loc[cell[EVENT], OUTCOME], cell.loc[~cell[EVENT], OUTCOME]
        if len(own) and len(controls):
            above += int((own > controls.median()).sum())
            total += len(own)
    record('against own controls', 'whipsaw days followed by more than their controls\' median move', above / total, high=total)
    record('medians', 'median after whipsaw days', events[OUTCOME].median())
    record('medians', 'median after all other days', others[OUTCOME].median())
    frame['up'] = np.where(frame.signed_1.notna(), (frame.signed_1 > 0).astype(float), np.nan)
    months, month = np.unique(frame.month.to_numpy(), return_inverse=True)
    up, _ = study.compare(frame, EVENT, 'up', month, study.month_weights(len(months)))
    record('next session closed up', 'share after whipsaw days', up['event_mean'])
    record('next session closed up', 'share after their matched controls', up['control_mean'])
    record('next session closed up', 'difference', up['matched_diff'], up['matched_lo'], up['matched_hi'])

    # 3. shape, or a day more volatile than its range shows?
    record('extra measures', 'inside movement: whipsaw days (mean)', events.inside_move.mean())
    record('extra measures', 'inside movement: all other days (mean)', others.inside_move.mean())
    record('extra measures', 'recent 5 / ATR20: whipsaw days (mean)', events.recent5.mean())
    record('extra measures', 'recent 5 / ATR20: all other days (mean)', others.recent5.mean())
    specifications = {'size of the day (frozen comparison)': ['range_ratio'],
                      '+ movement inside the session': ['range_ratio', 'inside_move'],
                      '+ stale yardstick (last 5 sessions / ATR20)': ['range_ratio', 'recent5'],
                      '+ both': ['range_ratio', 'inside_move', 'recent5']}
    for label, covariates in specifications.items():
        record('whipsaw flag after correcting for', label, *regression(frame, covariates))
    frame['inside_group'] = wd.size_groups(panel.inside_move)[wd.in_era(panel, SAMPLE)]
    record('whipsaw flag after correcting for',
           'same year and same tenth by inside movement, + inside movement, size, stale yardstick',
           *regression(frame, ['inside_move', 'range_ratio', 'recent5'], cell_by='inside_group'))

    checks = pd.DataFrame(rows)
    checks.to_csv(DOC / 'review_checks.csv', index=False)
    with pd.option_context('display.width', 200, 'display.max_colwidth', 90, 'display.max_rows', 200):
        print(checks.to_string(index=False, float_format=lambda v: f'{v:.3f}'))


if __name__ == '__main__':
    main()
