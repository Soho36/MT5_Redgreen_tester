"""Prepare the MT5 replay of the VWAP gate on GG, NQ (2026-10-30).

The VWAP gate EA (mt5/experts/RR_GG_r_MFE_buy-stop-entry_vwap.cs) with SignalCandle = green
trades GG. Two tester jobs with the GG baseline's settings and dates
(Reports/ym_baselines_20261023/ymbase_20261023_gg_nq.ini):
  off - gate off: must reproduce the GG baseline run trade for trade.
  on  - gate on, labels from the replay's NQ feature file (one row per M30 bar, so it serves
        green signals as well as red), decision log on: the full replay of the rule on GG.
Every EA input is written to the INIs: the tester reuses the last value of a missing input.
Run: python/run_mt5_job.py Reports/gg_vwap_ea_20261030 RR_r_MFE_buy-stop-entry_vwap
     then python/verify_gg_vwap_ea.py.
"""
import hashlib
import json
import re
import shutil

from project_paths import PROJECT_ROOT as ROOT

STUDY = ROOT / 'Reports' / 'gg_vwap_ea_20261030'
GG_RUN = ROOT / 'Reports' / 'ym_baselines_20261023'
EA_CHECK = ROOT / 'Reports' / 'rtl_vwap_ea_20261028'
EXPERTS = ROOT / 'mt5' / 'experts'
SOURCE = 'RR_GG_r_MFE_buy-stop-entry_vwap'  # the EA's source name since 2026-10-30
EXPERT = 'RR_r_MFE_buy-stop-entry_vwap'     # its name when these jobs ran (run folder, INIs)
FEATURES = 'rtl_vwap_replay_20261026_features.csv'
INCLUDES = ('early_closes.mqh', 'stock_early_closes.mqh', 'rtl_session_vwap.mqh')
JOBS = {'off': ('false', ''), 'on': ('true', FEATURES)}


def ini_lines(path):
    return path.read_text(encoding='utf-16').splitlines()


def tester_ini(tag, gate, label_file):
    """The checked RTL VWAP-EA INI with the GG baseline's dates and the green signal candle."""
    lines = ini_lines(EA_CHECK / 'vwapea_20261028_file.ini')
    gg = dict(x.split('=', 1) for x in ini_lines(GG_RUN / 'ymbase_20261023_gg_nq.ini') if '=' in x)
    changes = {'ToDate': gg['ToDate'], 'Report': f'{tag}.htm', 'RunTag': tag, 'UseVwapGate': gate,
               'VwapLabelFile': label_file, 'LogVwapDecisions': gate, 'MinRedRun': gg['MinGreenRun'],
               'MaxRedRun': gg['MaxGreenRun']}
    for key, value in changes.items():
        assert sum(x.startswith(key + '=') for x in lines) == 1, key
        lines = [f'{key}={value}' if x.startswith(key + '=') else x for x in lines]
    at = lines.index('[TesterInputs]') + 1
    lines[at:at] = ['SignalCandle=1']
    end = next(i for i in range(at, len(lines)) if lines[i].startswith('['))
    given = [x.split('=', 1)[0] for x in lines[at:end] if '=' in x]
    inputs = re.findall(r'^input\s+\w+\s+(\w+)\s*=', (EXPERTS / f'{SOURCE}.cs').read_text(encoding='utf-8'), re.MULTILINE)
    assert sorted(given) == sorted(inputs) and len(inputs) == 56, set(inputs) ^ set(given)
    # Everything but the EA, report, tag, run-band names and the new inputs equals the GG baseline run.
    mine = dict(x.split('=', 1) for x in lines if '=' in x)
    renamed = {'MinGreenRun': 'MinRedRun', 'MaxGreenRun': 'MaxRedRun'}
    for key, value in gg.items():
        if key not in ('Expert', 'Report', 'RunTag'):
            assert mine[renamed.get(key, key)].split('||')[0] == value.split('||')[0], key
    return '\n'.join(lines) + '\n'


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    if (STUDY / 'manifest.json').exists():
        raise RuntimeError('Prepared study already exists; preserve it')
    shutil.copyfile(EXPERTS / f'{SOURCE}.cs', STUDY / f'{EXPERT}.mq5')
    for name in INCLUDES:
        shutil.copyfile(EXPERTS / name, STUDY / name)
    assert (EXPERTS / 'early_closes.mqh').read_bytes() == (GG_RUN / 'early_closes.mqh').read_bytes()
    shutil.copyfile(EA_CHECK / FEATURES, STUDY / FEATURES)
    jobs = []
    for variant, (gate, label_file) in JOBS.items():
        tag = f'ggvwap_20261030_{variant}'
        (STUDY / f'{tag}.ini').write_text(tester_ini(tag, gate, label_file), encoding='utf-16')
        outputs = [f'rtlvwap_{tag}_1.00.csv', f'rtlvwap_{tag}_1.00_stats.csv']
        jobs.append({'tag': tag, 'expert': EXPERT, 'gate': gate == 'true', 'vwap_source': label_file or 'none',
                     'outputs': outputs + ([f'vwap_decisions_{tag}.csv'] if label_file else []),
                     'inputs_files': [FEATURES] if label_file else []})
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in STUDY.iterdir()
              if p.is_file() and p.suffix in ('.mq5', '.mqh', '.ini', '.csv')}
    manifest = {'symbol': 'MNQcontDTBNT20102026_2', 'model': '1-minute OHLC', 'reference': str(GG_RUN.relative_to(ROOT)),
                'purpose': 'VWAP gate EA on GG (green signal candle): gate off must reproduce the GG baseline run; '
                           'gate on is the full MT5 replay of the far-below rule on GG',
                'prepared_sha256': hashes, 'jobs': jobs}
    (STUDY / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Prepared {len(jobs)} jobs in {STUDY}')


if __name__ == '__main__':
    main()
