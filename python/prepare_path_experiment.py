"""Freeze and prepare the six-arm NQ/coarse-NQ/ES path experiment."""
import hashlib
import json
import shutil
from pathlib import Path

from path_collector_source import build_source
from prepare_signal_colour import build_source as original_source
from project_paths import PROJECT_ROOT as ROOT

RUN = ROOT / 'Reports' / 'path_experiment_20261009'
EXPERT = 'RTL_path'
SOURCES = {
    'NQ': Path(r'F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_continuous_2010-2026_ohlcv-1m.csv'),
    'NQcoarse': Path(r'F:\DATABENTO\MNQ_16_YEARS\MT5_NQ_coarse_2010-2026_ohlcv-1m.csv'),
    'ES': Path(r'F:\DATABENTO\ES_16_YEARS\MT5_ES_continuous_2010-2026_ohlcv-1m.csv'),
}
REFERENCE = {
    'NQ': ('signal_colour_20261008', 'MNQcontDTBNT20102026_2', 2.0),
    'NQcoarse': ('signal_colour_20261008_nqcoarse', 'MNQcoarseDTBNT20102026', 2.0),
    'ES': ('signal_colour_20261008_mes', 'MEScontDTBNT20102026', 5.0),
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    if (RUN / 'manifest.json').exists():
        raise RuntimeError('Frozen study manifest exists; resume rather than reprepare')
    source = build_source()
    (RUN / f'{EXPERT}.mq5').write_text(source, encoding='utf-8')
    frozen = [ROOT / 'docs/baseline/path-interaction/PROTOCOL.md',
              ROOT / 'mt5/experts/RR_r_MFE_buy-stop-entry_runband.cs',
              ROOT / 'python/prepare_signal_colour.py', ROOT / 'python/build_coarse_nq.py',
              ROOT / 'python/path_collector_source.py', Path(__file__).resolve(),
              ROOT / 'python/run_path_experiment.py', ROOT / 'python/validate_path_sources.py',
              RUN / f'{EXPERT}.mq5']
    for name in ('early_closes.mqh', 'path_research.mqh'):
        src = ROOT / 'mt5/experts' / name
        dst = RUN / name
        shutil.copyfile(src, dst)
        frozen.extend((src, dst))
    jobs = []
    original = original_source().replace('\r\n', '\n')
    for instrument, (folder, symbol, pv) in REFERENCE.items():
        old_run = ROOT / 'Reports' / folder
        ref_manifest = json.loads((old_run / 'manifest.json').read_text(encoding='utf-8'))
        old_ea = (old_run / 'RTL_signal.mq5').read_text(encoding='utf-8').replace('\r\n', '\n')
        if original != old_ea:
            raise RuntimeError(f'Current uninstrumented EA differs from original source: {instrument}')
        for mode, name in (('rtl', 'red_cap3'), ('control', 'market_control')):
            ref = next(j for j in ref_manifest['jobs'] if name in j['tag'])
            tag = f'path_20261009_{instrument.lower()}_{mode}'
            ini = old_run / f"{ref['tag']}.ini"
            lines = ini.read_text(encoding='utf-16').splitlines()
            replacements = {'Expert=': f'Expert=CodexTrendlineResearch\\{EXPERT}.ex5',
                            'Report=': f'Report={tag}.htm', 'RunTag=': f'RunTag={tag}'}
            for prefix, replacement in replacements.items():
                if sum(line.startswith(prefix) for line in lines) != 1:
                    raise RuntimeError(f'Missing or duplicate INI setting: {prefix}')
                lines = [replacement if line.startswith(prefix) else line for line in lines]
            for required in ('FromDate=2010.06.07', 'ToDate=2026.07.14', 'Model=1', 'Period=M30'):
                if required not in lines:
                    raise RuntimeError(f'Original tester setting differs: {required}')
            out_ini = RUN / f'{tag}.ini'
            out_ini.write_text('\n'.join(lines) + '\n', encoding='utf-16')
            raw = old_run / ref['outputs'][0]
            audited = raw.with_name(raw.stem + '_audited.csv')
            audit_path = old_run / f"{ref['tag']}.ledger_audit.json"
            audit = json.loads(audit_path.read_text(encoding='utf-8'))
            if not audit['all_passed'] or digest(audited) != audit['audited_sha256']:
                raise RuntimeError(f'Reference complete ledger audit invalid: {instrument} {mode}')
            frozen.extend((ini, out_ini, raw, old_run/ref['outputs'][1], audited,
                           audit_path, old_run/f"{ref['tag']}.htm", old_run/'RTL_signal.mq5'))
            outputs = [f'runband_{tag}_1.00.csv', f'runband_{tag}_1.00_stats.csv']
            outputs += [f'path_{tag}_{kind}.csv' for kind in ('trades','bars','checks','orders','summary')]
            jobs.append(dict(tag=tag, instrument=instrument, mode=mode, symbol=symbol, pv=pv,
                             point_value=pv, outputs=outputs, old_run=str(old_run),
                             old_tag=ref['tag'], reference_raw=str(raw), reference_audited=str(audited),
                             reference_stats=str(old_run/ref['outputs'][1]), reference_report=str(old_run/f"{ref['tag']}.htm")))
    frozen.extend(SOURCES.values())
    unique = list(dict.fromkeys(frozen))
    manifest = dict(expert=EXPERT, native_tick=.25, start='2010-06-07', end_exclusive='2026-07-14',
                    protocol='docs/baseline/path-interaction/PROTOCOL.md', jobs=jobs,
                    source_files={k:str(v) for k,v in SOURCES.items()},
                    periods=[['2010-15',2010,2015],['2016-19',2016,2019],['2020-26',2020,2026],['all',2010,2026]],
                    exclusion_dates=['2020-02-28','2020-06-30'],
                    matching=dict(min_trades=30,min_entry_days=10,
                                  size_edges=[0,8,16,24,32,48,64,128,None],
                                  sessions=[['pre_cash',60,990],['early_cash',990,1200],['late_cash',1200,1410]],
                                  six_arm_common=True,coarse_es_four_arm=True,native_tick_sensitivity=True,
                                  weights='minimum arm cell count, normalized, frozen'),
                    bootstrap=dict(draws=1000,seed=20261009,unit='common source entry day',fixed_support_weights=True),
                    input_hashes={str(p):digest(p) for p in unique})
    (RUN / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'Prepared six path jobs; {len(unique)} frozen input hashes; source EA matches all originals.')


if __name__ == '__main__':
    main()
