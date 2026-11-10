"""Separate native-statistic and raw-ledger checks of the news-day study."""
import json
import re
import zipfile
import hashlib
import numpy as np
import pandas as pd
from build_news_calendar import ROOT,RUN,OUT,sha
from prepare_rtl_news_days import BASE,TAG

def main():
    audit=json.loads((RUN/'verification.json').read_text())
    assert audit['all_passed']
    for name,value in audit['output_sha256'].items():assert sha(RUN/name)==value,name
    sources=json.loads((OUT/'us_major_news_2010_2026_manifest.json').read_text())
    with zipfile.ZipFile(OUT/'us_major_news_2010_2026_sources.zip') as archive:
        assert set(archive.namelist())==set(sources['sources'])
        for name,value in sources['sources'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==value
    events=pd.read_csv(OUT/'us_major_news_2010_2026.csv')
    base=pd.read_csv(BASE/f'rtlvwap_{TAG}_1.00.csv',sep='\t',encoding='utf-16')
    manifest=json.loads((RUN/'manifest.json').read_text())
    types={'control':[],'skip_cpi':['CPI'],'skip_payrolls':['PAYROLLS'],'skip_fomc':['FOMC'],
           'skip_all':['CPI','PAYROLLS','FOMC']}
    checks=[]
    for job in manifest['jobs']:
        tag=job['tag'];policy=job['policy']
        # Independent filter directly on the original raw ledger's entry date.
        blocked=set(events.loc[events.event.isin(types[policy]),'date'].str.replace('-','.'))
        expected=base.loc[~base.entry_time.str[:10].isin(blocked)].reset_index(drop=True)
        actual=pd.read_csv(RUN/job['outputs'][0],sep='\t',encoding='utf-16')
        fields=['entry_time','exit_time','trade_profit','candle_range']
        pd.testing.assert_frame_equal(actual[fields],expected[fields],check_exact=True)
        data=np.memmap(RUN/f'window_equity_{tag}.bin',dtype=[('t','<i8'),('b','<f8'),('e','<f8'),('n','<i8')],mode='r')
        peak=500000.;drawdown=0.
        for start in range(0,len(data),100000):
            chunk=data['e'][start:start+100000]
            highs=np.maximum.accumulate(np.r_[peak,chunk])[1:]
            drawdown=max(drawdown,float((highs-chunk).max()));peak=max(peak,float(chunk.max()))
        report=(RUN/(tag+'.htm')).read_text(encoding='utf-16')
        match=re.search(r'Equity Drawdown Maximal:</td>\s*<td[^>]*><b>([\d .,]+)\s*\(',report)
        assert match
        native=float(match[1].replace(' ',''))
        assert abs(drawdown-native)<.011,(policy,drawdown,native)
        checks.append(dict(policy=policy,trades=len(actual),raw_ledger_subset_exact=True,
                           recorded_gross_equity_dd=drawdown,mt5_gross_equity_dd=native))
    summary=pd.read_csv(RUN/'summary.csv')
    comparisons=pd.read_csv(RUN/'comparisons.csv')
    for row in comparisons.itertuples():
        random=pd.read_csv(RUN/f'placebo_{row.period}_{row.policy}.csv')
        assert len(random)==10000
        actual=summary.loc[summary.period.eq(row.period)&summary.policy.eq(row.policy)].iloc[0]
        assert abs((random.net<=actual.net_dollars).mean()*100-row.net_percentile)<1e-7
        assert abs((random.equity_dd>=actual.equity_dd).mean()*100-row.dd_better_percent)<1e-7
    output=dict(all_passed=True,native_gross_dd_and_raw_subset=checks,source_zip_hashes=True,
                placebo_saved_draws_checked=True,code_sha256=sha(__file__))
    (RUN/'independent_verification.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(output,indent=2))

if __name__=='__main__':main()
