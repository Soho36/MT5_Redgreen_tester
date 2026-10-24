"""Independent verification of the pullback/bounce warning statistics.

Uses the crystal-ball verifier's separately written zigzag and roll adjustment,
then recomputes features with loops, cutoffs, targets from explicit session
sets, rates, volatility matching, every circular shift by np.roll, timing
classes, leg lengths, hazards and the decision.
"""
from __future__ import annotations

import bisect
import json
import math

import numpy as np
import pandas as pd

import verify_rtl_downtrend_oracle as first

STUDY = first.ROOT / 'Reports/rtl_pullback_stats_20261025'
PROTOCOL = first.ROOT / 'docs/baseline/rtl-pullback-stats/PROTOCOL.md'
EXPECTED_PROTOCOL = 'e8322dd0e12e3bfe1485d2c0231e610fa3ea6e04ccb155039ebd6d87120e3461'
SIZES, LOOKBACKS, KS = (.02, .03, .05), (5, 10, 20), (1, 2, 3)
LEVELS = {'primary': (.90, .10), 'sensitivity': (.80, .20)}


def loop_features(c):
    n = len(c)
    out = {'vol': np.full(n, np.nan)}
    log_returns = [np.nan] + [math.log(c[t]/c[t-1]) for t in range(1, n)]
    for t in range(20, n):
        window = log_returns[t-19:t+1]
        mean = sum(window)/20
        out['vol'][t] = math.sqrt(sum((v-mean)**2 for v in window)/19)
    for m in LOOKBACKS:
        out[f'rise_{m}'] = np.array([c[t]/c[t-m]-1 if t >= m else np.nan for t in range(n)])
        out[f'zscore_{m}'] = np.array([math.log(c[t]/c[t-m])/(out['vol'][t]*math.sqrt(m)) if t >= max(m, 20) else np.nan
                                       for t in range(n)])
    return pd.DataFrame(out)


