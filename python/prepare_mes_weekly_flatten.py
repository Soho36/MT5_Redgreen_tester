"""Prepare the MT5 W1 check for the MES weekly-flatten study (2026-10-27).

One tester job: the frozen RTL_runband source of the YM/ES baselines (2026-10-23) on
MEScontDTBNT20102026_2, W1, with flattening and trade windows off (RTL held through nights
and weekends). The simulator's 'hold, raw, MT5 fills' variant on ES must reproduce it trade by
trade (docs/baseline/mes-weekly-flatten/PROTOCOL.md).
Run: python/run_mt5_job.py Reports/mes_weekly_flatten_20261027 RTL_weekly_hold_mes
"""
import hashlib
import json
import shutil

from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / 'Reports' / 'mes_weekly_flatten_20261027'
FROZEN = ROOT / 'Reports' / 'ym_baselines_20261023'
SOURCE_SHA256 = 'c13805f14d632049e1467f5cd018fa2e9f88a802c59d67a13849a62bcebe4851'
EXPERT = 'RTL_weekly_hold_mes'
TAG = 'meswk_20261027_w1_hold'


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    if (STUDY / 'manifest.json').exists():
        raise RuntimeError('Prepared study already exists; preserve it')
    source = FROZEN / 'RTL_runband.mq5'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256
    shutil.copyfile(source, STUDY / f'{EXPERT}.mq5')
    shutil.copyfile(FROZEN / 'early_closes.mqh', STUDY / 'early_closes.mqh')
    ini = (FROZEN / 'ymbase_20261023_rtl_es.ini').read_text(encoding='utf-16')
    changes = {'Expert': f'CodexResearch\\{EXPERT}.ex5', 'Period': 'W1', 'Report': f'{TAG}.htm',
               'RunTag': TAG, 'UseFlattenEnd': 'false||false||0||true||N',
               'UseTradeWindow': 'false||false||0||true||N', 'ServerClock': '0'}
    lines = ini.splitlines()
    for key, value in changes.items():
        assert sum(x.startswith(key + '=') for x in lines) == 1, key
        lines = [f'{key}={value}' if x.startswith(key + '=') else x for x in lines]
    assert 'Symbol=MEScontDTBNT20102026_2' in lines
    (STUDY / f'{TAG}.ini').write_text('\n'.join(lines) + '\n', encoding='utf-16')
    job = {'tag': TAG, 'expert': EXPERT, 'period': 'W1', 'rr': 1.0,
           'outputs': [f'runband_{TAG}_1.00.csv', f'runband_{TAG}_1.00_stats.csv']}
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in STUDY.iterdir()
              if p.is_file() and p.suffix in ('.mq5', '.mqh', '.ini')}
    manifest = {'symbol': 'MEScontDTBNT20102026_2', 'model': '1-minute OHLC', 'source_sha256': SOURCE_SHA256,
                'purpose': 'MES W1 hold check for the simulator', 'prepared_sha256': hashes, 'jobs': [job]}
    (STUDY / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Prepared {TAG} in {STUDY}')


if __name__ == '__main__':
    main()
