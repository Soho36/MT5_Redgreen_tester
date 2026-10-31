"""Verify and analyse native MT5 OFF/ON short VWAP runs.

All dollar results are one MNQ, less $1.05 per completed trade.
"""
from pathlib import Path
import json
import sys
import html
import numpy as np
import pandas as pd
import analyze_rtl_vwap as av
import analyze_rtl_vwap_cross as cx
import analyze_gg_vwap as gg
import build_rtl_vwap_features as vw
from analyze_rtl_vwap_cross import CELL, TAG as HTML_TAG, STAMP, number
from prepare_rtl_short_vwap import RUN, BASE, TAG, FEATURES, PROTOCOL
from project_paths import PROJECT_ROOT as ROOT

PERIODS = {'2010-15': ('2010-01-01','2016-01-01'), '2016-19': ('2016-01-01','2020-01-01'),
           '2020-26': ('2020-01-01','2026-10-01'), '2016-26': ('2016-01-01','2026-10-01')}
END = pd.Timestamp('2026-10-01')
REFERENCE = BASE/'ymbase_20261023_rtl_short_nq.htm'
CACHE = ROOT/'Reports/rtl_weekly_flatten_20261027/minutes.npz'


def economics(frame, short=True):
    frame=frame.copy()
    frame['session']=frame.submitted.dt.normalize()
    frame['initial_risk_dollars']=(frame.original_sl-frame.requested_price)*2 if short else (frame.requested_price-frame.original_sl)*2
    assert frame.initial_risk_dollars.gt(0).all()
    frame['gross_r']=frame.trade_profit/frame.initial_risk_dollars
    frame['net_dollars']=frame.trade_profit-1.05
    frame['net_r']=frame.net_dollars/frame.initial_risk_dollars
    frame['week_start']=frame.session-pd.to_timedelta(frame.session.dt.dayofweek,unit='D')
    return frame


def parse_short_report(path, symbol):
    """Sell-stop orders and sell-in/buy-out deal pairs from an MT5 tester report."""
    orders, trades, active, section = {}, [], None, None
    with Path(path).open(encoding='utf-16') as stream:
        for line in stream:
            if '>Orders<' in line:
                section = 'orders'
            elif '>Deals<' in line:
                section = 'deals'
            if '<tr' not in line or '</tr>' not in line:
                continue
            cells = [html.unescape(HTML_TAG.sub('', text)).strip() for text in CELL.findall(line)]
            if not cells or not STAMP.match(cells[0]):
                continue
            if section == 'orders' and len(cells) == 11 and cells[3] in ('sell stop', 'sell'):
                assert cells[2] == symbol and cells[3] == 'sell stop', cells
                ticket = int(cells[1])
                assert ticket not in orders
                orders[ticket] = {'submitted': cells[0], 'requested_price': number(cells[5]),
                                  'original_sl': number(cells[6]), 'state': cells[9]}
            elif section == 'deals' and len(cells) == 13 and cells[3] != 'balance':
                assert cells[2] == symbol, cells
                assert number(cells[5]) == 1 and number(cells[8]) == 0 and number(cells[9]) == 0, cells
                if cells[3:5] == ['sell', 'in']:
                    assert active is None
                    ticket = int(cells[7])
                    assert ticket in orders and orders[ticket]['state'] == 'filled'
                    active = dict(orders[ticket], ticket=ticket, entry_time=cells[0],
                                  fill_price=number(cells[6]), entry_profit=number(cells[10]))
                elif cells[3:5] == ['buy', 'out']:
                    assert active is not None
                    trades.append(dict(active, exit_time=cells[0], exit_price=number(cells[6]),
                                       trade_profit=active['entry_profit']+number(cells[10]),
                                       exit_comment=cells[12]))
                    active = None
                else:
                    raise ValueError(f'Unsupported deal {cells[3:5]}')
    assert active is None and trades
    frame = pd.DataFrame(trades).drop(columns=['state', 'entry_profit'])
    assert frame.ticket.is_unique
    for column in ('submitted', 'entry_time', 'exit_time'):
        frame[column] = pd.to_datetime(frame[column], format='%Y.%m.%d %H:%M:%S')
    return frame


def metrics(frame, calendar):
    net=frame.net_dollars
    daily=frame.groupby(frame.exit_time.dt.normalize()).net_dollars.sum().reindex(calendar,fill_value=0.)
    order=frame.sort_values(['exit_time','entry_time','ticket']).net_dollars.to_numpy()
    losses=-net[net<0].sum()
    return dict(trades=len(frame),net_dollars=float(net.sum()),gross_mean_r=float(frame.gross_r.mean()),
                net_mean_r=float(frame.net_r.mean()),profit_factor=float(net[net>0].sum()/losses) if losses else None,
                daily_close_dd=av.max_dd(daily),closed_trade_dd=av.max_dd(order),
                win_pct=float(100*net.gt(0).mean()),stress1_net_dollars=float(net.sum()-len(frame)),
                stress2_net_dollars=float(net.sum()-2*len(frame)))


