"""Run the frozen immediate, delayed and plain-delayed red shorts in native MT5."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pandas as pd

from prepare_gg_outside import once
from project_paths import PROJECT_ROOT as ROOT
from run_rtl_failed_breakout_buffered import RUN as PRIOR, EXPERT as PRIOR_EA, TAG as PRIOR_TAG
from run_rtl_vwap_replay import COMMON, INSTALL, SOURCE_DATA, digest, hidden_process, save_json

RUN = ROOT / 'Reports/rtl_delayed_failed_breakout_20261106'
PROTOCOL = ROOT / 'docs/baseline/rtl-delayed-failed-breakout/PROTOCOL.md'
EXPERT = 'RTL_delayed_failed_breakout'
FOLDER = 'CodexDelayedFailedBreakout'
TAG = 'rtldelay_20261106'
MODES = {'immediate': 0, 'delayed': 1, 'plain': 2}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def build_source():
    s = (PRIOR / (PRIOR_EA + '.mq5')).read_text(encoding='utf-8')
    s = once(s, 'bool g_fbWatching = false;', '''input int FailedBreakoutTiming = 1; // 0 immediate, 1 delayed, 2 plain delay
bool g_fbWatching = false;
bool g_delayQualified = false;''')
    start = s.index('void TryFailedBreakout()')
    send = s.index('   MqlTradeRequest req = {};', start)
    end = s.index('// ======== HELPER FUNCTIONS ========', send)
    submit_order = 'void SubmitBufferedOrder()\n{\n' + s[send:end]
    lifecycle = '''
void TryFailedBreakout()
{
   if(!UseFailedBreakout || !g_fbWatching) return;
   if(iTime(_Symbol, _Period, 0) != g_fbBar) return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(g_delayQualified)
   {
      if(bid <= g_fbLow - 0.25)
      {
         FailedBreakoutLog("touched");
         g_delayQualified = false;
         g_fbWatching = false;
      }
      return;
   }
   if(bid <= g_fbHigh) return;
   if(FailedBreakoutTiming == 1)
   {
      g_delayQualified = true;
      FailedBreakoutLog("break");
      return;
   }
   g_fbWatching = false;
   SubmitBufferedOrder();
}

void FinishFailedBreakoutWatch(datetime barOpen)
{
   if(!g_fbWatching) return;
   g_fbWatching = false;
   if(!g_delayQualified) { FailedBreakoutLog("expired"); return; }
   g_delayQualified = false;
   if(barOpen / 86400 != g_fbBar / 86400 || barOpen != g_fbBar + PeriodSeconds(_Period)
      || !IsTradeWindow(barOpen) || IsAtOrAfterFlattenTime(barOpen))
      FailedBreakoutLog("session");
   else if(PositionSelect(_Symbol)) FailedBreakoutLog("occupied");
   else if(iClose(_Symbol, _Period, 1) < iOpen(_Symbol, _Period, 1))
      FailedBreakoutLog("replaced");
   else if(SymbolInfoDouble(_Symbol, SYMBOL_BID) <= g_fbLow - 0.25)
      FailedBreakoutLog("gap");
   else SubmitBufferedOrder();
}

'''
    s = once(s, s[start:end], submit_order + lifecycle)
    start = s.index('   // At a new bar, expire only the unarmed')
    end = s.index('   // Display session borders', start)
    s = once(s, s[start:end], '   FinishFailedBreakoutWatch(barOpen);\n\n')
    s = once(s, '          g_fbWatching = true;', '''          g_fbWatching = true;
          g_delayQualified = (FailedBreakoutTiming == 2);''')
    s = once(s, '   if(_Period != PERIOD_M30) return INIT_PARAMETERS_INCORRECT;',
             '   if(_Period != PERIOD_M30 || !UseFailedBreakout || FailedBreakoutTiming < 0 || FailedBreakoutTiming > 2) return INIT_PARAMETERS_INCORRECT;')
    return s


def prepare():
    assert PROTOCOL.exists() and load(PRIOR / 'independent_verification.json')['all_passed']
    if (RUN / 'manifest.json').exists():
        raise RuntimeError('Preserve existing prepared study')
    RUN.mkdir(parents=True, exist_ok=True)
    reference = PRIOR_TAG + '_on'
    prior_hashes = load(PRIOR / 'manifest.json')['prepared_sha256']
    for name in [PRIOR_EA + '.mq5', 'early_closes.mqh', reference + '.ini']:
        assert digest(PRIOR / name) == prior_hashes[name], name
    (RUN / (EXPERT + '.mq5')).write_text(build_source(), encoding='utf-8')
    shutil.copyfile(PRIOR / 'early_closes.mqh', RUN / 'early_closes.mqh')
    original = (PRIOR / (reference + '.ini')).read_text(encoding='utf-16')
    for variant, mode in MODES.items():
        tag = f'{TAG}_{variant}'
        config = once(original, f'Expert=CodexFailedBreakoutBuffered\\{PRIOR_EA}.ex5',
                      f'Expert={FOLDER}\\{EXPERT}.ex5')
        config = once(config, 'Report=' + reference + '.htm', 'Report=' + tag + '.htm')
        config = once(config, 'RunTag=' + reference, 'RunTag=' + tag)
        config = once(config, 'UseFailedBreakout=true\n',
                      f'UseFailedBreakout=true\nFailedBreakoutTiming={mode}\n')
        (RUN / (tag + '.ini')).write_text(config, encoding='utf-16')
    parent_inputs = [PRIOR / p for p in [PRIOR_EA + '.mq5', reference + '.ini', 'early_closes.mqh',
                     'manifest.json', 'independent_verification.json', f'runband_{reference}_1.00.csv',
                     f'runband_{reference}_1.00_stats.csv', f'failed_breakout_{reference}.csv']]
    save_json(RUN / 'manifest.json', dict(
        modes=MODES, offset_each_side=0.25, cost_dollars=1.05, point_value=2,
        frozen_inputs={str(p): digest(p) for p in [
            PROTOCOL, Path(__file__), *parent_inputs, *RUN.glob('*.mq5'), *RUN.glob('*.mqh'), *RUN.glob('*.ini')]}))


def frozen():
    for name, expected in load(RUN / 'manifest.json')['frozen_inputs'].items():
        assert digest(name) == expected, name


def compile_ea():
    frozen()
    if (RUN / 'compile.completed.json').exists():
        raise RuntimeError('Preserve existing compiled binary')
    log = RUN / 'compile.log'
    process = hidden_process([str(INSTALL / 'MetaEditor64.exe'), '/compile:' + str(RUN / (EXPERT + '.mq5')),
                              '/log:' + str(log)], timeout=180)
    out = log.read_text(encoding='utf-16', errors='replace')
    assert 'Result: 0 errors, 0 warnings' in out, out[-2000:]
    save_json(RUN / 'compile.completed.json', dict(**process, binary_sha256=digest(RUN / (EXPERT + '.ex5'))))


def check_control(tag):
    reference = PRIOR_TAG + '_on'
    for name in [f'runband_{tag}_1.00.csv', f'failed_breakout_{tag}.csv']:
        assert digest(RUN / name) == digest(PRIOR / name.replace(tag, reference)), name
    def stats(folder, prefix):
        return pd.read_csv(folder / f'runband_{prefix}_1.00_stats.csv', sep='\t', encoding='utf-16')
    current, old = stats(RUN, tag), stats(PRIOR, reference)
    pd.testing.assert_frame_equal(current.drop(columns='run_tag'), old.drop(columns='run_tag'), check_exact=True)
    save_json(RUN / 'baseline_validation.json', dict(all_passed=True, ledger_byte_identical=True,
              events_byte_identical=True, native_statistics_identical=True, trades=int(old.trades.iloc[0])))


def run_native(variant):
    frozen()
    if variant != 'immediate':
        assert load(RUN / 'baseline_validation.json')['all_passed']
    tag = f'{TAG}_{variant}'
    config = RUN / (tag + '.ini')
    lines = config.read_text(encoding='utf-16').splitlines()
    assert all(x in lines for x in ('UseLocal=1', 'UseRemote=0', 'UseCloud=0', 'Visual=0',
                                     'AllowLiveTrading=0', 'Enabled=0', f'FailedBreakoutTiming={MODES[variant]}'))
    assert not any(line.startswith(('Password=', 'Server=', 'Login=')) for line in lines)
    files = [f'runband_{tag}_1.00.csv', f'runband_{tag}_1.00_stats.csv', f'failed_breakout_{tag}.csv']
    report = SOURCE_DATA / (tag + '.htm')
    if any((RUN / f).exists() or (COMMON / f).exists() for f in files) or report.exists() or (RUN / (tag + '.started.json')).exists():
        raise RuntimeError('Preserve existing native outputs')
    check = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq terminal64.exe', '/FO', 'CSV', '/NH'],
                           capture_output=True, text=True, check=True)
    if 'terminal64.exe' in check.stdout.lower():
        raise RuntimeError('An existing terminal is open; preserve its current work')
    binary = RUN / (EXPERT + '.ex5')
    binary_sha = load(RUN / 'compile.completed.json')['binary_sha256']
    assert digest(binary) == binary_sha
    target = SOURCE_DATA / 'MQL5/Experts' / FOLDER / binary.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert digest(target) == binary_sha, 'Preserve existing binary'
    else:
        shutil.copyfile(binary, target)
    record = dict(tag=tag, dedicated_tester_only_binary=True, binary_sha256=binary_sha,
                  protocol_sha256=digest(PROTOCOL), config_sha256=digest(config))
    save_json(RUN / (tag + '.started.json'), record)
    print('Starting native', variant, flush=True)
    process = hidden_process([str(INSTALL / 'terminal64.exe'), '/config:' + str(config)], timeout=900, cwd=INSTALL)
    assert process['returncode'] == 0, process
    for name in files:
        shutil.copyfile(COMMON / name, RUN / name)
    shutil.copyfile(report, RUN / report.name)
    ledger = pd.read_csv(RUN / files[0], sep='\t', encoding='utf-16')
    stats = pd.read_csv(RUN / files[1], sep='\t', encoding='utf-16').iloc[0]
    assert len(ledger) == int(stats.trades)
    assert np.isclose(ledger.trade_profit.sum(), stats.net_profit, rtol=0, atol=1e-6)
    record.update(process, outputs={n: digest(RUN / n) for n in files}, report_sha256=digest(report))
    save_json(RUN / (tag + '.completed.json'), record)
    if variant == 'immediate':
        check_control(tag)
    print('Completed native', variant, 'trades', len(ledger), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'compile', *MODES, 'all'])
    action = parser.parse_args().action
    if action == 'all':
        prepare()
        compile_ea()
        for variant in MODES:
            run_native(variant)
    elif action in MODES:
        run_native(action)
    else:
        {'prepare': prepare, 'compile': compile_ea}[action]()
