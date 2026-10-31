"""Verify native upper-band shorting and compare the frozen historical controls."""
import html
import json
import numpy as np
import pandas as pd
import analyze_rtl_short_vwap as original
import analyze_rtl_short_vwap_lines as line_study
import analyze_rtl_vwap_cross as cx
import analyze_rtl_vwap as av
import analyze_gg_vwap as gg
import build_rtl_vwap_features as vw
from prepare_rtl_short_vwap_upper import RUN,PRIOR,TAG,FEATURES
from prepare_rtl_short_vwap import BASE
from run_rtl_short_vwap_upper import checked_inputs
from project_paths import PROJECT_ROOT as ROOT


def check_decisions(variant,z,side):
    tag=TAG+'_'+variant
    d=pd.read_csv(RUN/f'short_vwap_{tag}.csv',sep='\t',encoding='cp1252')
    f=pd.read_csv(RUN/FEATURES,sep='\t',float_precision='round_trip')
    f.index=pd.to_datetime(f.bar_epoch,unit='s').dt.strftime('%Y.%m.%d %H:%M:%S')
    row=f.reindex(d.signal_bar)
    now=pd.to_datetime(d.time,format='%Y.%m.%d %H:%M:%S')
    known=row.known.eq(1).to_numpy()&pd.to_datetime(row.session_epoch,unit='s').eq(now.dt.normalize().to_numpy()).to_numpy()
    cutoff=row.vwap+z*row.a20
    qualifies=row.close.gt(cutoff) if side else row.close.lt(cutoff)
    eligible=known&qualifies.to_numpy()
    assert np.array_equal(d.known.to_numpy().astype(bool),known)
    assert np.array_equal(d.eligible.to_numpy().astype(bool),eligible)
    assert np.array_equal(d.allowed.to_numpy().astype(bool),eligible)
    assert d.filter_line.eq(0).all() and d.filter_side.eq(side).all()
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
            orders.append(dict(signal_bar=decision.signal_bar,requested_price=cx.number(cells[5]),original_sl=cx.number(cells[6])))
    return dict(candidates=len(d),known=int(known.sum()),eligible=int(eligible.sum()),blocked=int((~eligible).sum()),
                original_orders=len(orders),mismatches=0,offset_z=z,side=side,
                unknown_allowed=int(d.loc[~known,'allowed'].sum())),pd.DataFrame(orders)


