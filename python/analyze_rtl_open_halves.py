"""Verified native replay comparisons and entry/exit attribution around cash open."""
import json
import sys
import numpy as np
import pandas as pd
import analyze_rtl_vwap_cross as cx
from analyze_rtl_vwap_slope import ROOT, CROSS, PERIODS, metrics, sha
from prepare_rtl_open_halves import RUN, OLD, DOC
from verify_exclude16_replay import DTYPE, maxdd, equity_metrics

SCOPES = dict(PERIODS)
SCOPES.update({str(y): (f'{y}-01-01', min(f'{y+1}-01-01', '2026-10-01')) for y in range(2010, 2027)})


def stats(t):
    p = t.net_dollars
    loss = -p[p < 0].sum()
    return dict(trades=len(t), gross_profit=float(t.trade_profit.clip(lower=0).sum()),
                gross_loss=float(-t.trade_profit.clip(upper=0).sum()), net=float(p.sum()),
                mean_net=float(p.mean()), mean_gross_r=float(t.gross_r.mean()), mean_net_r=float(t.net_r.mean()),
                pf=float(p[p > 0].sum()/loss) if loss else None,
                wins=int(p.gt(0).sum()), stops=int(t.stop.sum()))


def half(s):
    m = s.dt.hour*60+s.dt.minute
    return (m//30*30).map(lambda x: f'{x//60:02d}:{x%60:02d}')


def origin(s, dates):
    m = s.dt.hour*60+s.dt.minute
    return pd.Series(np.select([s.dt.normalize().lt(dates), m.lt(960), m.lt(990), m.lt(1020)],
                     ['prior date', 'before 16:00', '16:00-16:30', '16:30-17:00'], default='17:00+'), index=s.index)


def load_baseline():
    tag = 'ex16_20261101_rtl_base_all'
    done = json.loads((OLD / (tag+'.completed.json')).read_text())
    for n, h in done['outputs'].items():
        if n.endswith('.csv'):
            assert sha(OLD/n) == h
    t = cx.economics(cx.parse_report(OLD/(tag+'.htm'), cx.INSTRUMENTS['NQ']['symbol']), cx.INSTRUMENTS['NQ'])
    ledger = pd.read_csv(OLD/f'rtlvwap_{tag}_1.00.csv', sep='\t', encoding='utf-16').set_index('ticket').loc[t.ticket]
    np.testing.assert_allclose(ledger.trade_profit, t.trade_profit, rtol=0, atol=1e-8)
    for c in ('entry_time', 'exit_time'):
        assert np.array_equal(pd.to_datetime(ledger[c]).to_numpy(), t[c].to_numpy())
    return t


def describe():
    t = load_baseline()
    t['stop'] = t.exit_comment.fillna('').str.startswith('sl ')
    t['entry_half'] = half(t.entry_time)
    t['submitted_half'] = half(t.submitted)
    t['exit_half'] = half(t.exit_time)
    t['entry_origin'] = origin(t.entry_time, t.exit_time.dt.normalize())
    t['order_origin'] = origin(t.submitted, t.exit_time.dt.normalize())
    rows, cohorts, origins, matrices, transitions = [], [], [], [], []
    for period, (start, end) in SCOPES.items():
        p = t[t.session.ge(start) & t.session.lt(end)]
        for field in ('entry_half', 'submitted_half', 'exit_half'):
            for key, g in p.groupby(field):
                rows.append(dict(period=period, basis=field, window=key, **stats(g)))
        for lo, hi, name in [(960,990,'16:00-16:30'), (990,1020,'16:30-17:00'), (1020,1080,'17:00-18:00')]:
            minute = p.exit_time.dt.hour*60+p.exit_time.dt.minute
            exits = p[minute.ge(lo) & minute.lt(hi)]
            for field in ('entry_origin', 'order_origin'):
                for key, g in exits.groupby(field):
                    origins.append(dict(period=period, exit_window=name, basis=field, origin=key, **stats(g)))
                assert sum(len(g) for _, g in exits.groupby(field)) == len(exits)
        m = p.exit_time.dt.hour*60+p.exit_time.dt.minute
        for (ex, en), g in p[m.ge(960)&m.lt(1080)].groupby(['exit_half','entry_half']):
            matrices.append(dict(period=period, exit_half=ex, entry_half=en, **stats(g)))
        for (en, sub), g in p.groupby(['entry_origin','order_origin']):
            transitions.append(dict(period=period, entry_origin=en, order_origin=sub, **stats(g)))
        opening = p.session + pd.Timedelta(minutes=990)
        held = p[p.entry_time.lt(opening) & p.exit_time.ge(opening)].copy()
        held['minutes_after_open'] = (held.exit_time - (held.session + pd.Timedelta(minutes=990))).dt.total_seconds()/60
        for key, g in [('ALL',held), *list(held.groupby('entry_origin'))]:
            rec = dict(period=period, origin=key, **stats(g))
            for lo, hi, label in [(0,5,'0_5'), (5,15,'5_15'), (15,30,'15_30'), (30,60,'30_60')]:
                hit = g.stop & g.minutes_after_open.ge(lo) & g.minutes_after_open.lt(hi)
                rec['stops_'+label] = int(hit.sum())
                rec['stop_net_'+label] = float(g.loc[hit,'net_dollars'].sum())
            rec['winners_exit17'] = int((g.exit_time.dt.hour.eq(17)&g.net_dollars.gt(0)).sum())
            cohorts.append(rec)
    for name, values in [('half_hour_outcomes',rows), ('exit_origins',origins), ('entry_exit_matrix',matrices),
                         ('opening_cohorts',cohorts), ('order_fill_origins',transitions)]:
        pd.DataFrame(values).to_csv(RUN/(name+'.csv'),index=False)
    t.to_csv(RUN/'baseline_attributed_trades.csv',index=False)
    print('Baseline trades reconciled:', len(t), flush=True)
    print(pd.DataFrame(origins).query("period == '2016-26' and basis == 'entry_origin'").to_string(index=False), flush=True)
    print(pd.DataFrame(cohorts).query("period == '2016-26'").to_string(index=False), flush=True)


def verify():
    manifest = json.loads((RUN/'manifest.json').read_text())
    assert sha(DOC/'PROTOCOL.md') == manifest['protocol_sha256']
    for n,h in manifest['prepared_sha256'].items():
        assert sha(RUN/n) == h, n
    cal = pd.read_csv(CROSS/'calendars.csv',parse_dates=['session'])
    cal = pd.DatetimeIndex(cal.loc[cal.instrument.eq('NQ'),'session']).sort_values()
    panel = pd.read_csv(CROSS/'features_NQ.csv',float_precision='round_trip')
    panel.index = pd.to_datetime(panel.bar_time)
    rows, checks = [], []
    for job in manifest['jobs']:
        tag, arm = job['tag'], job['arm']
        done = json.loads((RUN/(tag+'.completed.json')).read_text())
        for n,h in done['outputs'].items():
            assert sha(RUN/n) == h, n
        lp = RUN/f'rtlvwap_{tag}_1.00.csv'
        if arm in ('control','skip_both'):
            suffix = 'all' if arm == 'control' else 'skip'
            assert lp.read_bytes() == (OLD/f'rtlvwap_ex16_20261101_rtl_base_{suffix}_1.00.csv').read_bytes(), arm
        t = cx.economics(cx.parse_report(RUN/(tag+'.htm'),cx.INSTRUMENTS['NQ']['symbol']),cx.INSTRUMENTS['NQ'])
        ledger = pd.read_csv(lp,sep='\t',encoding='utf-16').set_index('ticket').loc[t.ticket]
        assert len(ledger) == len(t)
        np.testing.assert_allclose(ledger.trade_profit,t.trade_profit,rtol=0,atol=1e-7)
        np.testing.assert_allclose((t.exit_price-t.fill_price)*2,t.trade_profit,rtol=0,atol=1e-7)
        np.testing.assert_allclose(ledger.candle_range,(t.requested_price-t.original_sl),rtol=0,atol=1e-7)
        for c in ('entry_time','exit_time'):
            assert np.array_equal(pd.to_datetime(ledger[c]).to_numpy(),t[c].to_numpy())
        assert (t.submitted <= t.entry_time).all() and (t.entry_time <= t.exit_time).all()
        stat = pd.read_csv(RUN/f'rtlvwap_{tag}_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
        assert stat.trades == len(t) and abs(stat.net_profit-t.trade_profit.sum()) < 1e-6
        decisions = pd.read_csv(RUN/f'vwap_decisions_{tag}.csv',sep='\t',encoding='cp1252')
        assert decisions.blocked.eq(0).all()
        for times in (t.submitted,pd.to_datetime(decisions.time)):
            minutes = times.dt.hour*60+times.dt.minute
            assert not (minutes.ge(960)&minutes.lt(990)).any() if job['pre'] else True
            assert not (minutes.ge(990)&minutes.lt(1020)).any() if job['post'] else True
        di = decisions.copy()
        di.index = pd.to_datetime(di.time)
        accepted = di.reindex(t.submitted.dt.floor('30min'))
        assert accepted.blocked.eq(0).all()
        signals = panel.reindex(pd.to_datetime(accepted.signal_bar)).reset_index(drop=True)
        good = signals.high.notna().to_numpy()
        assert t.submitted.loc[~good].ge('2026-10-01').all()
        assert signals.close.loc[good].lt(signals.open.loc[good]).all()
        for tc,sc in [('requested_price','high'),('original_sl','low')]:
            np.testing.assert_allclose(t.loc[good,tc],signals.loc[good,sc],rtol=0,atol=1e-7)
        data = np.memmap(RUN/f'window_equity_{tag}.bin',dtype=DTYPE,mode='r')
        assert (np.diff(data['time']) >= 0).all()
        assert abs(data['balance'][-1]-500000-t.trade_profit.sum()) < 1e-6
        assert abs(data['equity'][-1]-data['balance'][-1]) < 1e-7
        grossdd = maxdd(data['equity'])
        assert abs(grossdd-stat.equity_dd) < 1e-6
        exits = np.sort(t.exit_time.to_numpy().astype('datetime64[s]').astype(np.int64))
        for period,(start,end) in SCOPES.items():
            p = t[t.session.ge(start)&t.session.lt(end)]
            days = cal[(cal>=start)&(cal<end)]
            em = equity_metrics(data,start,end,exits)
            rows.append(dict(arm=arm,period=period,**metrics(p,days),**em,
                             fills_pre=int((p.entry_time.dt.hour.eq(16)&p.entry_time.dt.minute.lt(30)).sum()),
                             fills_post=int((p.entry_time.dt.hour.eq(16)&p.entry_time.dt.minute.ge(30)).sum())))
        t.to_csv(RUN/(arm+'_trades.csv'),index=False)
        checks.append(dict(arm=arm,trades=len(t),control_byte_identical=arm in ('control','skip_both'),
                           native_gross_equity_dd=float(stat.equity_dd),observed_gross_equity_dd=grossdd,
                           decisions=len(decisions),equity_rows=len(data)))
        del data
        print('Verified',arm,len(t),flush=True)
    pd.DataFrame(rows).to_csv(RUN/'replay_metrics.csv',index=False)
    (RUN/'verification.json').write_text(json.dumps(dict(all_passed=True,checks=checks,code_sha256=sha(__file__)),indent=2))
    print(pd.DataFrame(rows).query("period in ['2016-19','2020-26','2016-26']").to_string(index=False),flush=True)


if __name__ == '__main__':
    describe() if len(sys.argv)>1 and sys.argv[1]=='describe' else verify()

