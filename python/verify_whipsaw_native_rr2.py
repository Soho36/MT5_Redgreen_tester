"""Independently replay both native 2R arms using the audited minute engine."""
import json
import numpy as np
import pandas as pd
import rtl_weekly_engine as engine
import whipsaw_days as wd
import analyze_rtl_vwap_cross as cx
from prepare_whipsaw_native import RUN, DOC
from verify_rtl_failed_breakout_short import CACHE


def main():
    minutes = engine.load_minutes(cache=CACHE)
    bars = wd.read_m30()
    pairs = pd.read_csv(RUN / 'event_sessions.csv', parse_dates=['session'])
    allowed = pairs.loc[pairs.horizon.eq(1), 'session'].unique()
    slots = bars.bar_time.to_numpy('datetime64[s]').astype(np.int64) // 1800
    forbidden = ~bars.bar_time.dt.normalize().shift(-1).isin(allowed).to_numpy()
    skips = set(slots[forbidden].tolist())
    results = []
    for strategy, signal in [('rtl', 'red'), ('gg', 'green')]:
        tag = f'whipnative_20261112_{strategy}_day1_rr2'
        native = cx.economics(cx.parse_report(RUN / (tag + '.htm'), cx.INSTRUMENTS['NQ']['symbol']), cx.INSTRUMENTS['NQ'])
        native = native.loc[native['sample'].eq('primary')].reset_index(drop=True)
        sim, rejected = engine.simulate_m30_ea(minutes, rr=2., signal=signal,
                                              cutoffs=engine.load_cutoffs(), signal_skips=skips)
        submitted = pd.to_datetime(sim.submitted)
        sim = sim.loc[submitted.ge('2016-01-01') & submitted.lt('2026-10-01')].reset_index(drop=True)
        assert len(sim) == len(native), (strategy, len(sim), len(native))
        for col in ('entry_time', 'exit_time'):
            assert np.array_equal(pd.to_datetime(sim[col]).dt.floor('min'), native[col].dt.floor('min')), (strategy, col)
        assert np.array_equal(pd.to_datetime(sim.submitted).dt.floor('30min'), native.submitted.dt.floor('30min'))
        for a, b in [('requested', 'requested_price'), ('sl', 'original_sl'), ('fill', 'fill_price'), ('exit_price', 'exit_price')]:
            np.testing.assert_allclose(sim[a], native[b], rtol=0, atol=1e-7)
        results.append(dict(strategy=strategy, primary_trades=len(native), all_matched=True))
        print(results[-1], flush=True)
    (DOC / 'rr2_verification.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
