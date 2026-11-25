"""Full replay of the full-body gate; original abnormal-M1 study stays intact."""
import json
import shutil
import numpy as np
import pandas as pd
from abnormal_green_m1 import SOURCE,RUN as BASE,DOC,sha,detect,simulate,metrics
from rtl_weekly_engine import load_minutes,load_cutoffs
from verify_abnormal_green_m1 import main as verify

RUN=BASE/'wick_filter'
PROTOCOL=DOC/'WICK_PROTOCOL.md'


def shape_gate(signals,minimum):
    if not 0<=minimum<=1:raise ValueError('Body fraction must be between zero and one')
    s=signals.copy()
    width=s['high']-s['low']
    if (width<=0).any() or (s['close']<=s['open']).any():
        raise ValueError('Expected positive-range green signal candles')
    s['body_fraction']=(s['close']-s['open'])/width
    s['upper_wick_fraction']=(s['high']-s['close'])/width
    s['lower_wick_fraction']=(s['open']-s['low'])/width
    s.loc[s.eligibility.eq('eligible') & s.body_fraction.lt(minimum),'eligibility']='long_wicks'
    return s


def markdown(frame):
    return '\n'.join(['| '+' | '.join(frame.columns)+' |','|'+'|'.join(['---']*len(frame.columns))+'|']+
                     ['| '+' | '.join(str(v) for v in r)+' |' for r in frame.itertuples(index=False,name=None)])


