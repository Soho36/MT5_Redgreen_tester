"""Independent reconstruction of the full RTL VWAP replay and its artifacts.

Does not import the production preparer, runner, analyzer or feature functions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT/'Reports/rtl_vwap_replay_20261026'
PRIOR = ROOT/'Reports/rtl_vwap_20261025'
BASE = ROOT/'Reports/rtl_market_regimes_20261023/trades.csv'
PROTOCOL = ROOT/'docs/baseline/rtl-vwap/REPLAY_PROTOCOL.md'
PROTOCOL_SHA = '074ec194de5603fe1adcb6bd53a08dd04a1c9992d00be5963d8a96a1d72a3748'
DTYPE = np.dtype([('time_msc','<i8'),('balance','<f8'),('equity','<f8')])
ERAS = {'2016-19': ('2016-01-01','2020-01-01'), '2020-26': ('2020-01-01','2026-10-01')}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def read(name):
    return pd.read_csv(RUN/name,sep='\t',encoding='utf-16',float_precision='round_trip')


def numeric(a,b,label,atol=1e-8):
    np.testing.assert_allclose(np.asarray(a,float),np.asarray(b,float),atol=atol,rtol=1e-10,
                               equal_nan=True,err_msg=label)


def exact(a,b,label):
    a=pd.Series(a).reset_index(drop=True)
    b=pd.Series(b).reset_index(drop=True)
    assert len(a)==len(b) and np.array_equal(a.to_numpy(),b.to_numpy()), label


def ms(values):
    return pd.to_datetime(values,unit='ms')


def epoch(values):
    return pd.to_datetime(values).to_numpy(dtype='datetime64[ms]').astype('int64')


def feature_export(manifest):
    provenance=json.loads((PRIOR/'feature_provenance.json').read_text())
    source=PRIOR/'features_full_hlc3.csv'
    assert sha(source)==provenance['outputs_sha256'][source.name]
    f=pd.read_csv(source,float_precision='round_trip')
    export=pd.read_csv(RUN/manifest['feature_common_name'],sep='\t',float_precision='round_trip')
    assert len(f)==len(export)==manifest['feature_rows']
    for a,b in [('available_epoch','available_at'),('session_epoch','feature_session'),('bar_epoch','bar_time')]:
        exact(export[a],pd.to_datetime(f[b]).to_numpy(dtype='datetime64[s]').astype('int64'),'feature epoch '+a)
    known=f.vwap_available & f.vwap.notna() & f.a20.gt(0)
    exact(export.known,known.astype(int),'feature known')
    numeric(export.close,f.close,'feature close')
    numeric(export.vwap,f.vwap.where(known,0),'feature VWAP')
    numeric(export.a20,f.a20.where(known,0),'feature A20')
    return f,export


def candidate_lookup(export,times_msc,closes,gate):
    """Literal completed-information lookup; no tolerance changes threshold ties."""
    at=np.asarray(times_msc,dtype='int64')//1000
    j=np.searchsorted(export.available_epoch.to_numpy(),at,side='right')-1
    row=export.iloc[np.maximum(j,0)].reset_index(drop=True)
    known=(j>=0)&row.known.eq(1).to_numpy()&row.session_epoch.eq(at-at%86400).to_numpy()
    blocked=known&(np.asarray(closes)<row.vwap.to_numpy()-row.a20.to_numpy())&gate
    return j,known,blocked


def verify_candidates(job,features,export):
    tag=job['tag']
    c=read(f'vwap_{tag}_candidates.csv')
    assert len(c) and c.candidate_id.is_unique
    exact(c.candidate_id,np.arange(1,len(c)+1),'candidate IDs')
    assert c.time_msc.is_monotonic_increasing and c.time_msc.is_unique
    exact(pd.to_datetime(c.time,format='%Y.%m.%d %H:%M:%S'),ms(c.time_msc),'candidate time')
    assert c.signal_close.lt(c.signal_open).all(), 'Only red candidates'
    bars=pd.to_datetime(features.bar_time)
    idx=bars.searchsorted(pd.to_datetime(c.signal_bar,format='%Y.%m.%d %H:%M:%S'))
    # End-of-source October1 candidates can reference bars outside the frozen panel.
    valid=(idx<len(features))
    check=features.iloc[idx[valid]].reset_index(drop=True)
    assert bars.iloc[idx[valid]].reset_index(drop=True).equals(pd.to_datetime(c.loc[valid,'signal_bar'],format='%Y.%m.%d %H:%M:%S').reset_index(drop=True))
    for field in ('open','high','low','close'):
        numeric(c.loc[valid,'signal_'+field],check[field],'candidate signal '+field)
    j,expected_known,expected_blocked=candidate_lookup(export,c.time_msc,c.signal_close,job['gate_enabled'])
    available=j>=0
    row=export.iloc[np.maximum(j,0)].reset_index(drop=True)
    exact(c.known,expected_known.astype(int),'candidate known')
    exact(c.blocked,expected_blocked.astype(int),'candidate blocked')
    assert c.gate_enabled.eq(int(job['gate_enabled'])).all()
    assert c.post_maintenance_orders.eq(0).all(), 'Original cancellation must precede candidate gate'
    for field,target in [('feature_available','available_epoch'),('feature_session','session_epoch'),('feature_bar','bar_epoch')]:
        actual=pd.to_datetime(c.loc[available,field],format='%Y.%m.%d %H:%M:%S')
        exact(actual,pd.to_datetime(row.loc[available,target],unit='s'),'candidate '+field)
        assert c.loc[~available,field].isna().all()
    numeric(c.loc[available,'feature_close'],row.loc[available,'close'],'candidate feature close')
    numeric(c.loc[expected_known,'vwap'],row.loc[expected_known,'vwap'],'candidate vwap')
    numeric(c.loc[expected_known,'a20'],row.loc[expected_known,'a20'],'candidate a20')
    numeric(c.loc[expected_known,'z'],(c.loc[expected_known,'signal_close'].to_numpy()-row.loc[expected_known,'vwap'].to_numpy())/row.loc[expected_known,'a20'].to_numpy(),'candidate z')
    assert c.loc[~expected_known,['vwap','a20','z']].isna().all().all()
    assert c.loc[expected_blocked,['order','retcode','send_success']].eq(0).all().all()
    known_bar=pd.to_datetime(c.loc[expected_known,'signal_bar'],format='%Y.%m.%d %H:%M:%S')
    exact(known_bar,pd.to_datetime(row.loc[expected_known,'bar_epoch'],unit='s'),'known signal identity')
    return c


def complete_deal_pairs(traded):
    """A complete position has one entry and one exit, even in one millisecond."""
    assert traded.deal.is_unique, 'Duplicate deal'
    entries=traded.loc[traded.type.eq(0)&traded.entry.eq(0)]
    exits=traded.loc[traded.type.eq(1)&traded.entry.eq(1)]
    assert len(entries)+len(exits)==len(traded) and len(entries)==len(exits)
    assert entries.position_id.is_unique and exits.position_id.is_unique
    e=entries.set_index('position_id').sort_index()
    x=exits.set_index('position_id').reindex(e.index)
    assert x.deal.notna().all(), 'Missing exit'
    assert np.all(x.time_msc.to_numpy()>=e.time_msc.to_numpy()), 'Exit precedes entry'
    return e,x


def reconstruct_trades(job,candidates):
    tag=job['tag']
    orders=read(f'vwap_{tag}_orders.csv')
    deals=read(f'vwap_{tag}_deals.csv')
    paths=read(f'path_{tag}_trades.csv')
    assert orders.order.is_unique and deals.deal.is_unique
    traded=deals.loc[deals.type.isin([0,1])].copy()
    assert traded.symbol.eq(job['symbol']).all() and traded.volume.eq(1).all()
    assert traded[['commission','swap','fee']].eq(0).all().all()
    e,x=complete_deal_pairs(traded)
    o=orders.set_index('order').reindex(e.order).reset_index(drop=True)
    assert o.state.eq(4).all() and o.type.eq(4).all() and o.symbol.eq(job['symbol']).all()
    assert o.volume_initial.eq(1).all()
    f=pd.DataFrame(dict(position_id=e.index,ticket=e.order.to_numpy(),
        submitted=ms(o.setup_msc),entry_time=ms(e.time_msc.to_numpy()),exit_time=ms(x.time_msc.to_numpy()),
        submitted_msc=o.setup_msc.to_numpy(),entry_time_msc=e.time_msc.to_numpy(),exit_time_msc=x.time_msc.to_numpy(),
        requested_price=o.price_open.to_numpy(),original_sl=o.sl.to_numpy(),fill_price=e.price.to_numpy(),exit_price=x.price.to_numpy(),
        trade_profit=e.profit.to_numpy()+x.profit.to_numpy(),entry_deal=e.deal.to_numpy(),exit_deal=x.deal.to_numpy()))
    f=f.sort_values(['entry_time_msc','ticket']).reset_index(drop=True)
    assert f.ticket.is_unique and f.submitted.is_unique
    assert f.submitted.le(f.entry_time).all() and f.entry_time.le(f.exit_time).all()
    assert (f.entry_time_msc.iloc[1:].to_numpy()>=f.exit_time_msc.iloc[:-1].to_numpy()).all()
    assert f.submitted.dt.normalize().equals(f.entry_time.dt.normalize())
    assert f.entry_time.dt.normalize().equals(f.exit_time.dt.normalize())
    numeric(f.trade_profit,(f.exit_price-f.fill_price)*2,'deal price profit')
    f['session']=f.submitted.dt.normalize()
    f['year']=f.session.dt.year
    f['initial_risk_dollars']=(f.requested_price-f.original_sl)*2
    f['fill_risk_dollars']=(f.fill_price-f.original_sl)*2
    assert f.initial_risk_dollars.gt(0).all()
    f['net_dollars']=f.trade_profit-1.05
    f['gross_r']=f.trade_profit/f.initial_risk_dollars
    f['net_r']=f.net_dollars/f.initial_risk_dollars
    f['holding_minutes']=(f.exit_time_msc-f.entry_time_msc)/60000
    f['week_start']=f.session-pd.to_timedelta(f.session.dt.weekday,unit='D')
    f['era']='warmup'
    for era,(start,stop) in ERAS.items():
        f.loc[f.session.ge(start)&f.session.lt(stop),'era']=era
    f.loc[f.session.ge('2026-10-01'),'era']='partial_endpoint'
    paired=paths.set_index('entry_order').reindex(f.ticket)
    assert len(paths)==len(f) and paths.entry_order.is_unique and paired.position_id.notna().all()
    for a,b in [('position_id','position_id'),('entry_time_msc','entry_time_msc'),('exit_time_msc','exit_time_msc'),
                ('actual_fill','fill_price'),('requested_entry','requested_price'),('initial_sl','original_sl'),
                ('exit_price','exit_price'),('trade_profit','trade_profit'),('entry_deal','entry_deal'),('exit_deal','exit_deal')]:
        numeric(paired[a],f[b],'path '+a)
    numeric(paired.requested_risk,f.initial_risk_dollars/2,'path requested risk')
    numeric(paired.actual_risk,f.fill_risk_dollars/2,'path actual risk')
    assert paired.first_quote_time_msc.eq(paired.entry_time_msc).all()
    numeric(paired.mae_R,np.maximum(0,(paired.actual_fill-paired.min_bid)/paired.actual_risk),'MAE')
    numeric(paired.mfe_R,np.maximum(0,(paired.max_bid-paired.actual_fill)/paired.actual_risk),'MFE')
    accepted=candidates.loc[candidates.order.gt(0)].set_index('order')
    assert accepted.index.is_unique
    original_buys=orders.loc[orders.type.eq(4)].set_index('order').sort_index()
    assert set(accepted.index)==set(original_buys.index), 'Every submitted buy stop has exactly one logged candidate'
    a=accepted.reindex(original_buys.index)
    assert a.blocked.eq(0).all() and a.send_success.eq(1).all()
    numeric(a.time_msc,original_buys.setup_msc,'candidate order submission')
    numeric(a.signal_high,original_buys.price_open,'candidate order entry')
    numeric(a.signal_low,original_buys.sl,'candidate order stop')
    filled=accepted.reindex(f.ticket)
    f['signal_bar']=pd.to_datetime(filled.signal_bar.to_numpy(),format='%Y.%m.%d %H:%M:%S')
    f['vwap_known']=filled.known.to_numpy().astype(bool)
    f['vwap']=filled.vwap.to_numpy()
    f['a20']=filled.a20.to_numpy()
    f['signal_close']=filled.signal_close.to_numpy()
    f['far_below']=f.vwap_known & f.signal_close.lt(f.vwap-f.a20)
    if job['gate_enabled']:
        assert not f.far_below.any()
    summary=read(f'path_{tag}_summary.csv').iloc[0]
    for name,value in [('observer_errors',0),('active_at_end',0),('counts_match',1),('profit_match',1),('max_entry_lag_msc',0),('exported_positions',len(f))]:
        assert summary[name]==value, name
    stats=read(job['outputs'][1]).iloc[0]
    assert stats.trades==len(f) and stats.run_tag==tag and stats.risk_reward==1
    numeric([stats.net_profit,stats.gross_profit,stats.gross_loss],
            [f.trade_profit.sum(),f.trade_profit.clip(lower=0).sum(),f.trade_profit.clip(upper=0).sum()],'tester totals')
    extra=read(f'vwap_{tag}_summary.csv').iloc[0]
    assert extra.observer_errors==0 and extra.candidates==len(candidates) and extra.blocked==candidates.blocked.sum()
    assert extra.history_orders==len(orders) and extra.history_deals==len(deals)
    return f,deals,extra


def verify_baseline(frame):
    reference=pd.read_csv(BASE,float_precision='round_trip')
    for col in ('submitted','entry_time','exit_time'):
        reference[col]=pd.to_datetime(reference[col],format='ISO8601')
    assert len(frame)==len(reference)==25833
    reference=reference.sort_values('submitted').reset_index(drop=True)
    actual=frame.sort_values('submitted').reset_index(drop=True)
    for col in ('submitted','entry_time','exit_time'):
        exact(actual[col],reference[col],'baseline '+col)
    for col in ('requested_price','original_sl','fill_price','exit_price','trade_profit','initial_risk_dollars','net_dollars','net_r','holding_minutes'):
        numeric(actual[col],reference[col],'baseline '+col)
    for era,count,net in [('2016-19',6167,4416.65),('2020-26',10501,38399.95)]:
        part=frame.loc[frame.era.eq(era)]
        assert len(part)==count
        numeric([part.net_dollars.sum()],[net],'baseline '+era)
    return bool(np.array_equal(actual.ticket,reference.ticket))


def verify_job(job,features,export):
    tag=job['tag']
    completion=json.loads((RUN/(tag+'.completed.json')).read_text())
    assert completion['tag']==tag
    assert set(completion['outputs'])==set(job['outputs']), 'Incomplete completion inventory'
    for name,expected in completion['outputs'].items():
        assert sha(RUN/name)==expected, name
    if completion['report_sha256'] is None:
        assert completion.get('report_status')=='not_generated', 'Missing report must be explicitly acknowledged'
        assert not (RUN/(tag+'.htm')).exists(), 'Unhashed report exists'
    else:
        assert sha(RUN/(tag+'.htm'))==completion['report_sha256']
    candidates=verify_candidates(job,features,export)
    frame,deals,summary=reconstruct_trades(job,candidates)
    ticket_equal=verify_baseline(frame) if job['variant']=='off' else None
    if job['variant']=='off':
        assert (RUN/job['outputs'][0]).read_bytes()==Path(job['reference_raw']).read_bytes(), 'Baseline ledger bytes'
    path=RUN/f'vwap_{tag}_equity.bin'
    assert path.stat().st_size%DTYPE.itemsize==0
    equity=np.memmap(path,dtype=DTYPE,mode='r')
    assert len(equity)==summary.equity_rows and len(equity)>0
    assert np.isfinite(equity['balance']).all() and np.isfinite(equity['equity']).all()
    assert np.all(np.diff(equity['time_msc'])>=0)
    deposit=deals.loc[deals.type.eq(2),'profit'].sum()
    numeric([equity[-1]['balance'],equity[-1]['equity']],[deposit+frame.trade_profit.sum()]*2,'final flat equity')
    return frame,dict(all_passed=True,variant=job['variant'],trades=len(frame),candidates=len(candidates),
        blocked=int(candidates.blocked.sum()),baseline_ticket_ids_equal=ticket_equal,equity_samples=len(equity),
        eligible_trades=int(frame.era.isin(ERAS).sum()),source_feature_rows=len(features))


def drawdown_episodes(values,times):
    """Measure complete underwater episodes through recovery, or final observation."""
    values=np.asarray(values,float)
    times=epoch(times)
    assert len(values)==len(times) and len(values)>0
    assert np.isfinite(values).all() and np.all(np.diff(times)>=0)
    peaks=np.maximum.accumulate(values)
    depths=peaks-values
    underwater=values<peaks-1e-9
    starts=np.flatnonzero(underwater & ~np.r_[False,underwater[:-1]])
    ends=np.flatnonzero(~underwater & np.r_[False,underwater[:-1]])
    if underwater[-1]:
        ends=np.r_[ends,len(values)-1]
    assert len(starts)==len(ends) and np.all(starts>0)
    durations=(times[ends]-times[starts-1])/86400000.
    return float(depths.max()),float(durations.max()) if len(durations) else 0.


def closed_episodes(increments,exit_times,endpoint):
    if not len(increments):
        return 0.,0.
    values=np.r_[0.,np.cumsum(increments)]
    times=pd.DatetimeIndex(exit_times)
    # No loss exists before the first observed closed trade.
    return drawdown_episodes(np.r_[values,values[-1]],
        pd.DatetimeIndex([times[0],*times,pd.Timestamp(endpoint)]))


def metric_values(t,calendar):
    """Independent ledger arithmetic, including flat calendar days."""
    d=t.groupby('session').net_dollars.sum().reindex(calendar,fill_value=0.)
    w=d.groupby(d.index-pd.to_timedelta(d.index.weekday,unit='D')).sum()
    ordered=t.sort_values(['exit_time','entry_time','ticket'])
    endpoint=calendar[-1]+pd.Timedelta(days=1)
    closed,closed_duration=closed_episodes(ordered.net_dollars,ordered.exit_time,endpoint)
    r_depth,r_duration=closed_episodes(ordered.net_r,ordered.exit_time,endpoint)
    balance=peak=dd=0.
    duration=0
    peak_date=calendar[0]
    for date,pnl in d.items():
        balance+=float(pnl)
        dd=max(dd,peak-balance)
        if balance>=peak-1e-9:
            peak=max(peak,balance)
            peak_date=date
        else:
            duration=max(duration,(date-peak_date).days)
    positive=t.net_dollars.clip(lower=0).sum()
    loss=-t.net_dollars.clip(upper=0).sum()
    result=dict(trades=len(t),active_sessions=t.session.nunique(),active_weeks=t.week_start.nunique(),
        eligible_sessions=len(calendar),eligible_weeks=len(w),gross_mean_r=t.gross_r.mean(),net_mean_r=t.net_r.mean(),
        gross_dollars=t.trade_profit.sum(),net_dollars=t.net_dollars.sum(),dollar_pf=positive/loss if loss else np.nan,
        risk_mean=t.initial_risk_dollars.mean(),risk_median=t.initial_risk_dollars.median(),
        commission_mean_r=t.commission_r.mean(),holding_hours=t.holding_minutes.sum()/60,
        mean_holding_minutes=t.holding_minutes.mean(),worst_day=d.min(),worst_week=w.min(),
        worst5pct_session_mean=d.nsmallest(int(np.ceil(.05*len(d)))).mean(),closed_trade_dd=closed,
        closed_trade_dd_duration_days=closed_duration,closed_trade_r_dd=r_depth,
        closed_trade_r_dd_duration_days=r_duration,
        daily_close_dd=dd,daily_dd_duration_days=duration)
    for k in (1,2):
        result[f'stress{k}_net_dollars']=t[f'stress{k}_net_dollars'].sum()
        result[f'stress{k}_mean_r']=t[f'stress{k}_net_r'].mean()
    return result,d


def compare_row(row,expected,label):
    for key,value in expected.items():
        assert key in row.index, label+'/'+key
        numeric([row[key]],[value],label+'/'+key,atol=1e-6)


def net_equity(raw,trades,start,stop,cost):
    start_ms=int(pd.Timestamp(start).value//1000000)
    stop_ms=int(pd.Timestamp(stop).value//1000000)
    mask=(raw['time_msc']>=start_ms)&(raw['time_msc']<stop_ms)
    times=raw['time_msc'][mask]
    assert len(times)
    prior=trades.loc[trades.exit_time_msc.lt(start_ms),'trade_profit'].sum()
    entered=trades.loc[trades.entry_time_msc.ge(start_ms)&trades.entry_time_msc.lt(stop_ms)]
    assert entered.exit_time_msc.lt(stop_ms).all()
    count=np.searchsorted(np.sort(entered.entry_time_msc),times,side='right')
    values=raw['equity'][mask]-500000-prior-cost*count
    numeric([values[-1]],[entered.trade_profit.sum()-cost*len(entered)],'sampled net endpoint')
    values=np.r_[0.,values,values[-1]]
    times=np.r_[start_ms,times,stop_ms-1]
    peaks=np.maximum.accumulate(values)
    depths=peaks-values
    peak_indices=np.maximum.accumulate(np.where(values>=peaks-1e-9,np.arange(len(values)),0))
    _,duration=drawdown_episodes(values,ms(times))
    trough=int(np.argmax(depths))
    return dict(samples=len(values)-2,sampled_open_equity_dd=float(depths[trough]),
        sampled_open_equity_dd_duration_days=duration,net_endpoint=float(values[-1]),
        cost_per_trade=cost),str(ms(times[peak_indices[trough]])),str(ms(times[trough]))


def add_economics(frame):
    f=frame.copy()
    f['commission_r']=1.05/f.initial_risk_dollars
    for k in (1,2):
        f[f'stress{k}_net_dollars']=f.net_dollars-k
        f[f'stress{k}_net_r']=f[f'stress{k}_net_dollars']/f.initial_risk_dollars
    return f


def static_scale(frame,fraction):
    f=frame.copy()
    for name in ('trade_profit','net_dollars','initial_risk_dollars','fill_risk_dollars','holding_minutes',
                 'stress1_net_dollars','stress2_net_dollars'):
        f[name]*=fraction
    return f


def independent_partition(left,right):
    keys=['submitted','requested_price','original_sl']
    l={tuple(row[k] for k in keys):row for row in left.to_dict('records')}
    r={tuple(row[k] for k in keys):row for row in right.to_dict('records')}
    assert len(l)==len(left) and len(r)==len(right)
    out={label:dict(matched_candidates=0,left_trades=0,right_trades=0,left_net_dollars=0.,
        right_net_dollars=0.,left_net_r_total=0.,right_net_r_total=0.,net_delta=0.)
         for label in ('unchanged','execution_changed','removed','new')}
    details={}
    for key in l.keys()|r.keys():
        a,b=l.get(key),r.get(key)
        if a is None:
            label='new'
        elif b is None:
            label='removed'
        elif all(a[k]==b[k] for k in ('entry_time','exit_time','fill_price','exit_price','trade_profit')):
            label='unchanged'
        else:
            label='execution_changed'
        row=out[label]
        row['matched_candidates']+=1
        for side,value in [('left',a),('right',b)]:
            if value is not None:
                row[side+'_trades']+=1
                row[side+'_net_dollars']+=value['net_dollars']
                row[side+'_net_r_total']+=value['net_r']
        delta=(b['net_dollars'] if b else 0)-(a['net_dollars'] if a else 0)
        row['net_delta']+=delta
        details[key]=(label,delta)
    numeric([sum(x['net_delta'] for x in out.values())],[right.net_dollars.sum()-left.net_dollars.sum()],'partition total')
    return out,details


def verify_economics(frames,features):
    frames={k:add_economics(v) for k,v in frames.items()}
    outputs={name:pd.read_csv(RUN/(name+'.csv'),float_precision='round_trip')
             for name in ('summaries','yearly','daily_curves','attribution','trade_changes','open_equity',
                          'candidate_counts','candidate_changes','accepted_order_states')}
    audit=json.loads((RUN/'analysis_audit.json').read_text())
    assert audit['all_passed'] and audit['baseline_exact'] and not audit['strategy_adopted']
    assert sha(ROOT/'python/analyze_rtl_vwap_replay.py')==audit['analyzer_sha256'], 'Analysis predates current analyzer'
    for name,frame in outputs.items():
        assert sha(RUN/(name+'.csv'))==audit['outputs_sha256'][name+'.csv']
        assert len(frame)==audit['output_rows'][name+'.csv']
    assert len(outputs['summaries'])==10 and len(outputs['yearly'])==55
    assert len(outputs['attribution'])==16 and len(outputs['open_equity'])==34
    assert len(outputs['candidate_counts'])==4 and len(outputs['accepted_order_states'])==40
    outputs['daily_curves']['session']=pd.to_datetime(outputs['daily_curves'].session)
    outputs['trade_changes']['submitted']=pd.to_datetime(outputs['trade_changes'].submitted)
    calendar_all=pd.DatetimeIndex(pd.to_datetime(features.bar_time).dt.normalize().unique()).sort_values()
    # Producer normalized trade tables must preserve all independently reconstructed fields.
    for variant,f in frames.items():
        actual=pd.read_csv(RUN/f'trades_{variant}.csv',float_precision='round_trip').sort_values('ticket')
        expected=f.sort_values('ticket')
        assert len(actual)==len(expected)
        for name in ('ticket','requested_price','original_sl','fill_price','exit_price','trade_profit',
                     'initial_risk_dollars','fill_risk_dollars','net_dollars','net_r','gross_r','holding_minutes'):
            numeric(actual[name],expected[name],'normalized '+variant+'/'+name)
        for name in ('submitted','entry_time','exit_time'):
            exact(pd.to_datetime(actual[name]),expected[name],'normalized '+variant+'/'+name)
    for era,(start,stop) in ERAS.items():
        calendar=calendar_all[(calendar_all>=start)&(calendar_all<stop)]
        a,b=[frames[k].loc[frames[k].era.eq(era)] for k in ('off','on')]
        omission=a.loc[~a.far_below]
        holding=b.holding_minutes.sum()/a.holding_minutes.sum()
        risk=b.initial_risk_dollars.sum()/a.initial_risk_dollars.sum()
        curves=dict(baseline=a,ledger_omission=omission,gated=b,
                    static_holding=static_scale(a,holding),static_planned_risk=static_scale(a,risk))
        for curve,t in curves.items():
            expected,day=metric_values(t,calendar)
            expected.update(retained_holding_fraction=holding,retained_planned_risk_fraction=risk,
                            net_over_daily_dd=expected['net_dollars']/expected['daily_close_dd'] if expected['daily_close_dd'] else np.nan)
            row=outputs['summaries'].query('era==@era and curve==@curve')
            assert len(row)==1
            compare_row(row.iloc[0],expected,'summary '+era+'/'+curve)
            saved=outputs['daily_curves'].query('era==@era and curve==@curve').sort_values('session')
            exact(saved.session,day.index,'daily dates')
            numeric(saved.net_dollars,day.to_numpy(),'daily pnl')
            for year in sorted(t.year.unique()):
                expected,_=metric_values(t.loc[t.year.eq(year)],calendar[calendar.year==year])
                row=outputs['yearly'].query('era==@era and curve==@curve and year==@year')
                assert len(row)==1 and row.iloc[0]['partial']==(year==2026)
                compare_row(row.iloc[0],expected,'annual '+str(year)+'/'+curve)
        for comparison,left in [('gated_minus_baseline',a),('gated_minus_omission',omission)]:
            expected,details=independent_partition(left,b)
            rows=outputs['attribution'].query('era==@era and comparison==@comparison')
            assert len(rows)==4
            for row in rows.itertuples(index=False):
                compare_row(pd.Series(row._asdict()),expected[row.category],'attribution '+era+'/'+comparison+'/'+row.category)
            saved=outputs['trade_changes'].query('era==@era and comparison==@comparison')
            assert len(saved)==len(details)
            for row in saved.itertuples(index=False):
                label,delta=details[(row.submitted,row.requested_price,row.original_sl)]
                assert row.category==label
                numeric([row.net_delta],[delta],'trade change delta')
            for side,frame in [('left',left),('right',b)]:
                lookup={(row['submitted'],row['requested_price'],row['original_sl']):row
                        for row in frame.to_dict('records')}
                reconstructed=pd.DataFrame([lookup.get((row.submitted,row.requested_price,row.original_sl),{})
                                            for row in saved.itertuples(index=False)])
                for field in ('fill_price','exit_price','trade_profit','net_dollars','net_r'):
                    numeric(saved[field+'_'+side],reconstructed[field],'trade change '+side+'/'+field)
                for field in ('entry_time','exit_time'):
                    exact(epoch(pd.to_datetime(saved[field+'_'+side],format='ISO8601')),
                          epoch(reconstructed[field]),'trade change '+side+'/'+field)
    eq_rows=outputs['open_equity']
    for variant,f in frames.items():
        raw=np.memmap(RUN/f'vwap_vwap_replay_20261026_{variant}_equity.bin',dtype=DTYPE,mode='r')
        for row in eq_rows.loc[eq_rows.variant.eq(variant)].itertuples(index=False):
            start,stop=ERAS[row.era]
            if pd.notna(row.year):
                year=int(row.year)
                start=max(pd.Timestamp(start),pd.Timestamp(year,1,1))
                stop=min(pd.Timestamp(stop),pd.Timestamp(year+1,1,1))
            expected,peak,trough=net_equity(raw,f,start,stop,row.cost_per_trade)
            saved=pd.Series(row._asdict())
            compare_row(saved,expected,'open equity '+variant+'/'+row.era)
            assert saved.depth_peak_time==peak and saved.depth_trough_time==trough
    verify_candidate_outputs(outputs,frames)
    return {name:len(frame) for name,frame in outputs.items()}


def verify_candidate_outputs(outputs,frames):
    identity=['submitted','signal_bar','signal_high','signal_low']
    fields=['candidate_id','blocked','order','retcode','send_success','known','unfavorable']
    maps={}
    orders={}
    for variant in ('off','on'):
        c=read(f'vwap_vwap_replay_20261026_{variant}_candidates.csv')
        c['submitted']=ms(c.time_msc)
        c['signal_bar']=pd.to_datetime(c.signal_bar,format='%Y.%m.%d %H:%M:%S')
        c['unfavorable']=c.known.eq(1)&c.signal_close.lt(c.vwap-c.a20)
        c=c.loc[c.submitted.ge('2016-01-01')&c.submitted.lt('2026-10-01')]
        maps[variant]={tuple(row[k] for k in identity):row for row in c.to_dict('records')}
        assert len(maps[variant])==len(c)
        orders[variant]=read(f'vwap_vwap_replay_20261026_{variant}_orders.csv').set_index('order')
    expected={key:('shared' if key in maps['off'] and key in maps['on'] else
                  'off_only' if key in maps['off'] else 'on_only')
              for key in maps['off'].keys()|maps['on'].keys()}
    actual=outputs['candidate_changes'].copy()
    for name in ('submitted','signal_bar','session'):
        actual[name]=pd.to_datetime(actual[name])
    assert len(actual)==len(expected) and not actual.duplicated(identity).any()
    for row in actual.to_dict('records'):
        key=tuple(row[k] for k in identity)
        assert row['category']==expected[key]
        assert row['session']==key[0].normalize()
        assert row['era']==('2016-19' if key[0]<pd.Timestamp('2020-01-01') else '2020-26')
        for variant in ('off','on'):
            source=maps[variant].get(key)
            for field in fields:
                value=row[field+'_'+variant]
                if source is None:
                    assert pd.isna(value)
                elif field=='unfavorable':
                    assert value in (True,False,'True','False')
                    assert (value==True or value=='True')==bool(source[field])
                else:
                    numeric([value],[source[field]],'candidate detail '+field)
    state_names=('started','placed','canceled','partial','filled','rejected','expired',
                 'request_add','request_modify','request_cancel')
    for row in outputs['candidate_counts'].itertuples(index=False):
        start,stop=map(pd.Timestamp,ERAS[row.era])
        own={key:source for key,source in maps[row.variant].items() if start<=key[0]<stop}
        other=maps['on' if row.variant=='off' else 'off']
        exclusive=[source for key,source in own.items() if key not in other]
        c=pd.DataFrame(own.values())
        compare_row(pd.Series(row._asdict()),dict(candidates=len(c),blocked=c.blocked.sum(),
            accepted=c.order.gt(0).sum(),unknown=c.known.eq(0).sum(),unfavorable=c.unfavorable.sum(),
            request_without_order=(c.order.eq(0)&c.blocked.eq(0)).sum(),
            shared_candidates=sum(key in other for key in own),arm_only_candidates=len(exclusive),
            newly_enabled_candidates=len(exclusive) if row.variant=='on' else 0,
            arm_only_accepted_orders=sum(x['order']>0 for x in exclusive),
            arm_only_blocked=sum(x['blocked']==1 for x in exclusive)),'candidate counts')
        accepted=c.loc[c.order.gt(0),'order']
        states=orders[row.variant].loc[accepted,'state']
        traded=set(frames[row.variant].loc[frames[row.variant].era.eq(row.era),'ticket'])
        assert set(states.loc[states.eq(4)].index)==traded
        saved=outputs['accepted_order_states'].query('era==@row.era and variant==@row.variant')
        assert len(saved)==10 and set(saved.state_code)==set(range(10))
        for state in saved.itertuples(index=False):
            ids=states.loc[states.eq(state.state_code)].index
            assert state.state==state_names[state.state_code]
            assert state.accepted_orders==len(ids)
            assert state.complete_trades==sum(order in traded for order in ids)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('arm',choices=['off','on','all'],nargs='?',default='all')
    args=parser.parse_args()
    assert sha(PROTOCOL)==PROTOCOL_SHA
    manifest=json.loads((RUN/'manifest.json').read_text())
    for path,expected in manifest['input_hashes'].items():
        assert sha(Path(path))==expected, 'Frozen input changed '+path
    source=(RUN/(manifest['expert']+'.mq5')).read_text(encoding='utf-8')
    assert source.index('if(!VwapReplayCandidate(o1,h1,l1,c1)) return;')>source.index('// Original red-candidate maintenance')
    assert '\t   CancelOldBuyStops();\n\n\t   // Original red-candidate maintenance' in source
    features,export=feature_export(manifest)
    results=[]
    frames={}
    for job in manifest['jobs']:
        if args.arm!='all' and job['variant']!=args.arm:
            continue
        frames[job['variant']],result=verify_job(job,features,export)
        results.append(result)
        print(json.dumps(result),flush=True)
    economic_rows=verify_economics(frames,features) if args.arm=='all' and (RUN/'analysis_audit.json').exists() else None
    output=dict(all_passed=True,checks=results,economics_verified=economic_rows is not None,economic_rows=economic_rows,
                protocol_sha256=PROTOCOL_SHA,verifier_sha256=sha(Path(__file__)),
                analysis_audit_sha256=sha(RUN/'analysis_audit.json') if economic_rows is not None else None,
                completion_sha256={job['variant']:sha(RUN/(job['tag']+'.completed.json'))
                                   for job in manifest['jobs'] if job['variant'] in frames})
    (RUN/f'independent_{args.arm}_verification.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
