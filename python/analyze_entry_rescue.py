"""Rejected-entry rescue: a buy limit at the level for W minutes when the buy stop is rejected.

Protocol: docs/baseline/entry-rescue/PROTOCOL.md (fixed before results).
Usage: python analyze_entry_rescue.py validate | analyze
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np
import pandas as pd

import rtl_weekly_engine as e
from rtl_weekly_engine import CUTOFF, is_signal, low_first, path, stamp

ROOT = e.ROOT
OUT = ROOT / 'Reports/entry_rescue_20261113'
PROTOCOL = ROOT / 'docs/baseline/entry-rescue/PROTOCOL.md'
MINUTES_CACHE = ROOT / 'Reports/rtl_weekly_flatten_20261027/minutes.npz'
GG_EA = ROOT / 'Reports/gg_vwap_ea_20261030'
LABELS = GG_EA / 'rtl_vwap_replay_20261026_features.csv'
LAST_DATE = 20260930
COST = 1.05
TICK = 0.25
SEED = 20261113
DRAWS = 10000
WINDOWS = (None, 1, 2, 5, 25)
ERAS = {'2010-15': ('2010-01-01', '2016-01-01'), '2016-19': ('2016-01-01', '2020-01-01'),
        '2020-26': ('2020-01-01', '2026-10-01')}
STRATEGIES = {'RTL': 'red', 'GG': 'green'}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------ engine copy + rescue

def simulate(bars, rr=1.0, cutoffs=None, last_date=None, signal='red', signal_skips=None, rescue=None):
    """simulate_m30_ea (no intrabar TP, no signal_stops, no blocked minutes) plus the rescue.

    rescue=None reproduces the engine. rescue=W places a buy limit at the rejected level
    for W clock minutes instead of skipping the signal.
    """
    cutoffs = cutoffs or {}
    date, day, minute = bars['date'], bars['day'], bars['minute']
    o, h, l, c = bars['o'], bars['h'], bars['l'], bars['c']
    n = len(o) if last_date is None else int(np.searchsorted(date, last_date, side='right'))
    slot = day * 48 + minute // 30
    tmin = day * 1440 + minute
    lf = low_first(o, c)
    trades, rejections = [], []
    pend = pos = None
    last_flat = prev_date = 0
    bar1 = cur = None
    cur_slot = signal_slot = -1

    def close(i, k, price, why):
        nonlocal pos
        trades.append({**pos, 'exit_time': stamp(day[i], minute[i], k), 'exit_price': price, 'reason': why})
        pos = None

    for i in range(n):
        new = slot[i] != cur_slot
        if new:
            signal_slot = cur_slot
            bar1 = cur
            cur = [o[i], h[i], l[i], c[i]]
            cur_slot = slot[i]
        else:
            cur[1] = max(cur[1], h[i]); cur[2] = min(cur[2], l[i]); cur[3] = c[i]
        if pend is not None and pend['kind'] == 'limit' and tmin[i] >= pend['expires']:
            pend = None
        if not new:
            quiet = (pend is None or (pend['kind'] == 'stop' and h[i] < pend['requested'])
                     or (pend['kind'] == 'limit' and l[i] > pend['requested']))
            if quiet and (pos is None or l[i] > pos['sl']):
                continue
        for k, p in enumerate(path(o[i], h[i], l[i], c[i], lf[i])):
            if pos is not None and p <= pos['sl']:
                close(i, k, pos['sl'], 'sl')
            if pend is not None:
                hit = p >= pend['requested'] if pend['kind'] == 'stop' else p <= pend['requested']
                if hit:
                    pos = {**pend, 'entry_time': stamp(day[i], minute[i], k), 'fill': pend['requested']}
                    pend = None
            if k or not new:
                continue
            bar_date, bar_min = date[i], (minute[i] // 30) * 30
            if prev_date and bar_date != prev_date and last_flat != prev_date:
                last_flat = prev_date
                if pos is not None:
                    close(i, k, p, 'fallback')
                pend = None
            prev_date = bar_date
            if bar_min >= cutoffs.get(bar_date, CUTOFF):
                if last_flat != bar_date:
                    last_flat = bar_date
                    if pos is not None:
                        close(i, k, p, 'flatten')
                    pend = None
                continue
            if pos is not None:
                if bar1[3] >= pos['fill'] + rr * (pos['fill'] - pos['sl']):
                    close(i, k, p, 'target')
                continue
            if bar_min < 60:
                pend = None
                continue
            if bar1 is not None and is_signal(bar1[0], bar1[3], signal):
                pend = None
                if signal_skips is not None and signal_slot in signal_skips:
                    continue
                if bar1[1] - bar1[2] <= 0:
                    continue
                submitted = stamp(day[i], minute[i], 0)
                if bar1[1] <= p:
                    rejections.append({'time': submitted, 'level': bar1[1], 'first_price': p,
                                       'overshoot_ticks': int(round((p - bar1[1]) / TICK)),
                                       'session_open': bool(i == 0 or tmin[i] - tmin[i - 1] > 5),
                                       'year': int(bar_date // 10000)})
                    if rescue is not None:
                        pend = {'submitted': submitted, 'requested': bar1[1], 'sl': bar1[2], 'kind': 'limit',
                                'expires': tmin[i] + rescue}
                    continue
                pend = {'submitted': submitted, 'requested': bar1[1], 'sl': bar1[2], 'kind': 'stop',
                        'expires': -1}
    if pos is not None:
        close(n - 1, 3, c[n - 1], 'end_of_data')
    return pd.DataFrame(trades), pd.DataFrame(rejections)


# ------------------------------------------------------------------ inputs

def gate_skips():
    """Signal slots the EA's VWAP gate skips, with the EA's label lookup (newest row
    available at the order bar, known only for that bar's session date)."""
    lab = pd.read_csv(LABELS, sep='\t')
    now_date = lab.available_epoch - lab.available_epoch % 86400
    known = (lab.known == 1) & (lab.session_epoch == now_date)
    skip = known & (lab.close < lab.vwap - lab.a20)
    bar = lab.bar_epoch[skip].to_numpy(np.int64)
    return set((bar // 86400 * 48 + (bar % 86400) // 1800).tolist())


def load():
    bars = e.load_minutes(MINUTES_CACHE)
    return bars, e.load_cutoffs()


def run(bars, cutoffs, strategy, gate, w, skips):
    tr, rj = simulate(bars, cutoffs=cutoffs, last_date=LAST_DATE, signal=STRATEGIES[strategy],
                      signal_skips=skips if gate else None, rescue=w)
    return tr, rj


# ------------------------------------------------------------------ validation

def mt5_ledger(name):
    d = pd.read_csv(GG_EA / name, sep='\t', encoding='utf-16')
    t = pd.to_datetime(d.entry_time, format='%Y.%m.%d %H:%M:%S')
    return t[t < pd.Timestamp('2026-10-01')].reset_index(drop=True)


def validate():
    bars, cutoffs = load()
    skips = gate_skips()
    report = {}
    for strategy, sig in STRATEGIES.items():
        for gate in (False, True):
            ref, _ = e.simulate_m30_ea(bars, cutoffs=cutoffs, last_date=LAST_DATE, signal=sig,
                                       signal_skips=skips if gate else None)
            mine, rj = run(bars, cutoffs, strategy, gate, None, skips)
            cols = ['submitted', 'requested', 'sl', 'entry_time', 'fill', 'exit_time', 'exit_price', 'reason']
            same = len(ref) == len(mine) and ref[cols].reset_index(drop=True).equals(mine[cols].reset_index(drop=True))
            key = f'{strategy} gate {"on" if gate else "off"}'
            report[key] = {'engine_trades': len(ref), 'copy_trades': len(mine), 'identical': bool(same),
                           'rejections': len(rj)}
            print(key, report[key], flush=True)
            assert same, f'{key}: copy differs from the engine'
            if strategy == 'GG':
                ledger = mt5_ledger(f'rtlvwap_ggvwap_20261030_{"on" if gate else "off"}_1.00.csv')
                sim = pd.to_datetime(mine.entry_time).reset_index(drop=True)
                match = len(ledger) == len(sim) and (ledger.values == sim.values).all()
                report[key].update(mt5_trades=len(ledger), mt5_entry_times_identical=bool(match))
                if not match:
                    a, b = set(ledger), set(sim)
                    report[key].update(only_mt5=len(a - b), only_sim=len(b - a),
                                       first_only_mt5=str(min(a - b)) if a - b else None,
                                       first_only_sim=str(min(b - a)) if b - a else None)
                print(key, 'MT5:', {k: v for k, v in report[key].items() if 'mt5' in k or 'only' in k}, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2))
    return report


# ------------------------------------------------------------------ analysis

def with_r(tr):
    tr = tr.copy()
    tr['entry_time'] = pd.to_datetime(tr.entry_time)
    tr['net'] = (tr.exit_price - tr.fill) * e.POINT_VALUE - COST
    tr['risk'] = (tr.fill - tr.sl) * e.POINT_VALUE
    tr['r'] = tr.net / tr.risk
    tr['rescued'] = tr.kind.eq('limit')
    return tr


def era_of(t):
    t = pd.to_datetime(t)
    out = pd.Series('', index=t.index if hasattr(t, 'index') else None, dtype=object)
    for name, (lo, hi) in ERAS.items():
        out[(t >= lo) & (t < hi)] = name
    return out


def boot_ci(x, rng):
    x = np.asarray(x, float)
    if len(x) < 2:
        return (np.nan, np.nan)
    m = rng.choice(x, size=(DRAWS, len(x)), replace=True).mean(axis=1)
    return tuple(np.percentile(m, [2.5, 97.5]))


def summarize(tr, rng):
    rows = []
    for era in list(ERAS) + ['all']:
        t = tr if era == 'all' else tr[tr.era == era]
        for group, g in (('all trades', t), ('normal', t[~t.rescued]), ('rescued', t[t.rescued])):
            lo, hi = boot_ci(g.r, rng) if group == 'rescued' else (np.nan, np.nan)
            rows.append({'era': era, 'group': group, 'trades': len(g), 'net_dollars': round(g.net.sum(), 2),
                         'mean_net_r': g.r.mean() if len(g) else np.nan, 'r_ci_lo': lo, 'r_ci_hi': hi,
                         'win_rate': (g.net > 0).mean() if len(g) else np.nan})
    return rows


def analyze():
    bars, cutoffs = load()
    skips = gate_skips()
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    summary, rescued_rows, rejection_rows, compare = [], [], [], []
    for strategy in STRATEGIES:
        for gate in (True, False):
            gname = 'on' if gate else 'off'
            base_tr, base_rj = run(bars, cutoffs, strategy, gate, None, skips)
            base = with_r(base_tr.assign(kind='stop'))
            base['era'] = era_of(base.entry_time).values
            rj = base_rj.copy()
            rj['strategy'], rj['gate'] = strategy, gname
            rejection_rows.append(rj)
            base_keys = set(base.entry_time)
            for w in WINDOWS:
                if w is None:
                    tr = base
                else:
                    t, _ = run(bars, cutoffs, strategy, gate, w, skips)
                    tr = with_r(t)
                    tr['era'] = era_of(tr.entry_time).values
                for row in summarize(tr, rng):
                    summary.append({'strategy': strategy, 'gate': gname, 'window_min': w or 0, **row})
                if w is not None:
                    resc = tr[tr.rescued].copy()
                    resc['strategy'], resc['gate'], resc['window_min'] = strategy, gname, w
                    sub = pd.to_datetime(resc.submitted)
                    lookup = rj.assign(time=pd.to_datetime(rj.time)).set_index('time')
                    resc['overshoot_ticks'] = lookup.overshoot_ticks.reindex(sub).to_numpy()
                    resc['session_open'] = lookup.session_open.reindex(sub).to_numpy()
                    rescued_rows.append(resc)
                    displaced = base[~base.entry_time.isin(set(tr.entry_time))]
                    for era in list(ERAS) + ['all']:
                        b = base if era == 'all' else base[base.era == era]
                        v = tr if era == 'all' else tr[tr.era == era]
                        d = displaced if era == 'all' else displaced[displaced.era == era]
                        nrj = len(rj) if era == 'all' else int((era_of(rj.time).values == era).sum())
                        compare.append({'strategy': strategy, 'gate': gname, 'window_min': w, 'era': era,
                                        'rejections': nrj, 'rescued_fills': int(v.rescued.sum()),
                                        'fill_rate': v.rescued.sum() / nrj if nrj else np.nan,
                                        'base_trades': len(b), 'variant_trades': len(v),
                                        'displaced_base_trades': len(d), 'displaced_net': round(d.net.sum(), 2),
                                        'base_net': round(b.net.sum(), 2), 'variant_net': round(v.net.sum(), 2),
                                        'net_change': round(v.net.sum() - b.net.sum(), 2),
                                        'rescued_net': round(v[v.rescued].net.sum(), 2),
                                        'base_mean_r': b.r.mean(), 'variant_mean_r': v.r.mean()})
                print(strategy, gname, w, len(tr), flush=True)
    summary = pd.DataFrame(summary)
    compare = pd.DataFrame(compare)
    rescued = pd.concat(rescued_rows, ignore_index=True)
    rejections = pd.concat(rejection_rows, ignore_index=True)
    summary.to_csv(OUT / 'summary.csv', index=False)
    compare.to_csv(OUT / 'compare.csv', index=False)
    rescued.to_csv(OUT / 'rescued_trades.csv', index=False)
    rejections.to_csv(OUT / 'rejections.csv', index=False)
    buckets(rescued, rng).to_csv(OUT / 'buckets.csv', index=False)
    freq(rejections).to_csv(OUT / 'rejection_frequency.csv', index=False)
    audit = {'protocol_sha256': sha(PROTOCOL), 'program_sha256': sha(ROOT / 'python/analyze_entry_rescue.py'),
             'labels_sha256': sha(LABELS), 'last_date': LAST_DATE, 'seed': SEED, 'draws': DRAWS}
    (OUT / 'provenance.json').write_text(json.dumps(audit, indent=2))


def buckets(rescued, rng):
    r = rescued.copy()
    r['overshoot'] = pd.cut(r.overshoot_ticks, [-1, 2, 8, 10 ** 9], labels=['1-2 ticks', '3-8 ticks', '>8 ticks'])
    r['where'] = np.where(r.session_open, 'session open', 'between bars')
    rows = []
    for keys, g in r.groupby(['strategy', 'gate', 'window_min', 'overshoot'], observed=True):
        lo, hi = boot_ci(g.r, rng)
        rows.append(dict(zip(['strategy', 'gate', 'window_min', 'split'], keys), trades=len(g),
                         mean_net_r=g.r.mean(), r_ci_lo=lo, r_ci_hi=hi, net=round(g.net.sum(), 2)))
    for keys, g in r.groupby(['strategy', 'gate', 'window_min', 'where']):
        lo, hi = boot_ci(g.r, rng)
        rows.append(dict(zip(['strategy', 'gate', 'window_min', 'split'], keys), trades=len(g),
                         mean_net_r=g.r.mean(), r_ci_lo=lo, r_ci_hi=hi, net=round(g.net.sum(), 2)))
    return pd.DataFrame(rows)


def freq(rj):
    rj = rj.copy()
    t = pd.to_datetime(rj.time)
    rj['overshoot'] = pd.cut(rj.overshoot_ticks, [-1, 0, 2, 8, 10 ** 9], labels=['0 (at level)', '1-2', '3-8', '>8'])
    rows = []
    for (s, g), d in rj.groupby(['strategy', 'gate']):
        td = pd.to_datetime(d.time)
        recent = d[td >= '2025-01-01']
        weeks = (pd.Timestamp('2026-10-01') - pd.Timestamp('2025-01-01')).days / 7
        rows.append({'strategy': s, 'gate': g, 'rejections': len(d), 'per_year_2020_26': len(d[td >= '2020-01-01']) / 6.75,
                     'per_week_2025_26': len(recent) / weeks, 'session_open_share': d.session_open.mean(),
                     **{f'overshoot {k}': v for k, v in d.overshoot.value_counts(normalize=True).sort_index().items()}})
    return pd.DataFrame(rows)


if __name__ == '__main__':
    {'validate': validate, 'analyze': analyze}[sys.argv[1]]()