def main():
    checked_inputs()
    assert json.loads((RUN/'lower_validation.json').read_text())['all_passed']
    line_study.RUN=RUN
    line_study.TAG=TAG
    features=gg.load_features()
    frames={}
    checks={}
    for variant,z,side in [('lower',-1,0),('upper',1,1)]:
        frame=line_study.check_report(variant)
        counts,orders=check_decisions(variant,z,side)
        labelled=vw.label_trades(frame,features)
        cutoff=labelled.vwap+z*labelled.a20
        assert (labelled.close.gt(cutoff) if side else labelled.close.lt(cutoff)).all()
        assert labelled.close.gt(labelled.open).all()
        assert np.allclose(labelled.low,labelled.requested_price,atol=1e-8,rtol=0)
        assert np.allclose(labelled.high,labelled.original_sl,atol=1e-8,rtol=0)
        order_features=features.set_index(features.bar_time.dt.strftime('%Y.%m.%d %H:%M:%S')).reindex(orders.signal_bar)
        assert order_features.close.gt(order_features.open).all()
        assert np.allclose(order_features.low,orders.requested_price,atol=1e-8,rtol=0)
        assert np.allclose(order_features.high,orders.original_sl,atol=1e-8,rtol=0)
        frame.to_csv(RUN/f'trades_{variant}.csv',index=False,float_format='%.17g')
        frames[variant]=frame
        checks[variant]=dict(**counts,filled_trades=len(frame),signal_levels_match_all_orders=True)
    old=original.economics(original.parse_short_report(PRIOR/'rtlshortlines_20261031_orange.htm','MNQcontDTBNT20102026_2'))
    pd.testing.assert_frame_equal(frames['lower'],old)
    baseline=original.economics(original.parse_short_report(BASE/'ymbase_20261023_rtl_short_nq.htm','MNQcontDTBNT20102026_2'))
    blue_path=PRIOR/'trades_blue.csv'
    blue_meta=json.loads((PRIOR/'verification.json').read_text())
    assert av.digest(blue_path)==blue_meta['output_hashes']['trades_blue.csv']
    blue=pd.read_csv(blue_path,parse_dates=['submitted','entry_time','exit_time','session','week_start'])
    long=original.economics(cx.parse_report(ROOT/'Reports/rtl_vwap_ea_20261028/vwapea_20261028_file.htm','MNQcontDTBNT20102026_2'),short=False)
    curves={'short unfiltered':baseline,'short lower':frames['lower'],'short blue':blue,'short upper':frames['upper'],
        'gated RTL long':long,'long + lower short':pd.concat([long,frames['lower']],ignore_index=True),
        'long + upper short':pd.concat([long,frames['upper']],ignore_index=True)}
    calendar=gg.nq_calendar()
    rows=[]
    for period,(start,stop) in original.PERIODS.items():
        cal=calendar[(calendar>=start)&(calendar<stop)]
        for curve,frame in curves.items():
            part=frame.loc[frame.session.ge(start)&frame.session.lt(stop)]
            row=dict(period=period,curve=curve,**original.metrics(part,cal))
            if curve=='short upper':row.update(original.bootstrap(part,cal,seed=20261101))
            rows.append(row)
    summaries=pd.DataFrame(rows)
    summaries.to_csv(RUN/'summaries.csv',index=False,float_format='%.10g')
    annual=[]
    for curve,frame in curves.items():
        frame=frame.loc[frame.session.lt(original.END)]
        for year,part in frame.groupby(frame.session.dt.year):
            annual.append(dict(curve=curve,year=int(year),**original.metrics(part,calendar[calendar.year==year])))
    pd.DataFrame(annual).to_csv(RUN/'annual.csv',index=False,float_format='%.10g')
    prior=pd.read_csv(PRIOR/'summaries.csv')
    for row in summaries.loc[summaries.curve.eq('short lower')].itertuples():
        ref=prior.loc[prior.period.eq(row.period)&prior.curve.eq('short orange')].iloc[0]
        for column in ('trades','net_dollars','gross_mean_r','net_mean_r','daily_close_dd','closed_trade_dd'):
            assert np.isclose(getattr(row,column),ref[column],atol=1e-5,rtol=1e-8)
    av.save_json(RUN/'verification.json',dict(all_passed=True,lower_identical=True,native_output_hashes_verified=True,
        decisions=checks,output_hashes={name:av.digest(RUN/name) for name in ('summaries.csv','annual.csv','trades_lower.csv','trades_upper.csv')}))
    print(summaries.to_string(index=False),flush=True)
    plot(curves,calendar)


def plot(curves,calendar):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,layout='constrained')
    cal=calendar[(calendar>='2016-01-01')&(calendar<original.END)]
    for ax,names in zip(axes,[('short unfiltered','short lower','short blue','short upper'),
                            ('gated RTL long','long + lower short','long + upper short')]):
        for name in names:
            frame=curves[name].loc[curves[name].session.ge(cal[0])&curves[name].session.lt(original.END)]
            daily=frame.groupby(frame.exit_time.dt.normalize()).net_dollars.sum().reindex(cal,fill_value=0.)
            ax.plot(cal,daily.cumsum(),label=name,lw=1.2)
        ax.axhline(0,color='gray',lw=.6);ax.grid(alpha=.2);ax.legend();ax.set_ylabel('Net USD')
    axes[0].set_title('RTL short above VWAP + A20: native MT5 descriptive experiment\nOne MNQ per leg; $1.05/trade; 2016 - September 2026')
    axes[1].set_title('Independent legs summed without netting')
    fig.savefig(RUN/'equity.png',dpi=150)
    plt.close(fig)


if __name__=='__main__':main()
