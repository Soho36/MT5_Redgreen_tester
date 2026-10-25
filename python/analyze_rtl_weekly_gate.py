"""Execute the frozen RTL weekly signal gate study.

Weekly red/green breaks switch new M30 RTL trades off (sell) and on (buy).
Gate states change only at M30 bar closes; ledger omission by submission time.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import analyze_rtl_downtrend_oracle as oracle
import analyze_rtl_market_regimes as prior
import analyze_rtl_price_structure as structure

STUDY = oracle.ROOT / 'Reports/rtl_weekly_gate_20261025'
PROTOCOL = oracle.ROOT / 'docs/baseline/rtl-weekly-gate/PROTOCOL.md'
PROTOCOL_SHA256 = '28fccc0ca54af3621c295828f1272976728633d2e24024a7e764a668e704d2f6'
LAST_SESSION = pd.Timestamp('2026-09-30')
BAR = pd.Timedelta(minutes=30)
OHLC = ['open', 'high', 'low', 'close']
VARIANTS = (('roll_adjusted', 'touch'), ('roll_adjusted', 'week_close'),
            ('roll_adjusted', 'close_confirmed'), ('raw', 'touch'))
PRIMARY = ('roll_adjusted', 'touch')


def load_m30():
    m30 = pd.read_csv(prior.M30, parse_dates=['bar_time'])
    m30 = m30.loc[m30.bar_time.dt.normalize() <= LAST_SESSION].reset_index(drop=True)
    assert m30.bar_time.is_monotonic_increasing and m30.bar_time.is_unique
    return m30


def roll_adjust(m30, switches):
    """Ratio back-adjustment: last close before a switch date to its first open becomes a zero move."""
    dates = m30.bar_time.dt.normalize().to_numpy()
    factor = np.ones(len(m30))
    for switch in switches:
        first = int(np.flatnonzero(dates == np.datetime64(switch))[0])
        assert first > 0
        factor[:first] *= m30.open.iloc[first]/m30.close.iloc[first-1]
    out = m30.copy()
    for column in OHLC:
        out[column] = m30[column].to_numpy()*factor
    return out


def weekly_bars(m30):
    """Monday-to-Friday weeks by source date, with first/last M30 bar positions."""
    dates = m30.bar_time.dt.normalize()
    week = (dates-pd.to_timedelta(dates.dt.dayofweek, unit='D')).to_numpy()
    starts = np.flatnonzero(np.r_[True, week[1:] != week[:-1]])
    ends = np.r_[starts[1:]-1, len(m30)-1]
    high, low = m30.high.to_numpy(), m30.low.to_numpy()
    weeks = pd.DataFrame(dict(week=week[starts], first_bar=starts, last_bar=ends,
                              open=m30.open.to_numpy()[starts], close=m30.close.to_numpy()[ends],
                              high=[high[a:b+1].max() for a, b in zip(starts, ends)],
                              low=[low[a:b+1].min() for a, b in zip(starts, ends)]))
    weeks['colour'] = np.where(weeks.close > weeks.open, 'green', np.where(weeks.close < weeks.open, 'red', 'doji'))
    return weeks


def signals(m30, weeks, variant):
    """(bar position after whose close the signal applies, 'buy'/'sell', week index of W+1)."""
    high, low = m30.high.to_numpy(), m30.low.to_numpy()
    out = []
    for w in range(1, len(weeks)):
        prev, this = weeks.iloc[w-1], weeks.iloc[w]
        if prev.colour == 'doji':
            continue
        kind = 'sell' if prev.colour == 'green' else 'buy'
        a, b = int(this.first_bar), int(this.last_bar)
        if variant == 'close_confirmed':
            crossed = this.close < prev.low if kind == 'sell' else this.close > prev.high
            if crossed:
                out.append((b, kind, w))
            continue
        hits = np.flatnonzero(low[a:b+1] < prev.low) if kind == 'sell' else np.flatnonzero(high[a:b+1] > prev.high)
        if len(hits):
            out.append((a+int(hits[0]) if variant == 'touch' else b, kind, w))
    return out


def gate_off(events, n_bars):
    """off[j]: gate disabled after bar j's close. Starts enabled; same-state signals change nothing."""
    off = np.zeros(n_bars, dtype=bool)
    state, current = False, 0
    for position, kind, _ in sorted(events):
        off[current:position] = state
        state, current = kind == 'sell', position
    off[current:] = state
    return off