def bootstrap(frame, calendar, seed=20261031, draws=5000):
    weeks=pd.date_range(calendar[0]-pd.Timedelta(days=calendar[0].dayofweek),
                        calendar[-1]-pd.Timedelta(days=calendar[-1].dayofweek),freq='7D')
    d=frame.groupby('week_start').agg(net=('net_dollars','sum'), r=('net_r','sum'), n=('net_r','count')).reindex(weeks,fill_value=0.)
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,len(weeks),size=(draws,int(np.ceil(len(weeks)/4))))
    ix=((starts[:,:,None]+np.arange(4))%len(weeks)).reshape(draws,-1)[:,:len(weeks)]
    results=[]
    for i in range(0,draws,100): results.append(d.to_numpy()[ix[i:i+100]].sum(axis=1))
    z=np.concatenate(results)
    mean_r=z[:,1]/z[:,2]
    return dict(net_mean_r_ci95_low=float(np.quantile(mean_r,.025)),net_mean_r_ci95_high=float(np.quantile(mean_r,.975)),
                boot_net_positive_fraction=float((z[:,0]>0).mean()),bootstrap_draws=draws,block_weeks=4)


def check_report(variant):
    tag=TAG+'_'+variant
    frame=economics(parse_short_report(RUN/(tag+'.htm'),'MNQcontDTBNT20102026_2'))
    raw=pd.read_csv(RUN/f'runband_{tag}_1.00.csv',sep='\t',encoding='utf-16')
    stats=pd.read_csv(RUN/f'runband_{tag}_1.00_stats.csv',sep='\t',encoding='utf-16').iloc[0]
    assert len(raw)==len(frame)==int(stats.trades)
    assert np.array_equal(raw.ticket.to_numpy(),frame.ticket.to_numpy())
    assert np.allclose(raw.trade_profit,frame.trade_profit,atol=1e-8,rtol=0)
    assert np.allclose(raw.candle_range*2,frame.initial_risk_dollars,atol=1e-8,rtol=0)
    assert np.isclose(frame.trade_profit.sum(),stats.net_profit,atol=1e-6,rtol=0)
    assert np.allclose(frame.trade_profit,(frame.fill_price-frame.exit_price)*2,atol=1e-8,rtol=0)
    return frame


def check_decisions():
    d=pd.read_csv(RUN/f'short_vwap_{TAG}_on.csv',sep='\t',encoding='cp1252')
    f=pd.read_csv(RUN/FEATURES,sep='\t',float_precision='round_trip')
    f.index=pd.to_datetime(f.bar_epoch,unit='s').dt.strftime('%Y.%m.%d %H:%M:%S')
    row=f.reindex(d.signal_bar)
    now=pd.to_datetime(d.time,format='%Y.%m.%d %H:%M:%S')
    known=row.known.eq(1).to_numpy() & pd.to_datetime(row.session_epoch,unit='s').eq(now.dt.normalize().to_numpy()).to_numpy()
    eligible=known & row.close.lt(row.vwap-row.a20).to_numpy()
    assert np.array_equal(known,d.known.to_numpy().astype(bool))
    assert np.array_equal(eligible,d.eligible.to_numpy().astype(bool))
    assert np.array_equal(eligible,d.allowed.to_numpy().astype(bool))
    for c in ('vwap','a20'):
        assert np.allclose(row[c].to_numpy()[known],d[c].to_numpy()[known],atol=1e-8,rtol=0)
    assert np.allclose(row.close.to_numpy()[known],d.signal_close.to_numpy()[known],atol=1e-8,rtol=0)
    # Inspect every original sell-stop order, including canceled/unfilled ones.
    order_times=[]
    section=None
    for line in (RUN/(TAG+'_on.htm')).read_text(encoding='utf-16').splitlines():
        if '>Orders<' in line: section='orders'
        elif '>Deals<' in line: section='deals'
        if section!='orders' or '<tr' not in line or '</tr>' not in line: continue
        cells=[html.unescape(HTML_TAG.sub('',text)).strip() for text in CELL.findall(line)]
        if len(cells)==11 and STAMP.match(cells[0]) and cells[3]=='sell stop':
            order_times.append(pd.Timestamp(cells[0]).floor('30min'))
    allowed=set(now[d.allowed.eq(1)].dt.floor('30min'))
    assert set(order_times).issubset(allowed)
    return dict(candidates=len(d),known=int(known.sum()),eligible=int(eligible.sum()),
                blocked=int((~eligible).sum()),original_sell_stop_orders=len(order_times),
                decision_mismatches=0,all_submitted_orders_have_allowed_decision=True)


