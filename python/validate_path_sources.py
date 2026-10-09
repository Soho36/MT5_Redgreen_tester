"""Validate path-study signal/close observations against the frozen source M1 OHLC."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_granularity_candles import _source_m30
from build_coarse_nq import K
from project_paths import PROJECT_ROOT as ROOT
from run_path_experiment import digest

RUN=ROOT/'Reports/path_experiment_20261009'


def source_cache(manifest):
    metadata={}
    frames={}
    for instrument,filename in manifest['source_files'].items():
        path=Path(filename)
        cache=RUN/f'source_{instrument}_m30.csv'
        info_path=RUN/f'source_{instrument}_metadata.json'
        expected=manifest['input_hashes'][str(path)]
        if digest(path)!=expected:
            raise RuntimeError(f'Frozen source changed: {path}')
        if cache.exists() and info_path.exists():
            info=json.loads(info_path.read_text())
            if info['source_sha256']!=expected or info['m30_sha256']!=digest(cache):
                raise RuntimeError('Source cache binding differs')
            frame=pd.read_csv(cache,index_col=0,parse_dates=True)
        else:
            print(f'Validating source M1 OHLC and aggregating {instrument}',flush=True)
            frame,info=_source_m30(path,manifest['start'],manifest['end_exclusive'])
            frame.to_csv(cache,index_label='bar_open')
            info.update(source_sha256=expected,m30_sha256=digest(cache),m30_bars=len(frame))
            info_path.write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
        metadata[instrument]=info
        frames[instrument]=frame
        print(f"PASS source {instrument}: {info['source_rows']:,} M1 rows / {len(frame):,} M30 bars",flush=True)
    nq,coarse=frames['NQ'],frames['NQcoarse']
    if not nq.index.equals(coarse.index):
        raise RuntimeError('Coarse NQ timestamps differ from native NQ')
    grids=np.array([K[int(y)] for y in nq.index.year],dtype=float)[:,None]
    expected=np.rint(nq.to_numpy(dtype=float)/grids)*grids
    if not np.array_equal(expected,coarse.to_numpy(dtype=float)):
        raise RuntimeError('Existing coarse M30 prices do not equal frozen yearly ties-even quantization')
    days=sorted(set().union(*(set(info['trading_days']) for info in metadata.values())))
    calendar=dict(trading_days=days,source_metadata=metadata,all_source_checks_passed=True,
                  coarse_m30_quantization_exact=True)
    (RUN/'source_calendar.json').write_text(json.dumps(calendar,indent=2)+'\n',encoding='utf-8')
    return frames,calendar


def main():
    manifest=json.loads((RUN/'manifest.json').read_text(encoding='utf-8'))
    frames,calendar=source_cache(manifest)
    checks=[]
    for job in manifest['jobs']:
        tag=job['tag']
        if not (RUN/f'{tag}.completed.json').exists():
            continue
        frame=frames[job['instrument']]
        orders=pd.read_csv(RUN/f'path_{tag}_orders.csv',sep='\t',encoding='utf-16')
        times=pd.to_datetime(orders.signal_bar_open,format='%Y.%m.%d %H:%M:%S')
        indexer=frame.index.get_indexer(times)
        if (indexer<0).any():
            raise RuntimeError(f'{tag}: signal bars absent from source')
        expected=frame.iloc[indexer].to_numpy(dtype=float)/4
        got=orders[['signal_open','signal_high','signal_low','signal_close']].to_numpy(dtype=float)
        if not np.array_equal(got,expected):
            raise RuntimeError(f'{tag}: signal OHLC differs from source')
        bars=pd.read_csv(RUN/f'path_{tag}_bars.csv',sep='\t',encoding='utf-16')
        times=pd.to_datetime(bars.closed_bar_open,format='%Y.%m.%d %H:%M:%S')
        indexer=frame.index.get_indexer(times)
        if (indexer<0).any():
            raise RuntimeError(f'{tag}: observed closed bars absent from source')
        if not np.array_equal(bars.closed_close.to_numpy(dtype=float),frame.iloc[indexer].close.to_numpy(dtype=float)/4):
            raise RuntimeError(f'{tag}: observed M30 closes differ from source')
        checks.append(dict(tag=tag,signal_orders=len(orders),observed_closed_bars=len(bars),signal_ohlc_exact=True,closed_bar_closes_exact=True))
        print(f'PASS source binding {tag}: {len(orders):,} order signal candles / {len(bars):,} observed M30 closes',flush=True)
    (RUN/'source_checks.json').write_text(json.dumps(dict(all_passed=True,jobs=checks,common_calendar_days=len(calendar['trading_days'])),indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
