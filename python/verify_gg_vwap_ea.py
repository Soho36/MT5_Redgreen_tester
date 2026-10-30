"""Check and summarise the MT5 replay of the VWAP gate on GG (prepare_gg_vwap_ea.py).

1. off: gate off, green signal candle. Pass = the GG baseline run's ledger byte for byte and its
   tester totals: the VWAP EA trades GG exactly like GG_runband.
2. on: every candidate's VWAP, A20, known and blocked flag follows the label file for its signal
   bar (same session, close < VWAP - A20), and no trade comes from a far-below signal.
3. Replay summary per era (submission sessions, $1.05 per trade, daily-close DD on the NQ
   calendar): baseline, ledger omission (must equal the GG test's retained curve) and the replay;
   plus RTL + GG in one account, RTL replayed by the EA check's file run.
Writes verification.json and summaries.csv in the run folder.
"""
import json

import numpy as np
import pandas as pd

import analyze_gg_vwap as gg
import analyze_rtl_vwap as av
import analyze_rtl_vwap_cross as cx
import build_rtl_vwap_features as vw
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / 'Reports' / 'gg_vwap_ea_20261030'
GG_TEST = ROOT / 'Reports' / 'gg_vwap_20261030'
RTL_REPLAY = ROOT / 'Reports' / 'rtl_vwap_ea_20261028' / 'vwapea_20261028_file.htm'
SYMBOL = 'MNQcontDTBNT20102026_2'
TOLERANCE = 1e-6   # the decision log prints 10 decimals
PERIODS = {'2010-15': ('2010-01-01', '2016-01-01'), '2016-19': ('2016-01-01', '2020-01-01'),
           '2020-26': ('2020-01-01', '2026-10-01'), '2016-26': ('2016-01-01', '2026-10-01')}
TOTALS = ('trades', 'net_profit', 'gross_profit', 'gross_loss', 'equity_dd', 'balance_dd')


def stats(path):
    return pd.read_csv(path, sep='\t', encoding='utf-16').iloc[0]


def trades_of(report, spec):
    frame = cx.economics(cx.parse_report(report, SYMBOL), spec)
    return frame.loc[frame.session < cx.END]


def check_off():
    tag = 'ggvwap_20261030_off'
    mine, base = RUN / f'rtlvwap_{tag}_1.00.csv', cx.YM_RUNS / 'runband_ymbase_20261023_gg_nq_1.00.csv'
    a, b = stats(RUN / f'rtlvwap_{tag}_1.00_stats.csv'), stats(cx.YM_RUNS / 'runband_ymbase_20261023_gg_nq_1.00_stats.csv')
    out = dict(trade_ledger_identical=mine.read_bytes() == base.read_bytes(),
               tester={k: dict(ea=float(a[k]), baseline=float(b[k])) for k in TOTALS},
               signal_candle=a.signal_candle, vwap_gate=int(a.vwap_gate))
    out['passed'] = bool(out['trade_ledger_identical'] and all(v['ea'] == v['baseline'] for v in out['tester'].values())
                         and a.signal_candle == 'green' and a.vwap_gate == 0)
    return out


def check_on(features):
    tag = 'ggvwap_20261030_on'
    d = pd.read_csv(RUN / f'vwap_decisions_{tag}.csv', sep='\t', encoding='cp1252')
    f = pd.read_csv(RUN / gg_features_name(), sep='\t', float_precision='round_trip')
    f.index = pd.to_datetime(f.bar_epoch, unit='s').dt.strftime('%Y.%m.%d %H:%M:%S')
    row = f.reindex(d.signal_bar)
    # The run goes on to 2026-10-23; labels end with September 2026, after which the gate is unknown.
    outside = row.bar_epoch.isna().to_numpy()
    assert (d.signal_bar[outside] > f.index[-1]).all(), 'signal bar missing inside the label file'
    session = pd.to_datetime(d.time, format='%Y.%m.%d %H:%M:%S').dt.normalize()
    known = (~outside & row.known.eq(1).to_numpy()
             & pd.to_datetime(row.session_epoch, unit='s').eq(session.to_numpy()).to_numpy())
    blocked = known & (row.close < row.vwap - row.a20).to_numpy()
    out = dict(candidates=len(d), known=dict(ea=int(d.known.sum()), file=int(known.sum()),
                                             mismatches=int((d.known.to_numpy() != known).sum())),
               blocked=dict(ea=int(d.blocked.sum()), file=int(blocked.sum()),
                            mismatches=int((d.blocked.to_numpy() != blocked).sum())))
    out['signal_bars_after_labels'] = int(outside.sum())
    out['max_signal_close_difference'] = float(np.abs(d.signal_close.to_numpy() - row.close.to_numpy())[~outside].max())
    for col in ('vwap', 'a20'):
        out[f'max_{col}_difference'] = float(np.abs(d[col].to_numpy()[known] - row[col].to_numpy()[known]).max())
    s = stats(RUN / f'rtlvwap_{tag}_1.00_stats.csv')
    out['ea_counts'] = {k: int(s[k]) for k in ('vwap_candidates', 'vwap_known', 'vwap_blocked')}
    replay = vw.label_trades(trades_of(RUN / f'{tag}.htm', gg.SPEC), features)
    out['replay_trades_from_far_below_signals'] = int(replay.distance.eq('far_below').sum())
    out['passed'] = bool(out['known']['mismatches'] == 0 and out['blocked']['mismatches'] == 0
                         and max(out['max_signal_close_difference'], out['max_vwap_difference'], out['max_a20_difference']) <= TOLERANCE
                         and out['ea_counts'] == dict(vwap_candidates=len(d), vwap_known=out['known']['ea'], vwap_blocked=out['blocked']['ea'])
                         and out['replay_trades_from_far_below_signals'] == 0)
    return out, replay


