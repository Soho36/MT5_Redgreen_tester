"""Execute the frozen pullback/bounce warning statistics.

Price data only: causal rise/fall signals against hindsight zigzag turns, with
volatility-matched base rates and all-shift placement controls.
"""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import pandas as pd

import analyze_rtl_downtrend_oracle as oracle
import analyze_rtl_market_regimes as prior

STUDY = oracle.ROOT / 'Reports/rtl_pullback_stats_20261025'
PROTOCOL = oracle.ROOT / 'docs/baseline/rtl-pullback-stats/PROTOCOL.md'
PROTOCOL_SHA256 = 'e8322dd0e12e3bfe1485d2c0231e610fa3ea6e04ccb155039ebd6d87120e3461'
CALIBRATION_END = pd.Timestamp('2016-01-01')
SIZES = (.02, .03, .05)
LOOKBACKS = (5, 10, 20)
FAMILIES = ('rise', 'zscore')
LEVELS = {'primary': (.90, .10), 'sensitivity': (.80, .20)}
KS = (1, 2, 3)
PRIMARY_K = 2
VOL_WINDOW = 20
MIN_SIGNALS, MIN_LIFT = 30, 1.25
AGE_BINS = ((1, 2), (3, 5), (6, 10), (11, 20), (21, 10**6))


def features(closes):
    """Rise and volatility-scaled rise over n sessions, all ending at t's close."""
    c = pd.Series(np.asarray(closes, dtype=float))
    log_return = np.log(c/c.shift())
    out = pd.DataFrame({'close': c, 'vol': log_return.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std(ddof=1)})
    for n in LOOKBACKS:
        out[f'rise_{n}'] = c/c.shift(n)-1
        out[f'zscore_{n}'] = np.log(c/c.shift(n))/(out.vol*np.sqrt(n))
    return out


def turn_targets(segments, length, k):
    """Stop target: a peak in [t, t+k]. Resume target: a confirmed trough in [t, t+k]."""
    stop, resume = np.zeros(length, dtype=bool), np.zeros(length, dtype=bool)
    for segment in segments:
        stop[max(segment['peak']-k, 0):segment['peak']+1] = True
        if not segment['censored']:
            resume[max(segment['trough']-k, 0):segment['trough']+1] = True
    return stop, resume


def last_known_pivot(segments):
    pivots = [s['peak'] for s in segments] + [s['trough'] for s in segments if not s['censored']]
    return max(pivots)


def leg_masks(segments, length):
    """Falling legs P+1..T; rising legs T+1..next P (to the end after the last trough)."""
    falling, rising = np.zeros(length, dtype=bool), np.zeros(length, dtype=bool)
    for number, segment in enumerate(segments):
        falling[segment['peak']+1:segment['trough']+1] = True
        if segment['censored']:
            continue
        end = segments[number+1]['peak'] if number+1 < len(segments) else length-1
        rising[segment['trough']+1:end+1] = True
    return falling, rising


def next_turn_distance(turns, length):
    """Sessions from t to the first turn at or after t; NaN if none."""
    out = np.full(length, np.nan)
    turns = np.sort(np.asarray(turns, dtype=int))
    after = np.searchsorted(turns, np.arange(length), side='left')
    found = after < len(turns)
    out[found] = turns[after[found]]-np.arange(length)[found]
    return out


@lru_cache(maxsize=8)
def shift_index(n):
    return (np.arange(n)[None, :]-np.arange(n)[:, None]) % n


def shift_hit_rates(signal, target):
    """Hit rate of every circular shift of the signal; row j equals np.roll(signal, j)."""
    shifted = signal[shift_index(len(signal))]
    return (shifted & target[None, :]).sum(axis=1)/signal.sum()


def statistics(signal, target, tercile, timing):
    """Rates, volatility-matched base, lifts, all-shift control and timing shares."""
    count, hits = int(signal.sum()), int((signal & target).sum())
    base = float(target.mean())
    tercile_base = {j: float(target[tercile == j].mean()) for j in range(3)}
    expected = float(np.mean([tercile_base[j] for j in tercile[signal]])) if count else np.nan
    row = dict(eval_sessions=len(signal), signals=count, hits=hits, hit_rate=hits/count if count else np.nan,
               base_rate=base, vol_matched_base=expected,
               tercile_base_low=tercile_base[0], tercile_base_mid=tercile_base[1], tercile_base_high=tercile_base[2])
    row['lift_base'] = row['hit_rate']/base if count and base else np.nan
    row['lift_vol_matched'] = row['hit_rate']/expected if count and expected else np.nan
    if count:
        rates = shift_hit_rates(signal, target)
        row.update(shift_p975=float(np.quantile(rates, .975)), shift_p50=float(np.quantile(rates, .5)),
                   share_shifts_at_least=float((rates >= row['hit_rate']-1e-12).mean()))
        for name in ('hit', 'late', 'early', 'false_alarm'):
            row[f'timing_{name}'] = float((timing[signal] == name).mean())
    return row


