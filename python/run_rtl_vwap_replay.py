"""Run the frozen VWAP replay in its own credential-free portable MT5 terminal.

This never launches, shuts down or installs an EA into the user's active MT5
instance.  Only the three installed binaries, custom-symbol definitions and the
requested symbol's yearly history are copied into this study's runtime.

Usage: run_rtl_vwap_replay.py setup | compile | run <job_tag>
Run the off arm first.  The on arm additionally requires baseline_validation.json
with all_passed=true; the runner does not manufacture that validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / 'Reports/rtl_vwap_replay_20261026'
RUNTIME = RUN / 'runtime'
INSTALL = Path(r'I:\Programs\1AMP Global (USA) MT5 Exchange-Traded Futures Only')
SOURCE_DATA = Path(os.environ['APPDATA']) / 'MetaQuotes/Terminal/F5855995045EF8A4C3CA7AE968872CF2'
COMMON = Path(os.environ['APPDATA']) / 'MetaQuotes/Terminal/Common/Files'
SYMBOL = 'MNQcontDTBNT20102026_2'
EXPERT_FOLDER = 'CodexVwapReplay'
BINARIES = ('terminal64.exe', 'metatester64.exe', 'MetaEditor64.exe')
OWNER = 'RTL VWAP full replay 2026-10-26; isolated portable runtime'


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')


def local(path):
    """Validate all generated paths stay inside the dedicated workspace run."""
    value = Path(path).resolve()
    if not value.is_relative_to(RUN.resolve()):
        raise ValueError('Generated path escapes study: '+str(value))
    return value


def hidden_process(command, *, timeout=600, cwd=None):
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    started = time.time()
    process = subprocess.Popen(command, cwd=cwd, startupinfo=info,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Only this child handle is terminated; never search/kill by process name.
        process.terminate()
        process.wait(timeout=30)
        raise RuntimeError(f'Owned portable process {process.pid} timed out after {timeout}s')
    return dict(pid=process.pid, returncode=code, seconds=round(time.time()-started, 2))


def setup_runtime():
    RUN.mkdir(parents=True, exist_ok=True)
    marker = RUN / 'runtime_setup.json'
    if marker.exists():
        record = json.loads(marker.read_text(encoding='utf-8'))
        if record.get('owner') != OWNER or record.get('runtime') != str(RUNTIME):
            raise RuntimeError('Existing runtime is not owned by this study')
        for name in BINARIES:
            if digest(RUNTIME/name) != record['copied_sha256'][name]:
                raise RuntimeError('Runtime binary changed: '+name)
        print('Existing isolated portable runtime verified.', flush=True)
        return
    if RUNTIME.exists() and any(RUNTIME.iterdir()):
        raise RuntimeError('Refusing unmarked nonempty runtime; inspect before resuming')
    RUNTIME.mkdir(parents=True, exist_ok=True)
    sources = {name: INSTALL/name for name in BINARIES}
    sources['bases/symbols.custom.dat'] = SOURCE_DATA/'bases/symbols.custom.dat'
    history = SOURCE_DATA/'bases/Custom/history'/SYMBOL
    years = sorted(history.glob('*.hcc'))
    if [p.stem for p in years] != [str(y) for y in range(2010, 2027)]:
        raise RuntimeError('Unexpected source yearly history inventory')
    for path in years:
        sources[f'bases/Custom/history/{SYMBOL}/{path.name}'] = path
    copied, originals = {}, {}
    for relative, source in sources.items():
        target = local(RUNTIME/relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        before = digest(source)
        shutil.copyfile(source, target)
        after = digest(source)
        if before != after or digest(target) != before:
            raise RuntimeError('Source changed during isolated copy: '+str(source))
        copied[relative] = before
        originals[str(source)] = before
    # Fresh settings contain no account, server, password or community identity.
    (RUNTIME/'Config').mkdir(exist_ok=True)
    (RUNTIME/'Config/common.ini').write_text(
        '[Common]\nKeepPrivate=0\nNewsEnable=0\n'
        '[Charts]\nMaxBars=10000000\n'
        '[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n', encoding='utf-16')
    save_json(marker, dict(owner=OWNER, runtime=str(RUNTIME), source_install=str(INSTALL),
        source_data=str(SOURCE_DATA), symbol=SYMBOL, copied_sha256=copied,
        source_sha256=originals, credentials_copied=False, user_terminal_modified=False,
        source_history_bytes=sum(p.stat().st_size for p in years),
        note='Only binaries, custom-symbol catalog and target yearly HCC; no account/config/profile files copied'))
    print(f'Prepared isolated portable runtime, {len(years)} source years; no credentials copied.', flush=True)


def load_manifest():
    manifest = json.loads((RUN/'manifest.json').read_text(encoding='utf-8'))
    for path, expected in manifest.get('input_hashes', {}).items():
        source = Path(path)
        if not source.is_absolute():
            source = RUN/source
        if digest(source) != expected:
            raise RuntimeError('Frozen replay input changed: '+str(source))
    for name, expected in manifest.get('prepared_sha256', {}).items():
        if digest(RUN/name) != expected:
            raise RuntimeError('Prepared replay input changed: '+name)
    return manifest


def compile_expert():
    setup_runtime()
    manifest = load_manifest()
    expert = manifest['expert']
    if not re.fullmatch(r'[A-Za-z0-9_]+', expert):
        raise ValueError('Unexpected expert name')
    target = local(RUNTIME/'MQL5/Experts'/EXPERT_FOLDER)
    target.mkdir(parents=True, exist_ok=True)
    inputs = [RUN/(expert+'.mq5'), *sorted(RUN.glob('*.mqh'))]
    for path in inputs:
        shutil.copyfile(path, target/path.name)
    log = RUN/'compile.log'
    process = hidden_process([str(RUNTIME/'MetaEditor64.exe'), '/portable',
        '/compile:'+str(target/(expert+'.mq5')), '/log:'+str(log)], timeout=180, cwd=RUNTIME)
    text = log.read_text(encoding='utf-16', errors='replace')
    results = [line for line in text.splitlines() if 'result' in line.lower()]
    if not results or '0 errors, 0 warnings' not in results[-1]:
        raise RuntimeError('Compile failed or warned: '+' | '.join(results[-3:]))
    output = target/(expert+'.ex5')
    shutil.copyfile(output, RUN/output.name)
    save_json(RUN/'compile.completed.json', dict(**process, result=results[-1],
        inputs_sha256={p.name:digest(p) for p in inputs}, binary_sha256=digest(output)))
    print(results[-1], flush=True)


def runtime_config(tag, expert):
    source = RUN/(tag+'.ini')
    text = source.read_text(encoding='utf-16')
    # Research-only protections remain explicit in the launch copy.
    for setting in ('Optimization=0', 'Model=1', 'Period=M30', 'Visual=0',
                    'UseRemote=0', 'UseCloud=0', 'ShutdownTerminal=1',
                    'Enabled=0', 'AllowLiveTrading=0', 'AllowDllImport=0'):
        if setting not in text.splitlines():
            raise RuntimeError('Unsafe or changed tester setting: '+setting)
    for key, value in {'Expert':f'{EXPERT_FOLDER}\\{expert}.ex5',
                       'Report':tag+'.htm'}.items():
        pattern = rf'^{key}=.*$'
        if len(re.findall(pattern, text, flags=re.MULTILINE)) != 1:
            raise RuntimeError('Nonunique tester key '+key)
        text = re.sub(pattern, lambda _:key+'='+value, text, flags=re.MULTILINE)
    if re.search(r'^(Password|Server|Login)=', text, re.MULTILINE):
        raise RuntimeError('Replay config must not carry credentials or a live account')
    if '[Charts]' not in text:
        text += '\n[Charts]\nMaxBars=10000000\n'
    destination = local(RUNTIME/(tag+'.ini'))
    destination.write_text(text, encoding='utf-16')
    return destination


def collect_logs(tag):
    """Keep isolated diagnostic logs, including failures, without touching user logs."""
    target = local(RUN/'runtime_logs'/tag)
    target.mkdir(parents=True, exist_ok=True)
    for path in RUNTIME.rglob('*.log'):
        relative = path.relative_to(RUNTIME)
        # A portable terminal's tester log may grow large. Preserve it as evidence.
        destination = local(target/relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)


def run_job(tag):
    setup_runtime()
    manifest = load_manifest()
    jobs = [j for j in manifest['jobs'] if j['tag'] == tag]
    if len(jobs) != 1:
        raise ValueError('Unknown or duplicate replay job '+tag)
    job = jobs[0]
    if not re.fullmatch(r'[A-Za-z0-9_]+', tag):
        raise ValueError('Unexpected job tag')
    marker = RUN/(tag+'.completed.json')
    if marker.exists():
        done = json.loads(marker.read_text(encoding='utf-8'))
        for name, expected in done['outputs'].items():
            if digest(RUN/name) != expected:
                raise RuntimeError('Completed output changed: '+name)
        print('Job already completed and preserved: '+tag, flush=True)
        return
    if tag.endswith('_on'):
        audit = json.loads((RUN/'baseline_validation.json').read_text(encoding='utf-8'))
        if not audit.get('all_passed'):
            raise RuntimeError('Gate-on requires successful exact baseline validation')
    expert = manifest['expert']
    binary = RUNTIME/'MQL5/Experts'/EXPERT_FOLDER/(expert+'.ex5')
    compile_record = json.loads((RUN/'compile.completed.json').read_text(encoding='utf-8'))
    if digest(binary) != compile_record['binary_sha256']:
        raise RuntimeError('Compiled binary differs from checked build')
    config = runtime_config(tag, expert)
    input_files = job.get('inputs_files', [])
    if not input_files and manifest.get('feature_common_name'):
        input_files = [manifest['feature_common_name']]
    common_copies = {}
    for name in input_files:
        if Path(name).name != name or not name.startswith('rtl_vwap_replay_20261026_'):
            raise ValueError('Non-study shared input name: '+name)
        source, destination = RUN/name, COMMON/name
        if destination.exists() and digest(destination) != digest(source):
            raise RuntimeError('Existing common input differs; preserve and investigate: '+name)
        if not destination.exists():
            shutil.copyfile(source, destination)
        common_copies[name] = digest(source)
    for name in job['outputs']:
        if Path(name).name != name or tag not in name:
            raise ValueError('Non-study output name: '+name)
        if (COMMON/name).exists() or (RUN/name).exists():
            raise RuntimeError('Uncompleted output already exists; preserve before rerun: '+name)
    print('Running isolated '+tag+'; original terminal is untouched.', flush=True)
    try:
        process = hidden_process([str(RUNTIME/'terminal64.exe'), '/portable', '/config:'+str(config)],
                                 timeout=600, cwd=RUNTIME)
    finally:
        collect_logs(tag)
    missing = []
    for name in job['outputs']:
        source = COMMON/name
        if source.exists():
            shutil.copyfile(source, RUN/name)
        else:
            missing.append(name)
    report = RUNTIME/(tag+'.htm')
    if report.exists():
        shutil.copyfile(report, RUN/report.name)
    else:
        missing.append(report.name)
    if missing:
        save_json(RUN/(tag+'.failed.json'), dict(**process, missing_outputs=missing,
            launch_config_sha256=digest(config), runtime=str(RUNTIME)))
        raise RuntimeError('Missing tester outputs: '+', '.join(missing))
    if process['returncode'] != 0:
        raise RuntimeError('Portable terminal returned '+str(process['returncode']))
    save_json(marker, dict(tag=tag, **process, runtime=str(RUNTIME),
        launch_config_sha256=digest(config), expert_sha256=digest(binary),
        shared_inputs_sha256=common_copies, outputs={name:digest(RUN/name) for name in job['outputs']},
        report_sha256=digest(RUN/report.name), user_terminal_modified=False,
        live_trading_enabled=False))
    print('Completed isolated '+tag+'; outputs and report collected.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['setup', 'compile', 'run'])
    parser.add_argument('tag', nargs='?')
    args = parser.parse_args()
    if args.action == 'setup':
        setup_runtime()
    elif args.action == 'compile':
        compile_expert()
    else:
        if not args.tag:
            parser.error('run requires one explicit tag; off must be validated before on')
        run_job(args.tag)


if __name__ == '__main__':
    main()
