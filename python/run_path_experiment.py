"""Run passive path observers with unchanged strategy and complete-ledger gates."""
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT
from run_mt5_job import compile_expert, run_job

RUN = ROOT / 'Reports' / 'path_experiment_20261009'
_REAL_RUN = subprocess.run


def hidden_run(*args, **kwargs):
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    kwargs.setdefault('startupinfo', info)
    kwargs.setdefault('timeout', 600)
    return _REAL_RUN(*args, **kwargs)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def completed(job):
    marker = RUN / f"{job['tag']}.completed.json"
    if not marker.exists():
        return False
    result = json.loads(marker.read_text())
    if result.get('tag') != job['tag']:
        raise RuntimeError('Wrong completion tag')
    for name in job['outputs']:
        if digest(RUN/name) != result['outputs'].get(name):
            raise RuntimeError(f'Completed output changed: {name}')
    return True


def validate_job(job):
    tag = job['tag']
    raw = RUN / job['outputs'][0]
    if raw.read_bytes() != Path(job['reference_raw']).read_bytes():
        raise RuntimeError(f'{tag}: original RAW ledger byte replication failed')
    paths = pd.read_csv(RUN/f'path_{tag}_trades.csv',sep='\t',encoding='utf-16')
    ref = pd.read_csv(job['reference_audited'],sep='\t',encoding='utf-16')
    if paths.position_id.duplicated().any() or ref.ticket.duplicated().any() or len(paths) != len(ref):
        raise RuntimeError(f'{tag}: complete position count/identity failed')
    if not (paths.first_quote_time_msc == paths.entry_time_msc).all():
        raise RuntimeError(f'{tag}: first observation does not coincide with entry quote')
    merged = paths.merge(ref,on=None,left_on='position_id',right_on='ticket',validate='one_to_one',suffixes=('_path','_ref'))
    if len(merged) != len(ref):
        raise RuntimeError(f'{tag}: complete position IDs do not replicate')
    for name in ('entry_time','exit_time'):
        if not merged[f'{name}_path'].equals(merged[f'{name}_ref']):
            raise RuntimeError(f'{tag}: complete {name} does not replicate')
    for left,right in (('trade_profit_path','trade_profit_ref'),('requested_risk','candle_range')):
        if not np.allclose(merged[left],merged[right],rtol=0,atol=1e-8):
            raise RuntimeError(f'{tag}: complete {left} differs from audited {right}')
    summary = pd.read_csv(RUN/f'path_{tag}_summary.csv',sep='\t',encoding='utf-16')
    if len(summary) != 1 or summary.iloc[0]['run_tag'] != tag:
        raise RuntimeError(f'{tag}: observer summary invalid')
    row = summary.iloc[0]
    for key,value in (('observer_errors',0),('max_entry_lag_msc',0),('active_at_end',0),('counts_match',1),('profit_match',1),('exported_positions',len(ref))):
        if row[key] != value:
            raise RuntimeError(f'{tag}: observer summary {key}={row[key]} expected {value}')
    stats = pd.read_csv(RUN/job['outputs'][1],sep='\t',encoding='utf-16')
    if len(stats) != 1 or stats.iloc[0]['trades'] != len(ref):
        raise RuntimeError(f'{tag}: tester count differs')
    if not np.isclose(stats.iloc[0]['net_profit'],paths.trade_profit.sum(),rtol=0,atol=1e-6):
        raise RuntimeError(f'{tag}: tester profit differs')
    result = dict(tag=tag,raw_byte_equal=True,complete_audited_trades=len(ref),
                  complete_times_profits_risk_equal=True,observer_errors=0,
                  path_sha256=digest(RUN/f'path_{tag}_trades.csv'))
    (RUN/f'{tag}.replication.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f"PASS {tag}: raw byte equality, {len(ref):,} complete paths, zero observer errors, all totals equal",flush=True)
    return result


def main():
    manifest = json.loads((RUN/'manifest.json').read_text(encoding='utf-8'))
    for path, expected in manifest['input_hashes'].items():
        if digest(path) != expected:
            raise RuntimeError(f'Frozen input changed: {path}')
    subprocess.run = hidden_run
    compile_expert(RUN,manifest['expert'])
    validations=[]
    for index,job in enumerate(manifest['jobs'],1):
        if not completed(job):
            print(f"RUN {index}/6: {job['instrument']} {job['mode']}",flush=True)
            run_job(RUN,job['tag'],job['outputs'],manifest['expert'])
        validations.append(validate_job(job))
    (RUN/'replication.json').write_text(json.dumps(dict(all_passed=True,jobs=validations),indent=2)+'\n',encoding='utf-8')
    print('All six complete path runs replicate the original strategies and audited ledgers.',flush=True)


if __name__ == '__main__':
    main()
