"""Run the fixed granularity study, with native replication before new histories.

All terminal starts are research-only configurations with live trading disabled.
Stops rather than silently accepting missing or stale outputs. Resumable jobs.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from project_paths import PROJECT_ROOT as ROOT
from run_mt5_job import DATA, COMMON, INSTALL_DIR, compile_expert, run_job

RUN = ROOT / 'Reports' / 'granularity_20261009'
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
    with open(path, 'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def verify_job(job):
    mark = RUN / (job['tag'] + '.completed.json')
    if not mark.exists():
        return False
    info = json.loads(mark.read_text())
    if info.get('tag') != job['tag']:
        raise RuntimeError('Completion marker tag differs')
    for filename in job['outputs']:
        path = RUN / filename
        if not path.exists() or digest(path) != info['outputs'].get(filename):
            raise RuntimeError(f'Changed/missing completed output: {path}')
    return True


def check_native(jobs):
    previous = ROOT / 'Reports' / 'signal_colour_20261008'
    refs = {'rtl':'red_cap3', 'control':'market_control'}
    checks = {}
    for job in jobs:
        old = previous / f"runband_signal_20261008_{refs[job['mode']]}_1.00.csv"
        new = RUN / job['outputs'][0]
        checks[job['mode']] = dict(byte_identical=new.read_bytes()==old.read_bytes(),
                                  previous_sha256=digest(old), new_sha256=digest(new))
        if not checks[job['mode']]['byte_identical']:
            raise RuntimeError(f"Native {job['mode']} failed byte-exact replication; stop")
    (RUN / 'native_replication.json').write_text(json.dumps(checks,indent=2))
    print('PASS: native RTL and control reproduce previous ledgers byte for byte', flush=True)


def import_symbols(manifest):
    marker = RUN / 'import.completed.json'
    if marker.exists():
        status = json.loads(marker.read_text())
        if digest(RUN / 'import.tsv') != status['diagnostic_sha256']:
            raise RuntimeError('Changed completed import diagnostics')
        return
    importer = manifest['importer']
    target = DATA / 'MQL5' / 'Scripts' / 'CodexTrendlineResearch'
    target.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(RUN / f'{importer}.mq5', target / f'{importer}.mq5')
    log = RUN / 'import_compile.log'
    hidden_run([str(INSTALL_DIR / 'MetaEditor64.exe'),f'/compile:{target / (importer+".mq5")}',f'/log:{log}'])
    results = [s for s in log.read_text(encoding='utf-16',errors='replace').splitlines() if 'result' in s.lower()]
    if not results or '0 errors, 0 warnings' not in results[-1]:
        raise RuntimeError(f'Importer compile failed/warned: {results}')
    print(results[-1],flush=True)
    shutil.copyfile(target / f'{importer}.ex5',RUN / f'{importer}.ex5')
    stamp = datetime.now().strftime('%Y%m%d')
    remote_done = COMMON / 'granularity_20261009_import.done'
    remote_diag = COMMON / 'granularity_20261009_import.tsv'
    # These names are dedicated to this study; never touch source symbols/data.
    remote_done.unlink(missing_ok=True)
    started = time.time()
    print('Importing 14 owned synthetic histories; source remains untouched',flush=True)
    hidden_run([str(INSTALL_DIR / 'terminal64.exe'),f'/config:{RUN / "import.ini"}'],check=True)
    terminal_log = DATA / 'logs' / f'{stamp}.log'
    if terminal_log.exists():
        text = terminal_log.read_text(encoding='utf-16',errors='replace').splitlines()
        (RUN / 'import_terminal.log').write_text('\n'.join(text[-500:]),encoding='utf-8')
    if not remote_done.exists() or not remote_diag.exists():
        raise RuntimeError('Import did not complete; inspect import_terminal.log')
    done = remote_done.read_text().strip().split()
    if done != ['complete', str(manifest['source_rows']), '14']:
        raise RuntimeError(f'Unexpected import marker: {done}')
    shutil.copyfile(remote_diag,RUN / 'import.tsv')
    shutil.copyfile(COMMON / 'granularity_20261009_settings.tsv',RUN / 'symbol_settings.tsv')
    d = pd.read_csv(RUN / 'import.tsv',sep='\t')
    expected = manifest['source_year_counts']
    for variant in manifest['variants']:
        q=d[d.symbol==variant['symbol']]
        got={str(int(y)):int(n) for y,n in zip(q.year,q.bars)}
        if got!=expected:
            raise RuntimeError(f"Imported counts differ from source for {variant['key']}: {got} vs {expected}")
        for _, row in q.iterrows():
            year = str(int(row.year))
            span = manifest['source_year_spans'][year]
            if str(row['first']) != span['first'] or str(row['last']) != span['last']:
                raise RuntimeError(f'Imported timestamp span differs from CSV for {year}')
            sums = manifest['source_year_price_sums'][year]
            for col in ('open','high','low','close'):
                if int(row['sum_'+col]) != sums[col]:
                    raise RuntimeError(f'Imported native price sums differ from CSV: {year} {col}')
        if not (q.contract_size == d[d.symbol==manifest['source_symbol']].contract_size.iloc[0]).all():
            raise RuntimeError('Copied contract size mismatch')
        if not (q.tick_size==.25).all():
            raise RuntimeError('Copied native tick mismatch')
    status=dict(seconds=round(time.time()-started,1),rows=manifest['source_rows'],synthetic_symbols=14,
                diagnostic_sha256=digest(RUN/'import.tsv'))
    marker.write_text(json.dumps(status,indent=2))
    print(f'PASS: 14 synthetic histories imported and source yearly counts verified ({status["seconds"]} seconds)',flush=True)


def main():
    manifest=json.loads((RUN/'manifest.json').read_text())
    if 'trading_days' not in manifest:
        from analyze_granularity_candles import analyze
        print('Computing frozen source/session and candle diagnostics',flush=True)
        cache = RUN / 'source_calendar.json'
        metadata = json.loads(cache.read_text()) if cache.exists() else analyze(RUN)
        if metadata.get('end_exclusive', manifest['end_exclusive']) != manifest['end_exclusive']:
            metadata = analyze(RUN)
        manifest.update(metadata)
        (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    for path, expected in manifest['input_hashes'].items():
        if digest(Path(path))!=expected:
            raise RuntimeError(f'Frozen input changed: {path}')
    subprocess.run=hidden_run
    native=[j for j in manifest['jobs'] if j['variant']=='k1_o0']
    compile_expert(RUN,manifest['expert'])
    for job in native:
        if not verify_job(job):
            print('RUN native '+job['mode'],flush=True)
            run_job(RUN,job['tag'],job['outputs'],manifest['expert'])
    check_native(native)
    import_symbols(manifest)
    for index,job in enumerate(manifest['jobs'],1):
        if verify_job(job):
            continue
        print(f"RUN {index}/{len(manifest['jobs'])}: {job['variant']} {job['mode']}",flush=True)
        run_job(RUN,job['tag'],job['outputs'],manifest['expert'])
    print('All 30 jobs complete and hashes verified',flush=True)


if __name__=='__main__':
    main()


