"""Chronological performance and annual selection, independent of MT5 exports."""
import numpy as np
import pandas as pd

REGIMES=("bull", "neutral", "bear")
CANDIDATES=("baseline", "mild", "strong")


def metrics(trades, start, end, extra_cost=0.):
    start,end=pd.Timestamp(start),pd.Timestamp(end)
    t=trades[(trades.entry_time>=start)&(trades.entry_time<end)].copy()
    net=t.trade_profit-1.05-extra_cost
    events=pd.Series(net.values,index=t.exit_time).groupby(level=0).sum().sort_index()
    # Aggregate simultaneous exits before measuring portfolio drawdown.
    curve=events.cumsum()
    peaks=curve.cummax().clip(lower=0)
    dd=float((peaks-curve).max()) if len(curve) else 0.
    gain=float(net[net>0].sum()); loss=float(-net[net<0].sum())
    month_index=pd.period_range(start,end-pd.Timedelta(nanoseconds=1),freq="M")
    month=events.groupby(events.index.to_period("M")).sum().reindex(month_index,fill_value=0.)
    quarter=month.groupby(month.index.asfreq("Q")).sum()
    years=month.groupby(month.index.year).sum()
    peak=0.; underwater_since=None; peak_time=start; longest=0.
    for time,value in curve.items():
        if value>=peak-1e-8:
            if underwater_since is not None:
                longest=max(longest,(time-underwater_since).total_seconds()/86400)
            peak=float(value); peak_time=time; underwater_since=None
        elif underwater_since is None:
            underwater_since=peak_time
    if underwater_since is not None:
        longest=max(longest,(end-underwater_since).total_seconds()/86400)
    n=len(t)
    qualified=t.qualified_time.notna() if n else pd.Series(dtype=bool)
    mfes=float(t.mfe_money.clip(lower=0).sum())
    return dict(trades=n,net=float(net.sum()),dd=dd,net_dd=float(net.sum())/dd if dd else 0.,
                avg_trade=float(net.mean()) if n else 0.,pf=gain/loss if loss else None,
                profitable_months=float((month>0).mean()),profitable_years=float((years>0).mean()),
                worst_month=float(month.min()),worst_quarter=float(quarter.min()),worst_year=float(years.min()),
                longest_dd_days=longest,unrecovered_drawdown=underwater_since is not None,
                average_duration_minutes=float((t.exit_time-t.entry_time).dt.total_seconds().mean()/60) if n else 0.,
                target_qualification_rate=float(qualified.mean()) if n else 0.,
                qualified_exit_completion_rate=float((t.loc[qualified,"exit_reason"].astype(int)==3).mean()) if qualified.any() else None,
                mfe_conversion=float(t.trade_profit.sum())/mfes if mfes else None,
                avg_net_r=float((net/t.initial_risk_money).mean()) if n else 0.,
                avg_mae_r=float((t.mae_money/t.initial_risk_money).mean()) if n else 0.,
                avg_mfe_r=float((t.mfe_money/t.initial_risk_money).mean()) if n else 0.,
                months={str(k):float(v) for k,v in month.items()},years={str(k):float(v) for k,v in years.items()})


def select_for_year(variants,year,training_start="2010-06-07"):
    end=pd.Timestamp(year=year,month=1,day=1)
    scores={};counts={}
    for name in CANDIDATES:
        t=variants[name]
        train=t[(t.entry_time>=pd.Timestamp(training_start))&(t.entry_time<end)]
        counts[name]={r:int((train.regime_name==r).sum()) for r in REGIMES}
        if name!="baseline" and min(counts[name].values())<75:
            continue
        scores[name]=metrics(train,training_start,end)["net_dd"]
    chosen=max(scores,key=scores.get) # insertion order is the prespecified tie break
    return chosen,scores,counts


def walk_forward(variants,years=range(2015,2026)):
    pieces=[];selections=[]
    for year in years:
        name,scores,counts=select_for_year(variants,year)
        t=variants[name]
        piece=t[t.entry_time.dt.year==year].copy()
        piece["selected_variant"]=name
        pieces.append(piece)
        selections.append(dict(year=year,variant=name,training_scores=scores,regime_counts=counts))
    return pd.concat(pieces,ignore_index=True),selections


def regime_metrics(trades,start,end,extra_cost=0.):
    total=metrics(trades,start,end,extra_cost)["net"]
    output={}
    for regime in (*REGIMES,"warmup"):
        m=metrics(trades[trades.regime_name==regime],start,end,extra_cost)
        m["share_of_total_net"]=m["net"]/total if total else None
        output[regime]=m
    return output
