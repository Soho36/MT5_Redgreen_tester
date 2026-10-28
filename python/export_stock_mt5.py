"""Export the ten stock minute series of the VWAP stock test as MT5 custom-symbol CSVs.

Same data as docs/baseline/rtl-vwap/STOCK_RESULTS.md: Databento XNAS.ITCH 1-minute bars in
New York time, session 04:00-15:59 (pre-market plus regular hours; 04:00-12:59 on early-close
days), split-adjusted to today's share basis, price-less bars dropped, Meta from 2022-06-09.
Writes F:\\DATABENTO\\STOCKS\\MT5\\MT5_<SYMBOL>_2018-2026_ohlcv-1m.csv in the layout of the futures
files (tab-separated <DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>), plus
manifest.json. The M30 VWAP features rebuilt from each file must match the study's features.
They are also written as the VWAP EA's label file rtl_vwap_features_<SYMBOL>.csv (the replay's
format, epochs in the files' New York time), here and in MT5's Common\\Files, for tester runs:
MT5's tester rebuilds 1-minute bars with synthetic volume, so it cannot compute the real VWAP.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_rtl_vwap as av
import analyze_rtl_vwap_stocks as st
from run_mt5_job import COMMON

TARGET = st.DATA / 'MT5'
DIGITS = 6


def export(stock, g):
    path = TARGET / f'MT5_{stock}_2018-2026_ohlcv-1m.csv'
    volume = np.rint(g.volume.to_numpy()).astype(np.int64)
    assert np.allclose(volume, g.volume.to_numpy(), rtol=0, atol=1e-6) and (volume > 0).all()
    frame = pd.DataFrame({'<DATE>': g.t.dt.strftime('%Y.%m.%d'), '<TIME>': g.t.dt.strftime('%H:%M:%S'),
                          **{f'<{k.upper()}>': np.round(g[k].to_numpy(), DIGITS) for k in ('open', 'high', 'low', 'close')},
                          '<TICKVOL>': volume, '<VOL>': volume, '<SPREAD>': 1})
    frame.to_csv(path, sep='\t', index=False, float_format=f'%.{DIGITS}f', lineterminator='\n')
    return path, frame


def check(stock):
    """Rebuild M30 features from the exported file and compare with the study's (which end 2026-09-30).

    Returns the summary and all rebuilt bars: the labels use past bars only, so the label file runs
    on to the end of the exported minutes."""
    raw = pd.read_csv(TARGET/f'MT5_{stock}_2018-2026_ohlcv-1m.csv', sep='\t', dtype={'<DATE>': str, '<TIME>': str})
    bars, _, _ = st.vw.aggregate_chunk(raw)
    bars = st.vw.combine_bars(bars)
    bars['switch_bar'] = False
    full = st.vw.build_features(bars, 'full_hlc3')
    rebuilt = full.loc[lambda x: x.available_at < st.END].reset_index(drop=True)
    study = av.dates(pd.read_csv(st.OUT/f'features_{stock}.csv', float_precision='round_trip'), ['bar_time'])
    assert len(rebuilt) == len(study) and (rebuilt.bar_time.to_numpy() == study.bar_time.to_numpy().astype(rebuilt.bar_time.dtype)).all()
    gaps = {c: float(np.nanmax(np.abs(rebuilt[c].to_numpy(float)-study[c].to_numpy(float)))) for c in ('close', 'vwap', 'a20', 'z')}
    flips = int((rebuilt.distance.eq('far_below') != study.distance.eq('far_below')).sum())
    return dict(m30_bars=len(rebuilt), max_abs_difference=gaps, far_below_label_changes=flips), full.reset_index(drop=True)


def label_frame(f):
    """The EA's label rows (rtl_session_vwap.mqh): one per M30 bar; the gate's close < VWAP - A20 equals z < -1."""
    known = f.vwap_available & f.vwap.notna() & f.a20.gt(0)
    far = (f.close < f.vwap - f.a20) & known
    assert far.equals(f.distance.eq('far_below') & known), 'gate form differs from z < -1'
    out = pd.DataFrame({name: f[source].to_numpy(dtype='datetime64[s]').astype('int64') for name, source in
                        (('available_epoch', 'available_at'), ('session_epoch', 'feature_session'), ('bar_epoch', 'bar_time'))})
    out['close'] = f.close.to_numpy()
    out['vwap'] = f.vwap.where(known, 0).to_numpy()
    out['a20'] = f.a20.where(known, 0).to_numpy()
    out['known'] = known.astype(int).to_numpy()
    assert (out.available_epoch == out.bar_epoch + 1800).all() and (out.session_epoch == out.bar_epoch - out.bar_epoch % 86400).all()
    return out, int(far.sum())


def labels(stock, f):
    out, far = label_frame(f)
    path = TARGET / f'rtl_vwap_features_{stock}.csv'
    out.to_csv(path, sep='\t', index=False, float_format='%.17g', lineterminator='\n')
    shutil.copyfile(path, COMMON / path.name)
    return dict(file=path.name, sha256=av.digest(path), rows=len(out), known=int(out.known.sum()), far_below=far)


def main():
    TARGET.mkdir(exist_ok=True)
    minutes, files, dropped, priceless = st.read_sources()
    manifest = dict(source='Databento XNAS.ITCH ohlcv-1m', files=files, clock='America/New_York',
                    session='04:00-15:59 (04:00-12:59 on early-close days), after-hours dropped',
                    price_basis='split-adjusted to the latest share basis (prices / ratio, volume x ratio)',
                    meta=f'from {META_FROM:%Y-%m-%d} only (no FB history); {dropped} earlier META bars were an ETF',
                    priceless_bars_dropped=len(priceless), digits=DIGITS,
                    symbol_settings=dict(digits=DIGITS, tick_size=10**-DIGITS, contract_size=1, currency='USD',
                                         note='tick value = tick size x contract size; volume = shares'),
                    splits=[dict(stock=s, date=d, ratio=n) for (s, d), n in st.SPLITS.items()],
                    early_closes=list(st.EARLY_CLOSES), stocks={})
    for stock in st.STOCKS:
        g = st.adjust_splits(stock, st.session_minutes(minutes.loc[minutes.symbol.eq(stock)], st.SESSION_START))
        st.validate_minutes(g)
        path, frame = export(stock, g)
        summary, rebuilt = check(stock)
        manifest['stocks'][stock] = dict(file=path.name, sha256=av.digest(path), rows=len(frame),
                                         first=f'{g.t.iloc[0]}', last=f'{g.t.iloc[-1]}', sessions=int(g.t.dt.normalize().nunique()),
                                         check=summary, vwap_labels=labels(stock, rebuilt))
        c = manifest['stocks'][stock]['check']
        print(f"{stock}: {len(frame):,} minutes, {c['m30_bars']:,} M30 bars; max |vwap diff| "
              f"{c['max_abs_difference']['vwap']:.2e}, far-below label changes {c['far_below_label_changes']}", flush=True)
    (TARGET/'manifest.json').write_text(json.dumps(st.cx.plain(manifest), indent=2)+'\n', encoding='utf-8')
    print(f'Wrote {len(st.STOCKS)} files and manifest.json to {TARGET}')


META_FROM = st.META_FROM

if __name__ == '__main__':
    main()