def timing_classes(target, inside_opposite_leg, distance, k):
    """Precedence: hit, late (already inside the leg it should anticipate), early, false alarm."""
    return np.where(target, 'hit', np.where(inside_opposite_leg, 'late',
                    np.where(distance <= 10, 'early', 'false_alarm')))


def legs_table(segments, sessions, series, x):
    """Leg lengths and hindsight hazard rows; only fully known legs."""
    leg_rows, hazard_rows = [], []
    for number, segment in enumerate(segments):
        if segment['censored']:
            continue
        legs = [('falling', segment['peak'], segment['trough'])]
        if number+1 < len(segments):
            legs.append(('rising', segment['trough'], segments[number+1]['peak']))
        for leg, start, end in legs:
            leg_rows.append(dict(series=series, size=x, leg=leg, start=sessions[start], end=sessions[end], length=end-start))
            for t in range(start+1, end+1):
                hazard_rows.append(dict(series=series, size=x, leg=leg, session=sessions[t], age=t-start,
                                        turn_within_2=bool(end-t <= 2)))
    return leg_rows, hazard_rows


def era_of(dates):
    """Era label per date; empty string outside both eras."""
    labels = np.full(len(dates), '', dtype=object)
    for era, (start, stop) in oracle.ERAS.items():
        labels[np.asarray((dates >= start) & (dates < stop))] = era
    return labels


def decide(stats):
    """Section 5, applied mechanically."""
    chosen = stats.loc[stats.level.eq('primary') & stats.k.eq(PRIMARY_K)]
    passes = (chosen.signals.ge(MIN_SIGNALS) & chosen.hit_rate.ge(MIN_LIFT*chosen.vol_matched_base)
              & chosen.hit_rate.ge(MIN_LIFT*chosen.base_rate) & chosen.hit_rate.gt(chosen.shift_p975))
    chosen = chosen.assign(passes=passes)
    both = chosen.groupby(['series', 'size', 'direction', 'predictor']).passes.agg(lambda v: bool(v.all() and len(v) == 2))
    out = {}
    for (series, x), part in both.groupby(level=['series', 'size']):
        part = part.droplevel(['series', 'size'])
        stop = sorted(part.loc['stop'][part.loc['stop']].index)
        resume = sorted(part.loc['resume'][part.loc['resume']].index)
        out[f'{series}|{x}'] = dict(stop_passing=stop, resume_passing=resume, rtl_test_worth_designing=bool(stop and resume))
    primary = [k for k, v in out.items() if k.startswith('roll_adjusted') and v['rtl_test_worth_designing']]
    raw = [k for k, v in out.items() if k.startswith('raw') and v['rtl_test_worth_designing']]
    return dict(by_series_size=out, summary=dict(
        sizes_worth_rtl_test=[k.split('|')[1] for k in primary],
        raw_series_agrees=[k.split('|')[1] for k in primary] == [k.split('|')[1] for k in raw],
        min_signals=MIN_SIGNALS, min_lift=MIN_LIFT, k=PRIMARY_K))


