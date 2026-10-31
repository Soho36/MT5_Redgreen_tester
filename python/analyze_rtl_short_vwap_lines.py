"""Verify and compare native RTL-short orange/blue cutoff replays."""
import html
import json
from pathlib import Path
import numpy as np
import pandas as pd
import analyze_rtl_short_vwap as previous
import analyze_gg_vwap as gg
import build_rtl_vwap_features as vw
import analyze_rtl_vwap as av
import analyze_rtl_vwap_cross as cx
from prepare_rtl_short_vwap_lines import RUN,PRIOR,TAG,FEATURES,PROTOCOL
from prepare_rtl_short_vwap import TAG as PRIOR_TAG,BASE
from run_rtl_short_vwap_lines import checked_inputs
from project_paths import PROJECT_ROOT as ROOT


def check_decisions(variant,line):
    tag=TAG+'_'+variant
    d=pd.read_csv(RUN/f'short_vwap_{tag}.csv',sep='\t',encoding='cp1252')
    f=pd.read_csv(RUN/FEATURES,sep='\t',float_precision='round_trip')
    f.index=pd.to_datetime(f.bar_epoch,unit='s').dt.strftime('%Y.%m.%d %H:%M:%S')
    row=f.reindex(d.signal_bar)
    now=pd.to_datetime(d.time,format='%Y.%m.%d %H:%M:%S')
    known=row.known.eq(1).to_numpy() & pd.to_datetime(row.session_epoch,unit='s').eq(now.dt.normalize().to_numpy()).to_numpy()
    z=-1 if line==0 else 0
    cutoff=row.vwap+z*row.a20
    eligible=known & row.close.lt(cutoff).to_numpy()
    assert np.array_equal(d.known.to_numpy().astype(bool),known)
    assert np.array_equal(d.eligible.to_numpy().astype(bool),eligible)
    assert np.array_equal(d.allowed.to_numpy().astype(bool),eligible)
    assert d.filter_line.eq(line).all()
    for column in ('vwap','a20'):
        assert np.allclose(d[column].to_numpy()[known],row[column].to_numpy()[known],atol=1e-8,rtol=0)
    assert np.allclose(d.cutoff.to_numpy()[known],cutoff.to_numpy()[known],atol=1e-8,rtol=0)
    assert np.allclose(d.signal_close.to_numpy()[known],row.close.to_numpy()[known],atol=1e-8,rtol=0)
    decisions=d.assign(slot=now.dt.floor('30min')).set_index('slot')
    assert decisions.index.is_unique
    section=None
    orders=[]
    for text in (RUN/(tag+'.htm')).read_text(encoding='utf-16').splitlines():
        if '>Orders<' in text:section='orders'
        elif '>Deals<' in text:section='deals'
        if section!='orders' or '<tr' not in text or '</tr>' not in text:continue
        cells=[html.unescape(cx.TAG.sub('',value)).strip() for value in cx.CELL.findall(text)]
        if len(cells)==11 and cx.STAMP.match(cells[0]) and cells[3]=='sell stop':
            decision=decisions.loc[pd.Timestamp(cells[0]).floor('30min')]
            assert decision.allowed==1
            orders.append(dict(ticket=int(cells[1]),signal_bar=decision.signal_bar,
                               requested_price=cx.number(cells[5]),original_sl=cx.number(cells[6])))
    counts=dict(candidates=len(d),known=int(known.sum()),eligible=int(eligible.sum()),blocked=int((~eligible).sum()),
                original_orders=len(orders),decision_mismatches=0,cutoff_z=z,
                known_equal_cutoff=int((known & row.close.eq(cutoff).to_numpy()).sum()),
                unknown_allowed=int(d.loc[~known,'allowed'].sum()))
    return counts,pd.DataFrame(orders)


