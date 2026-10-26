"""Prepare the MT5 W1 check for the weekly plain-long control (2026-10-27).

One tester job: the frozen signal-colour EA (SignalMode 3 = market buy at every bar open while
flat, stop one previous-bar range below) on W1 with flattening and trade windows off. The
simulator's 'hold, raw, MT5 fills, plain control, ask entry' must reproduce it trade by trade
(docs/baseline/rtl-weekly-flatten/CONTROL_PROTOCOL.md).
Run: python/run_mt5_job.py Reports/rtl_weekly_control_20261027 RTL_weekly_control
"""
import hashlib
import json
import shutil

from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / 'Reports' / 'rtl_weekly_control_20261027'
FROZEN = ROOT / 'Reports' / 'signal_colour_20261008'
SOURCE_SHA256 = 'cb180737c65b5ac3d5b9ac9385105a9da48d64f748f66207d164e028242d1575'
EXPERT = 'RTL_weekly_control'
TAG = 'wkctrl_20261027_w1_plain_hold'


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    if (STUDY / 'manifest.json').exists():
        raise RuntimeError('Prepared study already exists; preserve it')
    source = FROZEN / 'RTL_signal.mq5'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256
    shutil.copyfile(source, STUDY / f'{EXPERT}.mq5')
    shutil.copyfile(ROOT / 'Reports/timeframe_baseline_20261015/early_closes.mqh', STUDY / 'early_closes.mqh')
    ini = (FROZEN / 'signal_20261008_market_control.ini').read_text(encoding='utf-16')
    changes = {'Expert': f'CodexResearch\\{EXPERT}.ex5', 'Period': 'W1', 'ToDate': '2026.10.15',
               'Report': f'{TAG}.htm', 'RunTag': TAG, 'UseFlattenEnd': 'false||false||0||true||N',
               'UseTradeWindow': 'false||false||0||true||N', 'SignalMode': '3', 'MaxRedRun': '0'}
    lines = ini.splitlines()
    for key, value in changes.items():
        assert sum(x.startswith(key + '=') for x in lines) == 1, key
        lines = [f'{key}={value}' if x.startswith(key + '=') else x for x in lines]
    (STUDY / f'{TAG}.ini').write_text('\n'.join(lines) + '\n', encoding='utf-16')
    job = {'tag': TAG, 'expert': EXPERT, 'period': 'W1', 'rr': 1.0, 'signal_mode': 3,
           'outputs': [f'runband_{TAG}_1.00.csv', f'runband_{TAG}_1.00_stats.csv']}
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in STUDY.iterdir()
              if p.is_file() and p.suffix in ('.mq5', '.mqh', '.ini')}
    manifest = {'symbol': 'MNQcontDTBNT20102026_2', 'model': '1-minute OHLC', 'source_sha256': SOURCE_SHA256,
                'purpose': 'W1 plain-long control check for the simulator', 'prepared_sha256': hashes, 'jobs': [job]}
    (STUDY / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Prepared {TAG} in {STUDY}')


if __name__ == '__main__':
    main()
