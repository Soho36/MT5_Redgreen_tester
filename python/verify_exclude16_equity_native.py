"""Cross-check every passive gross-equity path against MT5's native equity-DD statistic."""
import json
import numpy as np
import pandas as pd
from analyze_rtl_vwap_slope import sha
from prepare_exclude16_replay import RUN as ORIGINAL
from prepare_exclude16_flatten import RUN as FLAT
from verify_exclude16_replay import DTYPE,maxdd


def main():
    for run in (ORIGINAL,FLAT):
        checks=[]
        for job in json.loads((run/'manifest.json').read_text())['jobs']:
            tag=job['tag'];data=np.memmap(run/f'window_equity_{tag}.bin',dtype=DTYPE,mode='r')
            stat=pd.read_csv(run/f'rtlvwap_{tag}_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
            observed=maxdd(data['equity'])
            assert abs(observed-stat.equity_dd)<1e-6,(tag,observed,stat.equity_dd)
            checks.append(dict(tag=tag,observed_gross_dd=observed,native_equity_dd=float(stat.equity_dd)))
            del data
        result=dict(all_passed=True,code_sha256=sha(__file__),jobs=checks)
        (run/'equity_native_crosscheck.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('Native gross equity-DD cross-checks passed:',len(checks))


if __name__=='__main__':main()
