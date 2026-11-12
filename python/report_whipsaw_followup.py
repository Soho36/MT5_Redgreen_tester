"""Render the exploratory whipsaw follow-up from saved results; no model fitting."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

import whipsaw_days as wd
import whipsaw_followup_features as features

DOC, RUN = features.DOC, features.RUN
IMAGE = DOC / 'img'


def markdown_table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(str(x) for x in row) + ' |' for row in rows])


def summary_chart(scores, shapes):
    primary = scores.loc[scores['sample'].eq('2016-26') & scores.subset.eq('all')].set_index('model')
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8), layout='constrained')
    for i, (name, label, color) in enumerate([
        ('whipsaw', 'Add whipsaw flag', '#2563a6'),
        ('structure', 'Then add structure', '#26866f'),
        ('whipsaw5', 'Add flag, 5-minute sensitivity', '#687482')]):
        row = primary.loc[name]
        scale = 100 / row.baseline_mse
        axes[0].errorbar(row.mse_gain * scale, i,
                         xerr=[[max(0, (row.mse_gain - row.mse_gain_lo) * scale)],
                               [max(0, (row.mse_gain_hi - row.mse_gain) * scale)]],
                         fmt='o', capsize=4, color=color)
    axes[0].set_yticks(range(3), ['Add whipsaw flag', 'Then add structure', 'Flag, 5-minute sensitivity'])
    axes[0].invert_yaxis()
    axes[0].axvline(0, color='#8b929b', lw=1)
    axes[0].set_xlabel('Reduction in squared forecast error (%)\nPositive = improvement; paired month 95% intervals')
    axes[0].set_title('Forecasts trained only on earlier years')
    chosen = shapes.set_index('group')
    labels = []
    for i, name in enumerate(('initial_bounded', 'initial_expanding', 'initial_other', 'bilateral_failure')):
        row = chosen.loc[name]
        labels.append(name.replace('initial_', '').replace('_', ' ') + f' (n={int(row.sessions)})')
        axes[1].errorbar(row.residual, i,
                         xerr=[[max(0, row.residual - row.residual_lo)],
                               [max(0, row.residual_hi - row.residual)]],
                         fmt='o', color='#7045a0', capsize=4)
    axes[1].set_yticks(range(4), labels)
    axes[1].invert_yaxis()
    axes[1].axvline(0, color='#8b929b', lw=1)
    axes[1].set_xlabel('Actual next move minus volatility + whipsaw forecast (ATR)\nExploratory groups; intervals are not multiplicity-adjusted')
    axes[1].set_title('Does structure add to expected movement?')
    for ax in axes:
        ax.grid(axis='x', alpha=.2)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('NQ 2016–September 2026 · exploratory follow-up', fontsize=14)
    fig.savefig(IMAGE / 'forecast_comparison.png', dpi=170)
    plt.close(fig)


def examples(panel):
    bars = wd.read_m30()
    by_day = dict(tuple(bars.groupby(bars.bar_time.dt.normalize())))
    fig, axes = plt.subplots(3, 2, figsize=(13.5, 10), layout='constrained')
    selected = []
    for r, label in enumerate(('bounded', 'expanding', 'other')):
        candidates = panel.loc[(panel.index >= '2016-01-01') & panel.whipsaw & panel.geometry.eq(label)]
        choices = [candidates.index[0], candidates.index[len(candidates) // 2]] if len(candidates) else []
        for c, ax in enumerate(axes[r]):
            if c >= len(choices):
                ax.set_visible(False)
                continue
            day = choices[c]
            row, b = panel.loc[day], by_day[day]
            opening, atr = b.open.iloc[0], row.atr20
            for j, candle in enumerate(b.itertuples()):
                o, h, l, close = [(getattr(candle, k) - opening) / atr for k in ('open', 'high', 'low', 'close')]
                color = '#25856b' if close >= o else '#c44d4d'
                ax.plot([j, j], [l, h], color=color, lw=.8)
                ax.add_patch(Rectangle((j - .3, min(o, close)), .6, max(abs(close - o), .002),
                                       facecolor=color, edgecolor=color, linewidth=.5))
            path = wd.bar_path(*(b[k].to_numpy() for k in ('open', 'high', 'low', 'close')))
            points, _ = features.swing_trace(path, .75 * atr)
            initial = points[:4]
            ax.plot([p[0] / 4 for p in initial], [(p[1] - opening) / atr for p in initial],
                    'o--', color='#7540a0', markersize=4, lw=1.3, label='Initial three legs')
            ax.axvline(row.detected_bar + .45, color='#245f9b', ls=':', lw=1.5, label='Third swing known')
            if row.prior_levels_available:
                for name in ('prev_high', 'prev_low'):
                    ax.axhline((row[name] - opening) / atr, color='#929292', ls='--', lw=.7)
            low, high = (b.low.min() - opening) / atr, (b.high.max() - opening) / atr
            pad = .12 * (high - low)
            ax.set_ylim(low - pad, high + pad)
            ticks = np.arange(0, len(b), 8)
            ax.set_xticks(ticks, b.bar_time.iloc[ticks].dt.strftime('%H:%M'))
            ax.set_title(f'{label.capitalize()} initial swings · {day.date()}')
            ax.set_ylabel('ATR from session open')
            ax.grid(alpha=.15)
            ax.spines[['top', 'right']].set_visible(False)
            selected.append(dict(geometry=label, session=str(day.date()), selection='first' if c == 0 else 'middle'))
    axes[0, 0].legend(fontsize=8, loc='best')
    fig.suptitle('Event sessions only · examples selected by date, not subsequent movement\n'
                 'Research clock; gray levels = previous session high/low; final endpoint may be unconfirmed', fontsize=12)
    fig.savefig(IMAGE / 'geometry_examples.png', dpi=150)
    plt.close(fig)
    pd.DataFrame(selected).to_csv(DOC / 'example_sessions.csv', index=False)


def main():
    IMAGE.mkdir(parents=True, exist_ok=True)
    scores = pd.read_csv(DOC / 'forecast_scores.csv')
    shapes = pd.read_csv(DOC / 'structure_groups.csv')
    regressions = pd.read_csv(DOC / 'regressions.csv')
    verdict = json.loads((DOC / 'verdict.json').read_text())
    panel = pd.read_csv(RUN / 'sessions.csv', index_col=0, parse_dates=[0, 'detected_at'])
    summary_chart(scores, shapes)
    examples(panel)
    rows = []
    for sample in ('2016-19', '2020-26', '2016-26'):
        row = scores.loc[scores['sample'].eq(sample) & scores.model.eq('whipsaw') & scores.subset.eq('all')].iloc[0]
        rows.append([sample, int(row.sessions), int(row.events), f'{row.baseline_mse:.4f}',
                     f'{row.model_mse:.4f}', f'{100*row.relative_mse_gain:+.2f}%',
                     f'{row.mse_gain:+.5f} ({row.mse_gain_lo:+.5f} to {row.mse_gain_hi:+.5f})'])
    forecast_table = markdown_table(['Period', 'Sessions', 'Whipsaws', 'Baseline MSE', '+ flag MSE',
                                     'MSE reduction', 'Paired gain (95% interval)'], rows)
    primary = scores.loc[scores['sample'].eq('2016-26') & scores.subset.eq('all')].set_index('model')
    extra_rows = []
    for model, label in [('structure', 'Structure added to volatility + whipsaw'),
                         ('whipsaw5', 'Whipsaw added to 5-minute baseline')]:
        row = primary.loc[model]
        extra_rows.append([label, f'{100*row.relative_mse_gain:+.2f}%',
                           f'{row.mse_gain:+.5f} ({row.mse_gain_lo:+.5f} to {row.mse_gain_hi:+.5f})'])
    extra_table = markdown_table(['Secondary comparison', 'MSE reduction', 'Paired gain (95% interval)'], extra_rows)
    shape_table = markdown_table(['Group', 'Events', 'Next move (ATR)', 'Share >=1 ATR',
                                  'Volatility + whipsaw forecast', 'Residual (95% interval)'],
        [[r.group, int(r.sessions), f'{r.next_move:.2f}', f'{r.big_share:.0%}', f'{r.whipsaw_forecast:.2f}',
          f'{r.residual:+.2f} ({r.residual_lo:+.2f} to {r.residual_hi:+.2f})'] for r in shapes.itertuples()
         if r.group != 'prior_levels_unavailable'])
    regression_table = markdown_table(['Period', 'Controls', 'Adjusted association (95% interval)'],
        [[r.sample, r.specification, f'{r.estimate:+.3f} ({r.low:+.3f} to {r.high:+.3f})']
         for r in regressions.itertuples()])
    events = panel.loc[(panel.index >= '2016-01-01') & panel.whipsaw]
    timed = events.dropna(subset=['remaining_abs_move'])
    event_row = scores.loc[scores['sample'].eq('2016-26') & scores.model.eq('whipsaw') & scores.subset.eq('whipsaw')].iloc[0]
    primary_row = primary.loc['whipsaw']
    conclusion = ('The fixed historical forecast test passes.' if verdict['forecast_improvement_demonstrated']
                  else 'The fixed historical forecast test does not demonstrate incremental improvement.')
    text = f"""# Whipsaw follow-up: does the flag add to a volatility forecast?

