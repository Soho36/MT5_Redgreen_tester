"""Matched native replays for one NQ tick outside the original red candle.

Run prepare, compile, off, then on with the project venv. The parent
zero-offset experiment is read only. candle_range stays the raw signal width;
the actual 1R reference is the trade's original stop minus its fill.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pandas as pd

from analyze_rtl_failed_breakout_short import SYMBOL
from analyze_rtl_short_vwap import economics, parse_short_report
from prepare_gg_outside import once
from prepare_rtl_failed_breakout_short import RUN as ZERO, TAG as ZERO_TAG, EXPERT as ZERO_EA
from project_paths import PROJECT_ROOT as ROOT
from run_rtl_vwap_replay import COMMON, INSTALL, SOURCE_DATA, digest, hidden_process, save_json

RUN = ROOT / 'Reports/rtl_failed_breakout_buffered_20261106'
PROTOCOL = ROOT / 'docs/baseline/rtl-failed-breakout-short/ONE_TICK_PROTOCOL.md'
EXPERT = 'RTL_failed_breakout_buffered'
FOLDER = 'CodexFailedBreakoutBuffered'
TAG = 'rtlfailedbuf_20261106'
OFFSET = 0.25  # Exchange tick on NQ/MNQ. The custom symbol's point is different.
VARIANTS = ('off', 'on')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def prepare():
    if (RUN / 'manifest.json').exists():
        raise RuntimeError('Preserve the already-prepared buffered study')
    assert PROTOCOL.exists() and load(ZERO / 'baseline_validation.json')['all_passed']
    prior = load(ZERO / 'manifest.json')['prepared_sha256']
    for name, expected in prior.items():
        assert digest(ZERO / name) == expected, name
    RUN.mkdir(parents=True, exist_ok=True)
    source = (ZERO / f'{ZERO_EA}.mq5').read_text(encoding='utf-8')
    for old, new in [('req.price = g_fbLow;', 'req.price = g_fbLow - 0.25;'),
                     ('req.sl = g_fbHigh;', 'req.sl = g_fbHigh + 0.25;'),
                     ('double entry = l1;', 'double entry = l1 - 0.25;'),
                     ('double stop  = h1;', 'double stop  = h1 + 0.25;')]:
        source = once(source, old, new)
    (RUN / f'{EXPERT}.mq5').write_text(source, encoding='utf-8')
    shutil.copyfile(ZERO / 'early_closes.mqh', RUN / 'early_closes.mqh')
    for variant in VARIANTS:
        old_tag = f'{ZERO_TAG}_{variant}'
        tag = f'{TAG}_{variant}'
        template = (ZERO / (old_tag + '.ini')).read_text(encoding='utf-16')
        config = once(template, f'Expert=CodexFailedBreakoutShort\\{ZERO_EA}.ex5',
                      f'Expert={FOLDER}\\{EXPERT}.ex5')
        config = once(config, 'Report=' + old_tag + '.htm', 'Report=' + tag + '.htm')
        config = once(config, 'RunTag=' + old_tag, 'RunTag=' + tag)
        (RUN / (tag + '.ini')).write_text(config, encoding='utf-16')
    prepared = [p for p in RUN.iterdir() if p.suffix in ('.ini', '.mq5', '.mqh')]
    save_json(RUN / 'manifest.json', dict(
        original_run=ZERO.name, price_offset_points=OFFSET, expert=EXPERT,
        unchanged_fields='raw signal high/low and ledger candle_range',
        input_sha256={str(p): digest(p) for p in (
            PROTOCOL, Path(__file__), ZERO / 'manifest.json', ZERO / 'baseline_validation.json')},
        parent_sha256=prior, prepared_sha256={p.name: digest(p) for p in prepared}))


def check_inputs():
    manifest = load(RUN / 'manifest.json')
    for prefix, key in [(ZERO, 'parent_sha256'), (RUN, 'prepared_sha256')]:
        for name, expected in manifest[key].items():
            assert digest(prefix / name) == expected, name
    for path, expected in manifest['input_sha256'].items():
        assert digest(path) == expected, path


def compile_ea():
    check_inputs()
    if (RUN / 'compile.completed.json').exists():
        raise RuntimeError('Preserve the compiled study binary')
    log = RUN / 'compile.log'
    process = hidden_process([str(INSTALL / 'MetaEditor64.exe'), '/compile:' + str(RUN / (EXPERT + '.mq5')),
                              '/log:' + str(log)], timeout=180)
    output = log.read_text(encoding='utf-16', errors='replace')
    assert 'Result: 0 errors, 0 warnings' in output, output[-2000:]
    save_json(RUN / 'compile.completed.json', dict(**process, binary_sha256=digest(RUN / (EXPERT + '.ex5'))))


def run_native(variant):
    check_inputs()
    tag = TAG + '_' + variant
    check = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq terminal64.exe', '/FO', 'CSV', '/NH'],
                           capture_output=True, text=True, check=True)
    if 'terminal64.exe' in check.stdout.lower():
        raise RuntimeError('Terminal already in use; preserve its current work')
    files = [f'runband_{tag}_1.00.csv', f'runband_{tag}_1.00_stats.csv', f'failed_breakout_{tag}.csv']
    for name in files:
        if (COMMON / name).exists() or (RUN / name).exists():
            raise RuntimeError('Preserve existing output: ' + name)
    report = SOURCE_DATA / (tag + '.htm')
    if report.exists() or (RUN / (tag + '.started.json')).exists():
        raise RuntimeError('Preserve existing native report/run record')
    binary = RUN / (EXPERT + '.ex5')
    expected_binary = load(RUN / 'compile.completed.json')['binary_sha256']
    assert digest(binary) == expected_binary
    target = SOURCE_DATA / 'MQL5/Experts' / FOLDER / binary.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert digest(target) == expected_binary, 'Preserve existing changed binary'
    else:
        shutil.copyfile(binary, target)
    config = RUN / (tag + '.ini')
    settings = config.read_text(encoding='utf-16').splitlines()
    for required in ('UseRemote=0', 'UseCloud=0', 'Visual=0', 'Enabled=0', 'AllowLiveTrading=0'):
        assert required in settings, required
    assert not any(s.startswith(('Password=', 'Server=', 'Login=')) for s in settings)
    record = dict(tag=tag, dedicated_tester_only_binary=True, binary_sha256=expected_binary,
                  config_sha256=digest(config), protocol_sha256=digest(PROTOCOL))
    save_json(RUN / (tag + '.started.json'), record)
    print('Starting native buffered ' + variant, flush=True)
    process = hidden_process([str(INSTALL / 'terminal64.exe'), '/config:' + str(config)], timeout=900, cwd=INSTALL)
    assert process['returncode'] == 0, process
    for name in files:
        shutil.copyfile(COMMON / name, RUN / name)
    shutil.copyfile(report, RUN / report.name)
    record.update(process, outputs={n: digest(RUN / n) for n in files}, report_sha256=digest(report))
    save_json(RUN / (tag + '.completed.json'), record)
    print('Completed native buffered ' + variant, flush=True)


def check_native(variant):
    tag = f'{TAG}_{variant}'
    done = load(RUN / (tag + '.completed.json'))
    for name, expected in done['outputs'].items():
        assert digest(RUN / name) == expected, name
    report = RUN / (tag + '.htm')
    assert digest(report) == done['report_sha256']
    trades = economics(parse_short_report(report, SYMBOL))
    ledger = pd.read_csv(RUN / f'runband_{tag}_1.00.csv', sep='\t', encoding='utf-16')
    stats = pd.read_csv(RUN / f'runband_{tag}_1.00_stats.csv', sep='\t', encoding='utf-16').iloc[0]
    assert len(trades) == len(ledger) == int(stats.trades)
    assert np.array_equal(trades.ticket, ledger.ticket)
    assert np.array_equal(trades.trade_profit, ledger.trade_profit)
    assert np.allclose((trades.fill_price - trades.exit_price) * 2, trades.trade_profit, atol=1e-8, rtol=0)
    assert np.array_equal(trades.fill_price, trades.requested_price)
    assert np.array_equal((ledger.candle_range + 2 * OFFSET) * 2, trades.initial_risk_dollars)
    assert np.isclose(trades.trade_profit.sum(), stats.net_profit, atol=1e-6, rtol=0)
    save_json(RUN / (tag + '.ledger_check.json'), dict(all_passed=True, native_trades=len(trades),
              gross_native_profit=float(stats.net_profit), initial_risk_includes_both_offsets=True))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=['prepare', 'compile', 'off', 'on'])
    action = ap.parse_args().action
    if action in VARIANTS:
        run_native(action)
        check_native(action)
    else:
        {'prepare': prepare, 'compile': compile_ea}[action]()