def gg_features_name():
    return next(j for j in json.loads((RUN / 'manifest.json').read_text())['jobs'] if j['gate'])['inputs_files'][0]


def metrics(frame, calendar):
    daily = frame.groupby('session').net_dollars.sum().reindex(calendar, fill_value=0.)
    assert frame.session.isin(calendar).all()
    ordered = frame.sort_values(['exit_time', 'entry_time', 'ticket']).net_dollars.to_numpy()
    wins, losses = frame.net_dollars[frame.net_dollars > 0].sum(), -frame.net_dollars[frame.net_dollars < 0].sum()
    return dict(trades=len(frame), net_dollars=float(frame.net_dollars.sum()), net_mean_r=float(frame.net_r.mean()),
                profit_factor=float(wins/losses), daily_close_dd=av.max_dd(daily.to_numpy()), closed_trade_dd=av.max_dd(ordered))


def main():
    features = gg.load_features()
    observed = gg.nq_calendar()
    verification = dict(off=check_off())
    verification['on'], replay = check_on(features)
    base = vw.label_trades(trades_of(cx.YM_RUNS / 'ymbase_20261023_gg_nq.htm', gg.SPEC), features)
    omission = base.loc[~base.distance.eq('far_below')]
    rtl_spec = dict(gg.SPEC, symbol=SYMBOL)
    rtl_base, rtl_replay = trades_of(cx.YM_RUNS / 'ymbase_20261023_rtl_nq.htm', rtl_spec), trades_of(RTL_REPLAY, rtl_spec)
    test = pd.read_csv(GG_TEST / 'summaries.csv')
    rows = []
    for period, (start, stop) in PERIODS.items():
        cal = observed[(observed >= start) & (observed < stop)]
        inside = lambda t: t.loc[(t.session >= start) & (t.session < stop)]
        curves = {'GG baseline': inside(base), 'GG ledger omission': inside(omission), 'GG replay': inside(replay),
                  'RTL + GG, no gate': pd.concat([inside(rtl_base), inside(base)]),
                  'RTL + GG, RTL replayed': pd.concat([inside(rtl_replay), inside(base)]),
                  'RTL + GG, both replayed': pd.concat([inside(rtl_replay), inside(replay)])}
        for curve, frame in curves.items():
            rows.append(dict(period=period, curve=curve, **metrics(frame, cal)))
        # The baseline and omission curves must equal the GG test's (2016-26 there is 'pooled').
        name = {'2016-26': 'pooled'}.get(period, period)
        for curve, saved in (('GG baseline', 'baseline'), ('GG ledger omission', 'retained')):
            ref = test.loc[test.period.eq(name) & test.curve.eq(saved)].iloc[0]
            mine = next(r for r in rows if r['period'] == period and r['curve'] == curve)
            assert mine['trades'] == ref.trades and np.isclose(mine['net_dollars'], ref.net_dollars, rtol=0, atol=1e-6) \
                and np.isclose(mine['daily_close_dd'], ref.daily_close_dd, rtol=0, atol=1e-6), (period, curve)
    summaries = pd.DataFrame(rows)
    summaries.to_csv(RUN / 'summaries.csv', index=False, float_format='%.10g')
    verification['baseline_and_omission_match_gg_test'] = True
    verification['passed'] = bool(verification['off']['passed'] and verification['on']['passed'])
    av.save_json(RUN / 'verification.json', cx.plain(verification))
    print(json.dumps(cx.plain({k: v for k, v in verification.items()}), indent=1)[:3000])
    print(summaries.to_string(index=False))
    assert verification['passed'], 'verification failed'


if __name__ == '__main__':
    main()
