"""The unchanged whipsaw-day rule on ES, YM and RTY.

The protocol's step after a supported NQ reading. Same event code, outcomes and comparisons; each
instrument uses its own ATR20 and its own ten size groups and is judged by points 1 to 3. They share
dates and moves with NQ: a check for an NQ-only accident, not independent evidence.
"""
import json

import pandas as pd

import analyze_whipsaw_days as study
import whipsaw_days as wd
from analyze_rtl_vwap_cross import FROZEN, INSTRUMENTS, minute_bars, rolls_path
from prepare_whipsaw_days import DOC, FREEZE, RUN, digest, frozen_texts

NAMES = ('ES', 'YM', 'RTY')
LONG = {'2010-15': wd.ERAS['2010-15'], '2016-19': wd.ERAS['2016-19'], '2020-26': wd.ERAS['2020-26'],
        '2016-26': wd.ERAS['2016-26']}
ERAS = {'ES': LONG, 'YM': LONG,   # RTY trades from 2017-07; judged from 2018 as in the earlier studies
        'RTY': {'2018-19': ('2018-01-01', '2020-01-01'), '2020-26': wd.ERAS['2020-26'], '2018-26': ('2018-01-01', wd.END)}}
JUDGED = {'ES': (('2016-19', '2020-26'), '2016-26'), 'YM': (('2016-19', '2020-26'), '2016-26'),
          'RTY': (('2018-19', '2020-26'), '2018-26')}


def roll_dates(path):
    rolls = pd.read_csv(path, parse_dates=['date'])
    return pd.DatetimeIndex(rolls.loc[rolls.symbol.ne(rolls.symbol.shift()) & rolls.symbol.shift().notna(), 'date'])


def main():
    freeze = json.loads(FREEZE.read_text(encoding='utf-8'))
    for key, value in frozen_texts().items():
        assert freeze[key] == value, f'{key} changed after the freeze'
    nq_verdict = json.loads((DOC / 'verdict.json').read_text(encoding='utf-8'))
    assert nq_verdict['supported'], 'the protocol applies the rule to other instruments only after a supported NQ reading'
    nq = pd.read_csv(RUN / 'sessions.csv', index_col=0, parse_dates=[0])
    news = study.news_dates()
    summaries, verdicts = [], {}
    for name in NAMES:
        spec = INSTRUMENTS[name]
        for path in (spec['minutes'], rolls_path(spec)):
            assert digest(path) == FROZEN[path], path      # the files hashed in the 2026-10-27 cross protocol
        bars, minutes = minute_bars(spec['minutes'])
        table = wd.session_table(bars)
        panel = wd.event_panel(bars)
        rolls = roll_dates(rolls_path(spec))
        panel = study.add_news(study.add_outcomes(panel, table, rolls), news)
        counts = wd.counts(panel)
        both = panel.index.intersection(nq.index)
        shared = float(nq.loc[both, 'whipsaw'][panel.loc[both, 'whipsaw'].to_numpy()].mean())
        print(f'{name}: {minutes:,} minutes, {len(panel):,} sessions {panel.index[0].date()} to {panel.index[-1].date()}, '
              f'{counts}; {shared:.0%} of its whipsaw days are NQ whipsaw days too', flush=True)
        summary, _ = study.summarise(panel, {era: study.MARKET for era in ERAS[name]}, eras=ERAS[name])
        summary.insert(0, 'instrument', name)
        main_eras, pooled = JUDGED[name]
        result = study.reading(summary, main_eras, pooled, neighbours=False)
        result.update(sessions=len(panel), counts=counts, roll_dates=len(rolls), minutes=minutes,
                      whipsaw_days_shared_with_nq=shared,
                      short_sessions_dropped=int((bars.groupby(bars.bar_time.dt.normalize()).size() < wd.MIN_BARS).sum()))
        verdicts[name] = result
        summaries.append(summary)
        panel.to_csv(RUN / f'sessions_{name}.csv')
        show = summary.loc[summary.outcome.eq(study.PRIMARY) & summary.variant.eq('all') & summary.event.eq('whipsaw'),
                           ['sample', 'events_used', 'event_mean', 'control_mean', 'matched_diff', 'matched_lo',
                            'matched_hi', 'corrected_diff', 'corrected_lo', 'corrected_hi']]
        print(show.to_string(index=False, float_format=lambda v: f'{v:.3f}'), flush=True)
        print(name, result['conditions'], result['verdict'], flush=True)
    pd.concat(summaries, ignore_index=True).to_csv(DOC / 'cross_summary.csv', index=False)
    passed = [name for name in NAMES if verdicts[name]['supported']]
    out = dict(instruments=verdicts, passed=passed, protocol_sha256=freeze['protocol_sha256'],
               event_code_sha256=freeze['event_code_sha256'], code_sha256=digest(__file__),
               analysis_code_sha256=digest(study.__file__))
    (DOC / 'cross_verdict.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(f'{len(passed)} of {len(NAMES)} pass points 1 to 3: {passed}')


if __name__ == '__main__':
    main()
