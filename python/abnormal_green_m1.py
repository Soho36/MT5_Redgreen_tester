"""Full-history abnormal-green M1 breakout screen; see the frozen protocol."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from project_paths import PROJECT_ROOT as ROOT
from rtl_weekly_engine import load_minutes, load_cutoffs, low_first

SOURCE = Path(r'F:\DATABENTO\MNQ_16_YEARS\NQ_extended_20261114\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv')
RUN = ROOT / 'Reports/abnormal_green_m1_20261124'
DOC = ROOT / 'docs/baseline/abnormal-green-m1'
COST = 1.05
TICK = .25
POINT = 2.


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def detect(b, multiplier=10., lookback=20, cutoffs=None):
    if multiplier <= 0 or lookback < 1:
        raise ValueError('Positive multiplier and lookback required')
    cutoffs = {} if cutoffs is None else cutoffs
    t = b['day']*1440+b['minute']
    ranges = b['h']-b['l']
    reference = pd.Series(ranges).shift().rolling(lookback).mean().to_numpy()
    ratio = np.divide(ranges, reference, out=np.full(len(t), np.nan), where=reference>0)
    indices = np.flatnonzero((b['c']>b['o']) & (ratio >= multiplier))
    rows = []
    for i in indices:
        status = 'eligible'
        if b['date'][i-lookback] != b['date'][i] or t[i]-t[i-lookback] != lookback:
            status = 'nonconsecutive_reference'
        elif i+1 == len(t) or t[i+1] != t[i]+1 or b['date'][i+1] != b['date'][i]:
            status = 'missing_next_minute'
        elif b['minute'][i]+1 < 60 or b['minute'][i]+1 >= cutoffs.get(int(b['date'][i]), 1410):
            status = 'outside_entry_session'
        rows.append(dict(index=int(i), signal_time=str(pd.Timestamp(int(t[i])*60, unit='s')),
                         date=int(b['date'][i]), open=b['o'][i], high=b['h'][i], low=b['l'][i], close=b['c'][i],
                         range=ranges[i], prior20_mean=reference[i], ratio=ratio[i], eligibility=status))
    return pd.DataFrame(rows, columns=['index','signal_time','date','open','high','low','close','range','prior20_mean','ratio','eligibility'])


def simulate(b, signals, cutoffs=None, mode='directional', cost=COST):
    if mode not in ('directional','low_first','high_first'):
        raise ValueError(mode)
    cutoffs = {} if cutoffs is None else cutoffs
    t = b['day']*1440+b['minute']
    direction = low_first(b['o'], b['c']) if mode == 'directional' else None
    eligible = {int(r.index): r for r in signals.itertuples() if r.eligibility == 'eligible'}
    states = {i: 'not_processed' for i in eligible}
    pending = pos = None
    trades = []

    def mark(price):
        pnl = (price-pos['entry_price'])*POINT-cost
        pos['min_mark_net'] = min(pos['min_mark_net'], pnl)
        pos['max_mark_net'] = max(pos['max_mark_net'], pnl)
        pos['internal_dd'] = max(pos['internal_dd'], pos['max_mark_net']-pnl)

    def close(i, k, price, reason):
        nonlocal pos
        mark(price)
        gross = (price-pos['entry_price'])*POINT
        trades.append({**pos, 'exit_index':i, 'exit_time':str(pd.Timestamp(int(t[i])*60+k, unit='s')),
                       'exit_price':price, 'reason':reason, 'gross':gross, 'net':gross-cost,
                       'net_r':(gross-cost)/pos['risk_dollars']})
        pos = None

    for i in range(len(t)):
        signal = eligible.get(i-1)
        if pending is None and pos is None and signal is None:
            continue
        o,h,l,c = (float(b[k][i]) for k in 'ohlc')
        date = int(b['date'][i])
        cutoff = cutoffs.get(date,1410)
        stale = (pos is not None and pos['date'] != date) or (pending is not None and pending.date != date)
        if stale or b['minute'][i] >= cutoff:
            if pos is not None:
                pos['gap_during_trade'] |= bool(i and t[i]-t[i-1]>1)
                close(i,0,o,'fallback' if stale else 'flatten')
            if pending is not None:
                states[pending.index] = 'expired_session'
                pending = None
            if signal is not None:
                states[signal.index] = 'expired_session'
            continue
        if signal is not None:
            if pos is not None:
                states[signal.index] = 'busy'
            else:
                if pending is not None:
                    states[pending.index] = 'replaced'
                pending = signal
                states[signal.index] = 'pending'
        if pos is not None:
            pos['gap_during_trade'] |= bool(t[i]-t[i-1]>1)
            pos['exit_overlap'] |= l <= pos['sl'] and h >= pos['tp']
        lf = bool(direction[i]) if mode == 'directional' else mode == 'low_first'
        prices = (o,l,h,c) if lf else (o,h,l,c)
        for k,p in zip((0,20,40,59), prices):
            if pos is not None:
                if p <= pos['sl']:
                    close(i,k,min(pos['sl'],p) if k==0 else pos['sl'],'sl')
                elif p >= pos['tp']:
                    close(i,k,pos['tp'],'tp')
                else:
                    mark(p)
            if pending is not None and p >= pending.high:
                fill = max(p,pending.high) if k==0 else pending.high
                sl = pending.low-TICK
                pos = dict(signal_index=int(pending.index), signal_time=pending.signal_time, date=date,
                           entry_index=i, entry_time=str(pd.Timestamp(int(t[i])*60+k,unit='s')),
                           entry_price=fill, sl=sl, tp=fill+(fill-sl), risk_dollars=(fill-sl)*POINT,
                           ratio=pending.ratio, signal_range=pending.range,
                           wait_minutes=int(t[i]-t[pending.index]),
                           entry_overlap=bool(l<=sl), exit_overlap=bool(l<=sl and h>=fill+(fill-sl)),
                           gap_entry=bool(fill>pending.high), gap_during_trade=False,
                           min_mark_net=-cost,max_mark_net=-cost,internal_dd=0.)
                states[pending.index] = 'filled'
                pending = None
                # Continuous travel from entry through the segment endpoint can hit TP.
                if p >= pos['tp']:
                    close(i,k,pos['tp'],'tp')
                else:
                    mark(p)
    if pos is not None:
        close(len(t)-1,59,float(b['c'][-1]),'end_of_data')
    if pending is not None:
        states[pending.index] = 'expired_end_of_data'
    columns = ['signal_index','signal_time','date','entry_index','entry_time','entry_price','sl','tp','risk_dollars',
               'ratio','signal_range','wait_minutes','entry_overlap','exit_overlap','gap_entry','gap_during_trade',
               'min_mark_net','max_mark_net','internal_dd','exit_index','exit_time','exit_price','reason','gross','net','net_r']
    return pd.DataFrame(trades,columns=columns), states


def metrics(tr):
    balance = peak = dd = 0.
    for r in tr.itertuples():
        dd = max(dd, peak-(balance+r.min_mark_net), r.internal_dd)
        peak = max(peak,balance+r.max_mark_net)
        balance += r.net
    net = tr.net.astype(float)
    curve = np.r_[0.,net.cumsum()]
    loss = -net[net<0].sum()
    return dict(trades=len(tr), gross=float(tr.gross.sum()), net=float(net.sum()),
                win_pct=100*float(net.gt(0).mean()) if len(tr) else None,
                pf=float(net[net>0].sum()/loss) if loss else None,
                mean_net_r=float(tr.net_r.mean()) if len(tr) else None,
                closed_dd=float(np.max(np.maximum.accumulate(curve)-curve)), path_equity_dd=dd,
                stress1_net=float(net.sum()-len(tr)), stress2_net=float(net.sum()-2*len(tr)),
                overlap_trades=int((tr.entry_overlap.astype(bool)|tr.exit_overlap.astype(bool)).sum()),
                gap_trades=int(tr.gap_during_trade.astype(bool).sum()), gap_entries=int(tr.gap_entry.astype(bool).sum()),
                median_wait_minutes=float(tr.wait_minutes.median()) if len(tr) else None,
                max_wait_minutes=int(tr.wait_minutes.max()) if len(tr) else None,
                forced_exits=int(tr.reason.isin(['flatten','fallback','end_of_data']).sum()))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--out',type=Path,default=RUN)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    print('Loading complete raw source',args.source,flush=True)
    b=load_minutes(source=args.source)
    n=len(b['o']); t=b['day']*1440+b['minute']
    assert np.all(np.diff(t)>0)
    assert all(np.isfinite(b[k]).all() for k in 'ohlc')
    assert np.all(b['h']>=np.maximum(b['o'],b['c'])) and np.all(b['l']<=np.minimum(b['o'],b['c']))
    assert np.all(b['l']>0)
    assert all(np.allclose(b[k]/TICK,np.round(b[k]/TICK)) for k in 'ohlc')
    cutoffs=load_cutoffs()
    source_hash=sha(args.source)
    manifest=dict(source=str(args.source),source_sha256=source_hash,bars=n,
                  first=str(pd.Timestamp(int(t[0])*60,unit='s')),last=str(pd.Timestamp(int(t[-1])*60,unit='s')),
                  protocol_sha256=sha(DOC/'PROTOCOL.md'),code_sha256=sha(__file__),
                  cutoff_sha256=sha(ROOT/'mt5/experts/early_closes.mqh'),point_value=POINT,cost=COST,
                  model='Python OHLC, no separate spread',runs=[])
    periods={'2010-15':(20100101,20160101),'2016-19':(20160101,20200101),
             '2020-Sep2026':(20200101,20261001),'Oct-Nov2026':(20261001,20261114),
             '2016-Nov2026':(20160101,20261114),'all':(20100101,20261114),
             **{str(y):(y*10000+101,(y+1)*10000+101) for y in range(2010,2027)}}
    rows=[]; countrows=[]; audits=[]
    for multiplier in (10.,7.5,5.):
        signals=detect(b,multiplier,cutoffs=cutoffs)
        # Independent direct sums on every detected signal, including exact threshold.
        for r in signals.itertuples():
            expected=float(np.mean(b['h'][r.index-20:r.index]-b['l'][r.index-20:r.index]))
            assert np.isclose(expected,r.prior20_mean,rtol=0,atol=1e-10)
            assert r.close>r.open and r.range >= multiplier*expected-1e-10
        count=int((signals.eligibility.eq('eligible') & signals.date.ge(20160101)).sum())
        print('Threshold',multiplier,'all signals',len(signals),'eligible since 2016',count,flush=True)
        for mode in ('directional','low_first','high_first'):
            tr,states=simulate(b,signals,cutoffs,mode)
            decisions=signals.copy(); decisions['decision']=[states.get(int(i),s) for i,s in zip(signals['index'],signals.eligibility)]
            label=f'{multiplier:g}x_{mode}'
            decisions.to_csv(args.out/f'{label}_signals.csv',index=False)
            tr.to_csv(args.out/f'{label}_trades.csv',index=False)
            assert len(tr)==sum(s=='filled' for s in states.values())
            assert tr.signal_index.is_unique and tr.entry_index.gt(tr.signal_index).all()
            assert np.allclose(tr.entry_price-tr.sl,tr.tp-tr.entry_price)
            assert np.allclose(tr.sl,b['l'][tr.signal_index.astype(int)]-TICK)
            assert np.allclose(tr.net,tr.gross-COST)
            if len(tr)>1:
                assert np.all(tr.entry_time.to_numpy()[1:]>=tr.exit_time.to_numpy()[:-1])
            for period,(a,z) in periods.items():
                sub=tr.loc[tr.date.ge(a)&tr.date.lt(z)]
                sig=decisions.loc[decisions.date.ge(a)&decisions.date.lt(z)]
                rows.append(dict(multiplier=multiplier,mode=mode,period=period,signals=len(sig),
                                 eligible=int(sig.eligibility.eq('eligible').sum()),**metrics(sub)))
            for status,num in decisions.decision.value_counts().items():
                countrows.append(dict(multiplier=multiplier,mode=mode,status=status,count=int(num)))
            audits.append(dict(multiplier=multiplier,mode=mode,trades=len(tr),signals=len(signals),
                               reference_direct_sum=True,causal_entries=True,geometry=True,unique_fills=True))
            print(label,metrics(tr),flush=True)
        manifest['runs'].append(dict(multiplier=multiplier,eligible_since_2016=count))
        if count>=100:
            break
    summary=pd.DataFrame(rows); summary.to_csv(args.out/'summary.csv',index=False)
    pd.DataFrame(countrows).to_csv(args.out/'decisions_summary.csv',index=False)
    manifest['output_sha256']={p.name:sha(p) for p in args.out.glob('*.csv')}
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (args.out/'verification.json').write_text(json.dumps(dict(all_passed=True,checks=audits),indent=2)+'\n')
    print(summary.loc[(summary['mode']=='directional') & ~summary.period.str.fullmatch(r'\d{4}')].to_string(index=False))


if __name__=='__main__':
    main()