def main():
    RUN.mkdir(exist_ok=True)
    original=json.loads((BASE/'manifest.json').read_text())
    assert sha(SOURCE)==original['source_sha256']
    for name,digest in original['output_sha256'].items():assert sha(BASE/name)==digest
    print('Loading raw history',flush=True)
    b=load_minutes(source=SOURCE);cutoffs=load_cutoffs()
    signals=detect(b,cutoffs=cutoffs)
    old=pd.read_csv(BASE/'10x_directional_trades.csv')
    shaped=shape_gate(signals,0)
    original446=old.merge(shaped[['index','open','high','low','close','body_fraction','upper_wick_fraction','lower_wick_fraction']],
                         left_on='signal_index',right_on='index',validate='one_to_one')
    assert len(original446)==446
    original446.to_csv(RUN/'original_446_candle_shapes.csv',index=False)
    counts=[]
    for threshold in (.7,.8,.9,1.):
        subset=original446.loc[original446.body_fraction.ge(threshold)]
        counts.append(dict(minimum_body=threshold,count=len(subset),percent=100*len(subset)/446,
                           ledger_subset_net=float(subset.net.sum())))
    pd.DataFrame(counts).to_csv(RUN/'original_446_counts.csv',index=False)
    periods={'2010-15':(20100101,20160101),'2016-19':(20160101,20200101),
             '2020-Sep2026':(20200101,20261001),'Oct-Nov2026':(20261001,20261114),
             '2016-Nov2026':(20160101,20261114),'all':(20100101,20261114),
             **{str(y):(y*10000+101,(y+1)*10000+101) for y in range(2010,2027)}}
    rows=[];changes=[];checks=[]
    for threshold in (0.,.7,.8,.9):
        label='control' if threshold==0 else f'body{round(threshold*100)}'
        dest=RUN/label;dest.mkdir(exist_ok=True)
        gated=shape_gate(signals,threshold)
        idx=gated['index'].to_numpy(int)
        direct=(b['c'][idx]-b['o'][idx])/(b['h'][idx]-b['l'][idx])
        assert np.array_equal(gated.body_fraction.to_numpy(),direct)
        assert np.array_equal(gated.eligibility.eq('eligible'),signals.eligibility.eq('eligible')&(direct>=threshold))
        local=[]
        for mode in ('directional','low_first','high_first'):
            tr,states=simulate(b,gated,cutoffs,mode)
            reference=pd.read_csv(BASE/f'10x_{mode}_trades.csv',float_precision='round_trip')
            if threshold==0:
                pd.testing.assert_frame_equal(tr,reference,check_dtype=False,check_exact=True)
            else:
                assert tr.signal_index.isin(gated.loc[gated.eligibility.eq('eligible'),'index']).all()
            decisions=gated.copy()
            decisions['decision']=[states.get(int(i),s) for i,s in zip(gated['index'],gated.eligibility)]
            decisions.to_csv(dest/f'10x_{mode}_signals.csv',index=False)
            tr.to_csv(dest/f'10x_{mode}_trades.csv',index=False)
            shared=tr.merge(reference,on='signal_index',suffixes=('_filtered','_base'))
            different=(shared.entry_time_filtered!=shared.entry_time_base)|(shared.exit_time_filtered!=shared.exit_time_base)|(~np.isclose(shared.net_filtered,shared.net_base))
            changes.append(dict(filter=label,mode=mode,shared=len(shared),new=int((~tr.signal_index.isin(reference.signal_index)).sum()),
                                removed=int((~reference.signal_index.isin(tr.signal_index)).sum()),changed_shared=int(different.sum())))
            for period,(a,z) in periods.items():
                sub=tr.loc[tr.date.ge(a)&tr.date.lt(z)]
                sig=decisions.loc[decisions.date.ge(a)&decisions.date.lt(z)]
                top=float(sub.net.max()) if len(sub) else 0.
                row=dict(filter=label,minimum_body=threshold,multiplier=10.,mode=mode,period=period,
                         eligible=int(sig.eligibility.eq('eligible').sum()),largest_win=top,
                         net_without_largest=float(sub.net.sum()-top),**metrics(sub))
                rows.append(row);local.append(row)
            print(label,mode,metrics(tr),flush=True)
        pd.DataFrame(local).to_csv(dest/'summary.csv',index=False)
        manifest=dict(source=str(SOURCE),source_sha256=original['source_sha256'],protocol_sha256=sha(PROTOCOL),
                      code_sha256=sha(__file__),engine_sha256=sha(BASE.parents[1]/'python/abnormal_green_m1.py'),
                      cutoff_sha256=original['cutoff_sha256'],minimum_body=threshold,runs=[dict(multiplier=10.)],
                      output_sha256={p.name:sha(p) for p in dest.glob('*.csv')})
        (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        verify(dest,PROTOCOL,b)
        checks.append(dict(filter=label,raw_shape_check=True,control_exact=threshold==0,independent_audit=True))
    summary=pd.DataFrame(rows);summary.to_csv(RUN/'summary.csv',index=False)
    pd.DataFrame(changes).to_csv(RUN/'trade_changes.csv',index=False)
    (RUN/'verification.json').write_text(json.dumps(dict(all_passed=True,checks=checks,code_sha256=sha(__file__)),indent=2)+'\n')
    for src,name in [('summary.csv','wick_summary.csv'),('original_446_counts.csv','wick_counts.csv'),
                     ('trade_changes.csv','wick_trade_changes.csv'),('verification.json','wick_verification.json')]:
        shutil.copyfile(RUN/src,DOC/name)
    primary=summary.loc[summary['mode'].eq('directional') & summary.period.eq('all')]
    view=pd.DataFrame({'Filter':primary['filter'],'Trades':primary.trades,'Net $':primary.net.map(lambda v:f'{v:,.2f}'),
                       'Win %':primary.win_pct.map(lambda v:f'{v:.1f}'),'PF':primary.pf.map(lambda v:f'{v:.3f}'),
                       'Path DD $':primary.path_equity_dd.map(lambda v:f'{v:,.2f}'),
                       'Net extra $2/trade':primary.stress2_net.map(lambda v:f'{v:,.2f}')})
    eras=summary.loc[summary['mode'].eq('directional') & summary.period.isin(list(periods)[:6])]
    era=eras.pivot(index='period',columns='filter',values='net').reindex(list(periods)[:6])
    era=era[['control','body70','body80','body90']].map(lambda v:f'{v:,.2f}').reset_index()
    counts_frame=pd.DataFrame(counts)
    counts_view=pd.DataFrame({'Minimum body %':counts_frame.minimum_body.map(lambda v:f'{v*100:g}'),
                              'Of original 446':counts_frame['count'],'Share %':counts_frame.percent.map(lambda v:f'{v:.1f}')})
    annual=summary.loc[summary['mode'].eq('directional') & summary.period.str.fullmatch(r'\d{4}')]
    annual=annual.pivot(index='period',columns='filter',values='net')[['control','body70','body80','body90']].map(lambda v:f'{v:,.2f}').reset_index()
    paths=summary.loc[summary['filter'].eq('body80') & summary.period.eq('all')]
    pathview=pd.DataFrame({'Path':paths['mode'],'Trades':paths.trades,'Net $':paths.net.map(lambda v:f'{v:,.2f}'),
                          'Path DD $':paths.path_equity_dd.map(lambda v:f'{v:,.2f}')})
    changeview=pd.DataFrame(changes);changeview=changeview.loc[changeview['mode'].eq('directional')].drop(columns='mode')
    body80=primary.loc[primary['filter'].eq('body80')].iloc[0]
    text=f'''# Full-bodied abnormal green candles

2026-11-24 follow-up to the [initial 10x screen](RESULTS.md).
**Primary definition fixed before results: body >=80% of high-low range**;
upper and lower wicks together <=20%. 70% and 90% are descriptive neighbours,
not a selection of the best historical cutoff. [Protocol](WICK_PROTOCOL.md).

## How many of the original 446?

{markdown(counts_view)}

Exactly wickless means open=low and close=high. The main 80% gate retains 170
original candles and excludes 276 (61.9%). This measures total wick fraction,
not only the upper wick; both limits are known when the signal candle closes.

## Full replay results

All original entry, stop, immediate 1R TP, pending lifetime, cutoff and cost
rules retained. A rejected signal does not replace an existing qualifying pending
order. Full-history one MNQ, $1.05/trade, June 2010-November 13, 2026:

{markdown(view)}

The primary 80% rule yields **${body80.net:,.2f}** on **{int(body80.trades)} trades**,
with **${body80.path_equity_dd:,.2f}** marked path drawdown. Removing its largest
winning trade leaves **${body80.net_without_largest:,.2f}**. The net figures for
70/80/90% are exploratory neighbours on reused history, not unseen confirmation.

### Net dollars by period

{markdown(era)}

### Why replay instead of just deleting ledger rows?

{markdown(changeview)}

Shared counts signal IDs present in both runs; new counts previously untraded
signals that now fill; removed counts baseline signals no longer filled.
Changed shared compares entry time, exit time and net. Detailed candle shapes
and a ledger-only subset calculation are saved, separately from replay outcomes.

### 80% OHLC path sensitivities

{markdown(pathview)}

Python OHLC screen, not native MT5. Spread is not separately simulated;
$1/$2 extra per-trade costs are stresses, not real execution modeling. Path
sensitivities do not bound every possible intraminute price ordering.

### Annual net dollars

{markdown(annual)}

## Reproduction and evidence

```powershell
.\\venv\\Scripts\\python.exe -m unittest discover -s python -p "test_abnormal_green_m1*.py" -v
.\\venv\\Scripts\\python.exe python\\abnormal_green_m1_wicks.py
```

All three unfiltered controls match original ledgers exactly. Shape values and
gates checked against raw OHLC; independent cumulative-sum signal detection,
first-entry/exit and full marked-DD verification passes for all 12 runs.
Original study outputs preserved. Full new outputs and hashes:
`Reports/abnormal_green_m1_20261124/wick_filter/`. The
`original_446_candle_shapes.csv` file contains each candle's body/upper/lower-wick
fractions. Subfolders `body70`, `body80`, `body90` contain trade and decision
ledgers and individual manifests. Compact tables and checks sit beside this report.
No production settings changed.
'''
    (DOC/'WICK_RESULTS.md').write_text(text,encoding='utf-8')
    print(view.to_string(index=False));print(era.to_string(index=False))


if __name__=='__main__':main()
