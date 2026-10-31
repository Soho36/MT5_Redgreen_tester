"""Independent native-output arithmetic checks for the short cutoff comparison."""
import json
import numpy as np
import pandas as pd
from prepare_rtl_short_vwap_lines import RUN,PRIOR,TAG
from prepare_rtl_short_vwap import TAG as OLD_TAG
from verify_rtl_short_vwap import dd
from run_rtl_vwap_replay import digest,save_json


def main():
    verification=json.loads((RUN/'verification.json').read_text())
    assert verification['all_passed'] and verification['orange_identical_to_original']
    for name,expected in verification['output_hashes'].items():assert digest(RUN/name)==expected
    summary=pd.read_csv(RUN/'summaries.csv')
    annual=pd.read_csv(RUN/'annual.csv')
    checked=[]
    for variant in ('orange','blue'):
        tag=TAG+'_'+variant
        done=json.loads((RUN/(tag+'.completed.json')).read_text())
        assert done['native_mt5'] and done['returncode']==0
        for name,expected in done['outputs'].items():assert digest(RUN/name)==expected
        assert digest(RUN/(tag+'.htm'))==done['report_sha256']
        raw=pd.read_csv(RUN/f'runband_{tag}_1.00.csv',sep='\t',encoding='utf-16').set_index('ticket')
        trades=pd.read_csv(RUN/f'trades_{variant}.csv',parse_dates=['submitted','exit_time','entry_time']).set_index('ticket')
        assert raw.index.equals(trades.index)
        trades=trades.assign(gross=raw.trade_profit,planned_risk=raw.candle_range*2,net=raw.trade_profit-1.05)
        for row in summary.loc[summary.curve.eq('short '+variant)].itertuples():
            lo,hi={'2010-15':('2010-01-01','2016-01-01'),'2016-19':('2016-01-01','2020-01-01'),
                   '2020-26':('2020-01-01','2026-10-01'),'2016-26':('2016-01-01','2026-10-01')}[row.period]
            t=trades.loc[trades.submitted.ge(lo)&trades.submitted.lt(hi)]
            assert len(t)==row.trades
            values=dict(net_dollars=t.net.sum(),gross_mean_r=(t.gross/t.planned_risk).mean(),
                net_mean_r=(t.net/t.planned_risk).mean(),profit_factor=t.net[t.net>0].sum()/-t.net[t.net<0].sum(),
                daily_close_dd=dd(t.groupby(t.exit_time.dt.normalize()).net.sum().sort_index()),
                closed_trade_dd=dd(t.sort_values(['exit_time','entry_time']).net),
                stress1_net_dollars=t.net.sum()-len(t),stress2_net_dollars=t.net.sum()-2*len(t))
            for key,value in values.items():assert np.isclose(value,getattr(row,key),atol=1e-5,rtol=1e-8),(variant,row.period,key)
            checked.append(dict(variant=variant,period=row.period,trades=len(t),checks=list(values)))
        for row in annual.loc[annual.curve.eq('short '+variant)].itertuples():
            t=trades.loc[trades.submitted.dt.year.eq(row.year)&trades.submitted.lt('2026-10-01')]
            assert len(t)==row.trades and np.isclose(t.net.sum(),row.net_dollars,atol=1e-5)
        for row in summary.loc[summary.curve.eq('gated long + '+variant+' short')].itertuples():
            part=summary.loc[summary.period.eq(row.period)]
            a=part.loc[part.curve.eq('gated RTL long')].iloc[0]
            b=part.loc[part.curve.eq('short '+variant)].iloc[0]
            assert row.trades==a.trades+b.trades
            assert np.isclose(row.net_dollars,a.net_dollars+b.net_dollars,atol=1e-5)
    assert (RUN/f'runband_{TAG}_orange_1.00.csv').read_bytes()==(PRIOR/f'runband_{OLD_TAG}_on_1.00.csv').read_bytes()
    save_json(RUN/'independent_verification.json',dict(all_passed=True,native_hashes=True,summary_rows=checked,
        annual_rows=34,combined_arithmetic=True,orange_ledger_byte_identical=True))
    print('Independent checks passed: native hashes, 8 short period rows, 34 annual rows and combined arithmetic.')


if __name__=='__main__':main()
