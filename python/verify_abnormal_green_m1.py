"""Audit saved screen ledgers against raw bars without using the strategy simulator."""
import json
import numpy as np
import pandas as pd
from abnormal_green_m1 import SOURCE, RUN, DOC, COST, POINT, TICK, sha
from rtl_weekly_engine import load_minutes, load_cutoffs


def main(run=RUN, protocol=DOC/'PROTOCOL.md', bars=None):
    manifest=json.loads((run/'manifest.json').read_text())
    assert sha(SOURCE)==manifest['source_sha256']
    assert sha(protocol)==manifest['protocol_sha256']
    for name,digest in manifest['output_sha256'].items():assert sha(run/name)==digest
    b=load_minutes(source=SOURCE) if bars is None else bars;cutoffs=load_cutoffs()
    epochs=(b['day']*1440+b['minute'])*60
    widths=b['h']-b['l'];sums=np.r_[0.,np.cumsum(widths)]
    previous=np.full(len(widths),np.nan)
    previous[20:]=(sums[20:-1]-sums[:-21])/20
    ratio=np.divide(widths,previous,out=np.full(len(widths),np.nan),where=previous>0)
    movement=pd.Series(np.sign(b['c']-b['o'])).replace(0,np.nan).ffill().shift().fillna(0).to_numpy()
    checks=[]
    for specification in manifest['runs']:
        multiple=specification['multiplier']
        expected=np.flatnonzero((b['c']>b['o'])&(ratio>=multiple))
        for mode in ('directional','low_first','high_first'):
            label=f'{multiple:g}x_{mode}'
            signals=pd.read_csv(run/f'{label}_signals.csv')
            tr=pd.read_csv(run/f'{label}_trades.csv')
            assert np.array_equal(expected,signals['index'])
            eligible=set(signals.loc[signals.eligibility.eq('eligible'),'index'])
            all_marks=[0.];balance=0.
            for row in tr.itertuples():
                s=int(row.signal_index);entry=int(row.entry_index)
                assert s in eligible and entry>s
                assert not any(s<j<entry for j in eligible)
                assert np.all(b['h'][s+1:entry]<b['h'][s])
                fill=max(float(b['o'][entry]),float(b['h'][s]))
                assert row.entry_price==fill and row.sl==b['l'][s]-TICK
                target=fill+(fill-row.sl);assert row.tp==target
                entrysecond=pd.Timestamp(row.entry_time).second
                marks=[-COST];expected_exit=None
                for i in range(entry,int(row.exit_index)+1):
                    o,h,l,c=(float(b[k][i]) for k in 'ohlc')
                    if i>entry and (b['date'][i]!=row.date or b['minute'][i]>=cutoffs.get(int(b['date'][i]),1410)):
                        reason='fallback' if b['date'][i]!=row.date else 'flatten'
                        expected_exit=(int(epochs[i]),o,reason);marks.append((o-fill)*POINT-COST);break
                    lf=(c>o or (c==o and movement[i]<0)) if mode=='directional' else mode=='low_first'
                    sequence=(o,l,h,c) if lf else (o,h,l,c)
                    for second,price in zip((0,20,40,59),sequence):
                        if i==entry and second<entrysecond:continue
                        if price<=row.sl:
                            price=min(price,row.sl) if second==0 else row.sl
                            expected_exit=(int(epochs[i]+second),price,'sl')
                        elif price>=target:
                            price=target;expected_exit=(int(epochs[i]+second),price,'tp')
                        marks.append((price-fill)*POINT-COST)
                        if expected_exit:break
                    if expected_exit:break
                if expected_exit is None:
                    assert row.reason=='end_of_data' and row.exit_index==len(epochs)-1
                    expected_exit=(int(epochs[-1]+59),float(b['c'][-1]),'end_of_data')
                assert expected_exit==(int(pd.Timestamp(row.exit_time).timestamp()),row.exit_price,row.reason),(label,row.signal_time,expected_exit)
                assert np.isclose(row.min_mark_net,min(marks)) and np.isclose(row.max_mark_net,max(marks))
                m=np.asarray(marks)
                assert np.isclose(row.internal_dd,np.max(np.maximum.accumulate(m)-m))
                all_marks.extend(balance+m);balance+=row.net
            curve=np.asarray(all_marks)
            dd=float(np.max(np.maximum.accumulate(curve)-curve))
            summary=pd.read_csv(run/'summary.csv')
            reported=summary.loc[summary.multiplier.eq(multiple)&summary['mode'].eq(mode)&summary.period.eq('all')].iloc[0]
            assert np.isclose(dd,reported.path_equity_dd)
            checks.append(dict(label=label,signals=len(signals),trades=len(tr),all_signals_match_cumulative_sums=True,
                               all_first_entries_and_exits_match=True,marks_and_equity_dd_match=True,path_equity_dd=dd))
            print('Verified',label,len(tr),'trades; equity DD',dd,flush=True)
    (run/'independent_verification.json').write_text(json.dumps(dict(all_passed=True,checks=checks,code_sha256=sha(__file__)),indent=2)+'\n')


if __name__=='__main__':main()
