"""Validate the exact baseline, then measure the frozen full VWAP replay."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_rtl_market_regimes as base

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT/'Reports/rtl_vwap_replay_20261026'
STUDY = ROOT/'Reports/rtl_vwap_20261025'
REFERENCE = ROOT/'Reports/rtl_market_regimes_20261023/trades.csv'
ERAS = base.ERAS
NUMERIC = ['requested_price','original_sl','fill_price','exit_price','trade_profit']
IDENTITY = ['submitted','requested_price','original_sl']
CANDIDATE_IDENTITY = ['submitted','signal_bar','signal_high','signal_low']
ORDER_STATES = {0:'started',1:'placed',2:'canceled',3:'partial',4:'filled',
                5:'rejected',6:'expired',7:'request_add',8:'request_modify',9:'request_cancel'}


def write_json(name, value):
    (RUN/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def read_output(tag, suffix, prefix='vwap'):
    return pd.read_csv(RUN/f'{prefix}_{tag}_{suffix}.csv', sep='\t', encoding='utf-16', float_precision='round_trip')


def manifest_job(variant):
    manifest = json.loads((RUN/'manifest.json').read_text())
    for path, expected in manifest['input_hashes'].items():
        assert base.digest(path) == expected, 'Frozen input changed: '+path
    job = next(j for j in manifest['jobs'] if j['variant'] == variant)
    done = json.loads((RUN/(job['tag']+'.completed.json')).read_text())
    for filename, expected in done['outputs'].items():
        assert base.digest(RUN/filename) == expected, 'Changed completed output: '+filename
    if done['report_sha256'] is not None:
        assert base.digest(RUN/(job['tag']+'.htm')) == done['report_sha256']
    else:
        assert done['report_status'] == 'not_generated'
    return manifest, job


def history_trades(tag):
    """Reconstruct executions directly from full native order/deal exports.

    The OFF terminal did not save HTML because MT5 requires a relative Report
    path. Native history contains all corresponding execution fields, including
    millisecond timestamps; HTML, when present, is an additional cross-check.
    """
    orders = read_output(tag, 'orders')
    deals = read_output(tag, 'deals')
    assert orders.order.is_unique and deals.deal.is_unique
    assert deals[['commission','swap','fee']].eq(0).all().all()
    traded = deals.loc[deals.type.ne(2)]
    assert traded.volume.eq(1).all() and traded.symbol.eq('MNQcontDTBNT20102026_2').all()
    entry = traded.loc[traded.entry.eq(0)].copy()
    exits = traded.loc[traded.entry.eq(1)].copy()
    assert entry.type.eq(0).all() and exits.type.eq(1).all()
    assert len(entry) + len(exits) == len(traded)
    assert len(entry) == len(exits) and entry.position_id.is_unique and exits.position_id.is_unique
    p = entry.merge(exits, on='position_id', suffixes=('_entry','_exit'), validate='one_to_one')
    p = p.merge(orders, left_on='order_entry', right_on='order', validate='one_to_one')
    assert len(p) == len(entry) and p.state.eq(4).all() and p.type.eq(4).all()
    t = pd.DataFrame(dict(ticket=p.order, submitted=pd.to_datetime(p.setup_msc,unit='ms'),
        requested_price=p.price_open, original_sl=p.sl,
        entry_time=pd.to_datetime(p.time_msc_entry,unit='ms'),
        exit_time=pd.to_datetime(p.time_msc_exit,unit='ms'),
        fill_price=p.price_entry, exit_price=p.price_exit,
        trade_profit=p.profit_entry+p.profit_exit, exit_comment=p.comment_exit))
    t = t.sort_values(['entry_time','ticket']).reset_index(drop=True)
    assert t.submitted.le(t.entry_time).all() and t.entry_time.le(t.exit_time).all()
    assert (t.entry_time.iloc[1:].to_numpy() >= t.exit_time.iloc[:-1].to_numpy()).all()
    if (RUN/(tag+'.htm')).exists():
        previous = base.HTML
        try:
            base.HTML = RUN/(tag+'.htm')
            html = base.parse_report().sort_values(['entry_time','ticket']).reset_index(drop=True)
        finally:
            base.HTML = previous
        assert len(html) == len(t)
        for column in ('ticket','submitted','entry_time','exit_time','requested_price',
                       'original_sl','fill_price','exit_price','trade_profit'):
            np.testing.assert_array_equal(html[column].to_numpy(),t[column].to_numpy(),err_msg=column)
    return t


def candidate_audit(tag, gate):
    c = read_output(tag, 'candidates')
    assert c.candidate_id.is_unique and c.time_msc.is_monotonic_increasing
    assert c.gate_enabled.eq(int(gate)).all()
    f = pd.read_csv(STUDY/'features_full_hlc3.csv', float_precision='round_trip',
                    usecols=['available_at','bar_time','feature_session','close','vwap','a20','vwap_available'])
    for name in ['available_at','bar_time','feature_session']:
        f[name] = pd.to_datetime(f[name], format='ISO8601')
    c['submitted'] = pd.to_datetime(c.time_msc, unit='ms')
    indexes = np.searchsorted(f.available_at.to_numpy(), c.submitted.to_numpy(), side='right')-1
    got = f.iloc[np.maximum(indexes, 0)].reset_index(drop=True)
    known = (indexes >= 0) & got.vwap_available & got.a20.gt(0) & got.feature_session.eq(c.submitted.dt.normalize())
    np.testing.assert_array_equal(c.known, known.astype(int))
    signal = pd.to_datetime(c.signal_bar, format='%Y.%m.%d %H:%M:%S')
    assert got.loc[known,'bar_time'].reset_index(drop=True).equals(signal.loc[known].reset_index(drop=True))
    for name in ('vwap','a20'):
        np.testing.assert_allclose(c.loc[known,name],got.loc[known,name],rtol=1e-12,atol=1e-8)
    np.testing.assert_allclose(c.loc[known,'signal_close'],got.loc[known,'close'],rtol=0,atol=1e-8)
    unfavorable = known & c.signal_close.lt(got.vwap-got.a20)
    np.testing.assert_array_equal(c.blocked, (unfavorable & gate).astype(int))
    assert c.loc[c.blocked.eq(1), ['order','send_success']].eq(0).all().all()
    assert c.post_maintenance_orders.eq(0).all(), 'Original replacement cancellation failed'
    c['unfavorable'] = unfavorable
    c['session'] = c.submitted.dt.normalize()
    return c


def load_run(variant):
    manifest, job = manifest_job(variant)
    tag = job['tag']
    t = history_trades(tag)
    paths = read_output(tag,'trades','path')
    assert len(t) == len(paths) and paths.entry_order.is_unique
    t = t.merge(paths[['entry_order','entry_time_msc','exit_time_msc','first_quote_time_msc',
                       'requested_risk','actual_risk','mae_R','mfe_R','actual_fill','trade_profit']],
                left_on='ticket',right_on='entry_order',validate='one_to_one',suffixes=('','_path'))
    for a,b in [('fill_price','actual_fill'),('trade_profit','trade_profit_path')]:
        np.testing.assert_allclose(t[a],t[b],rtol=0,atol=1e-8)
    np.testing.assert_allclose(t.requested_price-t.original_sl,t.requested_risk,rtol=0,atol=1e-8)
    np.testing.assert_allclose(t.fill_price-t.original_sl,t.actual_risk,rtol=0,atol=1e-8)
    assert t.first_quote_time_msc.eq(t.entry_time_msc).all()
    assert pd.to_datetime(t.entry_time_msc,unit='ms').equals(t.entry_time)
    assert pd.to_datetime(t.exit_time_msc,unit='ms').equals(t.exit_time)
    summary = read_output(tag,'summary','path').iloc[0]
    for key, value in dict(observer_errors=0,active_at_end=0,counts_match=1,profit_match=1,
                           max_entry_lag_msc=0,exported_positions=len(t)).items():
        assert summary[key] == value, (tag,key,summary[key])
    observer = read_output(tag,'summary').iloc[0]
    assert observer.observer_errors == 0
    c = candidate_audit(tag, variant == 'on')
    assert len(c) == observer.candidates and c.blocked.sum() == observer.blocked
    accepted = c.loc[c.order.gt(0)].copy()
    assert accepted.order.is_unique
    t = t.merge(accepted[['order','candidate_id','signal_bar','known','unfavorable','vwap','a20','z']],
                left_on='ticket',right_on='order',validate='one_to_one')
    assert len(t) == len(paths), 'Filled order lacks candidate'
    t['variant'] = variant
    t['session'] = t.submitted.dt.normalize()
    assert t.session.eq(t.entry_time.dt.normalize()).all()
    assert t.session.eq(t.exit_time.dt.normalize()).all()
    t['initial_risk_dollars'] = (t.requested_price-t.original_sl)*2
    t['fill_risk_dollars'] = (t.fill_price-t.original_sl)*2
    assert t.initial_risk_dollars.gt(0).all()
    np.testing.assert_allclose((t.exit_price-t.fill_price)*2,t.trade_profit,atol=1e-8,rtol=0)
    t['gross_r'] = t.trade_profit/t.initial_risk_dollars
    t['net_dollars'] = t.trade_profit-1.05
    t['net_r'] = t.net_dollars/t.initial_risk_dollars
    t['commission_r'] = 1.05/t.initial_risk_dollars
    t['holding_minutes'] = (t.exit_time-t.entry_time).dt.total_seconds()/60
    for extra in (1,2):
        t[f'stress{extra}_net_dollars'] = t.net_dollars-extra
        t[f'stress{extra}_net_r'] = t[f'stress{extra}_net_dollars']/t.initial_risk_dollars
    t['week_start'] = t.session-pd.to_timedelta(t.session.dt.dayofweek,unit='D')
    t['year'] = t.session.dt.year
    t['era'] = 'warmup'
    for era,(start,stop) in ERAS.items():
        t.loc[t.session.ge(start)&t.session.lt(stop),'era'] = era
    t.loc[t.session.ge('2026-10-01'),'era'] = 'partial_endpoint'
    t['primary'] = t.era.isin(ERAS)
    stats = pd.read_csv(RUN/job['outputs'][1],sep='\t',encoding='utf-16').iloc[0]
    assert stats.trades == len(t)
    assert np.isclose(stats.net_profit,t.trade_profit.sum(),atol=1e-6)
    t.to_csv(RUN/f'trades_{variant}.csv',index=False,float_format='%.17g')
    c.to_csv(RUN/f'candidates_{variant}.csv',index=False,float_format='%.17g')
    return t,c,job


def validate_baseline():
    t,c,job = load_run('off')
    ref = pd.read_csv(REFERENCE,parse_dates=['submitted','entry_time','exit_time'])
    assert len(t) == len(ref) == 25833
    assert not t.duplicated(IDENTITY).any() and not ref.duplicated(IDENTITY).any()
    pair = t.merge(ref,on=IDENTITY,validate='one_to_one',suffixes=('_run','_ref'))
    assert len(pair) == len(ref)
    for name in ('entry_time','exit_time'):
        # Native history uses datetime64[ms], CSV parsing may choose [us].
        # Compare exact timestamp values without requiring the same storage unit.
        np.testing.assert_array_equal(pair[name+'_run'].to_numpy(),pair[name+'_ref'].to_numpy(),err_msg=name)
    for name in ('fill_price','exit_price','trade_profit'):
        np.testing.assert_allclose(pair[name+'_run'],pair[name+'_ref'],rtol=0,atol=1e-8)
    assert t.loc[t.primary].groupby('era').size().to_dict() == {'2016-19':6167,'2020-26':10501}
    np.testing.assert_allclose(t.loc[t.primary].groupby('era').net_dollars.sum(),[4416.65,38399.95],rtol=0,atol=1e-7)
    raw_equal = (RUN/job['outputs'][0]).read_bytes() == Path(job['reference_raw']).read_bytes()
    ids_equal = pair.ticket_run.equals(pair.ticket_ref)
    assert raw_equal and ids_equal, 'Original full raw ledger or IDs differ; investigate before on arm'
    result = dict(all_passed=True,whole_run_trades=len(t),eligible_trades=int(t.primary.sum()),
        raw_byte_equal=raw_equal,ticket_ids_equal=ids_equal,all_execution_fields_equal=True,
        candidate_decisions_checked=len(c),reference_sha256=base.digest(REFERENCE),
        off_completion_sha256=base.digest(RUN/(job['tag']+'.completed.json')),
        analyzer_sha256=base.digest(Path(__file__)))
    write_json('baseline_validation.json',result)
    print(json.dumps(result,indent=2),flush=True)
    return t


def attribution(left,right,label):
    """Execution identity ignores ticket renumbering across engine arms."""
    assert not left.duplicated(IDENTITY).any() and not right.duplicated(IDENTITY).any()
    fields = ['entry_time','exit_time','fill_price','exit_price','trade_profit','net_dollars','net_r']
    p = left[IDENTITY+fields].merge(right[IDENTITY+fields],on=IDENTITY,how='outer',
                                  suffixes=('_left','_right'),indicator=True,validate='one_to_one')
    same = p['_merge'].eq('both')
    for name in ['entry_time','exit_time','fill_price','exit_price','trade_profit']:
        same &= p[name+'_left'].eq(p[name+'_right'])
    p['category'] = np.select([p['_merge'].eq('left_only'),p['_merge'].eq('right_only'),same],
                              ['removed','new','unchanged'],default='execution_changed')
    p['net_delta'] = p.net_dollars_right.fillna(0)-p.net_dollars_left.fillna(0)
    p['comparison'] = label
    rows = []
    for category in ['unchanged','execution_changed','removed','new']:
        g = p.loc[p.category.eq(category)]
        rows.append(dict(comparison=label,category=category,matched_candidates=len(g),
            left_trades=int(g.net_dollars_left.notna().sum()),right_trades=int(g.net_dollars_right.notna().sum()),
            left_net_dollars=float(g.net_dollars_left.sum()),right_net_dollars=float(g.net_dollars_right.sum()),
            left_net_r_total=float(g.net_r_left.sum()),right_net_r_total=float(g.net_r_right.sum()),
            net_delta=float(g.net_delta.sum())))
    assert np.isclose(p.net_delta.sum(),right.net_dollars.sum()-left.net_dollars.sum(),atol=1e-8)
    return p,rows


def equity_metrics(variant,trades,start,stop,cost=1.05):
    tag = f'vwap_replay_20261026_{variant}'
    path = RUN/f'vwap_{tag}_equity.bin'
    assert path.stat().st_size%24 == 0
    raw = np.fromfile(path,dtype=[('time_msc','<i8'),('balance','<f8'),('equity','<f8')])
    times = raw['time_msc']
    assert np.all(np.diff(times)>=0) and np.isfinite(raw['balance']).all() and np.isfinite(raw['equity']).all()
    start_ms = pd.Timestamp(start).value//10**6
    stop_ms = pd.Timestamp(stop).value//10**6
    before = trades.loc[trades.exit_time_msc.lt(start_ms),'trade_profit'].sum()
    selected = trades.loc[trades.entry_time_msc.ge(start_ms)&trades.entry_time_msc.lt(stop_ms)]
    assert selected.exit_time_msc.lt(stop_ms).all()
    ids = (times>=start_ms)&(times<stop_ms)
    ts = times[ids]
    assert len(ts)>0
    entries = np.sort(selected.entry_time_msc.to_numpy())
    counts = np.searchsorted(entries,ts,side='right')
    eq = raw['equity'][ids]-(500000.+before)-cost*counts
    # Flat endpoint and all historical trade profits must reconcile.
    assert np.isclose(raw['balance'][-1]-500000,trades.trade_profit.sum(),atol=1e-6)
    assert np.isclose(raw['equity'][-1],raw['balance'][-1],atol=1e-6)
    assert np.isclose(eq[-1],selected.trade_profit.sum()-cost*len(selected),atol=1e-6)
    ts = np.r_[start_ms,ts,stop_ms-1]
    eq = np.r_[0.,eq,eq[-1]]
    peaks = np.maximum.accumulate(eq)
    dd = peaks-eq
    last_peak = np.maximum.accumulate(np.where(eq>=peaks-1e-9,np.arange(len(eq)),0))
    duration = (ts-ts[last_peak])/86400000.
    # A recovery sample closes the preceding underwater interval before it
    # becomes the next peak anchor. Include the whole interval through recovery.
    was_underwater = np.r_[False,eq[:-1]<peaks[:-1]-1e-9]
    previous_peak = np.r_[0,last_peak[:-1]]
    duration = np.where(was_underwater,
                        np.maximum(duration,(ts-ts[previous_peak])/86400000.),duration)
    at = int(dd.argmax())
    return dict(samples=len(eq)-2,sampled_open_equity_dd=float(dd[at]),
                sampled_open_equity_dd_duration_days=float(duration.max()),
                depth_peak_time=str(pd.to_datetime(ts[last_peak[at]],unit='ms')),
                depth_trough_time=str(pd.to_datetime(ts[at],unit='ms')),
                net_endpoint=float(eq[-1]),cost_per_trade=cost)


def scaled(trades,fraction):
    t = trades.copy()
    for name in ('trade_profit','net_dollars','initial_risk_dollars','fill_risk_dollars',
                 'holding_minutes','stress1_net_dollars','stress2_net_dollars'):
        t[name] *= fraction
    return t


def closed_path_duration(values, times, start, end):
    """Exit-sampled peak-to-recovery duration; unfinished DD extends to endpoint.

    The initial anchor is the first exit, excluding flat time before any trade.
    Later ties reset the anchor to the latest at-peak exit. Recovery is included.
    """
    values = np.asarray(values, dtype=float)
    times = pd.DatetimeIndex(times)
    assert len(values) == len(times) and np.isfinite(values).all()
    assert times.is_monotonic_increasing
    initial_time = times[0] if len(times) else pd.Timestamp(start)
    balance, peak, peak_time, depth, longest = 0., 0., initial_time, 0., 0.
    for time, pnl in zip(times, values):
        # Carry an existing underwater stretch through flat time up to recovery,
        # not merely to the preceding losing exit (which can be days earlier).
        if balance < peak-1e-9:
            longest = max(longest,(time-peak_time).total_seconds()/86400.)
        balance += float(pnl)
        depth = max(depth, peak-balance)
        if balance >= peak-1e-9:
            peak, peak_time = max(peak,balance), time
        else:
            longest = max(longest,(time-peak_time).total_seconds()/86400.)
    if balance < peak-1e-9:
        longest = max(longest,(pd.Timestamp(end)-peak_time).total_seconds()/86400.)
    return float(depth), float(longest)


def replay_metrics(trades, calendar):
    """Preserve original economics, adding closed dollar and normalized-R duration."""
    out = base.metrics(trades,calendar)
    order = trades.sort_values(['exit_time','entry_time','ticket'],kind='stable')
    endpoint = pd.Timestamp(calendar[-1])+pd.Timedelta(days=1)
    depth,duration = closed_path_duration(order.net_dollars,order.exit_time,calendar[0],endpoint)
    assert np.isclose(depth,out['closed_trade_dd'],rtol=0,atol=1e-7)
    r_depth,r_duration = closed_path_duration(order.net_r,order.exit_time,calendar[0],endpoint)
    out.update(closed_trade_dd_duration_days=duration,closed_trade_r_dd=r_depth,
               closed_trade_r_dd_duration_days=r_duration)
    # The R path gives every trade equal planned-risk weight; it is not account equity.
    return out


def candidate_changes(off, on):
    """Candidate identity survives ticket/ordinal changes and position-state effects."""
    for frame in (off,on):
        assert not frame.duplicated(CANDIDATE_IDENTITY).any()
    fields = ['candidate_id','blocked','order','retcode','send_success','known','unfavorable']
    joined = off[CANDIDATE_IDENTITY+fields].merge(on[CANDIDATE_IDENTITY+fields],
        on=CANDIDATE_IDENTITY,how='outer',suffixes=('_off','_on'),indicator=True,
        validate='one_to_one')
    joined['category'] = joined['_merge'].map({'left_only':'off_only','right_only':'on_only','both':'shared'}).astype(str)
    joined['session'] = joined.submitted.dt.normalize()
    return joined.drop(columns='_merge').sort_values(CANDIDATE_IDENTITY,kind='stable').reset_index(drop=True)


def accepted_order_states(candidates, orders, trades):
    """Final states of accepted entry orders only; exclude closing market orders."""
    accepted = candidates.loc[candidates.order.gt(0),['order','submitted','time_msc']]
    assert accepted.order.is_unique and orders.order.is_unique
    linked = accepted.merge(orders,on='order',how='left',validate='one_to_one')
    assert linked.state.notna().all(), 'Accepted entry order absent from final order history'
    assert linked.type.eq(4).all(), 'Accepted RTL entry is not a buy stop'
    assert linked.state.isin(ORDER_STATES).all()
    assert linked.setup_msc.eq(linked.time_msc).all(), 'Candidate and accepted order setup time differ'
    trade_ids = set(trades.ticket)
    linked['has_trade'] = linked.order.isin(trade_ids)
    assert linked.loc[linked.state.eq(4),'has_trade'].all(), 'Filled accepted order lacks a complete trade'
    assert linked.loc[linked.has_trade,'state'].eq(4).all(), 'Trade references non-filled accepted order'
    assert set(linked.loc[linked.has_trade,'order']) == trade_ids
    rows = []
    for state_code,state in ORDER_STATES.items():
        part = linked.loc[linked.state.eq(state_code)]
        rows.append(dict(state_code=state_code,state=state,accepted_orders=len(part),
                         complete_trades=int(part.has_trade.sum())))
    assert sum(r['accepted_orders'] for r in rows) == len(accepted)
    return rows


def analyze():
    off = validate_baseline()
    on,candidates,job = load_run('on')
    candidate_frames = {'on':candidates}
    candidate_frames['off'] = pd.read_csv(RUN/'candidates_off.csv',parse_dates=['submitted','session'])
    candidate_detail = candidate_changes(candidate_frames['off'],candidate_frames['on'])
    order_history = {variant:read_output(f'vwap_replay_20261026_{variant}','orders') for variant in ('off','on')}
    source = pd.read_csv(STUDY/'features_full_hlc3.csv',usecols=['bar_time'],parse_dates=['bar_time'])
    all_dates = pd.DatetimeIndex(source.bar_time.dt.normalize().unique()).sort_values()
    summaries,annual,daily,changes,parts,open_rows,counts,states = [],[],[],[],[],[],[],[]
    for era,(start,stop) in ERAS.items():
        calendar = all_dates[(all_dates>=start)&(all_dates<stop)]
        a,b = off.loc[off.era.eq(era)],on.loc[on.era.eq(era)]
        omission = a.loc[~a.unfavorable]
        holding = b.holding_minutes.sum()/a.holding_minutes.sum()
        risk = b.initial_risk_dollars.sum()/a.initial_risk_dollars.sum()
        frames = dict(baseline=a,ledger_omission=omission,gated=b,
                      static_holding=scaled(a,holding),static_planned_risk=scaled(a,risk))
        for curve,t in frames.items():
            row = dict(era=era,curve=curve,**replay_metrics(t,calendar),
                       retained_holding_fraction=float(holding),retained_planned_risk_fraction=float(risk))
            row['net_over_daily_dd'] = row['net_dollars']/row['daily_close_dd'] if row['daily_close_dd'] else np.nan
            summaries.append(row)
            ds = t.groupby('session').net_dollars.sum().reindex(calendar,fill_value=0.)
            daily.extend(dict(era=era,curve=curve,session=d,net_dollars=float(v)) for d,v in ds.items())
            for year in sorted(t.year.unique()):
                y = t.loc[t.year.eq(year)]
                annual.append(dict(era=era,curve=curve,year=int(year),partial=bool(year==2026),
                                   **replay_metrics(y,calendar[calendar.year==year])))
        for label,left in [('gated_minus_baseline',a),('gated_minus_omission',omission)]:
            detail,rows = attribution(left,b,label)
            detail['era'] = era
            changes.append(detail)
            parts.extend(dict(era=era,**r) for r in rows)
        for variant,t in [('off',off),('on',on)]:
            for extra in (0,1,2):
                open_rows.append(dict(era=era,variant=variant,**equity_metrics(variant,t,start,stop,1.05+extra)))
            for year in range(pd.Timestamp(start).year,pd.Timestamp(stop).year+1):
                ys,ye=max(pd.Timestamp(start),pd.Timestamp(year,1,1)),min(pd.Timestamp(stop),pd.Timestamp(year+1,1,1))
                if ys<ye:
                    open_rows.append(dict(era=era,variant=variant,year=year,**equity_metrics(variant,t,ys,ye)))
        for variant in ('off','on'):
            c = candidate_frames[variant]
            c = c.loc[c.submitted.ge(start)&c.submitted.lt(stop)]
            candidate_part = candidate_detail.loc[candidate_detail.submitted.ge(start)&candidate_detail.submitted.lt(stop)]
            category = 'on_only' if variant=='on' else 'off_only'
            arm_only = candidate_part.loc[candidate_part.category.eq(category)]
            counts.append(dict(era=era,variant=variant,candidates=len(c),blocked=int(c.blocked.sum()),
                               accepted=int(c.order.gt(0).sum()),unknown=int(c.known.eq(0).sum()),
                               unfavorable=int(c.unfavorable.sum()),
                               request_without_order=int((c.order.eq(0)&c.blocked.eq(0)).sum()),
                               shared_candidates=int(candidate_part.category.eq('shared').sum()),
                               arm_only_candidates=len(arm_only),
                               newly_enabled_candidates=len(arm_only) if variant=='on' else 0,
                               arm_only_accepted_orders=int(arm_only['order_'+variant].gt(0).sum()),
                               arm_only_blocked=int(arm_only['blocked_'+variant].eq(1).sum())))
            arm_trades = a if variant=='off' else b
            states.extend(dict(era=era,variant=variant,**r)
                          for r in accepted_order_states(c,order_history[variant],arm_trades))
    candidate_detail = candidate_detail.loc[candidate_detail.submitted.ge('2016-01-01')&candidate_detail.submitted.lt('2026-10-01')].copy()
    candidate_detail['era'] = np.where(candidate_detail.submitted.lt('2020-01-01'),'2016-19','2020-26')
    outputs = {'summaries.csv':pd.DataFrame(summaries),'yearly.csv':pd.DataFrame(annual),
               'daily_curves.csv':pd.DataFrame(daily),'attribution.csv':pd.DataFrame(parts),
               'trade_changes.csv':pd.concat(changes,ignore_index=True),
               'open_equity.csv':pd.DataFrame(open_rows),'candidate_counts.csv':pd.DataFrame(counts),
               'candidate_changes.csv':candidate_detail,'accepted_order_states.csv':pd.DataFrame(states)}
    for name,frame in outputs.items():
        frame.to_csv(RUN/name,index=False,float_format='%.17g')
    write_json('analysis_audit.json',dict(all_passed=True,baseline_exact=True,
        off_trades=len(off),on_trades=len(on),off_primary=int(off.primary.sum()),on_primary=int(on.primary.sum()),
        analyzer_sha256=base.digest(Path(__file__)),output_rows={n:len(f) for n,f in outputs.items()},
        outputs_sha256={n:base.digest(RUN/n) for n in outputs},strategy_adopted=False))
    print(outputs['summaries.csv'][['era','curve','trades','net_dollars','daily_close_dd','daily_dd_duration_days']].to_string(index=False),flush=True)
    print(outputs['attribution.csv'].to_string(index=False),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['baseline','analyze'])
    args = parser.parse_args()
    validate_baseline() if args.action=='baseline' else analyze()
