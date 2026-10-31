"""Export causal M30 VWAP/A20 labels for the MT5 research EAs.

A label contains raw VWAP and A20, so the same file serves upper/lower bands.
Use --features for an existing full-session feature panel or --minutes for a
sorted tab-separated MT5 M1 export in the symbol's session/server clock.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from build_rtl_vwap_features import build_features,combine_bars
from run_rtl_vwap_replay import digest

COLUMNS=['available_epoch','session_epoch','bar_epoch','close','vwap','a20','known']


def minute_features(path,volume_column='<VOL>',chunksize=400000):
    pieces=[]
    last=None
    count=0
    with pd.read_csv(path,sep='\t',chunksize=chunksize) as reader:
        for raw in reader:
            needed=['<DATE>','<TIME>','<OPEN>','<HIGH>','<LOW>','<CLOSE>',volume_column]
            missing=set(needed)-set(raw.columns)
            if missing:raise ValueError('Missing M1 columns: '+', '.join(sorted(missing)))
            t=pd.to_datetime(raw['<DATE>'].astype(str)+' '+raw['<TIME>'].astype(str),format='%Y.%m.%d %H:%M:%S')
            if not t.is_monotonic_increasing or not t.is_unique or (last is not None and t.iloc[0]<=last):
                raise ValueError('M1 timestamps must be sorted, unique and increasing across chunks')
            if not t.dt.second.eq(0).all():raise ValueError('Expected M1 opening timestamps at second zero')
            prices=raw[['<OPEN>','<HIGH>','<LOW>','<CLOSE>']].to_numpy(float)
            volume=raw[volume_column].to_numpy(float)
            if not np.isfinite(prices).all() or (prices<=0).any():raise ValueError('Prices must be finite and positive')
            if not np.isfinite(volume).all() or (volume<=0).any():raise ValueError('Volume must be finite and positive; select the correct volume column')
            if (prices[:,1]<prices.max(axis=1)).any() or (prices[:,2]>prices.min(axis=1)).any():raise ValueError('Invalid M1 OHLC bounds')
            f=pd.DataFrame(dict(bar_time=t.dt.floor('30min'),open=prices[:,0],high=prices[:,1],low=prices[:,2],close=prices[:,3],
                volume=volume,pv_hlc3=prices[:,1:].mean(axis=1)*volume,pv_close=prices[:,3]*volume,
                minute_count=1,first_minute=t,last_minute=t))
            pieces.append(combine_bars(f))
            count+=len(raw)
            last=t.iloc[-1]
    if not pieces:raise ValueError('Empty M1 input')
    bars=combine_bars(pd.concat(pieces,ignore_index=True))
    bars['switch_bar']=False # Only roll_clean uses this; known/export never depends on it.
    features=build_features(bars,'full_hlc3')
    # An unfinished final slot must not become a tradable historical label.
    if bars.last_minute.iloc[-1] < bars.bar_time.iloc[-1]+pd.Timedelta(minutes=29):
        features.loc[features.index[-1],'vwap_available']=False
    return features,count


def feature_labels(frame):
    f=frame.copy()
    required={'available_at','feature_session','bar_time','close','vwap','a20','vwap_available'}
    if not required.issubset(f):raise ValueError('Missing feature columns: '+str(sorted(required-set(f))))
    for col in ('available_at','feature_session','bar_time'):
        f[col]=pd.to_datetime(f[col],format='ISO8601')
    if f.empty or not f.available_at.is_monotonic_increasing or not f.available_at.is_unique:
        raise ValueError('Feature rows must be nonempty and strictly increasing')
    if not f.available_at.eq(f.bar_time+pd.Timedelta(minutes=30)).all():raise ValueError('Feature availability must equal bar opening + 30 minutes')
    if not f.feature_session.eq(f.bar_time.dt.normalize()).all():raise ValueError('Expected one session per date in the provided clock')
    if f.bar_time.dt.second.ne(0).any() or (f.bar_time.dt.minute%30).ne(0).any():raise ValueError('Bar openings must align to M30')
    if not np.isfinite(f.close).all() or f.close.le(0).any():raise ValueError('Close must be finite and positive')
    available=f.vwap_available.map({True:True,False:False,'true':True,'false':False,'True':True,'False':False})
    if available.isna().any():raise ValueError('vwap_available must be true or false')
    known=available.astype(bool)&f.vwap.notna()&np.isfinite(f.vwap)&f.vwap.gt(0)&np.isfinite(f.a20)&f.a20.gt(0)
    labels=pd.DataFrame({name:f[col].to_numpy(dtype='datetime64[s]').astype('int64') for name,col in
        [('available_epoch','available_at'),('session_epoch','feature_session'),('bar_epoch','bar_time')]})
    labels['close']=f.close.to_numpy()
    labels['vwap']=f.vwap.where(known,0).to_numpy()
    labels['a20']=f.a20.where(known,0).to_numpy()
    labels['known']=known.astype(int).to_numpy()
    return labels[COLUMNS]


def export(source,output,mode='features',volume_column='<VOL>',end_before=None):
    source,output=Path(source),Path(output)
    metadata=output.with_suffix('.metadata.json')
    if output.exists() or metadata.exists():raise FileExistsError('Preserve existing output; choose a new filename: '+str(output))
    before=digest(source)
    if mode=='minutes':features,source_rows=minute_features(source,volume_column)
    elif mode=='features':
        features=pd.read_csv(source,float_precision='round_trip')
        source_rows=len(features)
    else:raise ValueError(mode)
    if end_before is not None:
        end=pd.Timestamp(end_before)
        if end.tzinfo is not None or end!=end.normalize():raise ValueError('--end-before must be a date in the input clock')
        features=features.loc[pd.to_datetime(features.available_at,format='ISO8601').lt(end)]
    labels=feature_labels(features)
    if digest(source)!=before:raise RuntimeError('Input changed during export')
    output.parent.mkdir(parents=True,exist_ok=True)
    labels.to_csv(output,sep='\t',index=False,float_format='%.17g',lineterminator='\n',mode='x')
    record=dict(source=str(source.resolve()),source_sha256=before,source_mode=mode,source_rows=source_rows,
        output=str(output.resolve()),output_sha256=digest(output),rows=len(labels),known=int(labels.known.sum()),
        first_available=str(pd.to_datetime(labels.available_epoch.iloc[0],unit='s')),
        last_available=str(pd.to_datetime(labels.available_epoch.iloc[-1],unit='s')),
        clock='Naive input session/server clock; no timezone conversion',
        definition='M1 HLC3 weighted by selected volume; cumulative per date; arithmetic 20 completed M30 true ranges',
        volume_column=volume_column if mode=='minutes' else 'As supplied by feature panel',
        threshold_embedded=False,end_before=str(end_before) if end_before is not None else None,program_sha256=digest(Path(__file__)))
    with metadata.open('x',encoding='utf-8') as stream:json.dump(record,stream,indent=2);stream.write('\n')
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--features',type=Path)
    group.add_argument('--minutes',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--volume-column',default='<VOL>',help='M1 real volume by default; use <TICKVOL> explicitly for a tick-volume study')
    p.add_argument('--end-before',help='Keep labels available strictly before this date, e.g. 2026-10-01; excludes an incomplete final session')
    args=p.parse_args()
    record=export(args.minutes or args.features,args.output,'minutes' if args.minutes else 'features',args.volume_column,args.end_before)
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
