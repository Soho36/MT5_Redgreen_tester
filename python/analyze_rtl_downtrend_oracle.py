"""Execute the frozen RTL downtrend crystal-ball study.

Hindsight daily downtrends, delayed copies and the live zigzag; ledger omission
only. Sets a ceiling for downtrend avoidance, not a tradable rule.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_rtl_market_regimes as prior
import analyze_rtl_price_structure as structure

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / 'Reports/rtl_downtrend_oracle_20261024'
PROTOCOL = ROOT / 'docs/baseline/rtl-downtrend-oracle/PROTOCOL.md'
PROTOCOL_SHA256 = 'a39d490acc8897adf206da557c1786d07adfeef1fb209ba3d6e5d3c73afa2ffa'
DAILY = structure.STUDY / 'features_d1_20.csv'
LAST_SESSION = pd.Timestamp('2026-09-30')
SIZES = (.02, .03, .05, .10)
DELAYS = (0, 1, 2, 3, 5, 10, 20)
RULES = tuple(f'oracle_d{d}' for d in DELAYS) + ('live_zigzag',)
SERIES = ('roll_adjusted', 'raw')
ERAS = prior.ERAS
DECISION_DELAY = 3


def text_digest(path):
    """SHA256 with CRLF normalized, so checkout line endings cannot break the freeze."""
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def roll_adjusted_closes(daily, switches):
    """Ratio back-adjustment: previous close to switch-session open becomes a zero return."""
    factor = np.ones(len(daily))
    for switch in switches:
        position = daily.index.get_loc(switch)
        assert position > 0
        factor[:position] *= daily.open.iloc[position]/daily.close.iloc[position-1]
    return pd.Series(daily.close.to_numpy(dtype=float)*factor, index=daily.index)


def zigzag(closes, x):
    """Frozen state machine; positions of peak, trough and both confirmations."""
    c = np.asarray(closes, dtype=float)
    state, high, low, current, segments = 0, 0, 0, None, []
    for i in range(1, len(c)):
        if state == 0:
            if c[i] >= c[high]:
                high = i
            if c[i] <= c[low]:
                low = i
            if c[i] <= c[high]*(1-x):
                state, current, low = -1, dict(peak=high, stop_confirm=i), i
            elif c[i] >= c[low]*(1+x):
                state, high = 1, i
        elif state == -1:
            if c[i] <= c[low]:
                low = i
            elif c[i] >= c[low]*(1+x):
                segments.append(dict(current, trough=low, resume_confirm=i, censored=False))
                state, high = 1, i
        else:
            if c[i] >= c[high]:
                high = i
            elif c[i] <= c[high]*(1-x):
                state, current, low = -1, dict(peak=high, stop_confirm=i), i
    if state == -1:
        segments.append(dict(current, trough=low, resume_confirm=None, censored=True))
    return segments


def skip_mask(segments, length, rule):
    """Session positions whose submitted trades are skipped."""
    mask = np.zeros(length, dtype=bool)
    for segment in segments:
        if rule == 'live_zigzag':
            first = segment['stop_confirm']+1
            last = length-1 if segment['censored'] else segment['resume_confirm']
        else:
            delay = int(rule.removeprefix('oracle_d'))
            first, last = segment['peak']+1+delay, segment['trough']+delay
        mask[first:min(last, length-1)+1] = True
    return mask


def max_dd(pnl):
    equity = np.r_[0., np.cumsum(pnl)]
    return float(np.max(np.maximum.accumulate(equity)-equity))


def shift_controls(pnl, hours, mask, actual_net, actual_dd):
    """Every circular shift of the session skip mask; row k equals np.roll(mask, k)."""
    n = len(mask)
    index = (np.arange(n)[None, :]-np.arange(n)[:, None]) % n
    keep = ~mask[index]
    kept = pnl[None, :]*keep
    net = kept.sum(axis=1)
    equity = np.c_[np.zeros(n), np.cumsum(kept, axis=1)]
    dd = (np.maximum.accumulate(equity, axis=1)-equity).max(axis=1)
    held = (hours[None, :]*keep).sum(axis=1)
    target = float(hours[~mask].sum())
    scale = np.divide(target, held, out=np.full(n, np.nan), where=held > 0)
    result = dict(shifts=n, shift_net_p025=float(np.quantile(net, .025)), shift_net_p50=float(np.quantile(net, .5)),
                  shift_net_p975=float(np.quantile(net, .975)),
                  share_shifts_net_at_least_rule=float((net >= actual_net-1e-9).mean()),
                  share_shifts_dd_at_most_rule=float((dd <= actual_dd+1e-9).mean()),
                  share_matched_shifts_net_at_least_rule=float((net*scale >= actual_net-1e-9).mean()),
                  share_matched_shifts_dd_at_most_rule=float((dd*scale <= actual_dd+1e-9).mean()))
    return result, net


def evaluate(part, calendar, era_positions, mask, session_pnl, session_hours):
    """Retained/skipped ledger, static control and exhaustive placement control."""
    skipped = mask[part.position.to_numpy()]
    retained, omitted = part.loc[~skipped], part.loc[skipped]
    base, kept = prior.metrics(part, calendar), prior.metrics(retained, calendar)
    era_mask = mask[era_positions]
    fraction = float(retained.holding_minutes.sum()/part.holding_minutes.sum())
    row = dict(sessions=len(calendar), skipped_sessions=int(era_mask.sum()),
               skipped_session_share=float(era_mask.mean()), trades=len(part), skipped_trades=int(skipped.sum()),
               baseline_net_dollars=base['net_dollars'], retained_net_dollars=kept['net_dollars'],
               skipped_net_dollars=float(omitted.net_dollars.sum()),
               gain_dollars=kept['net_dollars']-base['net_dollars'],
               gain_pct=(kept['net_dollars']-base['net_dollars'])/base['net_dollars']*100,
               baseline_mean_r=base['net_mean_r'], retained_mean_r=kept['net_mean_r'],
               skipped_mean_r=float(omitted.net_r.mean()) if len(omitted) else np.nan,
               losses_avoided=float(-omitted.net_dollars.clip(upper=0).sum()),
               profits_missed=float(omitted.net_dollars.clip(lower=0).sum()),
               baseline_daily_dd=base['daily_close_dd'], retained_daily_dd=kept['daily_close_dd'],
               baseline_closed_dd=base['closed_trade_dd'], retained_closed_dd=kept['closed_trade_dd'],
               retained_holding_fraction=fraction, static_net_dollars=base['net_dollars']*fraction,
               static_daily_dd=base['daily_close_dd']*fraction,
               retained_stress1_net_dollars=kept['stress1_net_dollars'],
               retained_stress2_net_dollars=kept['stress2_net_dollars'])
    controls, _ = shift_controls(session_pnl, session_hours, era_mask, kept['net_dollars'], kept['daily_close_dd'])
    row.update(controls)
    row['beats_baseline'] = bool(row['gain_dollars'] > 0)
    row['beats_shift_p975'] = bool(row['retained_net_dollars'] > row['shift_net_p975'])
    return row


def check_provenance():
    assert text_digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol hash mismatch: no outcomes computed'
    source = json.loads(structure.STUDY.joinpath('provenance.json').read_text(encoding='utf-8'))
    for name in ('trades.csv', 'features_d1_20.csv'):
        assert prior.digest(structure.STUDY/name) == source['outputs_sha256'][name], name
    assert prior.digest(prior.ROLLS) == source['inputs_sha256'][str(prior.ROLLS)]
    paths = (structure.STUDY/'trades.csv', DAILY, structure.STUDY/'provenance.json', prior.ROLLS,
             Path(prior.__file__), Path(structure.__file__), Path(__file__))
    hashes = {str(path): prior.digest(path) for path in paths}
    hashes[str(PROTOCOL)+' (CRLF-normalized)'] = PROTOCOL_SHA256
    return hashes


def load_daily():
    daily = pd.read_csv(DAILY, usecols=['bar_time', 'open', 'high', 'low', 'close'], parse_dates=['bar_time'])
    daily = daily.set_index('bar_time').loc[:LAST_SESSION]
    assert daily.index.is_unique and daily.index.is_monotonic_increasing and daily.index[-1] == LAST_SESSION
    rolls = pd.read_csv(prior.ROLLS, parse_dates=['date'])
    switches = pd.DatetimeIndex(rolls.loc[rolls.symbol.ne(rolls.symbol.shift()) & rolls.symbol.shift().notna(), 'date'])
    switches = switches[switches <= LAST_SESSION]
    assert switches.isin(daily.index).all()
    return daily, switches


def main():
    inputs = check_provenance()
    print('Frozen protocol and source hashes verified.', flush=True)
    STUDY.mkdir(parents=True, exist_ok=True)
    trades = structure.load_trades()
    trades = trades.loc[trades.primary].copy()
    daily, switches = load_daily()
    SESSIONS = daily.index
    closes = {'roll_adjusted': roll_adjusted_closes(daily, switches), 'raw': daily.close.astype(float)}
    positions_all = SESSIONS.get_indexer(trades.session)
    assert (positions_all >= 0).all()
    trades['position'] = positions_all
    segment_rows, mask_columns, yearly_rows, lag_rows = [], {}, [], []
    masks = {}
    for series in SERIES:
        for x in SIZES:
            segments = zigzag(closes[series].to_numpy(), x)
            for number, segment in enumerate(segments):
                peak, trough = segment['peak'], segment['trough']
                segment_rows.append(dict(series=series, size=x, segment=number, **segment,
                                         peak_session=str(SESSIONS[peak].date()), trough_session=str(SESSIONS[trough].date()),
                                         stop_confirm_session=str(SESSIONS[segment['stop_confirm']].date()),
                                         resume_confirm_session=(str(SESSIONS[segment['resume_confirm']].date())
                                                                 if segment['resume_confirm'] is not None else ''),
                                         decline_pct=(1-closes[series].iloc[trough]/closes[series].iloc[peak])*100,
                                         sessions_down=trough-peak,
                                         stop_lag=segment['stop_confirm']-peak,
                                         resume_lag=(segment['resume_confirm']-trough if segment['resume_confirm'] is not None else np.nan)))
            for rule in RULES:
                mask = skip_mask(segments, len(SESSIONS), rule)
                masks[(series, x, rule)] = mask
                mask_columns[f'{series}|{x}|{rule}'] = mask
            inside = pd.Series(masks[(series, x, 'oracle_d0')], index=SESSIONS)
            peaks = pd.Series(1, index=SESSIONS[[s['peak'] for s in segments]]) if segments else pd.Series(dtype=float)
            for year in range(2016, 2027):
                in_year = inside.loc[str(year)]
                yearly_rows.append(dict(series=series, size=x, year=year, sessions=len(in_year),
                                        downtrends_starting=int(peaks.loc[str(year)].sum()) if len(peaks) else 0,
                                        share_sessions_in_downtrend=float(in_year.mean())))
    segments_frame = pd.DataFrame(segment_rows)
    for (series, x), part in segments_frame.groupby(['series', 'size']):
        for era, (start, stop) in ERAS.items():
            chosen = part.loc[(part.peak_session >= start) & (part.peak_session < stop)]
            lag_rows.append(dict(series=series, size=x, era=era, downtrends=len(chosen),
                                 censored=int(chosen.censored.sum()),
                                 median_sessions_down=float(chosen.sessions_down.median()),
                                 median_stop_lag=float(chosen.stop_lag.median()), mean_stop_lag=float(chosen.stop_lag.mean()),
                                 median_resume_lag=float(chosen.resume_lag.median()),
                                 mean_resume_lag=float(chosen.resume_lag.mean())))
    print('Downtrends and skip masks built; computing outcomes and shift controls.', flush=True)
    rule_rows = []
    for era, (start, stop) in ERAS.items():
        calendar = SESSIONS[(SESSIONS >= start) & (SESSIONS < stop)]
        part = trades.loc[trades.era == era]
        assert part.session.isin(calendar).all()
        session_pnl = part.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.).to_numpy()
        session_hours = (part.groupby('session').holding_minutes.sum()/60).reindex(calendar, fill_value=0.).to_numpy()
        era_positions = SESSIONS.get_indexer(calendar)
        for (series, x, rule), mask in masks.items():
            row = evaluate(part, calendar, era_positions, mask, session_pnl, session_hours)
            assert np.isclose(row['retained_net_dollars']+row['skipped_net_dollars'], row['baseline_net_dollars'], atol=1e-6)
            rule_rows.append(dict(era=era, series=series, size=x, rule=rule, **row))
        print(f'{era}: {len(masks)} rules evaluated.', flush=True)
    rules = pd.DataFrame(rule_rows)
    decision = decide(rules)
    STUDY.joinpath('segments.csv').write_text(segments_frame.to_csv(index=False, float_format='%.15g'), encoding='utf-8')
    pd.DataFrame(mask_columns, index=SESSIONS.rename('session')).to_csv(STUDY/'masks.csv')
    for name, frame in (('rules.csv', rules), ('yearly.csv', pd.DataFrame(yearly_rows)), ('lags.csv', pd.DataFrame(lag_rows))):
        frame.to_csv(STUDY/name, index=False, float_format='%.15g')
    prior.save_json(STUDY/'decision.json', decision)
    assert text_digest(PROTOCOL) == PROTOCOL_SHA256
    generated = ('segments.csv', 'masks.csv', 'rules.csv', 'yearly.csv', 'lags.csv', 'decision.json')
    prior.save_json(STUDY/'provenance.json', dict(
        study='RTL downtrend crystal ball', protocol_sha256_crlf_normalized=PROTOCOL_SHA256, inputs_sha256=inputs,
        outputs_sha256={name: prior.digest(STUDY/name) for name in generated}, primary_eras=ERAS,
        sizes=SIZES, delays=DELAYS, last_session=str(LAST_SESSION.date()), roll_switches=len(switches),
        software=dict(numpy=np.__version__, pandas=pd.__version__), strategy_changed=False, exploratory_only=True,
        omission='counterfactual ledger omission by submission session, not an MT5 replay',
        placement='all circular shifts of the era session skip mask; shift zero is the rule itself'))
    view = rules.loc[rules.series.eq('roll_adjusted'), ['era', 'size', 'rule', 'skipped_session_share', 'gain_pct',
                                                        'skipped_mean_r', 'retained_mean_r', 'beats_shift_p975']]
    print(view.to_string(index=False, float_format=lambda v: f'{v:.3f}'), flush=True)
    print(json.dumps(decision['summary'], indent=2), flush=True)


def decide(rules):
    """Section 5 of the protocol, applied mechanically."""
    out, rows = {}, []
    for (series, x), part in rules.groupby(['series', 'size']):
        for era in ERAS:
            oracle = part.loc[part.era.eq(era) & part.rule.str.startswith('oracle')].copy()
            oracle['delay'] = oracle.rule.str.removeprefix('oracle_d').astype(int)
            oracle = oracle.sort_values('delay')
            first = oracle.iloc[0]
            not_gain = oracle.loc[~oracle.beats_baseline, 'delay']
            not_random = oracle.loc[~oracle.beats_shift_p975, 'delay']
            rows.append(dict(series=series, size=x, era=era,
                             ceiling_gain_dollars=float(first.gain_dollars), ceiling_gain_pct=float(first.gain_pct),
                             ceiling_mean_r_gain=float(first.retained_mean_r-first.baseline_mean_r),
                             ceiling_beats_shift_p975=bool(first.beats_shift_p975),
                             break_even_delay=int(not_gain.min()) if len(not_gain) else None,
                             random_equivalent_delay=int(not_random.min()) if len(not_random) else None))
        late_pass = [int(d) for d in DELAYS if d >= DECISION_DELAY and all(
            bool(r.beats_baseline and r.beats_shift_p975) for r in part.loc[part.rule.eq(f'oracle_d{d}')].itertuples())]
        live = part.loc[part.rule.eq('live_zigzag')]
        assert len(live) == len(ERAS)
        out[f'{series}|{x}'] = dict(late_delays_passing_both_eras=late_pass,
                                    live_zigzag_passes_both_eras=bool((live.beats_baseline & live.beats_shift_p975).all()))
    primary = {key: value for key, value in out.items() if key.startswith('roll_adjusted')}
    worthwhile = any(v['late_delays_passing_both_eras'] or v['live_zigzag_passes_both_eras'] for v in primary.values())
    raw_worthwhile = any(v['late_delays_passing_both_eras'] or v['live_zigzag_passes_both_eras']
                         for k, v in out.items() if k.startswith('raw'))
    return dict(rows=rows, by_series_size=out,
                summary=dict(further_downtrend_research_worthwhile=worthwhile, raw_series_agrees=worthwhile == raw_worthwhile,
                             decision_delay=DECISION_DELAY))


if __name__ == '__main__':
    main()
