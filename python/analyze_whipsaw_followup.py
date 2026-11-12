"""Prepare and run the exploratory, chronologically evaluated whipsaw follow-up."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import analyze_whipsaw_days as original
import review_whipsaw_days as review
import whipsaw_days as wd
import whipsaw_followup_features as features
from prepare_whipsaw_days import ROOT, digest, text_digest

DOC, RUN = features.DOC, features.RUN
PROTOCOL = DOC / 'PROTOCOL.md'
DESIGN = DOC / 'design.json'
ALPHA = 10.0
DRAWS = 5000
SEED = 20261112
MODELS = ('baseline', 'whipsaw', 'structure', 'baseline5', 'whipsaw5')
COMPARISONS = (('baseline', 'whipsaw'), ('whipsaw', 'structure'), ('baseline5', 'whipsaw5'))
SAMPLES = {'2016-19': ('2016-01-01', '2020-01-01'),
           '2020-26': ('2020-01-01', wd.END), '2016-26': ('2016-01-01', wd.END)}


def code_hashes():
    return {name: text_digest(ROOT / name) for name in (
        'docs/baseline/whipsaw-followup/PROTOCOL.md',
        'python/whipsaw_followup_features.py', 'python/analyze_whipsaw_followup.py')}


def prepare():
    if DESIGN.exists():
        raise RuntimeError('Design already recorded; do not overwrite it')
    old = features.verify_original()
    panel, _ = features.build_features()
    RUN.mkdir(parents=True, exist_ok=True)
    panel.to_csv(RUN / 'features.csv')
    record = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                  exploratory_reused_history=True, prior_m1_results_seen=True,
                  original_protocol_sha256=old['protocol_sha256'], hashes=code_hashes(),
                  features_sha256=digest(RUN / 'features.csv'),
                  counts=wd.counts(panel), main_events=int(panel.loc[panel.year >= 2016, 'whipsaw'].sum()),
                  initial_geometry_counts=panel.loc[panel.whipsaw].geometry.value_counts().to_dict(),
                  alpha=ALPHA, draws=DRAWS, seed=SEED)
    DESIGN.write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record, indent=2), flush=True)


def read_features():
    record = json.loads(DESIGN.read_text(encoding='utf-8'))
    if record['hashes'] != code_hashes():
        raise ValueError('Recorded follow-up specification/code changed')
    features.verify_original()
    if record['features_sha256'] != digest(RUN / 'features.csv'):
        raise ValueError('Prepared features changed')
    return pd.read_csv(RUN / 'features.csv', index_col=0, parse_dates=[0, 'next_session', 'detected_at', 'failed_both_at'])


def design_matrix(frame, model):
    frequency = 'rv5m' if model.endswith('5') else 'rv1'
    positive = ['range_ratio', frequency, frequency + '_prior5', frequency + '_prior20', 'recent5']
    out = pd.DataFrame({f'log1p_{name}': np.log1p(frame[name]) for name in positive}, index=frame.index)
    for name in ('signed_body', 'news', 'next_news', 'roll_day'):
        out[name] = frame[name].astype(float)
    for day in range(1, 5):
        out[f'weekday_{day}'] = (frame.index.dayofweek == day).astype(float)
    if model in ('whipsaw', 'structure', 'whipsaw5'):
        out['whipsaw'] = frame.whipsaw.astype(float)
    if model == 'structure':
        for name in ('whipsaw_bounded', 'whipsaw_expanding', 'whipsaw_failed_both'):
            out[name] = frame[name].astype(float)
    if not np.isfinite(out.to_numpy()).all():
        raise ValueError('nonfinite design')
    return out


def fit_predict(train_x, train_y, test_x, alpha=ALPHA):
    """Ridge with train-only scaling and unpenalized intercept."""
    x, y, future = np.asarray(train_x, float), np.asarray(train_y, float), np.asarray(test_x, float)
    mean, scale = x.mean(0), x.std(0)
    scale = np.where(scale > 1e-12, scale, 1.0)
    z = (x - mean) / scale
    center = y.mean()
    slopes = np.linalg.solve(z.T @ z + alpha * np.eye(x.shape[1]), z.T @ (y - center))
    coefficients = slopes / scale
    intercept = center - mean @ coefficients
    prediction = np.maximum(intercept + future @ coefficients, 0.0)
    return prediction, coefficients, intercept, mean, scale


def training_mask(frame, year):
    boundary = pd.Timestamp(year=year, month=1, day=1)
    return (frame.index < boundary) & (frame.next_session < boundary) & frame.abs_move_1.notna()


def forecasts(frame, years=range(2016, 2027)):
    predicted, coefficients, folds = [], [], []
    designs = {model: design_matrix(frame, model) for model in MODELS}
    for year in years:
        train = training_mask(frame, year)
        test = (frame.index.year == year) & frame.abs_move_1.notna()
        if not test.any():
            continue
        if train.sum() < 200:
            raise ValueError('too few earlier training sessions')
        part = frame.loc[test].copy()
        folds.append(dict(year=year, training_sessions=int(train.sum()), test_sessions=int(test.sum()),
                          last_train_event=str(frame.index[train].max().date()),
                          last_train_outcome=str(frame.loc[train, 'next_session'].max().date()),
                          first_test_event=str(frame.index[test].min().date())))
        for model, design in designs.items():
            prediction, beta, intercept, mean, scale = fit_predict(
                design.loc[train], frame.loc[train, 'abs_move_1'], design.loc[test])
            part['pred_' + model] = prediction
            coefficients.append(dict(year=year, model=model, term='intercept', coefficient=intercept,
                                     train_mean=np.nan, train_scale=np.nan))
            for term, value, mu, sd in zip(design.columns, beta, mean, scale):
                coefficients.append(dict(year=year, model=model, term=term, coefficient=value,
                                         train_mean=mu, train_scale=sd))
        predicted.append(part)
    return pd.concat(predicted).sort_index(), pd.DataFrame(coefficients), pd.DataFrame(folds)


def paired_interval(values, dates, draws=DRAWS, seed=SEED):
    """Pairwise comparison resampling complete months, including zero-usable months."""
    y = np.asarray(values, float)
    months, month = np.unique(pd.DatetimeIndex(dates).to_period('M').astype(str), return_inverse=True)
    valid = np.isfinite(y)
    counts = np.bincount(month[valid], minlength=len(months))
    sums = np.bincount(month[valid], weights=y[valid], minlength=len(months))
    if not valid.any():
        return np.nan, np.nan, np.nan, draws
    weights = original.month_weights(len(months), draws=draws, seed=seed)
    denominators = weights @ counts
    replicas = np.divide(weights @ sums, denominators,
                         out=np.full(draws, np.nan), where=denominators > 0)
    low, high = original.interval(replicas)
    return float(y[valid].mean()), float(low), float(high), int(np.isnan(replicas).sum())


def score(frame, baseline, model, subset='all'):
    y = frame.abs_move_1.to_numpy(float)
    a = frame['pred_' + baseline].to_numpy(float)
    b = frame['pred_' + model].to_numpy(float)
    keep = np.ones(len(frame), bool) if subset == 'all' else frame.whipsaw.to_numpy(bool)
    mse_a, mse_b = (y - a) ** 2, (y - b) ** 2
    mae_a, mae_b = np.abs(y - a), np.abs(y - b)
    result = dict(baseline=baseline, model=model, subset=subset, sessions=int(keep.sum()),
                  events=int(frame.loc[keep, 'whipsaw'].sum()),
                  baseline_mse=float(mse_a[keep].mean()), model_mse=float(mse_b[keep].mean()),
                  baseline_mae=float(mae_a[keep].mean()), model_mae=float(mae_b[keep].mean()))
    for name, values in (('mse_gain', mse_a - mse_b), ('mae_gain', mae_a - mae_b)):
        mean, low, high, failed = paired_interval(np.where(keep, values, np.nan), frame.index)
        result.update({name: mean, name + '_lo': low, name + '_hi': high, name + '_failed_draws': failed})
    result['relative_mse_gain'] = result['mse_gain'] / result['baseline_mse']
    return result


def summarize(predicted):
    rows, yearly = [], []
    for sample, (start, end) in SAMPLES.items():
        part = predicted.loc[(predicted.index >= start) & (predicted.index < end)]
        for baseline, model in COMPARISONS:
            for subset in ('all', 'whipsaw'):
                rows.append(dict(sample=sample, **score(part, baseline, model, subset)))
    for year, part in predicted.groupby(predicted.index.year):
        for baseline, model in COMPARISONS:
            yearly.append(dict(year=year, **score(part, baseline, model)))
    return pd.DataFrame(rows), pd.DataFrame(yearly)


def structure_summary(predicted):
    events = predicted.whipsaw.to_numpy(bool)
    groups = {'all_whipsaws': events}
    for name in ('bounded', 'expanding', 'other'):
        groups['initial_' + name] = events & predicted.geometry.eq(name).to_numpy()
    available = predicted.prior_levels_available.to_numpy(bool)
    both = predicted.failed_both.to_numpy(bool)
    groups['bilateral_failure'] = events & available & both
    groups['no_bilateral_failure'] = events & available & ~both
    groups['prior_levels_unavailable'] = events & ~available
    rows = []
    for name, mask in groups.items():
        part = predicted.loc[mask]
        residual = predicted.abs_move_1 - predicted.pred_whipsaw
        difference, low, high, failed = paired_interval(np.where(mask, residual, np.nan), predicted.index)
        rows.append(dict(group=name, sessions=len(part),
                         mean_range=part.range_ratio.mean(), mean_rv1=part.rv1.mean(),
                         next_move=part.abs_move_1.mean(), big_share=part.abs_move_1.ge(1).mean(),
                         baseline_forecast=part.pred_baseline.mean(), whipsaw_forecast=part.pred_whipsaw.mean(),
                         residual=difference, residual_lo=low, residual_hi=high, failed_draws=failed))
    return pd.DataFrame(rows)


def regression_summary(panel):
    rows = []
    for sample, (start, end) in SAMPLES.items():
        part = panel.loc[(panel.index >= start) & (panel.index < end)]
        for name, covariates in (
            ('replicate_review_m1', ['range_ratio', 'rv1', 'recent5']),
            ('add_volatility_history', ['range_ratio', 'rv1', 'rv1_prior5', 'rv1_prior20', 'recent5'])):
            estimate, low, high = review.regression(part, covariates)
            rows.append(dict(sample=sample, specification=name, estimate=estimate, low=low, high=high,
                             draws=original.DRAWS, seed=original.SEED))
    return pd.DataFrame(rows)


def reading(scores):
    primary = scores.loc[scores.model.eq('whipsaw') & scores.subset.eq('all')].set_index('sample')
    pooled = primary.loc['2016-26']
    conditions = dict(pooled_interval_above_zero=bool(pooled.mse_gain_lo > 0),
                      improvement_in_both_eras=bool((primary.loc[['2016-19', '2020-26'], 'mse_gain'] > 0).all()))
    return dict(exploratory=True, conditions=conditions,
                forecast_improvement_demonstrated=all(conditions.values()),
                primary_relative_mse_gain=float(pooled.relative_mse_gain),
                primary_mse_gain=float(pooled.mse_gain),
                primary_interval=[float(pooled.mse_gain_lo), float(pooled.mse_gain_hi)])


def analyze():
    panel = read_features()
    bars = wd.read_m30()
    panel = original.add_outcomes(panel, wd.session_table(bars), original.roll_dates())
    panel = features.add_remaining_outcomes(panel, bars)
    predicted, coefficients, folds = forecasts(panel)
    scores, yearly = summarize(predicted)
    shapes = structure_summary(predicted)
    regressions = regression_summary(panel)
    for name, table in [('forecast_scores', scores), ('yearly_scores', yearly),
                        ('structure_groups', shapes), ('regressions', regressions),
                        ('forecast_folds', folds), ('coefficients', coefficients)]:
        table.to_csv(DOC / (name + '.csv'), index=False)
    predicted.to_csv(RUN / 'predictions.csv')
    panel.to_csv(RUN / 'sessions.csv')
    result = reading(scores)
    result.update(evaluation_sessions=len(predicted), evaluation_events=int(predicted.whipsaw.sum()),
                  year_boundary_checks=bool((pd.to_datetime(folds.last_train_outcome)
                                              < pd.to_datetime(folds.year.astype(str) + '-01-01')).all()),
                  original_counts=wd.counts(panel),
                  m1_main_events=int(predicted.m1_whipsaw.sum()),
                  m1_main_disagreements=int(predicted.m1_whipsaw.ne(predicted.whipsaw).sum()),
                  hashes=code_hashes(),
                  features_sha256=digest(RUN / 'features.csv'),
                  predictions_sha256=digest(RUN / 'predictions.csv'))
    (DOC / 'verdict.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(scores.loc[scores.subset.eq('all'), ['sample', 'model', 'sessions', 'mse_gain',
                                               'mse_gain_lo', 'mse_gain_hi', 'relative_mse_gain']].to_string(index=False))
    print(shapes.to_string(index=False))
    print(regressions.to_string(index=False))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'analyze'))
    args = parser.parse_args()
    prepare() if args.action == 'prepare' else analyze()

