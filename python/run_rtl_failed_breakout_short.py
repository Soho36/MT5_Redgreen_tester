"""Native historical MT5 runs; OFF must reproduce the red-short control before ON."""
import json
import re
import shutil
import subprocess
import sys
import pandas as pd
from prepare_rtl_failed_breakout_short import RUN, BASE, TAG, EXPERT, PROTOCOL
from run_rtl_vwap_replay import INSTALL, SOURCE_DATA, COMMON, digest, hidden_process, save_json


def baseline_check():
    mine = RUN / f'runband_{TAG}_off_1.00.csv'
    base = BASE / 'runband_ggredshort_20261021_control_1.00.csv'
    a = pd.read_csv(RUN / f'runband_{TAG}_off_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
    b = pd.read_csv(BASE / 'runband_ggredshort_20261021_control_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
    keys = ('trades', 'net_profit', 'gross_profit', 'gross_loss', 'equity_dd', 'balance_dd')
    values = {k: dict(new=float(a[k]), reference=float(b[k])) for k in keys}
    passed = mine.read_bytes() == base.read_bytes() and all(v['new'] == v['reference'] for v in values.values())
    save_json(RUN / 'baseline_validation.json', dict(all_passed=bool(passed),
              native_ledger_byte_identical=mine.read_bytes() == base.read_bytes(), native_totals=values))
    assert passed, values
    print('Native OFF reproduces the red-short baseline byte for byte.', flush=True)


def main():
    variant = sys.argv[1]
    assert variant in ('off', 'on')
    if variant == 'on':
        assert json.loads((RUN / 'baseline_validation.json').read_text())['all_passed']
    tag = TAG + '_' + variant
    manifest = json.loads((RUN / 'manifest.json').read_text())
    job = next(j for j in manifest['jobs'] if j['tag'] == tag)
    if (RUN / (tag + '.completed.json')).exists():
        raise RuntimeError('Preserve completed run')
    for path, expected in manifest['input_hashes'].items():
        assert digest(path) == expected, 'Frozen input changed: ' + path
    for name, expected in manifest['prepared_sha256'].items():
        assert digest(RUN / name) == expected, 'Prepared input changed: ' + name
    check = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq terminal64.exe', '/FO', 'CSV', '/NH'], capture_output=True, text=True)
    if 'terminal64.exe' in check.stdout.lower():
        raise RuntimeError('Terminal already running; preserve its current work')
    binary = RUN / (EXPERT + '.ex5')
    compiled = json.loads((RUN / 'compile.completed.json').read_text())
    assert compiled['binary_sha256'] == digest(binary)
    assert 'if(!MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;' in (RUN / (EXPERT + '.mq5')).read_text(encoding='utf-8')
    target = SOURCE_DATA / 'MQL5/Experts/CodexFailedBreakoutShort'
    target.mkdir(parents=True, exist_ok=True)
    dest = target / binary.name
    if dest.exists():
        assert digest(dest) == digest(binary), 'Preserve changed existing binary'
    else:
        shutil.copyfile(binary, dest)
    config = (RUN / (tag + '.ini')).read_text(encoding='utf-16')
    assert 'UseRemote=0' in config and 'UseCloud=0' in config and 'Visual=0' in config
    assert 'AllowLiveTrading=0' in config and 'Enabled=0' in config
    assert not re.search(r'^(Password|Server|Login)=', config, re.M)
    launch = RUN / (tag + '.native.ini')
    launch.write_text(config, encoding='utf-16')
    for name in job['outputs']:
        if (COMMON / name).exists() or (RUN / name).exists():
            raise RuntimeError('Preserve existing output: ' + name)
    record = dict(tag=tag, execution='native MT5 historical Strategy Tester', live_trading_enabled=False,
                  dedicated_tester_only_binary=True, binary_sha256=digest(binary), config_sha256=digest(launch),
                  protocol_sha256=digest(PROTOCOL))
    save_json(RUN / (tag + '.started.json'), record)
    print('Launching native historical ' + variant + ' test', flush=True)
    process = hidden_process([str(INSTALL / 'terminal64.exe'), '/config:' + str(launch)], timeout=900, cwd=INSTALL)
    for name in job['outputs']:
        assert (COMMON / name).exists(), name
        shutil.copyfile(COMMON / name, RUN / name)
    report = None
    for folder in (SOURCE_DATA, INSTALL):
        candidate = folder / (tag + '.htm')
        if candidate.exists():
            shutil.copyfile(candidate, RUN / candidate.name)
            report = RUN / candidate.name
            break
    assert report is not None, 'Native report missing'
    record.update(process, outputs={n: digest(RUN / n) for n in job['outputs']}, report_sha256=digest(report))
    save_json(RUN / (tag + '.completed.json'), record)
    if variant == 'off':
        baseline_check()
    print('Native ' + variant + ' complete', flush=True)


if __name__ == '__main__':
    main()