def main():
    checks = {}
    provenance = json.loads((STUDY/'provenance.json').read_text(encoding='utf-8'))
    checks['protocol_unchanged'] = first.sha(PROTOCOL, True) == EXPECTED_PROTOCOL == provenance['protocol_sha256_crlf_normalized']
    checks['outputs_match_provenance'] = all(first.sha(STUDY/name) == digest for name, digest in provenance['outputs_sha256'].items())
    daily = pd.read_csv(first.SOURCE/'features_d1_20.csv', usecols=['bar_time', 'open', 'close'],
                        parse_dates=['bar_time'], index_col='bar_time')
    daily = daily.loc[daily.index <= '2026-09-30']
    rolls = pd.read_csv(first.ROLLS, parse_dates=['date'])
    switches = [d for d in rolls.loc[rolls.symbol != rolls.symbol.shift(), 'date'].iloc[1:] if d <= daily.index[-1]]
    sessions = daily.index
    closes = {'roll_adjusted': first.adjusted(daily, switches), 'raw': daily.close.to_numpy(dtype=float)}
    stats = pd.read_csv(STUDY/'stats.csv')
    cutoffs = pd.read_csv(STUDY/'cutoffs.csv')
    panel = pd.read_csv(STUDY/'panel.csv', parse_dates=['session'])
    era_of = {era: np.asarray((sessions >= start) & (sessions < stop)) for era, (start, stop) in first.ERAS.items()}
    pre2016 = np.asarray(sessions < '2016-01-01')
    ok = dict(features=True, cutoffs=True, rates=True, shifts=True, timing=True)
    passes = []
    for series, c in closes.items():
        frame = loop_features(c)
        saved = panel.loc[panel.series.eq(series)].reset_index(drop=True)
        ok['features'] &= np.allclose(frame.to_numpy(), saved[frame.columns].to_numpy(), equal_nan=True, rtol=1e-10, atol=1e-12)
        valid = frame.notna().all(axis=1).to_numpy()
        terciles = np.quantile(frame.vol[valid & pre2016], [1/3, 2/3])
        tercile = np.array([0 if v <= terciles[0] else 1 if v <= terciles[1] else 2 for v in frame.vol.fillna(0)])
        signal = {}
        for family in ('rise', 'zscore'):
            for m in LOOKBACKS:
                values = frame[f'{family}_{m}'].to_numpy()
                calibration = np.sort(values[valid & pre2016])
                for level, (high, low) in LEVELS.items():
                    def linear(q):
                        position = q*(len(calibration)-1)
                        lower = int(math.floor(position))
                        return calibration[lower]+(calibration[min(lower+1, len(calibration)-1)]-calibration[lower])*(position-lower)
                    top, bottom = linear(high), linear(low)
                    row = cutoffs.loc[cutoffs.series.eq(series) & cutoffs.predictor.eq(f'{family}_{m}') & cutoffs.level.eq(level)].iloc[0]
                    ok['cutoffs'] &= np.isclose(top, row.stop_cutoff, rtol=1e-12) and np.isclose(bottom, row.resume_cutoff, rtol=1e-12)
                    signal[('stop', f'{family}_{m}', level)] = valid & (values >= top)
                    signal[('resume', f'{family}_{m}', level)] = valid & (values <= bottom)
        for x in SIZES:
            segments = first.pivots(c, x)
            peaks = [s['peak'] for s in segments]
            troughs = [s['trough'] for s in segments if not s['censored']]
            last = max(peaks+troughs)
            falling, rising = set(), set()
            for number, s in enumerate(segments):
                falling.update(range(s['peak']+1, s['trough']+1))
                if not s['censored']:
                    end = segments[number+1]['peak'] if number+1 < len(segments) else len(c)-1
                    rising.update(range(s['trough']+1, end+1))
            for k in KS:
                for direction, turns, opposite in (('stop', peaks, falling), ('resume', troughs, rising)):
                    turn_set, ordered = set(turns), sorted(turns)
                    target = np.array([any(p in turn_set for p in range(t, t+k+1)) for t in range(len(c))])
                    timing = []
                    for t in range(len(c)):
                        nxt = bisect.bisect_left(ordered, t)
                        if target[t]:
                            timing.append('hit')
                        elif t in opposite:
                            timing.append('late')
                        elif nxt < len(ordered) and ordered[nxt]-t <= 10:
                            timing.append('early')
                        else:
                            timing.append('false_alarm')
                    timing = np.array(timing)
                    for (sig_direction, predictor, level), sig in signal.items():
                        if sig_direction != direction:
                            continue
                        for era, in_era in era_of.items():
                            chosen = valid & in_era & (np.arange(len(c)) <= last-k)
                            s_, t_, g_ = sig[chosen], target[chosen], tercile[chosen]
                            row = stats.loc[stats.series.eq(series) & np.isclose(stats['size'], x) & stats.direction.eq(direction)
                                            & stats.predictor.eq(predictor) & stats.level.eq(level) & stats.k.eq(k)
                                            & stats.era.eq(era)].iloc[0]
                            hit_rate = (s_ & t_).sum()/s_.sum()
                            expected = np.mean([t_[g_ == j].mean() for j in g_[s_]])
                            ok['rates'] &= (int(s_.sum()) == row.signals and np.isclose(hit_rate, row.hit_rate)
                                            and np.isclose(t_.mean(), row.base_rate) and np.isclose(expected, row.vol_matched_base))
                            rates = np.array([(np.roll(s_, j) & t_).sum()/s_.sum() for j in range(len(s_))])
                            ok['shifts'] &= np.isclose(np.quantile(rates, .975), row.shift_p975)
                            ok['timing'] &= np.isclose((timing[chosen][s_] == 'hit').mean(), row.timing_hit) and np.isclose(
                                (timing[chosen][s_] == 'false_alarm').mean(), row.timing_false_alarm)
                            if level == 'primary' and k == 2:
                                passes.append(dict(series=series, size=x, direction=direction, predictor=predictor,
                                                   ok=bool(s_.sum() >= 30 and hit_rate >= 1.25*expected
                                                           and hit_rate >= 1.25*t_.mean() and hit_rate > np.quantile(rates, .975))))
        print(f'{series}: recomputed.', flush=True)
    checks.update({f'{name}_reproduced': bool(value) for name, value in ok.items()})
    frame = pd.DataFrame(passes)
    both = frame.groupby(['series', 'size', 'direction', 'predictor']).ok.all()
    decision = json.loads((STUDY/'decision.json').read_text(encoding='utf-8'))
    same = True
    for (series, x), part in both.groupby(level=['series', 'size']):
        saved = decision['by_series_size'][f'{series}|{x}']
        part = part.droplevel(['series', 'size'])
        same &= sorted(part.loc['stop'][part.loc['stop']].index) == saved['stop_passing']
        same &= sorted(part.loc['resume'][part.loc['resume']].index) == saved['resume_passing']
    checks['decision_reproduced'] = bool(same)
    hazard = pd.read_csv(STUDY/'hazard.csv')
    legs = pd.read_csv(STUDY/'legs.csv')
    mine_hazard, mine_legs = {}, []
    bins = ((1, 2), (3, 5), (6, 10), (11, 20), (21, 10**6))
    for series, c in closes.items():
        for x in SIZES:
            segments = first.pivots(c, x)
            for number, s in enumerate(segments):
                if s['censored']:
                    continue
                pairs = [('falling', s['peak'], s['trough'])]
                if number+1 < len(segments):
                    pairs.append(('rising', s['trough'], segments[number+1]['peak']))
                for leg, start, end in pairs:
                    mine_legs.append((series, x, leg, end-start))
                    for t in range(start+1, end+1):
                        era = next((e for e, m in era_of.items() if m[t]), None)
                        if era is None:
                            continue
                        low, high = next(b for b in bins if b[0] <= t-start <= b[1])
                        key = (series, x, era, leg, f'[{low}, {high}]')
                        count, events = mine_hazard.get(key, (0, 0))
                        mine_hazard[key] = (count+1, events+(end-t <= 2))
    same_hazard = len(mine_hazard) == len(hazard)
    for row in hazard.itertuples():
        count, events = mine_hazard.get((row.series, row.size, row.era, row.leg, row.age_bin), (0, 0))
        same_hazard &= count == row.sessions and np.isclose(events/count, row.turn_within_2)
    checks['hazard_reproduced'] = bool(same_hazard)
    checks['leg_lengths_reproduced'] = sorted(mine_legs) == sorted(zip(legs.series, legs['size'], legs.leg, legs.length))
    result = dict(all_passed=all(checks.values()), checks=checks, verified_rows=len(stats))
    (STUDY/'independent_verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    assert result['all_passed']


if __name__ == '__main__':
    main()