def main():
    assert oracle.text_digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol hash mismatch: no statistics computed'
    inputs = oracle.check_provenance()
    inputs[str(PROTOCOL)+' (CRLF-normalized)'] = PROTOCOL_SHA256
    inputs[str(oracle.__file__)] = prior.digest(oracle.__file__)
    print('Frozen protocol and source hashes verified.', flush=True)
    STUDY.mkdir(parents=True, exist_ok=True)
    daily, switches = oracle.load_daily()
    sessions = daily.index
    eras = era_of(sessions)
    calibration = np.asarray(sessions < CALIBRATION_END)
    closes = {'roll_adjusted': oracle.roll_adjusted_closes(daily, switches).to_numpy(), 'raw': daily.close.to_numpy(dtype=float)}
    stat_rows, cutoff_rows, leg_rows, hazard_rows, panels = [], [], [], [], []
    for series, c in closes.items():
        frame = features(c)
        valid = frame.notna().all(axis=1).to_numpy()
        vol_cut = np.quantile(frame.vol[valid & calibration], [1/3, 2/3])
        tercile = np.searchsorted(vol_cut, frame.vol.to_numpy(), side='right')
        signals = {}
        for family in FAMILIES:
            for n in LOOKBACKS:
                values = frame[f'{family}_{n}'].to_numpy()
                for level, (high, low) in LEVELS.items():
                    top, bottom = np.quantile(values[valid & calibration], [high, low])
                    cutoff_rows.append(dict(series=series, predictor=f'{family}_{n}', level=level,
                                            stop_cutoff=float(top), resume_cutoff=float(bottom),
                                            calibration_sessions=int((valid & calibration).sum())))
                    signals[('stop', f'{family}_{n}', level)] = valid & (values >= top)
                    signals[('resume', f'{family}_{n}', level)] = valid & (values <= bottom)
        panel = frame.assign(session=sessions, series=series, vol_tercile=tercile, valid=valid)
        for x in SIZES:
            segments = oracle.zigzag(c, x)
            falling, rising = leg_masks(segments, len(c))
            peaks = [s['peak'] for s in segments]
            troughs = [s['trough'] for s in segments if not s['censored']]
            distance = {'stop': next_turn_distance(peaks, len(c)), 'resume': next_turn_distance(troughs, len(c))}
            inside = {'stop': falling, 'resume': rising}
            last = last_known_pivot(segments)
            legs, hazards = legs_table(segments, sessions, series, x)
            leg_rows.extend(legs)
            hazard_rows.extend(hazards)
            for k in KS:
                stop_target, resume_target = turn_targets(segments, len(c), k)
                target = {'stop': stop_target, 'resume': resume_target}
                evaluable = valid & (np.arange(len(c)) <= last-k)
                for direction in ('stop', 'resume'):
                    timing = timing_classes(target[direction], inside[direction], distance[direction], k)
                    if k == PRIMARY_K:
                        panel[f'{direction}_target_{x}'] = target[direction]
                    for (sig_direction, predictor, level), signal in signals.items():
                        if sig_direction != direction:
                            continue
                        for era in oracle.ERAS:
                            chosen = evaluable & (eras == era)
                            row = statistics(signal[chosen], target[direction][chosen], tercile[chosen], timing[chosen])
                            stat_rows.append(dict(series=series, size=x, direction=direction, predictor=predictor,
                                                  level=level, k=k, era=era, **row))
            panel[f'last_known_pivot_{x}'] = sessions[last]
        for (direction, predictor, level), signal in signals.items():
            panel[f'{direction}|{predictor}|{level}'] = signal
        panels.append(panel)
        print(f'{series}: statistics complete.', flush=True)
    stats = pd.DataFrame(stat_rows)
    decision = decide(stats)
    hazard = pd.DataFrame(hazard_rows)
    hazard['era'] = era_of(pd.DatetimeIndex(hazard.session))
    hazard = hazard.loc[hazard.era.ne('')]
    bins = pd.IntervalIndex.from_tuples(AGE_BINS, closed='both')
    hazard['age_bin'] = pd.cut(hazard.age, bins).astype(str)
    hazard_summary = hazard.groupby(['series', 'size', 'era', 'leg', 'age_bin'], observed=True).turn_within_2.agg(
        sessions='size', turn_within_2='mean').reset_index()
    legs = pd.DataFrame(leg_rows)
    legs['era'] = era_of(pd.DatetimeIndex(legs.start))
    durations = legs.loc[legs.era.ne('')].groupby(['series', 'size', 'era', 'leg']).length.describe(
        percentiles=[.1, .25, .5, .75, .9]).reset_index()
    outputs = {'stats.csv': stats, 'cutoffs.csv': pd.DataFrame(cutoff_rows), 'durations.csv': durations,
               'hazard.csv': hazard_summary, 'legs.csv': legs, 'panel.csv': pd.concat(panels, ignore_index=True)}
    for name, frame in outputs.items():
        frame.to_csv(STUDY/name, index=False, float_format='%.15g')
    prior.save_json(STUDY/'decision.json', decision)
    assert oracle.text_digest(PROTOCOL) == PROTOCOL_SHA256
    generated = tuple(outputs) + ('decision.json',)
    prior.save_json(STUDY/'provenance.json', dict(
        study='Pullback and bounce warning statistics', protocol_sha256_crlf_normalized=PROTOCOL_SHA256,
        inputs_sha256=inputs, outputs_sha256={name: prior.digest(STUDY/name) for name in generated},
        sizes=SIZES, lookbacks=LOOKBACKS, ks=KS, levels=LEVELS, vol_window=VOL_WINDOW,
        timing_precedence='hit, late, early (<=10 sessions), false alarm', price_data_only=True,
        software=dict(numpy=np.__version__, pandas=pd.__version__), exploratory_only=True))
    view = stats.loc[stats.series.eq('roll_adjusted') & stats.level.eq('primary') & stats.k.eq(PRIMARY_K),
                     ['size', 'direction', 'predictor', 'era', 'signals', 'hit_rate', 'base_rate', 'vol_matched_base',
                      'lift_vol_matched', 'share_shifts_at_least']]
    print(view.to_string(index=False, float_format=lambda v: f'{v:.3f}'), flush=True)
    print(json.dumps(decision, indent=2), flush=True)


if __name__ == '__main__':
    main()