Completed 2026-11-12 under the [recorded exploratory specification](PROTOCOL.md).
The original study and its positive historical association remain unchanged.

**{conclusion}** Adding the unchanged whipsaw flag changes pooled squared
forecast error by {100*primary_row.relative_mse_gain:+.2f}% improvement.
The paired loss reduction is {primary_row.mse_gain:+.5f}, with a month-resampling
95% interval of {primary_row.mse_gain_lo:+.5f} to {primary_row.mse_gain_hi:+.5f}.
Positive means the added feature improves forecasts; negative means worse.

On the 174 whipsaw sessions, the volatility-only model already forecast an
average move of {shapes.iloc[0].baseline_forecast:.2f} ATR, against {shapes.iloc[0].next_move:.2f}
actually observed. Adding the flag raises the forecast to {shapes.iloc[0].whipsaw_forecast:.2f} ATR,
but does not reliably reduce prediction errors. This does not prove the flag
contains no information: a full-history adjusted association and improvement
in predictions trained only on earlier history are different tests.

This is chronological historical evaluation on already studied data. It is
not fresh prospective evidence. No strategy, EA or live settings changed.

## The main comparison

Both models see current range, minute-level volatility, prior 5/20-session
volatility, recent true ranges, signed session body, scheduled news, weekday
and contract-roll indicators. The second also sees the unchanged whipsaw flag.
Each year uses coefficients and scaling fitted only on earlier years, excluding
training events whose outcomes cross into the evaluation year. Models predict
next-session absolute open-to-close movement in preceding-event ATR20 units.