def check_report(variant):
    tag=TAG+'_'+variant
    done=json.loads((RUN/(tag+'.completed.json')).read_text())
    assert done['returncode']==0
    for name,expected in done['outputs'].items():assert av.digest(RUN/name)==expected,name
    assert av.digest(RUN/(tag+'.htm'))==done['report_sha256']
    trades=previous.economics(previous.parse_short_report(RUN/(tag+'.htm'),'MNQcontDTBNT20102026_2'))
    raw=pd.read_csv(RUN/f'runband_{tag}_1.00.csv',sep='\t',encoding='utf-16')
    stats=pd.read_csv(RUN/f'runband_{tag}_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
    assert len(raw)==len(trades)==int(stats.trades)
    assert np.array_equal(raw.ticket,trades.ticket)
    assert np.allclose(raw.trade_profit,trades.trade_profit,atol=1e-8,rtol=0)
    assert np.allclose(raw.candle_range*2,trades.initial_risk_dollars,atol=1e-8,rtol=0)
    assert np.allclose(trades.trade_profit,(trades.fill_price-trades.exit_price)*2,atol=1e-8,rtol=0)
    assert np.isclose(raw.trade_profit.sum(),stats.net_profit,atol=1e-6,rtol=0)
    return trades


def main():
    checked_inputs()
    assert json.loads((RUN/'orange_validation.json').read_text())['all_passed']
    features=gg.load_features()
    frames={}
    checks={}
    for variant,line in [('orange',0),('blue',1)]:
        frame=check_report(variant)
        counts,orders=check_decisions(variant,line)
        labelled=vw.label_trades(frame,features)
        cutoff=labelled.vwap-(labelled.a20 if line==0 else 0)
        assert labelled.close.lt(cutoff).all()
        assert labelled.close.gt(labelled.open).all()
        assert np.allclose(labelled.low,labelled.requested_price,atol=1e-8,rtol=0)
        assert np.allclose(labelled.high,labelled.original_sl,atol=1e-8,rtol=0)
        of=features.set_index(features.bar_time.dt.strftime('%Y.%m.%d %H:%M:%S')).reindex(orders.signal_bar)
        assert of.close.gt(of.open).all()
        assert np.allclose(of.low,orders.requested_price,atol=1e-8,rtol=0)
        assert np.allclose(of.high,orders.original_sl,atol=1e-8,rtol=0)
        frame.to_csv(RUN/f'trades_{variant}.csv',index=False,float_format='%.17g')
        frames[variant]=frame
        checks[variant]=dict(**counts,filled_trades=len(frame),all_order_levels_match_signal=True)
    original=previous.economics(previous.parse_short_report(PRIOR/(PRIOR_TAG+'_on.htm'),'MNQcontDTBNT20102026_2'))
    pd.testing.assert_frame_equal(frames['orange'],original)
    baseline=previous.economics(previous.parse_short_report(BASE/'ymbase_20261023_rtl_short_nq.htm','MNQcontDTBNT20102026_2'))
    long=previous.economics(cx.parse_report(ROOT/'Reports/rtl_vwap_ea_20261028/vwapea_20261028_file.htm','MNQcontDTBNT20102026_2'),short=False)
    curves={'short unfiltered':baseline,'short orange':frames['orange'],'short blue':frames['blue'],
            'gated RTL long':long,'gated long + orange short':pd.concat([long,frames['orange']],ignore_index=True),
            'gated long + blue short':pd.concat([long,frames['blue']],ignore_index=True)}
    calendar=gg.nq_calendar()
    rows=[]
    for period,(start,stop) in previous.PERIODS.items():
        cal=calendar[(calendar>=start)&(calendar<stop)]
        for curve,frame in curves.items():
            part=frame.loc[frame.session.ge(start)&frame.session.lt(stop)]
            row=dict(period=period,curve=curve,**previous.metrics(part,cal))
            if curve in ('short orange','short blue'):row.update(previous.bootstrap(part,cal))
            rows.append(row)
    summaries=pd.DataFrame(rows)
    summaries.to_csv(RUN/'summaries.csv',index=False,float_format='%.10g')
    annual=[]
    for curve,frame in curves.items():
        frame=frame.loc[frame.session.lt(previous.END)]
        for year,part in frame.groupby(frame.session.dt.year):
            annual.append(dict(curve=curve,year=int(year),**previous.metrics(part,calendar[calendar.year==year])))
    pd.DataFrame(annual).to_csv(RUN/'annual.csv',index=False,float_format='%.10g')
    # Reconcile the full orange output against the original published period rows.
    prior=pd.read_csv(PRIOR/'summaries.csv')
    for row in summaries.loc[summaries.curve.eq('short orange')].itertuples():
        old=prior.loc[prior.period.eq(row.period)&prior.curve.eq('short full replay')].iloc[0]
        for column in ('trades','net_dollars','gross_mean_r','net_mean_r','profit_factor','daily_close_dd','closed_trade_dd'):
            assert np.isclose(getattr(row,column),old[column],atol=1e-5,rtol=1e-8),(row.period,column)
    av.save_json(RUN/'verification.json',dict(all_passed=True,orange_identical_to_original=True,
        native_output_hashes_verified=True,decisions=checks,
        output_hashes={name:av.digest(RUN/name) for name in ('summaries.csv','annual.csv','trades_orange.csv','trades_blue.csv')}))
    print(summaries.to_string(index=False),flush=True)
    plot(curves,calendar)


def plot(curves,calendar):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,layout='constrained')
    cal=calendar[(calendar>='2016-01-01')&(calendar<previous.END)]
    groups=[('short unfiltered','short orange','short blue'),('gated RTL long','gated long + orange short','gated long + blue short')]
    colors=['#7f8791','#dc861e','#2179b5']
    for ax,names in zip(axes,groups):
        for name,color in zip(names,colors):
            frame=curves[name].loc[curves[name].session.ge(cal[0])&curves[name].session.lt(previous.END)]
            daily=frame.groupby(frame.exit_time.dt.normalize()).net_dollars.sum().reindex(cal,fill_value=0.)
            ax.plot(cal,daily.cumsum(),label=name,color=color,lw=1.2)
        ax.axhline(0,color='gray',lw=.6);ax.grid(alpha=.2);ax.legend();ax.set_ylabel('Net USD')
    axes[0].set_title('RTL short: orange VWAP - A20 versus blue VWAP eligibility\nOne MNQ per leg; $1.05/trade; native MT5; 2016 - September 2026')
    axes[1].set_title('Independent legs summed without netting')
    fig.savefig(RUN/'equity.png',dpi=150)
    plt.close(fig)


if __name__=='__main__':main()
