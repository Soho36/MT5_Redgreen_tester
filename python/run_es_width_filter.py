"""Run four ES width-filter arms with complete-ledger and source gates."""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from audit_granularity_ledgers import ensure_audited
from project_paths import PROJECT_ROOT as ROOT
from run_mt5_job import compile_expert, run_job
from run_path_experiment import digest, hidden_run

RUN=ROOT/'Reports/es_width_filter_20261011'


def read(path):
    return pd.read_csv(path,sep='\t',encoding='utf-16')


def require(ok,message):
    if not bool(ok): raise RuntimeError(message)


def completed(job):
    marker=RUN/(job['tag']+'.completed.json')
    if not marker.exists(): return False
    done=json.loads(marker.read_text(encoding='utf-8'))
    require(done.get('tag')==job['tag'],'Wrong completion tag')
    for name in job['outputs']:
        require(digest(RUN/name)==done['outputs'].get(name),'Completed output changed: '+name)
    return True


def validate_job(job,manifest,source):
    tag=job['tag']; paths=read(RUN/f'path_{tag}_trades.csv')
    audited_path=ensure_audited(RUN,job,{'symbol':job['symbol'],'grid_points':.25},job['pv'],fix_risk=True)
    audited=read(audited_path)
    require(len(paths)==len(audited) and not paths.position_id.duplicated().any(),'Complete position count/duplicates')
    merged=paths.merge(audited,left_on='position_id',right_on='ticket',validate='one_to_one',suffixes=('_path','_audit'))
    require(len(merged)==len(audited),'Complete IDs differ from orders/deals')
    for key in ('entry_time','exit_time'):
        require(merged[key+'_path'].equals(merged[key+'_audit']),tag+': complete times differ')
    for left,right in (('trade_profit_path','trade_profit_audit'),('requested_risk','candle_range')):
        require(np.allclose(merged[left],merged[right],rtol=0,atol=1e-8),tag+': complete profit/risk differs')
    require(paths.first_quote_time_msc.eq(paths.entry_time_msc).all(),'Observer missing entry quote')
    require(paths.actual_risk.gt(0).all(),'Nonpositive actual risk')
    require(np.allclose(paths.requested_entry-paths.initial_sl,paths.requested_risk,rtol=0,atol=1e-8),'Requested risk identity')
    require(np.allclose((paths.exit_price-paths.actual_fill)*job['pv'],paths.trade_profit,rtol=0,atol=1e-6),'Dollar point-value/profit mismatch')
    require(np.allclose(paths.mae_R,np.maximum(0,(paths.actual_fill-paths.min_bid)/paths.actual_risk),atol=1e-7,rtol=0),'MAE formula')
    require(np.allclose(paths.mfe_R,np.maximum(0,(paths.max_bid-paths.actual_fill)/paths.actual_risk),atol=1e-7,rtol=0),'MFE formula')
    summary=read(RUN/f'path_{tag}_summary.csv')
    require(len(summary)==1 and summary.iloc[0].run_tag==tag,'Bad observer summary')
    for key,value in (('observer_errors',0),('max_entry_lag_msc',0),('active_at_end',0),('counts_match',1),('profit_match',1),('exported_positions',len(paths))):
        require(summary.iloc[0][key]==value,f'{tag}: observer summary {key} differs')
    symbol=read(RUN/f'width_{tag}_symbol.csv')
    require(len(symbol)==1 and symbol.iloc[0].symbol==job['symbol'],'Bad symbol metadata')
    s=symbol.iloc[0]
    require(np.isclose(s.point,.01) and np.isclose(s.trade_tick_size,.25) and s.digits==2,'Symbol units differ')
    require(np.isclose(s.tick_value/s.trade_tick_size,job['pv']),'Symbol dollar point value differs')
    require(s.range_filter==(job['variant']=='min50'),'Wrong range-filter switch')
    if job['variant']=='min50':
        require(s.minimum_native_ticks==50 and s.minimum_price_points==12.5,'Wrong effective minimum')
        require(s.maximum_price_points>manifest['expected_maximum_source_width'],'Maximum filter bound binds')
        require(paths.requested_risk.ge(12.5).all(),'Filtered trade below minimum original width')
    orders=read(RUN/f'path_{tag}_orders.csv')
    require(not orders.order.duplicated().any(),'Repeated entry order')
    t=pd.to_datetime(orders.signal_bar_open,format='%Y.%m.%d %H:%M:%S')
    idx=source.index.get_indexer(t)
    require((idx>=0).all(),'Order signal missing from source')
    require(np.array_equal(orders[['signal_open','signal_high','signal_low','signal_close']].to_numpy(),source.iloc[idx].to_numpy()/4),'Order signal OHLC differs from source')
    signal_width=orders.signal_high-orders.signal_low
    if job['variant']=='min50': require(signal_width.ge(12.5).all(),'Filtered submitted signal below minimum')
    binding=paths.merge(orders,left_on='entry_order',right_on='order',validate='many_to_one')
    require(len(binding)==len(paths),'Missing original entry-order signal')
    require(np.array_equal(binding.requested_risk,binding.signal_high-binding.signal_low),'Original order risk does not equal signal width')
    bars=read(RUN/f'path_{tag}_bars.csv')
    idx=source.index.get_indexer(pd.to_datetime(bars.closed_bar_open,format='%Y.%m.%d %H:%M:%S'))
    require((idx>=0).all() and np.array_equal(bars.closed_close,source.iloc[idx].close.to_numpy()/4),'Observed M30 close/source mismatch')
    if job['variant']=='baseline':
        require((RUN/job['outputs'][0]).read_bytes()==Path(job['reference_raw']).read_bytes(),'Baseline raw byte replication failed')
        require((RUN/f'path_{tag}_trades.csv').read_bytes()==Path(job['reference_path']).read_bytes(),'Baseline complete path byte replication failed')
        ref=read(job['reference_audited'])
        require(audited[['ticket','entry_time','exit_time','trade_profit','candle_range']].equals(ref[['ticket','entry_time','exit_time','trade_profit','candle_range']]),'Baseline complete audited replication failed')
    audit=json.loads((RUN/(tag+'.ledger_audit.json')).read_text(encoding='utf-8'))
    result=dict(tag=tag,mode=job['mode'],variant=job['variant'],all_passed=True,trades=len(paths),
                observer_errors=0,max_entry_lag_msc=0,point=float(s.point),native_tick=float(s.trade_tick_size),
                actual_minimum_ticks=float(s.minimum_native_ticks),maximum_price_points=float(s.maximum_price_points),
                baseline_byte_replication=job['variant']=='baseline',minimum_order_width=float(signal_width.min()),
                minimum_trade_risk=float(paths.requested_risk.min()),boundary_50_tick_orders=int(signal_width.eq(12.5).sum()),
                recovered_logger_trades=audit['recovered_trades'],signal_ohlc_source_exact=True,observed_closes_source_exact=True,
                input_sha256={name:digest(RUN/name) for name in job['outputs']},audited_sha256=digest(audited_path),
                report_sha256=digest(RUN/(tag+'.htm')))
    (RUN/(tag+'.validation.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f'PASS {tag}: {len(paths):,} complete trades; symbol units, HTML audit, source and filter gates pass.',flush=True)
    return result


def main():
    manifest=json.loads((RUN/'manifest.json').read_text(encoding='utf-8'))
    for path,expected in manifest['input_hashes'].items():
        require(digest(path)==expected,'Frozen input changed: '+path)
    source=pd.read_csv(RUN/'source_ES_m30.csv',index_col=0,parse_dates=True)
    max_width=float(((source.high-source.low)/4).max())
    require(max_width==manifest['expected_maximum_source_width'],'Source maximum range differs')
    subprocess.run=hidden_run
    if not all(completed(j) for j in manifest['jobs']):
        compile_expert(RUN,manifest['expert'])
    results=[]
    for index,job in enumerate(manifest['jobs'],1):
        if not completed(job):
            print(f'RUN {index}/4: {job["mode"]} {job["variant"]}',flush=True)
            run_job(RUN,job['tag'],job['outputs'],manifest['expert'])
        results.append(validate_job(job,manifest,source))
    result=dict(all_passed=True,jobs=results,complete_paths=sum(x['trades'] for x in results),
                maximum_source_width=max_width,frozen_input_count=len(manifest['input_hashes']),
                manifest_sha256=digest(RUN/'manifest.json'))
    (RUN/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('All four complete EA runs validated.',flush=True)


if __name__=='__main__':
    main()
