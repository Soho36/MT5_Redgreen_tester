"""Causal, frozen session-VWAP features for existing RTL submissions."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_rtl_market_regimes as base
import analyze_rtl_price_structure as structure

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Reports/rtl_vwap_20261025'
PROTOCOL = ROOT / 'docs/baseline/rtl-vwap/PROTOCOL.md'
PROTOCOL_SHA256 = 'a75e57ab36fe49fb63f3664f847cb8ba52ac651a109a76c3cc220c0344eb0314'
VARIANTS = ('full_hlc3', 'full_close', 'cash_hlc3')
END = pd.Timestamp('2026-10-01')


def aggregate_chunk(raw):
    """Minute starts and volume-weighted price products, never M30 typical price."""
    t = pd.to_datetime(raw['<DATE>']+' '+raw['<TIME>'], format='%Y.%m.%d %H:%M:%S')
    assert t.is_unique and t.is_monotonic_increasing
    ohlc = raw[['<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>']].to_numpy(float)
    volume = raw['<VOL>'].to_numpy(float)
    if not np.isfinite(ohlc).all() or not np.isfinite(volume).all() or (volume <= 0).any():
        raise ValueError('Nonfinite prices or nonpositive/nonfinite volume')
    assert np.array_equal(volume, raw['<TICKVOL>'].to_numpy(float))
    assert (ohlc[:, 1] >= ohlc.max(axis=1)).all()
    assert (ohlc[:, 2] <= ohlc.min(axis=1)).all()
    assert t.dt.hour.ge(1).all()
    f = pd.DataFrame(dict(bar_time=t.dt.floor('30min'), open=ohlc[:, 0],
                         high=ohlc[:, 1], low=ohlc[:, 2], close=ohlc[:, 3],
                         volume=volume, pv_hlc3=ohlc[:, 1:].mean(axis=1)*volume,
                         pv_close=ohlc[:, 3]*volume, minute_count=1,
                         first_minute=t, last_minute=t))
    return combine_bars(f), t.iloc[0], t.iloc[-1]


def combine_bars(frame):
    return frame.groupby('bar_time', sort=True).agg(
        open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
        close=('close', 'last'), volume=('volume', 'sum'),
        pv_hlc3=('pv_hlc3', 'sum'), pv_close=('pv_close', 'sum'),
        minute_count=('minute_count', 'sum'), first_minute=('first_minute', 'first'),
        last_minute=('last_minute', 'last')).reset_index()


def build_features(bars, variant):
    assert variant in VARIANTS
    f = bars.copy().sort_values('bar_time').reset_index(drop=True)
    f['variant'] = variant
    f['available_at'] = f.bar_time + pd.Timedelta(minutes=30)
    f['feature_session'] = f.bar_time.dt.normalize()
    prev = f.close.shift()
    tr = pd.concat([f.high-f.low, (f.high-prev).abs(), (f.low-prev).abs()], axis=1).max(axis=1)
    tr.iloc[0] = np.nan
    f['a20'] = tr.rolling(20, min_periods=20).mean()
    f['roll_clean'] = f.a20.gt(0) & f.switch_bar.astype(int).rolling(21, min_periods=21).sum().eq(0)
    eligible = pd.Series(True, index=f.index)
    if variant == 'cash_hlc3':
        eligible = (f.bar_time.dt.hour*60+f.bar_time.dt.minute).ge(16*60+30)
    pv = 'pv_close' if variant == 'full_close' else 'pv_hlc3'
    f['cum_volume'] = f.volume.where(eligible, 0).groupby(f.feature_session).cumsum().where(eligible)
    cum_pv = f[pv].where(eligible, 0).groupby(f.feature_session).cumsum().where(eligible)
    f['vwap'] = cum_pv/f.cum_volume
    f['anchor_age'] = eligible.astype(int).groupby(f.feature_session).cumsum().where(eligible, 0)
    f['vwap_available'] = eligible & f.cum_volume.gt(0)
    diff = (f.close-f.vwap).where(f.vwap_available)
    sign = np.sign(diff)
    f['side'] = np.select([diff.gt(0), diff.lt(0), diff.eq(0)], ['above', 'below', 'at'], default='unknown')
    f['z'] = (diff/f.a20).where(f.a20.gt(0))
    f['distance'] = np.select([f.z.lt(-1), f.z.ge(-1)&f.z.lt(0), f.z.eq(0),
                               f.z.gt(0)&f.z.le(1), f.z.gt(1)],
                              ['far_below', 'below', 'at', 'above', 'far_above'], default='unknown')
    previous_sign = sign.groupby(f.feature_session).shift()
    event_valid = sign.notna() & previous_sign.notna()
    f['event'] = np.select([~event_valid, previous_sign.le(0)&sign.gt(0),
                            previous_sign.ge(0)&sign.lt(0)],
                           ['unknown', 'reclaim', 'loss'], default='same_side')
    crossing = (sign*previous_sign).lt(0).astype(float).where(event_valid)
    for n, cutoff in ((6, 3), (4, 2)):
        counts = crossing.groupby(f.feature_session).transform(lambda x: x.rolling(n, min_periods=n).sum())
        f[f'crossings{n}'] = counts
        name = 'churn' if n == 6 else 'churn4'
        f[name] = np.select([counts.isna(), counts.ge(cutoff)], ['unknown', 'churn'], default='orderly')
    return f


def label_trades(trades, features):
    out = pd.merge_asof(trades.sort_values(['submitted', 'ticket']),
                        features.sort_values('available_at'), left_on='submitted',
                        right_on='available_at', direction='backward', allow_exact_matches=True)
    assert out.available_at.notna().all()
    assert (out.available_at <= out.submitted).all()
    # Orders submitted at the session open can reference yesterday's signal bar.
    # Today's VWAP does not yet exist; never turn that into yesterday's VWAP.
    stale = out.feature_session.ne(out.submitted.dt.normalize())
    out['unknown_reason'] = np.where(stale, 'session_reset',
        np.where(~out.vwap_available, 'before_anchor', ''))
    out.loc[stale, ['vwap', 'cum_volume', 'z', 'crossings6', 'crossings4']] = np.nan
    out.loc[stale, 'anchor_age'] = 0
    out.loc[stale, ['vwap_available', 'roll_clean']] = False
    out.loc[stale, ['side', 'distance', 'event', 'churn', 'churn4']] = 'unknown'
    return out


def main():
    assert base.digest(PROTOCOL) == PROTOCOL_SHA256
    source_provenance = ROOT / 'Reports/rtl_price_structure_20261024/provenance.json'
    provenance = json.loads(source_provenance.read_text())
    sources = [base.MINUTES, base.M30, base.ROLLS, structure.SOURCE]
    hashes = {str(p): base.digest(p) for p in sources}
    for p in sources:
        assert hashes[str(p)] == provenance['inputs_sha256'][str(p)], f'Changed source {p}'
    feature_source = ROOT / 'Reports/rtl_price_structure_20261024/features_m30_20.csv'
    assert base.digest(feature_source) == provenance['outputs_sha256'][feature_source.name]
    hashes[str(feature_source)] = base.digest(feature_source)
    hashes[str(source_provenance)] = base.digest(source_provenance)
    chunks, rows, last = [], 0, None
    for raw in pd.read_csv(base.MINUTES, sep='\t', chunksize=400000):
        bars, first, final = aggregate_chunk(raw)
        assert last is None or first > last
        last = final
        rows += len(raw)
        chunks.append(bars)
    bars = combine_bars(pd.concat(chunks, ignore_index=True))
    reference = pd.read_csv(base.M30, parse_dates=['bar_time'])
    assert np.array_equal(bars.bar_time, reference.bar_time)
    assert np.array_equal(bars[['open', 'high', 'low', 'close']], reference[['open', 'high', 'low', 'close']])
    switches = pd.read_csv(feature_source, usecols=['bar_time', 'switch_bar'], parse_dates=['bar_time'])
    bars = bars.merge(switches, on='bar_time', validate='one_to_one')
    assert bars.switch_bar.notna().all()
    trades = structure.load_trades().query('primary').copy()
    assert len(trades) == 16668
    assert np.allclose(trades.groupby('era').net_dollars.sum(), [4416.65, 38399.95], atol=1e-7)
    OUT.mkdir(parents=True, exist_ok=True)
    panels = []
    for variant in VARIANTS:
        features = build_features(bars, variant).loc[lambda x: x.available_at < END]
        features.to_csv(OUT/f'features_{variant}.csv', index=False, float_format='%.17g')
        labelled = label_trades(trades, features)
        assert len(labelled) == len(trades)
        panels.append(labelled)
    pd.concat(panels, ignore_index=True).to_csv(OUT/'trades.csv', index=False, float_format='%.17g')
    audit = dict(all_passed=True, minute_rows=rows, m30_rows=len(bars),
                 eligible_trades=len(trades), variants=list(VARIANTS),
                 m30_ohlc_exact=True, positive_volume=True, tickvol_equals_volume=True,
                 session_first_minutes=bars.groupby(bars.bar_time.dt.normalize()).first_minute.first().dt.strftime('%H:%M').value_counts().to_dict(),
                 session_reset_unknown_trades=int(panels[0].unknown_reason.eq('session_reset').sum()),
                 no_future_information=True, partial_endpoint_excluded=True)
    base.save_json(OUT/'feature_audit.json', audit)
    base.save_json(OUT/'feature_provenance.json', dict(protocol_sha256=PROTOCOL_SHA256,
        inputs_sha256=hashes, program_sha256=base.digest(Path(__file__)),
        outputs_sha256={p.name: base.digest(p) for p in OUT.glob('*.csv')},
        numpy=np.__version__, pandas=pd.__version__))
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