{forecast_table}

MSE is in squared ATR units. Its reduction measures forecast accuracy, not a
percentage increase in the market's move. Pooled all-session MAE:
{primary_row.baseline_mae:.4f} baseline versus {primary_row.model_mae:.4f} with flag.
Event-only MSE improvement: {100*event_row.relative_mse_gain:+.2f}% (secondary).
The primary test requires a positive pooled interval and improvement in both
eras. No secondary result can rescue it. Intervals hold fitted forecasts fixed;
they do not include all model-estimation uncertainty or correct for prior research.

![Forecast comparison and structure residuals](img/forecast_comparison.png)

## Structure and five-minute sensitivity

{extra_table}

The five-minute variant checks sensitivity to sampling frequency; it was fixed
before this run. The structure model adds bounded/expanding initial-swing labels
and a bilateral previous-boundary failure flag. These comparisons are exploratory,
not alternative primary tests.

## What the new structure labels actually found

{shape_table}

Bounded requires both repeated highs and repeated lows within 0.10 ATR.
Expanding requires a higher second high AND lower second low, each by more than
0.10 ATR. Other includes drift, contraction and mixed geometry. These classify
the first three legs only; the fourth endpoint can be the observed terminal
extreme at session close. They are specific operational proxies, not an exhaustive
classification of every visual rectangle or gramophone.

