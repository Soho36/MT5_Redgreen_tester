"""Native test and independent replay of a buy limit at every completed M30 low."""
from __future__ import annotations
import hashlib
import html
import json
import shutil
import sys
import numpy as np
import pandas as pd
import rtl_weekly_engine as e
from project_paths import PROJECT_ROOT as ROOT
from rtl_sell_limit_fade import CACHE, economics, metrics, max_dd, weekly_interval, compare

RUN = ROOT / 'Reports/candle_low_buy_limit_20261123'
DOC = ROOT / 'docs/baseline/candle-low-buy-limit'
SOURCE = ROOT / 'mt5/experts/Candle_low_buy_limit.mq5'
EXPERT = 'Candle_low_buy_limit'
TAG = 'candlelow_20261123'
SYMBOL = 'MNQcontDTBNT20102026_2'
PERIODS = {'2010-15': ('2010-01-01','2016-01-01'),
           '2016-19': ('2016-01-01','2020-01-01'),
           '2020-Sep2026': ('2020-01-01','2026-10-01'),
           '2016-Sep2026': ('2016-01-01','2026-10-01')}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def simulate(bars, cutoffs=None, spread=.25, through=0.):
    """MT5 minute OHLC ordering; buy-limit ask trigger, bid SL/TP, no lookahead.

    Resting orders/exits execute before OnTick at a new bar. Exits on a fresh
    fill are checked on the following quote, matching the tester model.
    through adds a conservative penetration requirement to entry AND target.
    """
    cutoffs = cutoffs or {}
    date, day, minute = (bars[k] for k in ('date','day','minute'))
    o,h,l,c = (bars[k] for k in 'ohlc')
    slot = day*48 + minute//30
    lowfirst=e.low_first(o,c)
    ticks=bars.get('ticks')
    pending=position=previous=current=None
    current_slot=-1
    prev_date=last_flat=skipped=0
    trades=[]

    def close(i,k,price,reason):
        nonlocal position
        trades.append({**position,'exit_time':e.stamp(day[i],minute[i],k),
                       'exit_price':price,'reason':reason})
        position=None

    for i in range(len(o)):
        new=slot[i]!=current_slot
        if new:
            previous,current=current,[o[i],h[i],l[i],c[i]]
            signal_slot=current_slot
            current_slot=slot[i]
        else:
            current[1]=max(current[1],h[i]); current[2]=min(current[2],l[i]); current[3]=c[i]
        if not new and (pending is None or l[i]+spread > pending['requested']-through):
            if position is None or (l[i]>position['sl'] and h[i]<position['tp']+through):
                continue
        # A one-tick minute has one quote, not four duplicate OHLC quotes.
        quotes=(o[i],) if ticks is not None and ticks[i]==1 else e.path(o[i],h[i],l[i],c[i],lowfirst[i])
        for k,p in enumerate(quotes):
            if position is not None and p<=position['sl']:
                close(i,k,position['sl'],'sl')
            if position is not None and p>=position['tp']+through:
                close(i,k,position['tp'],'tp')
            if pending is not None and p+spread<=pending['requested']-through:
                position={**pending,'entry_time':e.stamp(day[i],minute[i],k),'fill':pending['requested']}
                pending=None
            if k or not new:
                continue
            bar_min=minute[i]//30*30
            if prev_date and date[i]!=prev_date and last_flat!=prev_date:
                last_flat=prev_date
                if position is not None: close(i,k,p,'flatten')
                pending=None
            prev_date=date[i]
            if bar_min>=cutoffs.get(date[i],e.CUTOFF):
                if last_flat!=date[i]:
                    last_flat=date[i]
                    if position is not None: close(i,k,p,'flatten')
                    pending=None
                continue
            if position is not None:
                continue
            pending=None
            if bar_min<60 or previous is None:
                continue
            rng=previous[1]-previous[2]
            if rng<=0:
                continue
            if previous[2]>=p+spread:
                skipped+=1
                continue
            pending=dict(submitted=e.stamp(day[i],minute[i],0),requested=previous[2],
                         sl=previous[2]-rng,tp=previous[1],signal_slot=signal_slot,
                         signal_colour='green' if previous[3]>previous[0] else 'red' if previous[3]<previous[0] else 'doji')
    if position is not None: close(len(o)-1,3,c[-1],'end_of_data')
    return pd.DataFrame(trades),skipped