def last_completed_bar(bar_times, submitted):
    """Position of the last M30 bar whose close is at or before each submission."""
    closes = (bar_times+BAR).to_numpy()
    return np.searchsorted(closes, np.asarray(submitted, dtype='datetime64[ns]'), side='right')-1


def shift_nets(pnl, off):
    """Retained net for every circular shift k of the off mask (np.roll(off, k)), by exact correlation."""
    skipped = np.fft.irfft(np.fft.rfft(pnl)*np.conj(np.fft.rfft(off.astype(float))), n=len(pnl))
    return pnl.sum()-skipped


def off_periods(off, bar_times, weeks_of_bar):
    rows, start = [], None
    for j, value in enumerate(np.r_[off, False]):
        if value and start is None:
            start = j
        elif not value and start is not None:
            rows.append(dict(off_after_close=bar_times[start], on_after_close=bar_times[j] if j < len(off) else pd.NaT,
                             bars=j-start, weeks=int(weeks_of_bar[min(j, len(off)-1)]-weeks_of_bar[start])))
            start = None
    return rows


def evaluate(part, calendar, skip, bar_pnl, era_off):
    retained, omitted = part.loc[~skip], part.loc[skip]
    base, kept = prior.metrics(part, calendar), prior.metrics(retained, calendar)
    fraction = float(retained.holding_minutes.sum()/part.holding_minutes.sum())
    nets = shift_nets(bar_pnl, era_off)
    row = dict(trades=len(part), skipped_trades=int(skip.sum()), off_bar_share=float(era_off.mean()),
               baseline_net_dollars=base['net_dollars'], retained_net_dollars=kept['net_dollars'],
               skipped_net_dollars=float(omitted.net_dollars.sum()), gain_dollars=kept['net_dollars']-base['net_dollars'],
               gain_pct=(kept['net_dollars']-base['net_dollars'])/base['net_dollars']*100,
               baseline_mean_r=base['net_mean_r'], retained_mean_r=kept['net_mean_r'],
               skipped_mean_r=float(omitted.net_r.mean()) if len(omitted) else np.nan,
               losses_avoided=float(-omitted.net_dollars.clip(upper=0).sum()),
               profits_missed=float(omitted.net_dollars.clip(lower=0).sum()),
               baseline_daily_dd=base['daily_close_dd'], retained_daily_dd=kept['daily_close_dd'],
               baseline_closed_dd=base['closed_trade_dd'], retained_closed_dd=kept['closed_trade_dd'],
               retained_holding_fraction=fraction, static_net_dollars=base['net_dollars']*fraction,
               static_daily_dd=base['daily_close_dd']*fraction, shifts=len(nets),
               shift_net_p025=float(np.quantile(nets, .025)), shift_net_p50=float(np.quantile(nets, .5)),
               shift_net_p975=float(np.quantile(nets, .975)),
               share_shifts_net_at_least_rule=float((nets >= kept['net_dollars']-1e-6).mean()))
    assert np.isclose(nets[0], kept['net_dollars'], atol=1e-6)
    row['beats_baseline'] = bool(row['gain_dollars'] > 0)
    row['beats_shift_p975'] = bool(row['retained_net_dollars'] > row['shift_net_p975'])
    return row


def decide(rules):
    def pick(series, variant):
        return rules.loc[rules.series.eq(series) & rules.variant.eq(variant)]
    main = pick(*PRIMARY)
    promising = bool(len(main) == 2 and (main.retained_net_dollars > main.baseline_net_dollars).all()
                     and (main.retained_mean_r > main.baseline_mean_r).all() and main.beats_shift_p975.all())
    checks = {f'{s}|{v}_positive_both_eras': bool((pick(s, v).gain_dollars > 0).all())
              for s, v in VARIANTS if (s, v) != PRIMARY}
    label = 'promising' if promising and all(checks.values()) else 'fragile' if promising else 'not promising'
    return dict(primary=dict(promising=promising, **checks, label=label))