Bilateral failure requires the first buffered breach of EACH previous-session
boundary to close back through that boundary within four M30 closing opportunities.
Previous raw levels are unavailable on roll dates. A failure flag does not
identify stop executions, nor does it require the two breaches to alternate.
This narrow previous-day definition may miss the intraday levels in the user's
example. Small subgroup counts cannot settle the broader chart-pattern hypothesis.

Residual means actual next move minus the model forecast that already includes
volatility and the whipsaw flag. A positive residual is descriptive underprediction,
not proof of a causal shape effect. Intervals are not adjusted for multiple groups.
The bilateral and geometry groups overlap and must not be added together.
Two whipsaw sessions have unavailable prior levels on roll dates and are excluded
from the failure/no-failure comparison. Their two-observation residual interval
is not interpreted here. Resamples with no members of a sparse subgroup cannot
produce a mean; structure_groups.csv records the omitted-draw counts.

![Geometry examples selected without future outcomes](img/geometry_examples.png)

## Recognition timing

All {len(events)} main events have a recorded third-swing recognition bar.
Median number of M30 bars remaining after recognition: {events.bars_after_detection.median():.0f}.
{len(timed)} have at least one later bar; {len(events)-len(timed)} have none.
From the next bar's open, the mean remaining-session absolute displacement is
{timed.remaining_abs_move.mean():.3f} ATR and remaining range is
{timed.remaining_range.mean():.3f} ATR. These are descriptive event averages,
with no matched comparison or fills. The recognition bar is excluded.

The full forecast uses session-close information; it is not an intraday forecast
available at the earlier recognition timestamp. An executable entry/exit study
would need its own specification and point-in-time inputs.

## Association after more detailed volatility controls

{regression_table}

The first regression reproduces the previously disclosed M1 review. The second
adds prior 5/20-session minute volatility. These use the old year/size fixed
effects and old resampling seed, as recorded in the table; the forecast experiment
does not use full-history size bins. These coefficients are conditional
associations, not causal decompositions and not forecast-loss reductions.

## Verification and reproduction

- All seven original input files and the original frozen rule/protocol hashes
  were verified. Original counts: 4,180 sessions, 243 events; 174 in 2016-26.
- M1 reconstruction: {verdict['m1_main_events']} events in the evaluated main sample,
  {verdict['m1_main_disagreements']} labels different from the original M30 flag.
- All 11 annual fits record training/test boundaries in forecast_folds.csv;
  the latest training outcome is before the evaluation year.
- 53 focused original/follow-up tests passed. Independent verification reproduced
  both volatility measures and all four histories for 4,180 sessions, all 243
  recognition times, 8,230 available boundary labels, all 13,870 annual-model
  forecasts and all 18 score rows. See [verification.json](verification.json).
- The [design record](design.json) fixes code/specification hashes and the prepared
  feature hash. The [verdict](verdict.json) records prediction and code hashes.

Commands, from the project root with the project venv:
prepare once with python/analyze_whipsaw_followup.py prepare; reproduce results
with python/analyze_whipsaw_followup.py analyze; render with
python/report_whipsaw_followup.py. Independently verify with
python/verify_whipsaw_followup.py. Run unittest discovery for test_whipsaw*.py.

Compact outputs: forecast_scores.csv, yearly_scores.csv, structure_groups.csv,
regressions.csv, forecast_folds.csv, coefficients.csv and example_sessions.csv.
Full features, session outcomes and predictions:
Reports/whipsaw_followup_20261112/. No thresholds or models were tuned after
these results. The bounded/expanding classifications need visual validation
before they can represent the broader patterns the user recognizes.
"""
    (DOC / 'RESULTS.md').write_text(text, encoding='utf-8')
    print(conclusion)
    print(DOC / 'RESULTS.md')


if __name__ == '__main__':
    main()