def main():
    assert json.loads((RUN/'baseline_validation.json').read_text())['all_passed']
    manifest=json.loads((RUN/'native_input_manifest.json').read_text())
    for path,expected in manifest['input_hashes'].items(): assert av.digest(path)==expected,path
    native=check_report('off')
    replay=check_report('on')
    decisions=check_decisions()
    reference=economics(parse_short_report(REFERENCE,'MNQcontDTBNT20102026_2'))
    pd.testing.assert_frame_equal(native,reference)
    features=gg.load_features()
    labelled=vw.label_trades(replay,features)
    assert labelled.distance.eq('far_below').all(),labelled.distance.value_counts()
    assert labelled.close.gt(labelled.open).all()
    assert np.allclose(labelled.low,labelled.requested_price,rtol=0,atol=1e-8)
    assert np.allclose(labelled.high,labelled.original_sl,rtol=0,atol=1e-8)
    native_labels=vw.label_trades(native,features)
    omission=native_labels.loc[native_labels.distance.eq('far_below')]
    for name,frame in [('baseline',native_labels),('replay',labelled)]: frame.to_csv(RUN/f'trades_{name}.csv',index=False,float_format='%.17g')
    rtlbase=economics(cx.parse_report(BASE/'ymbase_20261023_rtl_nq.htm','MNQcontDTBNT20102026_2'),short=False)
    rtlon=economics(cx.parse_report(ROOT/'Reports/rtl_vwap_ea_20261028/vwapea_20261028_file.htm','MNQcontDTBNT20102026_2'),short=False)
    calendar=gg.nq_calendar()
    rows=[]
    for period,(start,stop) in PERIODS.items():
        cal=calendar[(calendar>=start)&(calendar<stop)]
        inside=lambda d:d.loc[d.session.ge(start)&d.session.lt(stop)]
        curves={'short baseline':native,'short qualifying baseline subset':omission,'short full replay':replay,
                'RTL long baseline':rtlbase,'RTL long gated':rtlon,
                'gated RTL long + gated short':pd.concat([rtlon,replay],ignore_index=True)}
        for curve,frame in curves.items():
            part=inside(frame)
            row=dict(period=period,curve=curve,**metrics(part,cal))
            if curve=='short full replay': row.update(bootstrap(part,cal))
            rows.append(row)
    summaries=pd.DataFrame(rows)
    summaries.to_csv(RUN/'summaries.csv',index=False,float_format='%.10g')
    annual=[]
    for curve,frame in [('short baseline',native),('short full replay',replay),('RTL long gated',rtlon),
                        ('gated RTL long + gated short',pd.concat([rtlon,replay],ignore_index=True))]:
        frame=frame.loc[frame.session.lt(END)]
        for year,part in frame.groupby(frame.session.dt.year):
            cal=calendar[calendar.year==year]
            annual.append(dict(year=int(year),curve=curve,**metrics(part,cal)))
    pd.DataFrame(annual).to_csv(RUN/'annual.csv',index=False,float_format='%.10g')
    shared=set(native.submitted)&set(replay.submitted)
    attribution=[]
    for period,(start,stop) in PERIODS.items():
        for source,frame in [('baseline',native),('replay',replay)]:
            for kind in ('shared','only_this_run'):
                part=frame.loc[frame.session.ge(start)&frame.session.lt(stop)&frame.submitted.isin(shared).eq(kind=='shared')]
                attribution.append(dict(period=period,source=source,kind=kind,trades=len(part),net_dollars=float(part.net_dollars.sum())))
    pd.DataFrame(attribution).to_csv(RUN/'attribution.csv',index=False)
    av.save_json(RUN/'verification.json',dict(all_passed=True,baseline_native_exact=True,
        native_gated_run_executed=True,decisions=decisions,replay_trades=len(replay),all_submissions_far_below=True,
        all_signal_candles_green=True,signal_low_and_high_match_order_levels=True,
        label_hash=av.digest(RUN/FEATURES),outcome_hashes={p.name:av.digest(p) for p in RUN.glob('*.csv') if p.name!='submission_gate.csv'}))
    print(summaries.to_string(index=False),flush=True)
    plot(native,replay,rtlon,calendar)


def plot(native,replay,rtlon,calendar):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cal=calendar[(calendar>='2016-01-01')&(calendar<END)]
    fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,layout='constrained')
    for frame,label in [(native,'Short unfiltered'),(replay,'Short below orange')]:
        part=frame.loc[frame.session.ge('2016-01-01')&frame.session.lt(END)]
        eq=part.groupby(part.exit_time.dt.normalize()).net_dollars.sum().reindex(cal,fill_value=0.).cumsum()
        axes[0].plot(eq.index,eq,label=label,lw=1.3)
    for frame,label in [(rtlon,'Gated RTL long'),(pd.concat([rtlon,replay]),'Gated long + gated short')]:
        part=frame.loc[frame.session.ge('2016-01-01')&frame.session.lt(END)]
        eq=part.groupby(part.exit_time.dt.normalize()).net_dollars.sum().reindex(cal,fill_value=0.).cumsum()
        axes[1].plot(eq.index,eq,label=label,lw=1.3)
    for ax in axes:
        ax.axhline(0,color='gray',lw=.6); ax.grid(alpha=.2);ax.legend();ax.set_ylabel('Net USD')
    axes[0].set_title('RTL short: entries only below unchanged VWAP - A20\nOne MNQ per leg, $1.05/trade; 2016 - September 2026; native MT5 full replay')
    axes[1].set_title('Independent legs summed without netting')
    fig.savefig(RUN/'equity.png',dpi=150)
    plt.close(fig)


if __name__=='__main__': main()