def prepare():
    assert not (RUN/'manifest.json').exists(), 'Preserve previous run'
    RUN.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(SOURCE,RUN/(EXPERT+'.mq5'))
    shutil.copyfile(e.CALENDAR,RUN/'early_closes.mqh')
    tester=dict(Expert='CodexResearch\\'+EXPERT+'.ex5',Symbol=SYMBOL,Period='M30',
                Optimization=0,Model=1,FromDate='2010.06.07',ToDate='2026.10.01',ForwardMode=0,
                Deposit=500000,Currency='USD',ProfitInPips=0,Leverage=100,ExecutionMode=0,
                OptimizationCriterion=0,Visual=0,UseLocal=1,UseRemote=0,UseCloud=0,
                ShutdownTerminal=1,Report=TAG+'.htm',ReplaceReport=1)
    lines=['[Tester]']+[f'{k}={v}' for k,v in tester.items()]+[
        '[TesterInputs]','Lots=1.0','RunTag='+TAG,'[Experts]','Enabled=0','AllowLiveTrading=0','AllowDllImport=0']
    (RUN/(TAG+'.ini')).write_text('\n'.join(lines)+'\n',encoding='utf-16')
    manifest=dict(expert=EXPERT,symbol=SYMBOL,jobs=[dict(tag=TAG,outputs=[TAG+'_stats.csv'])],
                  hashes={str(p):sha(p) for p in (SOURCE,e.CALENDAR,CACHE,DOC/'PROTOCOL.md')})
    (RUN/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Prepared',RUN)


def native():
    from analyze_rtl_vwap_cross import CELL,TAG as HTML_TAG,STAMP,number
    section=None; orders={}; rows=[]; active=None
    with (RUN/(TAG+'.htm')).open(encoding='utf-16') as stream:
        for line in stream:
            if '>Orders<' in line: section='orders'
            elif '>Deals<' in line: section='deals'
            if '<tr' not in line or '</tr>' not in line: continue
            cells=[html.unescape(HTML_TAG.sub('',x)).strip() for x in CELL.findall(line)]
            if not cells or not STAMP.match(cells[0]): continue
            if section=='orders' and len(cells)==11 and cells[3]=='buy limit':
                assert cells[2]==SYMBOL
                orders[int(cells[1])]=dict(submitted=cells[0],requested=number(cells[5]),sl=number(cells[6]),tp=number(cells[7]))
            elif section=='deals' and len(cells)==13 and cells[3]!='balance':
                assert cells[2]==SYMBOL and number(cells[5])==1
                assert number(cells[8])==number(cells[9])==0
                if cells[3:5]==['buy','in']:
                    assert active is None
                    active=dict(orders[int(cells[7])],entry_time=cells[0],fill=number(cells[6]))
                elif cells[3:5]==['sell','out']:
                    assert active is not None
                    rows.append(dict(active,exit_time=cells[0],exit_price=number(cells[6]),
                        trade_profit=number(cells[10]),reason='sl' if cells[12].startswith('sl') else
                        'tp' if cells[12].startswith('tp') else 'end_of_data' if cells[12].startswith('end of test') else 'flatten'))
                    active=None
                else: raise AssertionError(cells)
    assert active is None and rows
    frame=pd.DataFrame(rows)
    for col in ('submitted','entry_time','exit_time'): frame[col]=pd.to_datetime(frame[col],format='%Y.%m.%d %H:%M:%S')
    stats=pd.read_csv(RUN/(TAG+'_stats.csv'),sep='\t',encoding='utf-16').iloc[0]
    assert len(frame)==stats.trades
    assert np.isclose(frame.trade_profit.sum(),stats.gross,rtol=0,atol=1e-7)
    assert np.allclose(frame.trade_profit,(frame.exit_price-frame.fill)*2,rtol=0,atol=1e-8)
    assert frame.fill.eq(frame.requested).all()
    assert np.allclose(frame.tp-frame.fill,frame.fill-frame.sl)
    assert (frame.entry_time>=frame.submitted).all()
    assert (frame.entry_time.iloc[1:].reset_index(drop=True)>=frame.exit_time.iloc[:-1].reset_index(drop=True)).all()
    return frame,stats


def analyze():
    manifest=json.loads((RUN/'manifest.json').read_text())
    from pathlib import Path
    for p,digest in manifest['hashes'].items(): assert sha(Path(p))==digest,p
    bars=e.load_minutes(CACHE)
    volume=pd.read_csv(e.MINUTES,sep='\t',usecols=[0,1,6])
    assert len(volume)==len(bars['o'])
    assert np.array_equal(volume.iloc[:,0].str.replace('.','',regex=False).astype(np.int64),bars['date'])
    assert np.array_equal(volume.iloc[:,1].str[:2].astype(int)*60+volume.iloc[:,1].str[3:5].astype(int),bars['minute'])
    bars['ticks']=volume.iloc[:,2].to_numpy()
    assert (bars['ticks']>0).all()
    assert np.all(bars['h'][bars['ticks']==1]==bars['l'][bars['ticks']==1])
    keep=(bars['date']>=20100607)&(bars['date']<20261001)
    bars={k:v[keep] for k,v in bars.items()}
    calendar=pd.DatetimeIndex(np.unique(bars['day']).astype('datetime64[D]'))
    done=json.loads((RUN/(TAG+'.completed.json')).read_text())
    for name,digest in done['outputs'].items(): assert sha(RUN/name)==digest
    actual,stats=native()
    print('Replaying',len(bars['o']),'minutes',flush=True)
    replay,skipped=simulate(bars,e.load_cutoffs())
    check=compare(actual,replay)
    audit=dict(native_replay=check,replay_skipped_at_market=skipped,native_stats=stats.to_dict(),
               input_hashes=manifest['hashes'],raw_minute_source_sha256=sha(e.MINUTES),
               native_report_sha256=sha(RUN/(TAG+'.htm')),script_sha256=sha(ROOT/'python/candle_low_buy_limit.py'))
    (RUN/'verification.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps(check,indent=2),flush=True)
    replay.to_csv(RUN/'replay.csv',index=False)
    actual.to_csv(RUN/'native.csv',index=False)
    assert check.get('all_trades_identical'),check
    native_econ=economics(actual,short=False)
    # Label colour using causal signal information from the verified replay.
    colours=replay[['submitted','signal_colour']].assign(signal_minute=replay.submitted.dt.floor('min')).drop(columns='submitted')
    native_econ=native_econ.assign(signal_minute=native_econ.submitted.dt.floor('min')).merge(colours,on='signal_minute',how='left',validate='one_to_one')
    assert native_econ.signal_colour.notna().all()
    native_econ.to_csv(RUN/'trades.csv',index=False)
    cautious,_=simulate(bars,e.load_cutoffs(),through=.25)
    cautious=economics(cautious,short=False)
    cautious=cautious.loc[cautious.submitted>=actual.submitted.min().normalize()+pd.Timedelta(days=1)]
    cautious.to_csv(RUN/'trades_through.csv',index=False)
    rows=[]
    for arm,t in [('native',native_econ),('through_tick_replay',cautious)]:
        for period,(start,end) in PERIODS.items():
            part=t.loc[t.session.ge(start)&t.session.lt(end)]
            lo,hi=weekly_interval(part)
            rows.append(dict(arm=arm,period=period,**metrics(part,calendar[(calendar>=start)&(calendar<end)]),
                closed_trade_dd=max_dd(part.net),net_r_ci_low=lo,net_r_ci_high=hi))
    summary=pd.DataFrame(rows); summary.to_csv(RUN/'summary.csv',index=False)
    annual=[]
    for year,part in native_econ.groupby(native_econ.session.dt.year):
        annual.append(dict(year=year,**metrics(part,calendar[calendar.year==year]),closed_trade_dd=max_dd(part.net)))
    pd.DataFrame(annual).to_csv(RUN/'annual.csv',index=False)
    colour=[]
    for (year,co),part in native_econ.groupby([native_econ.session.dt.year,'signal_colour']):
        colour.append(dict(year=year,colour=co,trades=len(part),net=part.net.sum(),gross_r=part.gross_r.mean()))
    pd.DataFrame(colour).to_csv(RUN/'colour_descriptive.csv',index=False)
    plot(native_econ,cautious,calendar)
    print(summary.to_string(index=False),flush=True)


def plot(actual,cautious,calendar):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(11,5),layout='constrained')
    for label,t in [('MT5 native',actual),('Extra tick through entry and TP (replay)',cautious)]:
        daily=t.groupby(t.exit_time.dt.normalize()).net.sum().reindex(calendar,fill_value=0)
        ax.plot(daily.index,daily.cumsum(),label=label,lw=1.2)
    ax.axhline(0,color='gray',lw=.6); ax.grid(alpha=.2); ax.legend()
    ax.set_ylabel('Cumulative net USD, one MNQ')
    ax.set_title('Buy limit at every M30 candle low, SL one range below, TP at high\n$1.05/trade; session flatten; 1-minute OHLC, June 2010 - September 2026')
    (DOC/'img').mkdir(exist_ok=True)
    fig.savefig(DOC/'img/equity.png',dpi=150); plt.close(fig)


if __name__=='__main__':
    {'prepare':prepare,'analyze':analyze}[sys.argv[1]]()
