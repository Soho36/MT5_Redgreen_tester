"""Independent numerical checks of the saved follow-up (no output regeneration)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import whipsaw_days as wd
from prepare_whipsaw_days import digest, text_digest
from verify_rtl_failed_breakout_short import CACHE
from whipsaw_followup_features import DOC, RUN, ROOT


def verify():
    frame = pd.read_csv(RUN / 'sessions.csv', index_col=0, parse_dates=[0, 'next_session', 'detected_at'])
    predictions = pd.read_csv(RUN / 'predictions.csv', index_col=0, parse_dates=[0])
    verdict = json.loads((DOC / 'verdict.json').read_text())
    design_record = json.loads((DOC / 'design.json').read_text())
    for name, expected in design_record['hashes'].items():
        assert text_digest(ROOT / name) == expected, name
    assert digest(RUN / 'predictions.csv') == verdict['predictions_sha256']
    assert digest(RUN / 'features.csv') == design_record['features_sha256']
    bars = wd.read_m30()
    daily = wd.session_table(bars)
    with np.load(CACHE) as z:
        days, minutes, opening, closes = (z[k] for k in ('day', 'minute', 'o', 'c'))
    starts = np.flatnonzero(np.r_[True, days[1:] != days[:-1]])
    change = np.r_[0., np.diff(closes)]
    change[starts] = closes[starts] - opening[starts]
    rv1 = np.sqrt(np.add.reduceat(change ** 2, starts))
    keys = days * 288 + minutes // 5
    last = np.flatnonzero(np.r_[keys[1:] != keys[:-1], True])
    bucket_closes = closes[last]
    bucket_days = days[last]
    bucket_starts = np.flatnonzero(np.r_[True, bucket_days[1:] != bucket_days[:-1]])
    change5 = np.r_[0., np.diff(bucket_closes)]
    change5[bucket_starts] = bucket_closes[bucket_starts] - opening[starts]
    rv5 = np.sqrt(np.add.reduceat(change5 ** 2, bucket_starts))
    dates = pd.to_datetime(days[starts], unit='D')
    for name, values in [('rv1', rv1), ('rv5m', rv5)]:
        points = pd.Series(values, index=dates).reindex(daily.index)
        np.testing.assert_allclose(frame[name], points.reindex(frame.index) / frame.atr20, rtol=0, atol=1e-12)
        for n in (5, 20):
            independently_lagged = pd.Series(
                [points.iloc[i-n:i].mean() if i >= n else np.nan for i in range(len(points))],
                index=points.index)
            np.testing.assert_allclose(frame[f'{name}_prior{n}'],
                                       independently_lagged.reindex(frame.index) / frame.atr20,
                                       rtol=0, atol=1e-12)
    print('Both volatility measures and all four histories independently match all 4,180 sessions.', flush=True)

    timed = failures = 0
    for day, b in bars.groupby(bars.bar_time.dt.normalize()):
        if day not in frame.index:
            continue
        row = frame.loc[day]
        if row.whipsaw:
            k = int(row.detected_bar)
            path = wd.bar_path(*(b[c].to_numpy() for c in ('open', 'high', 'low', 'close')))
            assert wd.count_swings(path[:4*(k+1)], .75 * row.atr20) >= 3
            assert k == 0 or wd.count_swings(path[:4*k], .75 * row.atr20) < 3
            assert row.detected_at == b.bar_time.iloc[k] + pd.Timedelta(minutes=30)
            later = b.iloc[k+1:]
            if len(later):
                assert np.isclose(row.remaining_abs_move, abs(later.close.iloc[-1] - later.open.iloc[0]) / row.atr20)
            else:
                assert np.isnan(row.remaining_abs_move)
            timed += 1
        if row.prior_levels_available:
            for side in ('high', 'low'):
                level = row.prev_high if side == 'high' else row.prev_low
                first = None
                for i, price in enumerate(b[side]):
                    if (price >= level + .05 * row.atr20) if side == 'high' else (price <= level - .05 * row.atr20):
                        first = i
                        break
                failed = False
                if first is not None:
                    for i in range(first, min(first + 4, len(b))):
                        failed |= (b.close.iloc[i] <= level) if side == 'high' else (b.close.iloc[i] >= level)
                assert failed == row['failed_' + side], (day, side)
                failures += 1
        else:
            assert not row.failed_high and not row.failed_low and not row.failed_both
    print(f'Checked all {timed} recognition times and {failures} first-boundary failure labels.', flush=True)

    forecasts_checked = 0
    for year in sorted(predictions.index.year.unique()):
        boundary = pd.Timestamp(f'{year}-01-01')
        train = (frame.index < boundary) & (frame.next_session < boundary) & frame.abs_move_1.notna()
        test_dates = predictions.index[predictions.index.year == year]
        test = frame.index.isin(test_dates)
        assert frame.loc[train, 'next_session'].max() < boundary
        for model in ('baseline', 'whipsaw', 'structure', 'baseline5', 'whipsaw5'):
            prefix = 'rv5m' if model.endswith('5') else 'rv1'
            columns = [np.log1p(frame[c].to_numpy()) for c in (
                'range_ratio', prefix, prefix + '_prior5', prefix + '_prior20', 'recent5')]
            columns += [frame[c].to_numpy(float) for c in ('signed_body', 'news', 'next_news', 'roll_day')]
            columns += [(frame.index.dayofweek == d).astype(float) for d in range(1, 5)]
            if model in ('whipsaw', 'structure', 'whipsaw5'):
                columns.append(frame.whipsaw.to_numpy(float))
            if model == 'structure':
                columns += [frame[c].to_numpy(float) for c in ('whipsaw_bounded', 'whipsaw_expanding', 'whipsaw_failed_both')]
            x = np.column_stack(columns)
            mu, sd = x[train].mean(0), x[train].std(0)
            sd[sd <= 1e-12] = 1.
            train_design = np.c_[np.ones(train.sum()), (x[train] - mu) / sd]
            penalty = np.c_[np.zeros(x.shape[1]), np.sqrt(10.) * np.eye(x.shape[1])]
            beta = np.linalg.lstsq(np.vstack([train_design, penalty]),
                                  np.r_[frame.loc[train, 'abs_move_1'], np.zeros(x.shape[1])], rcond=None)[0]
            expected = np.maximum(np.c_[np.ones(test.sum()), (x[test] - mu) / sd] @ beta, 0.)
            np.testing.assert_allclose(expected, predictions.loc[test_dates, 'pred_' + model], rtol=0, atol=1e-10)
            forecasts_checked += len(test_dates)
    print(f'Independently solved every annual model: {forecasts_checked:,} forecasts agree.', flush=True)
    scores = pd.read_csv(DOC / 'forecast_scores.csv')
    for row in scores.itertuples():
        start, end = {'2016-19': ('2016-01-01', '2020-01-01'),
                      '2020-26': ('2020-01-01', '2026-10-01'),
                      '2016-26': ('2016-01-01', '2026-10-01')}[row.sample]
        part = predictions.loc[(predictions.index >= start) & (predictions.index < end)]
        if row.subset == 'whipsaw':
            part = part.loc[part.whipsaw]
        loss_a = (part.abs_move_1 - part['pred_' + row.baseline]) ** 2
        loss_b = (part.abs_move_1 - part['pred_' + row.model]) ** 2
        assert len(part) == row.sessions
        assert np.isclose((loss_a - loss_b).mean(), row.mse_gain, atol=1e-12, rtol=0)
    paths = ['python/whipsaw_followup_features.py', 'python/analyze_whipsaw_followup.py',
             'python/analyze_whipsaw_days.py', 'python/review_whipsaw_days.py',
             'python/whipsaw_days.py', 'python/prepare_whipsaw_days.py']
    result = dict(all_passed=True, sessions=len(frame), forecasts_checked=forecasts_checked,
                  recognition_times_checked=timed, boundary_labels_checked=failures,
                  score_rows_checked=len(scores),
                  dependency_hashes={name: text_digest(ROOT / name) for name in paths},
                  verification_code_sha256=text_digest(Path(__file__)),
                  numpy_version=np.__version__, pandas_version=pd.__version__)
    (DOC / 'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    verify()