def main():
    assert oracle.text_digest(PROTOCOL) == PROTOCOL_SHA256, 'Frozen protocol hash mismatch: no outcomes computed'
    inputs = oracle.check_provenance()
    source = json.loads((structure.STUDY/'provenance.json').read_text(encoding='utf-8'))
    assert prior.digest(prior.M30) == source['inputs_sha256'][str(prior.M30)]
    inputs.update({str(PROTOCOL)+' (CRLF-normalized)': PROTOCOL_SHA256, str(prior.M30): prior.digest(prior.M30)})
    print('Frozen protocol and source hashes verified.', flush=True)
    STUDY.mkdir(parents=True, exist_ok=True)
    trades = structure.load_trades()
    trades = trades.loc[trades.primary].copy()
    daily, switches = oracle.load_daily()
    raw = load_m30()
    prices = {'roll_adjusted': roll_adjust(raw, switches), 'raw': raw}
    bar_times = raw.bar_time
    trades['bar'] = last_completed_bar(bar_times, trades.submitted)
    assert (trades.bar >= 0).all()
    week_rows, event_rows, period_rows, gates = [], [], [], {}
    for series, variant in VARIANTS:
        weeks = weekly_bars(prices[series])
        weeks_of_bar = np.repeat(np.arange(len(weeks)), (weeks.last_bar-weeks.first_bar+1).to_numpy())
        events = signals(prices[series], weeks, variant)
        off = gate_off(events, len(raw))
        gates[(series, variant)] = off
        if variant == 'touch':
            week_rows.extend(dict(series=series, **r) for r in weeks.to_dict('records'))
        before = np.r_[False, off[:-1]]
        for position, kind, w in events:
            event_rows.append(dict(series=series, variant=variant, week=weeks.week.iloc[w], kind=kind,
                                   bar_time=bar_times[position], effective_after=bar_times[position]+BAR,
                                   changed=bool(off[position] != before[position])))
        period_rows.extend(dict(series=series, variant=variant, **r) for r in off_periods(off, bar_times, weeks_of_bar))
    rows = []
    for era, (start, stop) in oracle.ERAS.items():
        calendar = daily.index[(daily.index >= start) & (daily.index < stop)]
        part = trades.loc[trades.era == era]
        closes = bar_times+BAR
        era_bars = np.flatnonzero(((closes >= start) & (closes < stop)).to_numpy())
        assert part.bar.between(era_bars[0], era_bars[-1]).all()
        bar_pnl = part.groupby('bar').net_dollars.sum().reindex(era_bars, fill_value=0.).to_numpy()
        for (series, variant), off in gates.items():
            skip = off[part.bar.to_numpy()]
            row = evaluate(part, calendar, skip, bar_pnl, off[era_bars])
            periods = [p for p in period_rows if p['series'] == series and p['variant'] == variant
                       and pd.Timestamp(start) <= p['off_after_close'] < pd.Timestamp(stop)]
            rows.append(dict(era=era, series=series, variant=variant, off_periods=len(periods),
                             median_off_weeks=float(np.median([p['weeks'] for p in periods])) if periods else np.nan, **row))
        print(f'{era}: {len(gates)} gate variants evaluated.', flush=True)
    rules = pd.DataFrame(rows)
    decision = decide(rules)
    labels = trades[['ticket', 'submitted', 'era', 'bar']].copy()
    for (series, variant), off in gates.items():
        labels[f'skip|{series}|{variant}'] = off[trades.bar.to_numpy()]
    outputs = {'rules.csv': rules, 'weeks.csv': pd.DataFrame(week_rows), 'events.csv': pd.DataFrame(event_rows),
               'periods.csv': pd.DataFrame(period_rows), 'trade_labels.csv': labels}
    for name, frame in outputs.items():
        frame.to_csv(STUDY/name, index=False, float_format='%.15g')
    prior.save_json(STUDY/'decision.json', decision)
    assert oracle.text_digest(PROTOCOL) == PROTOCOL_SHA256
    generated = tuple(outputs) + ('decision.json',)
    prior.save_json(STUDY/'provenance.json', dict(
        study='RTL weekly signal gate', protocol_sha256_crlf_normalized=PROTOCOL_SHA256, inputs_sha256=inputs,
        outputs_sha256={name: prior.digest(STUDY/name) for name in generated}, variants=VARIANTS, primary=PRIMARY,
        last_session=str(LAST_SESSION.date()), software=dict(numpy=np.__version__, pandas=pd.__version__),
        strategy_changed=False, exploratory_only=True,
        omission='counterfactual ledger omission by submission time, not an MT5 replay'))
    view = rules[['era', 'series', 'variant', 'off_periods', 'median_off_weeks', 'off_bar_share', 'skipped_trades',
                  'gain_pct', 'skipped_mean_r', 'retained_mean_r', 'baseline_mean_r', 'share_shifts_net_at_least_rule',
                  'beats_shift_p975']]
    print(view.to_string(index=False, float_format=lambda v: f'{v:.3f}'), flush=True)
    print(json.dumps(decision, indent=2), flush=True)


if __name__ == '__main__':
    main()
