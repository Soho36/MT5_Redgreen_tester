"""Independent arithmetic and provenance checks of the RTL-short VWAP study."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_rtl_short_vwap import RUN,TAG,BASE
from run_rtl_vwap_replay import digest,save_json


def dd(values):
    peak=equity=worst=0.0
    for value in values:
        equity+=float(value)
        peak=max(peak,equity)
        worst=max(worst,peak-equity)
    return worst


def main():
    check=json.loads((RUN/'baseline_validation.json').read_text())
    assert check['all_passed'] and check['native_ledger_byte_identical']
    summaries=pd.read_csv(RUN/'summaries.csv')
    annual=pd.read_csv(RUN/'annual.csv')
    audits=[]
    for variant,curve in [('off','short baseline'),('on','short full replay')]:
        tag=TAG+'_'+variant
        record=json.loads((RUN/(tag+'.completed.json')).read_text())
        assert record['returncode']==0 and record['dedicated_tester_only_binary']
        for name,expected in record['outputs'].items(): assert digest(RUN/name)==expected,name
        assert digest(RUN/(tag+'.htm'))==record['report_sha256']
        trades=pd.read_csv(RUN/('trades_baseline.csv' if variant=='off' else 'trades_replay.csv'),parse_dates=['submitted','entry_time','exit_time','session'])
        raw=pd.read_csv(RUN/f'runband_{tag}_1.00.csv',sep='\t',encoding='utf-16').set_index('ticket')
        joined=trades.set_index('ticket').join(raw[['trade_profit','candle_range']],rsuffix='_raw')
        assert np.array_equal(joined.trade_profit,joined.trade_profit_raw)
        for row in summaries.loc[summaries.curve.eq(curve)].itertuples():
            start,stop={'2010-15':('2010-01-01','2016-01-01'),'2016-19':('2016-01-01','2020-01-01'),
                        '2020-26':('2020-01-01','2026-10-01'),'2016-26':('2016-01-01','2026-10-01')}[row.period]
            t=joined.loc[joined.submitted.ge(start)&joined.submitted.lt(stop)].copy()
            net=t.trade_profit_raw-1.05
            assert len(t)==row.trades
            expected={'net_dollars':net.sum(),'gross_mean_r':(t.trade_profit_raw/(t.candle_range*2)).mean(),
                      'net_mean_r':(net/(t.candle_range*2)).mean(),'profit_factor':net[net>0].sum()/-net[net<0].sum(),
                      'daily_close_dd':dd(net.groupby(t.exit_time.dt.normalize()).sum().sort_index()),
                      'closed_trade_dd':dd(t.assign(pnl=net).sort_values(['exit_time','entry_time']).pnl),
                      'stress1_net_dollars':net.sum()-len(t),'stress2_net_dollars':net.sum()-2*len(t)}
            for key,value in expected.items(): assert np.isclose(value,getattr(row,key),atol=1e-5,rtol=1e-8),(row.period,curve,key,value,getattr(row,key))
            audits.append(dict(curve=curve,period=row.period,trades=len(t),metrics_checked=list(expected)))
        for row in annual.loc[annual.curve.eq(curve)].itertuples():
            part=joined.loc[joined.submitted.dt.year.eq(row.year)&joined.submitted.lt('2026-10-01')]
            assert len(part)==row.trades and np.isclose((part.trade_profit_raw-1.05).sum(),row.net_dollars,atol=1e-6)
    for row in summaries.loc[summaries.curve.eq('gated RTL long + gated short')].itertuples():
        part=summaries.loc[summaries.period.eq(row.period)]
        long=part.loc[part.curve.eq('RTL long gated')].iloc[0]
        short=part.loc[part.curve.eq('short full replay')].iloc[0]
        assert row.trades==long.trades+short.trades
        assert np.isclose(row.net_dollars,long.net_dollars+short.net_dollars,atol=1e-6)
    assert (RUN/f'runband_{TAG}_off_1.00.csv').read_bytes()==(BASE/'runband_ymbase_20261023_rtl_short_nq_1.00.csv').read_bytes()
    save_json(RUN/'independent_verification.json',dict(all_passed=True,native_output_hashes_verified=True,
        summary_checks=audits,annual_rows_checked=len(annual.loc[annual.curve.isin(['short baseline','short full replay'])]),
        combined_net_and_trade_counts_add=True))
    print('Independent checks passed: native hashes, 8 period rows, 34 annual rows and combined arithmetic.')


if __name__=='__main__':main()
